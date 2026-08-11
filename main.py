import argparse

from config import (
    DEFAULT_LOCATIONS,
    DEFAULT_EMPLOYEE_RANGES,
    DEFAULT_INDUSTRIES,
    DEFAULT_COMPANY_LIMIT
)
from pipeline import run_pipeline, default_output_filename

def parse_args():
    parser = argparse.ArgumentParser(description="ALX Enterprise 2-Phase B2B Sourcing, Qualification & Enrichment Pipeline")
    parser.add_argument("--locations", nargs="+", default=DEFAULT_LOCATIONS, help="Target country (default: Morocco)")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_INDUSTRIES, help="Target industry keywords (loose Apollo-side keyword tag match)")
    parser.add_argument("--industries", nargs="+", default=None, help="Exact Apollo 'industry' field values to strictly filter to client-side, e.g. --industries \"hospital & health care\" \"medical practice\". See apollo_industries_reference.txt for real values pulled from Apollo's data. If omitted, only --keywords applies.")
    parser.add_argument("--employee-ranges", nargs="+", default=DEFAULT_EMPLOYEE_RANGES, help="Employee ranges (e.g. 51,200 201,500 501,1000 1001,5000 5001,10000)")
    parser.add_argument("--limit", type=int, default=DEFAULT_COMPANY_LIMIT, help="Number of 'Go'-qualified companies to find (default: 50) — Apollo is scanned as deep as needed (up to 5x this number) to reach it")
    parser.add_argument("--output", type=str, default=None, help="Output Excel filename (default: auto-named from industry + limit)")
    return parser.parse_args()

def main():
    args = parse_args()

    print("=========================================================================")
    print("🚀 ALX ENTERPRISE 2-PHASE B2B SOURCING, QUALIFICATION & BRIEFING PIPELINE")
    print("=========================================================================")

    output_path = args.output or default_output_filename(args.industries, args.keywords, args.limit)

    try:
        run_pipeline(
            locations=args.locations,
            keywords=args.keywords,
            industries=args.industries,
            employee_ranges=args.employee_ranges,
            limit=args.limit,
            output_path=output_path,
            on_progress=lambda msg: print(f"\n{msg}")
        )
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return

    print("\n=========================================================================")

if __name__ == "__main__":
    main()
