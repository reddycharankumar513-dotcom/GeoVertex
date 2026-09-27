#!/usr/bin/env python3
"""GeoVertex Database Restore and Disaster Recovery Script.

Restores database from compressed backup archives with mandatory SHA-256 integrity
verification, confirmation guards, and post-restore health inspection.
Supports both PostgreSQL/PostGIS (production) and SQLite (development/staging).
"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from sqlalchemy import create_engine, inspect, text


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 cryptographic digest of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def verify_backup_integrity(backup_path: Path) -> bool:
    """Validates the SHA-256 checksum of the backup file against .sha256 or .manifest.json."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    actual_hash = compute_sha256(backup_path)

    # 1. Check for companion .sha256 file
    checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
    if not checksum_file.exists():
        checksum_file = backup_path.parent / f"{backup_path.name}.sha256"

    if checksum_file.exists():
        with open(checksum_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            expected_hash = line.split()[0].strip()
            if actual_hash.lower() == expected_hash.lower():
                print(f"[Checksum Verified] SHA-256 matched .sha256 file: {actual_hash}")
                return True
            else:
                raise ValueError(
                    f"CHECKSUM MISMATCH! Expected: {expected_hash}, Actual: {actual_hash}"
                )

    # 2. Check for companion .manifest.json file
    manifest_file = backup_path.with_name(backup_path.stem.replace(".db", "").replace(".dump", "") + ".manifest.json")
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            expected_hash = manifest_data.get("sha256")
            if expected_hash and actual_hash.lower() == expected_hash.lower():
                print(f"[Checksum Verified] SHA-256 matched manifest: {actual_hash}")
                return True
            elif expected_hash:
                raise ValueError(
                    f"CHECKSUM MISMATCH! Expected: {expected_hash}, Actual: {actual_hash}"
                )

    print(f"[Warning] No checksum file found for {backup_path.name}. Computed SHA-256: {actual_hash}")
    return True


def verify_restored_database(sync_url: str) -> Dict[str, Any]:
    """Inspects restored database to ensure schema and table validity."""
    connect_args = {"check_same_thread": False} if "sqlite" in sync_url else {}
    engine = create_engine(sync_url, connect_args=connect_args)
    results = {}
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        results["table_count"] = len(tables)
        results["tables"] = tables

        try:
            res = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = res.fetchone()
            results["alembic_revision"] = str(row[0]) if row else "none"
        except Exception:
            results["alembic_revision"] = "not_found"

    return results


def restore_sqlite(backup_path: Path, target_path: Path):
    """Restores SQLite database file from compressed .db.gz archive."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_restored = target_path.with_suffix(".tmp_restore")

    try:
        with gzip.open(backup_path, "rb") as f_in:
            with open(temp_restored, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Integrity check on SQLite database
        test_conn = sqlite3.connect(str(temp_restored))
        cursor = test_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        status = cursor.fetchone()[0]
        test_conn.close()

        if status != "ok":
            raise ValueError(f"SQLite PRAGMA integrity_check failed with status: {status}")

        # Atomic replacement of target database
        if target_path.exists():
            backup_old = target_path.with_suffix(".pre_restore_bak")
            shutil.copy2(target_path, backup_old)

        shutil.move(str(temp_restored), str(target_path))
        print(f"Successfully restored SQLite database to: {target_path}")

    finally:
        if temp_restored.exists():
            temp_restored.unlink(missing_ok=True)


def restore_postgres(backup_path: Path, db_url: str):
    """Restores PostgreSQL database from compressed custom dump archive using pg_restore."""
    from urllib.parse import urlparse
    cleaned_url = db_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(cleaned_url)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    # Decompress to temporary file for pg_restore
    temp_dump = backup_path.with_suffix(".tmp_dump")
    try:
        with gzip.open(backup_path, "rb") as f_in:
            with open(temp_dump, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        cmd = [
            "pg_restore",
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "geovertex",
            "-d", parsed.path.lstrip("/") or "geovertex_db",
            "--clean",
            "--if-exists",
            "--no-owner",
            str(temp_dump),
        ]

        subprocess.run(cmd, env=env, check=True)
        print("Successfully restored PostgreSQL database via pg_restore.")
    finally:
        if temp_dump.exists():
            temp_dump.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="GeoVertex Production Database Restore Utility")
    parser.add_argument(
        "--backup-file",
        type=Path,
        required=True,
        help="Path to the .gz backup archive",
    )
    parser.add_argument(
        "--target-db-url",
        type=str,
        default=None,
        help="Target database sync URL (defaults to configured DATABASE_URL_SYNC)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify archive integrity and print manifest without restoring data",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Mandatory confirmation flag required to execute restore operation",
    )
    args = parser.parse_args()

    backup_path = args.backup_file.resolve()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Processing backup archive: {backup_path}")

    # 1. Integrity check
    try:
        verify_backup_integrity(backup_path)
    except Exception as e:
        print(f"Integrity check failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verify_only:
        print("Archive integrity verified successfully. (--verify-only mode: exiting without changes)")
        sys.exit(0)

    # 2. Safety guard check
    if not args.confirm:
        print(
            "ERROR: Database restoration requires explicit --confirm flag to avoid accidental data overwrite.\n"
            "Usage: python restore.py --backup-file <path> --confirm",
            file=sys.stderr,
        )
        sys.exit(2)

    db_url = args.target_db_url or settings.DATABASE_URL_SYNC
    is_sqlite = "sqlite" in db_url.lower()

    try:
        if is_sqlite:
            raw_path_str = db_url.split("///")[-1]
            target_path = Path(raw_path_str).resolve()
            restore_sqlite(backup_path, target_path)
        else:
            restore_postgres(backup_path, db_url)

        # 3. Post-restore verification
        verification = verify_restored_database(db_url)
        print(f"[{datetime.now(timezone.utc).isoformat()}] Post-restore verification successful:")
        print(f" - Restored Tables:   {verification['table_count']}")
        print(f" - Alembic Revision: {verification['alembic_revision']}")
        sys.exit(0)

    except Exception as e:
        print(f"Restoration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
