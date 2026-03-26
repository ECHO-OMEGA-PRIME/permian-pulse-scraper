"""D1 REST API direct ingestion — bypasses wrangler shell escaping."""
import json
import sys
import time
import urllib.request
import urllib.error

ACCOUNT_ID = "b9af3a4bf161132bb7e5d3d365fb8bb0"
DB_ID = "4a2c1d02-c377-4e70-b8f8-aec879f77ebb"
SQL_FILE = "ingest_prometheus_final_dedup.sql"

def get_oauth_token() -> str:
    import tomllib
    import os
    config_path = os.path.join(os.environ.get("APPDATA", ""), "xdg.config", ".wrangler", "config", "default.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    return config["oauth_token"]

def read_sql_statements(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        lines.append(line)
    raw = "\n".join(lines)
    statements = []
    current = []
    for line in raw.split("\n"):
        current.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []
    return statements

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

if __name__ == "__main__":
    token = get_oauth_token()
    stmts = read_sql_statements(SQL_FILE)
    print(f"Parsed {len(stmts)} SQL statements")

    # Test connectivity
    test = execute_d1_query(token, "SELECT COUNT(*) as n FROM competitors")
    if not test.get("success"):
        print(f"D1 connectivity failed: {test}")
        sys.exit(1)
    print(f"D1 connected. competitors: {test['result'][0]['results'][0]['n']} rows")

    success = 0
    failed = 0
    for i, stmt in enumerate(stmts):
        # Preview
        preview = stmt[:80].replace("\n", " ")
        print(f"[{i+1}/{len(stmts)}] {preview}...", end=" ", flush=True)

        result = execute_d1_query(token, stmt)
        if result.get("success"):
            changes = 0
            if result.get("result") and len(result["result"]) > 0:
                changes = result["result"][0].get("meta", {}).get("changes", 0)
            print(f"OK ({changes} rows)")
            success += 1
        else:
            errors = result.get("errors", [])
            msg = errors[0].get("message", "unknown") if errors else "unknown"
            print(f"FAILED: {msg[:120]}")
            failed += 1

        # Small delay to avoid rate limits
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE: {success}/{len(stmts)} OK, {failed} failed")

    # Verify counts
    tables = ["patents", "chemical_formulations", "market_intel", "competitor_osint", "competitor_financials"]
    print(f"\nTable counts:")
    for table in tables:
        r = execute_d1_query(token, f"SELECT COUNT(*) as n FROM {table}")
        if r.get("success") and r.get("result"):
            n = r["result"][0]["results"][0]["n"]
            print(f"  {table:30s} {n} rows")
