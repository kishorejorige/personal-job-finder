import re
from typing import Dict, Any, List, Set
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse

STOP_WORDS = {"and", "or", "in", "of", "to", "for", "the", "a", "an", "at", "with", "senior", "junior", "lead", "staff", "principal"}

def calculate_match(job_title: str, job_description: str, job_skills: List[str], job_remote: str, job_location: str, profile: Profile) -> Dict[str, Any]:
    if not profile:
        return {
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": job_skills,
            "explanation": "No active profile found. Please upload your resume to enable matching."
        }

    # Deserializing profile lists from model
    profile_skills = []
    if profile.skills:
        try:
            profile_skills = json_parse_list(profile.skills)
        except Exception:
            profile_skills = []

    profile_experience = []
    if profile.work_experience:
        try:
            profile_experience = json_parse_list(profile.work_experience)
        except Exception:
            profile_experience = []

    profile_projects = []
    if profile.projects:
        try:
            profile_projects = json_parse_list(profile.projects)
        except Exception:
            profile_projects = []

    profile_certs = []
    if profile.certifications:
        try:
            profile_certs = json_parse_list(profile.certifications)
        except Exception:
            profile_certs = []

    # 1. Skill Match Score (Max 60 points)
    skill_score = 0.0
    matched_skills = []
    missing_skills = list(job_skills)

    profile_skills_lower = {s.lower() for s in profile_skills}
    job_skills_lower = {s.lower() for s in job_skills}

    if job_skills:
        for s in job_skills:
            if s.lower() in profile_skills_lower:
                matched_skills.append(s)
                if s in missing_skills:
                    missing_skills.remove(s)
        
        # Calculation: percentage of matched skills out of required skills
        skill_score = (len(matched_skills) / len(job_skills)) * 60
    else:
        # Fallback: check how many of profile's skills appear in the job description
        desc_lower = job_description.lower()
        found_profile_skills = 0
        for s in profile_skills:
            pattern = r'\b' + re.escape(s.lower()) + r'\b'
            if re.search(pattern, desc_lower):
                found_profile_skills += 1
                matched_skills.append(s)

        if profile_skills:
            # 3 matched skills gives full 60 points
            skill_score = min(found_profile_skills / 3.0, 1.0) * 60
        else:
            skill_score = 0.0

    # 2. Title Match Score (Max 20 points)
    title_score = 0.0
    profile_title = (profile.professional_title or "").lower().strip()
    job_title_lower = job_title.lower().strip()

    if profile_title and job_title_lower:
        if profile_title == job_title_lower:
            title_score = 20.0
        else:
            # Check for keyword overlap
            profile_words = set(re.findall(r'\w+', profile_title)) - STOP_WORDS
            job_words = set(re.findall(r'\w+', job_title_lower)) - STOP_WORDS
            overlap = profile_words.intersection(job_words)
            if overlap:
                # If there's partial word overlap (e.g. both have "Engineer" or "Developer")
                title_score = 15.0
            else:
                title_score = 0.0

    # 3. Experience and Project Match (Max 15 points)
    exp_score = 0.0
    # Consolidate all profile texts
    profile_text = f"{profile.professional_summary or ''} {' '.join(profile_experience)} {' '.join(profile_projects)} {' '.join(profile_certs)}".lower()
    
    # Check if job title keywords or required skills show up in experience/projects
    job_title_words = set(re.findall(r'\w+', job_title_lower)) - STOP_WORDS
    check_words = job_title_words.union(job_skills_lower)
    
    matches_found = 0
    for word in check_words:
        if word in profile_text:
            matches_found += 1
            
    # Each match yields 3 points, capped at 15
    exp_score = min(matches_found * 3, 15)

    # 4. Location / Remote Preference Match (Max 5 points)
    location_score = 0.0
    profile_loc = (profile.location or "").lower()
    
    if job_remote == "remote":
        location_score = 5.0
    elif profile_loc and job_location:
        # Check if profile location is mentioned in job location (e.g. Hyderabad in Hyderabad, India)
        # Split by comma or spaces
        loc_keywords = [w.strip() for w in re.split(r'[\s,]+', profile_loc) if w.strip()]
        for kw in loc_keywords:
            if kw and kw in job_location.lower():
                location_score = 5.0
                break

    # Sum scores
    total_score = int(round(skill_score + title_score + exp_score + location_score))
    total_score = min(max(total_score, 0), 100)

    return {
        "match_score": total_score,
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),
        "explanation": f"Skills: {int(round(skill_score))}/60, Title: {int(round(title_score))}/20, Experience: {int(round(exp_score))}/15, Location: {int(round(location_score))}/5"
    }

def json_parse_list(val: str) -> List[str]:
    import json
    if not val or not val.strip():
        return []
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return parsed
        return [val]
    except Exception:
        return [val]
