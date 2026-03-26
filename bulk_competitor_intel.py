"""Bulk competitor intelligence ingestion via Tor on Charlie + D1 REST API.
Scrapes competitor websites through Tor, extracts products/tech/business intel,
ingests into D1 tables: competitor_osint, products, market_intel.
"""
import json
import subprocess
import sys
import time
import re
import urllib.request
import urllib.error

ACCOUNT_ID = "b9af3a4bf161132bb7e5d3d365fb8bb0"
DB_ID = "4a2c1d02-c377-4e70-b8f8-aec879f77ebb"

# All 23 competitors with known/discovered domains and product page URLs
COMPETITORS = [
    (1, "Champion X", "championx.com", [
        "https://www.championx.com",
        "https://www.championx.com/products-and-solutions/chemical-technologies/",
        "https://www.championx.com/products-and-solutions/artificial-lift-technologies/",
        "https://www.championx.com/company/about-us/",
        "https://www.championx.com/company/investors/",
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
        "https://www.imperativechem.com/products",
    ]),
    (5, "Corrosion Fluid Products", "corrosionfluid.com", [
        "https://www.corrosionfluid.com",
        "https://corrosionfluid.com",
    ]),
    (6, "Credence Resources", "credencechem.com", [
        "https://www.credencechem.com",
        "https://credencechem.com",
    ]),
    (7, "Enduro Pipeline Services", None, []),
    (8, "Energy Flow Solutions", "energyflow.com", [
        "https://www.energyflow.com",
        "https://energyflow.com",
    ]),
    (9, "Infinity Chemical", None, []),
    (10, "Integrity Chemical", "integritychemical.com", [
        "https://www.integritychemical.com",
        "https://integritychemical.com",
    ]),
    (11, "Interface Performance Materials", None, []),
    (12, "MaxFlow Chemical", None, []),
    (13, "OT Oilfield Services", None, []),
    (14, "Perfect Chemical", "perfectchem.com", [
        "https://www.perfectchem.com",
        "https://perfectchem.com",
    ]),
    (15, "Revive Energy", "reviveenergy.com", [
        "https://www.reviveenergy.com",
        "https://reviveenergy.com",
    ]),
    (16, "SGB Solutions", "sgb-solutions.com", [
        "https://www.sgb-solutions.com",
        "https://sgb-solutions.com",
    ]),
    (17, "Sol Nexus", "solnexus.com", [
        "https://www.solnexus.com",
        "https://solnexus.com",
    ]),
    (18, "SoluGen", "solugen.com", [
        "https://www.solugen.com",
        "https://www.solugen.com/technology",
        "https://www.solugen.com/about",
        "https://www.solugen.com/products",
    ]),
    (19, "Specialty Drilling Fluids", None, []),
    (20, "TruCam Solutions", None, []),
    (21, "Aquarius Water Conditioning", "aquariuswaterconditioning.com", [
        "https://www.aquariuswaterconditioning.com",
        "https://aquariuswaterconditioning.com",
    ]),
    (22, "Basin Chemical Solutions", None, []),
    (23, "JCAN Oilfield Services", "jcan.com", [
        "https://www.jcan.com",
        "https://jcan.com",
    ]),
    (24, "Suncoast Chemical", None, []),
]

# ChampionX known intel (pre-extracted from ShadowGlass scrape)
CHAMPIONX_INTEL = {
    "products": [
        "Production Chemicals", "Asset Integrity Chemicals", "Flow Assurance Chemicals",
        "Production Maximization Chemicals", "Surflo Chemical Qualification",
        "Corrosion Inhibitors", "Scale Inhibitors", "Demulsifiers", "Biocides",
        "H2S Scavengers", "Paraffin Control", "Asphaltene Control", "Wax Control",
        "Oxygen Scavengers", "Iron Control Chemicals", "Hydrate Inhibitors",
        "Emulsion Breakers", "Friction Reducers", "Pour Point Depressants",
        "Drag Reducers", "Foam Control", "Water Treatment Chemicals",
        "Chemical Injection Pumps", "Chemical Injection Skids",
        "Capillary Injection Systems", "Batch Treatment Systems",
        "Multipoint Injection Systems",
    ],
    "artificial_lift": [
        "Electrical Submersible Pumping (ESP) Systems", "ESP Motors", "ESP Pumps",
        "ESP Gas Handlers", "ESP Protectors", "ESP Sensors", "ESP Cables",
        "Rod Lift Systems", "Specialty Rod Pumps", "Subsurface Rod Pump Components",
        "Sucker Rods (Norris Rods)", "Rod Pump Design & Optimization Software",
        "Progressing Cavity Pumping Systems", "Gas Lift Mandrels", "Gas Lift Valves",
        "Gas Lift Packers", "Gas Lift Downhole Sensors", "Gas Injection Optimization",
        "Plunger Lift Systems", "Plunger Lift Surface Equipment",
    ],
    "digital": [
        "XSPOC Production Optimization Software", "LOOKOUT Optimization Services",
        "Theta Consulting and Automation", "Platinum 2 Online Monitoring",
        "AutoBalance™ System", "Pump Checker Optimization Software",
        "ALLY Production Optimization", "SMARTEN Rod Lift Automation",
        "DigiUltra Controls",
    ],
    "emissions": [
        "SOOFIE Continuous Emissions Monitoring", "AURA OGI Camera (Optical Gas Imaging)",
        "Leak Detection and Repair (LDAR) Surveys", "Drone Surveys", "Aerial Surveys",
        "Emissions Software & Analytics",
    ],
    "brands": [
        "ChampionX", "Norris Rods", "Norriseal-Wellmark", "PCS Ferguson",
        "Wellmark", "Quartzdyne", "Harbison-Fischer", "Oil Lift Technology",
        "Theta", "UNBRIDLED ESP", "Windrock",
    ],
    "business": {
        "ticker": "NYSE: CHX",
        "type": "Public Company",
        "hq": "The Woodlands, Texas",
        "employees": "7,000+",
        "revenue": "$3.6B+ (2024)",
        "founded": "2020 (merger of Apergy + Ecolab ChampionX)",
        "markets": "Global - 60+ countries",
        "sectors": "Production Chemicals, Artificial Lift, Digital, Emissions",
    },
}

# SoluGen known intel (from web scrape)
SOLUGEN_INTEL = {
    "products": [
        "Bio-based Chemicals", "Green Chemistry Platform", "Chelating Agents",
        "Descalers", "Water Treatment Chemicals", "Scale Inhibitors",
        "Iron Control Agents", "Hydrogen Peroxide Alternatives",
        "Biodegradable Chemical Solutions", "Oil & Gas Production Chemicals",
    ],
    "technology": [
        "Chemoenzymatic Synthesis Platform", "Bio-based Manufacturing",
        "Carbon-negative Chemical Production", "Enzyme Engineering",
        "Sustainable Chemistry", "Green Chemistry Processes",
    ],
    "business": {
        "type": "Private Startup (VC-backed)",
        "hq": "Houston, Texas",
        "founded": "2016",
        "funding": "$500M+ raised",
        "investors": "Baillie Gifford, BlackRock, GIC, Temasek, Lowercarbon Capital",
        "revenue": "Pre-revenue / Early revenue stage",
        "differentiator": "Bio-based chemicals from plants, not petroleum",
    },
}


def get_oauth_token() -> str:
    import tomllib
    import os
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
    if not s:
        return ""
    return s.replace("'", "''").replace("\n", " ").replace("\r", "")[:500]


def fetch_via_tor(url: str, timeout: int = 15) -> str:
    """Fetch URL through Tor on Charlie node."""
    cmd = [
        "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
        "echoprime@192.168.1.202",
        f"curl -s --socks5 127.0.0.1:9050 --max-time {timeout} -L '{url}'"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        html = result.stdout.strip()
        if html and len(html) > 100:
            return html
    except Exception as e:
        print(f"    Tor fetch error: {e}")
    return ""


def extract_text_from_html(html: str) -> str:
    """Strip HTML tags, scripts, styles."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_products(text: str, html: str) -> list[str]:
    """Extract chemical product names from page content."""
    products = set()
    product_patterns = [
        r'corrosion\s+inhibitor\w*', r'scale\s+inhibitor\w*', r'demulsifier\w*',
        r'biocide\w*', r'surfactant\w*', r'h2s\s+scavenger\w*', r'friction\s+reducer\w*',
        r'defoamer\w*', r'oxygen\s+scavenger\w*', r'emulsion\s+breaker\w*',
        r'paraffin\s+(?:inhibitor|control|solvent)\w*', r'wax\s+(?:inhibitor|control)\w*',
        r'asphaltene\s+(?:inhibitor|dispersant|control)\w*',
        r'iron\s+control\w*', r'pour\s+point\s+depressant\w*',
        r'drag\s+reducer\w*', r'clay\s+stabilizer\w*', r'hydrate\s+inhibitor\w*',
        r'foam\s+(?:control|inhibitor)\w*', r'water\s+treatment\w*',
        r'production\s+chemical\w*', r'drilling\s+fluid\w*', r'completion\s+fluid\w*',
        r'frac\s+(?:fluid|chemical)\w*', r'crosslinker\w*', r'breaker\w*',
        r'acid(?:izing)?\s+(?:treatment|system|service)\w*',
        r'scale\s+squeeze\w*', r'chemical\s+injection\w*',
        r'reverse\s+emulsion\w*', r'oil\s+soluble\s+\w+',
        r'water\s+soluble\s+\w+', r'micro\s*emulsion\w*',
        r'descal(?:er|ant|ing)\w*', r'chelat(?:ing|e)\s+agent\w*',
        r'bactericid\w*', r'fungicid\w*', r'algaecid\w*',
        r'flow\s+(?:improver|assurance)\w*',
    ]
    tl = text.lower()
    for pat in product_patterns:
        for m in re.finditer(pat, tl):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].strip()
            product_name = m.group(0).strip().title()
            products.add(product_name)

    # Also extract from title tags and h1-h6
    for tag_match in re.finditer(r'<(?:title|h[1-6])[^>]*>(.*?)</(?:title|h[1-6])>', html, re.I | re.DOTALL):
        tag_text = re.sub(r'<[^>]+>', '', tag_match.group(1)).strip()
        if any(kw in tag_text.lower() for kw in ['chemical', 'product', 'service', 'solution', 'treatment']):
            if 5 < len(tag_text) < 150:
                products.add(tag_text)

    return list(products)


def extract_technologies(text: str) -> list[str]:
    """Extract technology/innovation mentions."""
    techs = set()
    tech_patterns = [
        r'patented\s+\w+[\w\s]{0,40}',
        r'proprietary\s+\w+[\w\s]{0,40}',
        r'nanotechnolog\w*[\w\s]{0,30}',
        r'(?:ai|artificial\s+intelligence)[\-\s]+(?:powered|driven|based)[\w\s]{0,30}',
        r'machine\s+learning[\w\s]{0,30}',
        r'real[\-\s]time\s+(?:monitoring|optimization|analysis)[\w\s]{0,30}',
        r'automation\s+(?:system|solution|platform)[\w\s]{0,30}',
        r'iot[\-\s]+(?:enabled|sensor|device|platform)[\w\s]{0,30}',
        r'green\s+chemistry[\w\s]{0,30}',
        r'sustainable[\w\s]{0,40}',
        r'biodegradable[\w\s]{0,30}',
        r'digital\s+(?:twin|platform|solution|ecosystem)[\w\s]{0,30}',
        r'bio[\-\s]?based[\w\s]{0,30}',
        r'enzyme[\-\s]?\w+[\w\s]{0,30}',
        r'(?:chemoenzymatic|catalytic|electrochemical)[\w\s]{0,30}',
        r'carbon[\-\s]?(?:negative|neutral|zero|capture)[\w\s]{0,30}',
    ]
    tl = text.lower()
    for pat in tech_patterns:
        for m in re.finditer(pat, tl):
            tech = m.group(0).strip()
            if len(tech) > 8:
                techs.add(tech.title()[:150])
    return list(techs)


def extract_business_intel(text: str) -> dict:
    """Extract business information."""
    intel = {}
    tl = text.lower()

    # Location
    loc_match = re.search(r'(?:headquarter|based in|located in|office in)\s*:?\s*([^.]{5,80})', tl)
    if loc_match:
        intel["hq"] = loc_match.group(1).strip().title()

    # Employees
    emp_match = re.search(r'(\d[\d,]+)\s*(?:\+?\s*)employee', tl)
    if emp_match:
        intel["employees"] = emp_match.group(1).replace(",", "")

    # Revenue / Financial
    rev_match = re.search(r'\$\s*(\d[\d,.]+)\s*(billion|million|B|M)', tl)
    if rev_match:
        intel["revenue"] = f"${rev_match.group(1)} {rev_match.group(2)}"

    # Founded year
    founded_match = re.search(r'(?:founded|established|since|est\.?)\s*(?:in\s*)?(\d{4})', tl)
    if founded_match:
        intel["founded"] = founded_match.group(1)

    # Stock ticker
    ticker_match = re.search(r'(NYSE|NASDAQ|OTC)\s*:\s*([A-Z]{1,5})', text)
    if ticker_match:
        intel["ticker"] = f"{ticker_match.group(1)}: {ticker_match.group(2)}"

    # Certifications
    certs = []
    for cert in re.finditer(r'(ISO\s*\d+|API\s*\d+[A-Z]*|OSHA|EPA|NSF|UL\s+\d+)', text, re.I):
        certs.append(cert.group(1).upper())
    if certs:
        intel["certifications"] = ", ".join(set(certs))

    # Partnerships
    partners = re.findall(r'partner(?:ship|ed|ing)?\s+with\s+([^.]{5,60})', tl)
    if partners:
        intel["partnerships"] = "; ".join(p.strip().title() for p in partners[:5])

    return intel


def ingest_batch(token: str, statements: list[str]) -> tuple[int, int]:
    """Execute batch of SQL statements."""
    ok = 0
    fail = 0
    for stmt in statements:
        result = execute_d1_query(token, stmt)
        if result.get("success"):
            ok += 1
        else:
            fail += 1
            errors = result.get("errors", [])
            msg = errors[0].get("message", "unknown") if errors else "unknown"
            if "UNIQUE" not in msg:
                print(f"    D1 error: {msg[:100]}")
    return ok, fail


def main():
    token = get_oauth_token()

    # Verify D1 connection
    test = execute_d1_query(token, "SELECT COUNT(*) as n FROM competitor_osint")
    if not test.get("success"):
        print(f"D1 connection failed: {test}")
        sys.exit(1)
    current = test['result'][0]['results'][0]['n']
    print(f"D1 connected. Current OSINT records: {current}")

    all_statements = []
    total_products = 0
    total_findings = 0
    total_market = 0

    # ===== PHASE 1: Pre-extracted ChampionX intelligence =====
    print("\n=== PHASE 1: ChampionX Pre-Extracted Intel ===")
    cx = CHAMPIONX_INTEL
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Products
    for cat_name, items in [("products", cx["products"]), ("artificial_lift", cx["artificial_lift"]),
                            ("digital", cx["digital"]), ("emissions", cx["emissions"])]:
        for item in items:
            sql = f"INSERT OR IGNORE INTO products (competitor_id, product_name, category, description) VALUES (1, '{escape_sql(item)}', '{cat_name}', 'ChampionX {cat_name} product line')"
            all_statements.append(sql)
            total_products += 1

    # Brands as OSINT findings
    for brand in cx["brands"]:
        sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES (1, 'Champion X', 'championx.com', 'web_scrape', 'brand', '{escape_sql(brand)}', 'shadowglass', 'ChampionX subsidiary brand', 'info', '{now}')"
        all_statements.append(sql)
        total_findings += 1

    # Business intel
    biz = cx["business"]
    for key, val in biz.items():
        sql = f"INSERT INTO market_intel (competitor_id, intel_type, content, source, confidence) VALUES (1, '{escape_sql(key)}', '{escape_sql(val)}', 'championx.com investor page', 'high')"
        all_statements.append(sql)
        total_market += 1
        sql2 = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES (1, 'Champion X', 'championx.com', 'web_scrape', 'business_intel', '{escape_sql(key)}: {escape_sql(val)}', 'shadowglass', 'Business intelligence from public sources', 'info', '{now}')"
        all_statements.append(sql2)
        total_findings += 1

    # ===== PHASE 1B: SoluGen Pre-Extracted Intel =====
    print("=== PHASE 1B: SoluGen Pre-Extracted Intel ===")
    sg = SOLUGEN_INTEL
    for item in sg["products"]:
        sql = f"INSERT OR IGNORE INTO products (competitor_id, product_name, category, description) VALUES (18, '{escape_sql(item)}', 'chemicals', 'SoluGen bio-based chemical product')"
        all_statements.append(sql)
        total_products += 1

    for tech in sg["technology"]:
        sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES (18, 'SoluGen', 'solugen.com', 'web_scrape', 'technology', '{escape_sql(tech)}', 'tor_curl', 'Technology extracted from website', 'info', '{now}')"
        all_statements.append(sql)
        total_findings += 1

    for key, val in sg["business"].items():
        sql = f"INSERT INTO market_intel (competitor_id, intel_type, content, source, confidence) VALUES (18, '{escape_sql(key)}', '{escape_sql(val)}', 'solugen.com public info', 'medium')"
        all_statements.append(sql)
        total_market += 1

    # ===== PHASE 2: Live scraping through Tor =====
    print("\n=== PHASE 2: Live Web Scraping via Tor ===")

    for comp_id, name, domain, urls in COMPETITORS:
        if comp_id in (1, 18):  # Already handled above
            continue
        if not urls:
            print(f"  [{name}] No URLs to scrape")
            continue

        print(f"  [{name}] ({domain}) scraping {len(urls)} URLs...")
        combined_text = ""
        combined_html = ""

        for url in urls:
            html = fetch_via_tor(url)
            if html:
                combined_html += html + "\n"
                text = extract_text_from_html(html)
                combined_text += text + " "
                print(f"    {url} -> {len(text)} chars")
            else:
                print(f"    {url} -> empty")
            time.sleep(0.5)  # Rate limit

        if not combined_text.strip():
            print(f"    No content for {name}")
            # Still record we tried
            sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain or 'unknown')}', 'web_scrape', 'scrape_attempt', 'No content retrieved - site may block automated access', 'tor_curl', 'Attempted via Tor proxy', 'info', '{now}')"
            all_statements.append(sql)
            total_findings += 1
            continue

        # Extract products
        products = extract_products(combined_text, combined_html)
        for prod in products:
            sql = f"INSERT OR IGNORE INTO products (competitor_id, product_name, category, description) VALUES ({comp_id}, '{escape_sql(prod)}', 'extracted', '{escape_sql(name)} product extracted from website')"
            all_statements.append(sql)
            total_products += 1
            sql2 = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain)}', 'web_scrape', 'product', '{escape_sql(prod)}', 'tor_curl', 'Product extracted from website', 'info', '{now}')"
            all_statements.append(sql2)
            total_findings += 1
        print(f"    Products: {len(products)}")

        # Extract technologies
        techs = extract_technologies(combined_text)
        for tech in techs:
            sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain)}', 'web_scrape', 'technology', '{escape_sql(tech)}', 'tor_curl', 'Technology mention from website', 'info', '{now}')"
            all_statements.append(sql)
            total_findings += 1
        print(f"    Technologies: {len(techs)}")

        # Extract business intel
        biz = extract_business_intel(combined_text)
        for key, val in biz.items():
            sql = f"INSERT INTO market_intel (competitor_id, intel_type, content, source, confidence) VALUES ({comp_id}, '{escape_sql(key)}', '{escape_sql(val)}', '{escape_sql(domain)}', 'medium')"
            all_statements.append(sql)
            total_market += 1
            sql2 = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain)}', 'web_scrape', 'business_intel', '{escape_sql(key)}: {escape_sql(val)}', 'tor_curl', 'Business intel from website', 'info', '{now}')"
            all_statements.append(sql2)
            total_findings += 1
        print(f"    Business intel: {len(biz)}")

        # Extract page title and meta description as general intel
        title_match = re.search(r'<title[^>]*>(.*?)</title>', combined_html, re.I | re.DOTALL)
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()[:200]
            if title:
                sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain)}', 'web_scrape', 'page_title', '{escape_sql(title)}', 'tor_curl', 'Website title tag', 'info', '{now}')"
                all_statements.append(sql)
                total_findings += 1

        meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', combined_html, re.I)
        if meta_match:
            desc = meta_match.group(1).strip()[:300]
            if desc:
                sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(domain)}', 'web_scrape', 'meta_description', '{escape_sql(desc)}', 'tor_curl', 'Website meta description', 'info', '{now}')"
                all_statements.append(sql)
                total_findings += 1

    # ===== PHASE 3: Additional known competitor intel (manual research) =====
    print("\n=== PHASE 3: Manual Research Intel ===")

    manual_intel = [
        # Coastal Chemical
        (2, "Coastal Chemical", "coastalchemical.com", [
            ("product", "Production Chemicals"),
            ("product", "Completion Chemicals"),
            ("product", "Stimulation Chemicals"),
            ("product", "Drilling Fluid Additives"),
            ("product", "Water Treatment Chemicals"),
            ("product", "Corrosion Inhibitors"),
            ("product", "Scale Inhibitors"),
            ("product", "H2S Scavengers"),
            ("product", "Biocides"),
            ("product", "Demulsifiers"),
            ("business_intel", "hq: Abbeville, Louisiana"),
            ("business_intel", "type: Private Regional Supplier"),
            ("business_intel", "markets: Gulf Coast, Permian Basin"),
            ("business_intel", "specialty: Custom chemical blending"),
        ]),
        # Imperative Chemical Partners
        (3, "Imperative Chemical Partners", "imperativechem.com", [
            ("product", "Production Chemicals"),
            ("product", "Midstream Chemicals"),
            ("product", "Water Treatment"),
            ("product", "Corrosion Management"),
            ("product", "Scale Management"),
            ("product", "Flow Assurance"),
            ("business_intel", "hq: Midland, Texas"),
            ("business_intel", "type: Private - Permian Basin focused"),
            ("business_intel", "specialty: Permian Basin production optimization"),
            ("business_intel", "focus: Delaware & Midland Basin operations"),
        ]),
        # Corrosion Fluid Products
        (5, "Corrosion Fluid Products", "corrosionfluid.com", [
            ("product", "Corrosion Inhibitors"),
            ("product", "Scale Inhibitors"),
            ("product", "Specialty Chemicals"),
            ("business_intel", "type: Specialty Chemical Manufacturer"),
            ("business_intel", "specialty: Corrosion prevention for O&G"),
        ]),
        # Enduro Pipeline Services
        (7, "Enduro Pipeline Services", None, [
            ("product", "Pipeline Chemical Treatments"),
            ("product", "Corrosion Management"),
            ("product", "Pipeline Integrity Services"),
            ("business_intel", "type: Pipeline Services Company"),
            ("business_intel", "markets: Permian Basin"),
        ]),
        # Integrity Chemical
        (10, "Integrity Chemical", "integritychemical.com", [
            ("product", "Oilfield Production Chemicals"),
            ("product", "Water Treatment"),
            ("product", "Corrosion Inhibitors"),
            ("product", "Scale Inhibitors"),
            ("product", "H2S Scavengers"),
            ("business_intel", "type: Regional Oilfield Chemical Supplier"),
            ("business_intel", "markets: Permian Basin, Eagle Ford"),
        ]),
        # Specialty Drilling Fluids
        (19, "Specialty Drilling Fluids", None, [
            ("product", "Oil-Based Drilling Fluids"),
            ("product", "Water-Based Drilling Fluids"),
            ("product", "Synthetic-Based Drilling Fluids"),
            ("product", "Drilling Fluid Additives"),
            ("product", "Barite"),
            ("product", "Bentonite"),
            ("product", "Lost Circulation Materials"),
            ("business_intel", "type: Drilling Fluids Specialist"),
            ("business_intel", "specialty: Custom drilling fluid systems"),
        ]),
    ]

    for comp_id, name, domain, findings in manual_intel:
        for ftype, fval in findings:
            d = domain or "unknown"
            sql = f"INSERT INTO competitor_osint (competitor_id, competitor_name, domain, scan_type, finding_type, finding_value, source_tool, details, severity, scanned_at) VALUES ({comp_id}, '{escape_sql(name)}', '{escape_sql(d)}', 'manual_research', '{escape_sql(ftype)}', '{escape_sql(fval)}', 'osint_research', 'Manual competitive intelligence research', 'info', '{now}')"
            all_statements.append(sql)
            total_findings += 1

            if ftype == "product":
                sql2 = f"INSERT OR IGNORE INTO products (competitor_id, product_name, category, description) VALUES ({comp_id}, '{escape_sql(fval)}', 'oilfield_chemicals', '{escape_sql(name)} product line')"
                all_statements.append(sql2)
                total_products += 1

    # ===== PHASE 4: Ingest all to D1 =====
    print(f"\n=== PHASE 4: D1 Ingestion ===")
    print(f"  Total statements: {len(all_statements)}")
    print(f"  Products: {total_products}")
    print(f"  OSINT findings: {total_findings}")
    print(f"  Market intel: {total_market}")

    ok, fail = ingest_batch(token, all_statements)
    print(f"\n  Ingested: {ok}/{len(all_statements)} OK, {fail} failed")

    # Verify final counts
    for table in ["competitor_osint", "products", "market_intel"]:
        r = execute_d1_query(token, f"SELECT COUNT(*) as n FROM {table}")
        if r.get("success") and r.get("result"):
            n = r["result"][0]["results"][0]["n"]
            print(f"  {table:30s} {n} rows")

    print("\n=== COMPLETE ===")


if __name__ == "__main__":
    main()
