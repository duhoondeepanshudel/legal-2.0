"""
Day 6 — Graph Queries (Legal Intelligence)
Provides powerful analytical queries over the knowledge graph.
"""
import os, sys, json
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from utils import load_json, print_banner, PROCESSED_DIR


def load_graph():
    return load_json(os.path.join(PROCESSED_DIR, "knowledge_graph.json"))


def query_landmark_cases(graph, limit=20):
    """Find most cited cases (landmark detection)."""
    cit_count = Counter()
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Case"}
    for e in graph["edges"]:
        if e["type"] == "CITES":
            cit_count[e["target"]] += 1
    results = []
    for cid, count in cit_count.most_common(limit):
        results.append({"case_id": cid, "case_name": id_to_name.get(cid, "Unknown"), "citations": count})
    return results


def query_precedents(graph, case_name):
    """Find all precedents for a given case."""
    case_id = None
    for n in graph["nodes"]:
        if n["type"] == "Case" and case_name.lower() in n["label"].lower():
            case_id = n["id"]
            break
    if not case_id:
        return []
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Case"}
    return [{"case_id": e["target"], "case_name": id_to_name.get(e["target"], "Unknown")}
            for e in graph["edges"] if e["type"] == "CITES" and e["source"] == case_id]


def query_citing_cases(graph, case_name):
    """Find all cases that cite a given case."""
    case_id = None
    for n in graph["nodes"]:
        if n["type"] == "Case" and case_name.lower() in n["label"].lower():
            case_id = n["id"]
            break
    if not case_id:
        return []
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Case"}
    return [{"case_id": e["source"], "case_name": id_to_name.get(e["source"], "Unknown")}
            for e in graph["edges"] if e["type"] == "CITES" and e["target"] == case_id]


def query_judge_network(graph, limit=20):
    """Show which judges handled the most cases."""
    judge_count = Counter()
    for e in graph["edges"]:
        if e["type"] == "DECIDED":
            judge_count[e["source"]] += 1
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Judge"}
    return [{"judge_id": jid, "judge_name": id_to_name.get(jid, "Unknown"), "cases_decided": count}
            for jid, count in judge_count.most_common(limit)]


def query_judge_cases(graph, judge_name):
    """Find all cases decided by a specific judge."""
    judge_id = None
    for n in graph["nodes"]:
        if n["type"] == "Judge" and judge_name.lower() in n["label"].lower():
            judge_id = n["id"]
            break
    if not judge_id:
        return []
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Case"}
    return [{"case_id": e["target"], "case_name": id_to_name.get(e["target"], "Unknown")}
            for e in graph["edges"] if e["type"] == "DECIDED" and e["source"] == judge_id]


def query_statute_impact(graph, limit=20):
    """Find most referenced statutes."""
    stat_count = Counter()
    for e in graph["edges"]:
        if e["type"] == "REFERS_TO":
            stat_count[e["target"]] += 1
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Statute"}
    return [{"statute_id": sid, "statute_name": id_to_name.get(sid, "Unknown"), "references": count}
            for sid, count in stat_count.most_common(limit)]


def query_statute_cases(graph, statute_query):
    """Find all cases referencing a specific statute."""
    statute_id = None
    for n in graph["nodes"]:
        if n["type"] == "Statute" and statute_query.lower() in n["label"].lower():
            statute_id = n["id"]
            break
    if not statute_id:
        return []
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Case"}
    return [{"case_id": e["source"], "case_name": id_to_name.get(e["source"], "Unknown")}
            for e in graph["edges"] if e["type"] == "REFERS_TO" and e["target"] == statute_id]


def query_court_stats(graph):
    """Court-wise case distribution."""
    court_count = Counter()
    for n in graph["nodes"]:
        if n["type"] == "Case":
            court_count[n["properties"].get("court", "Unknown")] += 1
    return [{"court": c, "cases": cnt} for c, cnt in court_count.most_common()]


def query_year_stats(graph):
    """Year-wise case distribution."""
    year_count = Counter()
    for n in graph["nodes"]:
        if n["type"] == "Case":
            year_count[n["properties"].get("year", 0)] += 1
    return [{"year": y, "cases": cnt} for y, cnt in sorted(year_count.items())]


def query_case_detail(graph, case_name):
    """Get full details of a case including all relationships."""
    case_node = None
    for n in graph["nodes"]:
        if n["type"] == "Case" and case_name.lower() in n["label"].lower():
            case_node = n
            break
    if not case_node:
        return None
    cid = case_node["id"]
    id_to_name = {n["id"]: n["label"] for n in graph["nodes"]}
    prec = [{"id": e["target"], "name": id_to_name.get(e["target"],"")} for e in graph["edges"] if e["type"]=="CITES" and e["source"]==cid]
    cited_by = [{"id": e["source"], "name": id_to_name.get(e["source"],"")} for e in graph["edges"] if e["type"]=="CITES" and e["target"]==cid]
    judges = [{"id": e["source"], "name": id_to_name.get(e["source"],"")} for e in graph["edges"] if e["type"]=="DECIDED" and e["target"]==cid]
    statutes = [{"id": e["target"], "name": id_to_name.get(e["target"],"")} for e in graph["edges"] if e["type"]=="REFERS_TO" and e["source"]==cid]
    return {"case": case_node, "precedents_cited": prec, "cited_by": cited_by, "judges": judges, "statutes": statutes}


def search_graph(graph, query, limit=30):
    """Full-text search across all node types."""
    q = query.lower()
    results = []
    for n in graph["nodes"]:
        if q in n["label"].lower():
            results.append({"id": n["id"], "label": n["label"], "type": n["type"]})
            if len(results) >= limit:
                break
    return results


def run_demo_queries():
    """Run demo queries and print results."""
    print_banner("Day 6 — Legal Intelligence Queries")
    graph = load_graph()

    print("═══ TOP 10 LANDMARK CASES ═══")
    for r in query_landmark_cases(graph, 10):
        print(f"  [{r['citations']:3d} citations] {r['case_name']}")

    print("\n═══ TOP 10 ACTIVE JUDGES ═══")
    for r in query_judge_network(graph, 10):
        print(f"  [{r['cases_decided']:3d} cases] {r['judge_name']}")

    print("\n═══ TOP 10 REFERENCED STATUTES ═══")
    for r in query_statute_impact(graph, 10):
        print(f"  [{r['references']:3d} refs] {r['statute_name']}")

    print("\n═══ COURT DISTRIBUTION ═══")
    for r in query_court_stats(graph)[:5]:
        print(f"  {r['court']}: {r['cases']}")

    print("\n[OK] Query engine ready.")

if __name__ == "__main__":
    run_demo_queries()
