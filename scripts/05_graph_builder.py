"""
Day 5 — Graph Builder
Builds the legal knowledge graph using NetworkX.
Creates nodes: Case, Judge, Statute
Creates relationships: CITES, DECIDED, REFERS_TO
"""
import os, sys, json
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from utils import load_json, save_json, print_banner, print_stats, PROCESSED_DIR

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

def build_graph():
    print_banner("Day 5 — Graph Builder")
    cases = load_json(os.path.join(PROCESSED_DIR, "judgments.json"))
    citations = load_json(os.path.join(PROCESSED_DIR, "citations.json"))
    judge_rels = load_json(os.path.join(PROCESSED_DIR, "judge_case_relations.json"))
    statute_rels = load_json(os.path.join(PROCESSED_DIR, "statute_case_relations.json"))
    print(f"Cases: {len(cases)}, Citations: {len(citations)}")
    print(f"Judge Rels: {len(judge_rels)}, Statute Rels: {len(statute_rels)}\n")

    graph = {"nodes": [], "edges": [], "stats": {}}

    # Case nodes
    for c in cases:
        graph["nodes"].append({"id": c["case_id"], "label": c["case_name"], "type": "Case",
            "properties": {"name": c["case_name"], "year": c["year"], "court": c["court"],
                "case_type": c.get("case_type",""), "date": c.get("date",""), "judges": c.get("judges",[])}})

    # Judge nodes
    judge_ids = {}
    for r in judge_rels:
        jn = r["judge_name"]
        if jn not in judge_ids:
            jid = f"judge_{jn.replace(' ','_').lower()}"
            judge_ids[jn] = jid
            graph["nodes"].append({"id": jid, "label": f"Justice {jn}", "type": "Judge",
                "properties": {"name": jn, "full_name": f"Justice {jn}"}})

    # Statute nodes
    stat_ids = set()
    for r in statute_rels:
        sid = r["statute_id"]
        if sid not in stat_ids:
            stat_ids.add(sid)
            graph["nodes"].append({"id": sid, "label": r["full_reference"], "type": "Statute",
                "properties": {"section": r["section"], "act_name": r["act_name"],
                    "abbreviation": r["abbreviation"], "full_reference": r["full_reference"]}})

    # Edges
    for ci in citations:
        graph["edges"].append({"source": ci["source_case_id"], "target": ci["target_case_id"],
            "type": "CITES", "properties": {"source_name": ci["source_case_name"], "target_name": ci["target_case_name"]}})
    for r in judge_rels:
        jid = judge_ids.get(r["judge_name"])
        if jid:
            graph["edges"].append({"source": jid, "target": r["case_id"], "type": "DECIDED",
                "properties": {"judge_name": r["judge_name"], "year": r["year"]}})
    for r in statute_rels:
        graph["edges"].append({"source": r["case_id"], "target": r["statute_id"], "type": "REFERS_TO",
            "properties": {"case_name": r["case_name"], "statute": r["full_reference"]}})

    # Landmark detection
    cit_counts = Counter(ci["target_case_id"] for ci in citations)
    for cid, count in cit_counts.most_common(50):
        if count >= 10:
            for n in graph["nodes"]:
                if n["id"] == cid:
                    n["properties"]["is_landmark"] = True
                    n["properties"]["citation_count"] = count
                    break

    ec = Counter(e["type"] for e in graph["edges"])
    nc = Counter(n["type"] for n in graph["nodes"])
    graph["stats"] = {"total_nodes": len(graph["nodes"]), "total_edges": len(graph["edges"]),
        "case_nodes": nc.get("Case",0), "judge_nodes": nc.get("Judge",0), "statute_nodes": nc.get("Statute",0),
        "cites_edges": ec.get("CITES",0), "decided_edges": ec.get("DECIDED",0), "refers_to_edges": ec.get("REFERS_TO",0)}

    save_json(graph, os.path.join(PROCESSED_DIR, "knowledge_graph.json"))
    if HAS_NX:
        G = nx.DiGraph()
        for n in graph["nodes"]: G.add_node(n["id"], label=n["label"], node_type=n["type"], **n["properties"])
        for e in graph["edges"]: G.add_edge(e["source"], e["target"], edge_type=e["type"])
        graph["stats"]["density"] = round(nx.density(G), 6)
    print_stats(graph["stats"])
    return graph

if __name__ == "__main__":
    build_graph()
