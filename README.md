# Personal Job Finder - Phase 1: Foundation

This is a personal, local full-stack application to parse resumes, find jobs, track applications, and match job descriptions to your profile.

---

## Prerequisites

Ensure you have the following installed on your machine:
- **Python**: Version 3.10 or higher
- **Node.js**: Version 18.x or higher (includes `npm`)

---

## 1. Setup Instructions

### Windows (PowerShell)

#### Backend Setup
```powershell
# Navigate to the backend folder
# (Assuming you are in the project root directory)
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

To run the application locally, you will need to open two terminal windows (one for the backend and one for the frontend).

### Start the Backend Server

Inside the `backend` folder (with `.venv` active):
```bash
# Set PYTHONPATH and start uvicorn
# On Windows (PowerShell):
$env:PYTHONPATH="."; uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# On Linux / macOS:
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
The API is available at: `http://127.0.0.1:8001`
Interactive API documentation (Swagger UI) is available at: `http://127.0.0.1:8001/docs`

### Start the Angular Frontend

Inside the `frontend` folder:
```bash
npm start
```
The application will open automatically at: `http://localhost:4200/`

---

## 3. Verification

Once both servers are running, navigating to `http://localhost:4200` will display the dashboard displaying:
- **Backend API Status**: `HEALTHY`
- **SQLite Database**: `CONNECTED`
