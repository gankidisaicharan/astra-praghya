# ═══════════════════════════════════════════════════════════════════
# Astra v2.0 — Praghya Prakhar
# Supply Chain & Operations Resume Tailoring Engine
#
# Design goals (per Praghya, May 2026):
#  - Simple. No conditional gates that block CV generation.
#  - Truthful. Tailor to JD using ONLY skills/experience she actually has.
#  - Structure-preserving. Every base-resume section is always present.
#  - All her real base skills are kept; JD-relevant skills are added on top.
#  - Summary: 4-5 sentences in natural flow.
#  - Education / Certifications / Additional Info: untouched, always rendered.
#  - ATS-friendly output every run.
# ═══════════════════════════════════════════════════════════════════

import streamlit as st
import json
import re
import io
import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from xml.sax.saxutils import escape


# ═══════════════════════════════════════════════════════════════════
# 1. CONFIG
# ═══════════════════════════════════════════════════════════════════

PAGE_TITLE = "Astra — Praghya Prakhar"

# Generation model.
# As of May 2026, gemini-3-flash-preview is the recommended free-tier model
# in the Gemini 3 family. It handles structured-JSON output reliably.
#
# Migration notes — if you see errors, swap MODEL string to one of:
#   - "gemini-3.1-flash-lite-preview"  (cheaper, slightly weaker reasoning)
#   - "gemini-2.5-flash"               (stable until June 17, 2026)
#   - "gemini-2.5-pro"                 (best quality, lower rate limits, deprecates June 17, 2026)
GENERATION_MODEL = "gemini-3-flash-preview"

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    GOOGLE_API_KEY = ""


# ═══════════════════════════════════════════════════════════════════
# 2. FIXED CANDIDATE FACTS
# These NEVER change between runs, no matter what the JD says.
# ═══════════════════════════════════════════════════════════════════

CANDIDATE_NAME = "Praghya Prakhar"
CANDIDATE_TAGLINE = "Supply Chain & Operations Professional"
CANDIDATE_CONTACT = "Dublin, Ireland | +353 89 263 0034 | praghyaprakhar2012@gmail.com | linkedin.com/in/praghya-prakhar-a9b016209"

# Base skill set — real and verified. These are ALWAYS in the output.
# Each category is a list of skills. The tailoring step may APPEND
# JD-relevant skills, but it cannot remove any of these.
BASE_SKILLS = {
    "Supply Chain Management": [
        "Inventory Control", "Order Fulfilment", "Warehouse Operations",
        "Inbound/Outbound Logistics", "Stock Auditing", "Dispatch Coordination",
    ],
    "Operations & Process Improvement": [
        "Process Standardisation", "Operational Efficiency",
        "Quality Assurance", "SOP Development", "KPI Monitoring",
    ],
    "ERP & Software": [
        "SAP (Inventory & SCM Modules)", "Oracle Fusion Cloud SCM",
        "Microsoft Excel", "Microsoft Word", "Google Colab",
    ],
    "Leadership & Coordination": [
        "Team Training & Mentoring", "Cross-Functional Coordination",
        "Vendor Liaison", "Stakeholder Communication",
        "POSH Compliance Training",
    ],
    "Analytical & Research": [
        "Data Collection & Analysis", "Survey Design (Google Forms)",
        "Report Preparation", "Published Research",
    ],
}

# Three real roles. Tailoring rewrites the BULLETS within these,
# but never adds/removes roles or changes company/dates/title.
BASE_EXPERIENCE = [
    {
        "role_title": "Senior Graduate — Operations & Supply Chain",
        "company": "Reliance Retail (Quick Supply Chain Division)",
        "location": "Delhi, India",
        "dates": "Aug 2022 – Dec 2024",
        "responsibilities": [
            "Managed daily warehouse operations including inbound receipts, outbound dispatch, and stock reconciliation for a fulfilment centre servicing 250+ retail stores and e-commerce orders.",
            "Oversaw inventory accuracy across ~5,000 SKUs through systematic cycle counts and stock audits, maintaining accuracy levels above 97%.",
            "Coordinated with procurement, logistics, and store operations teams to reduce order dispatch delays by ~15%, ensuring on-time delivery targets were consistently met.",
            "Streamlined inbound shipment processing workflows, cutting average goods-in turnaround time by ~20% through improved staging and documentation procedures.",
            "Trained and mentored a team of 20+ warehouse staff on operational processes, safety protocols, hygiene standards, and POSH compliance, with a focus on onboarding female employees.",
        ],
        "achievements": [
            "Promoted from Graduate Trainee to Senior Graduate within 6 months based on strong operational performance and leadership.",
            "Recognised internally for improving dispatch reliability and warehouse floor discipline across the fulfilment centre.",
        ],
    },
    {
        "role_title": "Logistics Intern",
        "company": "Om Logistics",
        "location": "Delhi, India",
        "dates": "Jun 2021 – Aug 2021",
        "responsibilities": [
            "Tracked and monitored consignment movements across multiple routes, identifying and resolving shipment delays to maintain delivery timelines.",
            "Coordinated with vendors and internal warehouse teams to streamline incoming shipment processing and improve goods receipt accuracy.",
            "Assisted in shipment clearance procedures, reducing documentation bottlenecks and improving clearance turnaround by ~10%.",
            "Verified incoming inventory against purchase orders and maintained accurate records of ~200+ weekly consignments.",
        ],
        "achievements": [],
    },
    {
        "role_title": "Operations Intern",
        "company": "Shubh Consultants & Technocrats LLP",
        "location": "Delhi, India",
        "dates": "Jun 2022 – Jul 2022",
        "responsibilities": [
            "Supported day-to-day project coordination and documentation activities across multiple consulting engagements.",
            "Maintained project records, performed data entry, and organised operational information to ensure smooth workflow across teams.",
            "Gained practical exposure to structured project management processes and cross-functional team coordination in a professional consulting environment.",
        ],
        "achievements": [],
    },
]

# Education, certifications, additional info — NEVER tailored.
# Always rendered as-is.
BASE_EDUCATION = [
    {
        "degree": "MSc in Management (Strategy)",
        "institution": "Dublin City University (DCU), Dublin, Ireland",
        "dates": "Jan 2025 – Mar 2026",
        "grade": "Grade: 2:1",
        "extra": "Dissertation: Impact of Social Media on Decision-Making and Emotional Well-Being — primary data collection via surveys, analysis using Excel and Google Colab.",
    },
    {
        "degree": "BBA in Logistics & Supply Chain Management",
        "institution": "Galgotias University, Greater Noida, India",
        "dates": "May 2019 – May 2022",
        "grade": "GPA: 9.2/10 | Silver Medallist (Top 2)",
        "extra": "Published research paper on supply chain management challenges, analysing operational inefficiencies and proposing improvement frameworks.",
    },
]

BASE_CERTIFICATIONS = [
    "Oracle Fusion Cloud Applications SCM Process Essentials Certified (Rel 1) — Oracle University, November 2025",
    "Forage Virtual Experience Programme — Client Analysis, Sustainability Solutions & Fitment Matrix Presentation, September 2025",
    "Processes in SAP S/4HANA Extended Warehouse Management (EWM) — In Progress",
]

BASE_ADDITIONAL_INFO = [
    "Languages: English (Fluent), Hindi (Native)",
    "Awards: DCU Scholarship Recipient (€2,000); Silver Medal — BBA Graduation (Top 2)",
    "Volunteer & Extracurricular: CRY (NGO) Volunteer; Marketing Club Member; NCC B Certificate Holder",
    "Currently Learning: Six Sigma Green Belt, PMP (Project Management Professional)",
    "Work Authorisation: Stamp 1G. Eligible for full-time employment in Ireland.",
]


def build_base_resume_text() -> str:
    """Compose Praghya's base resume as plain text from the constants above.
    This is what pre-fills the 'Base Resume' box in the UI so she can see
    and edit what's being sent to the model."""
    lines = []
    lines.append(CANDIDATE_NAME)
    lines.append(CANDIDATE_TAGLINE)
    lines.append(CANDIDATE_CONTACT)
    lines.append("")

    lines.append("Professional Profile")
    lines.append(
        "Operations and supply chain professional with over 2 years of experience "
        "in warehouse management, inventory control, and logistics coordination "
        "within large-scale retail environments. Held a Senior Graduate role at "
        "Reliance Retail, one of India's largest retail conglomerates, overseeing "
        "end-to-end fulfilment operations across 50+ stores. Holds an MSc in "
        "Management (Strategy) from Dublin City University and a BBA in Logistics "
        "& Supply Chain Management (9.2/10 GPA, Silver Medallist). Certified in "
        "Oracle Fusion Cloud SCM. Seeking supply chain analyst, operations, and "
        "logistics coordinator roles in the Irish market."
    )
    lines.append("")

    lines.append("Key Skills / Tools & Technologies")
    for cat, skill_list in BASE_SKILLS.items():
        lines.append(f"- {cat}: {', '.join(skill_list)}")
    lines.append("")

    lines.append("Professional Experience")
    for role in BASE_EXPERIENCE:
        header = f"{role['role_title']} | {role['company']} | {role['location']} | {role['dates']}"
        lines.append(header)
        for r in role["responsibilities"]:
            lines.append(f"- {r}")
        if role["achievements"]:
            lines.append("Achievements:")
            for a in role["achievements"]:
                lines.append(f"- {a}")
        lines.append("")

    lines.append("Education")
    for edu in BASE_EDUCATION:
        lines.append(edu["degree"])
        lines.append(f"{edu['institution']} | {edu['dates']} | {edu['grade']}")
        if edu.get("extra"):
            lines.append(edu["extra"])
        lines.append("")

    lines.append("Certifications")
    for c in BASE_CERTIFICATIONS:
        lines.append(f"- {c}")
    lines.append("")

    lines.append("Additional Information")
    for a in BASE_ADDITIONAL_INFO:
        lines.append(f"- {a}")

    return "\n".join(lines)


PRAGHYA_BASE_RESUME = build_base_resume_text()


# ═══════════════════════════════════════════════════════════════════
# 3. SAFETY: BANNED SKILLS (Praghya does NOT have these)
# Used as a final scrub on tailored output. We don't fail — we just strip.
# ═══════════════════════════════════════════════════════════════════

BANNED_SKILLS = {
    # Programming
    "python", "sql", "r programming", "javascript", "java", "c++", "c#", "golang", "rust",
    # BI / Viz
    "power bi", "powerbi", "tableau", "looker", "qlik", "qlikview", "data studio",
    # Advanced Excel
    "vba", "macros", "advanced excel",
    # Cloud / DBs
    "aws", "azure", "gcp", "google cloud platform",
    "postgresql", "mysql", "mongodb", "redis", "snowflake", "bigquery",
    # Data Science / ML
    "machine learning", "deep learning", "data science", "nlp",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    # Certs she's only "in progress" with — must not appear as completed
    "six sigma certified", "six sigma black belt", "six sigma green belt certified",
    "pmp certified", "prince2 certified",
    # DevOps
    "docker", "kubernetes", "ci/cd", "terraform",
    # Frontend frameworks
    "react", "angular", "node.js", "vue.js",
}


# ═══════════════════════════════════════════════════════════════════
# 4. PROMPT — single, focused, no over-engineering
# ═══════════════════════════════════════════════════════════════════

ASTRA_PROMPT = """You are Astra, a resume tailoring engine for Praghya Prakhar — a Supply Chain & Operations professional based in Dublin.

Your job: take Praghya's BASE RESUME and the JOB DESCRIPTION, and produce a tailored version that mirrors the JD's language and priorities, while staying 100% truthful.

═══ CANDIDATE FACTS YOU CANNOT INVENT ═══

Praghya's REAL skills:
- ERP / Software: SAP (Inventory & SCM Modules — daily use at Reliance), Oracle Fusion Cloud SCM (certified Nov 2025), Microsoft Excel (basic-intermediate), Microsoft Word, Google Colab (basic).
- Supply Chain: Inventory control, order fulfilment, warehouse operations, inbound/outbound logistics, stock auditing, dispatch coordination, cycle counting, goods receipt verification.
- Operations: Process standardisation, SOP development, KPI monitoring, quality assurance.
- Leadership: Team training & mentoring, cross-functional coordination, vendor liaison, stakeholder communication, POSH compliance training.
- Analytical: Data collection via surveys (Google Forms), report preparation, published research on SCM.

Praghya does NOT have, and you must NEVER claim she does:
- Programming: Python, SQL, R, JavaScript, Java, C++.
- BI tools: Power BI, Tableau, Looker, Qlik.
- Advanced Excel: VBA, macros, complex pivot/array formulas.
- Cloud: AWS, Azure, GCP.
- Databases: PostgreSQL, MySQL, MongoDB, Snowflake.
- Data science / ML / deep learning.
- Six Sigma or PMP certification (currently learning, NOT certified).
- Any Irish professional work experience.

If the JD demands Python / SQL / Power BI as must-have, do NOT add them. The resume will simply be a weaker match for that role — that's fine. Honesty is non-negotiable.

═══ YOUR TASK — RETURN A JSON OBJECT WITH THIS EXACT SHAPE ═══

{
  "candidate_title": "<job-title-style line directly under the name. Mirror the JD's role title where possible. Examples: 'Supply Chain Analyst', 'Logistics Coordinator', 'Operations Analyst'. Default to 'Supply Chain & Operations Professional' if unclear.>",

  "summary": "<EXACTLY 4-5 sentences. Natural flow, no choppy listing. Each sentence carries weight:
    Sentence 1: Who she is (role identity matched to JD) + years of experience (use '2+ years' or 'over 2 years' — never inflate).
    Sentence 2: Strongest credential — Reliance Retail fulfilment ops for 50+ stores, with one concrete metric (97% inventory accuracy OR 15% dispatch delay reduction OR 20% turnaround improvement — pick the one most relevant to the JD).
    Sentence 3: Education weight — MSc Management (Strategy) from DCU and BBA in Logistics & SCM (9.2/10 GPA, Silver Medallist).
    Sentence 4: Oracle Fusion Cloud SCM certification + which capabilities/tools from the JD she brings.
    Sentence 5 (optional): One line connecting her profile to the target role/company.
   Avoid robotic phrasing. No 'leveraging', 'utilizing', 'spearheading', 'passionate about', 'committed to excellence'. Write like a confident human.>",

  "skills_additions": {
    "<existing category name>": ["<JD-relevant skill she actually has>", "..."],
    "...": []
  },

  "experience_bullets": [
    {
      "company": "Reliance Retail (Quick Supply Chain Division)",
      "responsibilities": ["<5 rewritten bullets>"],
      "achievements": ["<2 rewritten achievement bullets>"]
    },
    {
      "company": "Om Logistics",
      "responsibilities": ["<4 rewritten bullets>"],
      "achievements": []
    },
    {
      "company": "Shubh Consultants & Technocrats LLP",
      "responsibilities": ["<3 rewritten bullets>"],
      "achievements": []
    }
  ],

  "target_company": "<company name from JD, or 'Company' if not stated>"
}

═══ RULES FOR EACH FIELD ═══

SKILLS_ADDITIONS:
- The keys MUST be one of: "Supply Chain Management", "Operations & Process Improvement", "ERP & Software", "Leadership & Coordination", "Analytical & Research".
- Add ONLY skills that appear in the JD AND that Praghya genuinely has (or has equivalent demonstrated experience).
- Examples of valid additions: "Demand Planning", "S&OP awareness", "3PL Coordination", "ERP Reporting", "Stakeholder Reporting", "Supplier Onboarding", "Goods-In Documentation".
- Do NOT add: Python, SQL, Power BI, Tableau, AWS, Azure, GCP, advanced analytics, machine learning, VBA. Even if the JD asks for them.
- If a category has no relevant additions, return an empty list for that category.
- 0-3 additions per category. Quality over quantity.

EXPERIENCE_BULLETS:
- Rewrite each bullet so its WORDING aligns with the JD, but every concrete claim must come from the BASE responsibilities/achievements provided.
- Every metric stays IDENTICAL: 50+ stores, ~5,000 SKUs, 97% accuracy, ~15%, ~20%, 20+ staff, ~10%, ~200+, 6 months. Never change a number.
- Reliance Retail: keep 5 responsibility bullets and 2 achievement bullets.
- Om Logistics: keep 4 responsibility bullets, 0 achievement bullets.
- Shubh Consultants: keep 3 responsibility bullets, 0 achievement bullets.
- Each bullet starts with a strong past-tense verb: managed, oversaw, coordinated, tracked, maintained, reduced, improved, trained, processed, verified, supported, streamlined.
- Do NOT introduce new tools, sectors, or claims not in the base bullets. You may RE-LABEL an existing claim using a JD-aligned synonym (e.g., "warehouse operations" → "distribution centre operations" if JD uses that language) but the underlying fact must match.
- No em dashes inside bullets. Use commas or periods.

SUMMARY:
- 4-5 sentences. Count them.
- Mention the target company by name if it appears clearly in the JD.
- One concrete metric from her real experience.
- Confident but not boastful.

CANDIDATE_TITLE:
- Match the JD's role title verbatim where reasonable (max 8 words).
- Drop seniority modifiers ("Senior", "Lead") if present in the JD title — Praghya is entry-to-junior level.

═══ OUTPUT ═══
Return ONLY the JSON object. No prose, no markdown fences, no explanation.
"""


COVER_LETTER_PROMPT = """You are Praghya Prakhar writing a cover letter for the role described below.
Write in first person. Sound like a real human, not a corporate template.

═══ CONTEXT ═══
Praghya is an entry-to-junior level Supply Chain & Operations professional based in Dublin.
- 2+ years at Reliance Retail (Quick Supply Chain Division), Delhi: warehouse ops for 50+ stores, 97% inventory accuracy across ~5,000 SKUs, ~15% reduction in dispatch delays, ~20% reduction in goods-in turnaround time, trained 20+ warehouse staff.
- Promoted from Graduate Trainee to Senior Graduate within 6 months at Reliance.
- Internships at Om Logistics (consignment tracking, ~10% clearance turnaround improvement, ~200+ weekly consignments verified) and Shubh Consultants (project coordination).
- MSc in Management (Strategy) from Dublin City University.
- BBA in Logistics & Supply Chain Management from Galgotias University, 9.2/10 GPA, Silver Medallist (Top 2).
- Oracle Fusion Cloud SCM certified (Nov 2025).
- Eligible for full-time employment in Ireland (Stamp 1G).

═══ HARD RULES ═══

DO NOT mention skills she does not have:
- No Python, SQL, R, JavaScript, Java
- No Power BI, Tableau, Looker, Qlik
- No advanced Excel (no VBA, no macros)
- No AWS, Azure, GCP, databases, cloud platforms
- No machine learning, data science, advanced analytics
- No Six Sigma certification or PMP certification (she is currently learning, NOT certified)

DO NOT inflate experience:
- She has 2+ years of experience. Not 3, not 5.
- Her experience is in retail fulfilment / warehouse ops / logistics. If the JD is in pharma, construction, or another sector, FRAME her retail experience as transferable. Never claim sector-specific experience she does not have.

═══ BANNED PHRASES ═══
Do not use any of these (they make the letter sound AI-generated or template-y):
- "I am writing to express my interest"
- "I am excited to apply"
- "Please find my resume attached"
- "I believe I am a perfect fit"
- "passionate about", "driven by", "committed to excellence"
- "leveraging", "utilizing", "harnessing"
- "showcasing", "highlighting", "demonstrating"
- "testament to", "underscores", "pivotal", "tapestry", "realm"
- "seamless", "innovative", "groundbreaking", "cutting-edge"
- "at the forefront of", "at the intersection of"
- Three-adjective chains ("scalable, reliable, and efficient")

═══ STRUCTURE ═══
4 short paragraphs, plain text, no markdown, no headers, no bold.

Paragraph 1 (Hook — 2-3 sentences):
Open by referring to a SPECIFIC operational challenge or focus from the JD (not the company in general). Show you actually read what they wrote. Example openers:
- "Keeping inventory accuracy above 95% across hundreds of SKUs is harder than most people think — it depends entirely on the cycle counting discipline behind the scenes."
- "Coordinating 3PL deliveries against rolling forecast changes is exactly the kind of problem I worked on every day at Reliance Retail."
Mention the role title from the JD and the company name in this paragraph.

Paragraph 2 (War story — 3-4 sentences):
Pick the BEST matching war story from her real experience, based on the JD's focus:
- If the JD is heavy on inventory/SKU management → use the 97% inventory accuracy + 5,000 SKU cycle counting story.
- If the JD is about efficiency/process improvement → use the 20% goods-in turnaround OR 15% dispatch delay reduction story.
- If the JD is about people leadership / training / onboarding → use the "trained 20+ warehouse staff" + "Graduate Trainee to Senior Graduate in 6 months" story.
- If the JD is about vendor / 3PL / supplier coordination → use the Om Logistics 200+ weekly consignments + 10% clearance turnaround story.
- If the JD is a graduate programme → lead with the MSc from DCU + BBA Silver Medal + Oracle certification.
Use exact metrics. Never round or change numbers.

Paragraph 3 (Education + Certification — 2 sentences):
Briefly mention the MSc from DCU and the Oracle Fusion Cloud SCM certification (or BBA Silver Medal if the role is graduate-level). Connect the certification or coursework to a tool or process the JD asks for.

Paragraph 4 (Close — 2 sentences):
Brief, confident close. Express interest in discussing the role. End with "Thank you," on its own line, then "Praghya Prakhar" on the next line.

═══ STYLE ═══
- Vary sentence length. Mix short with longer.
- No em dashes. Use commas or periods.
- Use plain verbs: managed, coordinated, tracked, maintained, reduced, improved, trained, processed, verified.
- She is entry-level. Confident, not arrogant. Eager to learn, not desperate.
- Length: 230-330 words total in the letter body (excluding "Thank you, Praghya Prakhar" sign-off).

═══ OUTPUT ═══
Return ONLY the letter body as plain text. No "Dear Hiring Manager" greeting (the renderer adds it). No subject line. No address blocks. No markdown. No bold. No code fences.
Start directly with paragraph 1.
End with "Thank you," on its own line and "Praghya Prakhar" on the next line.
"""


# ═══════════════════════════════════════════════════════════════════
# 5. SCHEMA
# ═══════════════════════════════════════════════════════════════════

class ExperienceBullets(BaseModel):
    company: str
    responsibilities: List[str]
    achievements: List[str] = Field(default_factory=list)


class SkillsAdditions(BaseModel):
    supply_chain_management: List[str] = Field(default_factory=list, alias="Supply Chain Management")
    operations_process: List[str] = Field(default_factory=list, alias="Operations & Process Improvement")
    erp_software: List[str] = Field(default_factory=list, alias="ERP & Software")
    leadership: List[str] = Field(default_factory=list, alias="Leadership & Coordination")
    analytical: List[str] = Field(default_factory=list, alias="Analytical & Research")

    class Config:
        populate_by_name = True


class TailoredOutput(BaseModel):
    candidate_title: str
    summary: str
    skills_additions: dict  # {category_name: [skills]}
    experience_bullets: List[ExperienceBullets]
    target_company: str = "Company"


# ═══════════════════════════════════════════════════════════════════
# 6. CALL GEMINI
# ═══════════════════════════════════════════════════════════════════

def call_gemini(api_key: str, jd_text: str, resume_text: str = "") -> dict:
    """Single API call. JSON mode. Returns parsed dict or {'error': ...}.
    resume_text is Praghya's base resume — passed through so the model
    sees what she sees in the UI box and respects any edits she made there.
    Falls back to the constants-derived default if not supplied."""
    if not api_key:
        return {"error": "Missing GOOGLE_API_KEY."}
    if not jd_text or not jd_text.strip():
        return {"error": "Job description is empty."}

    if not resume_text or not resume_text.strip():
        resume_text = PRAGHYA_BASE_RESUME

    client = genai.Client(api_key=api_key)
    prompt = (
        f"{ASTRA_PROMPT}\n\n"
        f"═══ BASE RESUME ═══\n{resume_text}\n\n"
        f"═══ JOB DESCRIPTION ═══\n{jd_text}"
    )

    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,  # low for reliability
            ),
        )
        text = response.text.strip()
        # Strip code fences if model wrapped them despite JSON mode
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {"error": f"Could not parse JSON from model: {e}"}
    except Exception as e:
        return {"error": f"Generation error: {e}"}


def generate_cover_letter(api_key: str, resume_data: dict, jd_text: str) -> str:
    """Single API call. Plain text mode. Returns letter body or error message starting with 'ERROR:'."""
    if not api_key:
        return "ERROR: Missing GOOGLE_API_KEY."
    if not jd_text or not jd_text.strip():
        return "ERROR: Job description is empty."

    client = genai.Client(api_key=api_key)

    # Pass the tailored resume context so the cover letter aligns with what the JD-tailored CV says.
    resume_context = (
        f"Tailored role title: {resume_data.get('candidate_title', '')}\n"
        f"Target company: {resume_data.get('target_company', '')}\n"
        f"Tailored summary: {resume_data.get('summary', '')}"
    )

    prompt = (
        f"{COVER_LETTER_PROMPT}\n\n"
        f"═══ TAILORED RESUME CONTEXT ═══\n{resume_context}\n\n"
        f"═══ JOB DESCRIPTION ═══\n{jd_text}"
    )

    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.6),
        )
        text = (response.text or "").strip()
        # Strip code fences if any
        if text.startswith("```"):
            text = re.sub(r"^```(?:\w+)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        # Strip any "Dear ..." greeting if the model added one despite instructions
        text = re.sub(r"^dear\s+[^\n]+\n+", "", text, flags=re.IGNORECASE)
        # Final scrub of banned skills (safety net)
        text = scrub_banned_from_text(text)
        return text
    except Exception as e:
        return f"ERROR: Cover letter generation failed: {e}"


# ═══════════════════════════════════════════════════════════════════
# 7. ASSEMBLE: merge model output with base resume into final structure
# ═══════════════════════════════════════════════════════════════════

def is_banned(skill: str) -> bool:
    s = skill.lower().strip()
    return any(b in s for b in BANNED_SKILLS)


def scrub_banned_from_text(text: str) -> str:
    """Strip any banned skill mentions from a free-text string (summary, bullets)."""
    cleaned = text
    for b in BANNED_SKILLS:
        # Remove standalone occurrences with surrounding context cleanup
        pattern = re.compile(r"\b" + re.escape(b) + r"\b[, ]*", re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    # Tidy up double commas, double spaces, trailing punctuation
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.])", r"\1", cleaned)
    return cleaned.strip()


def merge_skills(additions: dict) -> dict:
    """Combine BASE_SKILLS with model additions. Banned terms are dropped."""
    final = {}
    for category, base_list in BASE_SKILLS.items():
        # Start with base (always present)
        merged = list(base_list)
        added = additions.get(category, []) if isinstance(additions, dict) else []
        if not isinstance(added, list):
            added = []
        # Append additions that are (a) not already present, (b) not banned
        existing_lower = {s.lower() for s in merged}
        for skill in added:
            if not isinstance(skill, str):
                continue
            s = skill.strip()
            if not s:
                continue
            if is_banned(s):
                continue
            if s.lower() in existing_lower:
                continue
            merged.append(s)
            existing_lower.add(s.lower())
        final[category] = merged
    return final


def merge_experience(model_bullets: list) -> list:
    """For each base role, replace bullets with the model's tailored versions
    (after scrubbing). If the model dropped a role or returned the wrong count,
    fall back to base bullets so the resume stays complete."""
    by_company = {}
    if isinstance(model_bullets, list):
        for item in model_bullets:
            if isinstance(item, dict) and item.get("company"):
                by_company[item["company"]] = item

    final = []
    for base_role in BASE_EXPERIENCE:
        company = base_role["company"]
        tailored = by_company.get(company, {})
        tailored_resps = tailored.get("responsibilities") or []
        tailored_achs = tailored.get("achievements") or []

        # Scrub banned terms; drop empty
        clean_resps = [scrub_banned_from_text(r) for r in tailored_resps if isinstance(r, str)]
        clean_resps = [r for r in clean_resps if r.strip()]

        clean_achs = [scrub_banned_from_text(a) for a in tailored_achs if isinstance(a, str)]
        clean_achs = [a for a in clean_achs if a.strip()]

        # Fallback: if tailoring lost too many bullets, use base
        expected_resp_count = len(base_role["responsibilities"])
        expected_ach_count = len(base_role["achievements"])

        if len(clean_resps) < max(1, expected_resp_count - 1):
            clean_resps = list(base_role["responsibilities"])
        if expected_ach_count > 0 and len(clean_achs) < expected_ach_count:
            clean_achs = list(base_role["achievements"])

        final.append({
            "role_title": base_role["role_title"],
            "company": base_role["company"],
            "location": base_role["location"],
            "dates": base_role["dates"],
            "responsibilities": clean_resps,
            "achievements": clean_achs,
        })
    return final


def assemble_resume(model_output: dict) -> dict:
    """Combine model output + base facts into a fully-populated resume dict."""
    summary = scrub_banned_from_text(model_output.get("summary", "") or "")
    if not summary or len(summary.split()) < 20:
        # Fallback summary if model failed
        summary = (
            "Operations and supply chain professional with over 2 years of hands-on "
            "experience in warehouse management, inventory control, and logistics "
            "coordination. Held a Senior Graduate role at Reliance Retail, overseeing "
            "fulfilment operations across 50+ stores and maintaining 97% inventory "
            "accuracy. Holds an MSc in Management (Strategy) from Dublin City "
            "University and a BBA in Logistics & Supply Chain Management with a "
            "9.2/10 GPA and Silver Medal. Oracle Fusion Cloud SCM certified, with "
            "working knowledge of SAP and Excel for daily operations and reporting."
        )

    return {
        "candidate_name": CANDIDATE_NAME,
        "candidate_title": (model_output.get("candidate_title") or CANDIDATE_TAGLINE).strip(),
        "contact_info": CANDIDATE_CONTACT,
        "summary": summary,
        "skills": merge_skills(model_output.get("skills_additions", {}) or {}),
        "experience": merge_experience(model_output.get("experience_bullets", []) or []),
        "education": list(BASE_EDUCATION),
        "certifications": list(BASE_CERTIFICATIONS),
        "additional_info": list(BASE_ADDITIONAL_INFO),
        "target_company": (model_output.get("target_company") or "Company").strip(),
    }


# ═══════════════════════════════════════════════════════════════════
# 8. DOCX RENDERER — clean, ATS-friendly, single-column, no tables
# ═══════════════════════════════════════════════════════════════════

def _set_font(run, size, bold=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    try:
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    except Exception:
        pass


def _add_section_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    _set_font(p.add_run(text), 12, bold=True)


def _add_bullet(doc, text, bold_prefix=None, justify=True):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY if justify else WD_PARAGRAPH_ALIGNMENT.LEFT
    p.paragraph_format.space_after = Pt(0)
    if bold_prefix:
        _set_font(p.add_run(bold_prefix), 12, bold=True)
    _set_font(p.add_run(text), 12)


def render_docx(data: dict) -> bytes:
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.5)

    # ─── Header ───
    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(data["candidate_name"])
    run.font.all_caps = True
    _set_font(run, 28, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    _set_font(p.add_run(data["candidate_title"]), 14, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    _set_font(p.add_run(data["contact_info"]), 11, bold=True)

    # ─── Professional Profile ───
    _add_section_heading(doc, "Professional Profile")
    p = doc.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    p.paragraph_format.space_after = Pt(0)
    _set_font(p.add_run(data["summary"]), 12)

    # ─── Skills ───
    _add_section_heading(doc, "Key Skills / Tools & Technologies")
    for cat, skill_list in data["skills"].items():
        _add_bullet(doc, ", ".join(skill_list), bold_prefix=f"{cat}: ")

    # ─── Experience ───
    _add_section_heading(doc, "Professional Experience")
    for role in data["experience"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        header = f"{role['role_title']} | {role['company']} | {role['location']} | {role['dates']}"
        _set_font(p.add_run(header), 12, bold=True)

        for resp in role["responsibilities"]:
            _add_bullet(doc, resp)

        if role["achievements"]:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(0)
            _set_font(p.add_run("Achievements:"), 12, bold=True)
            for ach in role["achievements"]:
                _add_bullet(doc, ach)

    # ─── Education ───
    _add_section_heading(doc, "Education")
    for edu in data["education"]:
        # Degree line (bold)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(0)
        _set_font(p.add_run(edu["degree"]), 12, bold=True)

        # Institution / dates / grade
        meta = f"{edu['institution']} | {edu['dates']} | {edu['grade']}"
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        _set_font(p.add_run(meta), 12)

        if edu.get("extra"):
            p = doc.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            p.paragraph_format.space_after = Pt(0)
            _set_font(p.add_run(edu["extra"]), 12)

    # ─── Certifications ───
    _add_section_heading(doc, "Certifications")
    for cert in data["certifications"]:
        _add_bullet(doc, cert)

    # ─── Additional Information ───
    _add_section_heading(doc, "Additional Information")
    for line in data["additional_info"]:
        _add_bullet(doc, line)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


# ═══════════════════════════════════════════════════════════════════
# 9. PDF RENDERER — same content, ATS-friendly, single column
# ═══════════════════════════════════════════════════════════════════

def _esc(t):
    if t is None:
        return ""
    return escape(str(t))


def render_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()

    sn = ParagraphStyle("N", parent=styles["Normal"], fontName="Times-Roman",
                        fontSize=12, leading=14, alignment=TA_JUSTIFY, spaceAfter=0)
    sn_left = ParagraphStyle("NL", parent=styles["Normal"], fontName="Times-Roman",
                             fontSize=12, leading=14, alignment=TA_LEFT, spaceAfter=0)
    sh_name = ParagraphStyle("HN", parent=styles["Normal"], fontName="Times-Bold",
                             fontSize=22, leading=26, alignment=TA_CENTER, spaceAfter=0)
    sh_title = ParagraphStyle("HT", parent=styles["Normal"], fontName="Times-Bold",
                              fontSize=14, leading=16, alignment=TA_CENTER, spaceAfter=0)
    sh_contact = ParagraphStyle("HC", parent=styles["Normal"], fontName="Times-Bold",
                                fontSize=11, leading=13, alignment=TA_CENTER, spaceAfter=6)
    s_sec = ParagraphStyle("Sec", parent=styles["Normal"], fontName="Times-Bold",
                           fontSize=12, leading=14, alignment=TA_LEFT,
                           spaceBefore=10, spaceAfter=2)

    el = []

    # Header
    el.append(Paragraph(_esc(data["candidate_name"]).upper(), sh_name))
    el.append(Paragraph(_esc(data["candidate_title"]), sh_title))
    el.append(Paragraph(_esc(data["contact_info"]), sh_contact))

    # Summary
    el.append(Paragraph("Professional Profile", s_sec))
    el.append(Paragraph(_esc(data["summary"]), sn))

    # Skills
    el.append(Paragraph("Key Skills / Tools &amp; Technologies", s_sec))
    skill_items = []
    for cat, skill_list in data["skills"].items():
        text = f"<b>{_esc(cat)}:</b> {_esc(', '.join(skill_list))}"
        skill_items.append(ListItem(Paragraph(text, sn_left), leftIndent=0))
    if skill_items:
        el.append(ListFlowable(skill_items, bulletType="bullet",
                               start="\u2022", leftIndent=15))

    # Experience
    el.append(Paragraph("Professional Experience", s_sec))
    for role in data["experience"]:
        header = f"{role['role_title']} | {role['company']} | {role['location']} | {role['dates']}"
        el.append(Paragraph(f"<b>{_esc(header)}</b>", sn_left))
        el.append(Spacer(1, 2))
        items = [ListItem(Paragraph(_esc(r), sn), leftIndent=0)
                 for r in role["responsibilities"] if r.strip()]
        if items:
            el.append(ListFlowable(items, bulletType="bullet", start="\u2022", leftIndent=15))
        if role["achievements"]:
            el.append(Paragraph("<b>Achievements:</b>", sn_left))
            ach_items = [ListItem(Paragraph(_esc(a), sn), leftIndent=0)
                         for a in role["achievements"] if a.strip()]
            if ach_items:
                el.append(ListFlowable(ach_items, bulletType="bullet",
                                       start="\u2022", leftIndent=25))
        el.append(Spacer(1, 4))

    # Education
    el.append(Paragraph("Education", s_sec))
    for edu in data["education"]:
        el.append(Paragraph(f"<b>{_esc(edu['degree'])}</b>", sn_left))
        meta = f"{edu['institution']} | {edu['dates']} | {edu['grade']}"
        el.append(Paragraph(_esc(meta), sn_left))
        if edu.get("extra"):
            el.append(Paragraph(_esc(edu["extra"]), sn))
        el.append(Spacer(1, 4))

    # Certifications
    el.append(Paragraph("Certifications", s_sec))
    cert_items = [ListItem(Paragraph(_esc(c), sn_left), leftIndent=0)
                  for c in data["certifications"]]
    if cert_items:
        el.append(ListFlowable(cert_items, bulletType="bullet",
                               start="\u2022", leftIndent=15))

    # Additional
    el.append(Paragraph("Additional Information", s_sec))
    add_items = [ListItem(Paragraph(_esc(a), sn_left), leftIndent=0)
                 for a in data["additional_info"]]
    if add_items:
        el.append(ListFlowable(add_items, bulletType="bullet",
                               start="\u2022", leftIndent=15))

    doc.build(el)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
# 9b. COVER LETTER DOCX RENDERER
# ═══════════════════════════════════════════════════════════════════

def render_cover_letter_docx(letter_body: str, target_company: str = "") -> bytes:
    """Render a cover letter as a clean DOCX. Body is passed in as plain text;
    the renderer adds the candidate header, date, greeting, and sign-off."""
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1.0)

    def _line(text, bold=False, space_after=0, align=WD_PARAGRAPH_ALIGNMENT.LEFT):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        if text:
            _set_font(p.add_run(text), 11, bold=bold)
        return p

    # ─── Sender header ───
    _line(CANDIDATE_NAME, bold=True, space_after=0)
    # Split contact info: "Dublin, Ireland | +353 ... | email | linkedin"
    for piece in [c.strip() for c in CANDIDATE_CONTACT.split("|")]:
        if piece:
            _line(piece, space_after=0)

    _line("", space_after=10)  # gap

    # ─── Date ───
    today = datetime.date.today().strftime("%d %B %Y")
    _line(today, space_after=14)

    # ─── Greeting ───
    if target_company.strip():
        greeting = f"Dear Hiring Team at {target_company.strip()},"
    else:
        greeting = "Dear Hiring Team,"
    _line(greeting, space_after=10)

    # ─── Body paragraphs ───
    # Strip any sign-off the model may have included so we don't render it twice
    body = letter_body.strip()
    sign_off_pattern = re.compile(
        r"\n+(thank you,?|regards,?|sincerely,?|kind regards,?|best regards,?)\s*\n+praghya prakhar\s*$",
        re.IGNORECASE,
    )
    # Detect sign-off, render it separately for nicer spacing
    sign_off_match = sign_off_pattern.search(body)
    if sign_off_match:
        body_main = body[: sign_off_match.start()].strip()
        sign_word = sign_off_match.group(1).rstrip(",").strip().capitalize()
    else:
        body_main = body
        sign_word = "Thank you"

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_main) if p.strip()]
    if not paragraphs:
        # Treat single-line newline-separated text as one paragraph each
        paragraphs = [p.strip() for p in body_main.split("\n") if p.strip()]

    for para in paragraphs:
        # Collapse internal newlines into a single space within a paragraph
        clean_para = re.sub(r"\s*\n\s*", " ", para)
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        p.paragraph_format.space_after = Pt(10)
        _set_font(p.add_run(clean_para), 11)

    # ─── Sign-off ───
    _line("", space_after=6)
    _line(f"{sign_word},", space_after=18)
    _line(CANDIDATE_NAME, space_after=0)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


# ═══════════════════════════════════════════════════════════════════
# 10. STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon="📦",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1.5rem;}
    div.stButton > button:first-child {border-radius: 6px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

# Session state
if "tailored" not in st.session_state:
    st.session_state["tailored"] = None
if "saved_jd" not in st.session_state:
    st.session_state["saved_jd"] = ""
if "saved_base" not in st.session_state:
    st.session_state["saved_base"] = PRAGHYA_BASE_RESUME
if "cover_letter" not in st.session_state:
    st.session_state["cover_letter"] = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    if GOOGLE_API_KEY:
        st.success("API key configured")
        api_key = GOOGLE_API_KEY
    else:
        st.warning("Add GOOGLE_API_KEY to Streamlit secrets, or paste it below.")
        api_key = st.text_input("Google API Key", type="password")

    st.divider()
    st.markdown("**Target roles:**")
    st.caption("Supply Chain Analyst · Operations Analyst · Logistics Coordinator · Inventory Analyst")

    st.divider()
    st.markdown(f"**Model:** `{GENERATION_MODEL}`")

    st.divider()
    if st.button("🗑️ Reset", use_container_width=True):
        st.session_state["tailored"] = None
        st.session_state["saved_jd"] = ""
        st.session_state["saved_base"] = PRAGHYA_BASE_RESUME
        st.session_state["cover_letter"] = None
        st.rerun()

    st.caption("Astra v2.0 — Praghya")

# Main UI
if not st.session_state["tailored"]:
    st.markdown(f"<h1 style='text-align: center;'>{PAGE_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #888;'>"
        "Paste a job description. Get a tailored, ATS-friendly resume.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_resume, col_jd = st.columns(2)

    with col_resume:
        st.subheader("📋 Base Resume")
        st.caption("Pre-filled with Praghya's profile. Edit only if you need a one-off tweak for this application.")
        base = st.text_area(
            "Base Resume",
            value=st.session_state["saved_base"],
            height=420,
            label_visibility="collapsed",
        )
        if st.button("↩️ Restore default base resume", use_container_width=True):
            st.session_state["saved_base"] = PRAGHYA_BASE_RESUME
            st.rerun()

    with col_jd:
        st.subheader("💼 Job Description")
        st.caption("Paste the full JD here.")
        jd = st.text_area(
            "Job Description",
            value=st.session_state["saved_jd"],
            height=420,
            label_visibility="collapsed",
            placeholder="Paste the full JD here…",
        )

    if st.button("✨ Generate Tailored Resume", type="primary", use_container_width=True):
        if not api_key:
            st.error("Need a Google API key to generate.")
        elif not jd.strip():
            st.warning("Please paste a job description.")
        elif not base.strip():
            st.warning("Base resume is empty. Click ‘Restore default base resume’ to bring it back.")
        else:
            st.session_state["saved_jd"] = jd
            st.session_state["saved_base"] = base
            with st.spinner("Tailoring resume to JD…"):
                model_out = call_gemini(api_key, jd, resume_text=base)
                if "error" in model_out:
                    st.error(model_out["error"])
                else:
                    final = assemble_resume(model_out)
                    st.session_state["tailored"] = final
                    st.rerun()

else:
    data = st.session_state["tailored"]

    # Top bar
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"## 🎯 Target: {data['target_company']}")
        st.caption(f"Tailored title: **{data['candidate_title']}**")
    with c2:
        if st.button("New JD", use_container_width=True):
            st.session_state["tailored"] = None
            st.session_state["saved_jd"] = ""
            st.session_state["cover_letter"] = None
            st.rerun()

    # Tabs: Preview | Edit | Cover Letter | Download
    tab_preview, tab_edit, tab_cover, tab_download = st.tabs(
        ["👀 Preview", "📝 Edit", "✍️ Cover Letter", "📥 Download"]
    )

    with tab_preview:
        st.subheader("Professional Profile")
        st.write(data["summary"])

        st.subheader("Key Skills / Tools & Technologies")
        for cat, skill_list in data["skills"].items():
            st.markdown(f"- **{cat}:** {', '.join(skill_list)}")

        st.subheader("Professional Experience")
        for role in data["experience"]:
            st.markdown(
                f"**{role['role_title']}** | {role['company']} | "
                f"{role['location']} | {role['dates']}"
            )
            for r in role["responsibilities"]:
                st.markdown(f"- {r}")
            if role["achievements"]:
                st.markdown("**Achievements:**")
                for a in role["achievements"]:
                    st.markdown(f"- {a}")

        st.subheader("Education")
        for edu in data["education"]:
            st.markdown(f"**{edu['degree']}**")
            st.markdown(f"{edu['institution']} | {edu['dates']} | {edu['grade']}")
            if edu.get("extra"):
                st.write(edu["extra"])

        st.subheader("Certifications")
        for c in data["certifications"]:
            st.markdown(f"- {c}")

        st.subheader("Additional Information")
        for a in data["additional_info"]:
            st.markdown(f"- {a}")

    with tab_edit:
        with st.form("edit_form"):
            data["candidate_title"] = st.text_input("Title under name", data["candidate_title"])
            data["summary"] = st.text_area("Summary", data["summary"], height=160)

            st.markdown("##### Skills (comma-separated per category)")
            for cat in list(data["skills"].keys()):
                joined = ", ".join(data["skills"][cat])
                edited = st.text_area(cat, joined, height=70, key=f"sk_{cat}")
                data["skills"][cat] = [s.strip() for s in edited.split(",") if s.strip()]

            st.markdown("##### Experience")
            for i, role in enumerate(data["experience"]):
                with st.expander(f"{role['role_title']} @ {role['company']}", expanded=False):
                    resps_text = "\n".join(role["responsibilities"])
                    new_resps = st.text_area("Responsibilities (one per line)",
                                             resps_text, height=180, key=f"r_{i}")
                    role["responsibilities"] = [
                        line.strip() for line in new_resps.split("\n") if line.strip()
                    ]
                    if role["achievements"] or i == 0:  # show achievements box for Reliance
                        achs_text = "\n".join(role["achievements"])
                        new_achs = st.text_area("Achievements (one per line)",
                                                achs_text, height=80, key=f"a_{i}")
                        role["achievements"] = [
                            line.strip() for line in new_achs.split("\n") if line.strip()
                        ]

            if st.form_submit_button("💾 Save edits", type="primary"):
                st.session_state["tailored"] = data
                st.success("Saved.")
                st.rerun()

    with tab_cover:
        st.caption(
            "A short, human-sounding cover letter using the war story that best matches the JD. "
            "Generated separately so it doesn't slow down resume tailoring."
        )

        cover_btn_label = "✨ Draft Cover Letter" if not st.session_state["cover_letter"] else "🔄 Re-draft Cover Letter"
        if st.button(cover_btn_label, type="primary"):
            if not api_key:
                st.error("Need a Google API key to generate.")
            elif not st.session_state["saved_jd"].strip():
                st.warning("No saved JD found. Generate the resume first.")
            else:
                with st.spinner("Picking the right war story, drafting…"):
                    cl = generate_cover_letter(api_key, data, st.session_state["saved_jd"])
                    if cl.startswith("ERROR:"):
                        st.error(cl)
                    else:
                        st.session_state["cover_letter"] = cl
                        st.rerun()

        if st.session_state["cover_letter"]:
            edited = st.text_area(
                "Cover letter (editable)",
                st.session_state["cover_letter"],
                height=420,
            )
            # Persist any manual edits the user makes here
            st.session_state["cover_letter"] = edited

            try:
                cl_bytes = render_cover_letter_docx(
                    st.session_state["cover_letter"],
                    target_company=data.get("target_company", ""),
                )
                company_safe = re.sub(r"[^A-Za-z0-9_-]", "_",
                                      (data["target_company"] or "Company").strip()) or "Company"
                st.download_button(
                    "📄 Download Cover Letter (.docx)",
                    data=cl_bytes,
                    file_name=f"CoverLetter_Praghya_Prakhar_{company_safe}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                )
            except Exception as e:
                st.error(f"Cover letter render error: {e}")

    with tab_download:
        company = data["target_company"] or "Company"
        company_safe = re.sub(r"[^A-Za-z0-9_-]", "_", company.strip()) or "Company"
        filename_base = f"Praghya_Prakhar_{company_safe}"

        st.text_input("Filename (no extension)", filename_base, key="fname")
        fname = st.session_state.get("fname", filename_base)

        c1, c2 = st.columns(2)
        try:
            docx_bytes = render_docx(data)
            c1.download_button(
                "📄 Word (.docx)",
                data=docx_bytes,
                file_name=f"{fname}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            c1.error(f"DOCX error: {e}")

        try:
            pdf_bytes = render_pdf(data)
            c2.download_button(
                "📕 PDF",
                data=pdf_bytes,
                file_name=f"{fname}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            c2.error(f"PDF error: {e}")
