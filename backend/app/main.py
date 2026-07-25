from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine, Base
from app.config import settings
from app.models.profile import Profile
from app.models.job import Job
from app.models.provider_run import ProviderRun
from app.routes import profile
from app.routes import jobs

# Automatically upgrade database schema for SQLite if needed before running create_all
with engine.connect() as conn:
    try:
        # Check jobs columns
        result = conn.execute(text("PRAGMA table_info(jobs)"))
        columns = [row[1] for row in result.fetchall()]

        if columns: # Only alter if table exists
            if "job_fingerprint" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_fingerprint VARCHAR"))
                conn.execute(text("CREATE INDEX ix_jobs_job_fingerprint ON jobs (job_fingerprint)"))
            if "duplicate_of_id" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN duplicate_of_id INTEGER"))
                conn.execute(text("CREATE INDEX ix_jobs_duplicate_of_id ON jobs (duplicate_of_id)"))
            conn.commit()
    except Exception as e:
        # If the table doesn't exist yet, create_all will handle it
        pass

# Create database tables (if not already existing)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Job Finder API")

# Register routes
app.include_router(profile.router)
app.include_router(jobs.router)

# Configure CORS for local development
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Run a simple query to verify database connectivity
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status
    }
