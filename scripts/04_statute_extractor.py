"""
Day 4 — Statute Extractor
Extracts statute references from judgment texts.
Handles: IPC sections, CrPC sections, Constitutional articles, NDPS, POCSO, etc.
Creates REFERS_TO relationships between cases and statutes.
"""
import os
import sys
import re
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from utils import load_json, save_json, print_banner, print_stats, PROCESSED_DIR


# Statute extraction patterns for Indian law
STATUTE_PATTERNS = [
    # "Section X of the Indian Penal Code" / "Section X IPC"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Indian\s+Penal\s+Code|I\.?P\.?C\.?)',
     "Indian Penal Code", "IPC"),

    # "Section X of the Code of Criminal Procedure" / "Section X CrPC"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Code\s+of\s+Criminal\s+Procedure|Cr\.?P\.?C\.?)',
     "Code of Criminal Procedure", "CrPC"),

    # "Section X of the Code of Civil Procedure" / "Section X CPC"
    (r'Section\s+(\d+)\s+(?:of\s+(?:the\s+)?)?(?:Code\s+of\s+Civil\s+Procedure|C\.?P\.?C\.?)',
     "Code of Civil Procedure", "CPC"),

    # "Article X of the Constitution"
    (r'Article\s+(\d+[\(\)\w]*)\s+(?:of\s+(?:the\s+)?)?(?:Constitution\s+of\s+India|Constitution)',
     "Constitution of India", "Constitution"),

    # Standalone "Article X" (common in constitutional cases)
    (r'Article\s+(\d+[\(\)\w]*?)(?:\s|,|\.|;)',
     "Constitution of India", "Constitution"),

    # "Section X of the NDPS Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:NDPS\s+Act|Narcotic\s+Drugs)',
     "NDPS Act", "NDPS"),

    # "Section X of the POCSO Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:POCSO\s+Act|Protection\s+of\s+Children)',
     "POCSO Act", "POCSO"),

    # "Section X of the Prevention of Corruption Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Prevention\s+of\s+Corruption\s+Act|P\.?C\.?\s*Act)',
     "Prevention of Corruption Act", "PCA"),

    # "Section X of the Hindu Marriage Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Hindu\s+Marriage\s+Act|H\.?M\.?A\.?)',
     "Hindu Marriage Act", "HMA"),

    # "Section X of the Negotiable Instruments Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Negotiable\s+Instruments?\s+Act|N\.?I\.?\s*Act)',
     "Negotiable Instruments Act", "NI Act"),

    # "Section X of the Arbitration and Conciliation Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Arbitration(?:\s+and\s+Conciliation)?\s+Act)',
     "Arbitration and Conciliation Act", "ACA"),

    # "Section X of the Information Technology Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Information\s+Technology\s+Act|I\.?T\.?\s*Act)',
     "Information Technology Act", "IT Act"),

    # "Section X of the Dowry Prohibition Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Dowry\s+Prohibition\s+Act)',
     "Dowry Prohibition Act", "DPA"),

    # "Section X of the SC/ST Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:SC/?ST.*?Act|Scheduled\s+Castes)',
     "SC/ST Prevention of Atrocities Act", "SC/ST Act"),

    # "Section X of the Right to Information Act"
    (r'Section\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?(?:Right\s+to\s+Information\s+Act|R\.?T\.?I\.?\s*Act)',
     "Right to Information Act", "RTI"),

    # "Order X Rule Y CPC" patterns
    (r'Order\s+([IVXLC]+)\s+Rule\s+(\d+)\s+(?:of\s+(?:the\s+)?)?(?:Code\s+of\s+Civil\s+Procedure|C\.?P\.?C\.?)',
     "Code of Civil Procedure", "CPC"),

    # Generic "Section X of the [Act Name]"
    (r'Section\s+(\d+[A-Z]?)\s+of\s+the\s+([A-Z][a-zA-Z\s]+?Act)',
     None, None),
]


def extract_statutes_from_text(text):
    """Extract all statute references from judgment text."""
    statutes = []
    seen = set()

    for pattern_info in STATUTE_PATTERNS:
        pattern = pattern_info[0]
        default_act = pattern_info[1]
        default_abbr = pattern_info[2]

        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = match.groups()

            if default_act is None and len(groups) >= 2:
                # Generic pattern
                section = groups[0]
                act_name = groups[1].strip()
                abbr = act_name[:3].upper()
            elif "Order" in pattern and len(groups) >= 2:
                section = f"Order {groups[0]} Rule {groups[1]}"
                act_name = default_act
                abbr = default_abbr
            else:
                section = f"Section {groups[0]}" if not groups[0].startswith("Article") else groups[0]
                if "Article" in pattern:
                    section = f"Article {groups[0]}"
                act_name = default_act
                abbr = default_abbr

            statute_key = f"{section}|{act_name}"
            if statute_key not in seen:
                seen.add(statute_key)
                statutes.append({
                    "section": section,
                    "act_name": act_name,
                    "abbreviation": abbr,
                    "full_reference": f"{section} of the {act_name}",
                })

    return statutes


def extract_statutes_from_raw(case):
    """Extract statutes from the raw cited_statutes field."""
    statutes = []
    raw_statutes = case.get("cited_statutes_raw", [])

    for s in raw_statutes:
        if isinstance(s, (list, tuple)) and len(s) >= 3:
            statutes.append({
                "section": s[0],
                "act_name": s[1],
                "abbreviation": s[2],
                "full_reference": f"{s[0]} of the {s[1]}",
            })

    return statutes


def run_statute_extraction():
    """Main statute extraction pipeline."""
    print_banner("Day 4 — Statute Extractor")

    # Load dataset
    judgments_path = os.path.join(PROCESSED_DIR, "judgments.json")
    cases = load_json(judgments_path)
    print(f"Loaded {len(cases)} cases.\n")

    all_statute_rels = []
    statute_counter = Counter()
    act_counter = Counter()
    all_unique_statutes = set()

    for i, case in enumerate(cases):
        # Method 1: From structured field
        field_statutes = extract_statutes_from_raw(case)

        # Method 2: From text via regex
        text_statutes = extract_statutes_from_text(case.get("judgment_text", ""))

        # Merge (deduplicate by full_reference)
        seen_refs = set()
        merged = []
        for s in field_statutes + text_statutes:
            ref = s["full_reference"]
            if ref not in seen_refs:
                seen_refs.add(ref)
                merged.append(s)

        for statute in merged:
            statute_id = f"{statute['section']}_{statute['abbreviation']}".replace(" ", "_")
            rel = {
                "case_id": case["case_id"],
                "case_name": case["case_name"],
                "statute_id": statute_id,
                "section": statute["section"],
                "act_name": statute["act_name"],
                "abbreviation": statute["abbreviation"],
                "full_reference": statute["full_reference"],
                "relationship": "REFERS_TO",
            }
            all_statute_rels.append(rel)
            statute_counter[statute["full_reference"]] += 1
            act_counter[statute["act_name"]] += 1
            all_unique_statutes.add(statute_id)

        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(cases)} cases...")

    # Build statute profiles
    statute_profiles = []
    statute_groups = {}
    for rel in all_statute_rels:
        sid = rel["statute_id"]
        if sid not in statute_groups:
            statute_groups[sid] = {
                "statute_id": sid,
                "section": rel["section"],
                "act_name": rel["act_name"],
                "abbreviation": rel["abbreviation"],
                "full_reference": rel["full_reference"],
                "cases": [],
                "total_references": 0,
            }
        statute_groups[sid]["cases"].append({
            "case_id": rel["case_id"],
            "case_name": rel["case_name"],
        })
        statute_groups[sid]["total_references"] += 1

    statute_profiles = sorted(statute_groups.values(), key=lambda x: -x["total_references"])

    # Save results
    rels_path = os.path.join(PROCESSED_DIR, "statute_case_relations.json")
    profiles_path = os.path.join(PROCESSED_DIR, "statute_profiles.json")

    save_json(all_statute_rels, rels_path)
    save_json(statute_profiles, profiles_path)

    # Print top statutes
    print("\nTop 20 Most Referenced Statutes:")
    print("-" * 60)
    for ref, count in statute_counter.most_common(20):
        print(f"  [{count:4d} refs] {ref}")

    print("\nAct Distribution:")
    print("-" * 60)
    for act, count in act_counter.most_common(10):
        print(f"  [{count:4d} refs] {act}")

    print_stats({
        "Total statute-case relationships": len(all_statute_rels),
        "Unique statutes identified": len(all_unique_statutes),
        "Unique acts referenced": len(act_counter),
        "Average statutes per case": f"{len(all_statute_rels) / len(cases):.1f}",
    })

    print(f"\n[OK] Statute-case relations saved to: {rels_path}")
    print(f"[OK] Statute profiles saved to: {profiles_path}")
    return all_statute_rels


if __name__ == "__main__":
    run_statute_extraction()
