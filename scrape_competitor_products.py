"""
Scrape competitor websites for product, technology, and business intelligence.
Ingests findings into D1 via REST API.
"""
import json
import sys
import time
import urllib.request
import urllib.error
import tomllib
import os
import re
from datetime import datetime

ACCOUNT_ID = "b9af3a4bf161132bb7e5d3d365fb8bb0"
DB_ID = "4a2c1d02-c377-4e70-b8f8-aec879f77ebb"

# Competitors with known/discovered domains
COMPETITORS_WITH_DOMAINS = [
    (1, "Champion X", "championx.com", [
        "https://www.championx.com",
        "https://www.championx.com/products",
        "https://www.championx.com/about",
        "https://www.championx.com/investors",
    ]),
    (2, "Coastal Chemical", "coastalchemical.com", [
        "https://www.coastalchemical.com",
        "https://www.coastalchemical.com/products",
        "https://www.coastalchemical.com/services",
        "https://www.coastalchemical.com/about",
    ]),
    (3, "Imperative Chemical Partners", "imperativechem.com", [
        "https://www.imperativechem.com",
        "https://www.imperativechem.com/about",
        "https://www.imperativechem.com/services",
    ]),
    (17, "Sol Nexus", "solnexus.com", [
        "https://www.solnexus.com",
        "https://www.solnexus.com/about",
        "https://www.solnexus.com/services",
    ]),
    (18, "SoluGen", "solugen.com", [
        "https://www.solugen.com",
        "https://www.solugen.com/products",
        "https://www.solugen.com/technology",
        "https://www.solugen.com/about",
    ]),
]

# Additional companies to try discovering
DISCOVERY_TARGETS = [
    (5, "Corrosion Fluid Products", ["corrosionfluidproducts.com", "corrosionfluid.com", "cfpchemical.com"]),
    (6, "Credence Resources", ["credenceresources.com", "credencechem.com"]),
    (7, "Enduro Pipeline Services", ["enduropipeline.com", "enduroservices.com"]),
    (8, "Energy Flow Solutions", ["energyflowsolutions.com", "energyflow.com"]),
    (9, "Infinity Chemical", ["infinitychemical.com", "infinitychem.com"]),
    (10, "Integrity Chemical", ["integritychemical.com", "integritychem.com"]),
    (11, "Interface Performance Materials", ["interfacepm.com", "interfaceperformance.com"]),
    (12, "MaxFlow Chemical", ["maxflowchemical.com", "maxflowchem.com"]),
    (13, "OT Oilfield Services", ["otoilfieldservices.com", "otoilfield.com"]),
    (14, "Perfect Chemical", ["perfectchemical.com", "perfectchem.com"]),
    (15, "Revive Energy", ["reviveenergy.com", "revive-energy.com"]),
    (16, "SGB Solutions", ["sgbsolutions.com", "sgb-solutions.com"]),
    (19, "Specialty Drilling Fluids", ["specialtydrilling.com", "sdfluids.com", "specialtydrillingfluids.com"]),
    (20, "TruCam Solutions", ["trucamsolutions.com", "trucam.com"]),
    (21, "Aquarius Water Conditioning", ["aquariuswc.com", "aquariuswater.com", "aquariuswaterconditioning.com"]),
    (22, "Basin Chemical Solutions", ["basinchemical.com", "basinchem.com"]),
    (23, "JCAN Oilfield Services", ["jcanoilfield.com", "jcan.com", "jcanoilfieldservices.com"]),
    (24, "Suncoast Chemical", ["suncoastchemical.com", "suncoastchem.com"]),
]


def get_oauth_token() -> str:
    config_path = os.path.join(os.environ.get("APPDATA", ""), "xdg.config", ".wrangler", "config", "default.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    return config["oauth_token"]


def execute_d1_query(token: str, sql: str) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DB_ID}/query"
    data = json.dumps({"sql": sql}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "errors": [{"message": f"HTTP {e.code}: {body[:300]}"}]}
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def escape_sql(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("'", "''").replace("\\", "\\\\")


def fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch a web page and return text content"""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    req.add_header("Accept", "text/html,application/xhtml+xml")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            # Basic HTML to text
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
    except Exception as e:
        return ""


def check_domain(domain: str) -> bool:
    """Check if a domain responds"""
    try:
        req = urllib.request.Request(f"https://{domain}", method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status < 400
    except:
        try:
            req = urllib.request.Request(f"http://{domain}", method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.status < 400
        except:
            return False


def extract_products(text: str) -> list:
    """Extract product names and categories from page text"""
    products = []
    # Look for common product patterns
    patterns = [
        r'(?:product|chemical|treatment|solution|fluid|additive|inhibitor|biocide|surfactant|demulsifier|scale\s*inhibitor|corrosion\s*inhibitor|h2s\s*scavenger|paraffin|asphaltene|pour\s*point|friction\s*reducer|breaker|crosslinker|gelling\s*agent|clay\s*stabilizer|iron\s*control|oxygen\s*scavenger)\s*[:\-–]\s*([^\n.]{5,100})',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        products.extend(matches)

    # Also look for capitalized product names near chemical keywords
    chemical_context = re.findall(r'(?:our|the|new|advanced|premium|proprietary)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\s+(?:product|system|technology|solution|program|service)', text)
    products.extend(chemical_context)

    return list(set(products))[:30]


def extract_technologies(text: str) -> list:
    """Extract technology and capability mentions"""
    techs = []
    tech_keywords = [
        "chembiotic", "bioengineered", "green chemistry", "enzyme", "catalytic",
        "nanotechnology", "nano", "microemulsion", "polymer", "copolymer",
        "digital", "AI", "machine learning", "IoT", "SCADA", "automation",
        "real-time monitoring", "predictive", "analytics", "cloud-based",
        "patented", "proprietary", "patent-pending", "trademarked",
    ]
    for kw in tech_keywords:
        if kw.lower() in text.lower():
            # Get surrounding context
            idx = text.lower().find(kw.lower())
            start = max(0, idx - 50)
            end = min(len(text), idx + len(kw) + 100)
            context = text[start:end].strip()
            techs.append((kw, context))

    return techs[:20]


def extract_business_intel(text: str) -> list:
    """Extract business intelligence (locations, employees, revenue, etc.)"""
    intel = []

    # Locations
    locations = re.findall(r'(?:headquartered|located|office|facility|plant|warehouse)\s+(?:in|at)\s+([^.]{5,80})', text, re.IGNORECASE)
    for loc in locations:
        intel.append(("location", loc.strip()))

    # Employee counts
    employees = re.findall(r'(\d{1,6}(?:,\d{3})*)\s*(?:\+\s*)?(?:employees|team members|associates|professionals|people)', text, re.IGNORECASE)
    for emp in employees:
        intel.append(("employee_count", emp))

    # Revenue / financial
    revenue = re.findall(r'\$\s*(\d+(?:\.\d+)?)\s*(?:billion|million|B|M)\s*(?:in\s+)?(?:revenue|sales|annual)', text, re.IGNORECASE)
    for rev in revenue:
        intel.append(("revenue", rev))

    # Founded year
    founded = re.findall(r'(?:founded|established|since|est\.?)\s*(?:in\s+)?(\d{4})', text, re.IGNORECASE)
    for yr in founded:
        intel.append(("founded_year", yr))

    # Partnerships / Clients
    partners = re.findall(r'(?:partner(?:ship)?|client|customer|work(?:ing)?\s+with)\s+(?:with\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})', text)
    for p in partners[:5]:
        intel.append(("partnership", p))

    # Certifications
    certs = re.findall(r'(ISO\s*\d+|API\s*\w+|NSF|EPA\s*registered|OSHA|HAZMAT|DOT)', text, re.IGNORECASE)
    for c in certs:
        intel.append(("certification", c.strip()))

    return intel[:25]


def ingest_osint(token: str, comp_id: int, comp_name: str, domain: str,
                 finding_type: str, finding_value: str, severity: str,
                 details: str, source_tool: str, scan_type: str) -> bool:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    sql = f"""INSERT OR IGNORE INTO competitor_osint
        (competitor_id, competitor_name, finding_type, finding_value, severity,
         details, source_tool, scan_type, domain, scanned_at)
        VALUES (
            {comp_id},
            '{escape_sql(comp_name)}',
            '{escape_sql(finding_type)}',
            '{escape_sql(finding_value[:500])}',
            '{escape_sql(severity)}',
            '{escape_sql(details[:500])}',
            '{escape_sql(source_tool)}',
            '{escape_sql(scan_type)}',
            '{escape_sql(domain)}',
            '{now}'
        )"""
    result = execute_d1_query(token, sql)
    return result.get("success", False)


def ingest_product(token: str, comp_id: int, product_name: str, category: str, description: str) -> bool:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    sql = f"""INSERT OR IGNORE INTO products
        (competitor_id, product_name, category, description, source, discovered_at)
        VALUES (
            {comp_id},
            '{escape_sql(product_name[:200])}',
            '{escape_sql(category[:100])}',
            '{escape_sql(description[:500])}',
            'web_scrape',
            '{now}'
        )"""
    result = execute_d1_query(token, sql)
    return result.get("success", False)


def ingest_market_intel(token: str, comp_id: int, intel_type: str, title: str, content: str, source: str) -> bool:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    sql = f"""INSERT OR IGNORE INTO market_intel
        (competitor_id, intel_type, title, content, source, reliability, discovered_at)
        VALUES (
            {comp_id},
            '{escape_sql(intel_type[:50])}',
            '{escape_sql(title[:200])}',
            '{escape_sql(content[:1000])}',
            '{escape_sql(source[:200])}',
            'medium',
            '{now}'
        )"""
    result = execute_d1_query(token, sql)
    return result.get("success", False)


def main():
    token = get_oauth_token()

    # Verify D1
    test = execute_d1_query(token, "SELECT COUNT(*) as n FROM competitor_osint")
    if not test.get("success"):
        print(f"D1 failed: {test}")
        sys.exit(1)
    print(f"D1 connected. OSINT: {test['result'][0]['results'][0]['n']} records")

    # Phase 1: Domain Discovery
    print("\n=== PHASE 1: DOMAIN DISCOVERY ===")
    discovered = []
    for comp_id, comp_name, domain_guesses in DISCOVERY_TARGETS:
        print(f"  [{comp_name}] trying {len(domain_guesses)} domains...", end=" ", flush=True)
        found = None
        for domain in domain_guesses:
            if check_domain(domain):
                found = domain
                break
        if found:
            print(f"FOUND: {found}")
            discovered.append((comp_id, comp_name, found))
            # Store domain discovery as OSINT
            ingest_osint(token, comp_id, comp_name, found,
                        "domain_verified", found, "info",
                        f"Domain {found} verified as belonging to {comp_name}",
                        "web_discovery", "domain_discovery")
        else:
            print("none responding")

    # Combine all known + discovered
    all_targets = COMPETITORS_WITH_DOMAINS + [(cid, cn, d, [f"https://www.{d}", f"https://{d}"]) for cid, cn, d in discovered]

    # Phase 2: Web Scraping
    print(f"\n=== PHASE 2: WEB SCRAPING ({len(all_targets)} competitors) ===")
    total_products = 0
    total_intel = 0
    total_osint = 0

    for comp_id, comp_name, domain, urls in all_targets:
        print(f"\n--- {comp_name} ({domain}) ---")

        all_text = ""
        for url in urls:
            print(f"  Fetching {url}...", end=" ", flush=True)
            text = fetch_page(url)
            if text:
                print(f"{len(text)} chars")
                all_text += " " + text
            else:
                print("failed/empty")
            time.sleep(0.5)

        if not all_text:
            print(f"  No content retrieved for {comp_name}")
            continue

        # Extract products
        products = extract_products(all_text)
        for p in products:
            if ingest_product(token, comp_id, p, "oilfield_chemical", f"Product/service: {p}"):
                total_products += 1
        print(f"  Products extracted: {len(products)}")

        # Extract technologies
        techs = extract_technologies(all_text)
        for kw, context in techs:
            if ingest_osint(token, comp_id, comp_name, domain,
                          "technology", kw, "info",
                          context, "web_scrape", "tech_fingerprint"):
                total_osint += 1
        print(f"  Technologies: {len(techs)}")

        # Extract business intel
        intel = extract_business_intel(all_text)
        for itype, value in intel:
            if ingest_market_intel(token, comp_id, itype, f"{comp_name} {itype}",
                                  value, f"https://{domain}"):
                total_intel += 1
            if ingest_osint(token, comp_id, comp_name, domain,
                          f"business_{itype}", value, "info",
                          f"Business intelligence: {itype}", "web_scrape", "business_intel"):
                total_osint += 1
        print(f"  Business intel: {len(intel)}")

        # Page titles and descriptions as general intel
        title_match = re.search(r'<title>([^<]+)</title>', all_text, re.IGNORECASE)
        if title_match:
            ingest_osint(token, comp_id, comp_name, domain,
                        "web_title", title_match.group(1), "info",
                        "Website title tag", "web_scrape", "web_fingerprint")

        time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"WEB SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Products ingested: {total_products}")
    print(f"Market intel ingested: {total_intel}")
    print(f"OSINT findings ingested: {total_osint}")

    # Final counts
    for table in ["competitor_osint", "products", "market_intel"]:
        r = execute_d1_query(token, f"SELECT COUNT(*) as n FROM {table}")
        if r.get("success"):
            print(f"{table}: {r['result'][0]['results'][0]['n']} total records")


if __name__ == "__main__":
    main()
