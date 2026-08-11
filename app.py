import os
import glob
from datetime import datetime
import streamlit as st

# Must happen before importing config/pipeline: copy any matching Streamlit Cloud
# "Secrets" into the environment so config.py (plain os.getenv, unchanged) picks
# them up exactly like it would a local .env file.
for _key in ("APOLLO_API_KEY", "PERPLEXITY_API_KEY", "PERPLEXITY_MODEL", "OFFERING_DESCRIPTION"):
    if _key in st.secrets:
        os.environ[_key] = str(st.secrets[_key])

from config import APOLLO_API_KEY, PERPLEXITY_API_KEY, DEFAULT_EMPLOYEE_RANGES, DEFAULT_INDUSTRIES
from pipeline import run_pipeline, default_output_filename

st.set_page_config(page_title="ALX Enterprise Prospecting", page_icon="🏢", layout="centered")

st.title("🏢 ALX Enterprise B2B Prospecting")
st.caption("Source companies, AI-qualify them, find decision-makers, and generate sales briefs — powered by Apollo + Perplexity.")

# Recovery: the pipeline saves progress to disk after every company/contact, not
# just at the end — so a run that dies partway (dropped connection, app restart,
# an API error) still leaves a file with whatever was completed. Surface any of
# those here so the credits already spent on them aren't lost.
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

if not APOLLO_API_KEY or not PERPLEXITY_API_KEY:
    st.error(
        "Missing API keys. If you're running this locally, set APOLLO_API_KEY and "
        "PERPLEXITY_API_KEY in a .env file. If this app is deployed, add them under "
        "your app's **Settings → Secrets** in Streamlit Community Cloud."
    )
    st.stop()

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
             "Each candidate scanned spends Apollo + Perplexity credits, so worst-case cost scales with this too."
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

    log_lines = []
    with st.status("Running pipeline...", expanded=True) as status:
        def on_progress(msg: str):
            log_lines.append(msg)
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
