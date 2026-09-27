"""Phase 15 Production Readiness, DevOps, Health, Metrics & Backup Test Suite."""

import gzip
import os
import shutil
import tempfile
from pathlib import Path
import pytest
from httpx import AsyncClient
from app.core.config import Settings, settings
from app.services.document_storage_service import DocumentStorageService, document_storage_service
from scripts.backup import backup_sqlite, compute_sha256, run_backup
from scripts.restore import restore_sqlite, verify_backup_integrity


def test_settings_production_fail_fast():
    """Verifies that Settings strictly fails fast when insecure production configurations are present."""
    # 1. Production with DEBUG=True must raise ValueError
    with pytest.raises(ValueError, match="DEBUG must be False in production mode"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET="0123456789abcdef0123456789abcdef0123456789abcdef",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        )

    # 2. Production with default JWT_SECRET must raise ValueError
    with pytest.raises(ValueError, match="JWT_SECRET must be configured"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="geovertex-super-secret-jwt-key-change-in-production-2026",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        )

    # 3. Production with SQLite must raise ValueError
    with pytest.raises(ValueError, match="SQLite is not supported for production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="0123456789abcdef0123456789abcdef0123456789abcdef",
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
        )

    # 4. Valid production settings must succeed
    valid_prod = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET="0123456789abcdef0123456789abcdef0123456789abcdef",
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
    )
    assert valid_prod.ENVIRONMENT == "production"
    assert valid_prod.DEBUG is False


def test_connection_pool_settings():
    """Verifies database pool parameters are configured on Settings."""
    assert settings.DB_POOL_SIZE >= 10
    assert settings.DB_MAX_OVERFLOW >= 5
    assert settings.DB_POOL_TIMEOUT >= 10
    assert settings.DB_POOL_RECYCLE >= 300
    assert settings.DB_POOL_PRE_PING is True


def test_document_storage_service_abstraction():
    """Verifies DocumentStorageService multi-backend operations and security protections."""
    status = document_storage_service.get_storage_status()
    assert "backend" in status
    assert "local_dir" in status
    assert "writable" in status

    # Traversal attack protection
    with pytest.raises(Exception):
        document_storage_service.get_file_path("../../../etc/passwd")

    # Byte storage and retrieval
    storage_key, filename, size, sha256_hash, mime = document_storage_service.save_raw_bytes(
        document_id="test-doc-phase15",
        version_number=1,
        filename="test_deed.pdf",
        content=b"%PDF-1.4 test cadastral document content",
        content_type="application/pdf",
    )
    assert storage_key.endswith("test_deed.pdf")
    assert size == len(b"%PDF-1.4 test cadastral document content")
    assert sha256_hash is not None

    retrieved = document_storage_service.get_file_bytes(storage_key)
    assert retrieved == b"%PDF-1.4 test cadastral document content"

    # Cleanup
    document_storage_service.delete_document_files("test-doc-phase15")


@pytest.mark.asyncio
async def test_health_and_metrics_endpoints(client: AsyncClient):
    """Verifies Liveness, Readiness, and Prometheus metrics endpoints."""
    # 1. Liveness Probe
    r_live = await client.get("/health/live")
    assert r_live.status_code == 200
    live_data = r_live.json()
    assert live_data["status"] == "healthy"
    assert "uptime_seconds" in live_data

    # 2. Readiness Probe
    r_ready = await client.get("/health/ready")
    assert r_ready.status_code == 200
    ready_data = r_ready.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"]["connected"] is True
    assert "storage" in ready_data
    assert "subsystems" in ready_data

    # 3. Prometheus Metrics
    r_metrics = await client.get("/metrics")
    assert r_metrics.status_code == 200
    assert "text/plain" in r_metrics.headers["content-type"]
    text = r_metrics.text
    assert "geovertex_build_info" in text
    assert "geovertex_uptime_seconds" in text
    assert "geovertex_db_pool_size" in text


def test_backup_and_restore_cycle():
    """Performs an automated backup and restore cycle with SHA-256 validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "source.db"

        # Create source SQLite database with test table
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_parcels (id INTEGER PRIMARY KEY, parcel_code TEXT);")
        conn.execute("INSERT INTO test_parcels (parcel_code) VALUES ('PARCEL-P15-001');")
        conn.commit()
        conn.close()

        # Run backup
        backup_file = tmp_path / "test_backup.db.gz"
        size = backup_sqlite(db_path, backup_file)
        assert size > 0
        assert backup_file.exists()

        # Compute and write SHA-256 checksum
        sha = compute_sha256(backup_file)
        checksum_file = tmp_path / "test_backup.db.gz.sha256"
        with open(checksum_file, "w") as f:
            f.write(f"{sha}  {backup_file.name}\n")

        # Verify integrity check
        assert verify_backup_integrity(backup_file) is True

        # Restore to new target
        target_db = tmp_path / "restored.db"
        restore_sqlite(backup_file, target_db)
        assert target_db.exists()

        # Verify data in restored database
        r_conn = sqlite3.connect(str(target_db))
        cur = r_conn.cursor()
        cur.execute("SELECT parcel_code FROM test_parcels;")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "PARCEL-P15-001"
        r_conn.close()
