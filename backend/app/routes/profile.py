import json
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse, ProfileUpdate, ResumeUploadResponse
from app.services.resume_parser import extract_resume_text, ResumeParsingError
from app.services.profile_extractor import extract_profile_from_text

router = APIRouter(prefix="/api/profile", tags=["Profile"])

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Validate file extension
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, and TXT resumes are supported."
        )

    # 2. Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded resume is larger than 2 MB."
        )

    # 3. Extract text from resume
    try:
        resume_text = extract_resume_text(filename, contents)
    except ResumeParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 4. Extract profile fields
    extracted = extract_profile_from_text(resume_text)

    # 5. Create or update the single active profile
    db_profile = db.query(Profile).first()
    if not db_profile:
        db_profile = Profile()
        db.add(db_profile)

    db_profile.full_name = extracted["full_name"]
    db_profile.email = extracted["email"]
    db_profile.phone = extracted["phone"]
    db_profile.location = extracted["location"]
    db_profile.professional_title = extracted["professional_title"]
    db_profile.professional_summary = extracted["professional_summary"]
    db_profile.career_objective = extracted["career_objective"]
    db_profile.total_experience = extracted["total_experience"]
    db_profile.current_company = extracted["current_company"]
    db_profile.current_role = extracted["current_role"]
    db_profile.preferred_job_role = extracted["preferred_job_role"]
    db_profile.preferred_location = extracted["preferred_location"]
    db_profile.availability = extracted["availability"]
    db_profile.occupation_category = extracted["occupation_category"]
    db_profile.additional_information = extracted["additional_information"]
    db_profile.resume_quality = extracted["resume_quality"]

    # Serialize lists to JSON strings
    db_profile.skills = json.dumps(extracted["skills"])
    db_profile.work_experience = json.dumps(extracted["work_experience"])
    db_profile.education = json.dumps(extracted["education"])
    db_profile.projects = json.dumps(extracted["projects"])
    db_profile.certifications = json.dumps(extracted["certifications"])
    db_profile.technical_skills = json.dumps(extracted["technical_skills"])
    db_profile.soft_skills = json.dumps(extracted["soft_skills"])
    db_profile.languages = json.dumps(extracted["languages"])
    db_profile.achievements = json.dumps(extracted["achievements"])
    db_profile.training = json.dumps(extracted["training"])
    db_profile.internships = json.dumps(extracted["internships"])
    db_profile.licences = json.dumps(extracted["licences"])
    db_profile.tools_and_equipment = json.dumps(extracted["tools_and_equipment"])

    db_profile.resume_filename = filename
    db_profile.resume_text = resume_text

    db.commit()
    db.refresh(db_profile)

    return {
        "message": "Resume uploaded and scanned successfully.",
        "profile": db_profile
    }

@router.get("", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    db_profile = db.query(Profile).first()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found. Please upload a resume first."
        )
    return db_profile

@router.put("", response_model=ProfileResponse)
def update_profile(profile_data: ProfileUpdate, db: Session = Depends(get_db)):
    db_profile = db.query(Profile).first()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found to update."
        )

    db_profile.full_name = profile_data.full_name
    db_profile.email = profile_data.email
    db_profile.phone = profile_data.phone
    db_profile.location = profile_data.location
    db_profile.professional_title = profile_data.professional_title
    db_profile.professional_summary = profile_data.professional_summary
    db_profile.career_objective = profile_data.career_objective
    db_profile.total_experience = profile_data.total_experience
    db_profile.current_company = profile_data.current_company
    db_profile.current_role = profile_data.current_role
    db_profile.preferred_job_role = profile_data.preferred_job_role
    db_profile.preferred_location = profile_data.preferred_location
    db_profile.availability = profile_data.availability
    db_profile.occupation_category = profile_data.occupation_category
    db_profile.additional_information = profile_data.additional_information
    db_profile.resume_quality = profile_data.resume_quality

    # Serialize lists to JSON strings
    db_profile.skills = json.dumps(profile_data.skills)
    db_profile.work_experience = json.dumps(profile_data.work_experience)
    db_profile.education = json.dumps(profile_data.education)
    db_profile.projects = json.dumps(profile_data.projects)
    db_profile.certifications = json.dumps(profile_data.certifications)
    db_profile.technical_skills = json.dumps(profile_data.technical_skills)
    db_profile.soft_skills = json.dumps(profile_data.soft_skills)
    db_profile.languages = json.dumps(profile_data.languages)
    db_profile.achievements = json.dumps(profile_data.achievements)
    db_profile.training = json.dumps(profile_data.training)
    db_profile.internships = json.dumps(profile_data.internships)
    db_profile.licences = json.dumps(profile_data.licences)
    db_profile.tools_and_equipment = json.dumps(profile_data.tools_and_equipment)

    db.commit()
    db.refresh(db_profile)

    return db_profile
