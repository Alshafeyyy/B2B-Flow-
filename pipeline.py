import logging
import re
from datetime import datetime
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


def default_output_filename(industries: Optional[List[str]], keywords: List[str], go_target: int) -> str:
    """Builds a filename that says what's actually in it, e.g. pharmaceuticals_5go_20260811_1630.xlsx."""
    label_source = industries or keywords or ["all_industries"]
    slug = "_".join(re.sub(r"[^a-z0-9]+", "-", i.lower()).strip("-") for i in label_source[:3])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{slug}_{go_target}go_{timestamp}.xlsx"


def run_pipeline(
    locations: List[str],
    keywords: List[str],
    industries: Optional[List[str]],
    employee_ranges: List[str],
    limit: int,
    output_path: str,
    revenue_range: Optional[Dict[str, int]] = None,
    hiring_for: Optional[List[str]] = None,
    exclude_companies: Optional[List[str]] = None,
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
    # `limit` is the target number of 'Go' companies, not raw companies fetched.
    # Apollo is paginated and each candidate is AI-qualified as it's found, until
    # `limit` Go companies are collected or the scan budget (5x the target, to
    # keep worst-case Perplexity cost bounded) is exhausted. Every company scanned
    # — Go or not — still lands in the Company Qualification sheet as an audit trail.
    scan_cap = limit * 5
    progress(f"🏢 PHASE 1: Sourcing companies in {locations} until {limit} are marked 'Go' (scanning up to {scan_cap} candidates)...")

    allowed_industries = {i.strip().lower() for i in industries} if industries else None
    if industries:
        progress(f"   🎯 Strict industry filter active: {', '.join(industries)}")

    excluded_names = [e.strip().lower() for e in exclude_companies if e.strip()] if exclude_companies else []
    if excluded_names:
        progress(f"   🚫 Excluding {len(excluded_names)} company name(s) already seen: {', '.join(excluded_names)}")

    go_companies = []
    scanned_count = 0
    seen_ids = set()
    page = 1
    max_pages = 20

    progress_bar = tqdm(total=scan_cap, desc="Phase 1 - Qualifying Companies")
    while len(go_companies) < limit and scanned_count < scan_cap and page <= max_pages:
        batch = apollo.search_organizations(
            locations=locations,
            keywords=keywords,
            employee_ranges=employee_ranges,
            revenue_range=revenue_range,
            job_titles=hiring_for,
            page=page,
            per_page=100
        )
        page += 1
        if not batch:
            break

        for comp in batch:
            if len(go_companies) >= limit or scanned_count >= scan_cap:
                break

            comp_id = comp.get("id") or comp.get("organization_id") or comp.get("primary_domain") or comp.get("name")
            if comp_id in seen_ids:
                continue
            seen_ids.add(comp_id)

            if allowed_industries and (comp.get("industry") or "").strip().lower() not in allowed_industries:
                continue

            comp_name_lower = (comp.get("name") or "").strip().lower()
            if excluded_names and comp_name_lower and any(
                excl in comp_name_lower or comp_name_lower in excl for excl in excluded_names
            ):
                continue

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
            scanned_count += 1
            progress_bar.update(1)

            if status == "Go":
                go_companies.append({
                    "raw": comp,
                    "record": record,
                    "suggested_roles": suggested_roles if isinstance(suggested_roles, list) else DEFAULT_CONTACT_TITLES
                })
                progress(f"   ✅ Go {len(go_companies)}/{limit}: {comp_name}")

    progress_bar.close()

    if not companies_sheet_records:
        logger.warning("No companies returned from Apollo. Exiting pipeline.")
        progress("⚠️ No companies returned from Apollo for these filters.")
        return {"output_path": None, "companies": [], "contacts": [], "go_count": 0}

    if len(go_companies) < limit:
        progress(f"⚠️ Phase 1 Complete: only {len(go_companies)}/{limit} 'Go' companies found after scanning {scanned_count} candidates — Apollo/AI supply may be exhausted for these filters.")
    else:
        progress(f"📊 Phase 1 Complete: {len(go_companies)}/{limit} 'Go' companies found after scanning {scanned_count} candidates.")

    # -------------------------------------------------------------------------
    # PHASE 2: Contact Search, People Enrichment & Pre-Call Briefing
    # -------------------------------------------------------------------------
    if go_companies:
        # ---- Phase 2a: Pull the real roster per 'Go' company, let AI pick the best fits ----
        progress(f"👥 PHASE 2a: Finding & selecting contacts for {len(go_companies)} 'Go' companies...")

        all_contacts = []

        for item in tqdm(go_companies, desc="Phase 2a - Selecting Contacts"):
            comp_raw = item["raw"]
            comp_record = item["record"]
            comp_name = comp_record["Company Name"]
            comp_id = comp_raw.get("id") or comp_raw.get("organization_id")
            comp_domain = comp_record["Domain"]
            suggested_roles = item["suggested_roles"] or DEFAULT_CONTACT_TITLES

            # No title/seniority filter here — Apollo's title matching is fairly
            # literal and AI-guessed titles routinely miss real people. Instead,
            # fetch the real roster (name + title only, no contact info) and let
            # the AI pick the best-fit people from what's actually there.
            roster = apollo.list_company_contacts(
                organization_id=comp_id,
                domain=comp_domain,
                company_name=comp_name,
                per_page=100
            )

            if not roster:
                logger.info(f"No contacts found for {comp_name}. Creating placeholder entry.")
                contacts_briefs_records.append({
                    "Company Name": comp_name,
                    "Contact Name": "N/A (No contact retrieved)",
                    "Job Title": "N/A",
                    "Email": "N/A",
                    "Phone Number": "N/A",
                    "LinkedIn URL": "N/A",
                    "Enrichment Status": "No Contacts Found",
                    "Why This Contact": "",
                    "1. Contact Insights & Experience": "No decision maker contact retrieved from search.",
                    "2. Tailored Sales Angle": f"Target company {comp_name} for enterprise AI & Data transformation training.",
                    "3. Target Company Brief": comp_record.get("Company Description", ""),
                    "4. Industry Position & Market Insights": f"Key player in {comp_record.get('Industry', 'Industry')}."
                })
                checkpoint()
                continue

            selected = perplexity.select_best_contacts(
                comp_raw, roster, OFFERING_DESCRIPTION, suggested_roles, max_selections=5
            )

            for c in selected:
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
                    "Why This Contact": c.get("_selection_reason", ""),
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


def run_company_deep_dive(
    company_query: str,
    output_path: str,
    on_progress: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Account Deep-Dive: researches ONE specific, already-known company in real depth
    — a full company dossier plus, for its best-fit contacts, deep individual
    research (professional background, public presence, persona-matched pitch) —
    for preparing an actual meeting. For discovering new leads across many
    companies, see run_pipeline instead.
    """
    def progress(msg: str):
        if on_progress:
            on_progress(msg)

    company_sheet_records: List[Dict[str, Any]] = []
    contacts_records: List[Dict[str, Any]] = []

    def checkpoint():
        try:
            export_pipeline_to_excel(
                company_sheet_records, contacts_records, output_path,
                sheet1_name="Company Dossier", sheet2_name="Contact Research"
            )
        except Exception as e:
            logger.warning(f"Checkpoint save failed (continuing run): {e}")

    if not APOLLO_API_KEY:
        raise RuntimeError("APOLLO_API_KEY missing — configure it in .env (local) or Secrets (deployed).")
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY missing — configure it in .env (local) or Secrets (deployed).")

    apollo = ApolloClient(api_key=APOLLO_API_KEY)
    perplexity = PerplexityClient(api_key=PERPLEXITY_API_KEY, model=PERPLEXITY_MODEL)

    # -------------------------------------------------------------------------
    # Look up the one company
    # -------------------------------------------------------------------------
    progress(f"🔎 Looking up '{company_query}'...")
    comp_raw = apollo.enrich_company(company_query)

    if not comp_raw:
        logger.warning(f"No company found for '{company_query}'.")
        progress(f"⚠️ No company found matching '{company_query}'.")
        return {"output_path": None, "company": None, "contacts": []}

    comp_name = comp_raw.get("name", company_query)
    domain = comp_raw.get("primary_domain") or comp_raw.get("domain", "")
    industry = comp_raw.get("industry", "Unknown")
    employees = comp_raw.get("estimated_num_employees", comp_raw.get("num_employees", "Unknown"))
    city = comp_raw.get("city", "")
    country = comp_raw.get("country", "")
    location = f"{city}, {country}".strip(", ") or "Morocco"
    website = comp_raw.get("website_url", f"https://{domain}" if domain else "")
    short_desc = comp_raw.get("short_description", "")
    comp_id = comp_raw.get("id") or comp_raw.get("organization_id")

    progress(f"✅ Found: {comp_name} ({industry}, {employees} employees)")

    # -------------------------------------------------------------------------
    # Deep company research
    # -------------------------------------------------------------------------
    progress(f"📊 Researching {comp_name} in depth...")
    dossier = perplexity.deep_company_research(comp_raw, OFFERING_DESCRIPTION)

    company_record = {
        "Company Name": comp_name,
        "Domain": domain,
        "Industry": industry,
        "Employees": employees,
        "Location": location,
        "Website": website,
        "Company Description": short_desc,
        "Signals Found": dossier.get("signals_found", ""),
        "Recent Developments": dossier.get("recent_developments", ""),
        "Competitive Position": dossier.get("competitive_position", ""),
        "Meeting Talking Points": dossier.get("meeting_talking_points", "")
    }
    company_sheet_records.append(company_record)
    checkpoint()

    # -------------------------------------------------------------------------
    # Contacts: real roster -> AI selection (unchanged, proven mechanism) -> enrich
    # -------------------------------------------------------------------------
    progress(f"👥 Finding contacts at {comp_name}...")
    roster = apollo.list_company_contacts(
        organization_id=comp_id, domain=domain, company_name=comp_name, per_page=100
    )

    if not roster:
        progress(f"⚠️ No contacts found at {comp_name}.")
        out_file = export_pipeline_to_excel(
            company_sheet_records, contacts_records, output_path,
            sheet1_name="Company Dossier", sheet2_name="Contact Research"
        )
        progress("🎉 DEEP-DIVE COMPLETE (no contacts found).")
        return {"output_path": out_file, "company": company_record, "contacts": []}

    progress(f"   Found {len(roster)} people on file. Selecting best-fit contacts...")
    selected = perplexity.select_best_contacts(comp_raw, roster, OFFERING_DESCRIPTION, None, max_selections=5)

    progress(f"🔓 Unlocking contact details for {len(selected)} selected people...")
    enriched = apollo.bulk_enrich_people(selected, reveal_personal_emails=False)

    # -------------------------------------------------------------------------
    # Deep individual research per selected contact (professional record only —
    # see PerplexityClient.deep_contact_research for the explicit scope boundary)
    # -------------------------------------------------------------------------
    progress(f"📝 Researching {len(enriched)} contacts in depth (professional background, public presence)...")

    for idx, c in enumerate(tqdm(enriched, desc="Deep Contact Research"), start=1):
        contact_name = c.get("name", f"{c.get('first_name', '')} {c.get('last_name', '')}").strip()
        job_title = c.get("title", "Executive")
        email = c.get("email") or "No verified email found"
        linkedin_url = c.get("linkedin_url") or "Not available"

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

        research = perplexity.deep_contact_research(c, comp_raw, OFFERING_DESCRIPTION)

        contact_entry = {
            "Company Name": comp_name,
            "Contact Name": contact_name,
            "Job Title": job_title,
            "Email": email,
            "Phone Number": phone_str,
            "LinkedIn URL": linkedin_url,
            "Enrichment Status": "Enriched" if c.get("_enriched") else "Not Matched",
            "Why This Contact": c.get("_selection_reason", ""),
            "1. Professional Background": research.get("professional_background", ""),
            "2. Public Presence (Articles/Interviews/Mentions)": research.get("public_presence", ""),
            "3. Opening Sales Angle": research.get("opening_sales_angle", ""),
            "4. Company Brief": research.get("company_brief", ""),
            "5. Meeting Prep Note": research.get("meeting_prep_note", "")
        }

        contacts_records.append(contact_entry)
        checkpoint()
        progress(f"   ✓ Researched {idx}/{len(enriched)}: {contact_name}")

    out_file = export_pipeline_to_excel(
        company_sheet_records, contacts_records, output_path,
        sheet1_name="Company Dossier", sheet2_name="Contact Research"
    )

    progress("🎉 DEEP-DIVE COMPLETE!")
    progress(f"📊 Company Dossier: {comp_name}")
    progress(f"👥 Contacts Researched: {len(contacts_records)}")
    progress(f"📁 Master Excel Workbook: {out_file}")

    return {
        "output_path": out_file,
        "company": company_record,
        "contacts": contacts_records
    }
