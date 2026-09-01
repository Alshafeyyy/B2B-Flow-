import os
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")

# All AI calls route through LLM Gateway (llmgateway.io) — a unified,
# OpenAI-compatible proxy in front of 40+ providers — so each pipeline stage can
# use whichever model actually fits it, rather than one fixed model for everything.
LLM_GATEWAY_API_KEY = os.getenv("LLM_GATEWAY_API_KEY", "")
LLM_GATEWAY_BASE_URL = os.getenv("LLM_GATEWAY_BASE_URL", "https://api.llmgateway.io/v1")

# Used for qualification + all deep research (needs real-time web search): Perplexity
# sonar, $1/$1 per M tokens + a flat $0.005/request. Kept off sonar-pro deliberately —
# 15x pricier on output for a quality delta that isn't worth roughly halving how many
# runs a small budget affords.
SEARCH_MODEL = os.getenv("SEARCH_MODEL", "sonar")

# Used only for contact selection (reasoning over an already-provided roster list —
# never needed web search): Groq gpt-oss-20b, $0.1/$0.5 per M tokens, no flat
# per-request fee, native JSON output. Over 20x cheaper than sonar for this one call.
REASONING_MODEL = os.getenv("REASONING_MODEL", "gpt-oss-20b")

OFFERING_DESCRIPTION = os.getenv(
    "OFFERING_DESCRIPTION",
    """ALX Enterprise — corporate upskilling for African organizations, delivered across three depth levels:

1. ALX Enterprise Academy (self-paced, online): AI (AI Career Essentials, Prompt Engineering, AI Productivity, Data & AI Literacy, AI Ethics), Data Analytics (incl. Data Analytics with Spreadsheets, PowerBI, Data Science), Leadership & Management (Teamwork & Agile Workflows, Communication, Self-Leadership), and Innovation & Business (Strategy, Startup Operations, Project Management). Priced per-seat/month (Tier 1-3: $17.99-$22.31), with a dedicated Learning Journey Manager (LJM) from Tier 2 up.

2. Ateliers & Workshops (1-2 day in-person, token-based):
   - AI Productivity — for operational & support teams (high-volume email/reporting/documentation work)
   - AI Strategic Roadmap — for executives & transformation leaders defining where AI creates value
   - Decision Intelligence — for senior executives & functional leaders (strategy, ops, financial performance owners)
   - Lead & Manage in the Age of AI — for frontline/first-line managers
   - High-Performance Execution — for Codir/executive committee & functional heads
   - Cross-Generational Manager — for managers of mixed-generation teams

3. Leadership Xcelerator (6-month hybrid program): for managers & emerging leaders — Self-Leadership, Commercial Leadership, People Leadership (coaching/feedback), Strategic Leadership, Execution.

WHO ACTUALLY BUYS/CHAMPIONS THIS (from ALX's own persona research):
- "Karim"-type buyer: senior operations/functional executive (e.g. Director of Operations), extremely time-constrained, skeptical of generic training, needs concrete methods with fast measurable ROI ("if I see impact in 2 weeks, I'll go further"). This is the actual budget-holder archetype — pitches to this type must lead with efficiency/ROI, not generic upskilling language.
- "Youssef"-type champion: individual contributor / functional specialist (e.g. Data Analyst), curious, self-directed, wants practical AI/automation skills for career growth. Not the budget holder, but a real internal advocate worth engaging.

ORGANIZATIONAL SIGNALS THAT PREDICT REAL FIT (from ALX's own market research, sourced from WEF, McKinsey, Gallup, Microsoft, Gartner, Deloitte, LinkedIn, NewVantage Partners 2024-2025 — judge fit from evidence, not assumption):
1. Skills gap (63% of organizations report this)
2. AI adoption happening WITHOUT a governance framework (78% prevalence — the single most common and highest-impact signal: companies experimenting with AI ad hoc, without structured rollout)
3. Manager/leadership readiness gaps (70%)
4. Resistance to change (60%)
5. Team productivity friction (57%)
6. Innovation capacity constraints (52%)
7. Talent retention pressure (51%)
8. Weak data-driven decision-making (under 33% of organizations are strong here)

A company showing public evidence of two or more of these (digital transformation news, AI pilot announcements, leadership/management hiring, active recruitment for digital/data/AI roles, a stated modernization strategy, visible retention challenges) is a strong candidate — regardless of how "obviously tech" its industry looks. Do not default to Go purely on size or industry; do not default to No-Go purely on being a "traditional" sector — Bank Al-Maghrib itself names AI/digital as a modernization priority for Moroccan banking, and ALX has proven placements across banking, telecom, retail, tech, and pharma-adjacent sectors alike.

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
