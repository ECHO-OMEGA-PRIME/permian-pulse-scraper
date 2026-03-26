"""
S2 INTELLIGENCE INGESTION — 96B BRAVO STYLE
Loads all gathered competitive intelligence into D1 database.
Sources: 8 parallel intelligence agents + Prometheus OSINT scans
"""
import subprocess
import json
import time

DB = "permian-pulse-scraper"
WRANGLER = "npx wrangler d1 execute"
BASE_CMD = f"{WRANGLER} {DB} --remote --command"

def run_sql(sql: str) -> bool:
    """Execute SQL against D1"""
    # Escape single quotes for shell
    escaped = sql.replace("'", "'\\''")
    cmd = f'{BASE_CMD}="{escaped}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30,
                                cwd="O:/ECHO_OMEGA_PRIME/WORKERS/permian-pulse-scraper")
        if "success" in result.stdout and '"success": true' in result.stdout:
            return True
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return False

def insert_patent(patent_number, title, assignee, filing_date, grant_date, abstract, key_claims, chemical_components, relevance, source_url):
    sql = f"INSERT OR IGNORE INTO patents (patent_number, title, assignee, filing_date, grant_date, abstract, key_claims, chemical_components, relevance, source_url) VALUES ('{patent_number}', '{title}', '{assignee}', '{filing_date}', '{grant_date}', '{abstract}', '{key_claims}', '{chemical_components}', '{relevance}', '{source_url}')"
    return run_sql(sql)

def insert_formulation(competitor_id, product_name, manufacturer, product_type, cas_number, chemical_name, conc_min, conc_max, source_doc, source_url, confidence=0.85):
    sql = f"INSERT INTO chemical_formulations (competitor_id, product_name, manufacturer, product_type, cas_number, chemical_name, concentration_min, concentration_max, source_document, source_url, confidence) VALUES ({competitor_id}, '{product_name}', '{manufacturer}', '{product_type}', '{cas_number}', '{chemical_name}', {conc_min}, {conc_max}, '{source_doc}', '{source_url}', {confidence})"
    return run_sql(sql)

def insert_market_intel(category, metric_name, metric_value, unit, source, source_url, year, confidence, notes):
    sql = f"INSERT INTO market_intel (category, metric_name, metric_value, unit, source, source_url, year, confidence, notes) VALUES ('{category}', '{metric_name}', '{metric_value}', '{unit}', '{source}', '{source_url}', {year}, {confidence}, '{notes}')"
    return run_sql(sql)

def insert_osint(competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool):
    sql = f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) VALUES ({competitor_id}, '{domain}', '{scan_type}', '{finding_type}', '{finding_value}', '{severity}', '{details}', '{source_tool}')"
    return run_sql(sql)

def insert_financial(competitor_id, fiscal_year, revenue, segment, gross_margin, operating_income, key_metrics, source):
    sql = f"INSERT INTO competitor_financials (competitor_id, fiscal_year, revenue, segment, gross_margin, operating_income, key_metrics, source) VALUES ({competitor_id}, {fiscal_year}, '{revenue}', '{segment}', {gross_margin}, '{operating_income}', '{key_metrics}', '{source}')"
    return run_sql(sql)

# =============================================================
# BATCH 1: USPTO PATENTS (16 patents from agent findings)
# =============================================================
print("=" * 60)
print("BATCH 1: USPTO PATENTS — 16 entries")
print("=" * 60)

patents = [
    ("US9382467B2", "Methods for treating produced water", "ChampionX Technologies", "2014-01-15", "2016-07-05",
     "Corrosion inhibitor compositions for produced water treatment in oil and gas operations",
     "Claim 1: Quaternary ammonium compound 5-25wt%; Claim 2: Phosphate ester corrosion inhibitor 1-10wt%",
     "Quaternary ammonium compounds (CAS 68424-85-1) 5-25%, Phosphate esters 1-10%, Imidazoline derivatives 2-15%",
     "direct", "https://patents.google.com/patent/US9382467B2"),
    ("US10336936B2", "Biocide compositions for oilfield applications", "Baker Hughes", "2016-03-22", "2019-07-02",
     "Synergistic biocide blends for controlling bacteria in produced water and injection systems",
     "Claim 1: Glutaraldehyde 5-50wt% with THPS synergist; Claim 2: DBNPA+glutaraldehyde dual action",
     "Glutaraldehyde (CAS 111-30-8) 5-50%, THPS (CAS 55566-30-8) 5-25%, DBNPA (CAS 10222-01-2) 1-5%",
     "direct", "https://patents.google.com/patent/US10336936B2"),
    ("US20210047568A1", "Scale inhibitor compositions with enhanced squeeze treatment lifetime", "Halliburton",
     "2019-08-14", "2021-02-18",
     "Phosphonate-polymer scale inhibitor blends for extended squeeze treatment protection",
     "Claim 1: ATMP+DTPMP phosphonate blend 10-40wt%; Claim 2: Polyaspartic acid co-inhibitor 5-15wt%",
     "ATMP (CAS 6419-19-8) 10-20%, DTPMP (CAS 15827-60-8) 5-15%, Polyaspartic acid 5-15%, HEDP (CAS 2809-21-4) 2-8%",
     "direct", "https://patents.google.com/patent/US20210047568A1"),
    ("US11208585B2", "Emulsion breaker compositions for crude oil dehydration", "Schlumberger", "2018-11-05", "2021-12-28",
     "Resin-based demulsifier compositions for breaking water-in-oil emulsions in production facilities",
     "Claim 1: Ethoxylated phenol-formaldehyde resin 15-45wt%; Claim 2: Oxyalkylated polyamine 5-20wt%",
     "Ethoxylated phenol-formaldehyde resin 15-45%, Oxyalkylated polyamine 5-20%, Aromatic solvent 30-60%",
     "direct", "https://patents.google.com/patent/US11208585B2"),
    ("US20230174858A1", "Hydrogen sulfide scavenger compositions", "ChampionX Technologies", "2021-12-01", "2023-06-08",
     "Triazine-based H2S scavenger with enhanced reaction kinetics for sour gas treatment",
     "Claim 1: MEA-triazine (CAS 645-05-6) 30-60wt%; Claim 2: Monoethanolamine activator 5-15wt%",
     "MEA-triazine (CAS 645-05-6) 30-60%, Monoethanolamine (CAS 141-43-5) 5-15%, Water 25-50%",
     "direct", "https://patents.google.com/patent/US20230174858A1"),
    ("US10920137B2", "Paraffin inhibitor and pour point depressant compositions", "Baker Hughes", "2017-06-15", "2021-02-16",
     "Polymer-based paraffin inhibitors for preventing wax deposition in production tubing",
     "Claim 1: Ethylene-vinyl acetate copolymer 10-30wt%; Claim 2: Poly(meth)acrylate PPD 5-20wt%",
     "EVA copolymer 10-30%, Poly(meth)acrylate 5-20%, Aromatic solvent (xylene/toluene) 40-70%",
     "direct", "https://patents.google.com/patent/US10920137B2"),
    ("US20250109503A1", "Enhanced corrosion inhibitor formulation for multiphase pipelines", "ChampionX Technologies",
     "2024-10-03", "2025-04-03",
     "Next-gen corrosion inhibitor with film-forming amines for CO2/H2S corrosion in multiphase flow",
     "Claim 1: Film-forming amine 10-35wt%; Claim 2: Imidazoline derivative 5-20wt% with phosphate ester synergist",
     "Film-forming amine (CAS 112-90-3) 10-35%, Imidazoline derivative 5-20%, Phosphate ester 2-10%, Methanol carrier 20-40%",
     "direct", "https://patents.google.com/patent/US20250109503A1"),
    ("US11345854B2", "Friction reducer compositions for hydraulic fracturing", "Halliburton",
     "2019-04-10", "2022-05-31",
     "Polyacrylamide-based friction reducer for slickwater fracturing operations",
     "Claim 1: Anionic polyacrylamide 20-40wt% in water-in-oil emulsion; Claim 2: Surfactant inverter 3-8wt%",
     "Anionic polyacrylamide (CAS 9003-05-8) 20-40%, Mineral oil 30-50%, Surfactant inverter 3-8%",
     "direct", "https://patents.google.com/patent/US11345854B2"),
    ("US10640703B2", "Oxygen scavenger compositions for injection water treatment", "ChampionX Technologies",
     "2016-09-20", "2020-05-05",
     "Catalyzed sulfite-based oxygen scavenger for boiler and injection water treatment",
     "Claim 1: Sodium bisulfite (CAS 7631-90-5) 20-40wt% with cobalt catalyst",
     "Sodium bisulfite 20-40%, Ammonium bisulfite 10-25%, Cobalt catalyst 0.01-0.1%, Water balance",
     "direct", "https://patents.google.com/patent/US10640703B2"),
    ("US20220298409A1", "Asphaltene inhibitor and dispersant compositions", "Schlumberger",
     "2021-03-19", "2022-09-22",
     "Alkylphenol resin-based asphaltene dispersant for deepwater and heavy oil production",
     "Claim 1: Alkylphenol-aldehyde resin 10-35wt%; Claim 2: Dodecylbenzenesulfonic acid 5-15wt%",
     "Alkylphenol-aldehyde resin 10-35%, DDBSA (CAS 27176-87-0) 5-15%, Heavy aromatic naphtha 40-65%",
     "direct", "https://patents.google.com/patent/US20220298409A1"),
    ("US10899944B2", "Iron sulfide scale dissolvers for wellbore remediation", "Baker Hughes",
     "2017-11-08", "2021-01-26",
     "Acidic iron sulfide scale dissolver with H2S scavenging capability for well interventions",
     "Claim 1: HCl 10-15wt% with chelating agent; Claim 2: Thioglycolic acid 5-15wt% iron sulfide dissolver",
     "HCl (CAS 7647-01-0) 10-15%, Thioglycolic acid 5-15%, Citric acid (CAS 77-92-9) 5-10%, Corrosion inhibitor 0.5-2%",
     "direct", "https://patents.google.com/patent/US10899944B2"),
    ("US11174420B2", "Foamer compositions for gas well deliquification", "ChampionX Technologies",
     "2018-07-12", "2021-11-16",
     "Fluorosurfactant-free foamer for gas well liquid unloading operations",
     "Claim 1: Alkyl polyglucoside surfactant 15-40wt%; Claim 2: Cocamidopropyl betaine co-surfactant 5-15wt%",
     "APG surfactant 15-40%, Cocamidopropyl betaine (CAS 61789-40-0) 5-15%, Isopropanol (CAS 67-63-0) 10-25%",
     "direct", "https://patents.google.com/patent/US11174420B2"),
    ("US20240101885A1", "Environmentally acceptable corrosion inhibitor for offshore operations", "Halliburton",
     "2022-09-26", "2024-03-28",
     "PLONOR-compliant corrosion inhibitor using fatty acid imidazoline chemistry",
     "Claim 1: Oleic acid imidazoline 10-30wt%; Claim 2: Biodegradable quaternary ammonium 5-15wt%",
     "Oleic acid imidazoline 10-30%, Biodegradable quat 5-15%, Propylene glycol 15-30%, Water balance",
     "direct", "https://patents.google.com/patent/US20240101885A1"),
]

p_ok = 0
for p in patents:
    ok = insert_patent(*p)
    if ok:
        p_ok += 1
    time.sleep(0.3)
print(f"  Patents loaded: {p_ok}/{len(patents)}")

# =============================================================
# BATCH 2: AQUASERV FORMULATIONS (SDS-sourced, exact concentrations)
# =============================================================
print("\n" + "=" * 60)
print("BATCH 2: AQUASERV SDS FORMULATIONS — 25 products")
print("=" * 60)

# Aquaserv is not in our competitor list but their SDS data reveals industry formulations
# We map these as market intel reference data
aquaserv_products = [
    # product_name, product_type, cas, chemical, min%, max%, source_doc
    ("AquaServ CI-200", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium chloride", 10, 30, "SDS CI-200"),
    ("AquaServ CI-200", "corrosion_inhibitor", "68-12-2", "N,N-Dimethylformamide", 10, 20, "SDS CI-200"),
    ("AquaServ CI-200", "corrosion_inhibitor", "67-56-1", "Methanol", 30, 50, "SDS CI-200"),
    ("AquaServ B-100", "biocide", "111-30-8", "Glutaraldehyde", 40, 50, "SDS B-100"),
    ("AquaServ B-100", "biocide", "7732-18-5", "Water", 50, 60, "SDS B-100"),
    ("AquaServ B-200", "biocide", "55566-30-8", "THPS", 35, 45, "SDS B-200"),
    ("AquaServ B-200", "biocide", "7732-18-5", "Water", 55, 65, "SDS B-200"),
    ("AquaServ SI-300", "scale_inhibitor", "6419-19-8", "ATMP", 20, 35, "SDS SI-300"),
    ("AquaServ SI-300", "scale_inhibitor", "7732-18-5", "Water", 65, 80, "SDS SI-300"),
    ("AquaServ H2S-400", "h2s_scavenger", "645-05-6", "MEA-Triazine", 40, 55, "SDS H2S-400"),
    ("AquaServ H2S-400", "h2s_scavenger", "141-43-5", "Monoethanolamine", 5, 15, "SDS H2S-400"),
    ("AquaServ H2S-400", "h2s_scavenger", "7732-18-5", "Water", 30, 45, "SDS H2S-400"),
    ("AquaServ D-500", "demulsifier", "68412-54-4", "Nonylphenol ethoxylate", 15, 30, "SDS D-500"),
    ("AquaServ D-500", "demulsifier", "64742-94-5", "Heavy aromatic naphtha", 40, 60, "SDS D-500"),
    ("AquaServ D-500", "demulsifier", "1330-20-7", "Xylene", 10, 25, "SDS D-500"),
    ("AquaServ PI-600", "paraffin_inhibitor", "24937-78-8", "EVA copolymer", 15, 25, "SDS PI-600"),
    ("AquaServ PI-600", "paraffin_inhibitor", "1330-20-7", "Xylene", 50, 70, "SDS PI-600"),
    ("AquaServ O2S-700", "oxygen_scavenger", "7631-90-5", "Sodium bisulfite", 25, 38, "SDS O2S-700"),
    ("AquaServ O2S-700", "oxygen_scavenger", "7803-55-6", "Ammonium bisulfite", 10, 20, "SDS O2S-700"),
    ("AquaServ FR-800", "friction_reducer", "9003-05-8", "Polyacrylamide", 25, 35, "SDS FR-800"),
    ("AquaServ FR-800", "friction_reducer", "8042-47-5", "Mineral oil", 35, 50, "SDS FR-800"),
    ("AquaServ CL-900", "clay_stabilizer", "7447-40-7", "Potassium chloride", 30, 50, "SDS CL-900"),
    ("AquaServ CL-900", "clay_stabilizer", "10043-52-4", "Calcium chloride", 10, 20, "SDS CL-900"),
    ("AquaServ FM-1000", "foamer", "61789-40-0", "Cocamidopropyl betaine", 10, 20, "SDS FM-1000"),
    ("AquaServ FM-1000", "foamer", "67-63-0", "Isopropanol", 15, 30, "SDS FM-1000"),
]

f_ok = 0
for prod in aquaserv_products:
    pn, pt, cas, chem, mn, mx, src = prod
    ok = insert_formulation(0, pn, "AquaServ Inc", pt, cas, chem, mn, mx, src, "https://aquaservinc.com/sds", 0.9)
    if ok:
        f_ok += 1
    time.sleep(0.25)
print(f"  Formulations loaded: {f_ok}/{len(aquaserv_products)}")

# =============================================================
# BATCH 3: CHAMPIONX FINANCIAL DATA (SEC filings)
# =============================================================
print("\n" + "=" * 60)
print("BATCH 3: CHAMPIONX FINANCIALS — CHX SEC EDGAR")
print("=" * 60)

financials = [
    (1, 2024, "$3.634B", "Total Company", 32.7, "$394.1M", "Production Chemicals $2.289B (63%), Production & Automation Tech $1.345B (37%)", "SEC 10-K FY2024"),
    (1, 2024, "$2.289B", "Production Chemicals", 34.2, "$243.5M", "63% of revenue, upstream chemical treatment, SLB acquisition $7.8B announced", "SEC 10-K FY2024"),
    (1, 2024, "$1.345B", "Production & Automation Tech", 30.1, "$150.6M", "37% of revenue, artificial lift, digital, automation", "SEC 10-K FY2024"),
    (1, 2023, "$3.769B", "Total Company", 33.1, "$412.8M", "Slight revenue decline Y/Y, margin improvement through cost optimization", "SEC 10-K FY2023"),
]

fin_ok = 0
for f in financials:
    ok = insert_financial(*f)
    if ok:
        fin_ok += 1
    time.sleep(0.3)
print(f"  Financials loaded: {fin_ok}/{len(financials)}")

# =============================================================
# BATCH 4: MARKET INTEL — PRICING & INDUSTRY BENCHMARKS
# =============================================================
print("\n" + "=" * 60)
print("BATCH 4: MARKET INTEL — PRICING & BENCHMARKS")
print("=" * 60)

market_data = [
    # category, metric, value, unit, source, url, year, confidence, notes
    ("pricing", "Glutaraldehyde bulk price", "$1,688", "per MT", "ICIS/industry", "", 2025, 0.85, "50% active, FOB US Gulf Coast"),
    ("pricing", "THPS bulk price", "$2,200-2,800", "per MT", "ICIS/industry", "", 2025, 0.8, "75% active, FOB pricing"),
    ("pricing", "Corrosion inhibitor retail", "$8-25", "per gallon", "Field surveys", "", 2025, 0.85, "End-user pricing, varies by volume and chemistry"),
    ("pricing", "Biocide retail", "$5-15", "per gallon", "Field surveys", "", 2025, 0.85, "Glutaraldehyde-based, end-user pricing"),
    ("pricing", "Scale inhibitor retail", "$10-35", "per gallon", "Field surveys", "", 2025, 0.8, "Phosphonate-based, varies by complexity"),
    ("pricing", "H2S scavenger retail", "$4-12", "per gallon", "Field surveys", "", 2025, 0.85, "Triazine-based, volume-dependent"),
    ("pricing", "Demulsifier retail", "$12-40", "per gallon", "Field surveys", "", 2025, 0.8, "Resin-based, application-specific"),
    ("pricing", "Friction reducer retail", "$3-8", "per gallon", "Field surveys", "", 2025, 0.85, "Emulsion polyacrylamide, high-volume"),
    ("pricing", "Per-well monthly chemical cost", "$200-400", "per well/month", "Industry average", "", 2025, 0.8, "Typical Permian Basin treating program"),
    ("pricing", "China glutaraldehyde wholesale", "$800-1,200", "per MT FOB China", "Chinese suppliers", "", 2025, 0.85, "5-50x markup from China to US end-user"),
    ("market_size", "Global oilfield chemicals market", "$25-33B", "annual", "Grand View Research", "", 2025, 0.9, "Growing 4-6% CAGR through 2030"),
    ("market_size", "Permian Basin chemical spend", "$2.5-3.5B", "annual", "Industry estimates", "", 2025, 0.75, "Largest single basin chemical market globally"),
    ("market_size", "US produced water volume", "20M+", "barrels/day", "Produced Water Society", "", 2025, 0.9, "Permian alone ~15M bpd"),
    ("operations", "Typical biocide dosage rate", "50-500", "ppm", "Industry standard", "", 2025, 0.9, "Glutaraldehyde continuous injection"),
    ("operations", "Typical CI dosage rate", "25-100", "ppm", "Industry standard", "", 2025, 0.9, "Film-forming amine type"),
    ("operations", "Typical scale inhibitor dosage", "5-50", "ppm", "Industry standard", "", 2025, 0.9, "Phosphonate squeeze or continuous"),
    ("operations", "Typical H2S scavenger dosage", "100-1000", "ppm", "Industry standard", "", 2025, 0.85, "Triazine type, depends on H2S loading"),
    ("acquisition", "SLB acquiring ChampionX", "$7.8B", "deal value", "SEC EDGAR / PR", "", 2025, 0.95, "All-stock merger, announced 2024, expected close 2025"),
    ("acquisition", "SLB CHX premium", "10.6%", "premium to 30-day VWAP", "SEC EDGAR", "", 2025, 0.95, "0.735 SLB shares per CHX share"),
    ("competitive", "ChampionX production chemicals revenue", "$2.289B", "annual FY2024", "SEC 10-K", "", 2024, 0.95, "63% of total revenue, market leader"),
    ("competitive", "ChampionX gross margin", "32.7%", "percentage", "SEC 10-K", "", 2024, 0.95, "Production chemicals higher at 34.2%"),
    ("competitive", "Industry average markup China-to-US", "5-50x", "multiplier", "Pricing analysis", "", 2025, 0.8, "Chinese wholesale FOB vs US government/field pricing"),
    ("government", "EPA produced water discharge regulations", "Pending", "regulatory", "EPA", "", 2025, 0.9, "Potential new NPDES permits for beneficial reuse"),
    ("government", "Texas RRC chemical disclosure", "Required", "regulatory", "Texas RRC", "", 2025, 0.95, "FracFocus reporting for hydraulic fracturing chemicals"),
]

mi_ok = 0
for m in market_data:
    ok = insert_market_intel(*m)
    if ok:
        mi_ok += 1
    time.sleep(0.25)
print(f"  Market intel loaded: {mi_ok}/{len(market_data)}")

# =============================================================
# BATCH 5: OSINT — PROMETHEUS SCAN FINDINGS
# =============================================================
print("\n" + "=" * 60)
print("BATCH 5: OSINT — PROMETHEUS INFRASTRUCTURE INTEL")
print("=" * 60)

osint_data = [
    # competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool
    # ChampionX (ID 1)
    (1, "championx.com", "infrastructure", "hosting", "Cloudflare CDN + WAF", "info", "Enterprise Cloudflare plan with WAF, DDoS protection", "whois/dns"),
    (1, "championx.com", "infrastructure", "subdomains", "40+ Connexia subdomains discovered", "medium", "connexia-*.championx.com — IoT/fleet management platform, not public. Subdomains: connexia-api, connexia-portal, connexia-fleet, connexia-telemetry, etc.", "subfinder"),
    (1, "championx.com", "infrastructure", "tech_stack", "React + Node.js + Azure", "info", "Modern tech stack with Azure cloud infrastructure", "dns/headers"),
    (1, "championx.com", "corporate", "acquisition", "SLB merger pending $7.8B", "high", "All-stock deal, 0.735 shares ratio, expected 2025 close", "sec_edgar"),

    # Coastal Chemical (ID 2)
    (2, "coastalchem.com", "infrastructure", "hosting", "GoDaddy hosting", "info", "Basic shared hosting, no enterprise CDN", "whois/dns"),
    (2, "coastalchem.com", "infrastructure", "registrar", "GoDaddy.com LLC", "info", "Standard registrar, WHOIS privacy enabled", "whois"),
    (2, "coastalchem.com", "infrastructure", "tech_stack", "WordPress", "info", "WordPress CMS, basic web presence", "headers"),

    # Imperative Chemicals (ID 3)
    (3, "imperativechemicals.com", "infrastructure", "hosting", "AWS + Cloudflare", "info", "Professional hosting with Cloudflare CDN layer", "dns"),
    (3, "imperativechemicals.com", "infrastructure", "email", "Google Workspace", "info", "MX records point to Google Workspace", "dnsrecon"),

    # Corrosion LTD (ID 5)
    (5, "corrosionltd.com", "infrastructure", "hosting", "Squarespace", "info", "Website builder platform, limited customization", "headers"),
    (5, "corrosionltd.com", "infrastructure", "tech_stack", "Squarespace static", "info", "No dynamic backend exposed", "dns"),

    # SGB Solutions (ID 16)
    (16, "sgbsolutions.com", "infrastructure", "whois_exposure", "Full owner info exposed", "high", "Owner: Gary Barmore, full address + phone + email in WHOIS — rare exposure, no privacy protection", "whois"),
    (16, "sgbsolutions.com", "infrastructure", "registrar", "GoDaddy.com", "info", "No WHOIS privacy, personal data exposed", "whois"),
    (16, "sgbsolutions.com", "vulnerability", "whois_privacy", "No WHOIS privacy protection", "high", "Personal information of company owner freely available via WHOIS lookup", "whois"),

    # Sol Nexus (ID 17)
    (17, "solnexus.com", "infrastructure", "hosting", "AWS Global Accelerator", "info", "Enterprise AWS hosting with Global Accelerator IPs", "dig"),
    (17, "solnexus.com", "infrastructure", "corporate_link", "Shared infrastructure with Revive Energy", "high", "Same AWS Global Accelerator IP addresses as reviveenergysolutions.com — indicates corporate relationship or shared infrastructure", "dig/dns"),
    (17, "solnexus.com", "vulnerability", "tls_config", "SWEET32 vulnerability potential", "medium", "TLS configuration may allow 3DES cipher suites vulnerable to SWEET32 birthday attack", "tls_scan"),

    # Revive Energy (ID 15)
    (15, "reviveenergysolutions.com", "infrastructure", "hosting", "AWS Global Accelerator", "info", "Enterprise AWS with Global Accelerator", "dig"),
    (15, "reviveenergysolutions.com", "infrastructure", "corporate_link", "Shared infrastructure with Sol Nexus", "high", "Same AWS Global Accelerator IPs as solnexus.com — corporate relationship confirmed", "dig/dns"),

    # SoluGen (ID 18)
    (18, "solugen.com", "infrastructure", "hosting", "Vercel + Modern stack", "info", "React/Next.js on Vercel — tech-forward biotech startup", "headers"),
    (18, "solugen.com", "infrastructure", "funding", "VC-backed biotech", "info", "Significant VC funding for bio-based chemical production", "public_records"),

    # Enduro Tech (ID 7)
    (7, "endurotech.com", "infrastructure", "hosting", "Basic hosting", "info", "Simple web presence, limited digital footprint", "dns"),

    # Energy Flow (ID 8)
    (8, "energyflowchem.com", "infrastructure", "hosting", "GoDaddy", "info", "Standard hosting, minimal web infrastructure", "whois"),

    # TruCam Solutions (ID 20)
    (20, "trucamsolutions.com", "infrastructure", "hosting", "Basic hosting", "info", "Standard web hosting, limited tech stack", "dns"),

    # Integrity Industries (ID 10)
    (10, "integrityind.com", "infrastructure", "hosting", "Wix/Squarespace", "info", "Website builder platform", "headers"),

    # Interface Treating (ID 11)
    (11, "interfacetreating.com", "infrastructure", "hosting", "Standard hosting", "info", "Simple web presence", "dns"),

    # OT Oilfield (ID 13)
    (13, "otoilfieldchemicals.com", "infrastructure", "hosting", "WordPress", "info", "WordPress site, basic hosting", "headers"),

    # Available domains
    (4, "corechemical.com", "infrastructure", "domain_status", "Domain may be available for acquisition", "medium", "No active website detected during scan", "whois"),
    (9, "infinityenergysolutions.com", "infrastructure", "domain_status", "Domain availability uncertain", "low", "Check GoDaddy/Namecheap for registration status", "whois"),
    (12, "maxflowchemicals.com", "infrastructure", "domain_status", "Domain may be available", "low", "No active web presence found", "whois"),
]

o_ok = 0
for o in osint_data:
    ok = insert_osint(*o)
    if ok:
        o_ok += 1
    time.sleep(0.25)
print(f"  OSINT findings loaded: {o_ok}/{len(osint_data)}")

# =============================================================
# BATCH 6: ADDITIONAL PATENT FORMULATIONS → chemical_formulations
# =============================================================
print("\n" + "=" * 60)
print("BATCH 6: PATENT-DERIVED FORMULATIONS")
print("=" * 60)

patent_formulations = [
    # ChampionX patent formulations (competitor_id=1)
    (1, "CHX CI Multiphase (US20250109503A1)", "ChampionX", "corrosion_inhibitor", "112-90-3", "Film-forming amine (oleylamine)", 10, 35, "US Patent 20250109503A1", "https://patents.google.com/patent/US20250109503A1", 0.95),
    (1, "CHX CI Multiphase (US20250109503A1)", "ChampionX", "corrosion_inhibitor", "68424-85-1", "Imidazoline derivative", 5, 20, "US Patent 20250109503A1", "https://patents.google.com/patent/US20250109503A1", 0.95),
    (1, "CHX H2S Scav (US20230174858A1)", "ChampionX", "h2s_scavenger", "645-05-6", "MEA-Triazine", 30, 60, "US Patent 20230174858A1", "https://patents.google.com/patent/US20230174858A1", 0.95),
    (1, "CHX O2 Scav (US10640703B2)", "ChampionX", "oxygen_scavenger", "7631-90-5", "Sodium bisulfite", 20, 40, "US Patent 10640703B2", "https://patents.google.com/patent/US10640703B2", 0.95),
    (1, "CHX Foamer (US11174420B2)", "ChampionX", "foamer", "61789-40-0", "Cocamidopropyl betaine", 5, 15, "US Patent 11174420B2", "https://patents.google.com/patent/US11174420B2", 0.95),
    (1, "CHX CI Produced Water (US9382467B2)", "ChampionX", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium compound", 5, 25, "US Patent 9382467B2", "https://patents.google.com/patent/US9382467B2", 0.95),
    # Baker Hughes formulations
    (0, "BH Biocide Blend (US10336936B2)", "Baker Hughes", "biocide", "111-30-8", "Glutaraldehyde", 5, 50, "US Patent 10336936B2", "https://patents.google.com/patent/US10336936B2", 0.95),
    (0, "BH Biocide Blend (US10336936B2)", "Baker Hughes", "biocide", "55566-30-8", "THPS synergist", 5, 25, "US Patent 10336936B2", "https://patents.google.com/patent/US10336936B2", 0.95),
    (0, "BH Paraffin Inhibitor (US10920137B2)", "Baker Hughes", "paraffin_inhibitor", "24937-78-8", "EVA copolymer", 10, 30, "US Patent 10920137B2", "https://patents.google.com/patent/US10920137B2", 0.95),
    (0, "BH FeS Dissolver (US10899944B2)", "Baker Hughes", "scale_dissolver", "7647-01-0", "Hydrochloric acid", 10, 15, "US Patent 10899944B2", "https://patents.google.com/patent/US10899944B2", 0.95),
    # Halliburton formulations
    (0, "HAL Scale Inhibitor (US20210047568A1)", "Halliburton", "scale_inhibitor", "6419-19-8", "ATMP phosphonate", 10, 20, "US Patent 20210047568A1", "https://patents.google.com/patent/US20210047568A1", 0.95),
    (0, "HAL Scale Inhibitor (US20210047568A1)", "Halliburton", "scale_inhibitor", "15827-60-8", "DTPMP phosphonate", 5, 15, "US Patent 20210047568A1", "https://patents.google.com/patent/US20210047568A1", 0.95),
    (0, "HAL Friction Reducer (US11345854B2)", "Halliburton", "friction_reducer", "9003-05-8", "Anionic polyacrylamide", 20, 40, "US Patent 11345854B2", "https://patents.google.com/patent/US11345854B2", 0.95),
    (0, "HAL Green CI (US20240101885A1)", "Halliburton", "corrosion_inhibitor", "0-0-0", "Oleic acid imidazoline", 10, 30, "US Patent 20240101885A1", "https://patents.google.com/patent/US20240101885A1", 0.95),
    # Schlumberger formulations
    (0, "SLB Demulsifier (US11208585B2)", "Schlumberger", "demulsifier", "0-0-0", "Ethoxylated phenol-formaldehyde resin", 15, 45, "US Patent 11208585B2", "https://patents.google.com/patent/US11208585B2", 0.95),
    (0, "SLB Asphaltene Disp (US20220298409A1)", "Schlumberger", "asphaltene_dispersant", "27176-87-0", "Dodecylbenzenesulfonic acid (DDBSA)", 5, 15, "US Patent 20220298409A1", "https://patents.google.com/patent/US20220298409A1", 0.95),
]

pf_ok = 0
for pf in patent_formulations:
    ok = insert_formulation(*pf)
    if ok:
        pf_ok += 1
    time.sleep(0.25)
print(f"  Patent formulations loaded: {pf_ok}/{len(patent_formulations)}")

# =============================================================
# SUMMARY
# =============================================================
print("\n" + "=" * 60)
print("S2 INTELLIGENCE INGESTION COMPLETE")
print("=" * 60)
total = p_ok + f_ok + fin_ok + mi_ok + o_ok + pf_ok
print(f"  Patents:             {p_ok}/{len(patents)}")
print(f"  SDS Formulations:    {f_ok}/{len(aquaserv_products)}")
print(f"  Financials:          {fin_ok}/{len(financials)}")
print(f"  Market Intel:        {mi_ok}/{len(market_data)}")
print(f"  OSINT Findings:      {o_ok}/{len(osint_data)}")
print(f"  Patent Formulations: {pf_ok}/{len(patent_formulations)}")
print(f"  TOTAL RECORDS:       {total}")
print("=" * 60)
