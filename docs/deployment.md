# Production Deployment Guide

This document describes how to deploy the Personal Job Finder application for production and personal use.

---

## 1. Environment Configuration

The backend is configured using Pydantic settings. Environment variables can be defined in a `.env` file in the `backend/` directory or injected directly into the execution environment.

### Available Variables

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Application environment (`development` or `production`) | `production` |
| `APP_NAME` | Display name of the application | `Personal Job Finder` |
| `APP_VERSION` | Version identifier | `1.0.0` |
| `DEBUG` | Enable debug logs and tracebacks | `false` |
| `HOST` | IP address to bind the backend server to | `0.0.0.0` |
| `PORT` | Port number to bind the backend server to | `8010` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./jobs.db` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:4200,http://127.0.0.1:4200` |
| `LOG_LEVEL` | Minimum logging severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `MAX_RESUME_SIZE_MB` | Maximum allowed file size for resume uploads | `2` |
| `PROVIDER_REFRESH_COOLDOWN_MINUTES` | Cooldown period before allowing next job fetch | `15` |
| `REQUEST_TIMEOUT_SECONDS` | Maximum timeout for job crawlers network requests | `10` |
| `MAX_EXPORT_ROWS` | Maximum limit of rows in PDF/CSV export results | `1000` |

---

## 2. Containerized Deployment (Recommended)

Docker Compose provides a fully automated build, run, and volume-persistence configuration.

### Prerequisites

Ensure you have Docker and Docker Compose installed:
- Docker Engine >= 20.10
- Docker Compose >= 2.0

### Run via Docker Compose

1. Clone the repository and navigate to the project directory:
   ```bash
   cd E:\dev\projects\personal-job-finder
   ```
2. Build and start the services in detached mode:
   ```bash
   docker compose up -d
   ```
3. Verify that both containers are running and healthy:
   ```bash
   docker compose ps
   ```
   - **Frontend**: Exposes port `4200` on your host machine (`http://localhost:4200`).
   - **Backend**: Exposes port `8010` on your host machine for checking endpoints (`http://localhost:8010`).

### Persistent Storage

The SQLite database is mapped to a named Docker volume (`personal_job_finder_sqlite_data`) pointing to the `/app/data` directory inside the backend container.

> [!WARNING]
> Running `docker compose down` will shut down the containers but preserve your database volume.
> Running `docker compose down -v` will **permanently delete** the database volume, losing all profiles and tracked applications.

---

## 3. Manual Server Deployment

If you are deploying to a local machine without Docker, follow these steps.

### Production Run Commands

#### Backend (Unix / Linux)

Navigate to the `backend` folder, activate the virtual environment, and run:
```bash
./start.sh
```
Or directly:
```bash
uvicorn app.main:app \
  --host "0.0.0.0" \
  --port 8010 \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips="*"
```
*(Using 1 worker is recommended for this personal SQLite application to prevent database write contention.)*

#### Backend (Windows PowerShell)

```powershell
$env:PORT=8010
$env:WEB_WORKERS=1
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 1
```

#### Frontend serving

Compile the static production bundle:
```bash
npm --prefix frontend run build
```
Copy the contents of `frontend/dist/frontend/browser` into the public directory of a high-performance web server (such as Nginx, Apache, or Caddy). Configure Nginx to reverse-proxy requests at `/api/` to the backend server at `http://127.0.0.1:8010/api/`.

---

## 4. Verification Procedures

### Health Check

Query the health check endpoint:
```bash
curl -f http://127.0.0.1:8010/api/health
```
**Expected Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2026-07-25T11:53:01Z"
}
```

### Readiness Check

Query the readiness check endpoint:
```bash
curl -f http://127.0.0.1:8010/api/ready
```
**Expected Status Code**:
- `200 OK` (when database connectivity is fully operational)
- `503 Service Unavailable` (when database connection fails)
