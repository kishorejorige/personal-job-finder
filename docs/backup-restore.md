# Backup and Restore Procedures

This document provides instructions for backup, recovery, and data migration of the SQLite database.

---

## 1. Database Storage Location

The application database is stored as a single SQLite file:
- **Local run default**: `backend/jobs.db`
- **Docker Compose default**: `/app/data/jobs.db` (persisted on host via the `personal_job_finder_sqlite_data` volume)

---

## 2. Backup Strategy

Since the database uses SQLite, taking a backup is simple: you can copy the file directly or use SQLite's safe online backup command (which prevents issues if a write transaction is in progress).

### Method A: Online SQLite Backup (Recommended)

Run this command inside the host or container environment to perform a safe hot-backup:
```bash
sqlite3 /app/data/jobs.db ".backup '/app/data/backup_$(date +%Y%m%d).db'"
```
This ensures SQLite's Write-Ahead Log (WAL) changes are fully checkpointed and the backup is structurally consistent.

### Method B: Host-Level Volume Backup

If running via Docker Compose, you can back up the named volume by creating a tarball:
```bash
docker run --rm \
  -v personal_job_finder_sqlite_data:/volume \
  -v "$(pwd)":/backup \
  alpine tar cvf /backup/backup_database.tar /volume
```
This command creates a `backup_database.tar` archive containing the SQLite database files in the current folder.

---

## 3. Restore Strategy

### Method A: Direct File Restore

To restore, replace the active database file with a backup copy while the server is stopped.

1. Stop the application services:
   ```bash
   docker compose down
   ```
2. Copy the backup file over the active database file:
   ```bash
   cp backup_20260725.db backend/jobs.db
   ```
3. Restart the application:
   ```bash
   docker compose up -d
   ```

### Method B: Docker Named Volume Restore

If you need to restore files into the named volume from a host tar archive:
1. Stop the services:
   ```bash
   docker compose down
   ```
2. Run a temporary container to extract the archive into the named volume:
   ```bash
   docker run --rm \
     -v personal_job_finder_sqlite_data:/volume \
     -v "$(pwd)":/backup \
     alpine sh -c "rm -rf /volume/* && tar xvf /backup/backup_database.tar -C /"
   ```
3. Start the services:
   ```bash
   docker compose up -d
   ```
