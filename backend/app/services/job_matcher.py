import re
from typing import Dict, Any, List, Set
from app.models.profile import Profile

STOP_WORDS = {"and", "or", "in", "of", "to", "for", "the", "a", "an", "at", "with", "senior", "junior", "lead", "staff", "principal"}

def calculate_match(job_title: str, job_description: str, job_skills: List[str], job_remote: str, job_location: str, profile: Profile) -> Dict[str, Any]:
    if not profile:
        return {
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": job_skills or [],
            "explanation": "No active profile found. Please upload your resume to enable matching."
        }

    # Helper function to parse lists safely from DB
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

    # Deserializing all profile lists
    profile_skills = json_parse_list(profile.skills)
    profile_tech_skills = json_parse_list(profile.technical_skills)
    profile_soft_skills = json_parse_list(profile.soft_skills)
    profile_experience = json_parse_list(profile.work_experience)
    profile_projects = json_parse_list(profile.projects)
    profile_certs = json_parse_list(profile.certifications)
    profile_training = json_parse_list(profile.training)
    profile_internships = json_parse_list(profile.internships)
    profile_licences = json_parse_list(profile.licences)
    profile_languages = json_parse_list(profile.languages)
    profile_tools = json_parse_list(profile.tools_and_equipment)

    # 1. Skill Match Score (Max 50 points)
    # Combine all profile skills (lowercased)
    all_profile_skills = set(profile_skills + profile_tech_skills + profile_soft_skills + profile_tools)
    profile_skills_lower = {s.lower() for s in all_profile_skills}

    skill_score = 0.0
    matched_skills = []
    missing_skills = list(job_skills or [])

    if job_skills:
        for s in job_skills:
            if s.lower() in profile_skills_lower:
                matched_skills.append(s)
                if s in missing_skills:
                    missing_skills.remove(s)
        # Ratio of matched skills out of required skills
        skill_score = (len(matched_skills) / len(job_skills)) * 50
    else:
        # Fallback: check how many of profile's skills appear in the job title or description
        desc_lower = (job_title + " " + job_description).lower()
        found_profile_skills = 0
        for s in all_profile_skills:
            pattern = r'\b' + re.escape(s.lower()) + r'\b'
            if re.search(pattern, desc_lower):
                found_profile_skills += 1
                matched_skills.append(s)

        if all_profile_skills:
            # 3 matched skills gives full 50 points
            skill_score = min(found_profile_skills / 3.0, 1.0) * 50
        else:
            skill_score = 0.0

    # 2. Title & Category Match Score (Max 25 points)
    title_score = 0.0
    profile_title = (profile.professional_title or "").lower().strip()
    preferred_role = (profile.preferred_job_role or "").lower().strip()
    occupation_cat = (profile.occupation_category or "").lower().strip()
    job_title_lower = job_title.lower().strip()

    title_matched = False
    if job_title_lower:
        # Direct matches
        if (profile_title and profile_title == job_title_lower) or (preferred_role and preferred_role == job_title_lower):
            title_score = 25.0
            title_matched = True
        else:
            # Overlap keywords in title or preferred role
            profile_words = set()
            if profile_title:
                profile_words.update(re.findall(r'\w+', profile_title))
            if preferred_role:
                profile_words.update(re.findall(r'\w+', preferred_role))

            profile_words = profile_words - STOP_WORDS
            job_words = set(re.findall(r'\w+', job_title_lower)) - STOP_WORDS

            overlap = profile_words.intersection(job_words)
            if overlap:
                title_score = 20.0
                title_matched = True

        # If title doesn't match, check category keywords as fallback
        if not title_matched and occupation_cat != "unknown":
            # Map categories to typical keywords
            cat_keywords = {
                "it and software": ["developer", "software", "programmer", "coder", "fullstack", "backend", "frontend", "devops", "cloud", "engineer"],
                "accounting and finance": ["accountant", "accounting", "bookkeeper", "finance", "audit", "billing", "accounts payable", "accounts receivable", "taxation"],
                "sales and marketing": ["sales", "marketing", "digital marketing", "seo", "business development", "lead generation", "telesales"],
                "customer service": ["customer support", "call center", "customer service", "helpdesk", "support executive"],
                "education": ["teacher", "teaching", "trainer", "tutor", "professor", "lecturer"],
                "healthcare": ["nurse", "nursing", "medical", "pharmacist", "healthcare", "patient care", "clinic"],
                "electronics and electrical": ["electrician", "wiring", "electrical", "electronics", "circuit", "hardware engineer"],
                "skilled trades": ["mechanic", "technician", "welder", "plumber", "maintenance"],
                "logistics and operations": ["warehouse", "driver", "driving", "delivery", "logistics", "supply chain"],
                "hospitality": ["hotel", "housekeeping", "food service", "chef", "cook", "restaurant", "waiter", "waitress"]
            }
            if occupation_cat in cat_keywords:
                for kw in cat_keywords[occupation_cat]:
                    if kw in job_title_lower:
                        title_score = 15.0
                        break

    # 3. Experience, Education, Training & Languages Match (Max 15 points)
    exp_score = 0.0
    # Consolidate all profile texts
    profile_text = f"{profile.professional_summary or ''} {profile.career_objective or ''} {' '.join(profile_experience)} {' '.join(profile_projects)} {' '.join(profile_certs)} {' '.join(profile_training)} {' '.join(profile_internships)} {' '.join(profile_licences)} {' '.join(profile_languages)}".lower()

    job_title_words = set(re.findall(r'\w+', job_title_lower)) - STOP_WORDS
    check_words = job_title_words.union({s.lower() for s in matched_skills})

    matches_found = 0
    for word in check_words:
        if len(word) >= 3 and word in profile_text:
            matches_found += 1

    # Check for education degrees overlap
    education_levels = ["iti", "diploma", "bachelor", "master", "phd", "degree", "intermediate", "apprentice"]
    for level in education_levels:
        if level in profile_text and level in (job_title_lower + " " + job_description.lower()):
            matches_found += 2

    # Each match yields 3 points, capped at 15
    exp_score = min(matches_found * 3, 15)

    # 4. Location & Preferred Location Preference Match (Max 10 points)
    location_score = 0.0
    profile_loc = (profile.location or "").lower().strip()
    pref_loc = (profile.preferred_location or "").lower().strip()

    if job_remote == "remote":
        location_score = 10.0
    elif job_location:
        job_loc_lower = job_location.lower()
        # Direct or substring check for both location and preferred location
        matched_loc = False
        if profile_loc:
            loc_keywords = [w.strip() for w in re.split(r'[\s,]+', profile_loc) if w.strip()]
            for kw in loc_keywords:
                if len(kw) >= 3 and kw in job_loc_lower:
                    location_score = 10.0
                    matched_loc = True
                    break
        if not matched_loc and pref_loc:
            pref_keywords = [w.strip() for w in re.split(r'[\s,]+', pref_loc) if w.strip()]
            for kw in pref_keywords:
                if len(kw) >= 3 and kw in job_loc_lower:
                    location_score = 10.0
                    break

    # Sum scores
    total_score = int(round(skill_score + title_score + exp_score + location_score))
    total_score = min(max(total_score, 0), 100)

    return {
        "match_score": total_score,
        "matched_skills": sorted(list(set(matched_skills))),
        "missing_skills": sorted(list(set(missing_skills))),
        "explanation": f"Skills: {int(round(skill_score))}/50, Title: {int(round(title_score))}/25, Experience: {int(round(exp_score))}/15, Location: {int(round(location_score))}/10"
    }
