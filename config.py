import os
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")

OFFERING_DESCRIPTION = os.getenv(
    "OFFERING_DESCRIPTION",
    "ALX Enterprise B2B corporate training programs in AI, Data (Science, Analytics, Engineering), Digital Skills, and Leadership. Sold as online courses, in-person workshops, and a 6-month management leadership program. Target clients: Enterprise & mid-market companies (50+ employees) in Morocco going through digital transformation, AI adoption, or modernization pressure (Banking, Telecom, Retail, Tech, Pharma, Manufacturing, Services)."
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
