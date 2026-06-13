"""
Day 1 — Legal Data Collector (Real Data from Indian Kanoon)
Scrapes real Indian legal judgments from indiankanoon.org.
Extracts: case names, dates, courts, judges, judgment text, citations, statutes.
Output format is compatible with pipeline Steps 2-5.
"""
import os
import sys
import json
import re
import time
import hashlib
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from utils import save_json, print_banner, print_stats, PROCESSED_DIR, RAW_DIR

# ─── Configuration ──────────────────────────────────────────────────
TARGET_CASES = 500
DELAY_MIN = 2.0
DELAY_MAX = 4.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 45

# ─── Search Queries (query, court_doctype, num_search_pages) ────────
SEARCH_QUERIES = [
    ("fundamental rights", "supremecourt", 5),
    ("basic structure doctrine", "supremecourt", 3),
    ("right to privacy", "supremecourt", 3),
    ("right to life article 21", "supremecourt", 5),
    ("freedom of speech article 19", "supremecourt", 3),
    ("right to equality article 14", "supremecourt", 3),
    ("judicial review", "supremecourt", 3),
    ("murder section 302 IPC", "supremecourt", 5),
    ("dowry death section 304B", "supremecourt", 3),
    ("cruelty section 498A", "supremecourt", 3),
    ("bail criminal appeal", "supremecourt", 5),
    ("NDPS narcotic drugs", "supremecourt", 3),
    ("anticipatory bail section 438", "supremecourt", 3),
    ("death sentence commutation", "supremecourt", 3),
    ("specific performance contract", "supremecourt", 3),
    ("land acquisition compensation", "supremecourt", 3),
    ("partition suit property", "supremecourt", 3),
    ("arbitration award challenge", "supremecourt", 3),
    ("negotiable instruments section 138", "supremecourt", 3),
    ("service matter termination", "supremecourt", 3),
    ("departmental inquiry misconduct", "supremecourt", 3),
    ("compassionate appointment", "supremecourt", 2),
    ("reservation OBC SC ST", "supremecourt", 3),
    ("divorce Hindu Marriage Act", "supremecourt", 3),
    ("maintenance wife section 125", "supremecourt", 3),
    ("child custody guardianship", "supremecourt", 2),
    ("income tax assessment", "supremecourt", 3),
    ("environment pollution", "supremecourt", 3),
    ("public interest litigation", "supremecourt", 3),
    ("writ petition article 226", "delhi", 5),
    ("criminal revision application", "bombay", 5),
    ("civil revision petition", "chennai", 5),
    ("writ petition service matter", "allahabad", 5),
    ("bail application", "delhi", 5),
    ("criminal appeal acquittal", "karnataka", 5),
    ("land acquisition", "allahabad", 3),
    ("motor accident compensation", "delhi", 3),
    ("habeas corpus", "delhi", 3),
    ("consumer complaint", "karnataka", 3),
    ("eviction tenant", "delhi", 3),
    ("POCSO child abuse", "delhi", 3),
    ("domestic violence protection", "delhi", 3),
    ("cheque bounce", "bombay", 3),
    ("appeal conviction", "allahabad", 3),
    ("special leave petition", "supremecourt", 5),
    ("section 482 quashing FIR", "allahabad", 3),
    ("mutual consent divorce", "delhi", 3),
    ("corruption prevention act", "delhi", 3),
    ("insolvency bankruptcy code", "supremecourt", 3),
    ("labor industrial dispute", "karnataka", 3),
    ("triple talaq", "supremecourt", 2),
    ("electoral bonds", "supremecourt", 2),
    ("sexual harassment workplace", "supremecourt", 2),
    ("right to education", "supremecourt", 2),
    ("preventive detention", "supremecourt", 2),
    ("contempt of court", "supremecourt", 2),
    ("cyber crime IT act", "delhi", 3),
    ("land revenue mutation", "allahabad", 3),
    ("trademark infringement", "delhi", 3),
    ("copyright violation", "bombay", 3),
    ("insurance claim", "supremecourt", 3),
    ("medical negligence", "supremecourt", 3),
    ("custodial death", "supremecourt", 2),
    ("inter state water dispute", "supremecourt", 2),
    ("election commission", "supremecourt", 2),
    ("RTI information", "delhi", 3),
]

COURT_MAP = {
    "supremecourt": "Supreme Court of India",
    "delhi": "Delhi High Court",
    "bombay": "Bombay High Court",
    "chennai": "Madras High Court",
    "calcutta": "Calcutta High Court",
    "karnataka": "Karnataka High Court",
    "allahabad": "Allahabad High Court",
    "gujarat": "Gujarat High Court",
    "kerala": "Kerala High Court",
    "punjab": "Punjab and Haryana High Court",
    "rajasthan": "Rajasthan High Court",
    "telangana": "Telangana High Court",
    "patna": "Patna High Court",
    "gauhati": "Gauhati High Court",
    "orissa": "Orissa High Court",
    "uttarakhand": "Uttarakhand High Court",
    "himachal": "Himachal Pradesh High Court",
    "jammu": "Jammu and Kashmir High Court",
    "hyderabad": "Telangana High Court",
    "madras": "Madras High Court",
}


def create_session():
    """Create a requests session that mimics a real browser."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    try:
        print("  Initializing session with Indian Kanoon...")
        resp = session.get("https://indiankanoon.org/", timeout=REQUEST_TIMEOUT)
        print(f"  Session initialized (status {resp.status_code}).\n")
        time.sleep(2)
    except Exception as e:
        print(f"  Warning: {e}\n")
    return session


def polite_delay():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def get_page(session, url, retries=MAX_RETRIES, params=None):
    """Fetch a page with retries and rate limiting."""
    for attempt in range(retries):
        try:
            polite_delay()
            resp = session.get(url, timeout=REQUEST_TIMEOUT, params=params)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (429, 403):
                wait = (attempt + 1) * 10
                print(f"    HTTP {resp.status_code}. Waiting {wait}s...")
                time.sleep(wait)
                if attempt >= 1:
                    session.cookies.clear()
                    session.get("https://indiankanoon.org/", timeout=REQUEST_TIMEOUT)
                    time.sleep(3)
            else:
                print(f"    HTTP {resp.status_code}")
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"    Error (attempt {attempt+1}): {str(e)[:60]}")
            time.sleep(5)
    return None


def search_cases(session, query, court_doctype, num_pages=1):
    """Search Indian Kanoon and return list of (doc_id, title) tuples."""
    results = []
    for page in range(num_pages):
        form_input = f"{query} doctypes: {court_doctype}"
        params = {"formInput": form_input}
        if page > 0:
            params["pagenum"] = page

        resp = get_page(session, "https://indiankanoon.org/search/", params=params)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Indian Kanoon uses /docfragment/ID/ links for search result titles
        frag_links = soup.find_all("a", href=re.compile(r"/docfragment/\d+/"))
        for link in frag_links:
            href = link.get("href", "")
            title = link.get_text(strip=True)
            m = re.search(r"/docfragment/(\d+)/", href)
            if not m or not title or len(title) < 10:
                continue
            # Skip pure law/statute entries
            if re.match(r'^(Article|Section|Order|Rule)\s+\d', title):
                continue
            if title.startswith("Constitution of India"):
                continue
            results.append((m.group(1), title))

    # Deduplicate
    seen = set()
    unique = []
    for doc_id, title in results:
        if doc_id not in seen:
            seen.add(doc_id)
            unique.append((doc_id, title))
    return unique


def parse_date(date_str):
    """Parse date from Indian Kanoon format."""
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str.strip())
    for fmt in ["%d %B, %Y", "%d %B %Y", "%B %d, %Y", "%d/%m/%Y",
                "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d"), dt.year
        except ValueError:
            continue
    ym = re.search(r'\b(19|20)\d{2}\b', date_str)
    return (f"{int(ym.group())}-01-01", int(ym.group())) if ym else (None, None)


def extract_court(soup, text, default_court):
    """Extract court name from the page."""
    # Check judgment text and page structure
    combined = text[:2000].lower()
    docsource = soup.find("div", class_="docsource_main")
    if docsource:
        combined += " " + docsource.get_text().lower()

    if "supreme court" in combined:
        return "Supreme Court of India"
    for key, name in COURT_MAP.items():
        if key in combined or name.lower() in combined:
            return name
    return default_court


def extract_judges(soup, full_text):
    """Extract judges from the judgment page."""
    judges = []

    # Method 1: benchid links (most reliable)
    bench_links = soup.find_all("a", href=re.compile(r"benchid:"))
    for link in bench_links:
        name = link.get_text(strip=True)
        if name and len(name) > 2:
            judges.append(f"Justice {name}")

    # Method 2: authorid links
    if not judges:
        for link in soup.find_all("a", href=re.compile(r"authorid:")):
            name = link.get_text(strip=True)
            if name and len(name) > 2:
                judges.append(f"Justice {name}")

    # Method 3: Parse BENCH section from <pre> tag or text
    if not judges:
        bench_match = re.search(
            r'BENCH:\s*\n?(.*?)(?:\n\s*\n|\nACT:|\nHEADNOTE:|\nJUDGM)',
            full_text[:3000], re.DOTALL
        )
        if bench_match:
            bench_text = bench_match.group(1).strip()
            for j in re.split(r'[,\n&]', bench_text):
                j = j.strip()
                if j and len(j) > 2:
                    j = re.sub(r'^(Hon\'?ble\s+|Mr\.?\s+|Chief\s+Justice\s+)',
                               '', j, flags=re.IGNORECASE).strip()
                    if j and not j.startswith("Justice"):
                        j = f"Justice {j}"
                    if j and len(j) > 5:
                        judges.append(j)

    # Method 4: Coram pattern
    if not judges:
        coram = re.search(r'(?:Coram|CORAM)\s*:?\s*\n?(.*?)(?:\n\s*\n)', full_text[:3000], re.DOTALL)
        if coram:
            for j in re.split(r'[,\n&]', coram.group(1)):
                j = j.strip()
                if j and len(j) > 3:
                    if not j.startswith("Justice"):
                        j = f"Justice {j}"
                    judges.append(j)

    # Deduplicate
    seen = set()
    unique = []
    for j in judges:
        k = j.lower().strip()
        if k not in seen and len(k) > 5:
            seen.add(k)
            unique.append(j)
    return unique if unique else ["Justice Unknown"]


def extract_case_type(case_name, text):
    """Determine case type."""
    t = (case_name + " " + text[:3000]).lower()
    for pattern, ctype in [
        (r'criminal\s+appeal', "Criminal Appeal"),
        (r'civil\s+appeal', "Civil Appeal"),
        (r'writ\s+petition\s*\(?\s*cri', "Writ Petition (Criminal)"),
        (r'writ\s+petition', "Writ Petition (Civil)"),
        (r'special\s+leave', "Special Leave Petition"),
        (r'transfer\s+petition', "Transfer Petition"),
        (r'review\s+petition', "Review Petition"),
        (r'contempt', "Contempt Petition"),
        (r'bail\s+appli', "Bail Application"),
        (r'anticipatory\s+bail', "Anticipatory Bail Application"),
        (r'habeas\s+corpus', "Habeas Corpus Petition"),
        (r'public\s+interest', "Public Interest Litigation"),
        (r'motor\s+accident', "Motor Accident Claim"),
        (r'crl\.?\s*appeal', "Criminal Appeal"),
    ]:
        if re.search(pattern, t):
            return ctype
    return "Civil Appeal"


def extract_cited_cases(soup, text):
    """Extract cited case names."""
    cited = set()
    jdiv = soup.find("div", class_="judgments")
    if jdiv:
        for link in jdiv.find_all("a", href=re.compile(r"/doc/\d+/")):
            t = link.get_text(strip=True)
            if t and re.search(r'\bvs?\.?\b', t, re.IGNORECASE) and 10 < len(t) < 200:
                cited.add(re.sub(r'\s+', ' ', t).strip())
    # Regex fallback
    if len(cited) < 3:
        for m in re.finditer(
            r'([A-Z][a-zA-Z\.\s&,]+?)\s+(?:vs?\.?|versus)\s+([A-Z][a-zA-Z\.\s&,]+?)(?:\s*\(|\s*on\s)',
            text[:20000]
        ):
            name = f"{m.group(1).strip()} vs {m.group(2).strip()}"
            if 10 < len(name) < 150:
                cited.add(re.sub(r'\s+', ' ', name))
    return list(cited)[:15]


def extract_statutes(text):
    """Extract statute references."""
    statutes = []
    seen = set()
    abbrevs = {
        "indian penal code": ("Indian Penal Code", "IPC"),
        "code of criminal procedure": ("Code of Criminal Procedure", "CrPC"),
        "code of civil procedure": ("Code of Civil Procedure", "CPC"),
        "constitution of india": ("Constitution of India", "Constitution"),
        "ndps act": ("NDPS Act", "NDPS"),
        "prevention of corruption": ("Prevention of Corruption Act", "PCA"),
        "hindu marriage act": ("Hindu Marriage Act", "HMA"),
        "negotiable instruments": ("Negotiable Instruments Act", "NI Act"),
        "information technology": ("Information Technology Act", "IT Act"),
        "arbitration": ("Arbitration and Conciliation Act", "ACA"),
        "pocso": ("POCSO Act", "POCSO"),
        "dowry prohibition": ("Dowry Prohibition Act", "DPA"),
        "transfer of property": ("Transfer of Property Act", "TPA"),
        "evidence act": ("Indian Evidence Act", "IEA"),
        "motor vehicles": ("Motor Vehicles Act", "MVA"),
        "consumer protection": ("Consumer Protection Act", "CPA"),
        "companies act": ("Companies Act", "CA"),
        "insolvency": ("Insolvency and Bankruptcy Code", "IBC"),
    }

    # Section X of Act
    for m in re.finditer(
        r'[Ss]ection\s+(\d+[A-Za-z]*(?:\(\d+\))?)\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s,]+?)(?:\s*[,\.]|\s+and\s|\s+read)',
        text[:30000]
    ):
        section, act = f"Section {m.group(1)}", m.group(2).strip().rstrip(',.')
        if 3 < len(act) < 80:
            act_l = act.lower()
            abbr = act
            for key, (full, short) in abbrevs.items():
                if key in act_l:
                    act, abbr = full, short
                    break
            if abbr == act:
                abbr = ''.join(w[0].upper() for w in act.split() if len(w) > 1)
            k = (section.lower(), act.lower())
            if k not in seen:
                seen.add(k)
                statutes.append((section, act, abbr))

    # Article X of Constitution
    for m in re.finditer(
        r'[Aa]rticle\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)\s+of\s+(?:the\s+)?Constitution',
        text[:30000]
    ):
        section = f"Article {m.group(1)}"
        k = (section.lower(), "constitution of india")
        if k not in seen:
            seen.add(k)
            statutes.append((section, "Constitution of India", "Constitution"))

    return statutes[:10]


def clean_judgment_text(text):
    """Clean up judgment text - remove cite counts, extra whitespace, etc."""
    # Remove [Cites X, Cited by Y] at the start
    text = re.sub(r'^\s*\[Cites\s*\n?\d+\s*\n?,\s*Cited by\s*\n?\d+\s*\n?\]\s*', '', text)
    # Remove excessive blank lines
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def scrape_case(session, doc_id, default_court="Supreme Court of India"):
    """Scrape a single case from Indian Kanoon."""
    resp = get_page(session, f"https://indiankanoon.org/doc/{doc_id}/")
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_tag = soup.find("title")
    if not title_tag:
        return None
    full_title = title_tag.get_text(strip=True)
    case_name = re.sub(r'\s+on\s+\d+.*$', '', full_title).strip()
    case_name = re.sub(r'\s*-\s*Indian Kanoon$', '', case_name).strip()
    if not case_name or len(case_name) < 5:
        return None

    # Date
    date_str, year = None, None
    dm = re.search(r'on\s+(\d+\s+\w+,?\s+\d{4})', full_title)
    if dm:
        date_str, year = parse_date(dm.group(1))
    if not year:
        ym = re.search(r'\b(19|20)\d{2}\b', full_title)
        year = int(ym.group()) if ym else 2000
        date_str = date_str or f"{year}-01-01"

    # Judgment text — try multiple sources
    judgment_text = ""

    # Source 1: <div class="judgments">
    jdiv = soup.find("div", class_="judgments")
    if jdiv:
        for tag in jdiv.find_all(["script", "style"]):
            tag.decompose()
        judgment_text = jdiv.get_text(separator="\n").strip()

    # Source 2: <pre> tag (older format)
    if not judgment_text or len(judgment_text) < 200:
        pre = soup.find("pre")
        if pre:
            pre_text = pre.get_text(separator="\n").strip()
            if len(pre_text) > len(judgment_text):
                judgment_text = pre_text

    if not judgment_text or len(judgment_text) < 100:
        return None

    judgment_text = clean_judgment_text(judgment_text)

    # Truncate if too long
    if len(judgment_text) > 15000:
        judgment_text = judgment_text[:15000] + "\n\n[... Judgment text truncated ...]"

    # Court
    court = extract_court(soup, judgment_text, default_court)

    # Judges
    judges = extract_judges(soup, judgment_text)

    # Case type, citations, statutes
    case_type = extract_case_type(case_name, judgment_text)
    cited_cases = extract_cited_cases(soup, judgment_text)
    cited_statutes = extract_statutes(judgment_text)
    case_id = hashlib.md5(f"{case_name}_{doc_id}".encode()).hexdigest()[:12]

    return {
        "case_id": case_id,
        "case_name": case_name,
        "year": year,
        "court": court,
        "case_type": case_type,
        "judges": judges,
        "judgment_text": judgment_text,
        "cited_cases_raw": cited_cases,
        "cited_statutes_raw": [list(s) for s in cited_statutes],
        "date": date_str,
        "source_url": f"https://indiankanoon.org/doc/{doc_id}/",
        "indian_kanoon_id": doc_id,
    }


def generate_dataset():
    """Scrape real legal judgments from Indian Kanoon."""
    print_banner("Day 1 -- Legal Data Collector (Real Data)")
    print(f"Target: {TARGET_CASES} real Indian legal judgments from Indian Kanoon\n")

    session = create_session()
    all_cases = []
    seen_doc_ids = set()
    seen_case_names = set()
    doc_queue = []

    # ── Phase 1: Collect document IDs ──────────────────────────────
    print("Phase 1: Searching for cases...\n")
    for idx, (query, court, pages) in enumerate(SEARCH_QUERIES):
        print(f"  [{idx+1}/{len(SEARCH_QUERIES)}] '{query}' in {court}...", end=" ", flush=True)
        results = search_cases(session, query, court, pages)
        new = 0
        for doc_id, title in results:
            if doc_id not in seen_doc_ids:
                seen_doc_ids.add(doc_id)
                doc_queue.append((doc_id, title, court))
                new += 1
        print(f"{len(results)} found, {new} new (total: {len(doc_queue)})")

        if len(doc_queue) >= TARGET_CASES * 2:
            print(f"\n  Enough candidates ({len(doc_queue)}). Moving on.\n")
            break

    print(f"\n  Total unique candidates: {len(doc_queue)}\n")

    # ── Phase 2: Scrape each case ──────────────────────────────────
    print("Phase 2: Scraping full case data...\n")
    errors = 0
    consecutive_errors = 0

    for idx, (doc_id, title, court_doctype) in enumerate(doc_queue):
        if len(all_cases) >= TARGET_CASES:
            break
        if consecutive_errors >= 15:
            print(f"\n  Too many consecutive errors. Stopping.\n")
            break

        default_court = COURT_MAP.get(court_doctype, "Supreme Court of India")
        short = title[:60] + "..." if len(title) > 60 else title
        print(f"  [{len(all_cases)+1}/{TARGET_CASES}] {short}", flush=True)

        try:
            case = scrape_case(session, doc_id, default_court)
            if case:
                norm = re.sub(r'\s+', ' ', case["case_name"].lower().strip())
                if norm in seen_case_names:
                    print(f"           -> duplicate, skip")
                    continue
                seen_case_names.add(norm)
                all_cases.append(case)
                consecutive_errors = 0
                print(f"           -> OK | {case['year']} | {len(case['judges'])} judges | "
                      f"{len(case['cited_cases_raw'])} cites | "
                      f"{len(case['cited_statutes_raw'])} statutes | "
                      f"{len(case['judgment_text'])} chars")
            else:
                errors += 1
                consecutive_errors += 1
                print(f"           -> could not parse")
        except Exception as e:
            errors += 1
            consecutive_errors += 1
            print(f"           -> error: {str(e)[:60]}")

    # ── Save ───────────────────────────────────────────────────────
    output_path = os.path.join(PROCESSED_DIR, "judgments.json")
    save_json(all_cases, output_path)
    save_json({
        "scraped_at": datetime.now().isoformat(),
        "total_cases": len(all_cases),
        "candidates": len(doc_queue),
        "errors": errors,
        "source": "indiankanoon.org",
    }, os.path.join(RAW_DIR, "scrape_metadata.json"))

    # ── Stats ──────────────────────────────────────────────────────
    courts_dist = {}
    year_dist = {}
    for c in all_cases:
        courts_dist[c["court"]] = courts_dist.get(c["court"], 0) + 1
        decade = (c["year"] // 10) * 10
        year_dist[f"{decade}s"] = year_dist.get(f"{decade}s", 0) + 1

    n = max(1, len(all_cases))
    print_stats({
        "Total scraped": len(all_cases),
        "Candidates": len(doc_queue),
        "Errors": errors,
        "Courts": len(courts_dist),
        "Avg citations": f"{sum(len(c['cited_cases_raw']) for c in all_cases)/n:.1f}",
        "Avg statutes": f"{sum(len(c['cited_statutes_raw']) for c in all_cases)/n:.1f}",
        "Avg text length": f"{sum(len(c['judgment_text']) for c in all_cases)/n:.0f} chars",
    })
    if courts_dist:
        print("Court Distribution:")
        for court, cnt in sorted(courts_dist.items(), key=lambda x: -x[1])[:10]:
            print(f"  {court}: {cnt}")
    if year_dist:
        print("\nDecade Distribution:")
        for decade, cnt in sorted(year_dist.items()):
            print(f"  {decade}: {cnt}")

    print(f"\n[OK] Dataset saved to: {output_path}")
    return all_cases


if __name__ == "__main__":
    generate_dataset()
