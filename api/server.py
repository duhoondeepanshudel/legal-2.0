"""
Flask API Server for the Legal Knowledge Graph.
Serves graph data and query results to the web frontend.
Production-ready: gunicorn-compatible, env-configured, gzip-compressed.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
from utils import PROCESSED_DIR
from _06_graph_queries_api import *
import json
import re
import gzip
from io import BytesIO

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web"))
CORS(app)

# ── Gzip compression middleware ─────────────────────────────────────
@app.after_request
def compress_response(response):
    """Gzip responses larger than 500 bytes if client supports it."""
    if (response.status_code < 200 or response.status_code >= 300 or
        response.direct_passthrough or
        'Content-Encoding' in response.headers or
        len(response.get_data()) < 500):
        return response

    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response

    buf = BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=buf, compresslevel=6) as gz:
        gz.write(response.get_data())

    response.set_data(buf.getvalue())
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.get_data())
    response.headers['Vary'] = 'Accept-Encoding'
    return response


# ── Cache headers for static assets ─────────────────────────────────
@app.after_request
def add_cache_headers(response):
    """Add cache headers for static assets."""
    if request.path.startswith('/css/') or request.path.startswith('/js/'):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


# ── Load graph data once at startup ─────────────────────────────────
GRAPH = None
JUDGMENTS = None  # case_id -> full judgment record

def get_graph():
    global GRAPH
    if GRAPH is None:
        gpath = os.path.join(PROCESSED_DIR, "knowledge_graph.json")
        with open(gpath, "r", encoding="utf-8") as f:
            GRAPH = json.load(f)
    return GRAPH

def get_judgments():
    global JUDGMENTS
    if JUDGMENTS is None:
        jpath = os.path.join(PROCESSED_DIR, "judgments.json")
        with open(jpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        JUDGMENTS = {c["case_id"]: c for c in data}
    return JUDGMENTS

def generate_summary(text, max_len=400):
    """Generate a concise summary from judgment text."""
    if not text:
        return "No summary available."
    # Try to find conclusion/order paragraphs
    lines = text.split('\n')
    conclusion_lines = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\d+\.\s', stripped):
            # Check for conclusion/order keywords
            lower = stripped.lower()
            if any(kw in lower for kw in ['conclusion', 'in light of', 'accordingly', 'in view of',
                'in the result', 'disposed of', 'is allowed', 'is dismissed',
                'we are of the', 'considered view', 'for the reasons', 'the petition',
                'the appeal', 'set aside', 'upheld', 'remanded']):
                conclusion_lines.append(stripped)
    if conclusion_lines:
        summary = ' '.join(conclusion_lines)
        if len(summary) > max_len:
            summary = summary[:max_len].rsplit(' ', 1)[0] + '...'
        return summary
    # Fallback: first substantive paragraph after the header
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 80 and not stripped.startswith('JUDGMENT') and not stripped.startswith('Bench'):
            if len(stripped) > max_len:
                stripped = stripped[:max_len].rsplit(' ', 1)[0] + '...'
            return stripped
    return text[:max_len] + '...' if len(text) > max_len else text


# ═══════════════════════════════════════════════════════════
# API Routes
# ═══════════════════════════════════════════════════════════

@app.route("/api/health")
def api_health():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "nyaya-graph"})

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)

@app.route("/api/stats")
def api_stats():
    g = get_graph()
    return jsonify(g.get("stats", {}))

@app.route("/api/graph/sample")
def api_graph_sample():
    """Return a sample subgraph for visualization (limited nodes for performance)."""
    g = get_graph()
    limit = int(request.args.get("limit", 200))
    node_type = request.args.get("type", "all")
    nodes = []
    node_ids = set()
    for n in g["nodes"]:
        if node_type != "all" and n["type"] != node_type:
            continue
        nodes.append(n)
        node_ids.add(n["id"])
        if len(nodes) >= limit:
            break
    edges = [e for e in g["edges"] if e["source"] in node_ids and e["target"] in node_ids]
    return jsonify({"nodes": nodes, "edges": edges[:limit*3]})

@app.route("/api/landmarks")
def api_landmarks():
    g = get_graph()
    limit = int(request.args.get("limit", 20))
    return jsonify(query_landmark_cases_api(g, limit))

@app.route("/api/judges")
def api_judges():
    g = get_graph()
    limit = int(request.args.get("limit", 20))
    return jsonify(query_judge_network_api(g, limit))

@app.route("/api/statutes")
def api_statutes():
    g = get_graph()
    limit = int(request.args.get("limit", 20))
    return jsonify(query_statute_impact_api(g, limit))

@app.route("/api/search")
def api_search():
    g = get_graph()
    q = request.args.get("q", "")
    limit = int(request.args.get("limit", 30))
    return jsonify(search_graph_api(g, q, limit))

@app.route("/api/case/<case_id>")
def api_case_detail(case_id):
    g = get_graph()
    j = get_judgments()
    result = query_case_by_id_api(g, case_id)
    # Enrich with judgment text and summary
    if case_id in j:
        jdata = j[case_id]
        result["judgment_text"] = jdata.get("judgment_text", "")
        result["summary"] = generate_summary(jdata.get("judgment_text", ""))
    return jsonify(result)

@app.route("/api/case/search/<case_name>")
def api_case_search(case_name):
    g = get_graph()
    return jsonify(query_case_detail_api(g, case_name))

@app.route("/api/judge/<judge_name>/cases")
def api_judge_cases(judge_name):
    g = get_graph()
    return jsonify(query_judge_cases_api(g, judge_name))

@app.route("/api/statute/<path:statute_query>/cases")
def api_statute_cases(statute_query):
    g = get_graph()
    return jsonify(query_statute_cases_api(g, statute_query))

@app.route("/api/courts")
def api_courts():
    g = get_graph()
    return jsonify(query_court_stats_api(g))

@app.route("/api/years")
def api_years():
    g = get_graph()
    return jsonify(query_year_stats_api(g))

@app.route("/api/graph/neighborhood/<node_id>")
def api_neighborhood(node_id):
    """Get neighborhood subgraph around a node."""
    g = get_graph()
    depth = int(request.args.get("depth", 1))
    return jsonify(get_neighborhood_api(g, node_id, depth))

@app.route("/api/cases")
def api_cases():
    """Paginated, searchable, filterable case listing."""
    j = get_judgments()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = request.args.get("q", "").lower()
    court = request.args.get("court", "").lower()
    year = request.args.get("year", "")
    sort_by = request.args.get("sort", "year_desc")

    all_cases = list(j.values())

    # Filter
    if q:
        all_cases = [c for c in all_cases if q in c["case_name"].lower()]
    if court:
        all_cases = [c for c in all_cases if court in c.get("court", "").lower()]
    if year:
        try:
            all_cases = [c for c in all_cases if c.get("year") == int(year)]
        except ValueError:
            pass

    # Sort
    if sort_by == "year_desc":
        all_cases.sort(key=lambda c: c.get("year", 0), reverse=True)
    elif sort_by == "year_asc":
        all_cases.sort(key=lambda c: c.get("year", 0))
    elif sort_by == "name":
        all_cases.sort(key=lambda c: c.get("case_name", ""))

    total = len(all_cases)
    start = (page - 1) * per_page
    end = start + per_page
    page_cases = all_cases[start:end]

    # Build response (summary only, not full text)
    results = []
    for c in page_cases:
        results.append({
            "case_id": c["case_id"],
            "case_name": c["case_name"],
            "year": c.get("year", ""),
            "court": c.get("court", ""),
            "case_type": c.get("case_type", ""),
            "date": c.get("date", ""),
            "judges": c.get("judges", []),
            "summary": generate_summary(c.get("judgment_text", ""), 200),
        })

    return jsonify({
        "cases": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })

@app.route("/api/courts/list")
def api_courts_list():
    """Return unique court names for filtering."""
    j = get_judgments()
    courts = sorted(set(c.get("court", "") for c in j.values()))
    return jsonify(courts)


# ═══════════════════════════════════════════════════════════
# Error Handlers
# ═══════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(app.static_folder, "index.html")

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print(f"Starting Legal Knowledge Graph API Server on port {port}...")
    print(f"Open http://localhost:{port} in your browser.\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
