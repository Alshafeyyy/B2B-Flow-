import logging
from typing import Callable, Dict, List, Optional, Any

from tqdm import tqdm

from config import (
    APOLLO_API_KEY,
    PERPLEXITY_API_KEY,
    PERPLEXITY_MODEL,
    OFFERING_DESCRIPTION,
    DEFAULT_CONTACT_TITLES
)
from apollo_client import ApolloClient
from perplexity_client import PerplexityClient
from exporter import export_pipeline_to_excel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ALXPipeline")


def run_pipeline(
    locations: List[str],
    keywords: List[str],
    industries: Optional[List[str]],
    employee_ranges: List[str],
    limit: int,
    output_path: str,
    on_progress: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Runs the full 2-phase sourcing/qualification/enrichment/briefing pipeline and
    exports the results to a multi-sheet Excel workbook. Shared by the CLI (main.py)
    and the Streamlit web UI (app.py) so both call one implementation.
    """
    def progress(msg: str):
        if on_progress:
            on_progress(msg)

    companies_sheet_records: List[Dict[str, Any]] = []
    contacts_briefs_records: List[Dict[str, Any]] = []

    def checkpoint():
        # Re-exports whatever has been produced so far to `output_path` after every
        # company qualified / contact briefed. If the run dies partway (connection
        # drop, app restart, API error), the credits already spent aren't wasted —
        # the file on disk always reflects the latest completed work.
        try:
            export_pipeline_to_excel(companies_sheet_records, contacts_briefs_records, output_path)
        except Exception as e:
            logger.warning(f"Checkpoint save failed (continuing run): {e}")

    if not APOLLO_API_KEY:
        raise RuntimeError("APOLLO_API_KEY missing — configure it in .env (local) or Secrets (deployed).")
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY missing — configure it in .env (local) or Secrets (deployed).")

    apollo = ApolloClient(api_key=APOLLO_API_KEY)
    perplexity = PerplexityClient(api_key=PERPLEXITY_API_KEY, model=PERPLEXITY_MODEL)

    # -------------------------------------------------------------------------
    # PHASE 1: Company Sourcing & AI Qualification
    # -------------------------------------------------------------------------
    progress(f"🏢 PHASE 1: Sourcing {limit} companies in {locations} (Size 50+)...")

    if not industries:
        raw_companies = apollo.search_organizations(
            locations=locations,
            keywords=keywords,
            employee_ranges=employee_ranges,
            page=1,
            per_page=limit
        )
    else:
        # Strict client-side filter on Apollo's clean 'industry' field (vs. the loose
        # keyword-tag match in `keywords`). Paginates through results until it finds
        # `limit` matching companies or hits the page safety cap.
        progress(f"   🎯 Strict industry filter active: {', '.join(industries)}")
        allowed_industries = {i.strip().lower() for i in industries}
        raw_companies = []
        page = 1
        max_pages = 10
        while len(raw_companies) < limit and page <= max_pages:
            batch = apollo.search_organizations(
                locations=locations,
                keywords=keywords,
                employee_ranges=employee_ranges,
                page=page,
                per_page=100
            )
            if not batch:
                break
            raw_companies.extend(c for c in batch if (c.get("industry") or "").strip().lower() in allowed_industries)
            page += 1
        raw_companies = raw_companies[:limit]
        progress(f"   Scanned {page - 1} page(s) of Apollo results to find {len(raw_companies)} industry-matching companies.")

    if not raw_companies:
        logger.warning("No companies returned from Apollo. Exiting pipeline.")
        progress("⚠️ No companies returned from Apollo for these filters.")
        return {"output_path": None, "companies": [], "contacts": [], "go_count": 0}

    progress(f"✅ Found {len(raw_companies)} companies. Running AI qualification & role suggestions...")

    go_companies = []

    for comp in tqdm(raw_companies, desc="Phase 1 - Qualifying Companies"):
        comp_id = comp.get("id") or comp.get("organization_id")
        comp_name = comp.get("name", "Unknown Company")
        domain = comp.get("primary_domain") or comp.get("domain", "")
        industry = comp.get("industry", "Unknown")
        employees = comp.get("estimated_num_employees", comp.get("num_employees", "Unknown"))
        city = comp.get("city", "")
        country = comp.get("country", "")
        location = f"{city}, {country}".strip(", ") or "Morocco"
        website = comp.get("website_url", f"https://{domain}" if domain else "")
        short_desc = comp.get("short_description", "")

        # AI Qualification & Target Role Suggestions
        ai_res = perplexity.qualify_company_and_suggest_roles(comp, OFFERING_DESCRIPTION)
        status = ai_res.get("status", "Review")
        reason = ai_res.get("reason", "")
        suggested_roles = ai_res.get("suggested_roles", DEFAULT_CONTACT_TITLES)
        suggested_roles_str = ", ".join(suggested_roles) if isinstance(suggested_roles, list) else str(suggested_roles)

        record = {
            "Company Name": comp_name,
            "Domain": domain,
            "Industry": industry,
            "Employees": employees,
            "Location": location,
            "Website": website,
            "Company Description": short_desc,
            "AI Status": status,
            "AI Reason": reason,
            "AI Suggested Target Roles": suggested_roles_str
        }

        companies_sheet_records.append(record)
        checkpoint()

        if status == "Go":
            go_companies.append({
                "raw": comp,
                "record": record,
                "suggested_roles": suggested_roles if isinstance(suggested_roles, list) else DEFAULT_CONTACT_TITLES
            })

    progress(f"📊 Phase 1 Complete: {len(go_companies)} / {len(companies_sheet_records)} marked as 'Go'.")

    # -------------------------------------------------------------------------
    # PHASE 2: Contact Search, People Enrichment & Pre-Call Briefing
    # -------------------------------------------------------------------------
    if go_companies:
        # ---- Phase 2a: Search contacts by AI-suggested role for each 'Go' company ----
        progress(f"👥 PHASE 2a: Searching contacts for {len(go_companies)} 'Go' companies...")

        all_contacts = []

        for item in tqdm(go_companies, desc="Phase 2a - Searching Contacts"):
            comp_raw = item["raw"]
            comp_record = item["record"]
            comp_name = comp_record["Company Name"]
            comp_id = comp_raw.get("id") or comp_raw.get("organization_id")
            comp_domain = comp_record["Domain"]
            target_roles = item["suggested_roles"] or DEFAULT_CONTACT_TITLES

            contacts = apollo.search_contacts_by_company(
                organization_id=comp_id,
                domain=comp_domain,
                company_name=comp_name,
                titles=target_roles,
                per_page=5
            )

            if not contacts:
                logger.info(f"No contacts found for {comp_name}. Creating placeholder entry.")
                contacts_briefs_records.append({
                    "Company Name": comp_name,
                    "Contact Name": "N/A (No contact retrieved)",
                    "Job Title": "N/A",
                    "Email": "N/A",
                    "Phone Number": "N/A",
                    "LinkedIn URL": "N/A",
                    "Enrichment Status": "No Contacts Found",
                    "1. Contact Insights & Experience": "No decision maker contact retrieved from search.",
                    "2. Tailored Sales Angle": f"Target company {comp_name} for enterprise AI & Data transformation training.",
                    "3. Target Company Brief": comp_record.get("Company Description", ""),
                    "4. Industry Position & Market Insights": f"Key player in {comp_record.get('Industry', 'Industry')}."
                })
                checkpoint()
                continue

            for c in contacts:
                c["_source_company_item"] = item
                all_contacts.append(c)

        # ---- Phase 2b: Enrich all found contacts via Apollo People Enrichment ----
        if all_contacts:
            progress(f"🔎 PHASE 2b: Enriching {len(all_contacts)} contacts via Apollo People Enrichment...")
            enriched_contacts = apollo.bulk_enrich_people(all_contacts, reveal_personal_emails=False)

            # ---- Phase 2c: Deep AI Research & Briefing for each enriched contact ----
            progress(f"📝 PHASE 2c: Generating deep briefs for {len(enriched_contacts)} enriched contacts...")

            for idx, c in enumerate(tqdm(enriched_contacts, desc="Phase 2c - AI Briefing"), start=1):
                item = c.pop("_source_company_item")
                comp_raw = item["raw"]
                comp_record = item["record"]
                comp_name = comp_record["Company Name"]

                contact_name = c.get("name", f"{c.get('first_name', '')} {c.get('last_name', '')}").strip()
                job_title = c.get("title", "Executive")
                email = c.get("email") or "No verified email found"
                linkedin_url = c.get("linkedin_url") or "Not available"

                # Parse Phone Numbers
                phone_list = c.get("phone_numbers", [])
                phone_str = ""
                if phone_list and isinstance(phone_list, list):
                    nums = [p.get("raw_number") or p.get("sanitized_number") or p.get("number") for p in phone_list if (p.get("raw_number") or p.get("sanitized_number") or p.get("number"))]
                    phone_str = ", ".join(nums)
                elif c.get("sanitized_phone_number"):
                    phone_str = c.get("sanitized_phone_number")
                else:
                    phone_str = c.get("phone", "Not available")

                if not phone_str:
                    phone_str = "Not available"

                deep_brief = perplexity.generate_deep_contact_brief(c, comp_raw, OFFERING_DESCRIPTION)

                contact_entry = {
                    "Company Name": comp_name,
                    "Contact Name": contact_name,
                    "Job Title": job_title,
                    "Email": email,
                    "Phone Number": phone_str,
                    "LinkedIn URL": linkedin_url,
                    "Enrichment Status": "Enriched" if c.get("_enriched") else "Not Matched",
                    "1. Contact Insights & Experience": deep_brief.get("contact_insights", ""),
                    "2. Tailored Sales Angle": deep_brief.get("opening_sales_angle", ""),
                    "3. Target Company Brief": deep_brief.get("company_brief", ""),
                    "4. Industry Position & Market Insights": deep_brief.get("industry_position", "")
                }

                contacts_briefs_records.append(contact_entry)
                checkpoint()
                progress(f"   ✓ Brief {idx}/{len(enriched_contacts)}: {contact_name} ({comp_name})")

    # -------------------------------------------------------------------------
    # EXPORT RESULTS TO MULTI-SHEET EXCEL
    # -------------------------------------------------------------------------
    out_file = export_pipeline_to_excel(companies_sheet_records, contacts_briefs_records, output_path)

    progress("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    progress(f"📊 Sheet 1 (Company Qualification): {len(companies_sheet_records)} companies logged.")
    progress(f"👥 Sheet 2 (Enriched Contacts & Briefs): {len(contacts_briefs_records)} contacts enriched.")
    progress(f"📁 Master Excel Workbook: {out_file}")

    return {
        "output_path": out_file,
        "companies": companies_sheet_records,
        "contacts": contacts_briefs_records,
        "go_count": len(go_companies)
    }
