import os
import streamlit as st

# Must happen before importing config/pipeline: copy any matching Streamlit Cloud
# "Secrets" into the environment so config.py (plain os.getenv, unchanged) picks
# them up exactly like it would a local .env file.
for _key in ("APOLLO_API_KEY", "PERPLEXITY_API_KEY", "PERPLEXITY_MODEL", "OFFERING_DESCRIPTION"):
    if _key in st.secrets:
        os.environ[_key] = str(st.secrets[_key])

from config import APOLLO_API_KEY, PERPLEXITY_API_KEY, DEFAULT_EMPLOYEE_RANGES, DEFAULT_INDUSTRIES
from pipeline import run_pipeline

st.set_page_config(page_title="ALX Enterprise Prospecting", page_icon="🏢", layout="centered")

st.title("🏢 ALX Enterprise B2B Prospecting")
st.caption("Source companies, AI-qualify them, find decision-makers, and generate sales briefs — powered by Apollo + Perplexity.")

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
        "Number of companies to source", min_value=1, max_value=50, value=10, step=1,
        help="Each company spends Apollo + Perplexity credits — keep this modest."
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
                output_path=f"prospects_{'_'.join(locations)}.xlsx",
                on_progress=on_progress
            )
        except RuntimeError as e:
            status.update(label=f"Failed: {e}", state="error")
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
            use_container_width=True
        )
