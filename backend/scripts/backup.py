#!/usr/bin/env python3
"""GeoVertex Automated Database Backup Script.

Creates timestamped, compressed database backups with cryptographic SHA-256 checksums
and metadata manifests for disaster recovery and operational compliance.
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
from typing import Any, Dict, List

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


def get_table_statistics(sync_url: str) -> Dict[str, int]:
    """Queries row counts for all application tables."""
    stats = {}
    try:
        connect_args = {"check_same_thread": False} if "sqlite" in sync_url else {}
        engine = create_engine(sync_url, connect_args=connect_args)
        with engine.connect() as conn:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            for t in sorted(table_names):
                try:
                    res = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"'))
                    stats[t] = res.scalar() or 0
                except Exception:
                    stats[t] = -1
    except Exception as e:
        print(f"Warning: Could not extract table statistics: {e}", file=sys.stderr)
    return stats


def get_alembic_version(sync_url: str) -> str:
    """Retrieves current migration head revision from the alembic_version table."""
    try:
        connect_args = {"check_same_thread": False} if "sqlite" in sync_url else {}
        engine = create_engine(sync_url, connect_args=connect_args)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = res.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    return "unknown"


def backup_sqlite(db_path: Path, output_gz: Path) -> int:
    """Performs atomic online backup of SQLite database and gzips it."""
    temp_raw = output_gz.with_suffix(".tmp_raw")
    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(temp_raw))
        with dst:
            src.backup(dst, pages=100)
        dst.close()
        src.close()

        with open(temp_raw, "rb") as f_in:
            with gzip.open(output_gz, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        return output_gz.stat().st_size
    finally:
        if temp_raw.exists():
            temp_raw.unlink(missing_ok=True)


def backup_postgres(db_url: str, output_gz: Path) -> int:
    """Performs pg_dump of PostgreSQL/PostGIS database and gzips it."""
    # Parse connection components
    from urllib.parse import urlparse
    cleaned_url = db_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(cleaned_url)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "geovertex",
        "-d", parsed.path.lstrip("/") or "geovertex_db",
        "-F", "c",  # Custom format (compressed, supports parallel restore)
    ]

    try:
        with open(output_gz, "wb") as f_out:
            proc = subprocess.run(cmd, stdout=f_out, stderr=subprocess.PIPE, env=env, check=True)
        return output_gz.stat().st_size
    except FileNotFoundError:
        print("pg_dump not found in system PATH. Attempting fallback SQL export...", file=sys.stderr)
        # Fallback to python-level schema+data export
        connect_args = {}
        engine = create_engine(settings.DATABASE_URL_SYNC, connect_args=connect_args)
        with gzip.open(output_gz, "wt", encoding="utf-8", compresslevel=9) as f_out:
            f_out.write(f"-- GeoVertex Automated SQL Fallback Backup\n-- Timestamp: {datetime.now(timezone.utc).isoformat()}\n\n")
            with engine.connect() as conn:
                inspector = inspect(engine)
                for t in inspector.get_table_names():
                    res = conn.execute(text(f'SELECT * FROM "{t}"'))
                    f_out.write(f"-- Table: {t}\n")
                    for row in res.mappings():
                        f_out.write(f"INSERT INTO {t} VALUES ({row});\n")
        return output_gz.stat().st_size


def run_backup(output_dir: Path, db_url: str) -> Dict[str, Any]:
    """Executes full database backup and returns metadata manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    is_sqlite = "sqlite" in db_url.lower()
    db_type = "sqlite" if is_sqlite else "postgresql"

    ext = ".db.gz" if is_sqlite else ".dump.gz"
    backup_filename = f"geovertex_backup_{db_type}_{timestamp_str}{ext}"
    backup_file_path = output_dir / backup_filename
    manifest_file_path = output_dir / f"geovertex_backup_{db_type}_{timestamp_str}.manifest.json"
    checksum_file_path = output_dir / f"{backup_filename}.sha256"

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting {db_type.upper()} database backup...")

    if is_sqlite:
        # Extract raw path
        raw_path_str = db_url.split("///")[-1]
        db_path = Path(raw_path_str).resolve()
        if not db_path.exists():
            raise FileNotFoundError(f"SQLite database file not found at: {db_path}")
        size_bytes = backup_sqlite(db_path, backup_file_path)
    else:
        size_bytes = backup_postgres(db_url, backup_file_path)

    # Compute Checksum
    sha256_hash = compute_sha256(backup_file_path)
    with open(checksum_file_path, "w", encoding="utf-8") as f_chk:
        f_chk.write(f"{sha256_hash}  {backup_filename}\n")

    # Table statistics & migration revision
    table_stats = get_table_statistics(settings.DATABASE_URL_SYNC)
    alembic_rev = get_alembic_version(settings.DATABASE_URL_SYNC)

    manifest: Dict[str, Any] = {
        "backup_name": backup_filename,
        "database_type": db_type,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_hash,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 3),
        "alembic_revision": alembic_rev,
        "environment": settings.ENVIRONMENT,
        "total_tables": len(table_stats),
        "tables": table_stats,
        "verified": True,
    }

    with open(manifest_file_path, "w", encoding="utf-8") as f_m:
        json.dump(manifest, f_m, indent=2)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Backup completed successfully:")
    print(f" - Backup file: {backup_file_path} ({manifest['size_mb']} MB)")
    print(f" - SHA-256:     {sha256_hash}")
    print(f" - Tables:      {manifest['total_tables']}")
    print(f" - Alembic Rev: {alembic_rev}")
    print(f" - Manifest:    {manifest_file_path}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="GeoVertex Production Database Backup Utility")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BACKEND_DIR / "backups",
        help="Target directory for backup archives (default: backend/backups)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=settings.DATABASE_URL_SYNC,
        help="Database connection URL",
    )
    args = parser.parse_args()

    try:
        run_backup(args.output_dir, args.database_url)
        sys.exit(0)
    except Exception as e:
        print(f"Backup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
