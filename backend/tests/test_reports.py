import csv
import io
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.job import Job
from app.models.profile import Profile

# SQLite test configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reports.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
client = TestClient(app)


@pytest.fixture
def db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db_sess = TestingSessionLocal()
        try:
            yield db_sess
        finally:
            db_sess.close()

    app.dependency_overrides[get_db] = override_get_db

    db_conn = TestingSessionLocal()

    # Clean tables before each test
    db_conn.query(Job).delete()
    db_conn.query(Profile).delete()
    db_conn.commit()

    yield db_conn

    # Tear down
    db_conn.close()
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


def populate_test_jobs(db):
    # Setup standard test jobs
    j1 = Job(
        title="Python Software Developer & Engineer",
        company_name="TechCorp 🚀",
        location="Delhi, India",
        remote_status="remote",
        employment_type="full-time",
        salary="120,000 INR",
        source="Greenhouse",
        source_board="tech-board",
        posted_date=datetime(2026, 7, 20),
        application_status="applied",
        applied_date=datetime(2026, 7, 21),
        matched_skills=json.dumps(["Python", "FastAPI"]),
        missing_skills=json.dumps(["Docker"]),
        notes="Notes with commas, quotes, and HTML tag <p>details</p>",
        original_url="https://example.com/jobs/python-dev-long-url-path-with-many-params-query-xyz-123456789",
        duplicate_of_id=None,
    )
    j2 = Job(
        title="Accountant",
        company_name="Finance Ledger",
        location="Mumbai, India",
        remote_status="onsite",
        employment_type="full-time",
        salary="60,000 INR",
        source="Lever",
        source_board="finance-site",
        posted_date=datetime(2026, 7, 22),
        application_status="saved",
        matched_skills=json.dumps(["Tally", "Accounting"]),
        missing_skills=json.dumps(["GST"]),
        notes="Saved for later.",
        original_url="https://example.com/jobs/accountant",
        duplicate_of_id=None,
    )
    j3 = Job(
        title="Office Administrator",
        company_name="Apex Admin",
        location="Delhi, India",
        remote_status="hybrid",
        employment_type="part-time",
        salary="30,000 INR",
        source="Ashby",
        source_board="apex-admin",
        posted_date=datetime(2026, 7, 23),
        application_status="not_applied",
        matched_skills=json.dumps(["Data Entry", "MS Office"]),
        missing_skills=json.dumps([]),
        notes="Not applied yet.",
        original_url="https://example.com/jobs/admin",
        duplicate_of_id=None,
    )
    j4 = Job(
        title="Software Engineer",
        company_name="Duplicate TechCorp",
        location="Delhi, India",
        remote_status="remote",
        employment_type="full-time",
        salary="120,000 INR",
        source="Greenhouse",
        posted_date=datetime(2026, 7, 20),
        application_status="applied",
        duplicate_of_id=1,
    )

    db.add_all([j1, j2, j3, j4])
    db.commit()


def populate_profile(db):
    p = Profile(
        full_name="Kishore Kumar",
        professional_title="Python Developer",
        occupation_category="IT and Software",
        preferred_job_role="Python Backend Developer",
        preferred_location="Delhi / Remote",
        total_experience="5 years",
        skills=json.dumps(["Python", "FastAPI", "SQL"]),
    )
    db.add(p)
    db.commit()


# --- PDF EXPORT TESTS ---


def test_export_all_jobs_pdf(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.pdf?status=all")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "content-disposition" in response.headers
    assert "personal-job-finder-all-jobs" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_applied_jobs_pdf(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.pdf?status=applied")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "personal-job-finder-applied-jobs" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_non_applied_jobs_pdf(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.pdf?status=non_applied")
    assert response.status_code == 200
    assert "personal-job-finder-non_applied-jobs" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_saved_jobs_pdf(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.pdf?status=saved")
    assert response.status_code == 200
    assert "personal-job-finder-saved-jobs" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_interview_jobs_pdf(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.pdf?status=interview")
    assert response.status_code == 200
    assert "personal-job-finder-interview-jobs" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_empty_pdf_report(db):
    # Database is empty, testing filters that yield zero matches
    response = client.get("/api/reports/jobs.pdf?status=applied")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_profile_available_and_missing(db):
    populate_test_jobs(db)
    # 1. Profile missing check
    response_no_prof = client.get("/api/reports/jobs.pdf?status=all")
    assert response_no_prof.status_code == 200
    assert response_no_prof.content.startswith(b"%PDF")

    # 2. Profile available check
    populate_profile(db)
    response_with_prof = client.get("/api/reports/jobs.pdf?status=all")
    assert response_with_prof.status_code == 200
    assert response_with_prof.content.startswith(b"%PDF")


def test_large_job_list_pdf_summary_trigger(db):
    # Populating 6 jobs to trigger summary section and pagebreak (> 5 limit)
    for i in range(7):
        db.add(
            Job(
                title=f"Job Title {i}",
                company_name="TechCorp",
                location="Delhi",
                remote_status="remote",
                source="Ashby",
                posted_date=datetime(2026, 7, 20),
                application_status="saved",
                match_score=85,
            )
        )
    db.commit()
    response = client.get("/api/reports/jobs.pdf?status=all")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_pdf_filter_export_duplicates(db):
    populate_test_jobs(db)
    # 1. Exclude duplicates (default)
    res_ex = client.get("/api/reports/jobs.pdf?include_duplicates=false")
    assert res_ex.status_code == 200
    assert res_ex.content.startswith(b"%PDF")

    # 2. Include duplicates
    res_in = client.get("/api/reports/jobs.pdf?include_duplicates=true")
    assert res_in.status_code == 200
    assert res_in.content.startswith(b"%PDF")


def test_pdf_current_filter_params(db):
    populate_test_jobs(db)
    # Check that query parameters filters apply successfully
    res = client.get("/api/reports/jobs.pdf?search=Python&remote_status=remote&minimum_match_score=50")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


def test_one_job_pdf_export_success_and_404(db):
    populate_test_jobs(db)
    # Success ID 1
    res = client.get("/api/reports/jobs/1.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "job-details-1" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")

    # Failure 404 ID 999
    res_fail = client.get("/api/reports/jobs/999.pdf")
    assert res_fail.status_code == 404
    assert "not found" in res_fail.json()["detail"].lower()


def test_application_summary_report(db):
    populate_test_jobs(db)
    res = client.get("/api/reports/application-summary.pdf")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


# --- CSV EXPORT TESTS ---


def test_csv_headers_and_content(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.csv?status=all")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "personal-job-finder-all-jobs" in response.headers["content-disposition"]

    # Read response content and verify Excel BOM is prepended
    raw_content = response.content
    assert raw_content.startswith(b"\xef\xbb\xbf")

    # Decode BOM-aware content
    csv_text = raw_content.decode("utf-8-sig")
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)

    # Verify CSV Headers
    headers = rows[0]
    assert headers[0] == "id"
    assert headers[2] == "job_title"
    assert headers[3] == "company_name"
    assert headers[13] == "matched_skills"
    assert headers[15] == "notes"

    # Verify Content Rows (duplicates filtered out by default, so 3 jobs)
    assert len(rows) == 4  # header + 3 data rows

    # Verify matched skills format (should be pipe-separated)
    python_job_row = next(r for r in rows if "Python Software Developer" in r[2])
    assert python_job_row[13] == "Python | FastAPI"  # formatted list
    assert python_job_row[14] == "Docker"  # missing skills

    # Verify quote escaping for notes containing commas
    # The csv reader handles quotes natively; we check that commas didn't split the notes into multiple columns
    assert "Notes with commas, quotes, and HTML tag <p>details</p>" in python_job_row[15]


def test_csv_filtered_jobs(db):
    populate_test_jobs(db)
    # Search for non-existing keyword
    response = client.get("/api/reports/jobs.csv?search=nonexistent")
    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)
    # Headers should still return when empty
    assert len(rows) == 1
    assert rows[0][0] == "id"


def test_csv_applied_only(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.csv?status=applied")
    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)
    assert len(rows) == 2  # header + 1 applied job row
    assert "Python Software Developer" in rows[1][2]


def test_csv_non_applied_only(db):
    populate_test_jobs(db)
    response = client.get("/api/reports/jobs.csv?status=non_applied")
    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)
    # Saved (Ledger) and Not Applied (Apex) -> 2 jobs
    assert len(rows) == 3  # header + 2 rows


def test_csv_formula_injection_protection(db):
    j = Job(
        title="=SUM(A1:A5)",
        company_name="+Addison",
        location="-Paris",
        remote_status="@Home",
        employment_type="full-time",
        source="Ashby",
        posted_date=datetime(2026, 7, 20),
        application_status="saved",
    )
    db.add(j)
    db.commit()

    response = client.get("/api/reports/jobs.csv?status=all")
    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)

    assert len(rows) == 2
    data_row = rows[1]
    assert data_row[2] == "'=SUM(A1:A5)"
    assert data_row[3] == "'+Addison"
    assert data_row[4] == "'-Paris"
    assert data_row[5] == "'@Home"
