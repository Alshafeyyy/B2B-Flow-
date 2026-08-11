import logging
import requests
import json
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PerplexityClient")

class PerplexityClient:
    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str, model: str = "sonar"):
        self.api_key = api_key
        self.model = model
        if not self.api_key:
            logger.warning("Perplexity API Key is missing! Set PERPLEXITY_API_KEY in your .env file.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def qualify_company_and_suggest_roles(self, company: Dict[str, Any], offering_context: str) -> Dict[str, Any]:
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
1. Assess this company against the ORGANIZATIONAL SIGNALS listed in OUR OFFERING above. Look for genuine public evidence (news, described initiatives, hiring patterns, stated strategy) of 2+ of those signals — not assumptions based on size or industry alone. Classify as:
   - "Go": clear public evidence of 2+ signals, or one strong signal (e.g. an explicit AI/digital transformation initiative) at a company large enough to plausibly have a structured HR/L&D function.
   - "Review": plausible fit (right size/sector, no disqualifying evidence) but not enough public evidence either way to be confident — needs human judgment.
   - "No-Go": clear evidence this isn't a fit (e.g. too small to plausibly have any L&D function, or no credible connection to the signals).
   Do not default to Go purely because the company is large or in banking/tech; do not default to No-Go purely because it's a "traditional" sector. Give a single-sentence reason that names the SPECIFIC signal(s) found or missing — not a generic statement.
2. Suggest 3 to 5 ideal target job FUNCTIONS to reach out to, chosen from what's actually relevant given which signal(s) you found — use the workshop audiences in OUR OFFERING as a guide (e.g. an AI-governance-gap signal → transformation/digital leadership roles; a manager-readiness signal → HR/L&D and frontline management roles; a productivity/retention signal → HR and operations leadership; a decision-making signal → senior functional/financial leadership).

Respond strictly with valid JSON with these 3 keys (no markdown code blocks, no extra text):
{{
  "status": "Go" | "No-Go" | "Review",
  "reason": "Single short sentence naming the specific signal(s) found or missing.",
  "suggested_roles": ["Title 1", "Title 2", "Title 3"]
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an analytical B2B sales screening assistant. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            response = requests.post(self.API_URL, json=payload, headers=self._headers(), timeout=30)
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
            logger.error(f"Perplexity company qualification error for {name}: {e}")
            return {
                "status": "Review",
                "reason": f"AI Evaluation completed with fallback: {str(e)}",
                "suggested_roles": ["Human Resources Director", "Head of L&D", "COO", "Chief Digital Officer", "CTO"]
            }

    def select_best_contacts(
        self,
        company: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        offering_context: str,
        suggested_roles: List[str] = None,
        max_selections: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Phase 2a AI Selection: Given the company's real contact roster (first name +
        job title only — nobody was pre-filtered by title, since Apollo's title match
        is fairly literal and misses real people whose title differs from AI-guessed
        phrasing), selects the best-fit people to reach out to. Returns the selected
        subset of `candidates`, each tagged with `_selection_reason`.
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
Select up to {max_selections} people from this REAL roster who are the best targets for our offering. Match each person's real title to the workshop audiences and buyer personas described in OUR OFFERING (e.g. a Director of Operations or functional exec is a "Karim"-type budget-holder worth prioritizing; an HR/L&D lead is a likely programme owner; a Digital/Transformation lead fits the AI Strategic Roadmap audience; a frontline manager fits Lead & Manage in the Age of AI). Prioritize genuine decision-makers and functional fits over generic seniority. Only select from the numbered roster above — do not invent people or renumber them. If fewer than {max_selections} are good fits, select fewer.

Respond strictly with valid JSON (no markdown code blocks, no extra text):
{{
  "selections": [
    {{"index": <roster number>, "reason": "One short sentence on why this person is a good target."}}
  ]
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an analytical B2B sales targeting assistant. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            response = requests.post(self.API_URL, json=payload, headers=self._headers(), timeout=30)
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
            logger.error(f"Perplexity contact selection error for {name}: {e}")
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
        offering_context: str
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

For the opening_sales_angle specifically: first judge whether this contact is closer to the "Karim" archetype (senior operational/functional executive — lead with efficiency/ROI, fast measurable payback, skip generic upskilling language) or the "Youssef" archetype (functional specialist/individual contributor — lead with practical skill-building and career growth) from OUR OFFERING above, and write the angle in that register. Name the SPECIFIC relevant offering (e.g. the "AI Strategic Roadmap" workshop, the "Decision Intelligence" workshop, or the Academy) rather than generic "training", and cite one real proof point (a stat or named client reference from OUR OFFERING) rather than a generic claim.

Respond strictly in valid JSON format with these 4 keys (no markdown code blocks, no extra text):
{{
  "contact_insights": "Detailed information about the contact including their background, career experience, education, tenure at the company, and key role responsibilities.",
  "opening_sales_angle": "A highly tailored, persona-matched opening pitch hook naming a specific ALX offering and a real proof point, connecting directly to this contact's role and company's likely pain signal(s).",
  "target_company_brief": "An internal brief on company scale, and which of the 8 organizational signals (from OUR OFFERING) this company shows evidence of, and the resulting workforce training needs.",
  "industry_position": "Analysis of current industry trends and where this company sits relative to competitors in digital and AI adoption."
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional enterprise sales intelligence researcher. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.API_URL, json=payload, headers=self._headers(), timeout=45)
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
            logger.error(f"Perplexity deep research error for {contact_name} at {comp_name}: {e}")
            return {
                "contact_insights": f"{contact_name} serves as {contact_title} at {comp_name}.",
                "opening_sales_angle": "Highlight ALX Enterprise corporate training bootcamps in Data, AI & Leadership.",
                "company_brief": f"{comp_name} ({industry}) operates in {location}.",
                "industry_position": "Industry digital journey."
            }
