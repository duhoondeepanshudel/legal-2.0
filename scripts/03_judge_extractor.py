"""
Day 3 — Judge Extractor
Extracts judge names and bench compositions from judgments.
Maps judges to cases with DECIDED relationship.
"""
import os
import sys
import re
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from utils import load_json, save_json, normalize_judge_name, print_banner, print_stats, PROCESSED_DIR


# Common patterns for judge names in Indian judgments
JUDGE_PATTERNS = [
    # "Bench: Justice X, Justice Y"
    r'(?:Bench|Coram|Present)\s*:\s*(.+?)(?:\n|$)',
    # "Justice X, J."
    r'(Justice\s+[A-Z][a-zA-Z\.\s]+?)(?:,\s*J\.|\s*J\.)',
    # "Delivered by Justice X"
    r'Delivered\s+by\s+(Justice\s+[A-Z][a-zA-Z\.\s]+?)(?:,|\s*J\.|\n)',
    # "Hon'ble Justice X"
    r"Hon'?ble\s+(Justice\s+[A-Z][a-zA-Z\.\s]+?)(?:,|\s*J\.|\n)",
]


def extract_judges_from_text(text):
    """Extract judge names from judgment text using regex patterns."""
    judges = set()

    for pattern in JUDGE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # Split by comma for multi-judge benches
            parts = re.split(r',\s*(?:and\s+)?', match)
            for part in parts:
                part = part.strip()
                # Clean up
                name = re.sub(r'^(Justice\s+)', '', part, flags=re.IGNORECASE)
                name = re.sub(r'\s*J\.\s*$', '', name)
                name = re.sub(r'\s+', ' ', name).strip()
                if name and len(name) > 2 and not name.startswith('('):
                    judges.add(name)

    return list(judges)


def extract_judges_from_field(case):
    """Extract judges from the judges field in case data."""
    judges = []
    raw_judges = case.get("judges", [])
    for j in raw_judges:
        name = normalize_judge_name(j)
        if name and len(name) > 2:
            judges.append(name)
    return judges


def run_judge_extraction():
    """Main judge extraction pipeline."""
    print_banner("Day 3 — Judge Extractor")

    # Load dataset
    judgments_path = os.path.join(PROCESSED_DIR, "judgments.json")
    cases = load_json(judgments_path)
    print(f"Loaded {len(cases)} cases.\n")

    all_judge_case_rels = []
    judge_counter = Counter()
    court_judge_map = {}
    all_unique_judges = set()

    for i, case in enumerate(cases):
        # Method 1: From structured field
        field_judges = extract_judges_from_field(case)

        # Method 2: From text (supplementary)
        text_judges = extract_judges_from_text(case.get("judgment_text", ""))

        # Merge (prefer field data, supplement with text)
        all_judges = list(set(field_judges + text_judges))

        for judge_name in all_judges:
            rel = {
                "judge_name": judge_name,
                "case_id": case["case_id"],
                "case_name": case["case_name"],
                "court": case["court"],
                "year": case["year"],
                "relationship": "DECIDED",
            }
            all_judge_case_rels.append(rel)
            judge_counter[judge_name] += 1
            all_unique_judges.add(judge_name)

            # Track court-judge mapping
            court = case["court"]
            if court not in court_judge_map:
                court_judge_map[court] = set()
            court_judge_map[court].add(judge_name)

        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(cases)} cases...")

    # Build judge profiles
    judge_profiles = []
    for judge_name in all_unique_judges:
        # Find all cases by this judge
        judge_cases = [r for r in all_judge_case_rels if r["judge_name"] == judge_name]
        courts = set(r["court"] for r in judge_cases)
        years = [r["year"] for r in judge_cases]

        profile = {
            "judge_name": judge_name,
            "total_cases": len(judge_cases),
            "courts": list(courts),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "cases": [{"case_id": r["case_id"], "case_name": r["case_name"]} for r in judge_cases],
        }
        judge_profiles.append(profile)

    # Save results
    rels_path = os.path.join(PROCESSED_DIR, "judge_case_relations.json")
    profiles_path = os.path.join(PROCESSED_DIR, "judge_profiles.json")

    save_json(all_judge_case_rels, rels_path)
    save_json(sorted(judge_profiles, key=lambda x: -x["total_cases"]), profiles_path)

    # Print top judges
    print("\nTop 20 Most Active Judges:")
    print("-" * 60)
    for judge, count in judge_counter.most_common(20):
        print(f"  [{count:4d} cases] Justice {judge}")

    print_stats({
        "Total judge-case relationships": len(all_judge_case_rels),
        "Unique judges identified": len(all_unique_judges),
        "Courts with judge data": len(court_judge_map),
        "Average cases per judge": f"{len(all_judge_case_rels) / max(len(all_unique_judges), 1):.1f}",
    })

    print(f"\n[OK] Judge-case relations saved to: {rels_path}")
    print(f"[OK] Judge profiles saved to: {profiles_path}")
    return all_judge_case_rels


if __name__ == "__main__":
    run_judge_extraction()
