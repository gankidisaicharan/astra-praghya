# Astra Resume Engine — Personalised for Praghya Prakhar (v1.1)
# Supply Chain & Operations ATS Optimisation Edition
# v1.1 upgrades: JD Pre-screener, Full-text hallucination scan, Score-driven re-generation
import streamlit as st
import json
import re
import io
import ast
import datetime
from typing import List

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API KEYS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    google_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    google_key = ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATION_MODEL = "gemini-2.5-flash-preview-05-20"
SCORING_MODEL = "gemini-2.0-flash-lite"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE_TITLE = "Astra — Praghya Prakhar"

PRAGHYA_BASE_RESUME = """PRAGHYA PRAKHAR
Supply Chain & Operations Professional
Dublin, Ireland | +353 89 263 0034 | pragyaprakhar2012@gmail.com | linkedin.com/in/praghya-prakhar-a9b016209

Professional Profile
Operations and supply chain professional with over 2 years of experience in warehouse management, inventory control, and logistics coordination within large-scale retail environments. Held a Senior Executive role at Reliance Retail, one of India's largest retail conglomerates, overseeing end-to-end fulfilment operations across 50+ stores. Holds an MSc in Management (Strategy) from Dublin City University and a BBA in Logistics & Supply Chain Management (9.2/10 GPA, Silver Medallist). Certified in Oracle Fusion Cloud SCM. Seeking supply chain analyst, operations, and logistics coordinator roles in the Irish market.

Key Skills/ Tools & Technologies
- Supply Chain Management: Inventory Control, Order Fulfilment, Warehouse Operations, Inbound/Outbound Logistics, Stock Auditing, Dispatch Coordination
- Operations & Process Improvement: Process Standardisation, Operational Efficiency, Quality Assurance, SOP Development, KPI Monitoring
- ERP & Software: SAP (Inventory & SCM Modules), Oracle Fusion Cloud SCM, Microsoft Excel, Microsoft Word, Google Colab
- Leadership & Coordination: Team Training & Mentoring, Cross-Functional Coordination, Vendor Liaison, Stakeholder Communication, POSH Compliance Training
- Analytical & Research: Data Collection & Analysis, Survey Design (Google Forms), Report Preparation, Published Research

Professional Experience

Senior Executive — Operations & Supply Chain | Reliance Retail (Quick Supply Chain Division) | Delhi, India | Aug 2022 – Dec 2024
- Managed daily warehouse operations including inbound receipts, outbound dispatch, and stock reconciliation for a fulfilment centre servicing 50+ retail stores and e-commerce orders.
- Oversaw inventory accuracy across ~5,000 SKUs through systematic cycle counts and stock audits, maintaining accuracy levels above 97%.
- Coordinated with procurement, logistics, and store operations teams to reduce order dispatch delays by ~15%, ensuring on-time delivery targets were consistently met.
- Streamlined inbound shipment processing workflows, cutting average goods-in turnaround time by ~20% through improved staging and documentation procedures.
- Trained and mentored a team of 20+ warehouse staff on operational processes, safety protocols, hygiene standards, and POSH compliance, with a focus on onboarding female employees.
Achievements:
- Promoted from Graduate Trainee to Senior Executive within 12 months based on strong operational performance and leadership.
- Recognised internally for improving dispatch reliability and warehouse floor discipline across the fulfilment centre.

Logistics Intern | Om Logistics | Delhi, India | Jun 2021 – Aug 2021
- Tracked and monitored consignment movements across multiple routes, identifying and resolving shipment delays to maintain delivery timelines.
- Coordinated with vendors and internal warehouse teams to streamline incoming shipment processing and improve goods receipt accuracy.
- Assisted in shipment clearance procedures, reducing documentation bottlenecks and improving clearance turnaround by ~10%.
- Verified incoming inventory against purchase orders and maintained accurate records of ~200+ weekly consignments.

Operations Intern | Shubh Consultants & Technocrats LLP | Delhi, India | Jun 2022 – Jul 2022
- Supported day-to-day project coordination and documentation activities across multiple consulting engagements.
- Maintained project records, performed data entry, and organised operational information to ensure smooth workflow across teams.
- Gained practical exposure to structured project management processes and cross-functional team coordination in a professional consulting environment.

Education
MSc in Management (Strategy), Dublin City University (DCU), Dublin, Ireland | Jan 2025 – Mar 2026 | Grade: 2:1
BBA in Logistics & Supply Chain Management, Galgotias University, Greater Noida, India | May 2019 – May 2022 | GPA: 9.2/10 | Silver Medallist (Top 2)

Certifications
- Oracle Fusion Cloud Applications SCM Process Essentials Certified (Rel 1) — Oracle University, November 2025
- Processes in SAP S/4HANA Extended Warehouse Management (EWM) — In Progress
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASTRA PROMPT — Supply Chain / Operations ATS Tailoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASTRA_PROMPT = """
Role: You are Astra, a ruthlessly effective ATS Optimisation Engine for supply chain and operations roles. Your ONLY job: get this candidate past automated screening and into the interview room.

Candidate: Praghya Prakhar — Supply Chain & Operations Professional with 2.3 years experience, based in Dublin, Ireland.
- Reliance Retail (India's largest retailer): Warehouse ops, inventory control, dispatch coordination, team training, SAP
- Om Logistics (Internship): Consignment tracking, shipment clearance, vendor coordination
- Shubh Consultants (Internship): Project coordination, documentation, data entry

Target seniority: entry-level to junior (0-3 years). She handles interviews herself. You get the phone call.

=== ANTI-HALLUCINATION RULES (CRITICAL — READ FIRST) ===

SKILL HONESTY — THE #1 RULE:
The candidate has these REAL skills: SAP (Inventory & SCM modules), Oracle Fusion Cloud SCM (certified), Microsoft Excel (basic-intermediate), warehouse operations, inventory management, inbound/outbound logistics, stock auditing, dispatch coordination, cycle counting, team training, vendor liaison, process standardisation, SOP development.

She does NOT have and you must NEVER claim:
- Python, SQL, R, or ANY programming language
- Power BI, Tableau, or ANY BI/visualization tool
- Advanced Excel (VBA, macros, pivot tables, complex formulas)
- AWS, Azure, GCP, or ANY cloud platform
- Any database skills (PostgreSQL, MySQL, MongoDB)
- Data science, machine learning, or advanced analytics
- Six Sigma certification (she is currently learning, NOT certified)
- PMP or PRINCE2 (she is currently learning, NOT certified)
- Any Irish professional work experience (she has part-time airport work only)

If the JD requires Python, SQL, Power BI, or programming as MUST-HAVE skills, acknowledge in the summary that the candidate brings operational domain expertise and is a quick learner, but NEVER claim she already has those technical skills.

EXPERIENCE HONESTY:
- She has 2 years 4 months at Reliance Retail. NEVER say "3+ years" or "5+ years".
- She managed operations for 50+ stores. This is her strongest professional claim.
- She maintained 97% inventory accuracy across ~5,000 SKUs. EXACT metric, never inflate.
- She reduced dispatch delays by ~15%. EXACT metric.
- She cut inbound turnaround time by ~20%. EXACT metric.
- She trained 20+ warehouse staff. EXACT number.
- She improved clearance turnaround by ~10% at Om Logistics. EXACT metric.
- She verified ~200+ weekly consignments. EXACT metric.
- NEVER round up, inflate, or fabricate any metric.

DOMAIN BRIDGE RULES:
When the JD is in a different sub-domain (e.g., pharma supply chain, construction logistics, FMCG distribution):
- CORRECT: "Supply chain professional with 2+ years of hands-on warehouse and fulfilment operations at one of India's largest retailers, bringing transferable inventory control and logistics coordination skills to [target sector]."
- WRONG: "Experienced pharma supply chain specialist" — she has NEVER worked in pharma. Never claim sector expertise she doesn't have.
- Frame Reliance Retail experience as transferable: retail fulfilment ops translate to any distribution/warehouse environment.

=== ANTI-AI-WRITING RULES ===

BANNED WORDS AND PHRASES — never use these anywhere in the resume:
- "testament to", "underscores", "pivotal", "realm", "tapestry", "landscape"
- "serves as", "stands as", "functions as" — use "is" or "are" instead
- "groundbreaking", "cutting-edge", "state-of-the-art", "best-in-class"
- "showcasing", "highlighting", "demonstrating", "underscoring"
- "fostering", "cultivating", "spearheading"
- "nestled", "at the intersection of", "at the forefront of"
- "passionate about", "driven by", "committed to excellence"
- "seamless", "robust" (overused), "innovative" (meaningless)
- "leveraging" — use "using" instead
- "harnessing" — use "using" instead
- "utilizing" — use "using" or "with" instead
- "ensuring alignment" or "ensuring seamless"
- Three-adjective chains: "scalable, reliable, and efficient" — pick ONE

WRITING STYLE RULES:
- Vary sentence length. Mix short punchy sentences with longer ones.
- Use plain verbs: managed, coordinated, tracked, maintained, reduced, improved, trained, processed, verified
- Be specific, not inflated. "Maintained 97% inventory accuracy across 5,000 SKUs" beats "achieved excellent inventory performance"
- No em dashes in bullet points. Use commas or periods.
- Each bullet should start with a strong past-tense verb, not a noun phrase.
- Avoid the "Rule of Three" pattern (X, Y, and Z => X and Y is fine)
- The summary should sound like a confident human wrote it, not ChatGPT.

=== CORE STRATEGY — KEYWORD ABSORPTION ===

1. KEYWORD HARVESTING:
   - Extract EVERY hard skill, tool, technology, and methodology from the JD.
   - For tools the candidate actually has (SAP, Oracle Fusion, Excel): place prominently in Skills and bullets.
   - For tools she doesn't have but the JD lists as nice-to-have: DO NOT add them. Only include real skills.
   - For process/methodology terms from the JD (e.g., "lean manufacturing", "demand forecasting", "S&OP"): include if she has adjacent experience. She can claim familiarity with concepts from her BBA in Logistics & SCM.

2. EDUCATION PROMINENCE:
   Praghya's education is her STRONGEST differentiator in the Irish market:
   - MSc in Management (Strategy) from DCU — Irish qualification, shows local commitment
   - BBA in Logistics & Supply Chain Management — 9.2/10 GPA, Silver Medallist (Top 2 in class)
   - Oracle Fusion Cloud SCM Certified — Oracle University
   - Published research on supply chain management
   - DCU Scholarship Recipient (€2,000)
   For graduate programmes or junior roles, LEAD with education credentials.

3. DOMAIN BRIDGE:
   - Warehouse/Distribution JDs → Lead with Reliance Retail fulfilment ops, inventory accuracy, dispatch metrics
   - Procurement/Sourcing JDs → Lead with vendor coordination (Om Logistics), cost awareness, supplier liaison
   - Graduate Programme JDs → Lead with education (DCU MSc + BBA Silver Medal), Oracle certification, published research
   - Planning/Forecasting JDs → Lead with KPI monitoring, stock reconciliation, demand patterns from managing 50+ store fulfilment
   - General Operations JDs → Blend warehouse ops + process standardisation + team leadership
   - ALWAYS frame as transferable from retail operations. Never claim domain experience in sectors she hasn't worked in.

4. SENIORITY (0-3 YEARS):
   - Use entry-to-junior verbs: "managed", "coordinated", "supported", "assisted", "maintained", "tracked"
   - Training 20+ staff is fine — this shows leadership potential.
   - Promotion from Graduate Trainee to Senior Executive in 12 months — highlight this as evidence of fast learning.
   - If JD says "1-3 years", frame as "2+ years of hands-on experience."
   - If JD says "3-5 years" (stretch), frame as "2+ years of progressive experience with rapid career growth."
   - NEVER claim more than 2.3 years.

5. SUMMARY:
   - Sentence 1: Who you are + years + the EXACT role title from the JD.
   - Sentence 2: Your strongest credential (Reliance Retail ops for 50+ stores) + education (DCU MSc).
   - Sentence 3: Key certification (Oracle Fusion Cloud SCM) + what you bring to the target company.
   - Mention the target company by name.
   - Must sound like a human wrote it. No promotional puffery.

6. SKILLS:
   - 5-6 categories. JD-specific terms listed FIRST in each category.
   - Categories should align with JD groupings (e.g., if JD groups "ERP & Systems", match that).
   - ONLY include skills she actually has. If the JD asks for Power BI, DO NOT add Power BI.
   - Include soft skills category if JD mentions communication, teamwork, stakeholder management.

7. EXPERIENCE:
   - ALL 3 roles MUST appear. Never drop any.
   - Reliance Retail: 5-6 responsibilities + 2-3 quantified achievements. This is the anchor.
   - Om Logistics: 3-4 bullets. Focus on logistics coordination and vendor liaison.
   - Shubh Consultants: 2-3 bullets. Focus on project coordination and documentation.
   - Rewrite bullets to maximize JD keyword density while staying truthful.
   - PRESERVE these EXACT metrics (never round, inflate, or change):
     * "97%" inventory accuracy (Reliance) — not 98%, not 99%, not ">95%"
     * "~15%" dispatch delay reduction (Reliance) — exact
     * "~20%" turnaround time reduction (Reliance) — exact
     * "50+" stores (Reliance) — exact
     * "~5,000 SKUs" (Reliance) — exact
     * "20+" warehouse staff trained (Reliance) — exact
     * "~10%" clearance turnaround improvement (Om Logistics) — exact
     * "~200+" weekly consignments (Om Logistics) — exact
     * "12 months" for promotion (Reliance) — exact

8. EDUCATION:
   - MSc in Management (Strategy), Dublin City University (DCU), Dublin, Ireland | Jan 2025 – Mar 2026 | Grade: 2:1
   - BBA in Logistics & Supply Chain Management, Galgotias University, Greater Noida, India | May 2019 – May 2022 | GPA: 9.2/10 | Silver Medallist (Top 2)
   - Include dissertation if relevant: "Impact of Social Media on Decision-Making and Emotional Well-Being"
   - Include published research if relevant: "Published research paper on supply chain management challenges"

9. CERTIFICATIONS:
   - Oracle Fusion Cloud Applications SCM Process Essentials Certified (Rel 1) — Oracle University, November 2025
   - SAP S/4HANA Extended Warehouse Management (EWM) — In Progress
   - ONLY mention "In Progress" for Six Sigma/PMP if the JD specifically asks for them.

10. ADDITIONAL:
   - Languages: English (Fluent), Hindi (Native)
   - Awards: DCU Scholarship Recipient (€2,000); Silver Medal — BBA Graduation (Top 2)
   - Work Authorisation: Stamp 1G (pending, expected May 2026). Eligible for full-time employment in Ireland.
   - Include work authorisation ONLY if the JD mentions visa/sponsorship.

11. CONTACT: +353 89 263 0034 | pragyaprakhar2012@gmail.com | Dublin, Ireland
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COVER LETTER PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVER_LETTER_PROMPT = """
Role: You are Praghya Prakhar writing a direct email to a Hiring Manager.
Goal: Sound 100% human. Get a response.

BANNED PHRASES — never use any of these:
"I am writing to express my interest", "I am excited to apply", "Please find my resume attached",
"testament to", "underscores", "pivotal", "realm", "tapestry", "I believe I am a perfect fit",
"passionate about", "driven by a desire", "committed to excellence", "at the forefront of",
"showcasing", "highlighting", "demonstrating", "serves as", "stands as",
"leveraging", "harnessing", "utilizing", "seamless", "innovative", "groundbreaking"

DOMAIN HONESTY:
- Praghya worked in Retail/FMCG distribution (Reliance Retail) and Logistics (Om Logistics).
- She has an MSc from DCU and a BBA in Logistics & SCM with a Silver Medal.
- She is Oracle Fusion Cloud SCM certified.
- If the JD is from a DIFFERENT industry (pharma, tech, construction), frame as:
  "I've solved [similar operational problem] in retail fulfilment, and the same approach transfers directly."
- NEVER claim: "I have experience in [target industry]" unless it's retail or logistics.

SKILL HONESTY:
- NEVER mention Python, SQL, Power BI, Tableau, or any programming skill.
- Focus on operational strengths: inventory accuracy, warehouse coordination, team training, vendor management.

THE OPENING: Start with a specific observation about the company's operational challenge from the JD.
   - Bad: "I am applying for the Supply Chain Analyst role at CompanyX."
   - Good: "Keeping inventory accuracy above 95% when you're servicing dozens of store locations and managing thousands of SKUs — most operations teams underestimate how much depends on the cycle counting process."

THE WAR STORY: Pick the BEST matching story based on the JD:
   1. RELIANCE (Inventory/Warehouse): "At Reliance Retail, I managed fulfilment operations across 50+ stores and maintained 97% inventory accuracy on ~5,000 SKUs through systematic cycle counts and stock audits."
   2. RELIANCE (Efficiency): "At Reliance Retail, I cut inbound turnaround time by 20% by reworking staging and documentation procedures, and reduced order dispatch delays by 15%."
   3. RELIANCE (Leadership): "At Reliance Retail, I was promoted from Graduate Trainee to Senior Executive in 12 months. I trained 20+ warehouse staff on operations, safety, and compliance."
   4. OM LOGISTICS (Vendor/Shipping): "During my internship at Om Logistics, I tracked 200+ weekly consignments and improved shipment clearance turnaround by 10% through better vendor coordination."

WRITING STYLE:
- Short sentences mixed with longer ones. Vary the rhythm.
- No em dashes. Use commas or periods.
- No three-adjective chains.
- Sound like a person talking, not a press release.
- She is entry-level. Sound confident but not arrogant. Show eagerness to learn.

STRUCTURE:
1. "Dear Hiring Team,"
2. Hook (company's pain point from JD — be specific)
3. Bridge: "This is close to a problem I solved at Reliance Retail..."
4. War Story with specific numbers
5. Brief mention of education (DCU MSc or Oracle certification) if relevant
6. Brief closing. End with "Thank you"

Return ONLY the letter body. No markdown. No bold. No headers.
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ATS SCORING PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATS_SCORING_PROMPT = """You are a strict ATS (Applicant Tracking System) scanner for supply chain and operations roles.
Compare the RESUME JSON against the JOB DESCRIPTION.

Scoring criteria (0-100):
- Keyword match density (40%): What percentage of hard skills/tools/certifications in the JD appear in the resume?
- Experience relevance (30%): Do the bullet points describe work that solves the JD's problems?
- Seniority alignment (15%): Does the experience level match what the JD asks for?
- Education & Certification fit (15%): Does the candidate's education and certifications match JD requirements?

IMPORTANT: Do NOT penalise for missing Python/SQL/Power BI if those are listed as "nice-to-have" in the JD.
DO penalise if they are listed as "must-have" and the resume doesn't have them.

Output ONLY valid JSON with no markdown, no backticks, no explanation:
{"score": <int 0-100>, "reasoning": "<1 sentence>", "missing_keywords": "<comma-separated list of JD keywords NOT found in resume>"}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. PYDANTIC SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ExperienceItem(BaseModel):
    role_title: str = Field(description="The job title exactly as it should appear")
    company: str = Field(description="The company name")
    dates: str = Field(description="Employment dates (e.g., 'Aug 2022 – Dec 2024')")
    location: str = Field(description="City, Country")
    responsibilities: List[str] = Field(description="List of 3-6 bullet points reframed for the JD with maximum keyword density")
    achievements: List[str] = Field(description="List of 1-3 quantified achievements with EXACT original metrics preserved")

class EducationItem(BaseModel):
    degree: str = Field(description="Full degree name with grade")
    college: str = Field(description="University name with location and dates")

class CertificationItem(BaseModel):
    name: str = Field(description="Full certification name with issuer and date")

class SkillCategory(BaseModel):
    category: str = Field(description="Skill category name (e.g., 'Supply Chain Management')")
    technologies: str = Field(description="Comma-separated skills. JD-mentioned terms listed FIRST.")

class ResumeSchema(BaseModel):
    candidate_name: str = Field(description="Always: Praghya Prakhar")
    candidate_title: str = Field(description="Professional title tailored to match the JD's exact role title")
    contact_info: str = Field(description="Always: +353 89 263 0034 | pragyaprakhar2012@gmail.com | Dublin, Ireland")
    summary: str = Field(description="3-4 sentence professional summary. Must mention target company name and match JD language.")
    skills: List[SkillCategory] = Field(description="5-6 skill categories. Only REAL skills.")
    experience: List[ExperienceItem] = Field(description="ALL 3 roles: Reliance Retail, Om Logistics, Shubh Consultants. Never drop any.")
    education: List[EducationItem] = Field(description="MSc from DCU and BBA from Galgotias with grades")
    certifications: List[CertificationItem] = Field(description="Oracle Fusion Cloud SCM + any in-progress certs relevant to JD")
    target_company: str = Field(description="Company name extracted from JD")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCHEMA CLEANER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_clean_schema(pydantic_cls):
    schema = pydantic_cls.model_json_schema()
    def _clean(d):
        if isinstance(d, dict):
            for key in ["additionalProperties", "title"]:
                d.pop(key, None)
            for v in d.values():
                _clean(v)
        elif isinstance(d, list):
            for item in d:
                _clean(item)
    _clean(schema)
    return schema


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. DATA NORMALIZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def clean_skill_string(skill_str):
    if not isinstance(skill_str, str):
        return str(skill_str)
    if skill_str.strip().startswith("["):
        try:
            list_match = re.search(r"\[(.*?)\]", skill_str)
            if list_match:
                actual_list = ast.literal_eval(list_match.group(0))
                extra_part = skill_str[list_match.end():].strip().lstrip(",").strip()
                clean_str = ", ".join([str(s) for s in actual_list])
                if extra_part:
                    clean_str += f", {extra_part}"
                return clean_str
        except Exception:
            pass
    return skill_str


def normalize_schema(data):
    if not isinstance(data, dict):
        return {"summary": str(data), "skills": {}, "experience": [], "education": [], "certifications": []}

    normalized = {}

    # Contact/Name
    normalized['candidate_name'] = data.get('candidate_name', 'Praghya Prakhar')
    normalized['candidate_title'] = data.get('candidate_title', 'Supply Chain & Operations Professional')
    raw_contact = data.get('contact_info', '+353 89 263 0034 | pragyaprakhar2012@gmail.com | Dublin, Ireland')
    normalized['contact_info'] = str(raw_contact) if not isinstance(raw_contact, dict) else ' | '.join(str(v) for v in raw_contact.values() if v)

    # Summary
    normalized['summary'] = data.get('summary', '')

    # Skills → always dict
    raw_skills = data.get('skills', {})
    normalized['skills'] = {}
    if isinstance(raw_skills, dict):
        for k, v in raw_skills.items():
            normalized['skills'][k] = clean_skill_string(str(v))
    elif isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                cat = item.get('category', '')
                tech = item.get('technologies', '')
                if cat and tech:
                    normalized['skills'][cat] = clean_skill_string(str(tech))
            else:
                normalized['skills'] = {"General Skills": ", ".join([str(s) for s in raw_skills])}
                break

    # Experience
    raw_exp = data.get('experience', [])
    norm_exp = []
    if isinstance(raw_exp, list):
        for role in raw_exp:
            if isinstance(role, dict):
                norm_exp.append({
                    'role_title': role.get('role_title', ''),
                    'company': role.get('company', ''),
                    'dates': role.get('dates', ''),
                    'location': role.get('location', ''),
                    'responsibilities': role.get('responsibilities', []),
                    'achievements': role.get('achievements', []),
                })
    normalized['experience'] = norm_exp

    # Education
    raw_edu = data.get('education', [])
    norm_edu = []
    if isinstance(raw_edu, list):
        for edu in raw_edu:
            if isinstance(edu, dict):
                norm_edu.append({
                    'degree': edu.get('degree', ''),
                    'college': edu.get('college', ''),
                })
            elif isinstance(edu, str):
                norm_edu.append({'degree': edu, 'college': ''})
    elif isinstance(raw_edu, str):
        norm_edu.append({'degree': raw_edu, 'college': ''})
    if not norm_edu:
        norm_edu = [
            {'degree': 'MSc in Management (Strategy) | Grade: 2:1', 'college': 'Dublin City University (DCU), Dublin, Ireland | Jan 2025 – Mar 2026'},
            {'degree': 'BBA in Logistics & Supply Chain Management | GPA: 9.2/10 | Silver Medallist (Top 2)', 'college': 'Galgotias University, Greater Noida, India | May 2019 – May 2022'},
        ]
    normalized['education'] = norm_edu

    # Certifications
    raw_certs = data.get('certifications', [])
    norm_certs = []
    if isinstance(raw_certs, list):
        for cert in raw_certs:
            if isinstance(cert, dict):
                norm_certs.append({'name': cert.get('name', '')})
            elif isinstance(cert, str):
                norm_certs.append({'name': cert})
    elif isinstance(raw_certs, str):
        norm_certs.append({'name': raw_certs})
    if not norm_certs:
        norm_certs = [{'name': 'Oracle Fusion Cloud Applications SCM Process Essentials Certified (Rel 1) — Oracle University, November 2025'}]
    normalized['certifications'] = norm_certs

    normalized['target_company'] = data.get('target_company', 'Company')
    return normalized


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. ATS SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calculate_ats_score(resume_json, jd_text, api_key):
    if not api_key:
        return {"score": 0, "reasoning": "No API Key", "missing_keywords": ""}
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=SCORING_MODEL,
            contents=f"{ATS_SCORING_PROMPT}\n\nRESUME:\n{str(resume_json)[:3000]}\n\nJOB DESCRIPTION:\n{jd_text[:3000]}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        content = response.text.strip()
        if "```" in content:
            match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()
        return json.loads(content)
    except Exception as e:
        return {"score": 0, "reasoning": f"Scoring Error: {str(e)}", "missing_keywords": ""}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. SKILL VALIDATION (Anti-Hallucination Guard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNED_SKILLS = [
    "python", "sql", "r programming", "javascript", "java", "c++", "c#",
    "power bi", "tableau", "looker", "qlik", "data studio",
    "vba", "macros", "pivot tables",
    "aws", "azure", "gcp", "cloud computing",
    "postgresql", "mysql", "mongodb", "redis", "snowflake",
    "machine learning", "deep learning", "data science", "nlp",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "six sigma certified", "six sigma black belt", "six sigma green belt",
    "pmp certified", "prince2 certified",
    "docker", "kubernetes", "ci/cd", "git",
    "react", "angular", "node.js",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5a. JD PRE-SCREENER (UPGRADE 1 — v1.1)
# Scans JD for dealbreakers BEFORE wasting a generation cycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CSEP_MINIMUM_SALARY = 40904  # EUR per year

# Title patterns that signal too-senior roles
SENIOR_TITLE_PATTERNS = [
    r'\bsenior\b', r'\bsr\.?\b', r'\bprincipal\b', r'\bstaff\b',
    r'\blead\b', r'\bdirector\b', r'\bvp\b', r'\bhead of\b',
    r'\bmanager\b',  # unless "assistant manager" or "warehouse manager"
]
SENIOR_TITLE_EXCEPTIONS = [r'\bassistant manager\b', r'\bwarehouse manager\b']

# Contract signals — context-aware to avoid false positives on "contract management/coordination"
CONTRACT_SIGNALS = [
    r'\bcontract role\b', r'\bcontract position\b', r'\bcontract basis\b',
    r'\btemporary\b', r'\bftc\b', r'\bfixed[ -]term\b',
    r'\bfreelance\b', r'\bmaternity cover\b', r'\b\d+[ -]month contract\b',
    r'\bmonth contract\b', r'\bmonths contract\b', r'\bcontract\)?\s*$',
    r'\b\d+[ -]month\s+(fixed|temp)', r'\bshort[ -]term contract\b',
    r'\brolling contract\b',
]
# Explicit non-contract: "contract management", "contract coordination" are procurement terms
CONTRACT_FALSE_POSITIVES = [
    r'\bcontract\s+(management|coordination|coordinator|negotiation|admin)',
    r'\b(supplier|vendor|procurement)\s+contract',
]

# No-visa signals
NO_VISA_SIGNALS = [
    r'\bno visa sponsorship\b', r'\bcannot sponsor\b', r'\bwill not sponsor\b',
    r'\bno sponsorship\b', r'\bmust have right to work\b',
    r'\bmust be authorized\b', r'\bno work permit\b',
]

# Experience year extraction
EXPERIENCE_YEAR_PATTERNS = [
    r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',
    r'minimum\s*(?:of)?\s*(\d+)\s*(?:years?|yrs?)',
    r'(\d+)\s*(?:to|-)\s*\d+\s*(?:years?|yrs?)',
    r'at least\s*(\d+)\s*(?:years?|yrs?)',
]

# Word-form numbers to catch "five years experience" etc.
WORD_TO_NUM = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
}
WORD_YEAR_PATTERN = r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)'

# Must-have technical skills Praghya doesn't have
MUST_HAVE_TECH_PATTERNS = [
    (r'\b(?:must have|required|essential|mandatory).*?(?:python|sql|power bi|tableau|r programming)', "Python/SQL/Power BI as must-have"),
    (r'\b(?:python|sql|power bi|tableau)\b.*?(?:required|essential|must|mandatory)', "Python/SQL/Power BI as must-have"),
]

# Irish experience requirement
IRISH_EXP_PATTERNS = [
    r'irish\s*(?:experience|exp|market)',
    r'experience\s*(?:in|within)\s*ireland',
    r'similar\s*irish',
    r'ireland\s*(?:experience|based)',
]

# Salary extraction
SALARY_PATTERNS = [
    r'€\s*([\d,]+)\s*(?:per|a|/)\s*(?:year|annum|yr)',
    r'€\s*([\d,]+)\s*(?:-|to|–)\s*€?\s*([\d,]+)\s*(?:per|a|/)\s*(?:year|annum|yr)',
    r'([\d,]+)\s*(?:per|a|/)\s*(?:year|annum|yr)',
    r'€\s*([\d,]+)\s*(?:per|a|/)\s*(?:hour|hr)',  # hourly = likely contract
]


def prescreen_jd(jd_text):
    """
    Scan JD for dealbreakers before generating.
    Returns dict with:
      - blockers: list of hard rejections (don't generate)
      - warnings: list of concerns (generate but flag)
      - proceed: bool (True if no blockers)
    """
    jd_lower = jd_text.lower()
    blockers = []
    warnings = []

    # 1. SENIORITY CHECK — extract max years required
    max_years = 0
    for pattern in EXPERIENCE_YEAR_PATTERNS:
        matches = re.findall(pattern, jd_lower)
        for m in matches:
            yr = int(m) if isinstance(m, str) else int(m[0]) if isinstance(m, tuple) else 0
            max_years = max(max_years, yr)

    # Also check word-form numbers: "five years experience"
    word_matches = re.findall(WORD_YEAR_PATTERN, jd_lower)
    for wm in word_matches:
        yr = WORD_TO_NUM.get(wm, 0)
        max_years = max(max_years, yr)

    if max_years >= 7:
        blockers.append(f"Requires {max_years}+ years experience — Praghya has 2.3 years. Hard reject.")
    elif max_years >= 5:
        warnings.append(f"Requires {max_years}+ years experience — Praghya has 2.3 years. Very likely filtered out by ATS. Stretch application.")
    elif max_years >= 4:
        warnings.append(f"Requires {max_years}+ years — stretch for Praghya's 2.3 years, but promotion story may help.")

    # 2. SENIOR TITLE CHECK
    is_senior = False
    for pattern in SENIOR_TITLE_PATTERNS:
        if re.search(pattern, jd_lower):
            is_exception = any(re.search(exc, jd_lower) for exc in SENIOR_TITLE_EXCEPTIONS)
            if not is_exception:
                is_senior = True
                break
    if is_senior:
        blockers.append("Title contains Senior/Lead/Director/Manager — too senior for Praghya's profile.")

    # 3. CONTRACT CHECK (with false positive exclusion)
    is_contract = False
    for pattern in CONTRACT_SIGNALS:
        if re.search(pattern, jd_lower):
            # Check if it's actually a false positive (procurement context)
            is_false_positive = any(re.search(fp, jd_lower) for fp in CONTRACT_FALSE_POSITIVES)
            if not is_false_positive:
                is_contract = True
                break
    if is_contract:
        blockers.append("Contract/temporary/FTC role detected. Stamp 1G requires permanent employment. Cannot sponsor via contract.")

    # 4. NO VISA CHECK
    for pattern in NO_VISA_SIGNALS:
        if re.search(pattern, jd_lower):
            blockers.append("JD explicitly states no visa sponsorship. Praghya needs CSEP sponsorship.")
            break

    # 5. MUST-HAVE TECH SKILLS CHECK
    for pattern, desc in MUST_HAVE_TECH_PATTERNS:
        if re.search(pattern, jd_lower):
            warnings.append(f"{desc} — Praghya doesn't have these. Resume will score low on keyword match.")
            break

    # 6. IRISH EXPERIENCE CHECK
    for pattern in IRISH_EXP_PATTERNS:
        if re.search(pattern, jd_lower):
            warnings.append("JD requires Irish market/work experience — Praghya has 0 years of Irish professional experience (only part-time airport work).")
            break

    # 7. SALARY CHECK (below CSEP minimum)
    for pattern in SALARY_PATTERNS:
        matches = re.findall(pattern, jd_lower)
        for m in matches:
            try:
                if isinstance(m, tuple):
                    sal = int(m[0].replace(',', ''))
                else:
                    sal = int(m.replace(',', ''))
                # Check if hourly (likely contract)
                if 'hour' in pattern or 'hr' in pattern:
                    warnings.append(f"Hourly rate (€{sal}/hr) detected — may indicate contract role. Verify if permanent.")
                elif sal < CSEP_MINIMUM_SALARY and sal > 1000:  # sanity check
                    warnings.append(f"Salary €{sal:,} is below CSEP minimum (€{CSEP_MINIMUM_SALARY:,}). May not qualify for Critical Skills Employment Permit.")
            except (ValueError, IndexError):
                pass
        if matches:
            break

    # 8. LOCATION CHECK
    # Northern Ireland is different visa jurisdiction — check BEFORE general Ireland check
    ni_patterns = [r'\bnorthern ireland\b', r'\bbelfast\b', r'\bderry\b', r'\bnewry\b']
    for pattern in ni_patterns:
        if re.search(pattern, jd_lower):
            blockers.append("Location is Northern Ireland (UK jurisdiction). Praghya's Stamp 1G is Republic of Ireland only.")
            break

    # Other UK locations (only if not already caught by NI check)
    if not any("Northern Ireland" in b for b in blockers):
        uk_patterns = [r'\blondon\b', r'\bmanchester\b', r'\buk only\b', r'\bunited kingdom\b', r'\bengland\b', r'\bscotland\b', r'\bwales\b']
        for pattern in uk_patterns:
            if re.search(pattern, jd_lower) and not re.search(r'\b(?:or\s+)?ireland\b', jd_lower):
                blockers.append("Location is UK — different visa jurisdiction. Praghya's Stamp 1G is Ireland only.")
                break

    return {
        "blockers": blockers,
        "warnings": warnings,
        "proceed": len(blockers) == 0,
        "max_years_required": max_years,
    }


def _strip_banned_from_text(text, banned_terms):
    """Remove banned terms from a text string. Returns (cleaned_text, list_of_removed)."""
    removed = []
    cleaned = text
    for term in banned_terms:
        if term in cleaned.lower():
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            if pattern.search(cleaned):
                removed.append(term)
                cleaned = pattern.sub('', cleaned)
    # Clean up leftover commas, double spaces
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r'^\s*,\s*', '', cleaned)
    cleaned = re.sub(r'\s*,\s*$', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned.strip(), removed


# Broader list for prose scanning (includes phrases that might appear in bullets)
BANNED_PROSE_TERMS = [
    "python", "sql", "power bi", "tableau", "looker", "qlik",
    "vba", "macros", "pivot tables", "advanced excel",
    "machine learning", "deep learning", "data science",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "aws", "azure", "gcp", "docker", "kubernetes",
    "postgresql", "mysql", "mongodb", "snowflake",
    "react", "angular", "node.js", "javascript", "java", "c++", "c#",
    "six sigma certified", "pmp certified", "prince2 certified",
    "5+ years", "5 years of experience", "3+ years of experience",
]


def validate_skills(data):
    """
    UPGRADE 2 (v1.1): Full-text hallucination scan.
    Scans skills section, summary, bullet points, AND achievements.
    Returns cleaned data + hallucination report.
    """
    hall_report = []  # track what was caught and where

    # 1. SKILLS SECTION — remove from comma-separated lists
    if 'skills' in data:
        cleaned_skills = {}
        for cat, tools_str in data['skills'].items():
            cleaned, removed = _strip_banned_from_text(tools_str, BANNED_SKILLS)
            if removed:
                hall_report.append(f"Skills/{cat}: removed {removed}")
            if cleaned:
                cleaned_skills[cat] = cleaned
        data['skills'] = cleaned_skills

    # 2. SUMMARY — remove banned terms from prose
    if data.get('summary'):
        cleaned, removed = _strip_banned_from_text(data['summary'], BANNED_PROSE_TERMS)
        if removed:
            hall_report.append(f"Summary: removed {removed}")
            data['summary'] = cleaned

    # 3. EXPERIENCE BULLETS — scan responsibilities AND achievements
    for role in data.get('experience', []):
        company = role.get('company', 'unknown')

        # Responsibilities
        new_resps = []
        for bullet in role.get('responsibilities', []):
            cleaned, removed = _strip_banned_from_text(bullet, BANNED_PROSE_TERMS)
            if removed:
                hall_report.append(f"Bullet({company}): removed {removed}")
            if cleaned:
                new_resps.append(cleaned)
        role['responsibilities'] = new_resps

        # Achievements
        new_achs = []
        for ach in role.get('achievements', []):
            cleaned, removed = _strip_banned_from_text(ach, BANNED_PROSE_TERMS)
            if removed:
                hall_report.append(f"Achievement({company}): removed {removed}")
            if cleaned:
                new_achs.append(cleaned)
        role['achievements'] = new_achs

    # Store report in data for UI display
    data['_hallucination_report'] = hall_report
    return data


def to_text_block(val):
    if val is None:
        return ""
    if isinstance(val, list):
        return "\n".join([str(x) for x in val])
    return str(val)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def analyze_and_generate(api_key, resume_text, jd_text, boost_keywords=None):
    """
    UPGRADE 3 (v1.1): Score-driven re-generation.
    If ATS score < 70 on first pass, auto-injects missing keywords
    into a second-pass prompt for improved keyword density.
    Max 2 passes to avoid infinite loops.
    """
    client = genai.Client(api_key=api_key)

    for attempt in range(2):  # max 2 passes
        try:
            safe_schema = get_clean_schema(ResumeSchema)

            # Build prompt — on second pass, inject missing keywords
            prompt = ASTRA_PROMPT
            if boost_keywords and attempt > 0:
                boost_instruction = f"""

=== SECOND PASS — KEYWORD BOOST (AUTO-GENERATED) ===
The first-pass resume scored below 70% on ATS keyword match.
These JD keywords were MISSING from the resume: {boost_keywords}

For each missing keyword:
- If Praghya has the skill or adjacent experience → ADD it to the relevant Skills category and weave it into bullet points.
- If it's a methodology/process concept she studied in her BBA/MSc → ADD it to Skills with "familiarity" framing.
- If she genuinely does NOT have it and it's not a banned skill → Add ONLY to Skills section as "awareness" level. Do NOT fabricate experience.
- If it's a banned skill (Python, SQL, Power BI, etc.) → DO NOT ADD IT. The anti-hallucination rules still apply.

IMPORTANT: Do NOT sacrifice truthfulness for keyword density. Only add what's defensible.
=== END SECOND PASS ===
"""
                prompt = ASTRA_PROMPT + boost_instruction

            response = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=f"{prompt}\n\nRESUME:\n{resume_text}\n\nJD:\n{jd_text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=safe_schema,
                )
            )

            raw_data = json.loads(response.text)
            data = raw_data.model_dump() if hasattr(raw_data, 'model_dump') else raw_data

            # Transform skills list → dict if needed
            if 'skills' in data and isinstance(data['skills'], list):
                transformed = {}
                for item in data['skills']:
                    cat = item.get('category') if isinstance(item, dict) else getattr(item, 'category', '')
                    tech = item.get('technologies') if isinstance(item, dict) else getattr(item, 'technologies', '')
                    if cat and tech:
                        transformed[cat] = tech
                data['skills'] = transformed

            data = normalize_schema(data)

            # Anti-hallucination: full-text validate (v1.1)
            data = validate_skills(data)

            # ATS Score
            judge = calculate_ats_score(data, jd_text, api_key)
            data['ats_score'] = judge.get('score', 0)
            data['ats_reason'] = judge.get('reasoning', '')
            data['missing_keywords'] = judge.get('missing_keywords', '')
            data['generation_pass'] = attempt + 1

            # If first pass scored below 70 AND we have missing keywords, try again
            if attempt == 0 and data['ats_score'] < 70 and data.get('missing_keywords'):
                boost_keywords = data['missing_keywords']
                data['_first_pass_score'] = data['ats_score']
                continue  # go to second pass

            # If this is second pass, record improvement
            if attempt == 1 and '_first_pass_score' in data:
                data['_score_improvement'] = data['ats_score'] - data['_first_pass_score']

            return data
        except Exception as e:
            return {"error": f"Generation Error (pass {attempt+1}): {str(e)}"}

    return data  # fallback


def generate_cover_letter(api_key, resume_data, jd_text):
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=f"{COVER_LETTER_PROMPT}\n\nRESUME DATA:\n{str(resume_data)}\n\nJOB DESCRIPTION:\n{jd_text}",
        )
        return response.text
    except Exception as e:
        return f"Error generating cover letter: {str(e)}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. DOCX RENDERER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def set_font(run, size, bold=False):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.bold = bold
    try:
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    except Exception:
        pass


def create_doc(data):
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.5)

    # Header
    for txt, sz, b in [
        (data.get('candidate_name', ''), 28, True),
        (data.get('candidate_title', ''), 14, True),
        (data.get('contact_info', ''), 12, True),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(to_text_block(txt))
        if sz == 28:
            run.font.all_caps = True
        set_font(run, sz, b)

    def add_sec(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(2)
        set_font(p.add_run(title), 12, True)

    def add_body(txt, bullet=False):
        style = 'List Bullet' if bullet else 'Normal'
        p = doc.add_paragraph(style=style)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        p.paragraph_format.space_after = Pt(0)
        set_font(p.add_run(to_text_block(txt)), 12)

    # Professional Profile
    add_sec("Professional Profile")
    add_body(data.get('summary', ''))

    # Skills
    add_sec("Key Skills/ Tools & Technologies")
    for k, v in data.get('skills', {}).items():
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        p.paragraph_format.space_after = Pt(0)
        set_font(p.add_run(f"{k}: "), 12, True)
        set_font(p.add_run(to_text_block(v)), 12)

    # Experience
    add_sec("Professional Experience")
    for role in data.get('experience', []):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        line = f"{role.get('role_title')} | {role.get('company')} | {role.get('location')} | {role.get('dates')}"
        set_font(p.add_run(to_text_block(line)), 12, True)

        resps = role.get('responsibilities', [])
        if isinstance(resps, str):
            resps = resps.split('\n')
        for r in resps:
            if str(r).strip():
                add_body(r, bullet=True)

        achs = role.get('achievements', [])
        if isinstance(achs, str):
            achs = achs.split('\n')
        if achs and any(str(a).strip() for a in achs):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            set_font(p.add_run("Achievements:"), 12, True)
            for a in achs:
                if str(a).strip():
                    add_body(a, bullet=True)

    # Education
    add_sec("Education")
    for edu in data.get('education', []):
        text = f"{edu.get('degree', '')}"
        college = edu.get('college', '')
        if college:
            text += f"\n{college}"
        add_body(text, bullet=True)

    # Certifications
    certs = data.get('certifications', [])
    if certs:
        add_sec("Certifications")
        for cert in certs:
            name = cert.get('name', '') if isinstance(cert, dict) else str(cert)
            if name.strip():
                add_body(name, bullet=True)

    # Additional Information
    add_sec("Additional Information")
    add_body("Languages: English (Fluent), Hindi (Native)", bullet=True)
    add_body("Awards: DCU Scholarship Recipient (€2,000); Silver Medal — BBA Graduation (Top 2)", bullet=True)
    add_body("Work Authorisation: Stamp 1G (pending, expected May 2026). Eligible for full-time employment in Ireland.", bullet=True)

    return doc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. COVER LETTER DOCX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def create_cover_letter_doc(cover_letter_text, data):
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.5)

    def add_line(text, bold=False, space_after=12, align=WD_PARAGRAPH_ALIGNMENT.LEFT):
        if not text:
            return
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(str(text))
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.bold = bold

    add_line(data.get('candidate_name', '').upper(), bold=True, space_after=0)
    contact_info = data.get('contact_info', '')
    if "|" in contact_info:
        for part in contact_info.split('|'):
            add_line(part.strip(), bold=False, space_after=0)
    else:
        add_line(contact_info, bold=False, space_after=0)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    today_str = datetime.date.today().strftime("%B %d, %Y")
    add_line(today_str, space_after=12)

    for para in cover_letter_text.split('\n'):
        if para.strip():
            add_line(para.strip(), bold=False, space_after=12, align=WD_PARAGRAPH_ALIGNMENT.JUSTIFY)

    return doc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. PDF RENDERER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def create_pdf(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    sn = ParagraphStyle('N', parent=styles['Normal'], fontName='Times-Roman', fontSize=12, leading=14, alignment=TA_JUSTIFY, spaceAfter=0)
    sh_name = ParagraphStyle('HName', parent=styles['Normal'], fontName='Times-Bold', fontSize=28, leading=30, alignment=TA_CENTER, spaceAfter=0)
    sh_title = ParagraphStyle('HTitle', parent=styles['Normal'], fontName='Times-Bold', fontSize=14, leading=16, alignment=TA_CENTER, spaceAfter=0)
    sh_contact = ParagraphStyle('HContact', parent=styles['Normal'], fontName='Times-Bold', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=6)
    s_sec = ParagraphStyle('Sec', parent=styles['Normal'], fontName='Times-Bold', fontSize=12, leading=14, alignment=TA_LEFT, spaceBefore=12, spaceAfter=2)

    def clean(txt):
        if txt is None:
            return ""
        txt = to_text_block(txt)
        return escape(txt).replace('\n', '<br/>')

    elements = []
    elements.append(Paragraph(clean(data.get('candidate_name', '')), sh_name))
    elements.append(Paragraph(clean(data.get('candidate_title', '')), sh_title))
    elements.append(Paragraph(clean(data.get('contact_info', '')), sh_contact))

    elements.append(Paragraph("Professional Profile", s_sec))
    elements.append(Paragraph(clean(data.get('summary', '')), sn))

    elements.append(Paragraph("Key Skills/ Tools &amp; Technologies", s_sec))
    skill_items = []
    for k, v in data.get('skills', {}).items():
        text = f"<b>{clean(k)}:</b> {clean(v)}"
        skill_items.append(ListItem(Paragraph(text, sn), leftIndent=0))
    if skill_items:
        elements.append(ListFlowable(skill_items, bulletType='bullet', start='\u2022', leftIndent=15))

    elements.append(Paragraph("Professional Experience", s_sec))
    for role in data.get('experience', []):
        line = f"{role.get('role_title')} | {role.get('company')} | {role.get('location')} | {role.get('dates')}"
        elements.append(Paragraph(f"<b>{clean(line)}</b>", sn))
        elements.append(Spacer(1, 2))

        role_bullets = []
        resps = role.get('responsibilities', [])
        if isinstance(resps, str):
            resps = resps.split('\n')
        for r in resps:
            if str(r).strip():
                role_bullets.append(ListItem(Paragraph(clean(r), sn), leftIndent=0))
        if role_bullets:
            elements.append(ListFlowable(role_bullets, bulletType='bullet', start='\u2022', leftIndent=15))

        achs = role.get('achievements', [])
        if isinstance(achs, str):
            achs = achs.split('\n')
        if achs and any(str(a).strip() for a in achs):
            elements.append(Paragraph("<b>Achievements:</b>", sn))
            ach_bullets = []
            for a in achs:
                if str(a).strip():
                    ach_bullets.append(ListItem(Paragraph(clean(a), sn), leftIndent=0))
            if ach_bullets:
                elements.append(ListFlowable(ach_bullets, bulletType='bullet', start='\u2022', leftIndent=25))
        elements.append(Spacer(1, 6))

    elements.append(Paragraph("Education", s_sec))
    edu_bullets = []
    for edu in data.get('education', []):
        degree = edu.get('degree', '')
        college = edu.get('college', '')
        text = f"{degree}"
        if college:
            text += f"<br/>{college}"
        edu_bullets.append(ListItem(Paragraph(clean(text) if '<br/>' not in text else text, sn), leftIndent=0))
    if edu_bullets:
        elements.append(ListFlowable(edu_bullets, bulletType='bullet', start='\u2022', leftIndent=15))

    # Certifications
    certs = data.get('certifications', [])
    if certs:
        elements.append(Paragraph("Certifications", s_sec))
        cert_bullets = []
        for cert in certs:
            name = cert.get('name', '') if isinstance(cert, dict) else str(cert)
            if name.strip():
                cert_bullets.append(ListItem(Paragraph(clean(name), sn), leftIndent=0))
        if cert_bullets:
            elements.append(ListFlowable(cert_bullets, bulletType='bullet', start='\u2022', leftIndent=15))

    # Additional
    elements.append(Paragraph("Additional Information", s_sec))
    add_bullets = [
        "Languages: English (Fluent), Hindi (Native)",
        "Awards: DCU Scholarship Recipient (€2,000); Silver Medal — BBA Graduation (Top 2)",
        "Work Authorisation: Stamp 1G (pending, expected May 2026). Eligible for full-time employment in Ireland.",
    ]
    add_items = [ListItem(Paragraph(clean(a), sn), leftIndent=0) for a in add_bullets]
    elements.append(ListFlowable(add_items, bulletType='bullet', start='\u2022', leftIndent=15))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. STREAMLIT UI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon="\U0001f4e6", initial_sidebar_state="expanded")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1.5rem;}
    div.stButton > button:first-child {border-radius: 6px; font-weight: 600;}
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
</style>
""", unsafe_allow_html=True)

if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'saved_base' not in st.session_state:
    st.session_state['saved_base'] = PRAGHYA_BASE_RESUME
if 'saved_jd' not in st.session_state:
    st.session_state['saved_jd'] = ""
if 'cover_letter' not in st.session_state:
    st.session_state['cover_letter'] = None

with st.sidebar:
    st.header("\u2699\ufe0f Configuration")
    if google_key:
        st.success("API key configured")
    else:
        st.error("API key missing — add GOOGLE_API_KEY to Streamlit secrets")
        google_key = st.text_input("Google API Key (fallback)", type="password")
    st.divider()
    st.markdown("**Target Roles:**")
    st.caption("Supply Chain Analyst \u2022 Operations Analyst \u2022 Logistics Coordinator \u2022 Inventory Analyst")
    st.divider()
    st.markdown("**Models:**")
    st.caption(f"Resume: {GENERATION_MODEL}")
    st.caption(f"Scoring: {SCORING_MODEL}")
    st.divider()
    if st.button("\U0001f5d1\ufe0f Reset", use_container_width=True):
        st.session_state['data'] = None
        st.session_state['saved_base'] = PRAGHYA_BASE_RESUME
        st.session_state['saved_jd'] = ""
        st.session_state['cover_letter'] = None
        st.rerun()
    st.caption("Astra v1.1 | Personalised for Praghya")

if not st.session_state['data']:
    st.markdown(f"<h1 style='text-align: center;'>{PAGE_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Paste a JD. Get a tailored resume. Get the call.</p>", unsafe_allow_html=True)
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("\U0001f4cb Base Resume")
        st.caption("Pre-loaded. Edit only if needed.")
        base = st.text_area("Resume", st.session_state['saved_base'], height=400, label_visibility="collapsed")
    with c2:
        st.subheader("\U0001f4bc Job Description")
        st.caption("Paste the full JD here.")
        jd = st.text_area("JD", st.session_state['saved_jd'], height=400, label_visibility="collapsed")

    if st.button("\u2728 Generate Tailored Resume", type="primary", use_container_width=True):
        if base and jd and google_key:
            st.session_state['saved_base'] = base
            st.session_state['saved_jd'] = jd

            # UPGRADE 1 (v1.1): JD Pre-screening
            prescreen = prescreen_jd(jd)

            if prescreen['blockers']:
                st.error("**JD Pre-Screen: BLOCKED — Do not apply**")
                for b in prescreen['blockers']:
                    st.error(f"\u274c {b}")
                if prescreen['warnings']:
                    for w in prescreen['warnings']:
                        st.warning(f"\u26a0\ufe0f {w}")
                st.info("This JD has hard dealbreakers for Praghya's profile. Generating a tailored resume would be a wasted effort. Skip this role.")
            else:
                # Show warnings but proceed
                if prescreen['warnings']:
                    st.warning("**JD Pre-Screen: Proceed with caution**")
                    for w in prescreen['warnings']:
                        st.warning(f"\u26a0\ufe0f {w}")

                with st.spinner("Harvesting keywords, bridging domains, optimising for ATS..."):
                    data = analyze_and_generate(google_key, base, jd)
                    if "error" in data:
                        st.error(data['error'])
                    else:
                        # Store prescreen results for display
                        data['_prescreen_warnings'] = prescreen['warnings']
                        st.session_state['data'] = data
                        st.rerun()
        else:
            st.warning("Please provide API Key and paste a Job Description.")

else:
    data = st.session_state['data']

    # Top bar
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown(f"## \U0001f3af Target: {data.get('target_company', 'Company')}")
    with c3:
        score = data.get('ats_score', 0)
        st.metric("ATS Match", f"{score}%")

    # Generation pass info (v1.1)
    gen_pass = data.get('generation_pass', 1)
    if gen_pass > 1:
        first_score = data.get('_first_pass_score', 0)
        improvement = data.get('_score_improvement', 0)
        st.success(f"\u267b\ufe0f Auto re-optimised: Pass 1 scored {first_score}% → Pass 2 scored {score}% (+{improvement} pts)")

    # Pre-screen warnings (v1.1)
    prescreen_warns = data.get('_prescreen_warnings', [])
    if prescreen_warns:
        with st.expander("\u26a0\ufe0f JD Pre-Screen Warnings", expanded=False):
            for w in prescreen_warns:
                st.warning(w)

    # Hallucination report (v1.1)
    hall_report = data.get('_hallucination_report', [])
    if hall_report:
        with st.expander(f"\U0001f6e1\ufe0f Anti-Hallucination: {len(hall_report)} items caught & removed", expanded=False):
            for item in hall_report:
                st.info(f"\u2702\ufe0f {item}")

    # Missing keywords alert
    missing = data.get('missing_keywords', '')
    if missing and str(missing).strip():
        st.warning(f"**Keywords still missing from resume:** {missing}")

    tab_edit, tab_export, tab_cover = st.tabs(["\U0001f4dd Editor", "\U0001f680 Export", "\u270d\ufe0f Cover Letter"])

    with tab_edit:
        with st.form("edit_form"):
            st.subheader("Candidate Details")
            c1, c2, c3 = st.columns(3)
            data['candidate_name'] = c1.text_input("Name", to_text_block(data.get('candidate_name')))
            data['candidate_title'] = c2.text_input("Title", to_text_block(data.get('candidate_title')))
            data['contact_info'] = c3.text_input("Contact", to_text_block(data.get('contact_info')))
            data['summary'] = st.text_area("Summary", to_text_block(data.get('summary')), height=120)

            st.subheader("Skills")
            skills = data.get('skills', {})
            new_skills = {}
            s_cols = st.columns(2)
            for i, (k, v) in enumerate(skills.items()):
                col = s_cols[i % 2]
                new_val = col.text_area(k, to_text_block(v), key=f"skill_{i}", height=80)
                new_skills[k] = new_val.replace('\n', ', ')
            data['skills'] = new_skills

            st.subheader("Experience")
            for i, role in enumerate(data.get('experience', [])):
                with st.expander(f"{role.get('role_title', 'Role')} @ {role.get('company', 'Company')}"):
                    c1, c2 = st.columns(2)
                    role['role_title'] = c1.text_input("Title", to_text_block(role.get('role_title')), key=f"jt_{i}")
                    role['company'] = c2.text_input("Company", to_text_block(role.get('company')), key=f"jc_{i}")
                    c3, c4 = st.columns(2)
                    role['dates'] = c3.text_input("Dates", to_text_block(role.get('dates')), key=f"jd_{i}")
                    role['location'] = c4.text_input("Location", to_text_block(role.get('location')), key=f"jl_{i}")
                    role['responsibilities'] = st.text_area("Responsibilities", to_text_block(role.get('responsibilities')), height=200, key=f"jr_{i}")
                    role['achievements'] = st.text_area("Achievements", to_text_block(role.get('achievements')), height=100, key=f"ja_{i}")

            st.subheader("Education")
            for i, edu in enumerate(data.get('education', [])):
                c1, c2 = st.columns(2)
                edu['degree'] = c1.text_input("Degree", to_text_block(edu.get('degree')), key=f"ed_{i}")
                edu['college'] = c2.text_input("Institution", to_text_block(edu.get('college')), key=f"ec_{i}")

            st.subheader("Certifications")
            for i, cert in enumerate(data.get('certifications', [])):
                cert_name = cert.get('name', '') if isinstance(cert, dict) else str(cert)
                new_name = st.text_input(f"Cert {i+1}", cert_name, key=f"cert_{i}")
                if isinstance(cert, dict):
                    cert['name'] = new_name
                else:
                    data['certifications'][i] = {'name': new_name}

            if st.form_submit_button("\U0001f4be Save Edits", type="primary"):
                st.session_state['data'] = data
                st.success("Saved!")
                st.rerun()

    with tab_export:
        st.subheader("\U0001f4e5 Download")
        c_name = data.get('candidate_name', 'Praghya_Prakhar')
        default_company = data.get('target_company', 'Company')
        target_company = st.text_input("Company (for filename)", default_company)

        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', c_name.strip().replace(' ', '_'))
        safe_company = re.sub(r'[^a-zA-Z0-9_-]', '_', target_company.strip())
        final_filename = f"{safe_name}_{safe_company}"

        c1, c2 = st.columns(2)

        doc_obj = create_doc(data)
        bio = io.BytesIO()
        doc_obj.save(bio)
        c1.download_button(
            label="\U0001f4c4 Word (.docx)",
            data=bio.getvalue(),
            file_name=f"{final_filename}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True,
        )

        try:
            pdf_data = create_pdf(data)
            c2.download_button(
                label="\U0001f4d5 PDF",
                data=pdf_data,
                file_name=f"{final_filename}.pdf",
                mime="application/pdf",
                type="secondary",
                use_container_width=True,
            )
        except Exception as e:
            c2.error(f"PDF Error: {e}")

    with tab_cover:
        st.subheader("\u270d\ufe0f Cover Letter")
        st.info("Generates a human-sounding cover letter using your best matching war story for this JD.")

        if st.button("\u2728 Draft Cover Letter", type="primary"):
            if google_key and st.session_state['saved_jd']:
                with st.spinner("Picking war story, drafting narrative..."):
                    cl_text = generate_cover_letter(google_key, data, st.session_state['saved_jd'])
                    st.session_state['cover_letter'] = cl_text
            else:
                st.warning("Need API key and JD.")

        if st.session_state['cover_letter']:
            edited_cl = st.text_area("Preview (editable)", st.session_state['cover_letter'], height=400)
            st.session_state['cover_letter'] = edited_cl

            cl_doc = create_cover_letter_doc(st.session_state['cover_letter'], data)
            bio_cl = io.BytesIO()
            cl_doc.save(bio_cl)
            st.download_button(
                label="\U0001f4c4 Download Cover Letter (.docx)",
                data=bio_cl.getvalue(),
                file_name=f"Cover_Letter_{final_filename}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )

    st.divider()
    c3, c4 = st.columns(2)
    if c3.button("\u267b\ufe0f Re-Optimise (Keyword Boost)", use_container_width=True):
        if st.session_state['saved_base'] and st.session_state['saved_jd']:
            # Feed missing keywords from current run into boost
            current_missing = st.session_state['data'].get('missing_keywords', '') if st.session_state['data'] else None
            with st.spinner("Re-tailoring with keyword boost..."):
                data = analyze_and_generate(
                    google_key,
                    st.session_state['saved_base'],
                    st.session_state['saved_jd'],
                    boost_keywords=current_missing
                )
                if "error" in data:
                    st.error(data['error'])
                else:
                    st.session_state['data'] = data
                    st.rerun()

    if c4.button("New Application (Keep Resume)", use_container_width=True):
        st.session_state['data'] = None
        st.session_state['saved_jd'] = ""
        st.session_state['cover_letter'] = None
        st.rerun()
