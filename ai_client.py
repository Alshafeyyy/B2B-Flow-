import logging
import requests
import json
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIClient")

class AIClient:
    """
    Routes every AI call through LLM Gateway (llmgateway.io) — a unified,
    OpenAI-compatible proxy in front of 40+ providers — so each method below can
    take its own `model` per call instead of one fixed model for everything. Search
    methods (qualification, deep research) are meant to be called with a real-time
    web-search-capable model (e.g. Perplexity's "sonar"); select_best_contacts only
    reasons over an already-provided roster list and never needed search, so it's
    meant to be called with a cheap plain-reasoning model instead (e.g. Groq's
    "gpt-oss-20b") — see config.py's SEARCH_MODEL / REASONING_MODEL.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.llmgateway.io/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            logger.warning("LLM Gateway API Key is missing! Set LLM_GATEWAY_API_KEY in your .env file.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def qualify_company_and_suggest_roles(self, company: Dict[str, Any], offering_context: str, model: str) -> Dict[str, Any]:
        """
        Phase 1 AI Assessment: Screens company fit (Go / No-Go / Review + Reason) AND suggests
        the ideal target contact job roles to reach out to inside this specific company.
        """
        name = company.get("name", "Unknown Company")
        industry = company.get("industry", "Unknown")
        employees = company.get("estimated_num_employees", company.get("num_employees", "Unknown"))
        city = company.get("city", "")
        country = company.get("country", "")
        location = f"{city}, {country}".strip(", ") or "Morocco"
        short_desc = company.get("short_description", company.get("snippet", "No description provided"))

        prompt = f"""You are a B2B sales qualification AI for ALX Enterprise Morocco.

OUR OFFERING:
{offering_context}

TARGET COMPANY TO EVALUATE:
- Name: {name}
- Industry: {industry}
- Location: {location}
- Employees: {employees}
- Description: {short_desc}

TASK:
1. Assess this company's fit using BOTH company-specific evidence (news, initiatives, hiring patterns) AND sector-level evidence from the signal research in OUR OFFERING (e.g. the banking-wide AI/digital modernization pressure cited above applies to any genuine, established bank — you do not need a press release about that exact bank's internal programs to credit it). Classify as:
   - "Go": the company is a real, established player (genuine headcount, genuine market presence — not a shell or single-location micro business) in a sector/segment where OUR OFFERING's signal research shows credible pressure, OR there's direct company-specific evidence of a signal. Sector-level evidence is sufficient on its own for an established company in a sector OUR OFFERING already flags (e.g. banking) — being unable to find a news article about THIS exact company is normal and NOT a reason to avoid Go.
   - "Review": genuinely ambiguous — unclear/very small size, an obscure or mixed-signal sector not covered by OUR OFFERING's research, or conflicting evidence.
   - "No-Go": clear evidence this isn't a fit (too small to plausibly have any structured L&D function, or a business type with no credible connection to any signal).
   Do not default to Review just because company-specific news wasn't found — use sector-level evidence and company characteristics instead. Do not default to Go purely on size with zero sector/signal relevance; do not default to No-Go purely for being a "traditional" sector. Give a single-sentence reason naming the SPECIFIC signal or evidence used.
2. Suggest 3 to 5 ideal target job FUNCTIONS to reach out to, chosen from what's actually relevant given which signal(s) you found — use the signal-to-offering table in OUR OFFERING as a guide (e.g. an AI-governance-gap signal → transformation/digital leadership roles; a manager-readiness or retention signal → HR/L&D and people leadership roles; an innovation-capacity signal → strategy/business development/product leadership roles; a productivity/execution signal → operations leadership; a decision-making signal → senior functional/financial leadership). Do not let AI-related signals crowd out the others — most real companies' evidence points to a mix.

Respond strictly with valid JSON with these 3 keys (no markdown code blocks, no extra text):
{{
  "status": "Go" | "No-Go" | "Review",
  "reason": "Single short sentence naming the specific signal(s) found or missing.",
  "suggested_roles": ["Title 1", "Title 2", "Title 3"]
}}"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an analytical B2B sales screening assistant. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            response = requests.post(self._url(), json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            status = result.get("status", "Review")
            if "go" in status.lower() and "no" not in status.lower():
                status = "Go"
            elif "no" in status.lower():
                status = "No-Go"
            else:
                status = "Review"

            return {
                "status": status,
                "reason": result.get("reason", "Evaluated based on company profile."),
                "suggested_roles": result.get("suggested_roles", ["HR Director", "Head of L&D", "COO", "CTO", "Head of Digital"])
            }
        except Exception as e:
            logger.error(f"AI company qualification error for {name}: {e}")
            return {
                "status": "Review",
                "reason": f"AI Evaluation completed with fallback: {str(e)}",
                "suggested_roles": ["Human Resources Director", "Head of L&D", "COO", "Chief Digital Officer", "CTO"]
            }

    def deep_company_research(self, company: Dict[str, Any], offering_context: str, model: str) -> Dict[str, str]:
        """
        Account Deep-Dive: produces a full research dossier on ONE specific, already-
        chosen company — recent news, initiatives, leadership context, and competitive
        position — grounded in the same 8 organizational signals used for qualification,
        but without the Go/No-Go framing (this company was picked deliberately, not
        screened from a list).
        """
        name = company.get("name", "Unknown Company")
        industry = company.get("industry", "Unknown")
        employees = company.get("estimated_num_employees", company.get("num_employees", "Unknown"))
        city = company.get("city", "")
        country = company.get("country", "")
        location = f"{city}, {country}".strip(", ") or "Morocco"
        short_desc = company.get("short_description", company.get("snippet", "No description provided"))
        website = company.get("website_url", "")

        prompt = f"""You are a senior B2B account researcher for ALX Enterprise Morocco, preparing a deep research dossier ahead of a real meeting with this company.

OUR OFFERING:
{offering_context}

TARGET COMPANY:
- Name: {name}
- Industry: {industry}
- Location: {location}
- Employees: {employees}
- Website: {website}
- Description: {short_desc}

Perform real public web research on this specific company. Produce a genuine, detailed dossier — not generic filler — covering:
1. Which of the 8 organizational signals from OUR OFFERING this company shows real evidence of (company-specific news/initiatives where findable, sector-level evidence otherwise), and why that matters for them specifically.
2. Recent developments: news, initiatives, leadership changes, expansions, or public strategic statements from the last 1-2 years.
3. Competitive/industry position: where this company sits versus peers — cover whichever dimension the evidence actually supports (digital/AI maturity, operational execution, talent/retention, innovation capacity, data-driven decision-making), not only digital/AI.
4. Concrete, meeting-ready talking points: 2-3 specific things worth raising in a real conversation with this company, each tied to what was actually found AND naming the specific real ALX offering that fits (using the signal-to-offering table in OUR OFFERING — the real catalog spans 4 equal Academy themes, 6 workshops, and Leadership Xcelerator; do not default to AI-themed offerings when the evidence points elsewhere).

Respond strictly with valid JSON with these 4 keys (no markdown code blocks, no extra text):
{{
  "signals_found": "Which signals apply and the specific evidence for each.",
  "recent_developments": "Real recent news/initiatives/leadership context found through research.",
  "competitive_position": "Where this company sits versus peers on the dimension the evidence actually supports.",
  "meeting_talking_points": "2-3 concrete, specific points worth raising, each naming the specific real ALX offering that fits."
}}"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a thorough enterprise account researcher. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self._url(), json=payload, headers=self._headers(), timeout=45)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            return {
                "signals_found": result.get("signals_found", "No specific signals identified."),
                "recent_developments": result.get("recent_developments", "No recent public developments found."),
                "competitive_position": result.get("competitive_position", f"{name} operates in {industry}."),
                "meeting_talking_points": result.get("meeting_talking_points", "")
            }
        except Exception as e:
            logger.error(f"AI deep company research error for {name}: {e}")
            return {
                "signals_found": f"Research unavailable: {str(e)}",
                "recent_developments": "Not available.",
                "competitive_position": f"{name} operates in {industry} in {location}.",
                "meeting_talking_points": "Not available."
            }

    def select_best_contacts(
        self,
        company: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        offering_context: str,
        model: str,
        suggested_roles: List[str] = None,
        max_selections: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Phase 2a AI Selection: Given the company's real contact roster (first name +
        job title only — nobody was pre-filtered by title, since Apollo's title match
        is fairly literal and misses real people whose title differs from AI-guessed
        phrasing), selects the best-fit people to reach out to. Returns the selected
        subset of `candidates`, each tagged with `_selection_reason`. Pure reasoning
        over an already-provided list — never needs web search, so this is meant to
        be called with a cheap plain-reasoning model (see config.REASONING_MODEL).
        """
        name = company.get("name", "Unknown Company")
        industry = company.get("industry", "Unknown")

        roster_text = "\n".join(
            f"{i}. {c.get('first_name') or 'Unknown'} — {c.get('title') or 'Unknown Title'}"
            for i, c in enumerate(candidates)
        )
        roles_hint = ", ".join(suggested_roles) if suggested_roles else \
            "HR, Learning & Development, Digital/IT, Operations/Transformation, executive leadership"

        prompt = f"""You are a B2B sales targeting AI for ALX Enterprise Morocco.

OUR OFFERING:
{offering_context}

TARGET COMPANY: {name} ({industry})

EARLIER ANALYSIS SUGGESTED THESE FUNCTIONAL AREAS AS GOOD FITS (use as guidance, not a strict filter — real titles rarely match this phrasing exactly):
{roles_hint}

REAL ROSTER OF PEOPLE APOLLO HAS ON FILE AT THIS COMPANY (first name + job title only, numbered):
{roster_text}

TASK:
Select up to {max_selections} people from this REAL roster who are the best targets for our offering. Match each person's real title to the workshop audiences and buyer personas described in OUR OFFERING (e.g. a Director of Operations or functional exec is a "Karim"-type budget-holder worth prioritizing; an HR/L&D lead is a likely programme owner for retention/leadership signals; a Digital/Transformation lead fits the AI Strategic Roadmap audience; a frontline manager fits Lead & Manage in the Age of AI; a strategy/business-development/product lead fits the Innovation & Business theme; a finance/BI/analytics lead fits Decision Intelligence or the Data Analytics theme). Prioritize genuine decision-makers and functional fits over generic seniority — do not default to Digital/IT roles out of habit when the roster has an equally or more relevant fit elsewhere. Only select from the numbered roster above — do not invent people or renumber them. If fewer than {max_selections} are good fits, select fewer.

Respond strictly with valid JSON (no markdown code blocks, no extra text):
{{
  "selections": [
    {{"index": <roster number>, "reason": "One short sentence on why this person is a good target."}}
  ]
}}"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an analytical B2B sales targeting assistant. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            response = requests.post(self._url(), json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            selections = result.get("selections", [])

            picked = []
            for sel in selections[:max_selections]:
                idx = sel.get("index")
                if isinstance(idx, int) and 0 <= idx < len(candidates):
                    picked.append({**candidates[idx], "_selection_reason": sel.get("reason", "")})

            if not picked:
                raise ValueError("AI returned no usable selections")
            return picked

        except Exception as e:
            logger.error(f"AI contact selection error for {name}: {e}")
            # Fail-soft: take the first max_selections roster entries rather than
            # losing this company's contacts entirely.
            return [
                {**c, "_selection_reason": "Selected by default (AI selection unavailable)."}
                for c in candidates[:max_selections]
            ]

    def generate_deep_contact_brief(
        self,
        contact: Dict[str, Any],
        company: Dict[str, Any],
        offering_context: str,
        model: str
    ) -> Dict[str, str]:
        """
        Phase 2 AI Research Engine: Performs deep research on the contact and company, returning
        rich insights on contact experience/education, tailored sales angle, target company brief, and industry positioning.
        """
        contact_name = contact.get("name", f"{contact.get('first_name', '')} {contact.get('last_name', '')}").strip()
        contact_title = contact.get("title", "Executive")
        contact_email = contact.get("email", "Not provided")
        contact_linkedin = contact.get("linkedin_url", "")
        contact_headline = contact.get("headline", "")

        comp_name = company.get("name", "Unknown Company")
        industry = company.get("industry", "Unknown")
        location = f"{company.get('city', '')}, {company.get('country', '')}".strip(", ") or "Morocco"
        desc = company.get("short_description", "")

        prompt = f"""You are a senior sales researcher for ALX Enterprise Morocco preparing a comprehensive pre-call brief for a sales executive.

OUR OFFERING:
{offering_context}

TARGET CONTACT DETAILS:
- Name: {contact_name}
- Job Title: {contact_title}
- Headline/Summary: {contact_headline}
- LinkedIn: {contact_linkedin}
- Email: {contact_email}

TARGET COMPANY DETAILS:
- Name: {comp_name}
- Industry: {industry}
- Location: {location}
- Description: {desc}

Perform public web research on this contact and company to produce 4 detailed, high-value sales briefing sections.

For the opening_sales_angle specifically: first judge whether this contact is closer to the "Karim" archetype (senior operational/functional executive — lead with efficiency/ROI, fast measurable payback, skip generic upskilling language) or the "Youssef" archetype (functional specialist/individual contributor — lead with practical skill-building and career growth) from OUR OFFERING above, and write the angle in that register. Use the signal-to-offering table in OUR OFFERING to name the SPECIFIC real offering that matches the evidence found — this spans 4 equal Academy themes (AI, Data Analytics — the largest catalog, Leadership & Management, Innovation & Business), 6 named workshops, and the 6-month Leadership Xcelerator program. Do NOT default to an AI-themed offering out of habit — most companies' real evidence points elsewhere (retention, execution friction, innovation capacity, data-driven decisions), and the pitch should reflect whichever theme the evidence actually shows, not the most familiar one. Cite one real proof point (a stat or named client reference from OUR OFFERING) rather than a generic claim.

Respond strictly in valid JSON format with these 4 keys (no markdown code blocks, no extra text):
{{
  "contact_insights": "Detailed information about the contact including their background, career experience, education, tenure at the company, and key role responsibilities.",
  "opening_sales_angle": "A highly tailored, persona-matched opening pitch hook naming a specific ALX offering and a real proof point, connecting directly to this contact's role and company's likely pain signal(s).",
  "target_company_brief": "An internal brief on company scale, and which of the 8 organizational signals (from OUR OFFERING) this company shows evidence of, and the resulting workforce training needs.",
  "industry_position": "Analysis of current industry trends and where this company sits relative to competitors in digital and AI adoption."
}}"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional enterprise sales intelligence researcher. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self._url(), json=payload, headers=self._headers(), timeout=45)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            brief_json = json.loads(raw_text)
            return {
                "contact_insights": brief_json.get("contact_insights", f"Contact: {contact_name}, {contact_title} at {comp_name}."),
                "opening_sales_angle": brief_json.get("opening_sales_angle", "Focus on workforce AI & digital skills modernization."),
                "company_brief": brief_json.get("company_brief", f"{comp_name} is a key player in {industry} in {location}."),
                "industry_position": brief_json.get("industry_position", "Digital transformation priority.")
            }
        except Exception as e:
            logger.error(f"AI deep research error for {contact_name} at {comp_name}: {e}")
            return {
                "contact_insights": f"{contact_name} serves as {contact_title} at {comp_name}.",
                "opening_sales_angle": "Highlight ALX Enterprise corporate training bootcamps in Data, AI & Leadership.",
                "company_brief": f"{comp_name} ({industry}) operates in {location}.",
                "industry_position": "Industry digital journey."
            }

    def deep_contact_research(
        self,
        contact: Dict[str, Any],
        company: Dict[str, Any],
        offering_context: str,
        model: str
    ) -> Dict[str, str]:
        """
        Account Deep-Dive: a deeper version of generate_deep_contact_brief for the
        small number of contacts actually selected ahead of a real meeting. Adds an
        explicit search for public professional presence (articles, interviews,
        quotes, blog mentions) on top of the standard persona-matched pitch — and is
        explicitly scoped to the professional public record only, never personal-life
        details (family, hobbies, personal social activity), even if technically
        discoverable.
        """
        contact_name = contact.get("name", f"{contact.get('first_name', '')} {contact.get('last_name', '')}").strip()
        contact_title = contact.get("title", "Executive")
        contact_linkedin = contact.get("linkedin_url", "")
        contact_headline = contact.get("headline", "")

        comp_name = company.get("name", "Unknown Company")
        industry = company.get("industry", "Unknown")
        location = f"{company.get('city', '')}, {company.get('country', '')}".strip(", ") or "Morocco"

        prompt = f"""You are a senior sales researcher for ALX Enterprise Morocco preparing deep, meeting-ready research on one specific contact ahead of a real meeting.

OUR OFFERING:
{offering_context}

TARGET CONTACT:
- Name: {contact_name}
- Job Title: {contact_title}
- Headline/Summary: {contact_headline}
- LinkedIn: {contact_linkedin}

TARGET COMPANY: {comp_name} ({industry}, {location})

Perform real public web research on this specific person. Scope: their PROFESSIONAL public record only — career background, public statements, articles, interviews, conference talks, or blog posts that name them. Do NOT search for or report personal-life details (family, hobbies, personal social activity) even if something is technically discoverable — this is for professional meeting prep, not personal profiling.

Produce 5 sections:
1. Professional background: career history, tenure, scope of responsibility, based on genuine research.
2. Public presence: any real articles, interviews, quotes, conference appearances, or blog mentions naming this person, with enough detail to reference in conversation. If genuinely nothing is found, say so plainly rather than inventing something.
3. Opening sales angle: judge whether this contact is closer to the "Karim" archetype (senior executive — lead with efficiency/ROI) or "Youssef" archetype (specialist/IC — lead with skill-building/growth) from OUR OFFERING, and write the angle in that register. Use the signal-to-offering table in OUR OFFERING to name the SPECIFIC real offering matching the evidence found — do NOT default to an AI-themed offering out of habit; the real catalog spans 4 equal Academy themes (Data Analytics is the largest, not AI), 6 named workshops, and the 6-month Leadership Xcelerator — pick whichever one the evidence actually points to, plus a real proof point.
4. Company brief: which of the 8 organizational signals this company shows evidence of, which real ALX offering(s) actually fit that signal (per the signal-to-offering table), and the resulting training needs.
5. Meeting prep note: one practical suggestion for how to open or steer a real conversation with this specific person, grounded in what was actually found about them.

Respond strictly with valid JSON with these 5 keys (no markdown code blocks, no extra text):
{{
  "professional_background": "...",
  "public_presence": "...",
  "opening_sales_angle": "...",
  "company_brief": "...",
  "meeting_prep_note": "..."
}}"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional enterprise sales intelligence researcher. Stay strictly within someone's professional public record. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self._url(), json=payload, headers=self._headers(), timeout=45)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            return {
                "professional_background": result.get("professional_background", f"{contact_name} serves as {contact_title} at {comp_name}."),
                "public_presence": result.get("public_presence", "No public articles, interviews, or mentions found."),
                "opening_sales_angle": result.get("opening_sales_angle", "Highlight ALX Enterprise corporate training bootcamps in Data, AI & Leadership."),
                "company_brief": result.get("company_brief", f"{comp_name} ({industry}) operates in {location}."),
                "meeting_prep_note": result.get("meeting_prep_note", "")
            }
        except Exception as e:
            logger.error(f"AI deep contact research error for {contact_name} at {comp_name}: {e}")
            return {
                "professional_background": f"{contact_name} serves as {contact_title} at {comp_name}.",
                "public_presence": "Research unavailable.",
                "opening_sales_angle": "Highlight ALX Enterprise corporate training bootcamps in Data, AI & Leadership.",
                "company_brief": f"{comp_name} ({industry}) operates in {location}.",
                "meeting_prep_note": ""
            }
