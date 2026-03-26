"""
Permian Pulse Pricing Intelligence Collector
Runs locally on ALPHA to collect pricing from government + distributor sources
that block Cloudflare Workers, then pushes to the Worker API.

Sources:
  1. USASpending.gov — Federal contract awards for oilfield chemicals
  2. SAM.gov — Government procurement opportunities
  3. Chemical distributor sites — Retail/wholesale pricing
"""
import json
import time
import requests
from pathlib import Path
from datetime import datetime

WORKER_URL = "https://permian-pulse-scraper.bmcii1976.workers.dev"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# Competitors to match against vendors
COMPETITORS = [
    "Champion X", "Coastal Chemical", "Imperative", "Core Chemical",
    "Corrosion LTD", "Credence IMC", "Enduro Tech", "Energy Flow",
    "Infinity Energy Solutions", "Integrity Industries", "Interface Treating",
    "Max Flow", "OT Oilfield Chemicals", "Perfect Chemical Solutions",
    "Revive Energy Solutions", "SGB Solutions", "Sol Nexus", "SoluGen",
    "Specialty Intermediates", "TruCam Solutions", "Halliburton",
    "Ecolab", "Flotek", "Newpark",
]

RESULTS = []

def push_pricing(records: list[dict]) -> int:
    """Push pricing records to the Worker via D1."""
    if not records:
        return 0
    # POST to worker which will store in D1
    try:
        resp = requests.post(
            f"{WORKER_URL}/ingest-pricing",
            json={"records": records},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            return data.get("inserted", 0)
        else:
            print(f"  Push failed: HTTP {resp.status_code}")
            return 0
    except Exception as e:
        print(f"  Push error: {e}")
        return 0


# ─── USASPENDING.GOV ─────────────────────────────────────────────────────────

def collect_usaspending() -> list[dict]:
    print("\n=== USASpending.gov ===")
    records = []

    # NAICS codes for chemical manufacturers
    naics_codes = ["325998", "325199", "325180", "325611", "213112"]

    # Keyword searches
    keywords = [
        "oilfield chemicals",
        "production chemicals",
        "water treatment chemicals oil gas",
        "corrosion inhibitor",
        "scale inhibitor",
        "biocide",
        "demulsifier",
        "drilling fluid",
        "well stimulation",
        "methanol",
        "glycol",
        "H2S scavenger",
        "fracturing chemicals",
        "completion chemicals",
        "hydrochloric acid well",
        "surfactant oilfield",
        "polymer flooding",
        "friction reducer",
        "paraffin wax inhibitor",
    ]

    # 1. NAICS code search
    for naics in naics_codes:
        print(f"  NAICS {naics}...")
        try:
            resp = requests.post(
                "https://api.usaspending.gov/api/v2/search/spending_by_award/",
                json={
                    "filters": {
                        "naics_codes": [naics],
                        "time_period": [{"start_date": "2022-01-01", "end_date": "2026-12-31"}],
                        "award_type_codes": ["A", "B", "C", "D"],
                    },
                    "fields": [
                        "Award ID", "Recipient Name", "Description",
                        "Award Amount", "Total Obligation",
                        "Start Date", "End Date", "Awarding Agency",
                        "Contract Award Type", "generated_internal_id",
                    ],
                    "limit": 100,
                    "page": 1,
                    "sort": "Award Amount",
                    "order": "desc",
                },
                headers={"User-Agent": UA},
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code}")
                continue

            data = resp.json()
            awards = data.get("results", [])
            print(f"    {len(awards)} awards (total: {data.get('page_metadata', {}).get('total', '?')})")

            for award in awards:
                desc = (award.get("Description") or "").lower()
                vendor = award.get("Recipient Name", "")
                amount = award.get("Award Amount") or award.get("Total Obligation") or 0

                # Filter for chemical-related
                chem_keywords = ["chemical", "inhibitor", "biocide", "treatment", "solvent",
                    "acid", "surfactant", "methanol", "glycol", "drilling", "well service",
                    "petroleum", "oilfield", "corrosion", "scale", "production chem"]
                is_relevant = any(kw in desc for kw in chem_keywords)

                if not is_relevant and naics not in ["325998", "325199", "325180"]:
                    continue

                # Match vendor to competitor
                matched_competitor = None
                for comp in COMPETITORS:
                    if comp.lower() in vendor.lower():
                        matched_competitor = comp
                        break

                records.append({
                    "product_name": (award.get("Description") or f"NAICS {naics} contract")[:200],
                    "product_category": f"NAICS_{naics}",
                    "price": amount,
                    "price_unit": "USD contract value",
                    "source": "USASpending.gov",
                    "source_url": f"https://www.usaspending.gov/award/{award.get('generated_internal_id', award.get('Award ID', ''))}",
                    "contract_number": award.get("Award ID", ""),
                    "buyer": award.get("Awarding Agency", ""),
                    "vendor": vendor,
                    "award_date": award.get("Start Date", ""),
                    "confidence": 0.9,
                    "notes": f"NAICS: {naics} | Period: {award.get('Start Date', '?')} to {award.get('End Date', '?')} | Type: {award.get('Contract Award Type', 'N/A')}",
                    "competitor_name": matched_competitor,
                })

        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)

    # 2. Keyword searches
    for kw in keywords:
        print(f"  Keyword: {kw}...")
        try:
            resp = requests.post(
                "https://api.usaspending.gov/api/v2/search/spending_by_award/",
                json={
                    "filters": {
                        "keywords": [kw],
                        "time_period": [{"start_date": "2023-01-01", "end_date": "2026-12-31"}],
                        "award_type_codes": ["A", "B", "C", "D"],
                    },
                    "fields": [
                        "Award ID", "Recipient Name", "Description",
                        "Award Amount", "Total Obligation",
                        "Start Date", "End Date", "Awarding Agency",
                        "generated_internal_id",
                    ],
                    "limit": 50,
                    "page": 1,
                    "sort": "Award Amount",
                    "order": "desc",
                },
                headers={"User-Agent": UA},
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code}")
                continue

            data = resp.json()
            awards = data.get("results", [])
            print(f"    {len(awards)} awards")

            for award in awards:
                vendor = award.get("Recipient Name", "")
                amount = award.get("Award Amount") or award.get("Total Obligation") or 0

                matched_competitor = None
                for comp in COMPETITORS:
                    if comp.lower() in vendor.lower():
                        matched_competitor = comp
                        break

                records.append({
                    "product_name": (award.get("Description") or kw)[:200],
                    "product_category": "oilfield_chemicals",
                    "price": amount,
                    "price_unit": "USD contract value",
                    "source": "USASpending.gov",
                    "source_url": f"https://www.usaspending.gov/award/{award.get('generated_internal_id', award.get('Award ID', ''))}",
                    "contract_number": award.get("Award ID", ""),
                    "buyer": award.get("Awarding Agency", ""),
                    "vendor": vendor,
                    "award_date": award.get("Start Date", ""),
                    "confidence": 0.85,
                    "notes": f"Keyword: {kw}",
                    "competitor_name": matched_competitor,
                })

        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(0.5)

    # 3. Direct competitor vendor search
    for comp in ["Champion X", "Halliburton", "Ecolab", "Coastal Chemical", "Imperative", "Flotek", "Newpark"]:
        print(f"  Vendor: {comp}...")
        try:
            resp = requests.post(
                "https://api.usaspending.gov/api/v2/search/spending_by_award/",
                json={
                    "filters": {
                        "recipient_search_text": [comp],
                        "time_period": [{"start_date": "2020-01-01", "end_date": "2026-12-31"}],
                        "award_type_codes": ["A", "B", "C", "D"],
                    },
                    "fields": [
                        "Award ID", "Recipient Name", "Description",
                        "Award Amount", "Total Obligation",
                        "Start Date", "End Date", "Awarding Agency",
                        "generated_internal_id",
                    ],
                    "limit": 100,
                    "page": 1,
                    "sort": "Award Amount",
                    "order": "desc",
                },
                headers={"User-Agent": UA},
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code}")
                continue

            data = resp.json()
            awards = data.get("results", [])
            print(f"    {len(awards)} awards for {comp}")

            for award in awards:
                amount = award.get("Award Amount") or award.get("Total Obligation") or 0
                records.append({
                    "product_name": (award.get("Description") or f"{comp} contract")[:200],
                    "product_category": "competitor_contract",
                    "price": amount,
                    "price_unit": "USD contract value",
                    "source": "USASpending.gov",
                    "source_url": f"https://www.usaspending.gov/award/{award.get('generated_internal_id', '')}",
                    "contract_number": award.get("Award ID", ""),
                    "buyer": award.get("Awarding Agency", ""),
                    "vendor": award.get("Recipient Name", comp),
                    "award_date": award.get("Start Date", ""),
                    "confidence": 0.95,
                    "notes": f"Direct competitor vendor search: {comp}",
                    "competitor_name": comp,
                })

        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)

    print(f"  Total USASpending records: {len(records)}")
    return records


# ─── CHEMICAL DISTRIBUTOR PRICING ─────────────────────────────────────────────

def collect_distributor_pricing() -> list[dict]:
    """Scrape pricing from chemical distributors that list prices publicly."""
    print("\n=== Chemical Distributor Pricing ===")
    records = []

    # Sites that actually list bulk chemical prices
    targets = [
        # Lab Alley — bulk chemical supplier (Austin, TX)
        ("LabAlley", "https://www.laballey.com/collections/methanol"),
        ("LabAlley", "https://www.laballey.com/collections/ethylene-glycol"),
        ("LabAlley", "https://www.laballey.com/collections/hydrochloric-acid"),
        ("LabAlley", "https://www.laballey.com/collections/sodium-hydroxide"),
        ("LabAlley", "https://www.laballey.com/collections/sulfuric-acid"),
        ("LabAlley", "https://www.laballey.com/collections/acetic-acid"),
        ("LabAlley", "https://www.laballey.com/collections/citric-acid"),
        ("LabAlley", "https://www.laballey.com/collections/hydrogen-peroxide"),
        # Alliance Chemical — acids and solvents
        ("AllianceChemical", "https://www.alliancechemical.com/product-category/acids/"),
        ("AllianceChemical", "https://www.alliancechemical.com/product-category/water-treatment/"),
        # PFP Industries — oilfield specialty chemicals
        ("PFPIndustries", "https://www.pfpindustries.com/oilfiled-chemicals/specialty-oilfield-chemicals"),
        # Flatirons Chemicals — oilfield chemicals
        ("FlatironsChemicals", "https://flatironschemicals.com/"),
    ]

    import re

    for dist_name, url in targets:
        print(f"  {dist_name}: {url}...")
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code}")
                continue

            html = resp.text

            # Look for JSON-LD product data first (most reliable)
            import re as re2
            jsonld_matches = re2.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re2.DOTALL)
            for jsonld in jsonld_matches:
                try:
                    data = json.loads(jsonld)
                    products = []
                    if isinstance(data, list):
                        products = data
                    elif data.get("@type") in ("Product", "ItemList"):
                        if "itemListElement" in data:
                            products = data["itemListElement"]
                        else:
                            products = [data]

                    for prod in products:
                        item = prod.get("item", prod)
                        name = item.get("name", "")
                        offers = item.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price = offers.get("price")
                        currency = offers.get("priceCurrency", "USD")

                        if price and name:
                            records.append({
                                "product_name": str(name)[:200],
                                "product_category": "distributor_retail",
                                "price": float(price),
                                "price_unit": f"{currency}/each",
                                "source": f"{dist_name} (JSON-LD)",
                                "source_url": url,
                                "vendor": dist_name,
                                "confidence": 0.9,
                                "notes": f"Structured data from {dist_name}",
                            })
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass

            # Regex price extraction from HTML
            # Remove scripts/styles
            clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', clean)
            text = re.sub(r'\s+', ' ', text)

            # Price patterns
            price_patterns = [
                # "$XX.XX" near product-like text
                r'([A-Z][A-Za-z\s\-/()]{3,60}?)\s*[\$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(gal(?:lon)?|lb|kg|drum|tote|pail|each|unit|liter|case)?',
                # "Product - $XX.XX per gallon"
                r'([A-Z][A-Za-z\s\-/()]{3,60}?)\s*[-–]\s*[\$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:per|/)\s*(gal(?:lon)?|lb|kg|drum|tote|pail|each|unit|liter)',
            ]

            for pattern in price_patterns:
                for match in re.finditer(pattern, text):
                    name = match.group(1).strip()
                    price = float(match.group(2).replace(",", ""))
                    unit = match.group(3) or "each"

                    # Filter garbage
                    if price > 0 and price < 50000 and len(name) > 3 and not any(x in name.lower() for x in ["copyright", "phone", "fax", "address"]):
                        records.append({
                            "product_name": name[:200],
                            "product_category": "distributor_retail",
                            "price": price,
                            "price_unit": f"USD/{unit}",
                            "source": dist_name,
                            "source_url": url,
                            "vendor": dist_name,
                            "confidence": 0.75,
                            "notes": f"Regex extraction from {dist_name}",
                        })

            print(f"    Found {len([r for r in records if r['source'].startswith(dist_name)])} prices")

        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)

    print(f"  Total distributor records: {len(records)}")
    return records


# ─── KNOWN OILFIELD CHEMICAL BENCHMARK PRICES ────────────────────────────────
# Scraped from Lab Alley, Alliance Chemical, and market reports (March 2026)

def inject_benchmark_prices() -> list[dict]:
    """Inject known benchmark pricing for key oilfield chemicals."""
    print("\n=== Benchmark Chemical Prices ===")
    benchmarks = [
        # Methanol — used for hydrate inhibition, gas dehydration
        {"product_name": "Methanol 99.85% Lab Grade - 55 Gallon Drum", "product_category": "methanol", "price": 505.56, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/methanol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Retail benchmark — $9.19/gal. Bulk oilfield pricing ~$2-4/gal"},
        {"product_name": "Methanol 99.85% Lab Grade - 270 Gallon Tote", "product_category": "methanol", "price": 2122.22, "price_unit": "USD/270gal tote", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/methanol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Retail benchmark — $7.86/gal. Bulk oilfield pricing ~$1.50-3/gal"},
        {"product_name": "Methanol ACS Reagent Grade - 55 Gallon Drum", "product_category": "methanol", "price": 806.19, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/methanol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "ACS grade retail — $14.66/gal"},
        {"product_name": "Methanol HPLC Grade - 55 Gallon Drum", "product_category": "methanol", "price": 1654.05, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/methanol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "HPLC grade premium — $30.07/gal"},
        # Ethylene Glycol — used for gas dehydration, hydrate prevention
        {"product_name": "Ethylene Glycol 99% Lab Grade - 55 Gallon Drum", "product_category": "glycol", "price": 769.11, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/ethylene-glycol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Retail benchmark — $13.98/gal. Bulk oilfield ~$5-8/gal"},
        {"product_name": "Ethylene Glycol 99% Lab Grade - 5 Gallon Pail", "product_category": "glycol", "price": 170.66, "price_unit": "USD/5gal pail", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/ethylene-glycol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Retail — $34.13/gal"},
        {"product_name": "Ethylene Glycol 99% ACS Grade - 5 Gallon Pail", "product_category": "glycol", "price": 285.86, "price_unit": "USD/5gal pail", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/ethylene-glycol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "ACS grade retail — $57.17/gal"},
        {"product_name": "Ethylene Glycol 30% Solution - 55 Gallon Drum", "product_category": "glycol", "price": 766.30, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/ethylene-glycol", "vendor": "Lab Alley", "confidence": 0.95, "notes": "30% solution — $13.93/gal"},
        # Hydrochloric Acid — used in acidizing, well stimulation
        {"product_name": "Hydrochloric Acid 37% ACS Grade - 55 Gallon Drum", "product_category": "hydrochloric_acid", "price": 1985.43, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/hydrochloric-acid", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Retail benchmark — $36.10/gal. Bulk oilfield 15% HCl ~$0.50-1.50/gal"},
        {"product_name": "Hydrochloric Acid 31% Lab Grade - 55 Gallon Drum", "product_category": "hydrochloric_acid", "price": 523.62, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/hydrochloric-acid", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Lab grade retail — $9.52/gal"},
        {"product_name": "Hydrochloric Acid 10% Lab Grade - 55 Gallon Drum", "product_category": "hydrochloric_acid", "price": 523.62, "price_unit": "USD/55gal drum", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/hydrochloric-acid", "vendor": "Lab Alley", "confidence": 0.95, "notes": "10% solution — $9.52/gal"},
        {"product_name": "Hydrochloric Acid 5% in Denatured Alcohol - 5 Gallon", "product_category": "hydrochloric_acid", "price": 402.60, "price_unit": "USD/5gal", "source": "LabAlley.com", "source_url": "https://www.laballey.com/collections/hydrochloric-acid", "vendor": "Lab Alley", "confidence": 0.95, "notes": "Specialty blend — $80.52/gal"},
        # Market benchmark estimates for oilfield-specific chemicals
        {"product_name": "Corrosion Inhibitor (film-forming amine) - Bulk", "product_category": "corrosion_inhibitor", "price": 15.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Typical oilfield corrosion inhibitor $8-25/gal depending on concentration and application"},
        {"product_name": "Scale Inhibitor (phosphonate-based) - Bulk", "product_category": "scale_inhibitor", "price": 20.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Typical scale inhibitor $12-35/gal. Premium formulations up to $50/gal"},
        {"product_name": "Biocide (glutaraldehyde-based) - Bulk", "product_category": "biocide", "price": 12.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Typical biocide $6-20/gal. THPS-based premium $15-30/gal"},
        {"product_name": "Demulsifier - Bulk", "product_category": "demulsifier", "price": 18.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Typical demulsifier $10-30/gal. Customized formulations higher"},
        {"product_name": "H2S Scavenger (triazine-based) - Bulk", "product_category": "h2s_scavenger", "price": 8.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Triazine scavenger $4-15/gal. MEA-triazine is cheapest"},
        {"product_name": "Paraffin Inhibitor - Bulk", "product_category": "paraffin_inhibitor", "price": 22.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Paraffin/wax inhibitor $15-35/gal"},
        {"product_name": "Oxygen Scavenger (sodium bisulfite) - Bulk", "product_category": "oxygen_scavenger", "price": 5.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Sodium bisulfite $3-8/gal. Catalyzed versions $6-12/gal"},
        {"product_name": "Surfactant (nonionic) - Bulk", "product_category": "surfactant", "price": 14.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Nonionic surfactant $8-25/gal. Specialty $20-50/gal"},
        {"product_name": "Friction Reducer (polyacrylamide) - Bulk", "product_category": "friction_reducer", "price": 3.50, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "FR $1.50-6/gal. High-viscosity premium $5-10/gal"},
        {"product_name": "Clay Stabilizer (KCl substitute) - Bulk", "product_category": "clay_stabilizer", "price": 10.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Clay stabilizer $5-18/gal"},
        {"product_name": "Iron Control Agent (citric acid blend) - Bulk", "product_category": "iron_control", "price": 16.00, "price_unit": "USD/gallon", "source": "Industry Estimate", "vendor": "Market Average", "confidence": 0.6, "notes": "Iron control $8-25/gal"},
        # ChampionX product catalog (no pricing — product intelligence)
        {"product_name": "ChampionX - Drilling Fluid & Mud Additives", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Well Construction category. No public pricing."},
        {"product_name": "ChampionX - Acidizing Chemicals", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Well Completion category. No public pricing."},
        {"product_name": "ChampionX - Fracturing Chemicals", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Complete portfolio of well stimulation additives. No public pricing."},
        {"product_name": "ChampionX - Asset Integrity (Corrosion/Scale)", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Corrosion inhibitors, scale treatment. No public pricing."},
        {"product_name": "ChampionX - Flow Assurance", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Wax/asphaltene/hydrate control. No public pricing."},
        {"product_name": "ChampionX - UltraFab H2S Removal Systems", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Midstream H2S removal. No public pricing."},
        {"product_name": "ChampionX - RenewIQ Water Treatment Program", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "Produced water lifecycle management. No public pricing."},
        {"product_name": "ChampionX - Enhanced Oil Recovery Services", "product_category": "competitor_product", "price": 0, "price_unit": "RFQ", "source": "championx.com", "source_url": "https://www.championx.com/products-and-solutions/chemical-technologies/", "vendor": "Champion X", "confidence": 0.5, "notes": "EOR surfactants, polymers. No public pricing."},
    ]
    print(f"  {len(benchmarks)} benchmark records")
    return benchmarks


# ─── PUSH TO WORKER ──────────────────────────────────────────────────────────

def push_all_to_worker(records: list[dict]):
    """Push pricing records to the worker's D1 database."""
    print(f"\n=== Pushing {len(records)} records to Worker ===")

    # Batch in chunks of 50
    total_pushed = 0
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        try:
            resp = requests.post(
                f"{WORKER_URL}/ingest-pricing",
                json={"records": batch},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                pushed = data.get("inserted", 0)
                total_pushed += pushed
                print(f"  Batch {i//50 + 1}: {pushed} inserted")
            else:
                print(f"  Batch {i//50 + 1}: HTTP {resp.status_code} — {resp.text[:200]}")
        except Exception as e:
            print(f"  Batch {i//50 + 1}: Error — {e}")
        time.sleep(0.5)

    print(f"  Total pushed: {total_pushed}")
    return total_pushed


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Permian Pulse Pricing Collector — {datetime.now().isoformat()}")
    print(f"Worker: {WORKER_URL}")

    all_records = []

    # Collect from all sources
    all_records.extend(collect_usaspending())
    all_records.extend(collect_distributor_pricing())
    all_records.extend(inject_benchmark_prices())

    # Deduplicate by contract_number + vendor
    seen = set()
    unique = []
    for r in all_records:
        key = f"{r.get('contract_number', '')}_{r.get('vendor', '')}_{r.get('product_name', '')}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\n=== SUMMARY ===")
    print(f"Total collected: {len(all_records)}")
    print(f"Unique records: {len(unique)}")

    # Save locally
    output_path = Path(__file__).parent / "pricing_data.json"
    with open(output_path, "w") as f:
        json.dump(unique, f, indent=2, default=str)
    print(f"Saved to: {output_path}")

    # Push to worker
    if unique:
        push_all_to_worker(unique)

    print(f"\nDone. {datetime.now().isoformat()}")
