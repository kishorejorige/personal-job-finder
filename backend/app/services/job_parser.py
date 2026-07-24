import re
import html
from typing import List

SKILLS_DICTIONARY = [
    "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript",
    "Angular", "React", "Node.js", "SQL", "SQLite", "PostgreSQL", "MySQL",
    "MongoDB", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git",
    "GitHub Actions", "REST API", "GraphQL", "Linux", "CI/CD",
    "Machine Learning", "AI", "LLM", "RAG", "LangChain", "LangGraph",
    "Pandas", "NumPy", "Pytest", "Redis", "Celery", "Microservices",
    "C++", "C#"
]

def clean_html(html_content: str) -> str:
    if not html_content:
        return ""

    # Strip script and style contents
    text = re.sub(r'<(script|style).*?>.*?</\1>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    text = re.sub(r'<.*?>', ' ', text)

    # Decode HTML entities (e.g. &nbsp; or &amp;)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')

    # Collapse repeated white spaces and tabs
    text = re.sub(r'[ \t]+', ' ', text)
    # Collapse multiple newlines
    text = re.sub(r'\n\s*\n', '\n', text)

    return text.strip()

def detect_remote_status(title: str, location: str, description: str) -> str:
    search_text = f"{title} {location} {description}".lower()

    if "hybrid" in search_text:
        return "hybrid"
    if "remote" in search_text or "work from home" in search_text or "wfh" in search_text:
        return "remote"
    if "on-site" in search_text or "onsite" in search_text or "office-only" in search_text or "in-office" in search_text:
        return "onsite"

    return "unknown"

def extract_skills_from_text(text: str) -> List[str]:
    if not text:
        return []

    detected_skills = set()
    for skill in SKILLS_DICTIONARY:
        # Safely compile a regex with boundaries depending on starting/ending characters
        escaped = re.escape(skill)
        start_boundary = r'\b' if re.match(r'^\w', skill) else ''
        end_boundary = r'\b' if re.match(r'\w$', skill) else ''
        pattern = f"{start_boundary}{escaped}{end_boundary}"

        if re.search(pattern, text, re.IGNORECASE):
            detected_skills.add(skill)

    return sorted(list(detected_skills))
