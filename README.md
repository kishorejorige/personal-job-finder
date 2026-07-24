# Personal Job Finder

This is a personal, local full-stack application to parse resumes, find jobs, track applications, and match job descriptions to your profile.

---

## Supported Resume Formats (Phase 2)
- **File Extensions**: `.pdf`, `.docx`, `.txt`
- **Maximum File Size**: 2 MB
- **Basic Protections**: File size limits, extension allowlist validation, safe filename handling, and no HTML execution from parsed text.

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

To run the application locally, open two terminal windows (one for backend and one for frontend).

### Start the Backend Server

Inside the `backend` folder (with `.venv` active):
```bash
# Set PYTHONPATH and start uvicorn
# On Windows (PowerShell):
$env:PYTHONPATH="."; uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# On Linux / macOS:
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
- **API Base URL**: `http://127.0.0.1:8001`
- **Interactive Documentation**: `http://127.0.0.1:8001/docs`

### Start the Angular Frontend

Inside the `frontend` folder:
```bash
npm start
```
The application will run at: `http://localhost:4200/`

---

## 3. Profile API Endpoints (Phase 2)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/profile/upload-resume` | Upload and parse `.pdf`/`.docx`/`.txt` resume (Max 2MB). Updates or creates the single active profile. |
| `GET` | `/api/profile` | Retrieve the active profile. Returns `404 Not Found` if empty. |
| `PUT` | `/api/profile` | Update profile fields manually. |

---

## 4. Verification and Testing

### Run Backend Unit Tests
To execute backend tests:
```powershell
cd backend
$env:PYTHONPATH="."; .venv\Scripts\python.exe -m pytest
```

### Manual Resume Verification Test
To manually verify the resume extraction pipeline:
1. Create a local temporary `.txt` file named `sample_resume.txt` with these contents:
   ```text
   Kishore
   Hyderabad, India
   kishore@example.com
   9876543210

   PYTHON DEVELOPER

   SUMMARY
   Python developer building automation tools, FastAPI applications and AI projects.

   SKILLS
   Python, FastAPI, Docker, SQLite, PostgreSQL, Git, REST API

   PROJECTS
   Personal Job Finder
   AI Resume and Proposal Generator
   JobMatch AI Agent

   EDUCATION
   ITI Electronics

   CERTIFICATIONS
   AI Foundations
   ```
2. Navigate to `http://localhost:4200/profile` in your browser.
3. Choose `sample_resume.txt` and click **Choose Resume File** to select it. The file will automatically upload and scan.
4. Verify that the profile form populates with the extracted data (Name: Kishore, Title: PYTHON DEVELOPER, etc.).
5. Make edits to the fields, click **Save Profile**, refresh the page, and confirm that the updated values persist.
