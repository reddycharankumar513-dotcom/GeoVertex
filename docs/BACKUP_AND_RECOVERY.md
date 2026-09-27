# GeoVertex Backup & Disaster Recovery Guide

## 1. Business Continuity & Disaster Recovery Objectives

The GeoVertex platform serves as the authoritative spatial registry for cadastral parcels, 3D vertical units, and underground utility alignments. Loss of data integrity or prolonged downtime carries severe legal and operational consequences.

### Operational Recovery Objectives

| Metric | Target Objective | Strategy |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | $\le 1\text{ hour}$ | Daily full backups + continuous Write-Ahead Log (WAL) archiving |
| **Recovery Time Objective (RTO)** | $\le 15\text{ minutes}$ | Automated decompress & restore scripts with checksum pre-verification |
| **Backup Retention** | 90 days local / 7 years cold archive | Daily rolling rotation + monthly immutable S3 Glacier snapshots |
| **Data Integrity Assurance** | 100% cryptographic match | SHA-256 digests computed at generation and verified prior to restore |

---

## 2. Backup Architecture & The 3-2-1 Rule

GeoVertex implements the industry-standard **3-2-1 Backup Strategy**:
- **3 copies of data**: Primary production database, local daily backup archive, and offsite cloud replica.
- **2 different media types**: NVMe block storage volume and cloud object storage (S3/MinIO).
- **1 offsite copy**: Geographically distinct cloud region (e.g., AWS S3 with Cross-Region Replication enabled).

```mermaid
flowchart TD
    subgraph Primary_Site["Primary Production Datacenter"]
        DB["PostgreSQL 16 + PostGIS\n(Active Master)"]
        WAL["Write-Ahead Logs (WAL)"]
        LocalBackups["Local Backup Storage\n(/opt/geovertex/backend/backups)"]
        BackupScript["backup.py\n(Nightly 02:00 UTC)"]
    end

    subgraph Offsite_Cloud["Offsite Cloud Replica (AWS S3)"]
        S3Bucket["S3 Cadastral Archive Bucket\n(Object Lock / WORM Enabled)"]
        S3Glacier["S3 Glacier Deep Archive\n(7-Year Statutory Retention)"]
    end

    DB -->|Continuous Stream| WAL
    DB -->|pg_dump snapshot| BackupScript
    BackupScript -->|Gzip + SHA-256| LocalBackups
    LocalBackups -->|Sync via AWS CLI / rclone| S3Bucket
    S3Bucket -->|Lifecycle Rule (90d)| S3Glacier
```

---

## 3. Automated Backup Utility (`backend/scripts/backup.py`)

The automated backup tool executes atomic snapshots of both PostgreSQL (production) and SQLite (staging/development).

### 3.1 Execution Command

```bash
# Execute standard scheduled backup
python backend/scripts/backup.py --output-dir backend/backups
```

### 3.2 Output Artifacts
For each backup execution, three synchronized artifacts are produced:
1. **Archive**: `geovertex_backup_postgresql_YYYYMMDD_HHMMSS.dump.gz` (Compressed binary dump).
2. **Checksum**: `geovertex_backup_postgresql_YYYYMMDD_HHMMSS.dump.gz.sha256` (Cryptographic verification hash).
3. **Manifest**: `geovertex_backup_postgresql_YYYYMMDD_HHMMSS.manifest.json` (Metadata, table statistics, and Alembic migration version).

### 3.3 Sample Manifest (`.manifest.json`)
```json
{
  "backup_name": "geovertex_backup_postgresql_20260927_020000.dump.gz",
  "database_type": "postgresql",
  "timestamp_utc": "2026-09-27T02:00:00.124500+00:00",
  "sha256": "eba5eb4760c32d730cb3826e645a5e409f45d2ad643ebd824cdb05fcd6f312ae",
  "size_bytes": 156241920,
  "size_mb": 148.98,
  "alembic_revision": "013_phase13_governance",
  "environment": "production",
  "total_tables": 66,
  "verified": true
}
```

---

## 4. Disaster Recovery & Restoration Procedures (`backend/scripts/restore.py`)

The restoration utility enforces mandatory integrity verification before applying changes and requires an explicit `--confirm` flag to prevent accidental data destruction.

### 4.1 Step 1: Verify Backup Integrity
Verify the archive without modifying the active database:
```bash
python backend/scripts/restore.py \
  --backup-file backend/backups/geovertex_backup_postgresql_20260927_020000.dump.gz \
  --verify-only
```

### 4.2 Step 2: Execute Database Restoration
```bash
python backend/scripts/restore.py \
  --backup-file backend/backups/geovertex_backup_postgresql_20260927_020000.dump.gz \
  --confirm
```

### 4.3 Step 3: Post-Restoration Verification Checklist
1. Ensure table counts match the manifest (`total_tables: 66`).
2. Verify Alembic schema migration head (`013_phase13_governance`).
3. Run readiness probe:
   ```bash
   curl -f http://localhost/health/ready
   ```
4. Perform sample query on core cadastral parcels:
   ```bash
   curl -f -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/parcels?limit=5
   ```
