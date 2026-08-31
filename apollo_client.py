import logging
import requests
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApolloClient")

class ApolloClient:
    BASE_URL = "https://app.apollo.io/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            logger.warning("Apollo API Key is empty! Make sure APOLLO_API_KEY is configured in your .env file.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "x-api-key": self.api_key
        }

    def search_organizations(
        self,
        locations: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        employee_ranges: Optional[List[str]] = None,
        revenue_range: Optional[Dict[str, int]] = None,
        job_titles: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Phase 1: Searches for organizations on Apollo based on country, industry keywords,
        employee size, annual revenue, and (optionally) roles the company is currently
        hiring for — a strong buying-intent signal for digital/data/AI-related offerings.
        """
        url = f"{self.BASE_URL}/organizations/search"

        payload: Dict[str, Any] = {
            "page": page,
            "per_page": per_page
        }

        if locations:
            payload["organization_locations"] = locations
        if keywords:
            payload["q_organization_keyword_tags"] = keywords
        if employee_ranges:
            payload["organization_num_employees_ranges"] = employee_ranges
        if revenue_range:
            payload["revenue_range"] = revenue_range
        if job_titles:
            payload["q_organization_job_titles"] = job_titles

        try:
            logger.info(f"Querying Apollo Organization Search (limit={per_page}, locations={locations}, keywords={keywords})...")
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            
            # Fallback to mixed_companies/search if organizations/search returns 404
            if response.status_code == 404:
                url = f"{self.BASE_URL}/mixed_companies/search"
                response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)

            response.raise_for_status()
            data = response.json()
            organizations = data.get("organizations", []) or data.get("accounts", [])
            logger.info(f"Successfully retrieved {len(organizations)} targeted organizations from Apollo.")
            return organizations
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Apollo Organization Search API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}, Body: {e.response.text}")
            return []

    def find_company_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Account Deep-Dive: returns a short list of real candidate companies matching
        a possibly loose or abbreviated name — e.g. "PMI" genuinely matches both
        "Project Management Institute" and "Philip Morris International". Confirmed
        live: enrich_company("PMI") silently returns the wrong one with no warning,
        so the UI should show these candidates for the user to confirm before
        spending research credits, rather than trusting a single guessed match.
        """
        url = f"{self.BASE_URL}/organizations/search"
        payload = {"page": 1, "per_page": limit, "q_organization_name": query}
        try:
            logger.info(f"Searching company candidates for '{query}'...")
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("organizations", []) or data.get("accounts", [])
            logger.info(f"Found {len(candidates)} candidate(s) for '{query}'.")
            return candidates
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching company candidates for '{query}': {e}")
            return []

    def enrich_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Account Deep-Dive: looks up ONE specific, known company by name or domain
        (unlike search_organizations, which scans many companies against filters).
        Accepts whatever the user typed — a domain-looking identifier (contains a
        "." and no spaces) is sent as `domain`, otherwise as `name`. Confirmed live
        against the real API that both param styles resolve correctly.
        """
        url = f"{self.BASE_URL}/organizations/enrich"
        identifier = (identifier or "").strip()
        if not identifier:
            return None

        is_domain = "." in identifier and " " not in identifier
        params = {"domain": identifier} if is_domain else {"name": identifier}

        try:
            logger.info(f"Looking up company '{identifier}' via Organization Enrichment...")
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            org = response.json().get("organization")
            if org:
                logger.info(f"Found company: {org.get('name')}")
            else:
                logger.warning(f"No company found for '{identifier}'.")
            return org
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enriching company '{identifier}': {e}")
            return None

    def list_company_contacts(
        self,
        organization_id: Optional[str] = None,
        domain: Optional[str] = None,
        company_name: Optional[str] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Phase 2a: Fetches the real contact roster for a company — first name + job
        title only, no email/phone/last name (those require enrichment, see
        bulk_enrich_people). Deliberately has no person_titles/seniority filter:
        Apollo's title matching is fairly literal and AI-guessed titles routinely
        miss real people, so instead the AI selects the best-fit people from this
        real roster afterward (see PerplexityClient.select_best_contacts).
        """
        url = f"{self.BASE_URL}/mixed_people/api_search"

        payload_attempts = []
        if domain:
            payload_attempts.append({"page": 1, "per_page": per_page, "q_organization_domains": domain})
        if organization_id:
            payload_attempts.append({"page": 1, "per_page": per_page, "organization_ids": [str(organization_id)]})

        for i, payload in enumerate(payload_attempts, 1):
            try:
                logger.info(f"Listing contacts for {company_name or domain or organization_id} (Attempt {i})...")
                response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    people = data.get("people", []) or data.get("contacts", [])
                    if people:
                        logger.info(f"Retrieved {len(people)} total contacts for {company_name or domain} on Attempt {i}.")
                        return people
            except Exception as e:
                logger.error(f"Error listing contacts on Attempt {i}: {e}")
                continue

        logger.warning(f"No contacts retrieved for {company_name or domain or organization_id} after all attempts.")
        return []

    def bulk_enrich_people(
        self,
        people: List[Dict[str, Any]],
        reveal_personal_emails: bool = False,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Phase 3: Enriches People Search results via Apollo's Bulk People Enrichment
        (/people/bulk_match), matching each contact by its Apollo `id` to retrieve
        complete verified fields (work email, headline, employment history, etc).
        Each returned dict is tagged with `_enriched` (True/False).
        """
        url = f"{self.BASE_URL}/people/bulk_match"
        enriched: List[Dict[str, Any]] = []

        for i in range(0, len(people), batch_size):
            batch = people[i:i + batch_size]
            sendable = [p for p in batch if p.get("id")]
            skipped = [p for p in batch if not p.get("id")]

            for p in skipped:
                enriched.append({**p, "_enriched": False})

            if not sendable:
                continue

            payload = {
                "reveal_personal_emails": reveal_personal_emails,
                "details": [{"id": p["id"]} for p in sendable]
            }

            try:
                batch_num = i // batch_size + 1
                logger.info(f"Enriching contact batch {batch_num} ({len(sendable)} people)...")
                response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                matches = response.json().get("matches", [])
                for original, match in zip(sendable, matches):
                    if match:
                        enriched.append({**original, **match, "_enriched": True})
                    else:
                        enriched.append({**original, "_enriched": False})
            except Exception as e:
                logger.error(f"Error bulk-enriching people batch {i // batch_size + 1}: {e}")
                for p in sendable:
                    enriched.append({**p, "_enriched": False})

        logger.info(f"Enrichment complete: {sum(1 for p in enriched if p.get('_enriched'))} / {len(enriched)} contacts matched.")
        return enriched
