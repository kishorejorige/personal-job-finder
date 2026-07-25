# Personal Job Finder

This is a personal, local full-stack application to parse resumes, find jobs, track applications, and match job descriptions to your profile.

---

## Capabilities & Supported Formats

### Resume Extraction (Phase 2)
- **Supported Resume formats**: `.pdf`, `.docx`, `.txt`
- **Maximum File Size**: 2 MB
- **Basic Protections**: File size limits, extension allowlist validation, safe filename handling, and no HTML execution from parsed text.

### Greenhouse Crawler (Phase 3)
- **Integration**: Scrapes public jobs via Greenhouse Boards API: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- **Search Scope**: Search is company-specific based on configured board tokens.
- **Fail-safe crawls**: Isolation per board token; if one board fails or times out, the search completes successfully for the other boards.
- **Automatic Matching**: Scores jobs from 0 to 100 based on matching skills, title overlap, experience keywords, and location.

---

## 1. Setup Instructions

### Windows (PowerShell)

#### Backend Setup
```powershell
# Navigate to the backend folder
cd backend

# Create the Python virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Create .env from template
copy .env.example .env
```

#### Frontend Setup
```powershell
# Navigate to the frontend folder
cd ../frontend

# Install dependencies
npm install
```

---

### Linux / macOS

#### Backend Setup
```bash
# Navigate to the backend folder
cd backend

# Create the Python virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
```

#### Frontend Setup
```bash
# Navigate to the frontend folder
cd ../frontend

# Install dependencies
npm install
```

---

## 2. Running the Application

### Option A: Running via Docker (Recommended)

To run the application with full persistence and production settings using Docker Compose:
```bash
# Start all services (detached mode)
docker compose up -d

# Stop services (keeps your database volume)
docker compose down

# Stop services and purge data volume (destructive)
docker compose down -v
```
The application will run at:
- **Frontend URL**: `http://localhost:4200/`
- **Backend API URL**: `http://localhost:8010/`

For detailed production instructions, see [Production Deployment Guide](file:///E:/dev/projects/personal-job-finder/docs/deployment.md).

### Option B: Running Locally (Development Mode)

To run the application locally, open two terminal windows (one for backend and one for frontend).

#### Start the Backend Server

Inside the `backend` folder (with `.venv` active):
```bash
# On Windows (PowerShell):
$env:PYTHONPATH="."; .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

# On Linux / macOS:
PYTHONPATH=. .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```
- **API Base URL**: `http://127.0.0.1:8010`
- **Interactive Documentation**: `http://127.0.0.1:8010/docs`

#### Start the Angular Frontend

Inside the `frontend` folder:
```bash
npm start
```
The application will run at: `http://localhost:4200/`

For security practices, see [Security and Access Protection Guide](file:///E:/dev/projects/personal-job-finder/docs/security.md).


---

## 3. Greenhouse Board Configurations (Phase 3)

Greenhouse jobs are fetched using company-specific board tokens defined in `backend/app/providers/greenhouse_boards.py`.

### How to Add a Company Board
1. Open a target company's Greenhouse-hosted careers page (e.g., `https://boards.greenhouse.io/stripe`).
2. Identify the board token from the URL (`stripe`).
3. Open `backend/app/providers/greenhouse_boards.py` and append it:
   ```python
   GREENHOUSE_BOARDS = [
       ...
       {
           "company_name": "Stripe",
           "board_token": "stripe",
       }
   ]
   ```
4. Restart the backend server.
5. In the frontend, navigate to **Jobs** and click **Fetch Greenhouse Jobs**.

> [!WARNING]
> Some companies use custom styling, redirects, or entirely custom career portals. Only public boards hosted on `boards.greenhouse.io` are supported.

---

## 4. Match Score Weights (Phase 3)

When a job is parsed, its match score (0-100) is calculated against the active resume profile using these weights:
- **Skill Match (Max 60 points)**: Intersection of required job skills with profile skills. If no skills are defined in the job description, it falls back to matching profile skills against the description body text.
- **Title Match (Max 20 points)**: Overlap of keywords between the job title and the profile's professional title candidate.
- **Experience Match (Max 15 points)**: Frequency of job title keywords and skills appearing in the profile summary, projects, experience, or certifications.
- **Location Match (Max 5 points)**: Checked if the job is remote, or if the profile location matches the job location.

---

## 5. API Endpoint Reference

### Profile Endpoints (Phase 2)
- `POST /api/profile/upload-resume` - Upload and extract resume PDF/DOCX/TXT text (Max 2MB).
- `GET /api/profile` - Retrieve the active profile.
- `PUT /api/profile` - Edit profile details manually.

### Job Endpoints (Phase 3)
- `POST /api/jobs/search/greenhouse` - Trigger crawler on configured Greenhouse boards.
- `GET /api/jobs` - Return paginated, sorted, and filtered jobs.
- `GET /api/jobs/summary` - Retrieve job statistics for the Dashboard counters.
- `GET /api/jobs/{job_id}` - Retrieve one job.
- `PATCH /api/jobs/{job_id}/status` - Update status (sets applied date automatically if transitioned to `applied`).
- `PATCH /api/jobs/{job_id}/notes` - Edit user notes for the job.
- `POST /api/jobs/recalculate-matches` - Recalculate scores for all jobs.
- `DELETE /api/jobs/{job_id}` - Delete job from the local database.

---

## 6. Verification and Testing

### Run Backend Pytest Suite
```powershell
cd backend
$env:PYTHONPATH="."; .venv\Scripts\python.exe -m pytest
```
This runs 16 unit tests covering:
- Health diagnostics
- PDF/DOCX/TXT text parsers and validation limits
- HTML description sanitation and unescaping
- Word-boundary skill extraction and remote-status checks
- Match score calculations
- Sync duplication checks
- REST routes and stats aggregation
