import re
from typing import Dict, Any, List

def extract_profile_from_text(text: str) -> Dict[str, Any]:
    profile = {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "professional_title": "",
        "professional_summary": "",
        "skills": [],
        "work_experience": [],
        "education": [],
        "projects": [],
        "certifications": []
    }

    if not text:
        return profile

    # Basic normalization of line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Heuristic Regex for email and phone numbers
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    # Captures standard forms: (123) 456-7890, 123-456-7890, +1 1234567890, +91 9876543210
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,12}'

    # Email extraction
    email_match = re.search(email_pattern, text)
    if email_match:
        profile["email"] = email_match.group(0).strip()

    # Phone extraction
    phone_match = re.search(phone_pattern, text)
    if phone_match:
        profile["phone"] = phone_match.group(0).strip()

    # Define headings map with aliases for matching
    headings_map = {
        "SUMMARY": ["SUMMARY", "PROFILE", "OBJECTIVE", "PROFESSIONAL SUMMARY", "ABOUT ME", "CAREER OBJECTIVE"],
        "SKILLS": ["SKILLS", "TECHNICAL SKILLS", "KEY SKILLS", "EXPERTISE", "TECHNOLOGIES", "CORE COMPETENCIES"],
        "EXPERIENCE": ["EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT", "WORK HISTORY", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE"],
        "EDUCATION": ["EDUCATION", "ACADEMIC BACKGROUND", "ACADEMICS", "QUALIFICATIONS", "STUDIES"],
        "PROJECTS": ["PROJECTS", "KEY PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"],
        "CERTIFICATIONS": ["CERTIFICATIONS", "AWARDS", "LICENSES", "CREDENTIALS", "COURSES"]
    }

    lines = text.splitlines()
    non_empty_lines = [l.strip() for l in lines if l.strip()]

    # Extract Full Name and Title from the first 5 non-empty lines
    name_candidate = ""
    title_candidate = ""

    for line in non_empty_lines[:5]:
        # Skip contact details, links, or lines with too many numbers
        if "@" in line or any(k in line.lower() for k in ["http", "www", "github", "linkedin", "phone", "email"]):
            continue
        if len(re.findall(r'\d', line)) >= 4:
            continue
        words = line.split()
        if not name_candidate and 1 <= len(words) <= 4:
            name_candidate = line
            continue
        if name_candidate and not title_candidate and len(line) < 40:
            # Skip if it looks like a location to avoid misclassifying it as a title
            if re.search(r'[A-Za-z\s]{2,},\s*[A-Za-z]{2,}', line):
                continue
            title_candidate = line

    profile["full_name"] = name_candidate
    profile["professional_title"] = title_candidate

    # Section Splitting Heuristic
    current_section = None
    sections_content = {
        "SUMMARY": [],
        "SKILLS": [],
        "EXPERIENCE": [],
        "EDUCATION": [],
        "PROJECTS": [],
        "CERTIFICATIONS": []
    }

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        # Check if line matches a known heading (case-insensitive check)
        upper_trimmed = trimmed.upper().rstrip(":").strip()
        is_heading = False
        for section_key, keywords in headings_map.items():
            if upper_trimmed in keywords and len(trimmed) < 35:
                current_section = section_key
                is_heading = True
                break

        if is_heading:
            continue

        if current_section:
            sections_content[current_section].append(trimmed)

    # Process extracted content
    profile["professional_summary"] = "\n".join(sections_content["SUMMARY"]).strip()

    # Skills: split on comma, bullet-points or newlines
    skills_raw = sections_content["SKILLS"]
    skills_list = []
    for s in skills_raw:
        if "," in s:
            parts = s.split(",")
            for p in parts:
                p_clean = p.strip().strip("•-*· ")
                if p_clean:
                    skills_list.append(p_clean)
        else:
            s_clean = s.strip("•-*· ")
            if s_clean:
                skills_list.append(s_clean)
    profile["skills"] = skills_list

    # Generic cleaner to convert section lines into list of entries
    def clean_section_list(raw_lines: List[str]) -> List[str]:
        items = []
        current_item = []
        for line in raw_lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            # Detect bullets as new items
            if line_clean.startswith(("-", "*", "•", "·", "–")):
                if current_item:
                    items.append(" ".join(current_item))
                current_item = [line_clean.lstrip("-*•· –").strip()]
            else:
                if not current_item:
                    current_item.append(line_clean)
                else:
                    # Append line to active item
                    current_item.append(line_clean)

        if current_item:
            items.append(" ".join(current_item))

        if not items and raw_lines:
            # Fallback: just return non-empty lines
            return [l.strip() for l in raw_lines if l.strip()]
        return items

    profile["work_experience"] = clean_section_list(sections_content["EXPERIENCE"])
    profile["education"] = clean_section_list(sections_content["EDUCATION"])
    profile["projects"] = clean_section_list(sections_content["PROJECTS"])
    profile["certifications"] = clean_section_list(sections_content["CERTIFICATIONS"])

    # Location heuristic (looks for "City, State" or "City, Country") in first 10 lines
    location_pattern = r'([A-Za-z\s]{2,},\s*[A-Za-z\s]{2,})'
    tech_keywords = {"python", "fastapi", "developer", "engineer", "skills", "docker", "sql", "java", "c++", "c#", "react", "angular", "manager", "architect"}
    for line in non_empty_lines[:10]:
        if "@" in line or "http" in line:
            continue
        if any(tk in line.lower() for tk in tech_keywords):
            continue
        match = re.search(location_pattern, line)
        if match:
            loc = match.group(0).strip()
            if loc != name_candidate and loc != title_candidate:
                profile["location"] = loc
                break

    return profile
