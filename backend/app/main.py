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
from app.routes import reports

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

    try:
        # Check profiles columns
        result = conn.execute(text("PRAGMA table_info(profiles)"))
        columns = [row[1] for row in result.fetchall()]

        if columns: # Only alter if table exists
            new_cols = {
                "career_objective": "TEXT",
                "total_experience": "VARCHAR",
                "current_company": "VARCHAR",
                "current_role": "VARCHAR",
                "preferred_job_role": "VARCHAR",
                "preferred_location": "VARCHAR",
                "availability": "VARCHAR",
                "occupation_category": "VARCHAR",
                "technical_skills": "TEXT",
                "soft_skills": "TEXT",
                "languages": "TEXT",
                "achievements": "TEXT",
                "training": "TEXT",
                "internships": "TEXT",
                "licences": "TEXT",
                "tools_and_equipment": "TEXT",
                "additional_information": "TEXT",
                "resume_quality": "VARCHAR"
            }
            for col, col_type in new_cols.items():
                if col not in columns:
                    conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col} {col_type}"))
            conn.commit()
    except Exception as e:
        pass

# Create database tables (if not already existing)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Job Finder API")

# Register routes
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

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
