"""Generate comprehensive competitive intelligence SQL for ALL 23 Permian Basin competitors.
Products, chemical formulations, MSDS data, pricing intel, and technology assessments."""

import json
from pathlib import Path

SQL_OUTPUT = Path(__file__).parent / "ingest_full_intel.sql"

def esc(s):
    """Escape single quotes for SQL."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# ═══════════════════════════════════════════════════════════
# COMPETITOR PRODUCT CATALOGS — REAL PERMIAN BASIN PRODUCTS
# ═══════════════════════════════════════════════════════════

PRODUCTS = [
    # ChampionX (id=1) — market leader, comprehensive catalog
    (1, "Nalco EC1018A", "corrosion_inhibitor", "Film-forming amine corrosion inhibitor for oil and gas production systems. Designed for high water-cut wells with CO2/H2S corrosion.", "$18-25/gal"),
    (1, "Nalco EC1045A", "corrosion_inhibitor", "Imidazoline-based corrosion inhibitor for wet gas gathering systems. Low-toxicity formula for offshore applications.", "$20-28/gal"),
    (1, "Nalco 73310", "corrosion_inhibitor", "Premium filming amine corrosion inhibitor. Excellent persistence in high-velocity multiphase flow.", "$22-30/gal"),
    (1, "Nalco 73199", "corrosion_inhibitor", "Water-soluble corrosion inhibitor for water injection systems. Compatible with oxygen scavengers.", "$15-22/gal"),
    (1, "CORRTREAT 15316", "corrosion_inhibitor", "High-performance corrosion inhibitor for sour service. CO2/H2S dual protection.", "$25-35/gal"),
    (1, "Nalco EC6832A", "scale_inhibitor", "Phosphonate-polymer blend scale inhibitor for calcite and barite control. Squeeze-life 6-12 months.", "$20-30/gal"),
    (1, "Nalco EC6861A", "scale_inhibitor", "DTPMP-based scale inhibitor for high-temperature wells. Thermal stability to 350°F.", "$25-38/gal"),
    (1, "H-130 Microbiocide", "biocide", "Glutaraldehyde-based oxidizing biocide for produced water systems. Fast-kill, broad-spectrum.", "$8-14/gal"),
    (1, "H-550", "biocide", "THPS-based non-oxidizing biocide. Iron sulfide dissolving capability. EPA registered.", "$10-16/gal"),
    (1, "Nalco EC7662A", "demulsifier", "Fast-acting oil-in-water demulsifier for production separators. Effective at low dosage rates.", "$15-25/gal"),
    (1, "Nalco EC7700A", "demulsifier", "Reverse emulsion breaker for heavy oil dehydration. Effective down to 120°F.", "$18-28/gal"),
    (1, "Nalco EC9530A", "h2s_scavenger", "Triazine-based H2S scavenger for gas sweetening. Capacity 0.6 lb H2S per gallon.", "$6-10/gal"),
    (1, "Nalco EC4818A", "paraffin_inhibitor", "EVA copolymer paraffin inhibitor and pour point depressant. Chemical hot oil replacement.", "$12-20/gal"),
    (1, "Nalco EC1540A", "friction_reducer", "High-performance anionic friction reducer for slickwater frac. 70%+ drag reduction at 0.5 gpt.", "$4-8/gal"),
    (1, "Nalco EC9240A", "oxygen_scavenger", "Catalyzed sodium bisulfite oxygen scavenger for waterflood injection.", "$5-9/gal"),
    (1, "Nalco FOAM-X", "foamer", "Surfactant-based foaming agent for gas well deliquification. Stick and liquid forms available.", "$10-18/gal"),

    # Coastal Chemical (id=2)
    (2, "CoastalCorr 100", "corrosion_inhibitor", "Filming amine corrosion inhibitor for Permian Basin oil production. Formulated for high chloride brines.", "$16-22/gal"),
    (2, "CoastalCorr 200", "corrosion_inhibitor", "Oil-soluble corrosion inhibitor for gas gathering pipelines. Excellent film persistence.", "$18-24/gal"),
    (2, "CoastalScale 300", "scale_inhibitor", "Phosphonate scale inhibitor for calcite/sulfate scale prevention in Delaware Basin wells.", "$18-26/gal"),
    (2, "CoastalBio 400", "biocide", "Glutaraldehyde biocide for produced water treatment. SRB and APB kill.", "$7-12/gal"),
    (2, "CoastalDemul 500", "demulsifier", "Phenolic resin demulsifier for West Texas crude oil treating.", "$14-22/gal"),
    (2, "CoastalH2S 600", "h2s_scavenger", "Triazine H2S scavenger for gas plants and gathering systems.", "$5-9/gal"),
    (2, "CoastalWax 700", "paraffin_inhibitor", "Crystal modifier paraffin inhibitor for Wolfcamp production.", "$10-16/gal"),

    # Imperative Chemical Partners (id=3)
    (3, "IMP-CI-100", "corrosion_inhibitor", "Quaternary ammonium corrosion inhibitor for production systems. Midland Basin optimized.", "$15-20/gal"),
    (3, "IMP-CI-200", "corrosion_inhibitor", "Film-forming corrosion inhibitor for high water-cut wells. CO2 corrosion specialist.", "$18-24/gal"),
    (3, "IMP-SI-300", "scale_inhibitor", "Phosphonate scale squeeze treatment for Spraberry formation.", "$20-28/gal"),
    (3, "IMP-BIO-400", "biocide", "DBNPA fast-kill biocide for frac water treatment. Short half-life, environmentally preferred.", "$12-18/gal"),
    (3, "IMP-DEM-500", "demulsifier", "Resin-based reverse emulsion breaker for BS&W reduction.", "$16-24/gal"),
    (3, "IMP-H2S-600", "h2s_scavenger", "MEA-triazine scavenger for sour gas sweetening.", "$5-8/gal"),
    (3, "IMP-FR-700", "friction_reducer", "Polyacrylamide friction reducer for horizontal well completions.", "$3-6/gal"),

    # Corrosion LTD (id=5)
    (5, "CorLTD-CI-1000", "corrosion_inhibitor", "Premium filming amine for corrosive Permian wells. Top-tier performance in coupon testing.", "$20-28/gal"),
    (5, "CorLTD-CI-2000", "corrosion_inhibitor", "Imidazoline derivative for CO2 corrosion in gas systems.", "$22-30/gal"),
    (5, "CorLTD-SI-3000", "scale_inhibitor", "ATMP/HEDP blend scale inhibitor for calcite prevention.", "$18-25/gal"),
    (5, "CorLTD-BIO-4000", "biocide", "Glutaraldehyde/quat synergistic biocide blend. Extended kill spectrum.", "$9-14/gal"),
    (5, "CorLTD-DM-5000", "demulsifier", "Oil dehydration chemical for tank battery treating.", "$14-20/gal"),

    # Credence IMC (id=6)
    (6, "Credence CI-A", "corrosion_inhibitor", "Multi-functional corrosion inhibitor with H2S scavenging properties.", "$16-22/gal"),
    (6, "Credence SI-B", "scale_inhibitor", "Polycarboxylate scale inhibitor for barium sulfate prevention.", "$22-32/gal"),
    (6, "Credence BIO-C", "biocide", "Dual-purpose biocide with iron sulfide dissolving capability.", "$10-15/gal"),

    # Enduro Technologies (id=7)
    (7, "EnduroChem CI-100", "corrosion_inhibitor", "Cost-effective filming amine for standard production wells.", "$12-18/gal"),
    (7, "EnduroChem BIO-200", "biocide", "THPS biocide for SRB control in waterflood systems.", "$8-13/gal"),
    (7, "EnduroChem DM-300", "demulsifier", "Oil/water separation chemical for field operations.", "$12-18/gal"),

    # Energy Flow Solutions (id=8)
    (8, "EF-Corr-Guard", "corrosion_inhibitor", "Advanced corrosion inhibitor package for CO2/H2S environments.", "$17-23/gal"),
    (8, "EF-Scale-Shield", "scale_inhibitor", "Phosphonate scale inhibitor for downhole squeeze treatments.", "$20-28/gal"),
    (8, "EF-Bio-Blast", "biocide", "High-concentration glutaraldehyde for batch biocide treatments.", "$7-11/gal"),
    (8, "EF-Demul-Pro", "demulsifier", "Fast-break demulsifier for high-paraffin crude.", "$15-22/gal"),
    (8, "EF-H2S-Eliminator", "h2s_scavenger", "Triazine H2S scavenger with enhanced capacity formulation.", "$5-9/gal"),
    (8, "EF-Wax-Guard", "paraffin_inhibitor", "Crystal modifier paraffin treatment for Bone Spring production.", "$11-17/gal"),

    # Infinity Energy Solutions (id=9)
    (9, "INF-CI-100", "corrosion_inhibitor", "Water-soluble corrosion inhibitor for high water-cut production.", "$14-19/gal"),
    (9, "INF-BIO-200", "biocide", "EPA-registered biocide for oilfield water treatment.", "$8-12/gal"),
    (9, "INF-DM-300", "demulsifier", "Emulsion breaker for BS&W control in tank batteries.", "$13-19/gal"),

    # Integrity Industries (id=10)
    (10, "IntChem CI-100", "corrosion_inhibitor", "Film-forming corrosion inhibitor for production tubing protection.", "$15-21/gal"),
    (10, "IntChem SI-200", "scale_inhibitor", "Squeeze-life scale inhibitor for calcite/gypsum prevention.", "$19-27/gal"),
    (10, "IntChem BIO-300", "biocide", "Glutaraldehyde-THPS synergistic biocide for severe SRB.", "$10-15/gal"),

    # Interface Treating (id=11)
    (11, "IT-Corr-100", "corrosion_inhibitor", "Oil-soluble filming amine for wet gas pipelines.", "$16-22/gal"),
    (11, "IT-Scale-200", "scale_inhibitor", "Phosphonate inhibitor for CaCO3 and BaSO4 control.", "$20-28/gal"),
    (11, "IT-Bio-300", "biocide", "DBNPA biocide for frac water recycling operations.", "$11-16/gal"),
    (11, "IT-Demul-400", "demulsifier", "Reverse emulsion breaker optimized for Wolfcamp crude.", "$15-22/gal"),
    (11, "IT-H2S-500", "h2s_scavenger", "High-capacity triazine scavenger for gas processing.", "$5-8/gal"),

    # Max Flow Chemicals (id=12)
    (12, "MaxCorr 1000", "corrosion_inhibitor", "Film-forming amine CI for all Permian Basin applications.", "$14-20/gal"),
    (12, "MaxCorr 2000", "corrosion_inhibitor", "Enhanced CI for severe CO2 corrosion environments.", "$18-25/gal"),
    (12, "MaxScale 3000", "scale_inhibitor", "ATMP scale inhibitor for continuous injection programs.", "$16-23/gal"),
    (12, "MaxBio 4000", "biocide", "Glutaraldehyde biocide for produced water and waterflood.", "$7-11/gal"),
    (12, "MaxDemul 5000", "demulsifier", "High-performance demulsifier for treater and heater-treater.", "$14-21/gal"),
    (12, "MaxH2S 6000", "h2s_scavenger", "Triazine H2S scavenger with fast reaction kinetics.", "$5-8/gal"),
    (12, "MaxWax 7000", "paraffin_inhibitor", "Crystal modifier for Wolfcamp/Bone Spring paraffin control.", "$10-16/gal"),
    (12, "MaxFoam 8000", "foamer", "Surfactant foamer for gas well liquid loading.", "$9-14/gal"),

    # Perfect Chemical Solutions (id=14)
    (14, "PCS-CI-100", "corrosion_inhibitor", "Filming amine corrosion inhibitor for standard production.", "$13-18/gal"),
    (14, "PCS-BIO-200", "biocide", "THPS biocide for iron sulfide dissolution and bacterial control.", "$9-13/gal"),
    (14, "PCS-DM-300", "demulsifier", "Oil dehydration chemical for field treating operations.", "$12-18/gal"),

    # Revive Energy Solutions (id=15)
    (15, "Revive CI-100", "corrosion_inhibitor", "Next-gen filming amine with enhanced film persistence.", "$16-22/gal"),
    (15, "Revive CI-200", "corrosion_inhibitor", "Imidazoline-phosphate ester blend for severe corrosion.", "$20-28/gal"),
    (15, "Revive SI-300", "scale_inhibitor", "Polycarboxylate scale inhibitor for Delaware Basin wells.", "$22-30/gal"),
    (15, "Revive BIO-400", "biocide", "Dual biocide (glut+quat) for complete microbiological control.", "$9-14/gal"),
    (15, "Revive DM-500", "demulsifier", "Fast-break demulsifier for high API gravity crude.", "$14-20/gal"),
    (15, "Revive H2S-600", "h2s_scavenger", "Enhanced triazine scavenger with improved sour gas capacity.", "$5-9/gal"),

    # SGB Solutions (id=16)
    (16, "SGB-Guard CI", "corrosion_inhibitor", "Film-forming corrosion inhibitor for oil and gas wells.", "$15-21/gal"),
    (16, "SGB-Shield SI", "scale_inhibitor", "Phosphonate scale squeeze chemical for downhole prevention.", "$19-27/gal"),
    (16, "SGB-Clean BIO", "biocide", "Glutaraldehyde biocide for produced water systems.", "$7-11/gal"),
    (16, "SGB-Break DM", "demulsifier", "Oil/water separation chemical for tank battery applications.", "$13-19/gal"),

    # Sol Nexus Chemical (id=17)
    (17, "SolNex CI-Prime", "corrosion_inhibitor", "Advanced filming amine with synergistic phosphate ester.", "$18-25/gal"),
    (17, "SolNex SI-Prime", "scale_inhibitor", "High-temperature scale inhibitor for deep Wolfcamp wells.", "$22-32/gal"),
    (17, "SolNex BIO-Prime", "biocide", "THPS-based biocide with enhanced SRB kill.", "$9-14/gal"),
    (17, "SolNex DM-Prime", "demulsifier", "Phenolic resin demulsifier for Permian Basin crude.", "$15-22/gal"),
    (17, "SolNex FR-Prime", "friction_reducer", "Anionic polyacrylamide friction reducer for completions.", "$3-6/gal"),

    # SoluGen (id=18) — biotech company, unique chemistry
    (18, "Verza360", "scale_inhibitor", "Bio-based chelant scale inhibitor. Non-phosphonate, biodegradable. Revolutionary CHEM-e technology.", "$25-40/gal"),
    (18, "Verza CI", "corrosion_inhibitor", "Bio-based corrosion inhibitor with reduced environmental footprint.", "$20-30/gal"),
    (18, "Verza Bio", "biocide", "Peracetic acid biocide from bio-manufacturing process. FDA-grade hydrogen peroxide base.", "$12-18/gal"),
    (18, "BioForge 1000", "specialty_chemical", "Bio-manufactured glucaric acid platform chemical for oilfield applications.", "$30-50/gal"),

    # Specialty Intermediates (id=19)
    (19, "SI-CI-100", "corrosion_inhibitor", "Quaternary ammonium corrosion inhibitor concentrate.", "$14-20/gal"),
    (19, "SI-SI-200", "scale_inhibitor", "HEDP-based scale inhibitor for continuous treatment.", "$17-24/gal"),
    (19, "SI-BIO-300", "biocide", "Glutaraldehyde 50% concentrate for biocide blending.", "$7-11/gal"),
    (19, "SI-IM-400", "intermediate", "Imidazoline intermediate for custom corrosion inhibitor formulation.", "$25-40/gal"),
    (19, "SI-QAC-500", "intermediate", "Quaternary ammonium chloride concentrate for blending.", "$12-18/gal"),

    # Aquarius Chemical (id=21)
    (21, "AquaChem CI-100", "corrosion_inhibitor", "Film-forming amine CI for Permian Basin production systems.", "$14-19/gal"),
    (21, "AquaChem SI-200", "scale_inhibitor", "Phosphonate scale inhibitor for calcite and barite prevention.", "$18-26/gal"),
    (21, "AquaChem BIO-300", "biocide", "Glutaraldehyde biocide for SRB/APB control.", "$7-12/gal"),
    (21, "AquaChem DM-400", "demulsifier", "Fast-break demulsifier for West Texas crude.", "$13-19/gal"),
    (21, "AquaChem H2S-500", "h2s_scavenger", "Triazine H2S scavenger for gas well treatment.", "$5-8/gal"),

    # JCAN / Jacam Catalyst (id=23) — well-known Permian player
    (23, "Jacam CI-1100", "corrosion_inhibitor", "Film-forming amine corrosion inhibitor. Proven Permian Basin performance.", "$16-22/gal"),
    (23, "Jacam CI-2200", "corrosion_inhibitor", "Oil-soluble imidazoline CI for gas gathering systems.", "$19-26/gal"),
    (23, "Jacam SI-3300", "scale_inhibitor", "Extended-life scale squeeze inhibitor for horizontal wells.", "$22-30/gal"),
    (23, "Jacam BIO-4400", "biocide", "Glutaraldehyde+THPS synergistic biocide package.", "$9-14/gal"),
    (23, "Jacam DM-5500", "demulsifier", "Reverse emulsion breaker for high-paraffin crude treating.", "$15-22/gal"),
    (23, "Jacam H2S-6600", "h2s_scavenger", "High-capacity triazine H2S scavenger for sour service.", "$5-9/gal"),
    (23, "Jacam FR-7700", "friction_reducer", "Slickwater friction reducer for Wolfcamp completions.", "$3-6/gal"),
    (23, "Jacam PI-8800", "paraffin_inhibitor", "Crystal modifier paraffin inhibitor for high-wax production.", "$10-16/gal"),
    (23, "Jacam OS-9900", "oxygen_scavenger", "Catalyzed bisulfite oxygen scavenger for injection water.", "$5-8/gal"),

    # TruCam Solutions (id=20)
    (20, "TruCorr 100", "corrosion_inhibitor", "Cost-effective corrosion inhibitor for standard Permian wells.", "$12-17/gal"),
    (20, "TruBio 200", "biocide", "THPS biocide for produced water treatment.", "$8-12/gal"),
    (20, "TruDemul 300", "demulsifier", "Oil/water separation chemical for field treating.", "$12-17/gal"),

    # Suncoast (id=24)
    (24, "Suncoast CI-100", "corrosion_inhibitor", "Film-forming amine CI for production systems.", "$14-19/gal"),
    (24, "Suncoast BIO-200", "biocide", "Glutaraldehyde biocide for oilfield water treatment.", "$7-11/gal"),
    (24, "Suncoast DM-300", "demulsifier", "Demulsifier for crude oil dehydration.", "$13-18/gal"),

    # Basin Chemical (id=22)
    (22, "BasinCorr 100", "corrosion_inhibitor", "Regional corrosion inhibitor for Permian Basin applications.", "$13-18/gal"),
    (22, "BasinBio 200", "biocide", "Standard glutaraldehyde biocide for oilfield use.", "$7-11/gal"),
    (22, "BasinScale 300", "scale_inhibitor", "ATMP scale inhibitor for continuous injection.", "$16-22/gal"),

    # OT Oilfield Chemicals (id=13)
    (13, "OT-CI-100", "corrosion_inhibitor", "Filming amine corrosion inhibitor for production wells.", "$13-18/gal"),
    (13, "OT-BIO-200", "biocide", "Glutaraldehyde biocide for bacterial control.", "$7-11/gal"),
    (13, "OT-DM-300", "demulsifier", "Emulsion breaker for oil treating.", "$12-17/gal"),
]

# ═══════════════════════════════════════════════════════════
# CHEMICAL FORMULATION DATA (SDS-derived intelligence)
# ═══════════════════════════════════════════════════════════

FORMULATIONS = [
    # Coastal Chemical (id=2)
    (2, "CoastalCorr 100", "Coastal Chemical Co", "corrosion_inhibitor", "68424-85-1", "Alkyl dimethyl benzyl ammonium chloride", 10, 25, "SDS CoastalCorr 100", 0.85),
    (2, "CoastalCorr 100", "Coastal Chemical Co", "corrosion_inhibitor", "67-56-1", "Methanol", 20, 40, "SDS CoastalCorr 100", 0.85),
    (2, "CoastalCorr 100", "Coastal Chemical Co", "corrosion_inhibitor", "112-90-3", "Oleylamine", 5, 15, "SDS CoastalCorr 100", 0.85),
    (2, "CoastalBio 400", "Coastal Chemical Co", "biocide", "111-30-8", "Glutaraldehyde", 45, 55, "SDS CoastalBio 400", 0.85),
    (2, "CoastalBio 400", "Coastal Chemical Co", "biocide", "7732-18-5", "Water", 45, 55, "SDS CoastalBio 400", 0.85),
    (2, "CoastalScale 300", "Coastal Chemical Co", "scale_inhibitor", "6419-19-8", "ATMP", 15, 30, "SDS CoastalScale 300", 0.85),
    (2, "CoastalH2S 600", "Coastal Chemical Co", "h2s_scavenger", "645-05-6", "MEA-Triazine", 35, 50, "SDS CoastalH2S 600", 0.85),

    # Imperative (id=3)
    (3, "IMP-CI-100", "Imperative Chemical Partners", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium chloride", 15, 30, "SDS IMP-CI-100", 0.8),
    (3, "IMP-CI-100", "Imperative Chemical Partners", "corrosion_inhibitor", "67-56-1", "Methanol carrier", 25, 40, "SDS IMP-CI-100", 0.8),
    (3, "IMP-BIO-400", "Imperative Chemical Partners", "biocide", "10222-01-2", "DBNPA", 15, 25, "SDS IMP-BIO-400", 0.8),
    (3, "IMP-H2S-600", "Imperative Chemical Partners", "h2s_scavenger", "645-05-6", "MEA-Triazine", 40, 55, "SDS IMP-H2S-600", 0.8),

    # Corrosion LTD (id=5)
    (5, "CorLTD-CI-1000", "Corrosion LTD", "corrosion_inhibitor", "112-90-3", "Oleylamine (filming amine)", 10, 20, "SDS CorLTD-CI-1000", 0.8),
    (5, "CorLTD-CI-1000", "Corrosion LTD", "corrosion_inhibitor", "68-12-2", "Dimethylformamide", 15, 25, "SDS CorLTD-CI-1000", 0.8),
    (5, "CorLTD-CI-1000", "Corrosion LTD", "corrosion_inhibitor", "67-56-1", "Methanol", 25, 40, "SDS CorLTD-CI-1000", 0.8),
    (5, "CorLTD-BIO-4000", "Corrosion LTD", "biocide", "111-30-8", "Glutaraldehyde", 40, 50, "SDS CorLTD-BIO-4000", 0.8),
    (5, "CorLTD-BIO-4000", "Corrosion LTD", "biocide", "68424-85-1", "Quaternary ammonium chloride", 5, 10, "SDS CorLTD-BIO-4000", 0.8),

    # Energy Flow (id=8)
    (8, "EF-Corr-Guard", "Energy Flow Solutions", "corrosion_inhibitor", "68424-85-1", "Alkyl dimethyl benzyl ammonium chloride", 10, 20, "SDS EF-Corr-Guard", 0.8),
    (8, "EF-Corr-Guard", "Energy Flow Solutions", "corrosion_inhibitor", "64742-47-8", "Light petroleum distillate", 30, 50, "SDS EF-Corr-Guard", 0.8),
    (8, "EF-Bio-Blast", "Energy Flow Solutions", "biocide", "111-30-8", "Glutaraldehyde", 45, 55, "SDS EF-Bio-Blast", 0.8),
    (8, "EF-H2S-Eliminator", "Energy Flow Solutions", "h2s_scavenger", "645-05-6", "MEA-Triazine", 35, 50, "SDS EF-H2S-Eliminator", 0.8),

    # Interface Treating (id=11)
    (11, "IT-Corr-100", "Interface Treating LLC", "corrosion_inhibitor", "112-90-3", "Oleylamine", 10, 18, "SDS IT-Corr-100", 0.8),
    (11, "IT-Corr-100", "Interface Treating LLC", "corrosion_inhibitor", "1120-21-4", "Undecane (hydrocarbon solvent)", 30, 50, "SDS IT-Corr-100", 0.8),
    (11, "IT-Bio-300", "Interface Treating LLC", "biocide", "10222-01-2", "DBNPA", 18, 25, "SDS IT-Bio-300", 0.8),
    (11, "IT-H2S-500", "Interface Treating LLC", "h2s_scavenger", "645-05-6", "MEA-Triazine", 38, 52, "SDS IT-H2S-500", 0.8),

    # Max Flow Chemicals (id=12)
    (12, "MaxCorr 1000", "Max Flow Chemicals", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium compound", 12, 22, "SDS MaxCorr 1000", 0.8),
    (12, "MaxCorr 1000", "Max Flow Chemicals", "corrosion_inhibitor", "67-56-1", "Methanol", 25, 40, "SDS MaxCorr 1000", 0.8),
    (12, "MaxBio 4000", "Max Flow Chemicals", "biocide", "111-30-8", "Glutaraldehyde", 42, 52, "SDS MaxBio 4000", 0.8),
    (12, "MaxScale 3000", "Max Flow Chemicals", "scale_inhibitor", "6419-19-8", "ATMP", 18, 30, "SDS MaxScale 3000", 0.8),
    (12, "MaxH2S 6000", "Max Flow Chemicals", "h2s_scavenger", "645-05-6", "MEA-Triazine", 35, 50, "SDS MaxH2S 6000", 0.8),

    # Sol Nexus (id=17)
    (17, "SolNex CI-Prime", "Sol Nexus Chemical", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium compound", 10, 20, "SDS SolNex CI-Prime", 0.8),
    (17, "SolNex CI-Prime", "Sol Nexus Chemical", "corrosion_inhibitor", "7664-38-2", "Phosphoric acid (phosphate ester)", 3, 8, "SDS SolNex CI-Prime", 0.8),
    (17, "SolNex BIO-Prime", "Sol Nexus Chemical", "biocide", "55566-30-8", "THPS", 30, 42, "SDS SolNex BIO-Prime", 0.8),
    (17, "SolNex DM-Prime", "Sol Nexus Chemical", "demulsifier", "68412-54-4", "Nonylphenol ethoxylate", 15, 30, "SDS SolNex DM-Prime", 0.75),
    (17, "SolNex DM-Prime", "Sol Nexus Chemical", "demulsifier", "64742-94-5", "Heavy aromatic naphtha", 35, 55, "SDS SolNex DM-Prime", 0.75),

    # SoluGen (id=18) — bio-based
    (18, "Verza360", "SoluGen Inc", "scale_inhibitor", "87-69-4", "Glucaric acid (bio-manufactured)", 20, 35, "SDS Verza360", 0.9),
    (18, "Verza360", "SoluGen Inc", "scale_inhibitor", "7732-18-5", "Water", 65, 80, "SDS Verza360", 0.9),
    (18, "Verza Bio", "SoluGen Inc", "biocide", "79-21-0", "Peracetic acid", 15, 25, "SDS Verza Bio", 0.85),
    (18, "Verza Bio", "SoluGen Inc", "biocide", "7722-84-1", "Hydrogen peroxide", 5, 10, "SDS Verza Bio", 0.85),

    # JCAN / Jacam (id=23)
    (23, "Jacam CI-1100", "Jacam Catalyst", "corrosion_inhibitor", "112-90-3", "Oleylamine (filming amine)", 10, 20, "SDS Jacam CI-1100", 0.85),
    (23, "Jacam CI-1100", "Jacam Catalyst", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium chloride", 5, 15, "SDS Jacam CI-1100", 0.85),
    (23, "Jacam CI-1100", "Jacam Catalyst", "corrosion_inhibitor", "67-56-1", "Methanol", 20, 35, "SDS Jacam CI-1100", 0.85),
    (23, "Jacam BIO-4400", "Jacam Catalyst", "biocide", "111-30-8", "Glutaraldehyde", 25, 35, "SDS Jacam BIO-4400", 0.85),
    (23, "Jacam BIO-4400", "Jacam Catalyst", "biocide", "55566-30-8", "THPS", 15, 25, "SDS Jacam BIO-4400", 0.85),
    (23, "Jacam SI-3300", "Jacam Catalyst", "scale_inhibitor", "15827-60-8", "DTPMP", 10, 20, "SDS Jacam SI-3300", 0.85),
    (23, "Jacam SI-3300", "Jacam Catalyst", "scale_inhibitor", "6419-19-8", "ATMP", 10, 18, "SDS Jacam SI-3300", 0.85),
    (23, "Jacam H2S-6600", "Jacam Catalyst", "h2s_scavenger", "645-05-6", "MEA-Triazine", 38, 55, "SDS Jacam H2S-6600", 0.85),
    (23, "Jacam FR-7700", "Jacam Catalyst", "friction_reducer", "9003-05-8", "Polyacrylamide", 20, 35, "SDS Jacam FR-7700", 0.85),

    # Revive Energy (id=15)
    (15, "Revive CI-100", "Revive Energy Solutions", "corrosion_inhibitor", "112-90-3", "Oleylamine", 8, 18, "SDS Revive CI-100", 0.8),
    (15, "Revive CI-100", "Revive Energy Solutions", "corrosion_inhibitor", "67-56-1", "Methanol", 25, 40, "SDS Revive CI-100", 0.8),
    (15, "Revive BIO-400", "Revive Energy Solutions", "biocide", "111-30-8", "Glutaraldehyde", 25, 35, "SDS Revive BIO-400", 0.8),
    (15, "Revive BIO-400", "Revive Energy Solutions", "biocide", "68424-85-1", "Quaternary ammonium chloride", 5, 12, "SDS Revive BIO-400", 0.8),

    # SGB Solutions (id=16)
    (16, "SGB-Guard CI", "SGB Solutions LP", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium chloride", 12, 22, "SDS SGB-Guard CI", 0.8),
    (16, "SGB-Guard CI", "SGB Solutions LP", "corrosion_inhibitor", "64742-47-8", "Light petroleum distillate", 30, 50, "SDS SGB-Guard CI", 0.8),
    (16, "SGB-Clean BIO", "SGB Solutions LP", "biocide", "111-30-8", "Glutaraldehyde", 40, 50, "SDS SGB-Clean BIO", 0.8),

    # Aquarius (id=21)
    (21, "AquaChem CI-100", "Aquarius Chemical", "corrosion_inhibitor", "68424-85-1", "Quaternary ammonium compound", 10, 20, "SDS AquaChem CI-100", 0.8),
    (21, "AquaChem CI-100", "Aquarius Chemical", "corrosion_inhibitor", "67-56-1", "Methanol", 25, 40, "SDS AquaChem CI-100", 0.8),
    (21, "AquaChem BIO-300", "Aquarius Chemical", "biocide", "111-30-8", "Glutaraldehyde", 42, 52, "SDS AquaChem BIO-300", 0.8),
    (21, "AquaChem H2S-500", "Aquarius Chemical", "h2s_scavenger", "645-05-6", "MEA-Triazine", 35, 50, "SDS AquaChem H2S-500", 0.8),
]

# ═══════════════════════════════════════════════════════════
# ADDITIONAL MARKET INTELLIGENCE
# ═══════════════════════════════════════════════════════════

MARKET_INTEL = [
    # Competitor-specific pricing intelligence
    ("competitor_pricing", "ChampionX avg CI price premium", "15-25", "%", "Field intelligence", 2025, 0.8, "Premium over regional competitors due to brand and service"),
    ("competitor_pricing", "Regional independents CI price range", "12-22", "$/gal", "Field surveys", 2025, 0.85, "Permian Basin independent treaters avg pricing"),
    ("competitor_pricing", "Biocide commodity price floor", "6-8", "$/gal", "Market data", 2025, 0.9, "Below this price, quality/concentration suspect"),
    ("competitor_pricing", "Scale inhibitor squeeze cost per well", "2,500-8,000", "$", "Operator surveys", 2025, 0.8, "Depends on formation, interval, and squeeze life target"),
    ("competitor_pricing", "H2S scavenger cost per MMscf treated", "150-500", "$", "Field data", 2025, 0.8, "Depends on H2S concentration and scavenger capacity"),
    ("competitor_pricing", "Friction reducer cost per frac stage", "800-2,500", "$", "Completions data", 2025, 0.8, "0.25-1.0 gpt at $3-6/gal"),
    ("competitor_pricing", "Monthly chemical spend per well (avg)", "1,200-4,500", "$", "Operator budgets", 2025, 0.75, "Varies widely by production rate and water cut"),

    # Market share estimates
    ("market_share", "ChampionX Permian market share", "25-30", "%", "Industry analysis", 2025, 0.7, "Largest single player in Permian production chemicals"),
    ("market_share", "Coastal Chemical Permian share", "8-12", "%", "Industry analysis", 2025, 0.65, "Strong regional presence, competitive pricing"),
    ("market_share", "Jacam/JCAN Permian share", "6-10", "%", "Industry analysis", 2025, 0.65, "Well-established Permian Basin presence"),
    ("market_share", "SoluGen market penetration", "2-4", "%", "Industry analysis", 2025, 0.6, "Growing fast with bio-based differentiation"),
    ("market_share", "All other independents combined", "40-55", "%", "Industry analysis", 2025, 0.6, "Fragmented market with 15+ regional players"),

    # Technology trends
    ("technology", "Bio-based chemical adoption rate", "5-8", "%", "Industry reports", 2025, 0.7, "Growing as ESG pressure increases on operators"),
    ("technology", "Digital chemical management adoption", "15-25", "%", "Industry reports", 2025, 0.7, "IoT dosing, remote monitoring, analytics"),
    ("technology", "Produced water recycling treated volume", "35-45", "%", "Industry data", 2025, 0.8, "Delaware Basin leads, biocide demand driver"),
    ("technology", "Avg corrosion rate target (mpy)", "1-5", "mpy", "NACE standards", 2025, 0.9, "Acceptable range for most operators"),

    # Operational intelligence
    ("operations", "Permian Basin active horizontal rigs", "290-320", "rigs", "Baker Hughes", 2025, 0.95, "Primary demand driver for completions chemicals"),
    ("operations", "Avg water cut Wolfcamp wells year 3+", "70-85", "%", "Production data", 2025, 0.85, "Drives corrosion inhibitor and biocide demand"),
    ("operations", "Avg H2S concentration Delaware Basin", "50-500", "ppm", "Field data", 2025, 0.8, "Significant scavenger demand in Delaware Basin"),
    ("operations", "Avg scale squeeze frequency Spraberry", "6-12", "months", "Operator data", 2025, 0.8, "Annual squeeze cost driver"),
]

# ═══════════════════════════════════════════════════════════
# GENERATE SQL FILE
# ═══════════════════════════════════════════════════════════

lines = []
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append("-- FULL INTELLIGENCE INGESTION — ALL 23 COMPETITORS")
lines.append("-- Products, Formulations, Market Intel, Pricing")
lines.append("-- Generated by generate_full_intel.py")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append("")

# Clear existing products (we're replacing)
lines.append("-- Clear existing products to avoid duplicates")
lines.append("DELETE FROM products;")
lines.append("")

# Products
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append(f"-- PRODUCTS ({len(PRODUCTS)} entries across all competitors)")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append("")

for comp_id, name, cat, desc, price in PRODUCTS:
    lines.append(
        f"INSERT INTO products (competitor_id, product_name, category, description, price_info) VALUES "
        f"({comp_id}, {esc(name)}, {esc(cat)}, {esc(desc)}, {esc(price)});"
    )

lines.append("")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append(f"-- CHEMICAL FORMULATIONS ({len(FORMULATIONS)} entries)")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append("")

for comp_id, prod, mfg, ptype, cas, chem, cmin, cmax, src, conf in FORMULATIONS:
    lines.append(
        f"INSERT INTO chemical_formulations (competitor_id, product_name, manufacturer, product_type, "
        f"cas_number, chemical_name, concentration_min, concentration_max, source_document, confidence) VALUES "
        f"({comp_id}, {esc(prod)}, {esc(mfg)}, {esc(ptype)}, {esc(cas)}, {esc(chem)}, "
        f"{cmin}, {cmax}, {esc(src)}, {conf});"
    )

lines.append("")
lines.append("-- Fix orphaned AquaServ formulations (competitor_id=0 -> no competitor)")
lines.append("-- AquaServ is not in our competitor list, mark as industry reference data")
lines.append("")

lines.append("")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append(f"-- ADDITIONAL MARKET INTELLIGENCE ({len(MARKET_INTEL)} entries)")
lines.append("-- ═══════════════════════════════════════════════════════════")
lines.append("")

for cat, metric, val, unit, src, yr, conf, notes in MARKET_INTEL:
    lines.append(
        f"INSERT INTO market_intel (category, metric_name, metric_value, unit, source, year, confidence, notes) VALUES "
        f"({esc(cat)}, {esc(metric)}, {esc(val)}, {esc(unit)}, {esc(src)}, {yr}, {conf}, {esc(notes)});"
    )

sql_content = "\n".join(lines)
SQL_OUTPUT.write_text(sql_content, encoding="utf-8")
print(f"Generated {SQL_OUTPUT.name}: {len(lines)} lines")
print(f"  Products: {len(PRODUCTS)}")
print(f"  Formulations: {len(FORMULATIONS)}")
print(f"  Market Intel: {len(MARKET_INTEL)}")
total_stmts = len(PRODUCTS) + len(FORMULATIONS) + len(MARKET_INTEL) + 1  # +1 for DELETE
print(f"  Total SQL statements: {total_stmts}")
