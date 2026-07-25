import re
from typing import Dict, Any, List

# Vocabulary dictionaries for Skill recognition
IT_SKILLS = {
    "python", "java", "javascript", "typescript", "angular", "react", "fastapi", "django", "sql", "postgresql",
    "docker", "aws", "azure", "linux", "git", "machine learning", "ai", "rag", "rest api", "c++", "c#",
    "html", "css", "kubernetes", "flask", "springboot", "spring", "golang", "devops", "ci/cd", "mongodb", "redis",
    "php", "node.js", "nodejs", "graphql", "bootstrap", "tailwind"
}

ADMIN_SKILLS = {"data entry", "ms office", "microsoft excel", "microsoft word", "documentation", "office administration", "record keeping", "scheduling", "billing", "inventory management"}
SALES_SKILLS = {"sales", "lead generation", "customer relationship management", "negotiation", "marketing", "digital marketing", "retail sales", "field sales", "business development", "customer acquisition"}
FINANCE_SKILLS = {"accounting", "bookkeeping", "tally", "gst", "taxation", "payroll", "invoicing", "accounts payable", "accounts receivable", "financial reporting"}
SERVICE_SKILLS = {"customer support", "call handling", "email support", "complaint resolution", "crm", "communication", "problem solving"}
EDUCATION_SKILLS = {"teaching", "lesson planning", "classroom management", "student assessment", "training", "curriculum development"}
HEALTH_SKILLS = {"patient care", "nursing", "medical records", "first aid", "clinical support", "pharmacy", "healthcare administration"}
TRADE_SKILLS = {"electrical wiring", "electronics", "equipment maintenance", "machine operation", "repair", "troubleshooting", "installation", "preventive maintenance", "quality inspection", "safety procedures"}
LOGISTICS_SKILLS = {"warehouse operations", "dispatch", "delivery", "driving", "route planning", "stock management", "packing", "supply chain", "procurement"}
HOSPITALITY_SKILLS = {"food service", "housekeeping", "front office", "guest relations", "hotel operations", "cooking", "kitchen support"}

SOFT_SKILLS = {
    "communication", "teamwork", "leadership", "time management", "problem solving",
    "adaptability", "attention to detail", "organisation", "organization", "customer service"
}

LANGUAGES_LIST = ["English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam", "Marathi", "Urdu", "Spanish", "French", "German"]

CORRECT_CASINGS = {
    "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
    "angular": "Angular", "react": "React", "fastapi": "FastAPI", "django": "Django",
    "sql": "SQL", "postgresql": "PostgreSQL", "docker": "Docker", "aws": "AWS",
    "azure": "Azure", "linux": "Linux", "git": "Git", "machine learning": "Machine Learning",
    "ai": "AI", "rag": "RAG", "rest api": "REST API", "c++": "C++", "c#": "C#",
    "html": "HTML", "css": "CSS", "kubernetes": "Kubernetes", "flask": "Flask",
    "springboot": "Spring Boot", "spring": "Spring", "golang": "Golang", "devops": "DevOps",
    "ci/cd": "CI/CD", "mongodb": "MongoDB", "redis": "Redis", "php": "PHP",
    "node.js": "Node.js", "nodejs": "Node.js", "graphql": "GraphQL", "bootstrap": "Bootstrap",
    "tailwind": "Tailwind", "ms office": "MS Office", "crm": "CRM", "gst": "GST",
    "pdf": "PDF", "tally": "Tally", "tally prime": "Tally Prime"
}

def extract_profile_from_text(text: str) -> Dict[str, Any]:
    profile = {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "professional_title": "",
        "career_objective": "",
        "professional_summary": "",
        "total_experience": "",
        "current_company": "",
        "current_role": "",
        "preferred_job_role": "",
        "preferred_location": "",
        "availability": "",
        "occupation_category": "Unknown",
        "skills": [],
        "technical_skills": [],
        "soft_skills": [],
        "languages": [],
        "work_experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
        "training": [],
        "internships": [],
        "licences": [],
        "tools_and_equipment": [],
        "additional_information": "",
        "resume_quality": "minimal"
    }

    if not text:
        return profile

    # Basic normalization of line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.splitlines()
    non_empty_lines = [l.strip() for l in lines if l.strip()]

    # Layer 1: Contact Extraction
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,12}'

    email_match = re.search(email_pattern, text)
    if email_match:
        profile["email"] = email_match.group(0).strip()

    phone_match = re.search(phone_pattern, text)
    if phone_match:
        profile["phone"] = phone_match.group(0).strip()

    # Layer 2: Headings Detection & Aliases Mapping
    headings_map = {
        "SUMMARY": ["SUMMARY", "PROFESSIONAL SUMMARY", "PROFILE", "ABOUT ME"],
        "OBJECTIVE": ["CAREER OBJECTIVE", "OBJECTIVE"],
        "SKILLS": ["SKILLS", "KEY SKILLS", "EXPERTISE", "TECHNOLOGIES", "CORE COMPETENCIES"],
        "TECHNICAL_SKILLS": ["TECHNICAL SKILLS", "HARD SKILLS"],
        "SOFT_SKILLS": ["SOFT SKILLS", "INTERPERSONAL SKILLS"],
        "EXPERIENCE": ["EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT", "WORK HISTORY", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE", "CAREER HISTORY"],
        "EDUCATION": ["EDUCATION", "ACADEMIC BACKGROUND", "ACADEMIC DETAILS", "ACADEMICS", "QUALIFICATIONS", "STUDIES", "ACADEMIC QUALIFICATIONS"],
        "PROJECTS": ["PROJECTS", "KEY PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"],
        "CERTIFICATIONS": ["CERTIFICATIONS", "CREDENTIALS"],
        "TRAINING": ["TRAINING", "COURSES", "VOCATIONAL TRAINING"],
        "INTERNSHIPS": ["INTERNSHIPS", "APPRENTICESHIPS"],
        "LICENCES": ["LICENCES", "LICENSES"],
        "TOOLS_AND_EQUIPMENT": ["TOOLS", "EQUIPMENT", "TOOLS AND EQUIPMENT"],
        "ACHIEVEMENTS": ["ACHIEVEMENTS", "AWARDS", "HONORS"]
    }

    # Helper maps for general extraction
    sections_content = {k: [] for k in headings_map}
    unrecognized_sections = {}

    current_section = None
    unclassified_lines = []

    # Map the lines into sections
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        upper_trimmed = trimmed.upper().rstrip(":").strip("•-*· ")
        is_heading = False

        # Look for recognized headings
        for section_key, keywords in headings_map.items():
            if upper_trimmed in keywords and len(trimmed) < 40:
                current_section = section_key
                is_heading = True
                break

        if is_heading:
            continue

        # Look for unrecognized headers (e.g. bold/uppercase line, short length)
        # To avoid treating bulleted list text as headings, ensure it doesn't start with bullets
        if len(trimmed) < 40 and trimmed.isupper() and not trimmed.startswith(("-", "*", "•", "·", "–")):
            # It's an unknown heading!
            current_section = trimmed.title()
            unrecognized_sections[current_section] = []
            continue

        if current_section:
            if current_section in sections_content:
                sections_content[current_section].append(trimmed)
            else:
                unrecognized_sections[current_section].append(trimmed)
        else:
            unclassified_lines.append(trimmed)

    # Process basic fields from first 5 lines (name and title)
    name_candidate = ""
    title_candidate = ""
    for line in non_empty_lines[:5]:
        if "@" in line or any(k in line.lower() for k in ["http", "www", "github", "linkedin", "phone", "email"]):
            continue
        if len(re.findall(r'\d', line)) >= 4:
            continue
        words = line.split()
        if not name_candidate and 1 <= len(words) <= 4:
            name_candidate = line
            continue
        if name_candidate and not title_candidate and len(line) < 40:
            if re.search(r'[A-Za-z\s]{2,},\s*[A-Za-z]{2,}', line):
                continue
            title_candidate = line

    profile["full_name"] = name_candidate
    profile["professional_title"] = title_candidate

    # Process Section Contents
    profile["professional_summary"] = "\n".join(sections_content["SUMMARY"]).strip()
    profile["career_objective"] = "\n".join(sections_content["OBJECTIVE"]).strip()

    # Generic bulleted cleaner
    def clean_section_list(raw_lines: List[str]) -> List[str]:
        items = []
        current_item = []
        for line in raw_lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            if line_clean.startswith(("-", "*", "•", "·", "–")):
                if current_item:
                    items.append(" ".join(current_item))
                current_item = [line_clean.lstrip("-*•· –").strip()]
            else:
                if not current_item:
                    current_item.append(line_clean)
                else:
                    current_item.append(line_clean)

        if current_item:
            items.append(" ".join(current_item))

        if not items and raw_lines:
            return [l.strip() for l in raw_lines if l.strip()]
        return items

    profile["work_experience"] = clean_section_list(sections_content["EXPERIENCE"])
    profile["education"] = clean_section_list(sections_content["EDUCATION"])
    profile["projects"] = clean_section_list(sections_content["PROJECTS"])
    profile["certifications"] = clean_section_list(sections_content["CERTIFICATIONS"])
    profile["achievements"] = clean_section_list(sections_content["ACHIEVEMENTS"])
    profile["training"] = clean_section_list(sections_content["TRAINING"])
    profile["internships"] = clean_section_list(sections_content["INTERNSHIPS"])
    profile["licences"] = clean_section_list(sections_content["LICENCES"])
    profile["tools_and_equipment"] = clean_section_list(sections_content["TOOLS_AND_EQUIPMENT"])

    # Location heuristic from first 10 lines
    location_pattern = r'([A-Za-z\s]{2,},\s*[A-Za-z\s]{2,})'
    tech_keywords = {"python", "fastapi", "developer", "engineer", "skills", "docker", "sql", "java", "c++", "c#", "react", "angular"}
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

    # Layer 3: Skill Recognition (IT, Trade/Non-IT, Soft Skills)
    explicit_skills = []
    for sec_name in ["SKILLS", "TECHNICAL_SKILLS", "SOFT_SKILLS", "TOOLS_AND_EQUIPMENT"]:
        for line in sections_content[sec_name]:
            for p in re.split(r'[,;]', line):
                p_clean = p.strip().strip("•-*· ")
                if p_clean:
                    explicit_skills.append(p_clean)

    scanned_skills = []
    text_lower = text.lower()
    all_vocab = IT_SKILLS | ADMIN_SKILLS | SALES_SKILLS | FINANCE_SKILLS | SERVICE_SKILLS | EDUCATION_SKILLS | HEALTH_SKILLS | TRADE_SKILLS | LOGISTICS_SKILLS | HOSPITALITY_SKILLS | SOFT_SKILLS

    for s in all_vocab:
        if s in ["ai", "rag", "git", "sql", "crm", "gst"]:
            pattern = r'\b' + re.escape(s) + r'\b'
        else:
            pattern = re.escape(s)
        if re.search(pattern, text_lower):
            scanned_skills.append(s)

    unique_tech = []
    unique_soft = []
    seen = set()

    for s in explicit_skills + scanned_skills:
        s_lower = s.lower()
        if s_lower in seen:
            continue
        seen.add(s_lower)

        # Map correct predefined casings
        if s_lower in CORRECT_CASINGS:
            s_clean = CORRECT_CASINGS[s_lower]
        else:
            words = s.split()
            s_clean = " ".join(w.capitalize() if w.lower() not in ["ms", "crm", "gst", "pdf"] else w.upper() for w in words)

        # Categorize
        if s_lower in SOFT_SKILLS:
            unique_soft.append(s_clean)
        else:
            unique_tech.append(s_clean)

    profile["technical_skills"] = unique_tech
    profile["soft_skills"] = unique_soft
    profile["skills"] = unique_tech + unique_soft

    # Languages Check
    detected_langs = []
    for lang in LANGUAGES_LIST:
        if re.search(r'\b' + re.escape(lang.lower()) + r'\b', text_lower):
            detected_langs.append(lang)
    profile["languages"] = list(set(detected_langs))

    # Experience Heuristics: total years, current company, current role
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience', text, re.IGNORECASE)
    if exp_match:
        profile["total_experience"] = f"{exp_match.group(1)} years"
    elif profile["work_experience"]:
        # Estimate based on length
        cnt = len(profile["work_experience"])
        profile["total_experience"] = f"{cnt} years" if cnt > 0 else ""

    if profile["work_experience"]:
        first_exp = profile["work_experience"][0]
        # Heuristic role & company split
        role = first_exp
        company = ""
        for sep in [" at ", " @ ", " - ", " – ", ", "]:
            if sep in first_exp:
                parts = first_exp.split(sep, 1)
                role = parts[0].strip()
                company = parts[1].strip()
                break
        profile["current_company"] = re.sub(r'\(.*?\)', '', company).strip()
        profile["current_role"] = re.sub(r'\(.*?\)', '', role).strip()

    # Preferred locations/roles heuristics
    if profile["professional_title"]:
        profile["preferred_job_role"] = profile["professional_title"]
    if profile["location"]:
        profile["preferred_location"] = profile["location"]

    # Occupation Category Detection
    profile_text_to_cat = f"{profile['professional_title']} {profile['career_objective']} {profile['professional_summary']} {' '.join(profile['skills'])} {' '.join(profile['work_experience'])}".lower()

    categories_keywords = {
        "IT and Software": ["developer", "programmer", "software", "python", "java", "javascript", "react", "angular", "fullstack", "backend", "frontend", "devops", "cloud", "aws", "azure", "database", "fastapi", "django"],
        "Engineering": ["mechanical engineer", "civil engineer", "chemical engineer", "cad designer", "solidworks", "structural engineer", "engineering"],
        "Electronics and Electrical": ["electrician", "electrical wiring", "electronics", "circuit", "soldering", "hardware technician", "embedded"],
        "Accounting and Finance": ["accountant", "accounting", "bookkeeping", "gst", "tally", "taxation", "finance", "audit", "accounts payable", "accounts receivable", "invoice", "payroll"],
        "Sales and Marketing": ["sales", "marketing", "business development", "lead generation", "digital marketing", "seo", "sales executive", "customer acquisition"],
        "Administration": ["administrator", "office admin", "data entry", "secretary", "clerk", "billing", "scheduling", "record keeping", "documentation"],
        "Customer Service": ["customer support", "call handling", "customer service", "support executive", "helpdesk", "help desk", "call center"],
        "Education": ["teacher", "teaching", "professor", "tutor", "lesson planning", "student assessment", "curriculum development", "classroom management", "school", "college", "academic"],
        "Healthcare": ["nurse", "nursing", "patient care", "medical", "healthcare", "clinic", "pharmacy", "pharmacist", "doctor", "clinical", "hospital"],
        "Logistics and Operations": ["warehouse", "dispatch", "delivery", "driver", "driving", "route planning", "logistics", "supply chain", "procurement", "stock management"],
        "Hospitality": ["hotel", "cooking", "guest relations", "housekeeping", "front office", "food service", "chef", "kitchen support", "restaurant"],
        "Skilled Trades": ["mechanic", "technician", "welder", "plumber", "carpenter", "HVAC", "repair", "maintenance technician"],
        "Human Resources": ["recruiter", "recruitment", "human resources", "hr professional", "talent acquisition", "onboarding"],
        "Fresher or Student": ["student", "fresher", "intern", "internship", "entry-level", "graduate", "college student"]
    }

    scores = {cat: 0 for cat in categories_keywords}
    for cat, keywords in categories_keywords.items():
        for kw in keywords:
            if kw in profile_text_to_cat:
                scores[cat] += 2 if kw in (profile["professional_title"] or "").lower() else 1

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        profile["occupation_category"] = best_cat
    else:
        profile["occupation_category"] = "Unknown"

    # Layer 4 & 5: Unknown section fallback and preservation of unclassified text
    additional_info_parts = []

    # Prepend unclassified header lines that aren't the name/title/contacts
    header_unclassified = []
    for line in unclassified_lines:
        if line != name_candidate and line != title_candidate and line != profile["email"] and line != profile["phone"] and line != profile["location"]:
            header_unclassified.append(line)

    if header_unclassified:
        additional_info_parts.append("\n".join(header_unclassified))

    # Add unrecognized sections
    for sec_name, sec_lines in unrecognized_sections.items():
        if sec_lines:
            additional_info_parts.append(f"[{sec_name}]\n" + "\n".join(sec_lines))

    profile["additional_information"] = "\n\n".join(additional_info_parts).strip()

    # Calculate Resume Quality Indicator
    has_name = bool(profile["full_name"])
    has_contact = bool(profile["email"] or profile["phone"])
    has_title = bool(profile["professional_title"])
    has_skills = bool(profile["skills"])
    has_experience = bool(profile["work_experience"])
    has_education = bool(profile["education"])

    if has_name and has_contact and has_title and has_skills and has_experience and has_education:
        profile["resume_quality"] = "complete"
    elif has_name and has_contact and (has_skills or has_experience or has_education):
        profile["resume_quality"] = "partial"
    else:
        profile["resume_quality"] = "minimal"

    return profile
