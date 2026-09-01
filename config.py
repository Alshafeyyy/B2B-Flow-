import os
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")

# All AI calls route through LLM Gateway (llmgateway.io) — a unified,
# OpenAI-compatible proxy in front of 40+ providers — so each pipeline stage can
# use whichever model actually fits it, rather than one fixed model for everything.
LLM_GATEWAY_API_KEY = os.getenv("LLM_GATEWAY_API_KEY", "")
LLM_GATEWAY_BASE_URL = os.getenv("LLM_GATEWAY_BASE_URL", "https://api.llmgateway.io/v1")

# Used for bulk qualification + lead-discovery contact briefs (both run many times
# per pipeline run, across many companies): Perplexity sonar, $1/$1 per M tokens +
# a flat $0.005/request. Kept off sonar-pro here deliberately — 15x pricier on
# output for a quality delta that isn't worth roughly halving how many bulk runs a
# small budget affords, and this stage doesn't need sonar-pro's extra depth anyway.
SEARCH_MODEL = os.getenv("SEARCH_MODEL", "sonar")

# Used only for the Deep-Dive tab's two research calls (deep_company_research,
# deep_contact_research) — a single, deliberately chosen target, not a bulk scan,
# so it's worth paying for real depth: Perplexity sonar-pro, $3/$15 per M tokens +
# a flat $0.005/request, 200K context (vs sonar's 130K) and genuinely more thorough
# multi-query search per Perplexity's own docs. Measured live against a real
# contact: ~$0.06/call (897 prompt + 3402 completion tokens) — a full company
# deep-dive (1 dossier + up to 5 contacts) runs well under $0.50 worst case.
DEEP_RESEARCH_MODEL = os.getenv("DEEP_RESEARCH_MODEL", "sonar-pro")

# Used only for contact selection (reasoning over an already-provided roster list —
# never needed web search): Groq gpt-oss-20b, $0.1/$0.5 per M tokens, no flat
# per-request fee, native JSON output. Over 20x cheaper than sonar for this one call.
REASONING_MODEL = os.getenv("REASONING_MODEL", "gpt-oss-20b")

OFFERING_DESCRIPTION = os.getenv(
    "OFFERING_DESCRIPTION",
    """ALX Enterprise — corporate upskilling for African organizations, delivered across three depth levels. IMPORTANT: this is FOUR EQUAL THEMES, not "AI plus some extras" — Data Analytics is actually the largest catalog (15+ modules), bigger than AI (7+ modules). Never default to an AI-themed offering out of habit; pick whichever theme the actual evidence points to.

1. ALX Enterprise Academy (self-paced online, per-seat/month, Tier 1-3: $17.99-$22.31, dedicated Learning Journey Manager from Tier 2 up), 4 equal themes:
   - Intelligence Artificielle (7+ modules): AI Career Essentials, Prompt Engineering, AI Productivity, Data and AI Literacy Foundations, AI Ethics
   - Data Analytics (15+ modules, the LARGEST catalog): Data Analytics, Data Analytics with Spreadsheets, PowerBI for Data Analytics, Data Science
   - Leadership & Management (5+ modules): Teamwork & Agile Workflows, Communication & Professional Writing, Self-Leadership & Learning Foundations
   - Innovation & Business (10+ modules): Business Strategy, Startup Operations, Project Management, Investment Readiness (Fundraising Essentials)

2. Ateliers & Workshops (1-2 day in-person, token-based — 1 token = 1 session for 20 people):
   - AI Productivity — operational & support teams (high-volume email/reporting/documentation work)
   - AI Strategic Roadmap — executives & transformation leaders defining where AI creates value
   - Decision Intelligence — senior executives & functional leaders (strategy, ops, financial performance owners)
   - Lead & Manage in the Age of AI — frontline/first-line managers
   - High-Performance Execution — Codir/executive committee & functional heads (unclear ownership, weak operating rhythm, cross-team friction)
   - Cross-Generational Manager — managers of mixed-generation teams (feedback, psychological safety, reverse mentoring, retention)

3. Leadership Xcelerator (6-month hybrid program, 2-day intensives monthly, for managers & emerging leaders): Self-Leadership, Commercial Leadership, People Leadership (coaching/feedback/conflict), Strategic Leadership, Execution. Differentiators: ROI-oriented, research-based methodology, built-in accountability, an intentional support community — NOT a single workshop, a sustained 6-month engagement. This is the right recommendation (over a 1-2 day workshop) whenever the underlying signal is a genuine, sustained capability gap rather than a one-off skills need — e.g. real leadership-pipeline risk, chronic retention problems, or persistent resistance to change.

WHO ACTUALLY BUYS/CHAMPIONS THIS (from ALX's own persona research):
- "Karim"-type buyer: senior operations/functional executive (e.g. Director of Operations), extremely time-constrained, skeptical of generic training, needs concrete methods with fast measurable ROI ("if I see impact in 2 weeks, I'll go further"). This is the actual budget-holder archetype — pitches to this type must lead with efficiency/ROI, not generic upskilling language.
- "Youssef"-type champion: individual contributor / functional specialist (e.g. Data Analyst), curious, self-directed, wants practical AI/automation skills for career growth. Not the budget holder, but a real internal advocate worth engaging.

ORGANIZATIONAL SIGNALS THAT PREDICT REAL FIT (from ALX's own market research, sourced from WEF, McKinsey, Gallup, Microsoft, Gartner, Deloitte, LinkedIn, NewVantage Partners 2024-2025 — judge fit from evidence, not assumption), each mapped to the REAL offering that actually fits it best — use this table, do not default to AI-named offerings when the evidence points elsewhere:
1. Skills gap (63%) → whichever Academy theme matches the SPECIFIC skill missing (Data Analytics, Leadership & Management, Innovation & Business, or AI) — this is the one signal that spans all four themes equally.
2. AI adoption happening WITHOUT a governance framework (78% prevalence — the single most common signal, but only the right fit when the evidence is genuinely about AI/digital rollout) → AI Strategic Roadmap workshop, or the Academy's AI theme.
3. Manager/leadership readiness gaps (70%) → Lead & Manage in the Age of AI workshop for a single acute gap; Leadership Xcelerator when the gap looks structural/ongoing rather than a one-off need.
4. Resistance to change (60%) → Cross-Generational Manager workshop, or Leadership Xcelerator's change-management thread — rarely an AI-themed fit.
5. Team productivity friction (57%) → AI Productivity workshop if the friction is tool/workflow-based; High-Performance Execution workshop if it's about unclear ownership or operating rhythm instead — these are different root causes, pick based on which one the evidence actually shows.
6. Innovation capacity constraints (52%) → Innovation & Business Academy theme (Business Strategy, Startup Operations, Project Management, Investment Readiness) — genuinely not an AI topic; this theme is the correct fit and is under-used in practice.
7. Talent retention pressure (51%) → Leadership Xcelerator's People Leadership module (retention is fundamentally a management-quality problem), or the Academy's Leadership & Management theme, or Cross-Generational Manager.
8. Weak data-driven decision-making (under 33% of organizations are strong here) → Decision Intelligence workshop, or the Academy's Data Analytics theme (the largest catalog — genuinely worth citing on its own, not just as a footnote to AI).

A company showing public evidence of two or more signals (digital transformation news, AI pilot announcements, leadership/management hiring, active recruitment for digital/data/AI roles, a stated modernization strategy, visible retention challenges) is a strong candidate — regardless of how "obviously tech" its industry looks. Do not default to Go purely on size or industry; do not default to No-Go purely on being a "traditional" sector — Bank Al-Maghrib itself names AI/digital as a modernization priority for Moroccan banking, and ALX has proven placements across banking, telecom, retail, tech, and pharma-adjacent sectors alike.

PROVEN TRACK RECORD (use for credible, specific proof points — not generic claims):
- 470+ corporate clients, 3,000+ enterprise learners trained to date
- Platform-wide (pan-Africa): 698,445 learners enrolled, 347K+ graduates, 172K+ youth placed into jobs (2024)
- Real attributed hires/promotions: Orange Maroc (Pricing Analyst), Sophatel (Software Engineer), Veeva Systems (Data Analyst), Carrefour Maroc (Business & Data Analyst, repeat hirer)
- Differentiator vs pure e-learning platforms: dedicated local Morocco team + a named Learning Journey Manager per client engagement, not fully remote/self-serve
- Strategic partnership with Mastercard Foundation (goal: 3M tech talents trained across Africa by 2030)"""
)

# Apollo Search Criteria
DEFAULT_LOCATIONS = ["Morocco"]
DEFAULT_EMPLOYEE_RANGES = ["51,200", "201,500", "501,1000", "1001,5000", "5001,10000"]
DEFAULT_INDUSTRIES = ["banking", "financial services", "telecommunications", "retail", "technology", "pharmaceuticals", "manufacturing", "consulting", "logistics"]
DEFAULT_COMPANY_LIMIT = 50

# Default Contact Roles (used if AI suggestions are empty or supplementary)
DEFAULT_CONTACT_TITLES = [
    "Chief Human Resources Officer",
    "Human Resources Director",
    "Head of HR",
    "Learning and Development Director",
    "Head of L&D",
    "Chief Operating Officer",
    "Chief Digital Officer",
    "Chief Technology Officer",
    "Head of Transformation",
    "Head of People"
]
