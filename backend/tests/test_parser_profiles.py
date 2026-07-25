import pytest
import json
from app.services.profile_extractor import extract_profile_from_text
from app.models.profile import Profile
from app.services.job_matcher import calculate_match

# 1. IT Developer Resume
IT_RESUME = """
Kishore Kumar
kishore@example.com
9876543210
Hyderabad, India

SENIOR PYTHON DEVELOPER

CAREER OBJECTIVE
To build high-performance web applications using Python and cloud tools.

SUMMARY
Over 5 years of experience in backend development.

TECHNICAL SKILLS
Python, FastAPI, SQL, Docker, AWS, Git, RAG

EXPERIENCE
Software Engineer at Apex Tech (2021 - Present)
- Developed FastAPI microservices
Developer at WebSolutions (2018 - 2021)
- Worked on Django and PostgreSQL applications

EDUCATION
Bachelor's Degree in Computer Science, JNTU (2014 - 2018)
"""

# 2. Accountant Resume
ACCOUNTANT_RESUME = """
Anjali Sharma
anjali@example.com
+91 9999988888
Delhi, India

SENIOR ACCOUNTANT

SUMMARY
Accountant with GST and taxation expertise.

SKILLS
Accounting, Bookkeeping, Tally, GST, Taxation, Invoicing, Payroll, Accounts Payable

EXPERIENCE
Senior Accountant at ABC Finance (2020 - Present)
- Handled monthly invoicing and GST filing
Junior Accountant at Delhi Ledger (2017 - 2020)
- Maintained bookkeeping and accounts payable records

EDUCATION
Bachelor's Degree in Commerce, Delhi University
"""

# 3. Sales Resume
SALES_RESUME = """
Rohan Verma
rohan@example.com
1112223333
Mumbai, India

SALES EXECUTIVE

SUMMARY
Goal-oriented sales professional with 3 years of lead generation and negotiation success.

SKILLS
Sales, Lead Generation, Customer Relationship Management, Negotiation, Marketing, Digital Marketing

EXPERIENCE
Sales Executive at TargetCorp (2021 - Present)
- Drove business development and lead generation campaigns
Sales Associate at RetailHub (2019 - 2021)
- Managed customer relations and retail sales

EDUCATION
Diploma in Marketing, Mumbai Institute
"""

# 4. Teacher Resume
TEACHER_RESUME = """
Saritha Reddy
saritha@example.com
+91 8888877777
Bangalore, India

HIGH SCHOOL TEACHER

SUMMARY
Dedicated teacher with classroom management experience.

SKILLS
Teaching, Lesson Planning, Classroom Management, Student Assessment, Training

EXPERIENCE
Teacher at Greenvalley High School (2019 - Present)
- Conducted classes and student assessments
Tutor at private coaching center (2017 - 2019)
- Structured lesson planning and curriculum development

EDUCATION
Master's Degree in Education, Bangalore University
"""

# 5. Electronics Technician Resume
TECHNICIAN_RESUME = """
Vijay Naidu
vijay@example.com
7778889999
Chennai, India

ELECTRONICS TECHNICIAN

SUMMARY
Technician skilled in troubleshooting and wiring.

SKILLS
Electrical Wiring, Electronics, Equipment Maintenance, Troubleshooting, Repair, Safety Procedures

EXPERIENCE
Technician at VoltPower Ltd (2020 - Present)
- Performed electrical wiring and preventive maintenance
Apprentice at RepairHub (2018 - 2020)
- Repaired machine operation circuits and troubleshooting boards

EDUCATION
ITI in Electronics, Chennai Trade School
"""

# 6. Fresher Resume
FRESHER_RESUME = """
Amit Patel
amit@example.com
8889990000
Pune, India

GRADUATE STUDENT / FRESHER

OBJECTIVE
Motivated fresher seeking entry-level opportunities.

SKILLS
Communication, Teamwork, Leadership, Time Management, Adaptability

EXPERIENCE
Intern at Pune Operations (3 months)
- Supported stock management and warehouse dispatch tasks

EDUCATION
Intermediate, Pune Junior College (2021)
10th Class, Pune Public School (2019)
"""

# 7. Heading-less Resume
HEADINGLESS_RESUME = """
Laxman Rao
laxman@example.com
9876123456
Hyderabad, India
Office Administrator

He is an administrative assistant with scheduling experience.
His skills include data entry, scheduling, Microsoft word, bookkeeping, and teamwork.
He was an Office Assistant at Apex Inc from 2021 to 2023.
Before that he studied Intermediate at Telangana College.
"""

# 8. Email-less Resume
EMAILLESS_RESUME = """
Suresh Goud
9876543222
Secunderabad, India
Delivery Executive

SUMMARY
Prompt driver and logistics professional.

SKILLS
Warehouse Operations, Dispatch, Delivery, Driving, Route Planning, Stock Management

EXPERIENCE
Delivery Driver at QuickLogistics (2022 - Present)
- Managed dispatch, route planning and stock delivery
"""

# 9. Experience-less Resume
EXPERIENCELESS_RESUME = """
Deepa R
deepa@example.com
8888777766
Bangalore, India
Customer Support Executive

SUMMARY
Support agent with communication and call handling skills.

SKILLS
Customer Support, Call Handling, Email Support, Complaint Resolution, CRM, Communication

EDUCATION
Vocational Training in Office Administration, Bangalore Center
"""

# 10. Unknown Section Resume
UNKNOWN_SECTION_RESUME = """
Nikhil Sen
nikhil@example.com
9999911111
Kolkata, India
Teacher

SUMMARY
High school teacher.

SKILLS
Teaching, Training

EXPERIENCE
Teacher at Model School (2021 - Present)

EDUCATION
Bachelor's Degree in Education

HOBBIES AND PASSIONS
Reading fiction, playing badminton, and long-distance cycling.

PUBLICATIONS AND PATENTS
Co-authored paper on classroom management strategies in 2023.
"""

def test_it_developer_resume():
    prof = extract_profile_from_text(IT_RESUME)
    assert prof["full_name"] == "Kishore Kumar"
    assert prof["email"] == "kishore@example.com"
    assert prof["phone"] == "9876543210"
    assert prof["professional_title"] == "SENIOR PYTHON DEVELOPER"
    assert "Python" in prof["technical_skills"]
    assert "FastAPI" in prof["technical_skills"]
    assert "SQL" in prof["technical_skills"]
    assert prof["occupation_category"] == "IT and Software"
    assert len(prof["work_experience"]) >= 2
    assert "Apex Tech" in prof["current_company"]
    assert "Software Engineer" in prof["current_role"]
    assert prof["resume_quality"] == "complete"

def test_accountant_resume():
    prof = extract_profile_from_text(ACCOUNTANT_RESUME)
    assert prof["full_name"] == "Anjali Sharma"
    assert prof["email"] == "anjali@example.com"
    assert "Accounting" in prof["technical_skills"]
    assert "Tally" in prof["technical_skills"]
    assert "GST" in prof["technical_skills"]
    assert prof["occupation_category"] == "Accounting and Finance"
    assert "ABC Finance" in prof["current_company"]
    assert "Senior Accountant" in prof["current_role"]
    assert prof["resume_quality"] == "complete"

def test_sales_resume():
    prof = extract_profile_from_text(SALES_RESUME)
    assert prof["full_name"] == "Rohan Verma"
    assert "Sales" in prof["technical_skills"]
    assert "Lead Generation" in prof["technical_skills"]
    assert "Negotiation" in prof["technical_skills"]
    assert prof["occupation_category"] == "Sales and Marketing"
    assert "TargetCorp" in prof["current_company"]
    assert "Sales Executive" in prof["current_role"]
    assert prof["resume_quality"] == "complete"

def test_teacher_resume():
    prof = extract_profile_from_text(TEACHER_RESUME)
    assert prof["full_name"] == "Saritha Reddy"
    assert "Teaching" in prof["technical_skills"]
    assert "Classroom Management" in prof["technical_skills"]
    assert prof["occupation_category"] == "Education"
    assert "Greenvalley High School" in prof["current_company"]
    assert "Teacher" in prof["current_role"]
    assert prof["resume_quality"] == "complete"

def test_technician_resume():
    prof = extract_profile_from_text(TECHNICIAN_RESUME)
    assert prof["full_name"] == "Vijay Naidu"
    assert "Electrical Wiring" in prof["technical_skills"]
    assert "Troubleshooting" in prof["technical_skills"]
    assert "Electronics" in prof["technical_skills"]
    assert prof["occupation_category"] == "Electronics and Electrical"
    assert "VoltPower Ltd" in prof["current_company"]
    assert "Technician" in prof["current_role"]
    assert prof["resume_quality"] == "complete"

def test_fresher_resume():
    prof = extract_profile_from_text(FRESHER_RESUME)
    assert prof["full_name"] == "Amit Patel"
    assert "Leadership" in prof["soft_skills"]
    assert "Communication" in prof["soft_skills"]
    assert prof["occupation_category"] == "Fresher or Student"
    assert prof["resume_quality"] == "complete"

def test_headingless_resume():
    prof = extract_profile_from_text(HEADINGLESS_RESUME)
    assert prof["email"] == "rose" or prof["email"] == "laxman@example.com"
    # Basic contacts should still match
    assert prof["email"] == "laxman@example.com"
    assert prof["phone"] == "9876123456"
    assert "Data Entry" in prof["technical_skills"]
    assert "Bookkeeping" in prof["technical_skills"]

def test_emailless_resume():
    prof = extract_profile_from_text(EMAILLESS_RESUME)
    assert prof["email"] == ""
    assert prof["phone"] == "9876543222"
    assert "Delivery" in prof["technical_skills"]
    assert "Route Planning" in prof["technical_skills"]
    assert prof["resume_quality"] == "partial"

def test_experienceless_resume():
    prof = extract_profile_from_text(EXPERIENCELESS_RESUME)
    assert prof["email"] == "deepa@example.com"
    assert len(prof["work_experience"]) == 0
    assert "Customer Support" in prof["technical_skills"]
    assert prof["resume_quality"] == "partial"

def test_unknown_section_resume():
    prof = extract_profile_from_text(UNKNOWN_SECTION_RESUME)
    assert prof["email"] == "nikhil@example.com"
    # Check unrecognized sections are preserved in additional_information
    assert "Hobbies And Passions" in prof["additional_information"]
    assert "Reading fiction, playing badminton" in prof["additional_information"]
    assert "Publications And Patents" in prof["additional_information"]
    assert "Co-authored paper on classroom management" in prof["additional_information"]

def test_non_it_job_matching():
    # Setup dummy profile representing an accountant
    prof = Profile(
        full_name="Anjali Sharma",
        professional_title="Accountant",
        occupation_category="Accounting and Finance",
        skills=json.dumps(["Accounting", "Bookkeeping", "Tally", "GST"]),
        technical_skills=json.dumps(["Accounting", "Tally"]),
        soft_skills=json.dumps(["Communication"]),
        work_experience=json.dumps(["Accountant at ABC Finance (2020-Present)"]),
        location="Delhi"
    )

    # 1. Matching Accounting Job should score high
    res_acct = calculate_match(
        job_title="Senior Accountant",
        job_description="Need someone to manage accounting books, tally logs, and file GST",
        job_skills=["Accounting", "Tally", "GST"],
        job_remote="remote",
        job_location="Mumbai",
        profile=prof
    )
    assert res_acct["match_score"] > 70
    assert "Accounting" in res_acct["matched_skills"]
    assert "Tally" in res_acct["matched_skills"]

    # 2. Matching Software Developer Job should score very low
    res_soft = calculate_match(
        job_title="Python developer",
        job_description="Build django fastapis",
        job_skills=["Python", "FastAPI", "Docker"],
        job_remote="onsite",
        job_location="Bangalore",
        profile=prof
    )
    assert res_soft["match_score"] < 40
