# ALX Enterprise Morocco — B2B Prospecting Pipeline

This repository provides a complete Python automation script tailored specifically for **ALX Enterprise Morocco**. It builds a qualified B2B prospect list and generates pre-call briefing reports for sales representatives.

---

## 💡 How It Solves the Apollo Plan Limitation

Standard Apollo accounts restrict direct Organization Search (`/v1/organizations/search`). 
This pipeline uses **People-First Sourcing** (`/v1/mixed_people/api_search`), which searches directly for target decision-maker roles at companies with 200–10,000 employees in Morocco. Each result returns both the **Contact details** and their **Employer metadata** in a single API call!

---

## ⚙️ The 2-Step Automated Process

### **Step 1 — Find and Qualify**
- Searches Apollo for contacts matching target roles (HR Directors, Head of L&D, COOs, Chief Digital Officers, CTOs, VP Transformation).
- **Perplexity AI (`sonar`)** screens the company and contact against ALX Enterprise offering rules (Corporate training in AI, Data Science, Digital Skills, Leadership).
- Assigns a status: **Go**, **No-Go**, or **Review** with a single-sentence reason.

### **Step 2 — Research and Brief (For 'Go' Prospects)**
For every prospect marked **Go**, **Perplexity AI** executes web research on the contact and company to generate 4 briefing columns:
1. **Contact Profile & Background**: Tenure, career highlights, and role scope.
2. **Best Opening Sales Angle**: Personalized hook connecting ALX Enterprise offerings (bootcamps/workshops/leadership program) to their context.
3. **Target Company Brief**: Scale, digital initiatives, and workforce training needs.
4. **Industry Digital Journey**: Positioning on where the company sits in its industry's modernization/AI curve.

All results are saved into a single master Excel spreadsheet: `ALX_Morocco_B2B_Prospects.xlsx`.

---

## 🏃 Quick Start & Commands

### 1. Configure `.env`
Ensure your keys are set in `.env`:
```env
APOLLO_API_KEY=your_key
PERPLEXITY_API_KEY=your_key
PERPLEXITY_MODEL=sonar
```

### 2. Run Prospecting Batch
```bash
# Default run for Morocco (200-10,000 employees)
python main.py --limit 20 --output ALX_Morocco_B2B_Prospects.xlsx

# Run with custom location or batch size
python main.py --locations Morocco --limit 50 --output Morocco_Q3_Batch.xlsx
```

---

## 👥 For Your Team — Web Form (No Python Required)

Teammates don't need Python, a terminal, or the API keys to run searches — `app.py` is a Streamlit web form that wraps this same pipeline (`pipeline.py`) behind Industry / Country / Size fields, a live progress log, and an Excel download button.

- **Run it locally**: `streamlit run app.py` (uses your local `.env`, same as the CLI).
- **Deployed version**: once hosted on Streamlit Community Cloud, share the app URL — API keys live in that app's Secrets, never on a teammate's machine.
- The Industries dropdown is populated from `apollo_industries_reference.txt` — real values pulled from Apollo's own data (see that file's header for how/when it was collected). Don't delete it; the web form reads it directly.

---

## 📌 Team Decisions & Recommendations

1. **Getting Full Contact Details (Real Name, Email, LinkedIn)**:
   - **Recommendation**: Standard Apollo search provides Names, Job Titles, and LinkedIn URLs without extra credits. Unlocking verified corporate emails costs Apollo credits per contact. We recommend retrieving Names + LinkedIn URLs for all candidates, and unlocking verified Emails **only for 'Go' status prospects** to keep API costs minimal.
2. **List of Job Titles**:
   - **Recommendation**: Our default search includes `HR Director`, `Head of L&D`, `COO`, `Chief Digital Officer`, `CTO`, and `Head of Transformation`. We can pass custom `--titles` flags dynamically when targeting specific industries (e.g. adding `VP Engineering` for Tech, `Chief Operations Officer` for Manufacturing).
3. **Scaling & Automation**:
   - **Recommendation**: Running via this Python script allows batch sizes up to thousands of contacts with zero per-month plan costs on automation tools (like Make/Zapier). It can be scheduled via `cron` or run on-demand by sales managers.
