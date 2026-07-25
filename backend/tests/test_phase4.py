import os
import json
import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.job import Job
from app.models.profile import Profile
from app.models.provider_run import ProviderRun
from app.providers import (
    JobProvider,
    LeverProvider,
    AshbyProvider,
    RemoteOkProvider,
    YCombinatorProvider,
    HackerNewsProvider,
    HasjobProvider,
    CompanyCareersProvider,
    ProviderFetchResult
)
from app.services.job_service import refresh_all_job_sources, generate_fingerprint, resolve_duplicates

# Use SQLite test DB
TEST_DATABASE_URL = "sqlite:///./test_phase4.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Programmatic schema check in case ALTER TABLE is needed for test DB
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(jobs)"))
        columns = [row[1] for row in result.fetchall()]
        if "job_fingerprint" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN job_fingerprint VARCHAR"))
        if "duplicate_of_id" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN duplicate_of_id INTEGER"))
        conn.commit()

    db = TestingSessionLocal()
    db.query(Job).delete()
    db.query(Profile).delete()
    db.query(ProviderRun).delete()
    db.commit()
    yield db
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_phase4.db"):
        try:
            os.remove("./test_phase4.db")
        except PermissionError:
            pass

# 1. Test Lever Provider
@pytest.mark.anyio
async def test_lever_provider(monkeypatch):
    sites = [
        {"company_name": "Test Global", "site_name": "test-global", "region": "global", "enabled": True},
        {"company_name": "Test EU", "site_name": "test-eu", "region": "eu", "enabled": True},
        {"company_name": "Test Invalid", "site_name": "test-invalid", "region": "global", "enabled": True}
    ]
    provider = LeverProvider(sites=sites)

    # Mock responses
    mock_global_data = [
        {
            "id": "lever_123",
            "title": "Software Engineer",
            "categories": {"location": "San Francisco", "commitment": "Full-time"},
            "description": "Awesome role.",
            "lists": [{"title": "Requirements", "content": "Python experience."}],
            "additional": "Apply now.",
            "createdAt": 1609459200000, # 2021-01-01
            "workplaceType": "hybrid",
            "hostedUrl": "https://jobs.lever.co/test-global/123",
            "salary": {"amount": 150000, "currency": "USD"}
        }
    ]
    mock_eu_data = [
        {
            "id": "lever_456",
            "title": "Data Scientist",
            "categories": {"location": "Amsterdam", "commitment": "Contract"},
            "description": "Data analysis.",
            "createdAt": 1609459200000,
            "workplaceType": "remote",
            "hostedUrl": "https://jobs.eu.lever.co/test-eu/456"
        }
    ]

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        if "test-global" in str(url):
            return httpx.Response(200, json=mock_global_data)
        elif "test-eu" in str(url):
            return httpx.Response(200, json=mock_eu_data)
        else:
            return httpx.Response(404, text="Not Found")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    assert result.sources_checked == 3
    assert result.sources_succeeded == 2
    assert result.sources_failed == 1
    assert len(result.jobs) == 2

    # Check first job normalization
    job1 = result.jobs[0]
    assert job1["external_id"] == "lever_123"
    assert job1["title"] == "Software Engineer"
    assert job1["location"] == "San Francisco"
    assert job1["remote_status"] == "hybrid"
    assert job1["employment_type"] == "Full-time"
    assert job1["salary"] == "USD 150000"
    assert "Python experience" in job1["description"]
    assert "2021-01-01" in job1["posted_date"]

    # Check second job normalization
    job2 = result.jobs[1]
    assert job2["external_id"] == "lever_456"
    assert job2["location"] == "Amsterdam"
    assert job2["remote_status"] == "remote"

    # Check invalid site isolation error logging
    assert len(result.errors) == 1
    assert "test-invalid" in result.errors[0]["site"]

# 2. Test Ashby Provider
@pytest.mark.anyio
async def test_ashby_provider(monkeypatch):
    boards = [
        {"company_name": "Ashby Corp", "job_board_name": "ashby-corp", "enabled": True},
        {"company_name": "Invalid Board", "job_board_name": "invalid-board", "enabled": True}
    ]
    provider = AshbyProvider(boards=boards)

    mock_ashby_data = {
        "jobs": [
            {
                "id": "ashby_999",
                "title": "Backend Dev",
                "location": "Berlin",
                "isRemote": True,
                "employmentType": "Full-time",
                "compensation": {"compensationTierSummary": "EUR 80,000 - 100,000"},
                "descriptionHtml": "<p>Build things.</p>",
                "jobUrl": "https://jobs.ashbyhq.com/ashby-corp/999"
            }
        ]
    }

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        if "ashby-corp" in str(url):
            return httpx.Response(200, json=mock_ashby_data)
        else:
            return httpx.Response(404, text="Not Found")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    assert result.sources_checked == 2
    assert result.sources_succeeded == 1
    assert result.sources_failed == 1
    assert len(result.jobs) == 1

    job = result.jobs[0]
    assert job["external_id"] == "ashby_999"
    assert job["title"] == "Backend Dev"
    assert job["location"] == "Berlin"
    assert job["remote_status"] == "remote"
    assert job["salary"] == "EUR 80,000 - 100,000"
    assert "Build things" in job["description"]

# 3. Test Remote OK Provider
@pytest.mark.anyio
async def test_remote_ok_provider(monkeypatch):
    provider = RemoteOkProvider()

    # Remote OK feed starts with a metadata row (legal notice)
    mock_feed = [
        {"legal": "This feed is copyright Remote OK"},
        {
            "id": "rok_777",
            "position": "Frontend Architect",
            "company": "Rok Startup",
            "location": "Worldwide",
            "tags": ["React", "TypeScript"],
            "salary_min": 120000,
            "salary_max": 140000,
            "url": "https://remoteok.com/api/777",
            "description": "Build UI templates.",
            "date": "2023-10-01T12:00:00Z"
        }
    ]

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=mock_feed)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    assert result.sources_checked == 1
    assert result.sources_succeeded == 1
    assert len(result.jobs) == 1

    job = result.jobs[0]
    assert job["external_id"] == "rok_777"
    assert job["title"] == "Frontend Architect"
    assert job["company_name"] == "Rok Startup"
    assert job["remote_status"] == "remote" # Always remote
    assert job["salary"] == "$120000 - $140000"
    assert "React" in job["skills"]
    assert job["original_url"] == "https://remoteok.com/api/777"

# 4. Test Hacker News Provider
@pytest.mark.anyio
async def test_hacker_news_provider(monkeypatch):
    config = {
        "enabled": True,
        "max_pages": 1,
        "country": "India",
        "remote_only": False
    }
    provider = HackerNewsProvider(config=config)

    mock_algolia_data = {
        "hits": [
            {
                "objectID": "yc_111",
                "title": "DrDroid (YC W23) Is Hiring a Senior Python Engineer",
                "url": "https://www.ycombinator.com/companies/drdroid/jobs/111",
                "created_at": "2023-10-01T12:00:00Z",
                "job_text": "Based in Bangalore, India. Remote hybrid role. Python developers needed."
            },
            {
                "objectID": "yc_222",
                "title": "US Startup (YC S24) Is Hiring a Founding Engineer",
                "url": "https://www.ycombinator.com/companies/us-startup/jobs/222",
                "created_at": "2023-10-01T12:00:00Z",
                "job_text": "Based in San Francisco. Python developer."
            }
        ]
    }

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=mock_algolia_data)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    # Hit 1 matches India (Bangalore, India in text), Hit 2 is excluded (no India)
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job["external_id"] == "yc_111"
    assert "Senior Python Engineer" in job["title"]
    assert "DrDroid" in job["company_name"]
    assert "W23" in job["company_name"]
    assert job["source"] == "hacker_news"
    assert job["employment_type"] is None  # Verify employment_type remains null when absent

@pytest.mark.anyio
async def test_disabled_ycombinator_provider():
    provider = YCombinatorProvider()
    result = await provider.fetch_jobs()
    assert result.sources_checked == 1
    assert result.sources_succeeded == 0
    assert result.sources_failed == 0
    assert len(result.jobs) == 0
    assert len(result.errors) == 1
    assert "pending implementation" in result.errors[0]["message"]

# 5. Test Hasjob Provider
@pytest.mark.anyio
async def test_hasjob_provider(monkeypatch):
    provider = HasjobProvider(config={"enabled": True, "location": "Bangalore"})

    mock_rss_xml = '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>Hasjob Feed</title><link>https://hasjob.co</link><item><title>React Developer at HasGeek</title><link>https://hasjob.co/react-dev</link><description>Build Web UI interfaces.</description><pubDate>Sun, 01 Oct 2023 12:00:00 GMT</pubDate><guid>hasjob_888</guid><category>Bangalore</category></item></channel></rss>'

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, text=mock_rss_xml)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    assert result.sources_checked == 1
    assert result.sources_succeeded == 1
    assert len(result.jobs) == 1

    job = result.jobs[0]
    assert job["external_id"] == "hasjob_888"
    assert job["title"] == "React Developer"
    assert job["company_name"] == "HasGeek"
    assert job["location"] == "Bangalore"
    assert "Web UI" in job["description"]

# 6. Test Company Careers Adapters
@pytest.mark.anyio
async def test_company_careers_provider(monkeypatch):
    sites = [
        {
            "company_name": "JSON-LD Corp",
            "careers_url": "https://jsonld.example/careers",
            "adapter": "json_ld",
            "enabled": True
        },
        {
            "company_name": "Selector Corp",
            "careers_url": "https://selectors.example/careers",
            "adapter": "generic_html",
            "enabled": True,
            "selectors": {
                "job_item_selector": "div.job-card",
                "title_selector": "h3.title",
                "location_selector": "span.location",
                "url_selector": "a.apply-link"
            }
        }
    ]
    provider = CompanyCareersProvider(sites=sites)

    # HTML containing structured JSON-LD
    json_ld_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "JobPosting",
          "identifier": "jld_999",
          "title": "Cloud Architect",
          "hiringOrganization": {
            "@type": "Organization",
            "name": "JSON-LD Corp"
          },
          "jobLocation": {
            "@type": "Place",
            "address": {
              "@type": "PostalAddress",
              "addressLocality": "Seattle",
              "addressRegion": "WA"
            }
          },
          "jobLocationType": "TELECOMMUTE",
          "description": "Design cloud systems.",
          "url": "https://jsonld.example/jobs/999"
        }
        </script>
      </head>
      <body>Careers page</body>
    </html>
    """

    # HTML matching selectors
    generic_html = """
    <html>
      <body>
        <div class="job-card">
          <h3 class="title">HTML Designer</h3>
          <span class="location">Remote</span>
          <a class="apply-link" href="/apply/555">Apply Now</a>
        </div>
      </body>
    </html>
    """

    import httpx
    async def mock_get(self, url, *args, **kwargs):
        if "jsonld" in str(url):
            return httpx.Response(200, text=json_ld_html)
        else:
            return httpx.Response(200, text=generic_html)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await provider.fetch_jobs()
    assert result.sources_checked == 2
    assert result.sources_succeeded == 2
    assert len(result.jobs) == 2

    # Check JSON-LD
    job1 = result.jobs[0]
    assert job1["external_id"] == "jld_999"
    assert job1["title"] == "Cloud Architect"
    assert job1["location"] == "Seattle, WA"
    assert job1["remote_status"] == "remote"

    # Check generic HTML selector
    job2 = result.jobs[1]
    assert job2["title"] == "HTML Designer"
    assert job2["location"] == "Remote"
    assert job2["remote_status"] == "remote"
    assert job2["original_url"] == "https://selectors.example/apply/555"

# 7. Test Unified Service integration (cooldown & duplicate resolution)
@pytest.mark.anyio
async def test_unified_service(setup_db, monkeypatch):
    db = setup_db

    # Create profile
    profile = Profile(
        full_name="Alice",
        professional_title="Python developer",
        skills=json.dumps(["Python", "FastAPI"])
    )
    db.add(profile)
    db.commit()

    # Mock all providers fetch_jobs method
    class MockGreenhouse(JobProvider):
        provider_name = "greenhouse"
        async def fetch_jobs(self):
            return ProviderFetchResult(
                source="greenhouse",
                jobs=[
                    {
                        "external_id": "gh_111",
                        "title": "Python Engineer",
                        "company_name": "Super Startup",
                        "location": "London",
                        "original_url": "https://boards.greenhouse.io/super/111",
                        "description": "FastAPI engineer",
                        "source": "greenhouse"
                    }
                ],
                sources_checked=1, sources_succeeded=1, sources_failed=0
            )

    class MockRemoteOk(JobProvider):
        provider_name = "remote_ok"
        async def fetch_jobs(self):
            return ProviderFetchResult(
                source="remote_ok",
                jobs=[
                    {
                        # Same job published on Remote OK!
                        "external_id": "rok_111",
                        "title": "Python Engineer",
                        "company_name": "Super Startup",
                        "location": "London",
                        "original_url": "https://remoteok.com/api/111",
                        "description": "FastAPI engineer",
                        "source": "remote_ok"
                    }
                ],
                sources_checked=1, sources_succeeded=1, sources_failed=0
            )

    import app.services.job_service
    def mock_create_provider(name):
        if name == "greenhouse":
            return MockGreenhouse()
        elif name == "remote_ok":
            return MockRemoteOk()
        else:
            # return dummy provider that returns empty jobs
            class DummyProvider(JobProvider):
                provider_name = name
                async def fetch_jobs(self):
                    return ProviderFetchResult(source=name, jobs=[], sources_checked=0, sources_succeeded=0, sources_failed=0)
            return DummyProvider()

    monkeypatch.setattr(app.services.job_service, "create_provider", mock_create_provider)

    # 1. Run sync (should create 2 jobs in DB, greenhouse + remote_ok)
    res = await refresh_all_job_sources(db, sources=["greenhouse", "remote_ok"], force=True)
    assert res["total_jobs_received"] == 2
    assert res["jobs_created"] == 2

    # Check duplicate linkage: Greenhouse is higher priority than Remote OK,
    # so greenhouse job should have duplicate_of_id = None, and remote_ok job duplicate_of_id = greenhouse.id
    gh_job = db.query(Job).filter(Job.source == "greenhouse").first()
    rok_job = db.query(Job).filter(Job.source == "remote_ok").first()
    assert gh_job is not None
    assert rok_job is not None
    assert gh_job.duplicate_of_id is None
    assert rok_job.duplicate_of_id == gh_job.id

    # 2. Recalculate matches check
    assert gh_job.match_score > 60

    # 3. Test Cooldown policy (should raise ValueError without force=True)
    with pytest.raises(ValueError) as exc:
        await refresh_all_job_sources(db, sources=["greenhouse"], force=False)
    assert "recently" in str(exc.value)

    # 4. Cooldown should bypass if force=True
    res_forced = await refresh_all_job_sources(db, sources=["greenhouse"], force=True)
    assert res_forced["total_jobs_received"] == 1
