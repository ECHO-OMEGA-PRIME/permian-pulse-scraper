"""
Ingest ALL gathered competitive intelligence into permian-pulse-scraper D1 database.
SDS formulations, patents, market pricing, competitor profiles.
Run: H:/Tools/PyManager/pythons/py311/python.exe ingest_intel.py
"""
import subprocess
import json
import sys
import time

DB = "permian-pulse-scraper"
WRANGLER = "npx"
SUCCESS = 0
FAIL = 0

def d1(sql: str) -> bool:
    global SUCCESS, FAIL
    try:
        r = subprocess.run(
            [WRANGLER, "wrangler", "d1", "execute", DB, "--remote", "--command", sql],
            capture_output=True, text=True, timeout=30,
            shell=True
        )
        if r.returncode == 0 and '"success": true' in r.stdout:
            SUCCESS += 1
            return True
        else:
            FAIL += 1
            err = r.stderr[:200] if r.stderr else r.stdout[:200]
            print(f"  FAIL: {err}")
            return False
    except Exception as e:
        FAIL += 1
        print(f"  ERROR: {e}")
        return False

def esc(s: str) -> str:
    """Escape single quotes for SQL."""
    return s.replace("'", "''") if s else ""

# ═══════════════════════════════════════════════════════════════════════════════
# SDS CHEMICAL FORMULATIONS — 21 products, ~40 chemical component rows
# ═══════════════════════════════════════════════════════════════════════════════

FORMULATIONS = [
    # (competitor_id or None, product_name, manufacturer, product_type, cas, chemical, min%, max%, source_doc, source_url)
    # Champion X products (competitor_id=1)
    (1, "CORR11540W", "ChampionX", "biocide_corrosion_inhibitor", "68424-85-1", "Benzalkonium Chloride (BDAC)", 10, 30, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORR11540W", "ChampionX", "biocide_corrosion_inhibitor", "111-30-8", "Glutaraldehyde", 5, 10, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORR11540W", "ChampionX", "biocide_corrosion_inhibitor", "64-17-5", "Ethanol", 1, 5, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", "95-38-5", "2-Heptadecenyl-4,5-dihydro-1H-Imidazole-1-ethanol", 10, 20, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", None, "Morpholine derivatives", 3, 5, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", None, "Quaternised copolymer of acrylamide", 1, 3, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", "60-24-2", "2-Mercaptoethanol", 1, 3, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", "143-22-6", "2-(2-Butoxyethoxy)ethanol", 1, 5, "ChampionX SDS", "https://www.championx.com/sds"),
    (1, "CORRTREAT 15316", "ChampionX", "corrosion_inhibitor", "7664-38-2", "Phosphoric acid", 1, 3, "ChampionX SDS", "https://www.championx.com/sds"),

    # Nalco (now part of Ecolab, but major supplier — maps to Champion X ecosystem)
    (1, "Nalco 73310", "Nalco/Ecolab", "corrosion_inhibitor", "7632-00-0", "Sodium Nitrite", 30, 60, "Nalco SDS/PA DEP MSDS #1764", "https://files.dep.state.pa.us/water/"),
    (1, "Nalco 73199", "Nalco/Ecolab", "corrosion_inhibitor", "15217-42-2", "Sodium Benzotriazole", 30, 60, "Nalco SDS", "https://www.nalco.com/sds"),
    (1, "Nalco 8338", "Nalco/Ecolab", "corrosion_inhibitor", "7632-00-0", "Sodium Nitrite", 10, 30, "Nalco SDS", "https://www.nalco.com/sds"),
    (1, "Nalco 8338", "Nalco/Ecolab", "corrosion_inhibitor", None, "Sodium Tolyltriazole", 1, 5, "Nalco SDS", "https://www.nalco.com/sds"),
    (1, "H-130 Microbiocide", "Nalco", "biocide", "7173-51-5", "Didecyl-Dimethyl-Ammonium Chloride (DDAC)", 30, 60, "PA DEP MSDS #307", "https://files.dep.state.pa.us/water/wastewater%20management/EDMRPortalFiles/Chemical_Additives/MSDS/"),
    (1, "H-130 Microbiocide", "Nalco", "biocide", "64-17-5", "Ethanol", 10, 30, "PA DEP MSDS #307", "https://files.dep.state.pa.us/water/"),
    (1, "H-550", "Nalco", "biocide", "111-30-8", "Glutaraldehyde", 30, 60, "PA DEP MSDS #308", "https://files.dep.state.pa.us/water/"),

    # EC products (generic competitor — multiple suppliers)
    (None, "EC6486A", "Unknown", "scale_inhibitor", None, "Amine Triphosphate (Proprietary)", 10, 30, "Industry SDS", ""),
    (None, "EC6486A", "Unknown", "scale_inhibitor", "107-21-1", "Ethylene Glycol", 10, 30, "Industry SDS", ""),
    (None, "EC1317A", "Unknown", "corrosion_inhibitor", "67-56-1", "Methanol", 30, 60, "Industry SDS", ""),
    (None, "EC1317A", "Unknown", "corrosion_inhibitor", "68140-11-4", "Tall Oil DETA Imidazoline Acetates", 5, 10, "Industry SDS", ""),
    (None, "EC1317A", "Unknown", "corrosion_inhibitor", "139-07-1", "Benzyl-DMDA Chloride (Quat)", 1, 5, "Industry SDS", ""),
    (None, "EC1317A", "Unknown", "corrosion_inhibitor", "68-11-1", "Thioglycolic Acid", 1, 5, "Industry SDS", ""),

    # Baker Hughes/Baker Petrolite
    (None, "BPB 59316", "Baker Petrolite/Baker Hughes", "scale_inhibitor", "1310-73-2", "Sodium Hydroxide", 1, 5, "PA DEP MSDS #358", "https://files.dep.state.pa.us/water/"),

    # GE Betz (now SUEZ Water Technologies)
    (None, "BIOMATE MBC2881", "GE Betz", "biocide", "10222-01-2", "DBNPA (2,2-Dibromo-3-Nitrilopropionamide)", 15, 40, "PA DEP MSDS #642", "https://files.dep.state.pa.us/water/"),
    (None, "BIOMATE MBC2881", "GE Betz", "biocide", "7647-15-6", "Sodium Bromide", 3, 7, "PA DEP MSDS #642", "https://files.dep.state.pa.us/water/"),
    (None, "BIOMATE MBC2881", "GE Betz", "biocide", "3252-43-5", "Dibromoacetonitrile", 1, 5, "PA DEP MSDS #642", "https://files.dep.state.pa.us/water/"),
    (None, "SPECTRUS NX1100", "GE Betz", "biocide", "52-51-7", "Bronopol (2-Bromo-2-Nitropropane-1,3-Diol)", 5, 10, "PA DEP MSDS #167", "https://files.dep.state.pa.us/water/"),
    (None, "SPECTRUS NX1100", "GE Betz", "biocide", "10377-60-3", "Magnesium Nitrate", 1, 5, "PA DEP MSDS #167", "https://files.dep.state.pa.us/water/"),
    (None, "SPECTRUS NX1100", "GE Betz", "biocide", "55965-84-9", "CMIT/MIT Isothiazolinones", 1, 5, "PA DEP MSDS #167", "https://files.dep.state.pa.us/water/"),

    # SUEZ Water Technologies
    (None, "SPECTRUS NX106", "SUEZ WTS", "biocide", "10377-60-3", "Magnesium Nitrate", 1, 2.5, "PA DEP MSDS #1040", "https://files.dep.state.pa.us/water/"),
    (None, "SPECTRUS NX106", "SUEZ WTS", "biocide", "55965-84-9", "CMIT/MIT Isothiazolinones", 1, 2.5, "PA DEP MSDS #1040", "https://files.dep.state.pa.us/water/"),

    # Solenis
    (None, "Biosperse CN6501", "Solenis", "biocide", "68424-85-1", "ADBAC (Alkyl C12-16 Dimethylbenzyl Ammonium Chloride)", 50, 60, "PA DEP MSDS #1788", "https://files.dep.state.pa.us/water/"),
    (None, "Biosperse CN6501", "Solenis", "biocide", "64-17-5", "Ethanol", 10, 15, "PA DEP MSDS #1788", "https://files.dep.state.pa.us/water/"),
    (None, "Spectrum XD8904", "Solenis", "biocide_oxidizer", "118-52-5", "DCDMH (Dichloro-1,3,5,5-Dimethylhydantoin)", 80, 90, "PA DEP MSDS #2028", "https://files.dep.state.pa.us/water/"),
    (None, "Spectrum XD8904", "Solenis", "biocide_oxidizer", "89415-87-2", "Dichloro-1,3,5-Ethyl-5-Methylhydantoin", 15, 20, "PA DEP MSDS #2028", "https://files.dep.state.pa.us/water/"),

    # Water Science Technologies / Italmatch
    (None, "K-BAC 1020", "Water Science Technologies/Italmatch", "biocide", "10222-01-2", "DBNPA", 19, 21, "PA DEP MSDS #2383", "https://files.dep.state.pa.us/water/"),

    # SoluGen (competitor_id=18)
    (18, "Verza360", "SoluGen", "chelant_scale_inhibitor", None, "Bio-chelant (replaces EDTA/THPS)", None, None, "SoluGen website", "https://www.solugen.com"),

    # Generic industry
    (None, "Glutaraldehyde 25%", "Fisher Scientific/Multiple", "biocide_active", "111-30-8", "Glutaraldehyde", 25, 25, "Fisher Scientific SDS", "https://www.fishersci.com"),
    (None, "Sodium Bisulfite", "Fisher Scientific/Multiple", "oxygen_scavenger", "7631-90-5", "Sodium Bisulfite", 95, 100, "Fisher Scientific SDS", "https://www.fishersci.com"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# PATENTS
# ═══════════════════════════════════════════════════════════════════════════════

PATENTS = [
    ("US11718781", "Scale Inhibitor Composition", "Unknown", None, None,
     "Low MW copolymer of (meth)acrylic acid + AMPS + phosphonic acid monomer for scale inhibition in oilfield operations",
     "Scale prevention using low MW copolymers with phosphonic acid groups",
     "(meth)acrylic acid, AMPS, phosphonic acid monomer",
     "Direct competitor to phosphonate-based scale inhibitors used in Permian Basin",
     "https://patents.google.com/patent/US11718781"),
    ("US20230124406", "Corrosion Inhibition Composition", "Unknown", None, None,
     "Terpene + cinnamaldehyde + amphoteric surfactant for oilfield corrosion inhibition — green chemistry alternative",
     "Green corrosion inhibitor using natural terpenes and cinnamaldehyde",
     "Terpene, cinnamaldehyde, amphoteric surfactant",
     "Green chemistry alternative to traditional imidazoline-based CI formulations",
     "https://patents.google.com/patent/US20230124406"),
    ("US20240110096", "Corrosion Inhibitor Polymer System", "Unknown", None, None,
     "Polymer (vinylpyrrolidone + vinyl acetate) + thioamide for corrosion inhibition in produced water systems",
     "Polymer-thioamide synergy for produced water corrosion control",
     "Polyvinylpyrrolidone-vinyl acetate copolymer, thioamide",
     "Novel polymer approach to CI — different mechanism than quat/imidazoline formulations",
     "https://patents.google.com/patent/US20240110096"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MARKET INTEL — pricing, sizing, benchmarks
# ═══════════════════════════════════════════════════════════════════════════════

MARKET_INTEL = [
    # (category, metric_name, metric_value, unit, source, year, notes)
    ("market_size", "Oilfield Corrosion Inhibitor Market", "1887", "M USD", "Industry Reports", 2024, "Global market size"),
    ("market_size", "Oilfield Corrosion Inhibitor Market Projected", "3036", "M USD", "Industry Reports", 2032, "Projected global market"),
    ("market_trend", "North American Independents Production Chemistry Cut", "12-18", "%", "Industry Analysis", 2024, "Cost reduction in production chemistry spending"),
    ("production", "Permian Basin Share of US Oil Production", "48+", "%", "EIA", 2024, "Permian Basin dominance"),
    ("production", "US Oil Production Record", "13.2", "M bbl/day", "EIA", 2024, "Record US production"),
    ("production", "Permian Horizontal Well Flowback Peak", "35000", "bbl fluid/day", "SPE Papers", 2024, "Peak flowback rates observed"),
    ("pricing_treatment", "Produced Water Treatment Cost - Basic", "2.55-10", "$/bbl", "Industry Benchmarks", 2024, "Range from basic treatment to drinking water quality"),
    ("pricing_treatment", "Produced Water Treatment - Agricultural Reuse", "2.55-4", "$/bbl", "Industry Benchmarks", 2024, "Treatment for ag reuse"),
    ("pricing_treatment", "Produced Water Treatment - Drinking Water", "4-10", "$/bbl", "Industry Benchmarks", 2024, "Full treatment to potable quality"),
    ("pricing_treatment", "Chemical Coagulation Cost", "2.33", "$/bbl", "Research Papers", 2024, "Chemical coagulation treatment cost"),
    ("pricing_treatment", "Electrocoagulation Cost", "2.77", "$/bbl", "Research Papers", 2024, "Electrocoagulation treatment cost"),
    ("pricing_treatment", "Recycling for Frac Reuse", "0.15-1.50", "$/bbl", "Industry Benchmarks", 2024, "Treatment for frac water recycling"),
    ("pricing_treatment", "Robust Produced Water Treatment", "17458-75580", "$/Ac-ft", "Research Papers", 2024, "Full treatment cost range"),
    ("pricing_treatment", "Brackish Water Desalination", "360-790", "$/Ac-ft", "Research Papers", 2024, "Baseline comparison - desal is much cheaper"),
    ("pricing_treatment", "Delaware Sub-basin Water Disposal", "2", "$/bbl oil", "Industry Analysis", 2024, "Water handling cost per barrel of oil"),
    ("pricing_raw_material", "Glutaraldehyde Bulk Price", "1826-1943", "USD/MT", "Chemical Market Reports", 2024, "Raw material wholesale price"),
    ("pricing_dosage", "Combined CI/Biocide/O2 Scavenger Dosage", "400-800", "ppm", "Treatment Protocols", 2024, "Typical combined dosage rate for produced water"),
    ("financials_chx", "ChampionX Production Chemicals Revenue", "2288.9", "M USD", "CHX 10-K SEC Filing", 2024, "FY2024 Production Chemical Technologies segment"),
    ("financials_chx", "ChampionX Operating Margin", "15.9", "%", "CHX 10-K SEC Filing", 2024, "Production Chemicals segment operating margin"),
    ("financials_chx", "ChampionX EBITDA Margin", "21.4", "%", "CHX 10-K SEC Filing", 2024, "Production Chemicals EBITDA margin"),
    ("financials_chx", "ChampionX Total Revenue", "3634.0", "M USD", "CHX 10-K SEC Filing", 2024, "FY2024 total company revenue"),
    ("financials_chx", "ChampionX Gross Margin", "32.7", "%", "CHX 10-K SEC Filing", 2024, "Company-wide gross margin"),
    ("financials_chx", "ChampionX COGS", "2445.3", "M USD", "CHX 10-K SEC Filing", 2024, "Total cost of goods sold"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTS (for the products table — summary per product)
# ═══════════════════════════════════════════════════════════════════════════════

PRODUCTS = [
    # (competitor_id, product_name, category, description, price_info, source_url)
    (1, "Nalco 73310", "corrosion_inhibitor", "Sodium nitrite-based corrosion inhibitor (30-60% sodium nitrite). Inorganic CI for closed systems.", "Sodium nitrite bulk: ~$800-1200/MT", "PA DEP MSDS repository"),
    (1, "Nalco 73199", "corrosion_inhibitor", "Sodium benzotriazole-based CI (30-60%). Copper/yellow metal corrosion protection.", None, "Nalco SDS"),
    (1, "Nalco 8338", "corrosion_inhibitor", "Multi-component CI: sodium nitrite 10-30%, sodium tolyltriazole 1-5%. Closed system protection.", None, "Nalco SDS"),
    (1, "CORR11540W", "biocide_CI_combo", "Combined biocide/CI: BDAC 10-30%, glutaraldehyde 5-10%, ethanol 1-5%. Dual-action oilfield treatment.", "Glutaraldehyde raw: $1826-1943/MT", "ChampionX SDS"),
    (1, "CORRTREAT 15316", "corrosion_inhibitor", "Advanced imidazoline-based CI: heptadecenyl-imidazoline 10-20%, mercaptoethanol 1-3%, phosphoric acid 1-3%. Film-forming CI for H2S environments.", None, "ChampionX SDS"),
    (1, "H-130 Microbiocide", "biocide", "DDAC-based biocide (30-60% didecyl-dimethyl-ammonium chloride). Non-oxidizing microbiocide for oilfield water.", None, "PA DEP MSDS #307"),
    (1, "H-550", "biocide", "Concentrated glutaraldehyde biocide (30-60%). Primary biocide for SRB/APB control in produced water.", None, "PA DEP MSDS #308"),
    (None, "EC6486A", "scale_inhibitor", "Phosphonate-based scale inhibitor: amine triphosphate 10-30%, ethylene glycol 10-30%. Prevents calcium carbonate/barium sulfate scale.", None, "Industry SDS"),
    (None, "EC1317A", "corrosion_inhibitor", "Methanol-based CI (30-60%): imidazoline acetates 5-10%, quat ammonium 1-5%, thioglycolic acid 1-5%. Pipeline/downhole CI.", None, "Industry SDS"),
    (None, "BPB 59316", "scale_inhibitor", "Baker Petrolite scale inhibitor with sodium hydroxide carrier. Proprietary phosphonate/polymer blend.", None, "PA DEP MSDS #358"),
    (None, "BIOMATE MBC2881", "biocide", "DBNPA-based rapid-kill biocide (15-40% DBNPA). Fast-acting, auto-degrading. For cooling water and oilfield injection systems.", None, "PA DEP MSDS #642"),
    (None, "SPECTRUS NX106", "biocide", "CMIT/MIT isothiazolinone biocide (1-2.5%). Non-oxidizing broad-spectrum microbiocide for water treatment.", None, "PA DEP MSDS #1040"),
    (None, "SPECTRUS NX1100", "biocide", "Multi-active biocide: bronopol 5-10%, CMIT/MIT 1-5%, magnesium chloride 1-5%. Synergistic biocide system.", None, "PA DEP MSDS #167"),
    (None, "Biosperse CN6501", "biocide", "Concentrated ADBAC biocide (50-60% alkyl dimethylbenzyl ammonium chloride). High-potency quat for severe biofouling.", None, "PA DEP MSDS #1788"),
    (None, "Spectrum XD8904", "biocide_oxidizer", "Solid halogenated biocide: DCDMH 80-90%. Slow-release oxidizing biocide for water systems.", None, "PA DEP MSDS #2028"),
    (None, "K-BAC 1020", "biocide", "DBNPA biocide (19-21%). Fast-acting non-oxidizing biocide in glycol/water carrier.", None, "PA DEP MSDS #2383"),
    (18, "Verza360", "chelant_scale_inhibitor", "Bio-chelant replacing EDTA/THPS. Uses 1/3 concentration of EDTA. Green chemistry alternative for scale/deposit control.", None, "https://www.solugen.com"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR PROFILES (extracted_data entries)
# ═══════════════════════════════════════════════════════════════════════════════

COMPETITOR_PROFILES = [
    # (competitor_id, data_type, data_key, data_value, confidence)
    (1, "financials", "fy2024_production_chem_revenue", "$2,288.9M", 0.95),
    (1, "financials", "fy2024_total_revenue", "$3,634.0M", 0.95),
    (1, "financials", "fy2024_gross_margin", "32.7%", 0.95),
    (1, "financials", "fy2024_prod_chem_operating_margin", "15.9%", 0.95),
    (1, "financials", "fy2024_prod_chem_ebitda_margin", "21.4%", 0.95),
    (1, "financials", "fy2024_cogs", "$2,445.3M", 0.95),
    (3, "company_profile", "size", "900+ employees, 45 locations, Midland TX HQ", 0.9),
    (3, "company_profile", "market_position", "Largest privately held oilfield chem co in North America", 0.9),
    (16, "company_profile", "products_count", "450+ chemical products", 0.85),
    (16, "company_profile", "founded", "2012", 0.9),
    (16, "company_profile", "location", "Midland TX", 0.95),
    (21, "company_profile", "employees", "21-50", 0.8),
    (21, "company_profile", "revenue_estimate", "$5-10M", 0.7),
    (21, "company_profile", "location", "Midland TX", 0.95),
    (18, "company_profile", "key_product", "Verza360 bio-chelant — replaces EDTA/THPS at 1/3 concentration", 0.9),
    (2, "company_profile", "parent", "Brenntag subsidiary", 0.95),
    (2, "company_profile", "capability", "Own lab management platform with stored data", 0.85),
]

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTE ALL INSERTS
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("PERMIAN PULSE INTELLIGENCE INGESTION")
print("=" * 70)

# 1. Chemical formulations
print(f"\n--- CHEMICAL FORMULATIONS ({len(FORMULATIONS)} rows) ---")
for f in FORMULATIONS:
    comp_id, prod, mfg, ptype, cas, chem, cmin, cmax, sdoc, surl = f
    comp_str = str(comp_id) if comp_id else "NULL"
    cas_str = f"'{esc(cas)}'" if cas else "NULL"
    cmin_str = str(cmin) if cmin is not None else "NULL"
    cmax_str = str(cmax) if cmax is not None else "NULL"
    sql = f"INSERT OR IGNORE INTO chemical_formulations (competitor_id, product_name, manufacturer, product_type, cas_number, chemical_name, concentration_min, concentration_max, source_document, source_url) VALUES ({comp_str}, '{esc(prod)}', '{esc(mfg)}', '{esc(ptype)}', {cas_str}, '{esc(chem)}', {cmin_str}, {cmax_str}, '{esc(sdoc)}', '{esc(surl)}')"
    d1(sql)
    print(f"  [{SUCCESS}] {prod} — {chem}")
    time.sleep(0.3)

# 2. Patents
print(f"\n--- PATENTS ({len(PATENTS)} rows) ---")
for p in PATENTS:
    pnum, title, assignee, fdate, gdate, abstract, claims, components, relevance, url = p
    fdate_str = f"'{fdate}'" if fdate else "NULL"
    gdate_str = f"'{gdate}'" if gdate else "NULL"
    sql = f"INSERT OR IGNORE INTO patents (patent_number, title, assignee, filing_date, grant_date, abstract, key_claims, chemical_components, relevance, source_url) VALUES ('{esc(pnum)}', '{esc(title)}', '{esc(assignee)}', {fdate_str}, {gdate_str}, '{esc(abstract)}', '{esc(claims)}', '{esc(components)}', '{esc(relevance)}', '{esc(url)}')"
    d1(sql)
    print(f"  [{SUCCESS}] {pnum}: {title}")
    time.sleep(0.3)

# 3. Market intel
print(f"\n--- MARKET INTEL ({len(MARKET_INTEL)} rows) ---")
for m in MARKET_INTEL:
    cat, name, val, unit, source, year, notes = m
    unit_str = f"'{esc(unit)}'" if unit else "NULL"
    sql = f"INSERT OR IGNORE INTO market_intel (category, metric_name, metric_value, unit, source, year, notes) VALUES ('{esc(cat)}', '{esc(name)}', '{esc(val)}', {unit_str}, '{esc(source)}', {year}, '{esc(notes)}')"
    d1(sql)
    print(f"  [{SUCCESS}] {name}: {val} {unit or ''}")
    time.sleep(0.3)

# 4. Products
print(f"\n--- PRODUCTS ({len(PRODUCTS)} rows) ---")
for p in PRODUCTS:
    comp_id, name, cat, desc, price, url = p
    comp_str = str(comp_id) if comp_id else "NULL"
    price_str = f"'{esc(price)}'" if price else "NULL"
    url_str = f"'{esc(url)}'" if url else "NULL"
    sql = f"INSERT OR IGNORE INTO products (competitor_id, product_name, category, description, price_info, source_url) VALUES ({comp_str}, '{esc(name)}', '{esc(cat)}', '{esc(desc)}', {price_str}, {url_str})"
    d1(sql)
    print(f"  [{SUCCESS}] {name}")
    time.sleep(0.3)

# 5. Competitor profiles
print(f"\n--- COMPETITOR PROFILES ({len(COMPETITOR_PROFILES)} rows) ---")
for cp in COMPETITOR_PROFILES:
    comp_id, dtype, dkey, dval, conf = cp
    sql = f"INSERT OR IGNORE INTO extracted_data (competitor_id, data_type, data_key, data_value, confidence, source_url) VALUES ({comp_id}, '{esc(dtype)}', '{esc(dkey)}', '{esc(dval)}', {conf}, 'intelligence_gathering')"
    d1(sql)
    print(f"  [{SUCCESS}] [{comp_id}] {dkey}: {dval}")
    time.sleep(0.3)

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print(f"INGESTION COMPLETE: {SUCCESS} succeeded, {FAIL} failed")
print(f"  Chemical formulations: {len(FORMULATIONS)} rows")
print(f"  Patents: {len(PATENTS)} rows")
print(f"  Market intel: {len(MARKET_INTEL)} rows")
print(f"  Products: {len(PRODUCTS)} rows")
print(f"  Competitor profiles: {len(COMPETITOR_PROFILES)} rows")
print(f"  TOTAL: {len(FORMULATIONS) + len(PATENTS) + len(MARKET_INTEL) + len(PRODUCTS) + len(COMPETITOR_PROFILES)} rows attempted")
print("=" * 70)
