import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.profile import Profile

# Use a temporary local SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test_profile.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    # Clean up previous runs
    db.query(Profile).delete()
    db.commit()

    yield db

    db.close()
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_profile.db"):
        try:
            os.remove("./test_profile.db")
        except PermissionError:
            pass


client = TestClient(app)

# Sample resumes
SAMPLE_TXT_RESUME = """
John Doe
New York, NY
john.doe@example.com
1234567890

SOFTWARE ENGINEER

SUMMARY
Experienced software engineer with a focus on web applications.

SKILLS
Python, FastAPI, SQL, Docker

EXPERIENCE
- Software Engineer at TechCorp (2021 - Present)
- Developer at StartupInc (2019 - 2021)

EDUCATION
- BS in Computer Science, State University

PROJECTS
- Job Finder App
- Personal Portfolio Website

CERTIFICATIONS
- AWS Certified Developer
"""


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_profile_not_found():
    response = client.get("/api/profile")
    assert response.status_code == 404
    assert "No profile found" in response.json()["detail"]


def test_unsupported_file_rejection():
    # Test uploading a file with an unsupported extension (e.g. .jpg)
    files = {"file": ("resume.jpg", b"fake image content", "image/jpeg")}
    response = client.post("/api/profile/upload-resume", files=files)
    assert response.status_code == 400
    assert "Only PDF, DOCX, and TXT resumes are supported" in response.json()["detail"]


def test_oversized_file_rejection():
    # Test file larger than 2MB
    large_content = b"a" * (2 * 1024 * 1024 + 10)
    files = {"file": ("resume.txt", large_content, "text/plain")}
    response = client.post("/api/profile/upload-resume", files=files)
    assert response.status_code == 400
    assert "larger than 2 MB" in response.json()["detail"]


def test_empty_resume_rejection():
    # Test empty text file
    files = {"file": ("resume.txt", b"", "text/plain")}
    response = client.post("/api/profile/upload-resume", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_profile_creation_from_txt_resume():
    # Test upload and check parsing
    files = {"file": ("resume.txt", SAMPLE_TXT_RESUME.encode("utf-8"), "text/plain")}
    response = client.post("/api/profile/upload-resume", files=files)
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Resume uploaded and scanned successfully."

    profile = data["profile"]
    assert profile["full_name"] == "John Doe"
    assert profile["email"] == "john.doe@example.com"
    assert profile["phone"] == "1234567890"
    assert profile["location"] == "New York, NY"
    assert profile["professional_title"] == "SOFTWARE ENGINEER"
    assert "Python" in profile["skills"]
    assert "FastAPI" in profile["skills"]
    assert len(profile["work_experience"]) == 2
    assert "State University" in profile["education"][0]
    assert "Job Finder App" in profile["projects"][0]
    assert "AWS Certified Developer" in profile["certifications"][0]


def test_get_profile_success():
    # First upload profile
    files = {"file": ("resume.txt", SAMPLE_TXT_RESUME.encode("utf-8"), "text/plain")}
    client.post("/api/profile/upload-resume", files=files)

    response = client.get("/api/profile")
    assert response.status_code == 200
    profile = response.json()
    assert profile["full_name"] == "John Doe"
    assert profile["email"] == "john.doe@example.com"


def test_update_profile():
    # Upload profile first
    files = {"file": ("resume.txt", SAMPLE_TXT_RESUME.encode("utf-8"), "text/plain")}
    client.post("/api/profile/upload-resume", files=files)

    # Send PUT update
    update_data = {
        "full_name": "John Updated",
        "email": "john.updated@example.com",
        "phone": "9999999999",
        "location": "Boston, MA",
        "professional_title": "Senior Software Engineer",
        "professional_summary": "Updated summary description.",
        "skills": ["Python", "FastAPI", "Kubernetes", "AWS"],
        "work_experience": [
            "Senior Developer at BigCo (2022-Present)",
            "Software Engineer at TechCorp (2021-2022)",
        ],
        "education": [
            "MS in Computer Science, State University",
            "BS in Computer Science, State University",
        ],
        "projects": ["Updated Project"],
        "certifications": ["AWS Solutions Architect", "AWS Certified Developer"],
    }

    response = client.put("/api/profile", json=update_data)
    assert response.status_code == 200
    profile = response.json()
    assert profile["full_name"] == "John Updated"
    assert profile["email"] == "john.updated@example.com"
    assert "Kubernetes" in profile["skills"]
    assert len(profile["skills"]) == 4

    # Confirm DB got updated and resume_text wasn't overwritten
    get_resp = client.get("/api/profile")
    assert get_resp.status_code == 200
    profile_db = get_resp.json()
    assert profile_db["resume_text"] is not None
    assert profile_db["full_name"] == "John Updated"


def test_reupload_updates_active_profile():
    # 1. Upload first profile
    files1 = {"file": ("resume1.txt", SAMPLE_TXT_RESUME.encode("utf-8"), "text/plain")}
    client.post("/api/profile/upload-resume", files=files1)

    # 2. Upload second profile (updates the single active profile)
    second_resume = """
    Jane Smith
    San Francisco, CA
    jane.smith@example.com
    9876543210

    PRODUCT MANAGER

    SUMMARY
    Product Manager leading product teams.

    SKILLS
    Product Roadmap, Agile, SQL
    """
    files2 = {"file": ("resume2.txt", second_resume.encode("utf-8"), "text/plain")}
    response = client.post("/api/profile/upload-resume", files=files2)
    assert response.status_code == 200

    # 3. Get profile and check that it's now Jane Smith
    get_resp = client.get("/api/profile")
    assert get_resp.status_code == 200
    profile = get_resp.json()
    assert profile["full_name"] == "Jane Smith"
    assert profile["email"] == "jane.smith@example.com"
    assert "Product Roadmap" in profile["skills"]
