import html
import io
import json
import re
from datetime import datetime
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.job import Job
from app.models.profile import Profile


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render footer page numbers ('Page X of Y')
    on A4 landscape layouts.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#4b5563"))

        # A4 landscape width is 841.89, height is 595.27
        # Bottom margin is 36pt, print footer at height 20pt
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(841.89 - 36, 20, page_text)

        timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")
        footer_left = f"Personal Job Finder | Report Generated: {timestamp}"
        self.drawString(36, 20, footer_left)
        self.restoreState()


def safe_text(val: Any) -> str:
    """
    Sanitize text before rendering to prevent ReportLab XML parser crashes.
    Decodes HTML entities, strips control characters, escapes special XML symbols,
    and converts newlines to <br/>.
    """
    if val is None:
        return ""

    # Cast to string and strip
    s = str(val).strip()
    if not s:
        return ""

    # 1. Strip raw HTML tags
    s = re.sub(r"<[^>]*>", "", s)

    # 2. Decode existing entities
    s = html.unescape(s)

    # 3. Strip control characters
    s = "".join(ch for ch in s if ch.isprintable() or ch in "\n\t")

    # 4. XML escape
    s = html.escape(s)

    # 5. Convert newlines to ReportLab line breaks
    s = s.replace("\n", "<br/>")
    return s


def format_date(dt: Any) -> str:
    """
    Format dates consistently to YYYY-MM-DD or return fallback.
    """
    if not dt:
        return "-"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    s = str(dt).strip()
    if not s:
        return "-"
    # Parse standard YYYY-MM-DD
    try:
        parsed = datetime.strptime(s[:10], "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return s


def create_report_header(report_title: str, profile: Profile | None, styles: Any) -> list[Any]:
    """
    Generates report title and candidate profile details block.
    """
    flowables = []

    # Document main title
    title_p = Paragraph("<b>Personal Job Finder</b>", styles["DocTitle"])
    flowables.append(title_p)

    subtitle_p = Paragraph(f"Report: {report_title}", styles["DocSubtitle"])
    flowables.append(subtitle_p)
    flowables.append(Spacer(1, 12))

    # Candidate details card
    if profile:
        profile_data = [
            [
                Paragraph("<b>Candidate Name:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.full_name), styles["HeaderValue"]),
                Paragraph("<b>Professional Title:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.professional_title), styles["HeaderValue"]),
            ],
            [
                Paragraph("<b>Occupation Category:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.occupation_category), styles["HeaderValue"]),
                Paragraph("<b>Preferred Job Role:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.preferred_job_role), styles["HeaderValue"]),
            ],
            [
                Paragraph("<b>Preferred Location:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.preferred_location), styles["HeaderValue"]),
                Paragraph("<b>Total Experience:</b>", styles["HeaderLabel"]),
                Paragraph(safe_text(profile.total_experience), styles["HeaderValue"]),
            ],
        ]

        # Table takes 4 columns (Label1: 120, Value1: 250, Label2: 120, Value2: 250)
        profile_table = Table(profile_data, colWidths=[120, 250, 120, 250])
        profile_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f3f4f6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
                ]
            )
        )

        flowables.append(profile_table)
        flowables.append(Spacer(1, 16))

    return flowables


def create_summary_section(jobs: list[Job], styles: Any) -> Table:
    """
    Renders match distributions, remote status ratios, and application statuses.
    """
    total = len(jobs)

    # 1. Match Categories
    strong = sum(1 for j in jobs if j.match_score is not None and 80 <= j.match_score <= 100)
    good = sum(1 for j in jobs if j.match_score is not None and 60 <= j.match_score <= 79)
    partial = sum(1 for j in jobs if j.match_score is not None and 40 <= j.match_score <= 59)
    low = sum(1 for j in jobs if j.match_score is not None and 0 <= j.match_score <= 39)

    # 2. Remote ratios
    remote = sum(1 for j in jobs if (j.remote_status or "").lower() == "remote")
    hybrid = sum(1 for j in jobs if (j.remote_status or "").lower() == "hybrid")
    onsite = sum(1 for j in jobs if (j.remote_status or "").lower() == "onsite")
    unknown_arr = sum(1 for j in jobs if (j.remote_status or "").lower() not in ["remote", "hybrid", "onsite"])

    # 3. Statuses
    applied = sum(1 for j in jobs if j.application_status == "applied")
    saved = sum(1 for j in jobs if j.application_status == "saved")
    not_applied = sum(1 for j in jobs if j.application_status == "not_applied")
    interview = sum(1 for j in jobs if j.application_status == "interview")
    rejected = sum(1 for j in jobs if j.application_status == "rejected")
    offer = sum(1 for j in jobs if j.application_status == "offer")

    summary_data = [
        [
            Paragraph("<b>MATCH PROFILE</b>", styles["SectionHeader"]),
            Paragraph("<b>WORK ARRANGEMENTS</b>", styles["SectionHeader"]),
            Paragraph("<b>APPLICATION TRACKING</b>", styles["SectionHeader"]),
        ],
        [
            Paragraph(
                f"• <b>Strong (80-100):</b> {strong}<br/>"
                f"• <b>Good (60-79):</b> {good}<br/>"
                f"• <b>Partial (40-59):</b> {partial}<br/>"
                f"• <b>Low (0-39):</b> {low}",
                styles["SummaryCell"],
            ),
            Paragraph(
                f"• <b>Remote:</b> {remote}<br/>"
                f"• <b>Hybrid:</b> {hybrid}<br/>"
                f"• <b>Onsite:</b> {onsite}<br/>"
                f"• <b>Unknown:</b> {unknown_arr}",
                styles["SummaryCell"],
            ),
            Paragraph(
                f"• <b>Not Applied:</b> {not_applied}<br/>"
                f"• <b>Saved:</b> {saved}<br/>"
                f"• <b>Applied:</b> {applied}<br/>"
                f"• <b>Interview:</b> {interview}<br/>"
                f"• <b>Rejected:</b> {rejected}<br/>"
                f"• <b>Offer:</b> {offer}",
                styles["SummaryCell"],
            ),
        ],
    ]

    # Available width is 770
    t = Table(summary_data, colWidths=[256, 256, 258])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, 1), HexColor("#f8fafc")),
            ]
        )
    )
    return t


def format_job_record(job: Job, styles: Any) -> list[Any]:
    """
    Format job data fields into wrapped Flowables representing a single table row.
    """
    # 1. Match score
    match_val = f"{job.match_score}%" if job.match_score is not None else "-"
    match_p = Paragraph(f"<b>{match_val}</b>", styles["ScoreCell"])

    # 2. Title & Company
    title_escaped = safe_text(job.title)
    company_escaped = safe_text(job.company_name)
    title_company = Paragraph(
        f"<b>{title_escaped}</b><br/><font color='#4b5563'>{company_escaped}</font>",
        styles["TableCell"],
    )

    # 3. Location, Remote & Type
    loc = safe_text(job.location) or "Unknown"
    remote = (job.remote_status or "Unknown").capitalize()
    emptype = (job.employment_type or "Full-Time").capitalize()
    loc_type = Paragraph(f"{loc}<br/><i>{remote} | {emptype}</i>", styles["TableCell"])

    # 4. Salary & Source
    sal = safe_text(job.salary) or "Not specified"
    src = safe_text(job.source)
    sal_source = Paragraph(f"{sal}<br/><font color='#0d9488'>{src}</font>", styles["TableCell"])

    # 5. Status & Dates
    status_val = (job.application_status or "not_applied").replace("_", " ").upper()
    posted_d = format_date(job.posted_date)
    applied_d = format_date(job.applied_date) if job.application_status == "applied" and job.applied_date else "-"
    status_dates = Paragraph(
        f"<b>{status_val}</b><br/>Posted: {posted_d}<br/>Applied: {applied_d}",
        styles["TableCell"],
    )

    # 6. Skills (technical/soft)
    try:
        matched_arr = json.loads(job.matched_skills) if job.matched_skills else []
    except Exception:
        matched_arr = []
    try:
        missing_arr = json.loads(job.missing_skills) if job.missing_skills else []
    except Exception:
        missing_arr = []

    matched_s = ", ".join(matched_arr) if matched_arr else "None"
    missing_s = ", ".join(missing_arr) if missing_arr else "None"

    skills = Paragraph(
        f"<b>Matched:</b> <font color='#16a34a'>{safe_text(matched_s)}</font><br/>"
        f"<b>Missing:</b> <font color='#b91c1c'>{safe_text(missing_s)}</font>",
        styles["TableCell"],
    )

    # 7. Notes & Job Link
    notes_escaped = safe_text(job.notes)
    notes_display = f"{notes_escaped[:120]}..." if len(notes_escaped) > 120 else notes_escaped

    link_html = "-"
    if job.original_url:
        # Escape the raw url to avoid breaking reportlab anchor
        raw_url = html.escape(job.original_url)
        link_html = f"<a href='{raw_url}' color='#2563eb'><u>Job Link</u></a>"

    notes_link = Paragraph(f"{notes_display or 'No notes added.'}<br/>{link_html}", styles["TableCell"])

    return [
        match_p,
        title_company,
        loc_type,
        sal_source,
        status_dates,
        skills,
        notes_link,
    ]


def create_jobs_table(jobs: list[Job], styles: Any) -> Table:
    """
    Assembles a landscape, paginated table of jobs.
    """
    header_row = [
        Paragraph("<b>Match</b>", styles["TableHeader"]),
        Paragraph("<b>Job Title & Company</b>", styles["TableHeader"]),
        Paragraph("<b>Location & Type</b>", styles["TableHeader"]),
        Paragraph("<b>Salary & Source</b>", styles["TableHeader"]),
        Paragraph("<b>Status & Dates</b>", styles["TableHeader"]),
        Paragraph("<b>Matched / Missing Skills</b>", styles["TableHeader"]),
        Paragraph("<b>Notes & Apply Link</b>", styles["TableHeader"]),
    ]

    table_data = [header_row]
    for job in jobs:
        table_data.append(format_job_record(job, styles))

    # Table column widths must equal 770pt total
    col_widths = [35, 120, 90, 80, 90, 170, 185]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Base grid and header formatting
    t_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f766e")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    # Alternating row colors
    for i in range(1, len(jobs) + 1):
        bg = "#ffffff" if i % 2 != 0 else "#f9fafb"
        t_styles.append(("BACKGROUND", (0, i), (-1, i), HexColor(bg)))

    t.setStyle(TableStyle(t_styles))
    return t


def create_jobs_pdf(jobs: list[Job], report_title: str, profile: Profile | None = None) -> bytes:
    """
    Main generator method. Compiles reports with covers, stats summaries,
    safe HTML escaping, and returns PDF raw bytes.
    """
    buffer = io.BytesIO()

    # 36pt margins (0.5 inch margins)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    # Build standard paragraph styles
    base_styles = getSampleStyleSheet()
    styles = {}

    styles["DocTitle"] = ParagraphStyle(
        name="DocTitle",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=HexColor("#0f766e"),
    )

    styles["DocSubtitle"] = ParagraphStyle(
        name="DocSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=HexColor("#4b5563"),
    )

    styles["HeaderLabel"] = ParagraphStyle(
        name="HeaderLabel",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#0f766e"),
    )

    styles["HeaderValue"] = ParagraphStyle(
        name="HeaderValue",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#1f2937"),
    )

    styles["SectionHeader"] = ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=HexColor("#ffffff"),
        alignment=1,  # Center
    )

    styles["SummaryCell"] = ParagraphStyle(
        name="SummaryCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=HexColor("#1e293b"),
    )

    styles["TableHeader"] = ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=HexColor("#ffffff"),
    )

    styles["TableCell"] = ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=7,
        leading=9.5,
        textColor=HexColor("#1e293b"),
    )

    styles["ScoreCell"] = ParagraphStyle(
        name="ScoreCell",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,  # Center
        textColor=HexColor("#0f766e"),
    )

    styles["EmptyText"] = ParagraphStyle(
        name="EmptyText",
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=HexColor("#b91c1c"),
    )

    flowables = []

    # 1. Header Information Block
    flowables.extend(create_report_header(report_title, profile, styles))

    if not jobs:
        # Empty result PDF layout
        flowables.append(Spacer(1, 16))
        flowables.append(
            Paragraph(
                "<b>No jobs matched the selected report and filters.</b>",
                styles["EmptyText"],
            )
        )
    else:
        # 2. Summary Page Section (Only for reports with 5 or more jobs)
        if len(jobs) >= 5:
            summary_title = Paragraph("<b>REPORT OVERVIEW & STATISTICS</b>", styles["DocSubtitle"])
            flowables.append(summary_title)
            flowables.append(Spacer(1, 8))
            flowables.append(create_summary_section(jobs, styles))
            flowables.append(PageBreak())

            # Start page 2 with mini header and jobs table
            mini_title = Paragraph(
                f"<b>Personal Job Finder — {report_title} (List View)</b>",
                styles["DocSubtitle"],
            )
            flowables.append(mini_title)
            flowables.append(Spacer(1, 8))

        # 3. Main Jobs List Table
        flowables.append(create_jobs_table(jobs, styles))

    doc.build(flowables, canvasmaker=NumberedCanvas)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_single_job_pdf(job: Job, profile: Profile | None = None) -> bytes:
    """
    Renders detailed print layout (A4 Portrait) for a single job description.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    base_styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        name="JobTitle",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=HexColor("#0f766e"),
    )
    company_style = ParagraphStyle(
        name="JobCompany",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=HexColor("#4b5563"),
    )
    section_title_style = ParagraphStyle(
        name="SectionTitle",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=HexColor("#0f766e"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        name="JobBody",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#1e293b"),
    )
    label_style = ParagraphStyle(
        name="LabelStyle",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=HexColor("#0f766e"),
    )

    flowables = []

    # Title & Company
    flowables.append(Paragraph(safe_text(job.title), title_style))
    flowables.append(Spacer(1, 4))
    flowables.append(Paragraph(safe_text(job.company_name), company_style))
    flowables.append(Spacer(1, 12))

    # Metadata grid table
    meta_data = [
        [
            Paragraph("<b>Location:</b>", label_style),
            Paragraph(safe_text(job.location) or "Unknown", body_style),
            Paragraph("<b>Remote Status:</b>", label_style),
            Paragraph((job.remote_status or "Unknown").capitalize(), body_style),
        ],
        [
            Paragraph("<b>Employment Type:</b>", label_style),
            Paragraph((job.employment_type or "Full-Time").capitalize(), body_style),
            Paragraph("<b>Salary:</b>", label_style),
            Paragraph(safe_text(job.salary) or "Not specified", body_style),
        ],
        [
            Paragraph("<b>Source:</b>", label_style),
            Paragraph(safe_text(job.source), body_style),
            Paragraph("<b>Match Score:</b>", label_style),
            Paragraph(
                f"{job.match_score}%" if job.match_score is not None else "N/A",
                body_style,
            ),
        ],
        [
            Paragraph("<b>App Status:</b>", label_style),
            Paragraph(
                (job.application_status or "not_applied").replace("_", " ").upper(),
                body_style,
            ),
            Paragraph("<b>Posted Date:</b>", label_style),
            Paragraph(format_date(job.posted_date), body_style),
        ],
    ]
    # Printable A4 Portrait is 595.27 - 108 = 487.27 pt.
    meta_table = Table(meta_data, colWidths=[100, 143, 100, 144])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ]
        )
    )
    flowables.append(meta_table)
    flowables.append(Spacer(1, 16))

    # Skills match
    flowables.append(Paragraph("Skills Fit", section_title_style))
    try:
        matched_arr = json.loads(job.matched_skills) if job.matched_skills else []
    except Exception:
        matched_arr = []
    try:
        missing_arr = json.loads(job.missing_skills) if job.missing_skills else []
    except Exception:
        missing_arr = []

    matched_s = ", ".join(matched_arr) if matched_arr else "None"
    missing_s = ", ".join(missing_arr) if missing_arr else "None"

    skills_p = Paragraph(
        f"<b>Matched Skills:</b> <font color='#16a34a'>{safe_text(matched_s)}</font><br/>"
        f"<b>Missing Skills:</b> <font color='#b91c1c'>{safe_text(missing_s)}</font>",
        body_style,
    )
    flowables.append(skills_p)

    # Notes
    flowables.append(Paragraph("Personal Tracking Notes", section_title_style))
    notes_val = safe_text(job.notes) or "No tracking notes added."
    flowables.append(Paragraph(notes_val, body_style))

    # Description
    flowables.append(Paragraph("Job Description", section_title_style))
    desc_val = safe_text(job.description) or "No job description available."
    flowables.append(Paragraph(desc_val, body_style))

    # Link
    if job.original_url:
        flowables.append(Spacer(1, 16))
        raw_url = html.escape(job.original_url)
        link_html = f"<a href='{raw_url}' color='#2563eb'>Apply / View Original Posting: <u>{raw_url}</u></a>"
        flowables.append(Paragraph(link_html, body_style))

    doc.build(flowables)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_application_summary_pdf(jobs: list[Job], profile: Profile | None = None) -> bytes:
    """
    Renders overview dashboard details (A4 Portrait) for the candidate's job hunting tracking metrics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="SummaryTitle",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=HexColor("#0f766e"),
    )
    subtitle_style = ParagraphStyle(
        name="SummarySubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=HexColor("#4b5563"),
    )
    section_header_style = ParagraphStyle(
        name="SectionHeaderSummary",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=HexColor("#0f766e"),
        spaceBefore=14,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        name="SummaryCellP",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#1e293b"),
    )

    flowables = []

    flowables.append(Paragraph("<b>Personal Job Finder</b>", title_style))
    flowables.append(Paragraph("Application Tracking Summary Report", subtitle_style))
    flowables.append(Spacer(1, 12))

    # 1. Candidate profile block (if available)
    if profile:
        profile_data = [
            [
                Paragraph("<b>Candidate Name:</b>", cell_style),
                Paragraph(safe_text(profile.full_name), cell_style),
                Paragraph("<b>Professional Title:</b>", cell_style),
                Paragraph(safe_text(profile.professional_title), cell_style),
            ],
            [
                Paragraph("<b>Occupation Category:</b>", cell_style),
                Paragraph(safe_text(profile.occupation_category), cell_style),
                Paragraph("<b>Preferred Job Role:</b>", cell_style),
                Paragraph(safe_text(profile.preferred_job_role), cell_style),
            ],
        ]
        t_profile = Table(profile_data, colWidths=[90, 153, 90, 154])
        t_profile.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f3f4f6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
                ]
            )
        )
        flowables.append(t_profile)
        flowables.append(Spacer(1, 16))

    # 2. Key Metrics Table
    total = len(jobs)
    saved = sum(1 for j in jobs if j.application_status == "saved")
    not_applied = sum(1 for j in jobs if j.application_status == "not_applied")
    applied = sum(1 for j in jobs if j.application_status == "applied")
    interview = sum(1 for j in jobs if j.application_status == "interview")
    rejected = sum(1 for j in jobs if j.application_status == "rejected")
    offer = sum(1 for j in jobs if j.application_status == "offer")

    strong = sum(1 for j in jobs if j.match_score is not None and 80 <= j.match_score <= 100)

    metrics_data = [
        [
            Paragraph("<b><font color='white'>Metric</font></b>", cell_style),
            Paragraph("<b><font color='white'>Count</font></b>", cell_style),
            Paragraph("<b><font color='white'>Metric</font></b>", cell_style),
            Paragraph("<b><font color='white'>Count</font></b>", cell_style),
        ],
        [
            Paragraph("Total Jobs Tracked", cell_style),
            Paragraph(str(total), cell_style),
            Paragraph("Interviewing Stage", cell_style),
            Paragraph(str(interview), cell_style),
        ],
        [
            Paragraph("Not Applied", cell_style),
            Paragraph(str(not_applied), cell_style),
            Paragraph("Offers Received", cell_style),
            Paragraph(str(offer), cell_style),
        ],
        [
            Paragraph("Saved", cell_style),
            Paragraph(str(saved), cell_style),
            Paragraph("Rejections", cell_style),
            Paragraph(str(rejected), cell_style),
        ],
        [
            Paragraph("Applied Status", cell_style),
            Paragraph(str(applied), cell_style),
            Paragraph("Strong Matches (80+)", cell_style),
            Paragraph(str(strong), cell_style),
        ],
    ]
    t_metrics = Table(metrics_data, colWidths=[150, 93, 150, 94])
    t_metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f766e")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f8fafc")),
            ]
        )
    )

    flowables.append(Paragraph("Job Hunting Metrics", section_header_style))
    flowables.append(t_metrics)

    # 3. Recent Applied Jobs Table
    applied_jobs = [j for j in jobs if j.application_status in ["applied", "interview", "offer"]]
    # Sort by applied date desc (or created_at if not set)
    applied_jobs.sort(key=lambda j: j.applied_date or j.created_at or datetime.min, reverse=True)

    flowables.append(Paragraph("Recent Application Activity", section_header_style))
    if not applied_jobs:
        flowables.append(Paragraph("No active applications tracked yet.", cell_style))
    else:
        app_rows = [
            [
                Paragraph("<b><font color='white'>Match</font></b>", cell_style),
                Paragraph("<b><font color='white'>Job Title & Company</font></b>", cell_style),
                Paragraph("<b><font color='white'>Status</font></b>", cell_style),
                Paragraph("<b><font color='white'>Applied Date</font></b>", cell_style),
            ]
        ]
        for j in applied_jobs[:6]:
            app_rows.append(
                [
                    Paragraph(
                        f"<b>{j.match_score}%</b>" if j.match_score is not None else "-",
                        cell_style,
                    ),
                    Paragraph(
                        f"<b>{safe_text(j.title)}</b> at {safe_text(j.company_name)}",
                        cell_style,
                    ),
                    Paragraph(
                        (j.application_status or "").replace("_", " ").upper(),
                        cell_style,
                    ),
                    Paragraph(
                        format_date(j.applied_date) if j.applied_date else format_date(j.created_at),
                        cell_style,
                    ),
                ]
            )
        t_apps = Table(app_rows, colWidths=[40, 260, 97, 90])
        t_apps.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f766e")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ]
            )
        )
        flowables.append(t_apps)

    # 4. Recent Interviews/Offers Table
    int_jobs = [j for j in jobs if j.application_status in ["interview", "offer"]]
    int_jobs.sort(key=lambda j: j.updated_at or datetime.min, reverse=True)

    flowables.append(Paragraph("Recent Interviews & Offers", section_header_style))
    if not int_jobs:
        flowables.append(Paragraph("No interviews or offers recorded yet.", cell_style))
    else:
        int_rows = [
            [
                Paragraph("<b><font color='white'>Job Title & Company</font></b>", cell_style),
                Paragraph("<b><font color='white'>Status</font></b>", cell_style),
                Paragraph("<b><font color='white'>Last Updated</font></b>", cell_style),
            ]
        ]
        for j in int_jobs[:5]:
            int_rows.append(
                [
                    Paragraph(
                        f"<b>{safe_text(j.title)}</b> at {safe_text(j.company_name)}",
                        cell_style,
                    ),
                    Paragraph((j.application_status or "").upper(), cell_style),
                    Paragraph(format_date(j.updated_at), cell_style),
                ]
            )
        t_ints = Table(int_rows, colWidths=[310, 87, 90])
        t_ints.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f766e")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ]
            )
        )
        flowables.append(t_ints)

    doc.build(flowables)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
