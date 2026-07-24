import os
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.job import Job
from app.models.profile import Profile
from app.services.job_parser import clean_html, detect_remote_status, extract_skills_from_text
from app.services.job_matcher import calculate_match

# Override Database Url for testing
TEST_DATABASE_URL = "sqlite:///./test_jobs.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.query(Job).delete()
    db.query(Profile).delete()
    db.commit()
    yield db
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_jobs.db"):
        try:
            os.remove("./test_jobs.db")
        except PermissionError:
            pass

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Test HTML description cleaning
def test_html_cleaning():
    html_text = "<p>Hello <b>World</b>!</p><script>console.log('test')</script> &amp; Welcome&nbsp;here."
    cleaned = clean_html(html_text)
    assert "Hello World" in cleaned
    assert "console.log" not in cleaned
    assert "Welcome here" in cleaned
    assert "  " not in cleaned

# 2. Test Remote-status detection
def test_remote_status_detection():
    assert detect_remote_status("Software Engineer (Remote)", "New York", "We work from home.") == "remote"
    assert detect_remote_status("Senior Architect", "Office in SF", "This is a hybrid position.") == "hybrid"
    assert detect_remote_status("Staff Engineer", "Onsite - Austin, TX", "In-office work required.") == "onsite"
    assert detect_remote_status("Developer", "Unknown", "Apply now.") == "unknown"

# 3. Test Skill extraction
def test_skill_extraction():
    text = "We are looking for a Python backend engineer with FastAPI, docker experience. SQL/PostgreSQL database knowledge. Not searching for react developer."
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "PostgreSQL" in skills
    assert "SQL" in skills
    assert "React" in skills
    assert "R" not in skills

# 4. Test Match score calculation
def test_match_score_calculation(setup_db):
    db = setup_db
    # Create profile
    profile = Profile(
        full_name="John Doe",
        professional_title="Python Developer",
        location="New York, NY",
        professional_summary="Backend python engineer",
        skills=json.dumps(["Python", "FastAPI", "Docker"]),
        work_experience=json.dumps(["Worked at TechCorp"]),
        projects=json.dumps(["Built Job Finder"]),
        certifications=json.dumps(["AWS Certified Developer"])
    )
    db.add(profile)
    db.commit()

    # Calculate match
    res = calculate_match(
        job_title="Python Developer",
        job_description="We build FastAPI and docker apps.",
        job_skills=["Python", "FastAPI", "Docker", "AWS"],
        job_remote="remote",
        job_location="Unknown",
        profile=profile
    )

    assert res["match_score"] > 70
    assert "Python" in res["matched_skills"]
    assert "AWS" in res["missing_skills"]

# 5. Test Missing-profile behavior
def test_missing_profile_match():
    res = calculate_match(
        job_title="Python Developer",
        job_description="FastAPI apps.",
        job_skills=["Python", "FastAPI"],
        job_remote="remote",
        job_location="Unknown",
        profile=None
    )
    assert res["match_score"] == 0
    assert len(res["matched_skills"]) == 0
    assert "Python" in res["missing_skills"]

# 6. Test crawler mock and duplicate prevention
def test_greenhouse_search_and_sync(setup_db, monkeypatch):
    db = setup_db

    # Create dummy profile
    profile = Profile(
        full_name="John Doe",
        professional_title="Developer",
        skills=json.dumps(["Python", "FastAPI"])
    )
    db.add(profile)
    db.commit()

    # Mock provider.fetch_jobs
    mock_jobs = [
        {
            "external_id": "job_123",
            "title": "Python Developer",
            "company_name": "Test Company",
            "location": "Remote",
            "original_url": "https://boards.greenhouse.io/test/jobs/123",
            "description": "<p>We build with Python &amp; FastAPI</p>",
            "posted_date": "2023-10-01T12:00:00Z",
            "source": "greenhouse",
            "source_board": "test"
        }
    ]
    mock_stats = {
        "source": "greenhouse",
        "boards_checked": 1,
        "boards_succeeded": 1,
        "boards_failed": 0,
        "errors": []
    }

    from app.providers.greenhouse import GreenhouseProvider
    async def mock_fetch(self):
        return mock_jobs, mock_stats

    monkeypatch.setattr(GreenhouseProvider, "fetch_jobs", mock_fetch)

    # 1. Trigger search (jobs_created should be 1)
    response = client.post("/api/jobs/search/greenhouse")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["jobs_created"] == 1
    assert res_data["jobs_updated"] == 0

    # Verify job is in DB
    job_db = db.query(Job).filter(Job.external_id == "job_123").first()
    assert job_db is not None
    assert job_db.application_status == "not_applied"
    assert job_db.match_score > 50

    # 2. Update status and notes manually
    job_db.application_status = "saved"
    job_db.notes = "Initial notes"
    db.commit()

    # 3. Trigger search again (should result in jobs_updated == 1 and preserve status/notes)
    response2 = client.post("/api/jobs/search/greenhouse")
    assert response2.status_code == 200
    res_data2 = response2.json()
    assert res_data2["jobs_created"] == 0
    assert res_data2["jobs_updated"] == 1

    job_db_refetched = db.query(Job).filter(Job.external_id == "job_123").first()
    assert job_db_refetched.application_status == "saved"
    assert job_db_refetched.notes == "Initial notes"

# 7. Test REST API Actions
def test_job_endpoints(setup_db):
    db = setup_db
    # Create a job
    job = Job(
        external_id="job_abc",
        title="Frontend Dev",
        company_name="Awesome Company",
        source="greenhouse",
        application_status="not_applied",
        skills=json.dumps(["JavaScript"]),
        matched_skills=json.dumps([]),
        missing_skills=json.dumps(["JavaScript"]),
        match_score=20
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # GET details
    response = client.get(f"/api/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Frontend Dev"

    # PATCH status to applied (sets applied_date)
    response_status = client.patch(f"/api/jobs/{job.id}/status", json={"application_status": "applied"})
    assert response_status.status_code == 200
    assert response_status.json()["application_status"] == "applied"
    assert response_status.json()["applied_date"] is not None

    # PATCH status to invalid (should fail)
    response_invalid = client.patch(f"/api/jobs/{job.id}/status", json={"application_status": "super_applied"})
    assert response_invalid.status_code == 422

    # PATCH notes
    response_notes = client.patch(f"/api/jobs/{job.id}/notes", json={"notes": "Updated Notes"})
    assert response_notes.status_code == 200
    assert response_notes.json()["notes"] == "Updated Notes"

    # GET summary
    response_summary = client.get("/api/jobs/summary")
    assert response_summary.status_code == 200
    sum_data = response_summary.json()
    assert sum_data["total_jobs"] == 1
    assert sum_data["applied"] == 1

    # DELETE
    response_del = client.delete(f"/api/jobs/{job.id}")
    assert response_del.status_code == 200
    assert db.query(Job).count() == 0
