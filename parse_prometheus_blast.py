"""Parse Prometheus blast results (per-domain JSON files) → D1 SQL.

Reads /tmp/prometheus_results/*.json from Charlie via SSH, parses each scan type,
and generates SQL INSERT statements for competitor_osint, tech_stack, contacts tables.
"""
import json
import re
import sys
from pathlib import Path

# Competitor ID map — domain → ID
DOMAIN_MAP = {
    "championx.com": 1, "coastalchem.com": 2, "coastalchemical.com": 2,
    "imperativechem.com": 3, "corrosionltd.com": 5, "creedence-energy.com": 6,
    "credencechemical.com": 6, "eesokc.com": 7, "endurochemicals.com": 7,
    "energyflowsolutions.com": 8, "infinityenergy.com": 9, "infinitychemicals.com": 9,
    "integrityindustriesinc.com": 10, "integritychem.com": 10,
    "interfacetreating.com": 11, "interfacechem.com": 11,
    "maxflowchem.com": 12, "maxflowchemicals.com": 12,
    "otoilfieldchemicals.com": 13, "otoilfieldservices.com": 13,
    "perfectchem.com": 14, "perfectchemicals.com": 14,
    "reviveenergy.com": 15, "revivechem.com": 15,
    "sgbchemicals.com": 16, "sgbsolutions.com": 16,
    "solnexuschem.com": 17, "solnexus.com": 17,
    "solugen.com": 18, "specialtyintermediates.com": 19, "specialtychemicals.com": 19,
    "trucam.com": 20, "aquariuschemical.com": 21, "aquariuschem.com": 21,
    "basinchemicals.com": 22, "jcanchemicals.com": 23, "suncoastchemicals.com": 24,
}


def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''").replace("\n", " ").replace("\r", "").strip()[:500] + "'"


def parse_harvester(data, comp_id, domain):
    """Parse theHarvester output → emails, hosts, IPs."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # Extract emails
    emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', stdout)
    for email in set(emails):
        if email.endswith(domain) or '@' in email:
            stmts.append(
                f"INSERT OR IGNORE INTO contacts (competitor_id, contact_type, contact_value, label, source_url) "
                f"VALUES ({comp_id}, 'email', {esc(email)}, {esc(email.split('@')[0])}, 'theHarvester');"
            )
            stmts.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, 'harvester', 'email', {esc(email)}, 'medium', {esc(stdout[:500])}, 'theHarvester');"
            )

    # Extract hosts/IPs
    hosts = re.findall(r'(?:[\w-]+\.)+' + re.escape(domain), stdout)
    for host in set(hosts):
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'harvester', 'subdomain', {esc(host)}, 'low', {esc(stdout[:300])}, 'theHarvester');"
        )

    ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', stdout)
    for ip in set(ips):
        if not ip.startswith("127.") and not ip.startswith("0."):
            stmts.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, 'harvester', 'ip_address', {esc(ip)}, 'low', {esc(f'Host IP for {domain}')}, 'theHarvester');"
            )

    return stmts


def parse_whois(data, comp_id, domain):
    """Parse WHOIS data → registrar, dates, nameservers."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # Registrar
    reg = re.search(r'Registrar:\s*(.+)', stdout)
    if reg:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'whois', 'registrar', {esc(reg.group(1).strip())}, 'info', {esc(stdout[:500])}, 'whois');"
        )

    # Creation date
    created = re.search(r'Creation Date:\s*(\S+)', stdout)
    if created:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'whois', 'domain_created', {esc(created.group(1))}, 'info', {esc(f'{domain} created {created.group(1)}')}, 'whois');"
        )

    # Expiry
    expiry = re.search(r'(?:Registry )?Expiry Date:\s*(\S+)', stdout)
    if expiry:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'whois', 'domain_expiry', {esc(expiry.group(1))}, 'info', {esc(f'{domain} expires {expiry.group(1)}')}, 'whois');"
        )

    # Nameservers
    nss = re.findall(r'Name Server:\s*(\S+)', stdout, re.IGNORECASE)
    for ns in set(nss):
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'whois', 'nameserver', {esc(ns)}, 'info', {esc(f'{domain} NS: {ns}')}, 'whois');"
        )

    # DNSSEC
    dnssec = re.search(r'DNSSEC:\s*(\S+)', stdout)
    if dnssec:
        stmts.append(
            f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
            f"VALUES ({comp_id}, {esc('DNSSEC: ' + dnssec.group(1))}, 'security', 'whois');"
        )

    return stmts


def parse_dnsrecon(data, comp_id, domain):
    """Parse DNSRecon output → DNS records."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # MX records
    mx_records = re.findall(r'MX\s+(\S+)\s+(\S+)', stdout)
    for priority, mx in mx_records:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'dnsrecon', 'mx_record', {esc(mx)}, 'info', {esc(f'MX {priority} {mx}')}, 'dnsrecon');"
        )
        # Detect email provider
        if 'google' in mx.lower() or 'gmail' in mx.lower():
            stmts.append(
                f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
                f"VALUES ({comp_id}, 'Google Workspace', 'email', 'dnsrecon-mx');"
            )
        elif 'outlook' in mx.lower() or 'microsoft' in mx.lower():
            stmts.append(
                f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
                f"VALUES ({comp_id}, 'Microsoft 365', 'email', 'dnsrecon-mx');"
            )

    # TXT records (SPF, DKIM, DMARC)
    txt_records = re.findall(r'TXT\s+(.+)', stdout)
    for txt in txt_records:
        if 'spf' in txt.lower():
            stmts.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, 'dnsrecon', 'spf_record', {esc(txt[:300])}, 'info', {esc(txt[:500])}, 'dnsrecon');"
            )

    # A records
    a_records = re.findall(r'\bA\s+(\S+)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', stdout)
    for host, ip in a_records:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'dnsrecon', 'dns_a_record', {esc(f'{host} -> {ip}')}, 'low', {esc(f'A record: {host} {ip}')}, 'dnsrecon');"
        )

    return stmts


def parse_subfinder(data, comp_id, domain):
    """Parse subfinder output → subdomains."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    subs = re.findall(r'([\w.-]+\.' + re.escape(domain) + r')', stdout)
    for sub in set(subs):
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'subfinder', 'subdomain', {esc(sub)}, 'low', {esc(f'Discovered subdomain: {sub}')}, 'subfinder');"
        )

    return stmts


def parse_headers(data, comp_id, domain):
    """Parse HTTP headers → security analysis."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # Server header
    server = re.search(r'[Ss]erver:\s*(.+)', stdout)
    if server:
        stmts.append(
            f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
            f"VALUES ({comp_id}, {esc(server.group(1).strip())}, 'web_server', 'http-headers');"
        )

    # Security headers check
    security_headers = ['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options',
                        'X-Content-Type-Options', 'X-XSS-Protection']
    for h in security_headers:
        if h.lower() not in stdout.lower():
            stmts.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, 'headers', 'missing_security_header', {esc(h)}, 'medium', {esc(f'{domain} missing {h}')}, 'http-headers');"
            )

    # Powered-By
    powered = re.search(r'X-Powered-By:\s*(.+)', stdout, re.IGNORECASE)
    if powered:
        stmts.append(
            f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
            f"VALUES ({comp_id}, {esc(powered.group(1).strip())}, 'framework', 'http-headers');"
        )

    return stmts


def parse_whatweb(data, comp_id, domain):
    """Parse WhatWeb output → technologies."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # WhatWeb outputs tech in brackets: [WordPress], [jQuery], etc.
    techs = re.findall(r'\[([^\]]+)\]', stdout)
    for tech in set(techs):
        if len(tech) < 100 and tech not in ('200', '301', '302', '403', '404'):
            stmts.append(
                f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
                f"VALUES ({comp_id}, {esc(tech)}, 'web_technology', 'whatweb');"
            )

    return stmts


def parse_sslscan(data, comp_id, domain):
    """Parse SSL scan → certificate info."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # Certificate issuer
    issuer = re.search(r'Issuer:\s*(.+)', stdout)
    if issuer:
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'sslscan', 'ssl_issuer', {esc(issuer.group(1).strip())}, 'info', {esc(stdout[:500])}, 'sslscan');"
        )

    # Weak protocols
    for proto in ['SSLv2', 'SSLv3', 'TLSv1.0', 'TLSv1.1']:
        if proto.lower() in stdout.lower() and 'enabled' in stdout.lower():
            stmts.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, 'sslscan', 'weak_ssl', {esc(f'{proto} enabled')}, 'high', {esc(f'{domain} supports deprecated {proto}')}, 'sslscan');"
            )

    return stmts


def parse_geoip(data, comp_id, domain):
    """Parse GeoIP → hosting location."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)
    parsed = data.get("parsed", {}) if isinstance(data, dict) else {}

    country = None
    # Try parsed field first (structured data from Prometheus)
    if parsed and parsed.get("country"):
        country = parsed["country"]
    else:
        # Try GeoIP Country Edition format
        m = re.search(r'GeoIP Country Edition:\s*\w+,\s*(.+)', stdout)
        if m:
            country = m.group(1).strip()
        else:
            # Fallback regex
            m2 = re.search(r'(?:Country|country):\s*(.+)', stdout)
            if m2:
                country = m2.group(1).strip()

    if country and 'not found' not in country.lower() and "can't resolve" not in country.lower():
        stmts.append(
            f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            f"VALUES ({comp_id}, {esc(domain)}, 'geoip', 'hosting_location', {esc(country)}, 'info', {esc(f'{domain} hosted in {country}')}, 'geoip');"
        )

    org = parsed.get("org") if parsed else None
    if not org:
        m = re.search(r'(?:Org|org|Organization|organization):\s*(.+)', stdout)
        if m:
            org = m.group(1).strip()
    if org:
        stmts.append(
            f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
            f"VALUES ({comp_id}, {esc(org)}, 'hosting_provider', 'geoip');"
        )

    return stmts


def parse_httpx(data, comp_id, domain):
    """Parse httpx → web tech fingerprint."""
    stmts = []
    stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)

    # Status codes, tech, CDN
    techs = re.findall(r'\[([^\]]+)\]', stdout)
    for tech in set(techs):
        if len(tech) < 80 and tech not in ('200', '301', '302'):
            stmts.append(
                f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
                f"VALUES ({comp_id}, {esc(tech)}, 'web_infrastructure', 'httpx');"
            )

    return stmts


PARSERS = {
    "harvester": parse_harvester,
    "whois": parse_whois,
    "dnsrecon": parse_dnsrecon,
    "subfinder": parse_subfinder,
    "headers": parse_headers,
    "whatweb": parse_whatweb,
    "sslscan": parse_sslscan,
    "geoip": parse_geoip,
    "httpx": parse_httpx,
}


def main():
    """Read JSON results from stdin (piped from Charlie) and generate SQL."""
    results = json.load(sys.stdin)  # dict: {filename: json_content}

    all_stmts = []

    for filename, data in results.items():
        # Parse filename: domain_scantype.json
        parts = filename.replace(".json", "").rsplit("_", 1)
        if len(parts) != 2:
            continue
        domain, scan_type = parts

        comp_id = DOMAIN_MAP.get(domain)
        if not comp_id:
            # Try partial match
            for d, cid in DOMAIN_MAP.items():
                if d in domain or domain in d:
                    comp_id = cid
                    break
        if not comp_id:
            print(f"-- SKIPPED: {filename} (no competitor ID for {domain})", file=sys.stderr)
            continue

        parser = PARSERS.get(scan_type)
        if not parser:
            # Generic: store raw as OSINT finding
            stdout = data.get("stdout", "") if isinstance(data, dict) else str(data)
            if stdout and len(stdout) > 10:
                all_stmts.append(
                    f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                    f"VALUES ({comp_id}, {esc(domain)}, {esc(scan_type)}, {esc(scan_type)}, {esc(f'{domain} {scan_type} scan')}, 'info', {esc(stdout[:500])}, {esc(scan_type)});"
                )
            continue

        stmts = parser(data, comp_id, domain)
        all_stmts.extend(stmts)

    # Output SQL
    print(f"-- Prometheus Blast Results: {len(all_stmts)} statements from {len(results)} scan files")
    print(f"-- Generated: {__import__('datetime').datetime.now().isoformat()}")
    print()
    for stmt in all_stmts:
        print(stmt)

    print(f"\n-- TOTAL: {len(all_stmts)} SQL statements", file=sys.stderr)


if __name__ == "__main__":
    main()
