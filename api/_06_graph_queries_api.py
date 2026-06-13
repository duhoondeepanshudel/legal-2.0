"""
API query functions for the Flask server.
Adapted from 06_graph_queries.py for API use.
"""
from collections import Counter


def query_landmark_cases_api(graph, limit=20):
    cit = Counter()
    id_name = {n["id"]: n for n in graph["nodes"] if n["type"] == "Case"}
    for e in graph["edges"]:
        if e["type"] == "CITES": cit[e["target"]] += 1
    return [{"case_id": c, "case_name": id_name[c]["label"] if c in id_name else "?",
             "citations": cnt, "year": id_name[c]["properties"].get("year","") if c in id_name else "",
             "court": id_name[c]["properties"].get("court","") if c in id_name else ""}
            for c, cnt in cit.most_common(limit)]


def query_judge_network_api(graph, limit=20):
    jc = Counter()
    for e in graph["edges"]:
        if e["type"] == "DECIDED": jc[e["source"]] += 1
    id_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Judge"}
    return [{"judge_id": j, "judge_name": id_name.get(j, "?"), "cases_decided": c} for j, c in jc.most_common(limit)]


def query_statute_impact_api(graph, limit=20):
    sc = Counter()
    for e in graph["edges"]:
        if e["type"] == "REFERS_TO": sc[e["target"]] += 1
    id_name = {n["id"]: n["label"] for n in graph["nodes"] if n["type"] == "Statute"}
    return [{"statute_id": s, "statute_name": id_name.get(s, "?"), "references": c} for s, c in sc.most_common(limit)]


def search_graph_api(graph, query, limit=30):
    q = query.lower()
    results = []
    for n in graph["nodes"]:
        if q in n["label"].lower():
            results.append({"id": n["id"], "label": n["label"], "type": n["type"],
                            "properties": n.get("properties", {})})
            if len(results) >= limit: break
    return results


def query_case_by_id_api(graph, case_id):
    node = None
    for n in graph["nodes"]:
        if n["id"] == case_id: node = n; break
    if not node: return {"error": "Case not found"}
    id_name = {n["id"]: n["label"] for n in graph["nodes"]}
    prec = [{"id": e["target"], "name": id_name.get(e["target"],"")} for e in graph["edges"] if e["type"]=="CITES" and e["source"]==case_id]
    cited_by = [{"id": e["source"], "name": id_name.get(e["source"],"")} for e in graph["edges"] if e["type"]=="CITES" and e["target"]==case_id]
    judges = [{"id": e["source"], "name": id_name.get(e["source"],"")} for e in graph["edges"] if e["type"]=="DECIDED" and e["target"]==case_id]
    statutes = [{"id": e["target"], "name": id_name.get(e["target"],"")} for e in graph["edges"] if e["type"]=="REFERS_TO" and e["source"]==case_id]
    return {"case": node, "precedents_cited": prec, "cited_by": cited_by, "judges": judges, "statutes": statutes}


def query_case_detail_api(graph, case_name):
    for n in graph["nodes"]:
        if n["type"] == "Case" and case_name.lower() in n["label"].lower():
            return query_case_by_id_api(graph, n["id"])
    return {"error": "Case not found"}


def query_judge_cases_api(graph, judge_name):
    jid = None
    for n in graph["nodes"]:
        if n["type"] == "Judge" and judge_name.lower() in n["label"].lower():
            jid = n["id"]; break
    if not jid: return []
    id_name = {n["id"]: n for n in graph["nodes"] if n["type"] == "Case"}
    results = []
    for e in graph["edges"]:
        if e["type"] == "DECIDED" and e["source"] == jid and e["target"] in id_name:
            c = id_name[e["target"]]
            results.append({"case_id": c["id"], "case_name": c["label"],
                            "year": c["properties"].get("year",""), "court": c["properties"].get("court","")})
    return results


def query_statute_cases_api(graph, statute_query):
    sid = None
    for n in graph["nodes"]:
        if n["type"] == "Statute" and statute_query.lower() in n["label"].lower():
            sid = n["id"]; break
    if not sid: return []
    id_name = {n["id"]: n for n in graph["nodes"] if n["type"] == "Case"}
    results = []
    for e in graph["edges"]:
        if e["type"] == "REFERS_TO" and e["target"] == sid and e["source"] in id_name:
            c = id_name[e["source"]]
            results.append({"case_id": c["id"], "case_name": c["label"],
                            "year": c["properties"].get("year",""), "court": c["properties"].get("court","")})
    return results


def query_court_stats_api(graph):
    cc = Counter()
    for n in graph["nodes"]:
        if n["type"] == "Case": cc[n["properties"].get("court", "Unknown")] += 1
    return [{"court": c, "cases": cnt} for c, cnt in cc.most_common()]


def query_year_stats_api(graph):
    yc = Counter()
    for n in graph["nodes"]:
        if n["type"] == "Case": yc[n["properties"].get("year", 0)] += 1
    return [{"year": y, "cases": cnt} for y, cnt in sorted(yc.items())]


def get_neighborhood_api(graph, node_id, depth=1):
    """Get neighborhood subgraph around a node."""
    visited = {node_id}
    frontier = {node_id}
    for _ in range(depth):
        new_frontier = set()
        for e in graph["edges"]:
            if e["source"] in frontier and e["target"] not in visited:
                new_frontier.add(e["target"])
                visited.add(e["target"])
            if e["target"] in frontier and e["source"] not in visited:
                new_frontier.add(e["source"])
                visited.add(e["source"])
        frontier = new_frontier
        if not frontier: break
    nodes = [n for n in graph["nodes"] if n["id"] in visited]
    edges = [e for e in graph["edges"] if e["source"] in visited and e["target"] in visited]
    return {"nodes": nodes[:150], "edges": edges[:500]}
