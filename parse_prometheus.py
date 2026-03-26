"""Parse prometheus_intel.json → clean, deduped SQL for D1 competitor_osint + tech_stack + contacts."""
import json
import re
from pathlib import Path

NAME_MAP = {
    "ChampionX": 1, "Coastal Chemical": 2, "Imperative Chemical": 3,
    "Corrosion LTD": 5, "Credence IMC": 6, "Enduro Technologies": 7,
    "Energy Flow Solutions": 8, "Infinity Energy Solutions": 9,
    "Integrity Industries": 10, "Interface Treating": 11, "Max Flow Chemicals": 12,
    "OT Oilfield Chemicals": 13, "Perfect Chemical Solutions": 14,
    "Revive Energy Solutions": 15, "SGB Solutions": 16, "Sol Nexus": 17,
    "SoluGen": 18, "Specialty Intermediates": 19, "TruCam Solutions": 20,
    "Aquarius Chemical": 21, "Basin Chemical": 22, "JCAN": 23, "Suncoast": 24,
}

def esc(s):
    if s is None: return "NULL"
    return "'" + str(s).replace("'", "''").replace("\n", " ").replace("\r", "").strip()[:500] + "'"

def get_text(scan_data):
    """Get combined stdout + stderr + sources text from a scan."""
    if isinstance(scan_data, str):
        return scan_data
    if isinstance(scan_data, dict):
        parts = []
        for key in ['stdout', 'stderr', 'output', 'raw_output']:
            v = scan_data.get(key, '')
            if v:
                parts.append(str(v))
        # intel_domain has sources dict
        sources = scan_data.get('sources', {})
        if isinstance(sources, dict):
            for k, v in sources.items():
                if isinstance(v, list):
                    parts.append(f"{k}: " + ", ".join(str(x) for x in v))
                elif isinstance(v, str):
                    parts.append(f"{k}: {v}")
        # whois_snippet inside sources
        ws = sources.get('whois_snippet', '')
        if ws:
            parts.append(str(ws))
        # parsed dict
        parsed = scan_data.get('parsed', {})
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                if isinstance(v, list):
                    parts.append(f"{k}: " + ", ".join(str(x) for x in v[:20]))
                else:
                    parts.append(f"{k}: {v}")
        return "\n".join(parts)
    return ""

def extract_whois(raw):
    findings = []
    m = re.search(r'Registrar[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m and 'URL' not in m.group(0): findings.append(("registrar", m.group(1).strip()[:200], "info", "whois"))
    m = re.search(r'Registrar URL[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m: findings.append(("registrar_url", m.group(1).strip(), "info", "whois"))
    m = re.search(r'Creation Date[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m: findings.append(("domain_created", m.group(1).strip()[:30], "info", "whois"))
    m = re.search(r'(?:Registry )?Expir[a-z]* Date[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m: findings.append(("domain_expiry", m.group(1).strip()[:30], "info", "whois"))
    m = re.search(r'Registrant Organization[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m and "REDACTED" not in m.group(1).upper() and "Privacy" not in m.group(1):
        findings.append(("registrant_org", m.group(1).strip(), "info", "whois"))
    m = re.search(r'Registrant State[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m and "REDACTED" not in m.group(1).upper():
        findings.append(("registrant_state", m.group(1).strip(), "info", "whois"))
    m = re.search(r'Registrant Country[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m and "REDACTED" not in m.group(1).upper():
        findings.append(("registrant_country", m.group(1).strip(), "info", "whois"))
    ns = list(set(re.findall(r'Name Server[:\s]+(\S+)', raw, re.I)))
    if ns:
        findings.append(("nameservers", ", ".join(sorted(n.lower() for n in ns[:6])), "info", "whois"))
        # Identify DNS provider
        for n in ns:
            nl = n.lower()
            if "cloudflare" in nl: findings.append(("dns_provider", "Cloudflare", "info", "whois")); break
            elif "aws" in nl or "amazon" in nl: findings.append(("dns_provider", "AWS Route53", "info", "whois")); break
            elif "azure" in nl: findings.append(("dns_provider", "Azure DNS", "info", "whois")); break
            elif "google" in nl: findings.append(("dns_provider", "Google Cloud DNS", "info", "whois")); break
            elif "godaddy" in nl or "domaincontrol" in nl: findings.append(("dns_provider", "GoDaddy", "info", "whois")); break
    m = re.search(r'DNSSEC[:\s]+(.+?)(?:\n|$)', raw, re.I)
    if m:
        val = m.group(1).strip().lower()
        sev = "info" if "signed" in val else "low"
        findings.append(("dnssec", val, sev, "whois"))
    return findings

def extract_harvester(raw):
    findings = []
    # Emails
    emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', raw))
    emails = {e for e in emails if not e.endswith(('.png','.jpg','.gif','.css','.js'))}
    for e in sorted(emails)[:20]:
        findings.append(("email", e, "medium", "theHarvester"))
    # Hosts
    hosts_match = re.search(r'\[\*\]\s*Hosts found.*?:\s*\n(.+?)(?:\[\*\]|\[!\]|$)', raw, re.S)
    hosts = set()
    if hosts_match:
        for line in hosts_match.group(1).split('\n'):
            line = line.strip()
            if ':' in line:
                h = line.split(':')[0].strip()
                if '.' in h and len(h) > 4: hosts.add(h.lower())
            elif '.' in line and len(line) > 4 and ' ' not in line:
                hosts.add(line.lower())
    for h in sorted(hosts)[:30]:
        findings.append(("host", h, "info", "theHarvester"))
    if hosts:
        findings.append(("host_count", str(len(hosts)), "info", "theHarvester"))
    # IPs
    ips = set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', raw))
    # Filter out common non-useful IPs
    ips = {ip for ip in ips if not ip.startswith('127.') and not ip.startswith('0.')}
    for ip in sorted(ips)[:15]:
        findings.append(("ip_address", ip, "info", "theHarvester"))
    # Interesting URLs
    urls = set(re.findall(r'https?://[^\s\'"<>\)]+', raw))
    interesting_kw = ['api', 'admin', 'login', 'portal', 'dev', 'staging', 'test', 'internal', 'vpn', 'remote']
    interesting = [u for u in urls if any(k in u.lower() for k in interesting_kw)]
    for u in sorted(interesting)[:10]:
        findings.append(("interesting_url", u[:300], "medium", "theHarvester"))
    # Count from output
    m = re.search(r'\[\*\]\s*(\d+)\s+(?:results?|hosts?|ips?)', raw, re.I)
    if m:
        findings.append(("harvester_total_results", m.group(1), "info", "theHarvester"))
    return findings

def extract_dnsrecon(raw):
    findings = []
    # MX records
    mx_records = re.findall(r'MX\s+([\w.-]+)\s+([\w.-]+)', raw)
    if not mx_records:
        mx_records = [(m,m) for m in re.findall(r'(?:MX|mail)[:\s]+([\w.-]+)', raw, re.I)]
    seen_mx = set()
    for parts in mx_records[:5]:
        mx = parts[-1] if isinstance(parts, tuple) else parts
        if mx.lower() in seen_mx: continue
        seen_mx.add(mx.lower())
        provider = identify_email_provider(mx)
        findings.append(("mx_record", f"{mx} ({provider})", "info", "dnsrecon"))
    # SPF
    spf = re.findall(r'v=spf1[^"\']*', raw)
    if spf: findings.append(("spf_record", spf[0][:300], "info", "dnsrecon"))
    # DMARC
    dmarc = re.findall(r'v=DMARC1[^"\']*', raw, re.I)
    if dmarc:
        pm = re.search(r'p=(\w+)', dmarc[0])
        policy = pm.group(1) if pm else "unknown"
        sev = "low" if policy == "none" else "info"
        findings.append(("dmarc_policy", f"p={policy} — {dmarc[0][:200]}", sev, "dnsrecon"))
    # A records
    a_recs = re.findall(r'A\s+([\w.-]+)\s+(\d+\.\d+\.\d+\.\d+)', raw)
    seen_a = set()
    for name, ip in a_recs[:10]:
        if ip not in seen_a:
            seen_a.add(ip)
            findings.append(("a_record", f"{name} → {ip}", "info", "dnsrecon"))
    # NS
    ns_recs = set(re.findall(r'NS\s+[\w.-]+\s+([\w.-]+)', raw))
    for n in sorted(ns_recs)[:5]:
        findings.append(("ns_record", n, "info", "dnsrecon"))
    # DNSSEC
    if "DNSSEC is configured" in raw:
        findings.append(("dnssec_status", "enabled", "info", "dnsrecon"))
    elif "DNSSEC is not configured" in raw:
        findings.append(("dnssec_status", "disabled", "low", "dnsrecon"))
    # SOA
    soa = re.search(r'SOA\s+([\w.-]+)\s+([\w.-]+)', raw)
    if soa:
        findings.append(("soa_record", f"{soa.group(1)} {soa.group(2)}", "info", "dnsrecon"))
    return findings

def extract_subfinder(raw):
    findings = []
    subs = set()
    for line in raw.split('\n'):
        line = line.strip()
        # Skip ANSI codes and info lines
        if line.startswith('[') or not line or 'INF' in line or 'subfinder' in line.lower():
            continue
        if '.' in line and len(line) > 4 and ' ' not in line:
            subs.add(line.lower().strip('.'))
    if subs:
        findings.append(("subdomain_count", str(len(subs)), "info", "subfinder"))
        # Categorize
        categories = {
            "dev": [], "staging": [], "api": [], "admin": [], "vpn": [],
            "mail": [], "portal": [], "internal": [], "test": [], "app": [],
            "cdn": [], "remote": [], "qa": []
        }
        uncategorized = []
        for sub in sorted(subs):
            categorized = False
            for cat in categories:
                if cat in sub:
                    categories[cat].append(sub)
                    categorized = True
                    break
            if not categorized:
                uncategorized.append(sub)

        for cat, items in categories.items():
            if items:
                sev = "medium" if cat in ("admin","internal","vpn","staging","test","qa","remote") else "low"
                for item in items[:5]:
                    findings.append((f"subdomain_{cat}", item, sev, "subfinder"))

        # Top uncategorized
        for sub in uncategorized[:15]:
            findings.append(("subdomain", sub, "info", "subfinder"))
    return findings

def extract_dig(raw):
    findings = []
    # A records
    a_recs = re.findall(r'([\w.-]+)\.\s+\d+\s+IN\s+A\s+(\d+\.\d+\.\d+\.\d+)', raw)
    seen = set()
    for name, ip in a_recs:
        if ip not in seen:
            seen.add(ip)
            findings.append(("dns_a", f"{name} → {ip}", "info", "dig"))
    # MX
    mx_recs = re.findall(r'([\w.-]+)\.\s+\d+\s+IN\s+MX\s+\d+\s+([\w.-]+)', raw)
    for name, mx in mx_recs[:5]:
        provider = identify_email_provider(mx)
        findings.append(("dns_mx", f"{mx} ({provider})", "info", "dig"))
    # CNAME
    cnames = re.findall(r'([\w.-]+)\.\s+\d+\s+IN\s+CNAME\s+([\w.-]+)', raw)
    for name, target in cnames[:5]:
        findings.append(("dns_cname", f"{name} → {target}", "info", "dig"))
    # TXT
    txts = re.findall(r'IN\s+TXT\s+"([^"]+)"', raw)
    for txt in txts[:5]:
        if 'spf' in txt.lower() or 'dmarc' in txt.lower() or 'google' in txt.lower() or 'ms=' in txt.lower():
            findings.append(("dns_txt", txt[:300], "info", "dig"))
    return findings

def extract_intel_domain(scan_data):
    findings = []
    sources = scan_data.get('sources', {}) if isinstance(scan_data, dict) else {}
    # DNS IPs
    dns_ips = sources.get('dns', [])
    if isinstance(dns_ips, list):
        for ip in dns_ips[:5]:
            findings.append(("primary_ip", str(ip), "info", "intel_domain"))
    # WHOIS snippet
    ws = sources.get('whois_snippet', '')
    if ws:
        m = re.search(r'Registrar URL[:\s]+(.+?)(?:\n|$)', ws, re.I)
        if m: findings.append(("registrar_url_snippet", m.group(1).strip(), "info", "intel_domain"))
        m = re.search(r'Creation Date[:\s]+(.+?)(?:\n|$)', ws, re.I)
        if m: findings.append(("domain_created_snippet", m.group(1).strip()[:30], "info", "intel_domain"))
    # Risk score
    risk = scan_data.get('risk_score', None) if isinstance(scan_data, dict) else None
    if risk is not None:
        sev = "info" if risk == 0 else ("medium" if risk > 5 else "low")
        findings.append(("risk_score", str(risk), sev, "intel_domain"))
    return findings

def identify_email_provider(mx_host):
    ml = mx_host.lower()
    if "google" in ml or "gmail" in ml or "aspmx" in ml: return "Google Workspace"
    if "outlook" in ml or "microsoft" in ml or "protection.outlook" in ml: return "Microsoft 365"
    if "pphosted" in ml or "proofpoint" in ml: return "Proofpoint"
    if "mimecast" in ml: return "Mimecast"
    if "barracuda" in ml: return "Barracuda"
    if "secureserver" in ml or "godaddy" in ml: return "GoDaddy Email"
    if "zoho" in ml: return "Zoho Mail"
    if "mailgun" in ml: return "Mailgun"
    if "sendgrid" in ml: return "SendGrid"
    return "Custom/Unknown"

def main():
    with open("prometheus_intel.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    sql_lines = [
        "-- S2 Prometheus Arsenal: Cleaned OSINT Intelligence Ingestion",
        "-- 23 competitors × 6 scan types, deduped and categorized",
        "",
        "-- Clear old prometheus scan data",
        "DELETE FROM competitor_osint WHERE source_tool IN ('whois','theHarvester','dnsrecon','subfinder','dig','intel_domain','prometheus');",
        "",
    ]
    tech_entries = []
    contact_entries = []
    total_findings = 0

    for name, comp_data in data.items():
        comp_id = NAME_MAP.get(name)
        if not comp_id:
            print(f"WARNING: No D1 ID for {name}")
            continue

        domain = comp_data.get("domain", "unknown")
        scans = comp_data.get("scans", {})
        all_findings = []

        # Always add primary domain
        all_findings.append(("primary_domain", domain, "info", "prometheus"))

        for scan_name, scan_data in scans.items():
            sn = scan_name.lower()
            if sn == "intel_domain":
                all_findings.extend(extract_intel_domain(scan_data))
            elif sn == "whois":
                raw = get_text(scan_data)
                all_findings.extend(extract_whois(raw))
            elif sn == "harvester":
                raw = get_text(scan_data)
                all_findings.extend(extract_harvester(raw))
            elif sn == "dnsrecon":
                raw = get_text(scan_data)
                all_findings.extend(extract_dnsrecon(raw))
            elif sn == "subfinder":
                raw = get_text(scan_data)
                all_findings.extend(extract_subfinder(raw))
            elif sn == "dig":
                raw = get_text(scan_data)
                all_findings.extend(extract_dig(raw))

        # Deduplicate
        seen = set()
        deduped = []
        for ft, val, sev, tool in all_findings:
            key = (ft, val.lower().strip()[:100])
            if key not in seen:
                seen.add(key)
                deduped.append((ft, val, sev, tool))

        sql_lines.append(f"-- {name} ({domain}): {len(deduped)} findings")
        for ft, val, sev, tool in deduped:
            sql_lines.append(
                f"INSERT INTO competitor_osint (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
                f"VALUES ({comp_id}, {esc(domain)}, {esc(tool)}, {esc(ft)}, {esc(val)}, {esc(sev)}, 'S2 Prometheus arsenal scan 2026-03-16', {esc(tool)});"
            )
            total_findings += 1

            # Tech stack entries
            if ft in ("dns_provider", "mx_record"):
                if "Google" in val: tech_entries.append((comp_id, "Google Workspace", "Email/Productivity", "MX record analysis"))
                elif "Microsoft" in val: tech_entries.append((comp_id, "Microsoft 365", "Email/Productivity", "MX record analysis"))
                elif "Proofpoint" in val: tech_entries.append((comp_id, "Proofpoint", "Email Security", "MX record analysis"))
                elif "Cloudflare" in val: tech_entries.append((comp_id, "Cloudflare", "CDN/DNS", "DNS analysis"))
                elif "AWS" in val: tech_entries.append((comp_id, "AWS", "Cloud/DNS", "DNS analysis"))
                elif "Azure" in val: tech_entries.append((comp_id, "Azure", "Cloud/DNS", "DNS analysis"))
                elif "GoDaddy" in val: tech_entries.append((comp_id, "GoDaddy", "DNS/Registrar", "DNS analysis"))

            # Contact entries
            if ft == "email":
                contact_entries.append((comp_id, val, domain))

        sql_lines.append("")

    # Tech stack
    if tech_entries:
        sql_lines.append("-- Tech stack from OSINT analysis")
        sql_lines.append("DELETE FROM tech_stack WHERE evidence = 'MX record analysis' OR evidence = 'DNS analysis';")
        seen_tech = set()
        for cid, tech, cat, evidence in tech_entries:
            key = (cid, tech)
            if key not in seen_tech:
                seen_tech.add(key)
                sql_lines.append(
                    f"INSERT INTO tech_stack (competitor_id, technology, category, evidence) "
                    f"VALUES ({cid}, {esc(tech)}, {esc(cat)}, {esc(evidence)});"
                )
        sql_lines.append("")

    # Contacts
    if contact_entries:
        sql_lines.append("-- Harvested email contacts")
        sql_lines.append("DELETE FROM contacts WHERE label = 'S2 Harvest';")
        seen_contacts = set()
        for cid, email, domain in contact_entries:
            if email not in seen_contacts:
                seen_contacts.add(email)
                sql_lines.append(
                    f"INSERT INTO contacts (competitor_id, contact_type, contact_value, label, source_url) "
                    f"VALUES ({cid}, 'email', {esc(email)}, 'S2 Harvest', {esc(domain)});"
                )
        sql_lines.append("")

    Path("ingest_s2_osint.sql").write_text("\n".join(sql_lines), encoding="utf-8")
    stmts = len([l for l in sql_lines if l.strip().endswith(';')])
    print(f"Generated ingest_s2_osint.sql:")
    print(f"  {total_findings} OSINT findings across {len(data)} competitors")
    print(f"  {len(set(t[:2] for t in tech_entries))} tech stack entries")
    print(f"  {len(set(c[1] for c in contact_entries))} contact emails")
    print(f"  {stmts} total SQL statements")

if __name__ == "__main__":
    main()
