"""
Day 2 — Citation Extractor
Extracts case-to-case citation relationships from judgment texts.
IMPORTANT: Only creates citation links between cases that EXIST in the dataset.
No invented/hallucinated case references are included.
"""
import os
import sys
import re
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from utils import load_json, save_json, normalize_case_name, print_banner, print_stats, PROCESSED_DIR


def build_case_name_index(cases):
    """Build a lookup index of all case names in the dataset for matching."""
    index = {}
    for case in cases:
        # Index by full name
        name = case["case_name"]
        normalized = normalize_case_name(name).lower()
        index[normalized] = case["case_id"]

        # Also index by short forms (e.g., "Maneka Gandhi" from "Maneka Gandhi vs Union of India")
        parts = re.split(r'\s+vs\.?\s+', name, flags=re.IGNORECASE)
        if parts:
            petitioner_short = parts[0].strip().lower()
            if len(petitioner_short) > 3:
                index[petitioner_short] = case["case_id"]

    return index


def extract_citations_from_text(text, case_name_index, own_case_id):
    """
    Extract case citations from judgment text.
    Only returns citations to cases that EXIST in our dataset.
    """
    citations = set()

    # Pattern 1: "Name vs Name" style references
    pattern_vs = r'([A-Z][a-zA-Z\.\s]+?)\s+vs\.?\s+([A-Z][a-zA-Z\.\s]+?)(?:\s*[\(\[\,\.])'
    matches = re.findall(pattern_vs, text)
    for m in matches:
        full_name = f"{m[0].strip()} vs {m[1].strip()}"
        normalized = normalize_case_name(full_name).lower()
        if normalized in case_name_index:
            target_id = case_name_index[normalized]
            if target_id != own_case_id:
                citations.add(target_id)

    # Pattern 2: Direct full case name matches against our dataset
    text_lower = text.lower()
    for name_key, case_id in case_name_index.items():
        if case_id != own_case_id and len(name_key) > 10:
            if name_key in text_lower:
                citations.add(case_id)

    return list(citations)


def extract_citations_from_raw(case, case_name_index):
    """
    Extract citations from the raw cited_cases field.
    Only includes citations to cases that EXIST in our dataset.
    """
    citations = set()
    raw_citations = case.get("cited_cases_raw", [])

    for cited_name in raw_citations:
        normalized = normalize_case_name(cited_name).lower()
        # Check exact match
        if normalized in case_name_index:
            target_id = case_name_index[normalized]
            if target_id != case["case_id"]:
                citations.add(target_id)
            continue

        # Check partial match (petitioner name)
        parts = re.split(r'\s+vs\.?\s+', cited_name, flags=re.IGNORECASE)
        if parts:
            petitioner_short = parts[0].strip().lower()
            if petitioner_short in case_name_index:
                target_id = case_name_index[petitioner_short]
                if target_id != case["case_id"]:
                    citations.add(target_id)

    return list(citations)


def run_citation_extraction():
    """Main citation extraction pipeline."""
    print_banner("Day 2 — Citation Extractor")

    # Load dataset
    judgments_path = os.path.join(PROCESSED_DIR, "judgments.json")
    cases = load_json(judgments_path)
    print(f"Loaded {len(cases)} cases from dataset.\n")

    # Build case name index (only cases in our dataset)
    case_name_index = build_case_name_index(cases)
    print(f"Built case name index with {len(case_name_index)} entries.\n")

    # Build case_id -> case_name lookup
    id_to_name = {c["case_id"]: c["case_name"] for c in cases}

    # Extract citations
    all_citations = []
    citation_counts = Counter()
    cases_with_citations = 0

    for i, case in enumerate(cases):
        # Method 1: From raw cited_cases field (generator already tracked these)
        raw_cites = extract_citations_from_raw(case, case_name_index)

        # Method 2: From judgment text via regex
        text_cites = extract_citations_from_text(
            case.get("judgment_text", ""),
            case_name_index,
            case["case_id"]
        )

        # Merge (deduplicate)
        all_cited_ids = list(set(raw_cites + text_cites))

        if all_cited_ids:
            cases_with_citations += 1

        for target_id in all_cited_ids:
            citation_record = {
                "source_case_id": case["case_id"],
                "source_case_name": case["case_name"],
                "target_case_id": target_id,
                "target_case_name": id_to_name.get(target_id, "Unknown"),
                "relationship": "CITES",
            }
            all_citations.append(citation_record)
            citation_counts[target_id] += 1

        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(cases)} cases...")

    # Save citations
    output_path = os.path.join(PROCESSED_DIR, "citations.json")
    save_json(all_citations, output_path)

    # Find most cited cases
    most_cited = citation_counts.most_common(20)
    print("\nTop 20 Most Cited Cases (Landmark Detection):")
    print("-" * 60)
    for case_id, count in most_cited:
        name = id_to_name.get(case_id, "Unknown")
        print(f"  [{count:4d} citations] {name}")

    print_stats({
        "Total citation relationships": len(all_citations),
        "Cases with at least one citation": cases_with_citations,
        "Unique cited cases": len(citation_counts),
        "Average citations per case": f"{len(all_citations) / len(cases):.1f}",
        "Most cited case": id_to_name.get(most_cited[0][0], "N/A") if most_cited else "N/A",
    })

    print(f"\n[OK] Citations saved to: {output_path}")
    return all_citations


if __name__ == "__main__":
    run_citation_extraction()
