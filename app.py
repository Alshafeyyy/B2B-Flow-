import os
import glob
import base64
from datetime import datetime
import streamlit as st

# Must happen before importing config/pipeline: copy any matching Streamlit Cloud
# "Secrets" into the environment so config.py (plain os.getenv, unchanged) picks
# them up exactly like it would a local .env file.
for _key in ("APOLLO_API_KEY", "LLM_GATEWAY_API_KEY", "LLM_GATEWAY_BASE_URL", "SEARCH_MODEL", "REASONING_MODEL", "OFFERING_DESCRIPTION"):
    if _key in st.secrets:
        os.environ[_key] = str(st.secrets[_key])

from config import APOLLO_API_KEY, LLM_GATEWAY_API_KEY, DEFAULT_EMPLOYEE_RANGES, DEFAULT_INDUSTRIES
from pipeline import (
    run_pipeline,
    run_company_deep_dive,
    run_person_deep_dive,
    search_company_candidates,
    search_person_candidates,
    default_output_filename
)

st.set_page_config(page_title="ALX Enterprise Prospecting", page_icon="🎯", layout="centered")


@st.cache_data
def _load_logo_b64() -> str:
    with open(os.path.join(os.path.dirname(__file__), "assets", "alx-enterprise-logo.png"), "rb") as f:
        return base64.b64encode(f.read()).decode()


_logo_b64 = _load_logo_b64()

# -----------------------------------------------------------------------------
# Brand styling — ALX's real logo and wordmark colors (deep navy "alx" + bright
# blue "Enterprise"), Inter for a clean, professional feel, and real tabs (not
# radio buttons) for the two flows so they read as two actual pages, not two
# options in a form.
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* font-family on html/body only, relying on normal CSS inheritance — a universal
   `*` selector here previously overrode Streamlit's own icon fonts (arrows,
   chevrons), making them render as literal icon-name text instead of glyphs.
   Leaving icon elements alone entirely lets Streamlit's own (more specific)
   icon-font rule keep working as designed. */
html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

:root {
    --alx-navy: #0B1F4D;
    --alx-blue: #1E5AFF;
    --alx-bg: #F6F8FC;
    --alx-border: #E2E8F0;
    --alx-muted: #64748B;
}

[data-testid="stAppViewContainer"] { background: var(--alx-bg); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 760px; }

.alx-header { margin-bottom: 0.2rem; }
.alx-header img { height: 42px; width: auto; display: block; }
.alx-tagline { color: var(--alx-muted); font-size: 0.98rem; margin: 0.6rem 0 1.6rem 0; }

/* Tabs as a real page switcher, not the default small underline */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid var(--alx-border); }
.stTabs [data-baseweb="tab"] {
    height: 3rem; padding: 0 1.1rem; font-weight: 600; font-size: 1.02rem;
    color: var(--alx-muted); border-radius: 10px 10px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--alx-navy); background: #FFFFFF; }
.stTabs [aria-selected="true"] {
    color: var(--alx-blue) !important;
    border-bottom: 3px solid var(--alx-blue) !important;
    background: #FFFFFF;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.4rem; }

/* Forms as clean cards instead of the default plain box */
[data-testid="stForm"] {
    background: #FFFFFF; border: 1px solid var(--alx-border);
    border-radius: 14px; padding: 1.6rem 1.6rem 1.2rem 1.6rem;
}

.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 8px; font-weight: 600;
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: var(--alx-blue); border: none;
}

[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid var(--alx-border);
    border-radius: 10px; padding: 0.75rem 1rem;
}

[data-testid="stExpander"] { border: 1px solid var(--alx-border); border-radius: 10px; }

/* Bordered st.container(border=True) cards — same card language as the form,
   for the Deep-Dive tab which can't use st.form (it's a multi-step flow). */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF; border: 1px solid var(--alx-border) !important;
    border-radius: 14px; padding: 0.4rem 0.6rem;
}
.alx-card-title {
    font-weight: 700; font-size: 1.02rem; color: var(--alx-navy);
    margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

# Separate markdown call (an f-string, so it can interpolate the logo) — kept
# apart from the <style> block above, which is full of literal { } CSS braces
# that would break an f-string.
st.markdown(f"""
<div class="alx-header"><img src="data:image/png;base64,{_logo_b64}" alt="alx Enterprise"></div>
<div class="alx-tagline">B2B Prospecting — source companies, qualify them, find decision-makers, and generate sales briefs. Powered by Apollo + LLM Gateway.</div>
""", unsafe_allow_html=True)

# Recovery: the pipeline saves progress to disk after every company/contact, not
# just at the end — so a run that dies partway (dropped connection, app restart,
# an API error) still leaves a file with whatever was completed. Surface any of
# those here so the credits already spent on them aren't lost. Shared by both
# tabs below, since either can produce a checkpointed file.
existing_files = sorted(glob.glob("*.xlsx"), key=os.path.getmtime, reverse=True)
if existing_files:
    with st.expander(f"📂 Previous run files on this server ({len(existing_files)})"):
        st.caption("Includes runs that didn't finish — each file has everything completed up to the point it stopped.")
        for path in existing_files:
            saved_at = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            with open(path, "rb") as f:
                st.download_button(
                    f"⬇️ {os.path.basename(path)} (saved {saved_at})",
                    data=f.read(),
                    file_name=os.path.basename(path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"recover_{path}"
                )

if not APOLLO_API_KEY or not LLM_GATEWAY_API_KEY:
    st.error(
        "Missing API keys. If you're running this locally, set APOLLO_API_KEY and "
        "LLM_GATEWAY_API_KEY in a .env file. If this app is deployed, add them under "
        "your app's **Settings → Secrets** in Streamlit Community Cloud."
    )
    st.stop()

tab_search, tab_deep_dive = st.tabs(["🔍  Find New Companies", "🎯  Deep-Dive"])

# =============================================================================
# TAB 1: Find New Companies (lead discovery — logic unchanged from before)
# =============================================================================
with tab_search:
    EMPLOYEE_RANGE_LABELS = {
        "51,200": "51 – 200 employees",
        "201,500": "201 – 500 employees",
        "501,1000": "501 – 1,000 employees",
        "1001,5000": "1,001 – 5,000 employees",
        "5001,10000": "5,001 – 10,000 employees",
    }

    @st.cache_data
    def load_industry_options():
        with open("apollo_industries_reference.txt") as f:
            return sorted(line.strip() for line in f if line.strip() and not line.startswith("#"))

    industry_options = load_industry_options()

    with st.form("prospecting_form"):
        industries = st.multiselect(
            "Industries",
            options=industry_options,
            default=[i for i in DEFAULT_INDUSTRIES if i in industry_options],
            help="Pulled from real Apollo data. Leave empty to search broadly across all industries."
        )
        country_input = st.text_input("Country / Location", value="Morocco", help="Comma-separate multiple countries.")
        size_labels = st.multiselect(
            "Company size",
            options=list(EMPLOYEE_RANGE_LABELS.values()),
            default=[EMPLOYEE_RANGE_LABELS[r] for r in DEFAULT_EMPLOYEE_RANGES]
        )
        limit = st.number_input(
            "Number of 'Go' companies wanted", min_value=1, max_value=20, value=5, step=1,
            help="This is the target Go count, not raw companies scanned — Apollo will be searched as deep as "
                 "needed (up to 5x this number of candidates) to find that many qualified companies. "
                 "Each candidate scanned spends Apollo + AI credits, so worst-case cost scales with this too."
        )

        with st.expander("Advanced filters (optional)"):
            rev_col1, rev_col2 = st.columns(2)
            revenue_min_input = rev_col1.number_input("Min annual revenue (USD)", min_value=0, value=0, step=100_000)
            revenue_max_input = rev_col2.number_input("Max annual revenue (USD)", min_value=0, value=0, step=100_000)
            hiring_for_input = st.text_input(
                "Only companies currently hiring for...",
                value="",
                help="Comma-separated roles, e.g. \"data analyst, AI engineer\". Companies hiring for these roles "
                     "signal active investment in exactly what we sell — a sharper buying signal than industry/size alone."
            )
            exclude_input = st.text_area(
                "Exclude companies",
                value="",
                help="One per line or comma-separated, e.g. companies from a previous run you don't want to see again. "
                     "Matches by name (not exact — \"Maroc Telecom\" will also skip \"Maroc Telecom S.A.\")."
            )

        submitted = st.form_submit_button("Run Pipeline", type="primary")

    if submitted:
        locations = [loc.strip() for loc in country_input.split(",") if loc.strip()]
        label_to_range = {v: k for k, v in EMPLOYEE_RANGE_LABELS.items()}
        employee_ranges = [label_to_range[label] for label in size_labels] or list(EMPLOYEE_RANGE_LABELS.keys())
        keywords = industries or DEFAULT_INDUSTRIES

        if not locations:
            st.warning("Enter at least one country/location.")
            st.stop()

        revenue_range = None
        if revenue_min_input or revenue_max_input:
            revenue_range = {}
            if revenue_min_input:
                revenue_range["min"] = int(revenue_min_input)
            if revenue_max_input:
                revenue_range["max"] = int(revenue_max_input)
        hiring_for = [h.strip() for h in hiring_for_input.split(",") if h.strip()] or None
        exclude_companies = [e.strip() for e in exclude_input.replace(",", "\n").splitlines() if e.strip()] or None

        with st.status("Running pipeline...", expanded=True) as status:
            def on_progress(msg: str):
                status.write(msg)

            try:
                result = run_pipeline(
                    locations=locations,
                    keywords=keywords,
                    industries=industries or None,
                    employee_ranges=employee_ranges,
                    limit=int(limit),
                    output_path=default_output_filename(industries, keywords, int(limit)),
                    revenue_range=revenue_range,
                    hiring_for=hiring_for,
                    exclude_companies=exclude_companies,
                    on_progress=on_progress
                )
            except Exception as e:
                status.update(label=f"Failed: {e}", state="error")
                st.error(
                    "The run stopped before finishing, but everything completed up to that point "
                    "was already saved — reload this page and check **Previous run files** above."
                )
                st.stop()

            status.update(label="Pipeline complete", state="complete")

        if not result["output_path"]:
            st.warning("No companies matched these filters — try broadening the industries or size range.")
        else:
            companies = result["companies"]
            contacts = result["contacts"]
            go_count = result["go_count"]

            st.subheader("Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Companies sourced", len(companies))
            c2.metric("Marked 'Go'", go_count)
            c3.metric("Contacts found", len(contacts))

            with open(result["output_path"], "rb") as f:
                st.download_button(
                    "⬇️ Download Excel Workbook",
                    data=f.read(),
                    file_name=os.path.basename(result["output_path"]),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            st.dataframe(
                [{"Company": c["Company Name"], "Status": c["AI Status"], "Industry": c["Industry"]} for c in companies],
                width="stretch"
            )

# =============================================================================
# TAB 2: Deep-Dive (account research — you already know the company, or the
# specific person, and want a real research brief rather than a broad search)
# =============================================================================
MODE_COMPANY = "🏢 I know the company"
MODE_PERSON = "👤 I know a specific person"

with tab_deep_dive:
    st.caption(
        "You already have a specific target in mind — this does real research on it, not a broad "
        "search. Scoped to public professional information only."
    )

    dd_mode = st.radio(
        "What do you know?",
        [MODE_COMPANY, MODE_PERSON],
        horizontal=True,
        label_visibility="collapsed",
        key="dd_mode"
    )

    # =========================================================================
    # MODE: Company — full dossier on the company, plus deep research on its
    # best-fit contacts (unchanged from before).
    # =========================================================================
    if dd_mode == MODE_COMPANY:
        st.caption(
            "Pulls a full research dossier on the company, plus deep, meeting-ready research on its "
            "best-fit contacts (professional background, public presence, a persona-matched opening angle)."
        )

        # Two steps on purpose: a loose name can genuinely match more than one real
        # company (e.g. "PMI" matches both Project Management Institute and Philip
        # Morris International) — confirmed live that trusting a single guessed match
        # silently picks the wrong one with no warning. So: search for candidates,
        # confirm the right one, then spend research credits on it.
        if "dd_candidates" not in st.session_state:
            st.session_state.dd_candidates = []

        # Step 1: search. A single atomic action (type a name, click search), so this
        # can safely use st.form — gives it the same bordered-card look as Tab 1's
        # form for free.
        with st.form("dd_search_form"):
            st.markdown('<div class="alx-card-title">🔍 Search for a company</div>', unsafe_allow_html=True)
            company_query = st.text_input(
                "Company name",
                value="",
                label_visibility="collapsed",
                placeholder="e.g. \"Sothema\", \"CIH Bank\", or a domain like \"sothema.ma\"",
                key="dd_company_input"
            )
            search_submitted = st.form_submit_button("Search", type="primary")

        if search_submitted:
            if not company_query.strip():
                st.warning("Enter a company name.")
            else:
                with st.spinner(f"Searching for '{company_query}'..."):
                    st.session_state.dd_candidates = search_company_candidates(company_query.strip(), limit=5)
                if not st.session_state.dd_candidates:
                    st.warning(f"No companies found matching \"{company_query}\" — try a different spelling or the website domain instead.")

        # Step 2: confirm which real match is the right one. A separate step (can only
        # appear once search results exist), so it's its own bordered container.
        if st.session_state.dd_candidates:
            with st.container(border=True):
                st.markdown('<div class="alx-card-title">✅ Confirm the right company</div>', unsafe_allow_html=True)
                options = {}
                for c in st.session_state.dd_candidates:
                    label = f"{c.get('name', 'Unknown')} — {c.get('primary_domain') or c.get('domain') or 'no domain on file'}"
                    options[label] = c

                choice_label = st.radio("Candidates", list(options.keys()), label_visibility="collapsed", key="dd_radio")
                selected = options[choice_label]
                research_clicked = st.button("Research This Company", type="primary", key="dd_research_btn")

            if research_clicked:
                identifier = selected.get("primary_domain") or selected.get("domain") or selected.get("name")
                comp_display_name = selected.get("name", identifier)

                with st.status(f"Researching {comp_display_name}...", expanded=True) as status:
                    def on_progress(msg: str):
                        status.write(msg)

                    try:
                        result = run_company_deep_dive(
                            company_query=identifier,
                            output_path=f"deepdive_{str(comp_display_name).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            on_progress=on_progress
                        )
                    except Exception as e:
                        status.update(label=f"Failed: {e}", state="error")
                        st.error(
                            "The run stopped before finishing, but everything completed up to that point "
                            "was already saved — reload this page and check **Previous run files** above."
                        )
                        st.stop()

                    status.update(label="Research complete", state="complete")

                if not result["output_path"]:
                    st.warning(f"Couldn't retrieve full details for \"{comp_display_name}\" — try again or use its website domain instead.")
                else:
                    company = result["company"]
                    contacts = result["contacts"]

                    st.subheader("Summary")
                    c1, c2 = st.columns(2)
                    c1.metric("Company", company["Company Name"])
                    c2.metric("Contacts researched", len(contacts))

                    with open(result["output_path"], "rb") as f:
                        st.download_button(
                            "⬇️ Download Excel Workbook",
                            data=f.read(),
                            file_name=os.path.basename(result["output_path"]),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )

                    if contacts:
                        st.dataframe(
                            [{"Contact": c["Contact Name"], "Title": c["Job Title"], "Email": c["Email"]} for c in contacts],
                            width="stretch"
                        )

    # =========================================================================
    # MODE: Person — deep research on ONE already-identified person at an
    # already-known company. Skips the full company dossier (cheaper, faster) —
    # the contact brief already includes company context.
    # =========================================================================
    else:
        st.caption(
            "Deep, meeting-ready research on one specific person you already have in mind — professional "
            "background, public presence, and a persona-matched opening angle. Skips the full company "
            "dossier since you're not researching the company itself, just this one contact."
        )

        if "pd_company" not in st.session_state:
            st.session_state.pd_company = None
        if "pd_candidates" not in st.session_state:
            st.session_state.pd_candidates = []

        # Step 1: search. Needs BOTH the company and the person's name — Apollo's
        # people search by name alone (no company context) returns far too many
        # unrelated global matches to reliably find one specific person.
        with st.form("pd_search_form"):
            st.markdown('<div class="alx-card-title">🔍 Search for a person</div>', unsafe_allow_html=True)
            pd_company_query = st.text_input(
                "Company name",
                value="",
                placeholder="e.g. \"Sothema\", \"CIH Bank\", or a domain like \"sothema.ma\"",
                key="pd_company_input"
            )
            pd_person_query = st.text_input(
                "Person's name",
                value="",
                placeholder="e.g. \"Youssef El Amrani\"",
                key="pd_person_input"
            )
            pd_search_submitted = st.form_submit_button("Search", type="primary")

        if pd_search_submitted:
            if not pd_company_query.strip() or not pd_person_query.strip():
                st.warning("Enter both a company name and a person's name.")
            else:
                with st.spinner(f"Searching for '{pd_person_query}' at '{pd_company_query}'..."):
                    pd_result = search_person_candidates(pd_company_query.strip(), pd_person_query.strip(), limit=5)
                st.session_state.pd_company = pd_result["company"]
                st.session_state.pd_candidates = pd_result["candidates"]

                if not pd_result["company"]:
                    st.warning(f"No company found matching \"{pd_company_query}\" — try a different spelling or the website domain instead.")
                elif not pd_result["candidates"]:
                    st.warning(
                        f"Found {pd_result['company'].get('name')}, but no one matching \"{pd_person_query}\" "
                        "on file there — check the spelling, or try just their first name."
                    )

        # Step 2: confirm which real match is the right person. Shows which company
        # was actually resolved, so a wrong company match (e.g. an abbreviated name)
        # is visible here rather than silently researching the wrong person.
        if st.session_state.pd_candidates:
            with st.container(border=True):
                pd_comp_name = (st.session_state.pd_company or {}).get("name", "Unknown company")
                st.markdown(
                    f'<div class="alx-card-title">✅ Confirm the right person — matched at {pd_comp_name}</div>',
                    unsafe_allow_html=True
                )
                pd_options = {}
                for p in st.session_state.pd_candidates:
                    p_name = p.get("name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "Unknown"
                    label = f"{p_name} — {p.get('title') or 'no title on file'}"
                    pd_options[label] = p

                pd_choice_label = st.radio("Candidates", list(pd_options.keys()), label_visibility="collapsed", key="pd_radio")
                pd_selected = pd_options[pd_choice_label]
                pd_research_clicked = st.button("Research This Person", type="primary", key="pd_research_btn")

            if pd_research_clicked:
                person_display_name = pd_selected.get("name") or f"{pd_selected.get('first_name', '')} {pd_selected.get('last_name', '')}".strip()

                with st.status(f"Researching {person_display_name}...", expanded=True) as status:
                    def on_progress(msg: str):
                        status.write(msg)

                    try:
                        result = run_person_deep_dive(
                            company_raw=st.session_state.pd_company,
                            person_raw=pd_selected,
                            output_path=f"deepdive_person_{str(person_display_name).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            on_progress=on_progress
                        )
                    except Exception as e:
                        status.update(label=f"Failed: {e}", state="error")
                        st.error(
                            "The run stopped before finishing, but everything completed up to that point "
                            "was already saved — reload this page and check **Previous run files** above."
                        )
                        st.stop()

                    status.update(label="Research complete", state="complete")

                if not result["output_path"]:
                    st.warning(f"Couldn't retrieve full details for \"{person_display_name}\" — try again.")
                else:
                    contacts = result["contacts"]

                    st.subheader("Summary")
                    c1, c2 = st.columns(2)
                    c1.metric("Company", result["company"]["Company Name"])
                    c2.metric("Contact", contacts[0]["Contact Name"] if contacts else "N/A")

                    with open(result["output_path"], "rb") as f:
                        st.download_button(
                            "⬇️ Download Excel Workbook",
                            data=f.read(),
                            file_name=os.path.basename(result["output_path"]),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )

                    if contacts:
                        st.dataframe(
                            [{"Contact": c["Contact Name"], "Title": c["Job Title"], "Email": c["Email"]} for c in contacts],
                            width="stretch"
                        )
