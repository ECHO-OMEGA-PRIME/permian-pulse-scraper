"""
Prometheus Deep OSINT Scanner for Permian Pulse Competitors
Runs through Tor on Charlie (192.168.1.202) via Prometheus API (port 8370)
Ingests results into D1 competitor_osint table
"""
import json
import sys
import time
import urllib.request
import urllib.error
import tomllib
import os
from datetime import datetime

# D1 config
ACCOUNT_ID = "b9af3a4bf161132bb7e5d3d365fb8bb0"
DB_ID = "4a2c1d02-c377-4e70-b8f8-aec879f77ebb"

# Prometheus on Charlie
PROMETHEUS = "http://192.168.1.202:8370"

# All 23 competitors with domains and IDs
COMPETITORS = [
    (1, "Champion X", "championx.com"),
    (2, "Coastal Chemical", "coastalchemical.com"),
    (3, "Imperative Chemical Partners", "imperativechem.com"),
    (5, "Corrosion Fluid Products", None),
    (6, "Credence Resources", None),
    (7, "Enduro Pipeline Services", None),
    (8, "Energy Flow Solutions", None),
    (9, "Infinity Chemical", None),
    (10, "Integrity Chemical", None),
    (11, "Interface Performance Materials", None),
    (12, "MaxFlow Chemical", None),
    (13, "OT Oilfield Services", None),
    (14, "Perfect Chemical", None),
    (15, "Revive Energy", None),
    (16, "SGB Solutions", None),
    (17, "Sol Nexus", "solnexus.com"),
    (18, "SoluGen", "solugen.com"),
    (19, "Specialty Drilling Fluids", None),
    (20, "TruCam Solutions", None),
    (21, "Aquarius Water Conditioning", None),
    (22, "Basin Chemical Solutions", None),
    (23, "JCAN Oilfield Services", None),
    (24, "Suncoast Chemical", None),
]

# Scan types and their Prometheus endpoints
SCAN_TYPES = {
    "whois": "/osint/whois/{domain}",
    "dns_lookup": "/osint/dig/{domain}",
    "subdomain_discovery": "/osint/subfinder/{domain}",
    "email_harvest": "/osint/theharvester/{domain}",
    "dns_recon": "/osint/dnsrecon/{domain}",
    "ssl_scan": "/vuln/sslscan/{domain}",
    "ssl_analysis": "/vuln/sslyze/{domain}",
    "web_fingerprint": "/web/whatweb/{domain}",
    "http_headers": "/web/headers/{domain}",
    "robots_txt": "/web/robots/{domain}",
    "sitemap": "/web/sitemap/{domain}",
    "httpx_probe": "/web/httpx/{domain}",
    "domain_intel": "/intel/domain/{domain}",
    "quick_scan": "/scan/quick/{domain}",
}


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


def prometheus_scan(endpoint: str, timeout: int = 120) -> dict:
    """Call a Prometheus endpoint"""
    url = f"{PROMETHEUS}{endpoint}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body[:500]}
    except Exception as e:
        return {"error": str(e)}


def extract_findings(scan_type: str, domain: str, result: dict) -> list:
    """Extract structured findings from raw scan results"""
    findings = []

    if "error" in result:
        return findings

    stdout = result.get("stdout", "") or ""
    parsed = result.get("parsed", {}) or {}

    # Whois findings
    if scan_type == "whois":
        whois_data = parsed if parsed else {}
        if not whois_data and stdout:
            # Parse raw whois output
            for line in stdout.split("\n"):
                if ":" in line and not line.startswith("%") and not line.startswith("#"):
                    key, _, val = line.partition(":")
                    key = key.strip().lower()
                    val = val.strip()
                    if val and key in ("registrar", "creation date", "registrant organization",
                                       "registrant country", "name server", "registrant email",
                                       "tech email", "admin email", "registrant name",
                                       "registrant state/province", "registrant city"):
                        findings.append({
                            "finding_type": "whois_" + key.replace(" ", "_").replace("/", "_"),
                            "finding_value": val[:500],
                            "severity": "info",
                            "details": f"WHOIS {key}: {val}",
                        })
        for k, v in whois_data.items():
            if v and str(v).strip():
                findings.append({
                    "finding_type": f"whois_{k}",
                    "finding_value": str(v)[:500],
                    "severity": "info",
                    "details": f"WHOIS record: {k}",
                })

    # DNS findings
    elif scan_type in ("dns_lookup", "dns_recon"):
        if stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith(";") and len(line) > 5:
                    findings.append({
                        "finding_type": "dns_record",
                        "finding_value": line[:500],
                        "severity": "info",
                        "details": f"DNS record for {domain}",
                    })
        if parsed:
            for rtype, records in parsed.items():
                if isinstance(records, list):
                    for rec in records:
                        findings.append({
                            "finding_type": f"dns_{rtype}",
                            "finding_value": str(rec)[:500],
                            "severity": "info",
                            "details": f"DNS {rtype} record",
                        })

    # Subdomain findings
    elif scan_type == "subdomain_discovery":
        subs = parsed.get("subdomains", []) if parsed else []
        if not subs and stdout:
            subs = [s.strip() for s in stdout.split("\n") if s.strip() and "." in s]
        for sub in subs:
            findings.append({
                "finding_type": "subdomain",
                "finding_value": sub[:500],
                "severity": "low",
                "details": f"Subdomain discovered: {sub}",
            })

    # Email harvest
    elif scan_type == "email_harvest":
        emails = parsed.get("emails", []) if parsed else []
        hosts = parsed.get("hosts", []) if parsed else []
        if not emails and stdout:
            import re
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', stdout)
        for email in set(emails):
            findings.append({
                "finding_type": "email_address",
                "finding_value": email[:500],
                "severity": "medium",
                "details": f"Email harvested from public sources",
            })
        for host in hosts:
            findings.append({
                "finding_type": "discovered_host",
                "finding_value": str(host)[:500],
                "severity": "low",
                "details": f"Host discovered via theHarvester",
            })

    # SSL findings
    elif scan_type in ("ssl_scan", "ssl_analysis"):
        if stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue
                severity = "info"
                if any(w in line.lower() for w in ("vulnerable", "weak", "expired", "deprecated", "sslv", "tls 1.0", "tls 1.1", "rc4", "des", "md5")):
                    severity = "high"
                elif any(w in line.lower() for w in ("warning", "sha1", "self-signed")):
                    severity = "medium"
                elif any(w in line.lower() for w in ("subject:", "issuer:", "not after", "serial", "tls 1.2", "tls 1.3", "cipher")):
                    findings.append({
                        "finding_type": "ssl_config",
                        "finding_value": line[:500],
                        "severity": severity,
                        "details": f"SSL/TLS configuration detail",
                    })
                    continue
                if len(line) > 10:
                    findings.append({
                        "finding_type": "ssl_finding",
                        "finding_value": line[:500],
                        "severity": severity,
                        "details": f"SSL scan result",
                    })

    # Web fingerprint
    elif scan_type == "web_fingerprint":
        if stdout:
            for line in stdout.split("\n"):
                if line.strip() and len(line.strip()) > 5:
                    findings.append({
                        "finding_type": "web_technology",
                        "finding_value": line.strip()[:500],
                        "severity": "info",
                        "details": f"Web technology fingerprint",
                    })
        if parsed:
            for tech in parsed.get("technologies", parsed.get("plugins", [])):
                findings.append({
                    "finding_type": "web_technology",
                    "finding_value": str(tech)[:500],
                    "severity": "info",
                    "details": f"Detected web technology",
                })

    # HTTP headers
    elif scan_type == "http_headers":
        if parsed:
            for header, value in parsed.items():
                sev = "info"
                if header.lower() in ("x-powered-by", "server"):
                    sev = "low"  # Info disclosure
                if header.lower() == "strict-transport-security":
                    sev = "info"
                findings.append({
                    "finding_type": "http_header",
                    "finding_value": f"{header}: {value}"[:500],
                    "severity": sev,
                    "details": f"HTTP response header",
                })
        elif stdout:
            for line in stdout.split("\n"):
                if ":" in line and line.strip():
                    findings.append({
                        "finding_type": "http_header",
                        "finding_value": line.strip()[:500],
                        "severity": "info",
                        "details": f"HTTP header",
                    })

    # Robots.txt / Sitemap
    elif scan_type in ("robots_txt", "sitemap"):
        if stdout:
            for line in stdout.split("\n"):
                if line.strip() and len(line.strip()) > 3:
                    ftype = "robots_entry" if scan_type == "robots_txt" else "sitemap_url"
                    findings.append({
                        "finding_type": ftype,
                        "finding_value": line.strip()[:500],
                        "severity": "info",
                        "details": f"{scan_type.replace('_', ' ').title()} entry",
                    })

    # HTTPx probe
    elif scan_type == "httpx_probe":
        if stdout:
            for line in stdout.split("\n"):
                if line.strip():
                    findings.append({
                        "finding_type": "httpx_result",
                        "finding_value": line.strip()[:500],
                        "severity": "info",
                        "details": f"HTTP probe result",
                    })

    # Domain intel
    elif scan_type == "domain_intel":
        if isinstance(result, dict):
            for k, v in result.items():
                if k not in ("error", "success", "duration", "code") and v:
                    findings.append({
                        "finding_type": f"intel_{k}",
                        "finding_value": str(v)[:500],
                        "severity": "info" if k not in ("threats", "malware", "phishing") else "high",
                        "details": f"Domain intelligence: {k}",
                    })

    # Quick scan (port scan)
    elif scan_type == "quick_scan":
        if parsed:
            for port_info in parsed.get("ports", parsed.get("hosts", [])):
                findings.append({
                    "finding_type": "open_port",
                    "finding_value": str(port_info)[:500],
                    "severity": "low",
                    "details": f"Open port/service discovered",
                })
        elif stdout:
            for line in stdout.split("\n"):
                if "/tcp" in line or "/udp" in line or "open" in line.lower():
                    findings.append({
                        "finding_type": "open_port",
                        "finding_value": line.strip()[:500],
                        "severity": "low",
                        "details": f"Port scan result",
                    })

    # Generic fallback — capture raw output
    if not findings and stdout and len(stdout) > 20:
        # Split into chunks if large
        chunks = [stdout[i:i+400] for i in range(0, min(len(stdout), 2000), 400)]
        for i, chunk in enumerate(chunks):
            findings.append({
                "finding_type": f"{scan_type}_raw",
                "finding_value": chunk,
                "severity": "info",
                "details": f"Raw {scan_type} output (part {i+1})",
            })

    return findings


def escape_sql(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("'", "''").replace("\\", "\\\\")


def ingest_findings(token: str, comp_id: int, comp_name: str, domain: str,
                    scan_type: str, findings: list) -> int:
    """Insert findings into D1 competitor_osint table"""
    inserted = 0
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for f in findings:
        sql = f"""INSERT OR IGNORE INTO competitor_osint
            (competitor_id, competitor_name, finding_type, finding_value, severity,
             details, source_tool, scan_type, domain, scanned_at)
            VALUES (
                {comp_id},
                '{escape_sql(comp_name)}',
                '{escape_sql(f["finding_type"])}',
                '{escape_sql(f["finding_value"])}',
                '{escape_sql(f.get("severity", "info"))}',
                '{escape_sql(f.get("details", ""))}',
                'prometheus_prime',
                '{escape_sql(scan_type)}',
                '{escape_sql(domain)}',
                '{now}'
            )"""

        result = execute_d1_query(token, sql)
        if result.get("success"):
            inserted += 1

    return inserted


def try_find_domain(comp_name: str) -> str | None:
    """Try to guess domain for companies without known domains"""
    guesses = []
    name_lower = comp_name.lower().replace(" ", "")

    # Common patterns
    parts = comp_name.lower().split()
    if len(parts) >= 2:
        guesses.append(parts[0] + parts[1] + ".com")
        guesses.append(parts[0] + "-" + parts[1] + ".com")
    guesses.append(name_lower + ".com")
    guesses.append(name_lower.replace("services", "") + ".com")
    guesses.append(name_lower.replace("solutions", "") + ".com")
    guesses.append(name_lower.replace("chemical", "chem") + ".com")

    # Try each with a quick HTTP probe
    for domain in guesses[:4]:
        try:
            req = urllib.request.Request(f"https://{domain}", method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status < 400:
                    return domain
        except:
            pass

    return None


def main():
    token = get_oauth_token()

    # Verify D1 connectivity
    test = execute_d1_query(token, "SELECT COUNT(*) as n FROM competitor_osint")
    if not test.get("success"):
        print(f"D1 connection failed: {test}")
        sys.exit(1)
    existing = test["result"][0]["results"][0]["n"]
    print(f"D1 connected. Existing OSINT records: {existing}")

    # Verify Prometheus
    try:
        req = urllib.request.Request(f"{PROMETHEUS}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            health = json.loads(resp.read())
        print(f"Prometheus: {health.get('status')} v{health.get('version')}")
    except Exception as e:
        print(f"Prometheus connection failed: {e}")
        sys.exit(1)

    total_new = 0
    scan_count = 0

    # First, try to discover domains for competitors without them
    print("\n=== DOMAIN DISCOVERY ===")
    for i, (comp_id, comp_name, domain) in enumerate(COMPETITORS):
        if domain is None:
            print(f"  [{comp_name}] Searching for domain...", end=" ", flush=True)
            found = try_find_domain(comp_name)
            if found:
                print(f"FOUND: {found}")
                COMPETITORS[i] = (comp_id, comp_name, found)
            else:
                print("not found")

    # Run scans on all competitors with domains
    print("\n=== DEEP OSINT SCANNING VIA PROMETHEUS (through Tor) ===")
    for comp_id, comp_name, domain in COMPETITORS:
        if domain is None:
            print(f"\n[SKIP] {comp_name} — no domain found")
            continue

        print(f"\n{'='*60}")
        print(f"SCANNING: {comp_name} ({domain}) [ID: {comp_id}]")
        print(f"{'='*60}")

        comp_findings = 0

        for scan_type, endpoint_tmpl in SCAN_TYPES.items():
            endpoint = endpoint_tmpl.replace("{domain}", domain)
            print(f"  [{scan_type:25s}] ", end="", flush=True)

            try:
                result = prometheus_scan(endpoint, timeout=120)

                if "error" in result and "Not Found" in str(result.get("error", "") or result.get("detail", "")):
                    print("endpoint N/A")
                    continue

                findings = extract_findings(scan_type, domain, result)

                if findings:
                    inserted = ingest_findings(token, comp_id, comp_name, domain, scan_type, findings)
                    print(f"{len(findings)} findings, {inserted} new")
                    comp_findings += inserted
                    total_new += inserted
                else:
                    has_data = bool(result.get("stdout", "").strip()) if isinstance(result, dict) else False
                    print(f"0 findings {'(raw data exists)' if has_data else '(no data)'}")

                scan_count += 1

            except Exception as e:
                print(f"ERROR: {str(e)[:80]}")

            # Small delay between scans to avoid rate limiting
            time.sleep(0.5)

        print(f"  >> {comp_name}: {comp_findings} new findings ingested")

        # Slightly longer delay between competitors
        time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"PROMETHEUS DEEP SCAN COMPLETE")
    print(f"{'='*60}")
    print(f"Scans executed: {scan_count}")
    print(f"New findings ingested: {total_new}")

    # Final count
    final = execute_d1_query(token, "SELECT COUNT(*) as n FROM competitor_osint")
    if final.get("success"):
        total = final["result"][0]["results"][0]["n"]
        print(f"Total OSINT records: {total} (was {existing})")

    # Breakdown by severity
    sev = execute_d1_query(token, "SELECT severity, COUNT(*) as n FROM competitor_osint GROUP BY severity ORDER BY n DESC")
    if sev.get("success"):
        print("\nBy severity:")
        for row in sev["result"][0]["results"]:
            print(f"  {row['severity']:12s} {row['n']}")

    # Breakdown by competitor
    comp = execute_d1_query(token, """
        SELECT competitor_name, COUNT(*) as n
        FROM competitor_osint
        GROUP BY competitor_name
        ORDER BY n DESC
        LIMIT 15
    """)
    if comp.get("success"):
        print("\nTop competitors by findings:")
        for row in comp["result"][0]["results"]:
            print(f"  {row['competitor_name']:35s} {row['n']}")


if __name__ == "__main__":
    main()
