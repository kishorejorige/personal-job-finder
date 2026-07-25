from datetime import datetime

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.routes import jobs, profile, reports

# Automatically upgrade database schema for SQLite if needed before running create_all
with engine.connect() as conn:
    try:
        # Check jobs columns
        result = conn.execute(text("PRAGMA table_info(jobs)"))
        columns = [row[1] for row in result.fetchall()]

        if columns:  # Only alter if table exists
            if "job_fingerprint" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_fingerprint VARCHAR"))
                conn.execute(text("CREATE INDEX ix_jobs_job_fingerprint ON jobs (job_fingerprint)"))
            if "duplicate_of_id" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN duplicate_of_id INTEGER"))
                conn.execute(text("CREATE INDEX ix_jobs_duplicate_of_id ON jobs (duplicate_of_id)"))
            conn.commit()
    except Exception:
        # If the table doesn't exist yet, create_all will handle it
        pass

    try:
        # Check profiles columns
        result = conn.execute(text("PRAGMA table_info(profiles)"))
        columns = [row[1] for row in result.fetchall()]

        if columns:  # Only alter if table exists
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
                "resume_quality": "VARCHAR",
            }
            for col, col_type in new_cols.items():
                if col not in columns:
                    conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col} {col_type}"))
            conn.commit()
    except Exception:
        pass

# Create database tables (if not already existing)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Job Finder API")

# Register routes
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

# Configure CORS dynamically
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

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
    except Exception:
        db_status = "error"

    return {
        "status": "healthy",
        "database": db_status,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/ready")
def ready_check(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}
