"""
ingest_prometheus.py — Parse Prometheus PRIME OSINT scan results and ingest into
the permian-pulse D1 competitor_osint table via Cloudflare D1 REST API.

Parses: whois, theHarvester, dnsrecon, subfinder, dig, intel_domain scans for 23 companies.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

import urllib.request
import urllib.error
import ssl

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCOUNT_ID = "b9af3a4bf161132bb7e5d3d365fb8bb0"
DATABASE_ID = "4a2c1d02-c377-4e70-b8f8-aec879f77ebb"
D1_API_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"

JSON_FILE = Path(__file__).parent / "prometheus_intel.json"
WRANGLER_CONFIG = Path.home() / "AppData" / "Roaming" / "xdg.config" / ".wrangler" / "config" / "default.toml"

# Competitor ID mapping (must match D1 competitors table)
COMPETITOR_ID_MAP: dict[str, int] = {
    "championx.com": 1,
    "coastalchemical.com": 2,
    "imperativechem.com": 3,
    "corrosionltd.com": 5,
    "credenceimc.com": 6,
    "endurotechnologies.com": 7,
    "energyflowsolutions.com": 8,
    "infinityenergysolutions.com": 9,
    "integrityindustriestx.com": 10,
    "interfacetreating.com": 11,
    "maxflowchemicals.com": 12,
    "otoilfieldchemicals.com": 13,
    "perfectchemsolutions.com": 14,
    "reviveenergysolutions.com": 15,
    "sgbsolutions.com": 16,
    "solnexus.com": 17,
    "solugen.com": 18,
    "specialtyintermediates.com": 19,
    "trucamsolutions.com": 20,
    "aquariuschem.com": 21,
    "basinchemical.com": 22,
    "jcan.com": 23,
    "suncoastchemical.com": 24,
}


# ---------------------------------------------------------------------------
# OAuth token loader
# ---------------------------------------------------------------------------

def load_oauth_token() -> str:
    """Read the wrangler OAuth token from the default.toml config file."""
    if not WRANGLER_CONFIG.exists():
        print(f"ERROR: Wrangler config not found at {WRANGLER_CONFIG}")
        sys.exit(1)
    with open(WRANGLER_CONFIG, "rb") as f:
        config = tomllib.load(f)
    token = config.get("oauth_token")
    if not token:
        print("ERROR: oauth_token not found in wrangler config")
        sys.exit(1)
    return token


# ---------------------------------------------------------------------------
# D1 API helpers
# ---------------------------------------------------------------------------

def d1_execute(token: str, sql: str, params: list | None = None) -> dict:
    """Execute a single SQL statement against the D1 REST API."""
    body: dict = {"sql": sql}
    if params:
        body["params"] = params
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        D1_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        print(f"D1 API error {e.code}: {err_body[:500]}")
        raise


def d1_batch_insert(token: str, rows: list[dict]) -> int:
    """Insert rows in batches using multi-row INSERT VALUES.

    D1 REST API accepts one statement per request, so we batch multiple
    rows into a single INSERT with multiple value tuples.
    Batch size capped at 50 rows to stay within D1 payload limits.
    """
    if not rows:
        return 0

    inserted = 0
    # D1 has a 100-variable limit per statement.
    # 8 columns per row → max 12 rows per batch (96 variables)
    batch_size = 12

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        placeholders = []
        params = []
        for row in batch:
            placeholders.append("(?, ?, ?, ?, ?, ?, ?, ?)")
            params.extend([
                row["competitor_id"],
                row["domain"],
                row["scan_type"],
                row["finding_type"],
                row["finding_value"],
                row["severity"],
                row["details"],
                row["source_tool"],
            ])

        sql = (
            "INSERT INTO competitor_osint "
            "(competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool) "
            "VALUES " + ", ".join(placeholders)
        )

        try:
            result = d1_execute(token, sql, params)
            if result.get("success"):
                meta = result.get("result", [{}])[0].get("meta", {})
                inserted += meta.get("changes", len(batch))
            else:
                errors = result.get("errors", [])
                print(f"  Batch insert error: {errors}")
        except Exception as exc:
            print(f"  Batch insert exception: {exc}")

    return inserted


# ---------------------------------------------------------------------------
# Parsers — one per scan type
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    """Truncate and clean text for DB storage."""
    if not text:
        return ""
    return text[:4000].replace("\x00", "")


def _severity_from_count(count: int, thresholds: tuple[int, int, int] = (0, 5, 20)) -> str:
    """Map a count to a severity level: info / low / medium / high."""
    if count <= thresholds[0]:
        return "info"
    elif count <= thresholds[1]:
        return "low"
    elif count <= thresholds[2]:
        return "medium"
    return "high"


def parse_subfinder(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract subdomains from subfinder results."""
    rows = []
    if not scan_data or not scan_data.get("success"):
        return rows

    subdomains = scan_data.get("parsed", {}).get("subdomains", [])
    if not subdomains:
        # Try parsing from stdout
        stdout = scan_data.get("stdout", "")
        if stdout.strip():
            subdomains = [s.strip() for s in stdout.strip().split("\n") if s.strip() and not s.startswith("[")]

    if not subdomains:
        return rows

    count = len(subdomains)
    severity = _severity_from_count(count, (0, 10, 50))

    # Summary row
    rows.append({
        "competitor_id": comp_id,
        "domain": domain,
        "scan_type": "subdomain_enum",
        "finding_type": "subdomain_count",
        "finding_value": f"{count} subdomains discovered for {domain}",
        "severity": severity,
        "details": json.dumps({"count": count, "sample": subdomains[:25]}),
        "source_tool": "subfinder",
    })

    # Flag dev/staging/test subdomains (security concern)
    risky_subs = [s for s in subdomains if any(kw in s.lower() for kw in ("dev", "test", "staging", "stg", "qa", "uat", "predev"))]
    if risky_subs:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "subdomain_enum",
            "finding_type": "exposed_dev_envs",
            "finding_value": f"{len(risky_subs)} dev/test/staging subdomains exposed",
            "severity": "medium",
            "details": json.dumps({"subdomains": risky_subs[:30]}),
            "source_tool": "subfinder",
        })

    # Flag internal-looking hostnames (SAP, Oracle, VPN, RDP, etc.)
    internal_kw = ("sap.", "oracle", "vpn.", "rds.", "rdp.", "citrix", "adms.", "fax", "smarthost", "evolve.", "insite.")
    internal_subs = [s for s in subdomains if any(kw in s.lower() for kw in internal_kw)]
    if internal_subs:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "subdomain_enum",
            "finding_type": "internal_infra_exposure",
            "finding_value": f"{len(internal_subs)} internal infrastructure subdomains exposed (SAP, VPN, etc.)",
            "severity": "medium",
            "details": json.dumps({"subdomains": internal_subs[:20]}),
            "source_tool": "subfinder",
        })

    return rows


def parse_dig(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract IP addresses and DNS records from dig results."""
    rows = []
    if not scan_data or not scan_data.get("success"):
        return rows

    stdout = scan_data.get("stdout", "")
    if not stdout.strip():
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_lookup",
            "finding_type": "no_dns_records",
            "finding_value": f"No DNS records found for {domain} — domain may be parked or inactive",
            "severity": "info",
            "details": json.dumps({"raw": "empty dig output"}),
            "source_tool": "dig",
        })
        return rows

    # Parse A records for IPs
    a_records = re.findall(r"IN\s+A\s+(\d+\.\d+\.\d+\.\d+)", stdout)
    if a_records:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_lookup",
            "finding_type": "ip_addresses",
            "finding_value": f"{len(a_records)} IP address(es): {', '.join(a_records[:5])}",
            "severity": "info",
            "details": json.dumps({"ips": a_records}),
            "source_tool": "dig",
        })

    # Parse MX records
    mx_records = re.findall(r"IN\s+MX\s+\d+\s+(\S+)", stdout)
    if mx_records:
        mx_clean = [m.rstrip(".") for m in mx_records]
        provider = "unknown"
        mx_joined = " ".join(mx_clean).lower()
        if "outlook" in mx_joined or "protection.outlook" in mx_joined:
            provider = "Microsoft 365"
        elif "google" in mx_joined or "googlemail" in mx_joined:
            provider = "Google Workspace"
        elif "mailhostbox" in mx_joined:
            provider = "MailHostBox"
        elif "secureserver" in mx_joined or "godaddy" in mx_joined:
            provider = "GoDaddy"
        elif "proofpoint" in mx_joined:
            provider = "Proofpoint"
        elif "mimecast" in mx_joined:
            provider = "Mimecast"
        elif "barracuda" in mx_joined:
            provider = "Barracuda"
        elif "idmi.net" in mx_joined:
            provider = "IDMI Filtering"
        elif "zoho" in mx_joined:
            provider = "Zoho"

        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_lookup",
            "finding_type": "mail_infrastructure",
            "finding_value": f"Mail provider: {provider} ({len(mx_clean)} MX records)",
            "severity": "info",
            "details": json.dumps({"provider": provider, "mx_records": mx_clean}),
            "source_tool": "dig",
        })

    # Parse NS records
    ns_records = re.findall(r"IN\s+NS\s+(\S+)", stdout)
    if ns_records:
        ns_clean = [n.rstrip(".") for n in ns_records]
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_lookup",
            "finding_type": "nameservers",
            "finding_value": f"Nameservers: {', '.join(ns_clean[:4])}",
            "severity": "info",
            "details": json.dumps({"nameservers": ns_clean}),
            "source_tool": "dig",
        })

    return rows


def parse_whois(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract WHOIS exposure findings."""
    rows = []
    if not scan_data or not scan_data.get("success"):
        return rows

    stdout = scan_data.get("stdout", "")
    parsed = scan_data.get("parsed", {})

    # Check registrar info
    registrars = parsed.get("registrar", [])
    created_dates = parsed.get("created", [])
    expiry_dates = parsed.get("expires", [])

    registrar = registrars[0] if registrars else "unknown"
    created = created_dates[0] if created_dates else "unknown"
    expires = expiry_dates[0] if expiry_dates else "unknown"

    # Basic domain registration info
    rows.append({
        "competitor_id": comp_id,
        "domain": domain,
        "scan_type": "whois",
        "finding_type": "registration_info",
        "finding_value": f"Registrar: {registrar}, Created: {created[:10]}, Expires: {expires[:10]}",
        "severity": "info",
        "details": json.dumps({
            "registrar": registrar,
            "created": created,
            "expires": expires,
        }),
        "source_tool": "whois",
    })

    # Check for domain expiry within 6 months
    if expires and expires != "unknown":
        try:
            exp_str = expires.replace("Z", "+00:00")
            exp_dt = datetime.fromisoformat(exp_str)
            now = datetime.now(timezone.utc)
            days_left = (exp_dt - now).days
            if days_left < 180:
                rows.append({
                    "competitor_id": comp_id,
                    "domain": domain,
                    "scan_type": "whois",
                    "finding_type": "domain_expiry_risk",
                    "finding_value": f"Domain expires in {days_left} days ({expires[:10]})",
                    "severity": "medium" if days_left < 90 else "low",
                    "details": json.dumps({"days_until_expiry": days_left, "expiry_date": expires}),
                    "source_tool": "whois",
                })
        except (ValueError, TypeError):
            pass

    # Check for exposed PII in WHOIS (non-redacted registrant info)
    pii_patterns = {
        "registrant_name": re.findall(r"Registrant Name:\s*(.+?)(?:\n|$)", stdout),
        "registrant_email": re.findall(r"Registrant Email:\s*(\S+@\S+)", stdout),
        "registrant_phone": re.findall(r"Registrant Phone:\s*(\+?\d[\d\s\-\.]+)", stdout),
        "registrant_address": re.findall(r"Registrant Street:\s*(.+?)(?:\n|$)", stdout),
        "registrant_city": re.findall(r"Registrant City:\s*(.+?)(?:\n|$)", stdout),
        "admin_name": re.findall(r"Admin Name:\s*(.+?)(?:\n|$)", stdout),
        "admin_email": re.findall(r"Admin Email:\s*(\S+@\S+)", stdout),
        "tech_name": re.findall(r"Tech Name:\s*(.+?)(?:\n|$)", stdout),
        "tech_email": re.findall(r"Tech Email:\s*(\S+@\S+)", stdout),
    }

    # Filter out proxy/redacted entries
    exposed_fields = {}
    for field, values in pii_patterns.items():
        for val in values:
            val = val.strip()
            if val and not any(kw in val.lower() for kw in (
                "redacted", "not available", "data protected", "privacy",
                "contact privacy", "whois", "proxy", "select request",
                "please query", "gdpr", "select contact domain"
            )):
                # Also skip godaddy/registrar whois result links
                if "godaddy.com/whois" in val.lower() or "publicdomainregistry" in val.lower():
                    continue
                exposed_fields.setdefault(field, []).append(val)

    if exposed_fields:
        exposed_count = sum(len(v) for v in exposed_fields.values())
        summary_parts = []
        for field, values in exposed_fields.items():
            summary_parts.append(f"{field}: {values[0]}")
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "whois",
            "finding_type": "whois_pii_exposure",
            "finding_value": f"{exposed_count} PII fields exposed in WHOIS — {'; '.join(summary_parts[:3])}",
            "severity": "high" if exposed_count >= 5 else "medium",
            "details": json.dumps(exposed_fields),
            "source_tool": "whois",
        })

    # Check DNSSEC status
    if "DNSSEC: unsigned" in stdout or "DNSSEC: Unsigned" in stdout:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "whois",
            "finding_type": "dnssec_disabled",
            "finding_value": f"DNSSEC is NOT enabled for {domain}",
            "severity": "low",
            "details": json.dumps({"dnssec": "unsigned"}),
            "source_tool": "whois",
        })
    elif "DNSSEC: signedDelegation" in stdout:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "whois",
            "finding_type": "dnssec_enabled",
            "finding_value": f"DNSSEC is enabled for {domain}",
            "severity": "info",
            "details": json.dumps({"dnssec": "signedDelegation"}),
            "source_tool": "whois",
        })

    return rows


def parse_harvester(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract emails, IPs, hosts, and interesting URLs from theHarvester results."""
    rows = []
    if not scan_data or not scan_data.get("success"):
        return rows

    stdout = scan_data.get("stdout", "")

    # Extract emails
    email_match = re.search(r"\[\*\] Emails found:.*?\n-+\n(.*?)(?:\n\n|\[\*\])", stdout, re.DOTALL)
    emails = []
    if email_match:
        emails = [e.strip() for e in email_match.group(1).strip().split("\n") if e.strip() and "@" in e]

    if emails:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "email_harvest",
            "finding_type": "emails_found",
            "finding_value": f"{len(emails)} email(s) found: {', '.join(emails[:5])}",
            "severity": "medium",
            "details": json.dumps({"emails": emails}),
            "source_tool": "theHarvester",
        })

    # Extract IPs
    ip_match = re.search(r"\[\*\] IPs found:.*?\n-+\n(.*?)(?:\n\n|\[\*\])", stdout, re.DOTALL)
    ips = []
    if ip_match:
        ips = [ip.strip() for ip in ip_match.group(1).strip().split("\n") if ip.strip()]

    if ips:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "email_harvest",
            "finding_type": "ips_discovered",
            "finding_value": f"{len(ips)} IP(s) from harvester: {', '.join(ips[:5])}",
            "severity": "info",
            "details": json.dumps({"ips": ips}),
            "source_tool": "theHarvester",
        })

    # Extract host count
    host_match = re.search(r"\[\*\] Hosts found:\s*(\d+)", stdout)
    if not host_match:
        host_section = re.search(r"\[\*\] Hosts found:.*?\n-+\n(.*?)(?:\n\n|$)", stdout, re.DOTALL)
        if host_section:
            hosts = [h.strip() for h in host_section.group(1).strip().split("\n") if h.strip()]
            host_count = len(hosts)
        else:
            host_count = 0
            hosts = []
    else:
        host_count = int(host_match.group(1))
        hosts = []

    if host_count > 0:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "email_harvest",
            "finding_type": "hosts_discovered",
            "finding_value": f"{host_count} host(s) discovered via theHarvester",
            "severity": _severity_from_count(host_count, (0, 10, 50)),
            "details": json.dumps({"count": host_count, "sample": hosts[:20]}),
            "source_tool": "theHarvester",
        })

    # Extract ASNs
    asn_match = re.search(r"\[\*\] ASNS found:.*?\n-+\n(.*?)(?:\n\n|\[\*\])", stdout, re.DOTALL)
    if asn_match:
        asns = [a.strip() for a in asn_match.group(1).strip().split("\n") if a.strip()]
        if asns:
            rows.append({
                "competitor_id": comp_id,
                "domain": domain,
                "scan_type": "email_harvest",
                "finding_type": "asns_found",
                "finding_value": f"ASNs: {', '.join(asns[:5])}",
                "severity": "info",
                "details": json.dumps({"asns": asns}),
                "source_tool": "theHarvester",
            })

    # Extract interesting URLs
    url_match = re.search(r"\[\*\] Interesting Urls found:.*?\n-+\n(.*?)(?:\n\n|\[\*\])", stdout, re.DOTALL)
    if url_match:
        urls = [u.strip() for u in url_match.group(1).strip().split("\n") if u.strip()]
        if urls:
            # Flag OAuth/login URLs as potential attack surface
            auth_urls = [u for u in urls if any(kw in u.lower() for kw in ("login", "oauth", "auth", "account"))]
            rows.append({
                "competitor_id": comp_id,
                "domain": domain,
                "scan_type": "email_harvest",
                "finding_type": "interesting_urls",
                "finding_value": f"{len(urls)} interesting URL(s) found, {len(auth_urls)} auth-related",
                "severity": "low" if auth_urls else "info",
                "details": json.dumps({"urls": urls[:15], "auth_urls": auth_urls[:10]}),
                "source_tool": "theHarvester",
            })

    # If nothing was found at all
    if not rows:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "email_harvest",
            "finding_type": "no_results",
            "finding_value": f"theHarvester found no significant results for {domain}",
            "severity": "info",
            "details": json.dumps({"raw_length": len(stdout)}),
            "source_tool": "theHarvester",
        })

    return rows


def parse_dnsrecon(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract DNS enumeration findings from dnsrecon results."""
    rows = []
    if not scan_data or not scan_data.get("success"):
        return rows

    stderr = scan_data.get("stderr", "")  # dnsrecon outputs to stderr as INFO lines

    # Parse record types
    records: dict[str, list[str]] = {}
    for line in stderr.split("\n"):
        # Match lines like: INFO \t SOA ns1-09.azure-dns.com 13.107.236.9
        rec_match = re.search(r"INFO\s+\t\s+(SOA|NS|MX|A|AAAA|TXT|SRV|CNAME)\s+(.+)", line)
        if rec_match:
            rtype = rec_match.group(1)
            rdata = rec_match.group(2).strip()
            records.setdefault(rtype, []).append(rdata)

    if not records:
        return rows

    # Summary of all DNS records
    record_summary_parts = [f"{rtype}: {len(vals)}" for rtype, vals in sorted(records.items())]
    rows.append({
        "competitor_id": comp_id,
        "domain": domain,
        "scan_type": "dns_recon",
        "finding_type": "dns_records_summary",
        "finding_value": f"DNS records — {', '.join(record_summary_parts)}",
        "severity": "info",
        "details": json.dumps({rtype: vals[:10] for rtype, vals in records.items()}),
        "source_tool": "dnsrecon",
    })

    # Check DNSSEC from dnsrecon output
    if "DNSSEC is configured" in stderr:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_recon",
            "finding_type": "dnssec_configured",
            "finding_value": f"DNSSEC is properly configured for {domain}",
            "severity": "info",
            "details": json.dumps({"dnssec": True}),
            "source_tool": "dnsrecon",
        })
    elif "No answer for DNSSEC" in stderr:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_recon",
            "finding_type": "dnssec_missing",
            "finding_value": f"DNSSEC not configured for {domain} — vulnerable to DNS spoofing",
            "severity": "low",
            "details": json.dumps({"dnssec": False}),
            "source_tool": "dnsrecon",
        })

    # Check SPF/DMARC from TXT records
    txt_records = records.get("TXT", [])
    has_spf = any("v=spf1" in t for t in txt_records)
    has_dmarc = any("v=DMARC1" in t or "_dmarc" in t for t in txt_records)

    if not has_spf:
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_recon",
            "finding_type": "missing_spf",
            "finding_value": f"No SPF record found for {domain} — email spoofing possible",
            "severity": "medium",
            "details": json.dumps({"spf": False}),
            "source_tool": "dnsrecon",
        })

    if has_dmarc:
        dmarc_txt = next((t for t in txt_records if "DMARC" in t or "_dmarc" in t), "")
        policy = "none"
        if "p=reject" in dmarc_txt:
            policy = "reject"
        elif "p=quarantine" in dmarc_txt:
            policy = "quarantine"
        elif "p=none" in dmarc_txt:
            policy = "none"
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_recon",
            "finding_type": "dmarc_policy",
            "finding_value": f"DMARC policy: {policy} for {domain}",
            "severity": "info" if policy == "reject" else ("low" if policy == "quarantine" else "medium"),
            "details": json.dumps({"dmarc_policy": policy, "record": dmarc_txt[:200]}),
            "source_tool": "dnsrecon",
        })

    # Bind version exposure
    bind_match = re.search(r"Bind Version for .+ (.+)", stderr)
    if bind_match:
        version = bind_match.group(1).strip().strip('"')
        rows.append({
            "competitor_id": comp_id,
            "domain": domain,
            "scan_type": "dns_recon",
            "finding_type": "bind_version_exposed",
            "finding_value": f"DNS server BIND version exposed: {version}",
            "severity": "low",
            "details": json.dumps({"bind_version": version}),
            "source_tool": "dnsrecon",
        })

    return rows


def parse_intel_domain(scan_data: dict, domain: str, comp_id: int) -> list[dict]:
    """Extract domain intelligence findings."""
    rows = []
    if not scan_data:
        return rows

    risk_score = scan_data.get("risk_score", 0)
    sources = scan_data.get("sources", {})
    dns_ips = sources.get("dns", [])
    whois_snippet = sources.get("whois_snippet", "")

    # Risk score finding
    severity = "info"
    if risk_score > 70:
        severity = "high"
    elif risk_score > 40:
        severity = "medium"
    elif risk_score > 10:
        severity = "low"

    rows.append({
        "competitor_id": comp_id,
        "domain": domain,
        "scan_type": "intel_domain",
        "finding_type": "risk_score",
        "finding_value": f"Domain intel risk score: {risk_score}/100 for {domain}",
        "severity": severity,
        "details": json.dumps({
            "risk_score": risk_score,
            "dns_ips": [ip for ip in dns_ips if ip],
            "whois_snippet_len": len(whois_snippet),
        }),
        "source_tool": "intel_domain",
    })

    return rows


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_company(company_name: str, company_data: dict) -> list[dict]:
    """Process all scans for a single company, return finding rows."""
    domain = company_data.get("domain", "")
    comp_id = company_data.get("id")

    # Verify against our mapping
    expected_id = COMPETITOR_ID_MAP.get(domain)
    if expected_id is None:
        print(f"  WARNING: {domain} not in competitor ID map — skipping")
        return []
    if comp_id != expected_id:
        print(f"  WARNING: ID mismatch for {domain}: JSON has {comp_id}, map has {expected_id}. Using map value.")
        comp_id = expected_id

    scans = company_data.get("scans", {})
    all_rows = []

    all_rows.extend(parse_subfinder(scans.get("subfinder"), domain, comp_id))
    all_rows.extend(parse_dig(scans.get("dig"), domain, comp_id))
    all_rows.extend(parse_whois(scans.get("whois"), domain, comp_id))
    all_rows.extend(parse_harvester(scans.get("harvester"), domain, comp_id))
    all_rows.extend(parse_dnsrecon(scans.get("dnsrecon"), domain, comp_id))
    all_rows.extend(parse_intel_domain(scans.get("intel_domain"), domain, comp_id))

    return all_rows


def main() -> None:
    print("=" * 70)
    print("Prometheus PRIME OSINT → Permian Pulse D1 Ingestion")
    print("=" * 70)

    # Load data
    print(f"\n[1/4] Loading {JSON_FILE.name}...")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} companies")

    # Load OAuth token
    print("\n[2/4] Loading wrangler OAuth token...")
    token = load_oauth_token()
    print(f"  Token loaded ({len(token)} chars)")

    # Ensure table exists
    print("\n[3/4] Ensuring competitor_osint table exists...")
    create_sql = """
    CREATE TABLE IF NOT EXISTS competitor_osint (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competitor_id INTEGER,
        domain TEXT,
        scan_type TEXT NOT NULL,
        finding_type TEXT,
        finding_value TEXT,
        severity TEXT DEFAULT 'info',
        details TEXT,
        source_tool TEXT,
        scanned_at TEXT DEFAULT (datetime('now'))
    )
    """
    try:
        result = d1_execute(token, create_sql)
        if result.get("success"):
            print("  Table ready")
        else:
            print(f"  Table creation issue: {result.get('errors', [])}")
    except Exception as exc:
        print(f"  Table creation error: {exc}")

    # Create index for fast querying
    try:
        d1_execute(token, "CREATE INDEX IF NOT EXISTS idx_osint_competitor ON competitor_osint(competitor_id)")
        d1_execute(token, "CREATE INDEX IF NOT EXISTS idx_osint_severity ON competitor_osint(severity)")
        d1_execute(token, "CREATE INDEX IF NOT EXISTS idx_osint_scan_type ON competitor_osint(scan_type)")
    except Exception:
        pass  # Indexes may already exist

    # Process all companies
    print("\n[4/4] Processing OSINT data and ingesting into D1...")
    total_rows = 0
    total_inserted = 0
    company_stats: dict[str, int] = {}

    for company_name, company_data in data.items():
        domain = company_data.get("domain", "unknown")
        comp_id = COMPETITOR_ID_MAP.get(domain, company_data.get("id", 0))
        print(f"\n  [{comp_id:2d}] {company_name} ({domain})")

        rows = process_company(company_name, company_data)
        total_rows += len(rows)
        company_stats[company_name] = len(rows)

        if rows:
            inserted = d1_batch_insert(token, rows)
            total_inserted += inserted
            print(f"      {len(rows)} findings parsed, {inserted} inserted")

            # Print severity breakdown
            sev_counts: dict[str, int] = {}
            for r in rows:
                sev_counts[r["severity"]] = sev_counts.get(r["severity"], 0) + 1
            sev_str = ", ".join(f"{s}: {c}" for s, c in sorted(sev_counts.items()))
            print(f"      Severities: {sev_str}")
        else:
            print("      No findings")

    # Summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"  Companies processed:  {len(data)}")
    print(f"  Total findings:       {total_rows}")
    print(f"  Total inserted:       {total_inserted}")
    print(f"\n  Severity breakdown:")
    all_severities: dict[str, int] = {"info": 0, "low": 0, "medium": 0, "high": 0}
    # Re-process for totals (faster than re-querying)
    for company_name, company_data in data.items():
        for row in process_company(company_name, company_data):
            all_severities[row["severity"]] = all_severities.get(row["severity"], 0) + 1
    for sev in ("high", "medium", "low", "info"):
        print(f"    {sev:8s}: {all_severities.get(sev, 0)}")

    print(f"\n  Top 5 companies by findings:")
    for name, count in sorted(company_stats.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name:40s} {count} findings")

    print("\nDone.")


if __name__ == "__main__":
    main()
