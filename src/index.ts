/**
 * PERMIAN PULSE COMPETITOR SCRAPER v2.0.0
 * Scrapes 24+ oilfield chemical competitor websites.
 * Collects intel from SEC EDGAR, Google News, PubChem, SecurityTrails, USPTO.
 * Extracts: company info, products, services, team, contact, tech stack, exposed APIs,
 *           patents, chemical formulations, financial data, OSINT, market intel.
 * Runs reverse engineering engines on scraped data.
 * Stores all intelligence in D1 + Shared Brain.
 */

export interface Env {
  DB: D1Database;
  CACHE: KVNamespace;
  SHARED_BRAIN: Fetcher;
  ENGINE_RUNTIME: Fetcher;
  KNOWLEDGE_FORGE: Fetcher;
  ECHO_API_KEY: string;
  WORKER_VERSION: string;
  SECURITYTRAILS_API_KEY: string;
  NEWSAPI_KEY: string;
}

// ─── COMPETITOR REGISTRY ───────────────────────────────────────────────────────
// From JP business discussion transcript (2026-03-16)
// Priority targets marked with ★

interface Competitor {
  name: string;
  search_terms: string[];
  priority: 'high' | 'medium' | 'low';
  notes: string;
}

const COMPETITORS: Competitor[] = [
  { name: 'Champion X', search_terms: ['championx.com', 'Champion X oilfield chemicals'], priority: 'high', notes: 'JP top 3 — huge database potential' },
  { name: 'Coastal Chemical', search_terms: ['coastalchem.com', 'Coastal Chemical oilfield'], priority: 'high', notes: 'JP top 3 — Brenntag subsidiary, has own lab management platform with stored data' },
  { name: 'Imperative', search_terms: ['imperativechemicals.com', 'Imperative Chemical Partners oilfield'], priority: 'high', notes: 'JP top 3 — largest privately held oilfield chem co in North America, 900+ employees, 45 locations, Midland TX HQ' },
  { name: 'Core Chemical', search_terms: ['corechemical.com', 'Core Chemical oilfield'], priority: 'medium', notes: '' },
  { name: 'Corrosion LTD', search_terms: ['corrosionltd.com', 'Corrosion LTD oilfield'], priority: 'medium', notes: '' },
  { name: 'Credence IMC', search_terms: ['creedence-energy.com', 'Creedence Energy Services oilfield'], priority: 'medium', notes: 'May be Creedence Energy Services — production + midstream chemicals' },
  { name: 'Enduro Tech', search_terms: ['endurotech.com', 'Enduro Tech oilfield chemicals'], priority: 'medium', notes: '' },
  { name: 'Energy Flow', search_terms: ['energyflow.com', 'Energy Flow oilfield'], priority: 'medium', notes: '' },
  { name: 'Infinity Energy Solutions', search_terms: ['infinityenergysolutions.com', 'Infinity Energy Solutions oilfield'], priority: 'medium', notes: '' },
  { name: 'Integrity Industries', search_terms: ['integrityindustries.com', 'Integrity Industries oilfield'], priority: 'medium', notes: '' },
  { name: 'Interface Treating', search_terms: ['interfacetreating.com', 'Interface Treating oilfield'], priority: 'medium', notes: '' },
  { name: 'Max Flow', search_terms: ['maxflow oilfield chemicals', 'Max Flow energy'], priority: 'medium', notes: '' },
  { name: 'OT Oilfield Chemicals', search_terms: ['otoilfieldchemicals.com', 'OT Oilfield Chemicals'], priority: 'medium', notes: '' },
  { name: 'Perfect Chemical Solutions', search_terms: ['perfectchemicalsolutions.com', 'Perfect Chemical Solutions'], priority: 'medium', notes: '' },
  { name: 'Revive Energy Solutions', search_terms: ['reviveenergysolutions.com', 'Revive Energy Solutions'], priority: 'medium', notes: '' },
  { name: 'SGB Solutions', search_terms: ['sgblp.com', 'SGB Solutions oilfield Midland TX'], priority: 'medium', notes: 'Midland TX based, 450+ chemical products, founded 2012' },
  { name: 'Sol Nexus', search_terms: ['solnexus.com', 'Sol Nexus oilfield chemicals'], priority: 'medium', notes: '' },
  { name: 'SoluGen', search_terms: ['solugen.com', 'SoluGen chemicals'], priority: 'medium', notes: '' },
  { name: 'Specialty Intermediates', search_terms: ['specialtyintermediates.com', 'Specialty Intermediates'], priority: 'medium', notes: '' },
  { name: 'TruCam Solutions', search_terms: ['trucamsolutions.com', 'TruCam Solutions oilfield'], priority: 'medium', notes: '' },
  { name: 'Aquarius Chemical', search_terms: ['aquariuschemical.com', 'Aquarius Chemical oilfield'], priority: 'low', notes: '' },
  { name: 'Basin Chemical', search_terms: ['basinchemical.com', 'Basin Chemical oilfield'], priority: 'low', notes: '' },
  { name: 'JCAN', search_terms: ['jcan oilfield chemicals', 'JCAN chemical'], priority: 'low', notes: '' },
  { name: 'Suncoast', search_terms: ['suncoast fuels solvents', 'Suncoast chemical'], priority: 'low', notes: 'Fuels and solvents only per JP' },
];

// ─── D1 SCHEMA ─────────────────────────────────────────────────────────────────

const SCHEMA = `
CREATE TABLE IF NOT EXISTS competitors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  website_url TEXT,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  last_scraped TEXT,
  scrape_count INTEGER DEFAULT 0,
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scrape_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  page_type TEXT DEFAULT 'unknown',
  title TEXT,
  content_text TEXT,
  content_html TEXT,
  meta_description TEXT,
  meta_keywords TEXT,
  links_found INTEGER DEFAULT 0,
  status_code INTEGER,
  content_length INTEGER,
  scraped_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_scrape_competitor ON scrape_results(competitor_id, scraped_at DESC);

CREATE TABLE IF NOT EXISTS extracted_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  data_type TEXT NOT NULL,
  data_key TEXT NOT NULL,
  data_value TEXT,
  confidence REAL DEFAULT 0.5,
  source_url TEXT,
  extracted_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_extracted_type ON extracted_data(competitor_id, data_type);

CREATE TABLE IF NOT EXISTS tech_stack (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  technology TEXT NOT NULL,
  category TEXT NOT NULL,
  evidence TEXT,
  detected_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_tech_competitor ON tech_stack(competitor_id);

CREATE TABLE IF NOT EXISTS exposed_endpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  endpoint_url TEXT NOT NULL,
  method TEXT DEFAULT 'GET',
  endpoint_type TEXT,
  response_sample TEXT,
  requires_auth INTEGER DEFAULT 0,
  severity TEXT DEFAULT 'info',
  discovered_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_endpoints_competitor ON exposed_endpoints(competitor_id);

CREATE TABLE IF NOT EXISTS reveng_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  engine_id TEXT,
  report_type TEXT NOT NULL,
  summary TEXT,
  full_report TEXT,
  score REAL,
  generated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_reveng_competitor ON reveng_reports(competitor_id);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  product_name TEXT NOT NULL,
  category TEXT,
  description TEXT,
  price_info TEXT,
  source_url TEXT,
  extracted_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_products_competitor ON products(competitor_id);

CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  contact_type TEXT NOT NULL,
  contact_value TEXT NOT NULL,
  label TEXT,
  source_url TEXT,
  extracted_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_contacts_competitor ON contacts(competitor_id);

CREATE TABLE IF NOT EXISTS scrape_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  priority INTEGER DEFAULT 5,
  attempts INTEGER DEFAULT 0,
  last_attempt TEXT,
  error TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(url)
);
CREATE INDEX IF NOT EXISTS idx_queue_status ON scrape_queue(status, priority DESC);

CREATE TABLE IF NOT EXISTS chemical_formulations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER,
  product_name TEXT NOT NULL,
  manufacturer TEXT,
  product_type TEXT,
  cas_number TEXT,
  chemical_name TEXT,
  concentration_min REAL,
  concentration_max REAL,
  concentration_unit TEXT DEFAULT '%',
  source_document TEXT,
  source_url TEXT,
  confidence REAL DEFAULT 0.5,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_cf_competitor ON chemical_formulations(competitor_id);
CREATE INDEX IF NOT EXISTS idx_cf_product ON chemical_formulations(product_name);
CREATE INDEX IF NOT EXISTS idx_cf_cas ON chemical_formulations(cas_number);

CREATE TABLE IF NOT EXISTS patents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER,
  patent_number TEXT UNIQUE,
  title TEXT NOT NULL,
  assignee TEXT,
  filing_date TEXT,
  grant_date TEXT,
  abstract TEXT,
  key_claims TEXT,
  chemical_components TEXT,
  relevance TEXT DEFAULT 'medium',
  source_url TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_pat_competitor ON patents(competitor_id);
CREATE INDEX IF NOT EXISTS idx_pat_assignee ON patents(assignee);
CREATE INDEX IF NOT EXISTS idx_pat_filing ON patents(filing_date);

CREATE TABLE IF NOT EXISTS market_intel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER,
  category TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value TEXT,
  unit TEXT,
  source TEXT,
  source_url TEXT,
  year TEXT,
  confidence REAL DEFAULT 0.5,
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_mi_category ON market_intel(category);
CREATE INDEX IF NOT EXISTS idx_mi_competitor ON market_intel(competitor_id);

CREATE TABLE IF NOT EXISTS competitor_osint (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER NOT NULL,
  domain TEXT,
  scan_type TEXT NOT NULL,
  finding_type TEXT NOT NULL,
  finding_value TEXT NOT NULL,
  severity TEXT DEFAULT 'info',
  details TEXT,
  source_tool TEXT,
  scanned_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_osint_competitor ON competitor_osint(competitor_id);
CREATE INDEX IF NOT EXISTS idx_osint_severity ON competitor_osint(severity);
CREATE INDEX IF NOT EXISTS idx_osint_scan ON competitor_osint(scan_type);

CREATE TABLE IF NOT EXISTS competitor_financials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER,
  company_name TEXT NOT NULL,
  cik TEXT,
  revenue REAL,
  revenue_unit TEXT DEFAULT 'USD',
  period TEXT,
  filing_type TEXT,
  filing_date TEXT,
  market_cap REAL,
  employees INTEGER,
  sic_code TEXT,
  sic_description TEXT,
  source_url TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_fin_competitor ON competitor_financials(competitor_id);
CREATE INDEX IF NOT EXISTS idx_fin_company ON competitor_financials(company_name);

CREATE TABLE IF NOT EXISTS intel_collection_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  collection_type TEXT NOT NULL,
  records_collected INTEGER DEFAULT 0,
  records_new INTEGER DEFAULT 0,
  errors TEXT,
  duration_ms INTEGER,
  started_at TEXT DEFAULT (datetime('now')),
  completed_at TEXT,
  status TEXT DEFAULT 'running'
);
CREATE INDEX IF NOT EXISTS idx_icl_source ON intel_collection_log(source);
CREATE INDEX IF NOT EXISTS idx_icl_status ON intel_collection_log(status);

CREATE TABLE IF NOT EXISTS news_intel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competitor_id INTEGER,
  headline TEXT NOT NULL,
  source_name TEXT,
  published_at TEXT,
  url TEXT UNIQUE,
  snippet TEXT,
  sentiment TEXT,
  relevance REAL DEFAULT 0.5,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);
CREATE INDEX IF NOT EXISTS idx_news_competitor ON news_intel(competitor_id);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_intel(published_at);
`;

// ─── HELPERS ───────────────────────────────────────────────────────────────────

function log(level: string, msg: string, data?: Record<string, unknown>) {
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, worker: 'permian-pulse-scraper', msg, ...data }));
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  });
}

// ─── GOOGLE SEARCH (find competitor URLs) ──────────────────────────────────────

async function searchForWebsite(competitor: Competitor): Promise<string | null> {
  // Try common domain patterns first
  const domainGuesses = competitor.search_terms
    .filter(t => t.includes('.com') || t.includes('.net') || t.includes('.io'))
    .map(t => t.startsWith('http') ? t : `https://${t}`);

  for (const url of domainGuesses) {
    try {
      const resp = await fetch(url, {
        method: 'HEAD',
        redirect: 'follow',
        signal: AbortSignal.timeout(8000),
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36' },
      });
      if (resp.ok || resp.status === 403) {
        return new URL(resp.url).origin;
      }
    } catch { /* try next */ }
  }

  // Fallback: search via Workers AI or return null
  return null;
}

// ─── PAGE SCRAPER ──────────────────────────────────────────────────────────────

interface ScrapedPage {
  url: string;
  statusCode: number;
  title: string;
  metaDescription: string;
  metaKeywords: string;
  bodyText: string;
  html: string;
  links: string[];
  emails: string[];
  phones: string[];
  techSignals: TechSignal[];
}

interface TechSignal {
  technology: string;
  category: string;
  evidence: string;
}

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

async function scrapePage(url: string): Promise<ScrapedPage | null> {
  try {
    const resp = await fetch(url, {
      headers: { 'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9' },
      redirect: 'follow',
      signal: AbortSignal.timeout(15000),
    });

    if (!resp.ok && resp.status !== 403) return null;

    const html = await resp.text();
    const bodyText = extractText(html);
    const title = extractTag(html, 'title');
    const metaDescription = extractMeta(html, 'description');
    const metaKeywords = extractMeta(html, 'keywords');
    const links = extractLinks(html, url);
    const emails = extractEmails(bodyText + html);
    const phones = extractPhones(bodyText);
    const techSignals = detectTechStack(html, resp.headers);

    return { url, statusCode: resp.status, title, metaDescription, metaKeywords, bodyText: bodyText.slice(0, 50000), html: html.slice(0, 200000), links, emails, phones, techSignals };
  } catch (err) {
    log('error', `Failed to scrape ${url}`, { error: String(err) });
    return null;
  }
}

function extractText(html: string): string {
  return html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractTag(html: string, tag: string): string {
  const m = html.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i'));
  return m ? m[1].trim() : '';
}

function extractMeta(html: string, name: string): string {
  const m = html.match(new RegExp(`<meta[^>]+name=["']${name}["'][^>]+content=["']([^"']+)["']`, 'i'))
    || html.match(new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+name=["']${name}["']`, 'i'));
  return m ? m[1].trim() : '';
}

function extractLinks(html: string, baseUrl: string): string[] {
  const links: string[] = [];
  const re = /href=["']([^"'#]+)["']/gi;
  let m;
  const origin = new URL(baseUrl).origin;
  while ((m = re.exec(html)) !== null) {
    try {
      const href = m[1];
      if (href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) continue;
      const full = href.startsWith('http') ? href : new URL(href, origin).href;
      if (full.startsWith(origin) && !links.includes(full)) links.push(full);
    } catch { /* skip bad URLs */ }
  }
  return links.slice(0, 100);
}

function extractEmails(text: string): string[] {
  const re = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  const found = text.match(re) || [];
  return [...new Set(found)].filter(e => !e.includes('example.com') && !e.includes('sentry'));
}

function extractPhones(text: string): string[] {
  // Match real phone numbers with area codes — require separator or parentheses to avoid matching random digit sequences
  const re = /(?:\+?1[-.\s])?\(?[2-9]\d{2}\)[-.\s][2-9]\d{2}[-.\s]\d{4}/g;
  const found = text.match(re) || [];
  // Filter out obvious non-phones (dates, IDs, sequences)
  return [...new Set(found)].filter(p => {
    const digits = p.replace(/\D/g, '');
    if (digits.length < 10 || digits.length > 11) return false;
    // Area code can't start with 0 or 1
    const areaCode = digits.length === 11 ? digits.substring(1, 4) : digits.substring(0, 3);
    if (areaCode[0] === '0' || areaCode[0] === '1') return false;
    // Reject sequential/repeated digits
    if (/^(\d)\1{6,}/.test(digits)) return false;
    return true;
  }).slice(0, 10);
}

// ─── TECH STACK DETECTION ──────────────────────────────────────────────────────

function detectTechStack(html: string, headers: Headers): TechSignal[] {
  const signals: TechSignal[] = [];
  const lowerHtml = html.toLowerCase();

  // Server/platform
  const server = headers.get('server');
  if (server) signals.push({ technology: server, category: 'server', evidence: `Server header: ${server}` });
  const powered = headers.get('x-powered-by');
  if (powered) signals.push({ technology: powered, category: 'framework', evidence: `X-Powered-By: ${powered}` });

  // CMS/Framework detection
  const patterns: [RegExp, string, string][] = [
    [/wp-content|wordpress/i, 'WordPress', 'cms'],
    [/shopify/i, 'Shopify', 'ecommerce'],
    [/wix\.com/i, 'Wix', 'cms'],
    [/squarespace/i, 'Squarespace', 'cms'],
    [/drupal/i, 'Drupal', 'cms'],
    [/joomla/i, 'Joomla', 'cms'],
    [/hubspot/i, 'HubSpot', 'marketing'],
    [/salesforce/i, 'Salesforce', 'crm'],
    [/react/i, 'React', 'frontend'],
    [/angular/i, 'Angular', 'frontend'],
    [/vue\.js|vuejs/i, 'Vue.js', 'frontend'],
    [/next\.js|nextjs|_next\//i, 'Next.js', 'framework'],
    [/bootstrap/i, 'Bootstrap', 'css'],
    [/tailwind/i, 'Tailwind CSS', 'css'],
    [/jquery/i, 'jQuery', 'javascript'],
    [/google-analytics|gtag|ga\.js/i, 'Google Analytics', 'analytics'],
    [/googletagmanager/i, 'Google Tag Manager', 'analytics'],
    [/facebook.*pixel|fbq\(/i, 'Facebook Pixel', 'analytics'],
    [/hotjar/i, 'Hotjar', 'analytics'],
    [/cloudflare/i, 'Cloudflare', 'cdn'],
    [/amazonaws\.com/i, 'AWS', 'hosting'],
    [/azure/i, 'Azure', 'hosting'],
    [/stripe/i, 'Stripe', 'payments'],
    [/recaptcha/i, 'reCAPTCHA', 'security'],
    [/intercom/i, 'Intercom', 'chat'],
    [/zendesk/i, 'Zendesk', 'support'],
    [/mailchimp/i, 'Mailchimp', 'email'],
    [/api\/v[0-9]/i, 'REST API detected', 'api'],
    [/graphql/i, 'GraphQL', 'api'],
    [/swagger|openapi/i, 'Swagger/OpenAPI', 'api'],
    [/\.aspx|__viewstate/i, 'ASP.NET', 'framework'],
    [/\.php/i, 'PHP', 'language'],
    [/\.jsp/i, 'Java/JSP', 'language'],
  ];

  for (const [regex, tech, cat] of patterns) {
    if (regex.test(html) || regex.test(lowerHtml)) {
      signals.push({ technology: tech, category: cat, evidence: `Pattern match in HTML` });
    }
  }

  // Check for exposed paths
  const exposedPatterns: [string, string][] = [
    ['/wp-admin', 'WordPress Admin'],
    ['/wp-json', 'WordPress REST API'],
    ['/api/', 'API endpoint'],
    ['/admin', 'Admin panel'],
    ['/login', 'Login page'],
    ['/dashboard', 'Dashboard'],
    ['/graphql', 'GraphQL endpoint'],
    ['/swagger', 'API docs'],
    ['/.env', 'Environment file'],
    ['/sitemap.xml', 'Sitemap'],
    ['/robots.txt', 'Robots.txt'],
  ];

  for (const [path, label] of exposedPatterns) {
    if (html.includes(path)) {
      signals.push({ technology: label, category: 'exposed_path', evidence: `Found reference to ${path}` });
    }
  }

  return signals;
}

// ─── CONTENT INTELLIGENCE EXTRACTION ───────────────────────────────────────────

interface ExtractedIntel {
  dataType: string;
  key: string;
  value: string;
  confidence: number;
}

function extractIntelligence(page: ScrapedPage): ExtractedIntel[] {
  const intel: ExtractedIntel[] = [];
  const text = page.bodyText;

  // Company info
  if (page.metaDescription) {
    intel.push({ dataType: 'company_description', key: 'meta_description', value: page.metaDescription, confidence: 0.9 });
  }

  // Address detection
  const addressRe = /\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln|way|circle|court|ct)[\s,]+[\w\s]+,?\s*(?:TX|Texas|NM|New Mexico|OK|Oklahoma|CO|Colorado|LA|Louisiana|ND|North Dakota|WY|Wyoming)\s*\d{5}/gi;
  const addresses = text.match(addressRe) || [];
  for (const addr of addresses) {
    intel.push({ dataType: 'address', key: 'physical_address', value: addr.trim(), confidence: 0.8 });
  }

  // Services detection
  const serviceKeywords = [
    'water analysis', 'chemical treatment', 'scale inhibitor', 'corrosion inhibitor',
    'biocide', 'demulsifier', 'flow assurance', 'production chemicals',
    'completion fluids', 'drilling fluids', 'stimulation', 'acidizing',
    'water treatment', 'waste management', 'environmental services',
    'lab services', 'field services', 'consulting', 'pipeline',
    'salt water disposal', 'SWD', 'fracturing', 'well stimulation',
    'paraffin', 'asphaltene', 'H2S', 'iron control', 'oxygen scavenger',
  ];

  for (const kw of serviceKeywords) {
    if (text.toLowerCase().includes(kw.toLowerCase())) {
      intel.push({ dataType: 'service', key: kw, value: `Offers ${kw}`, confidence: 0.7 });
    }
  }

  // Product mentions
  const productPatterns = [
    /(?:our |we offer |products include |specializing in )([^.]{10,100})/gi,
    /(?:product(?:s)?[:\s]+)([^.]{10,150})/gi,
  ];
  for (const re of productPatterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'product_mention', key: 'product_text', value: m[1].trim(), confidence: 0.6 });
    }
  }

  // Chemical product names (specific oilfield chemicals)
  const chemicalNames = [
    /\b((?:scale|corrosion|paraffin|asphaltene|H2S|iron|oxygen|bacteria|sulfate)[- ]?(?:inhibitor|scavenger|treatment|dispersant|control|preventer|solvent)s?)\b/gi,
    /\b(demulsifier|biocide|surfactant|clay stabilizer|friction reducer|gelling agent|crosslinker|breaker|foamer|defoamer|emulsion breaker)\b/gi,
    /\b(hydrochloric acid|HCl|muriatic acid|acetic acid|citric acid|formic acid|EDTA|DTPA|NTA)\b/gi,
    /\b(methanol|glycol|MEG|DEG|TEG|KCl|CaCl2|NaCl brine)\b/gi,
  ];
  for (const re of chemicalNames) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'chemical_product', key: 'chemical_name', value: m[1].trim(), confidence: 0.8 });
    }
  }

  // Pricing signals (rare but valuable)
  const pricingPatterns = [
    /\$\s*[\d,]+(?:\.\d{2})?\s*(?:\/\s*(?:gallon|gal|barrel|bbl|drum|tote|ton|lb|kg|liter|case|unit|month|year|well|treatment))/gi,
    /(?:price|cost|rate|fee|pricing|quote)\s*(?:of |is |at |from |starting )?\s*\$\s*[\d,]+(?:\.\d{2})?/gi,
    /\$\s*[\d,]+(?:\.\d{2})?\s*(?:to|-)\s*\$\s*[\d,]+(?:\.\d{2})?/gi,
    /(?:starting at|from|as low as|only)\s*\$\s*[\d,]+/gi,
    /\b(\d+(?:\.\d+)?)\s*(?:cents?|¢)\s*(?:per|\/)\s*(?:gallon|gal|barrel|bbl|lb|kg)/gi,
  ];
  for (const re of pricingPatterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'pricing_signal', key: 'price_mention', value: m[0].trim(), confidence: 0.9 });
    }
  }

  // Quantity/packaging info (useful for pricing comparison)
  const packagingPatterns = [
    /\b(\d+)\s*(?:gallon|gal)\s*(?:drum|tote|container|tank)/gi,
    /\b(\d+)\s*(?:barrel|bbl)\s*(?:tank|tote|minimum)/gi,
    /(?:available in|sold in|packaged in|comes in)\s+([^.]{10,80})/gi,
    /(?:minimum order|MOQ|minimum quantity)[:\s]+([^.]{5,50})/gi,
    /(?:bulk|wholesale|volume)\s+(?:pricing|discount|rates?)/gi,
  ];
  for (const re of packagingPatterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'packaging_info', key: 'packaging', value: m[0].trim(), confidence: 0.7 });
    }
  }

  // Service area / coverage (competitive intelligence)
  const coveragePatterns = [
    /(?:serving|operating in|coverage|service area|locations? in)\s+([^.]{10,120})/gi,
    /(?:Permian Basin|Delaware Basin|Midland Basin|Eagle Ford|Bakken|Haynesville|DJ Basin|Marcellus|Utica|SCOOP|STACK|Anadarko)/gi,
  ];
  for (const re of coveragePatterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'service_area', key: 'coverage', value: m[0].trim(), confidence: 0.7 });
    }
  }

  // Certifications and standards
  const certPatterns = [
    /\b(ISO\s*\d{4,5}(?::\d{4})?|API\s*\d+[A-Z]?|NSF\s*\d+|OSHA|EPA|DOT)\b/gi,
    /(?:certified|accredited|compliant|approved)\s+(?:by |to |with )?([^.]{5,60})/gi,
  ];
  for (const re of certPatterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      intel.push({ dataType: 'certification', key: 'cert', value: m[0].trim(), confidence: 0.8 });
    }
  }

  // Team/leadership
  const titlePatterns = /(?:CEO|President|VP|Vice President|Director|Manager|Engineer|Chemist|Owner|Founder|CTO|CFO|COO)\s*[:\-–]?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)/g;
  let m;
  while ((m = titlePatterns.exec(text)) !== null) {
    intel.push({ dataType: 'team_member', key: m[0].split(/[:\-–]/)[0].trim(), value: m[1], confidence: 0.7 });
  }

  // Emails and phones
  for (const email of page.emails) {
    intel.push({ dataType: 'contact', key: 'email', value: email, confidence: 0.95 });
  }
  for (const phone of page.phones) {
    intel.push({ dataType: 'contact', key: 'phone', value: phone, confidence: 0.85 });
  }

  // Social media
  const socialPatterns: [RegExp, string][] = [
    [/(?:https?:\/\/)?(?:www\.)?facebook\.com\/[a-zA-Z0-9._-]+/gi, 'facebook'],
    [/(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:company|in)\/[a-zA-Z0-9._-]+/gi, 'linkedin'],
    [/(?:https?:\/\/)?(?:www\.)?twitter\.com\/[a-zA-Z0-9._-]+/gi, 'twitter'],
    [/(?:https?:\/\/)?(?:www\.)?instagram\.com\/[a-zA-Z0-9._-]+/gi, 'instagram'],
    [/(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:channel|c|@)[a-zA-Z0-9._-]+/gi, 'youtube'],
  ];
  for (const [re, platform] of socialPatterns) {
    const matches = (page.html).match(re) || [];
    for (const url of [...new Set(matches)]) {
      intel.push({ dataType: 'social_media', key: platform, value: url, confidence: 0.9 });
    }
  }

  return intel;
}

// ─── REVERSE ENGINEERING VIA ENGINE RUNTIME ────────────────────────────────────

interface EngineMatch {
  engine_id: string;
  topic: string;
  conclusion: string;
  reasoning: string;
}
interface EngineQueryResult {
  ok: boolean;
  domain: string;
  matches: EngineMatch[];
  total_matches: number;
  response_ms: number;
  related_domains?: Array<{ domain: string; label: string }>;
}

async function queryEngines(queryText: string, domain: string, env: Env): Promise<EngineMatch[]> {
  try {
    const resp = await env.ENGINE_RUNTIME.fetch('https://engine/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Echo-API-Key': env.ECHO_API_KEY || '' },
      body: JSON.stringify({ query: queryText, domain, mode: 'DEFENSE', limit: 5 }),
    });
    if (!resp.ok) return [];
    const data = await resp.json() as EngineQueryResult;
    return data.matches || [];
  } catch {
    return [];
  }
}

async function runReverseEngineering(competitorName: string, scrapedData: string, env: Env): Promise<string | null> {
  try {
    const queryText = `Analyze oilfield chemical company ${competitorName}: technology, services, competitive position, vulnerabilities`;

    // Query multiple relevant engine domains in parallel
    const [revengMatches, chemMatches, oilMatches] = await Promise.all([
      queryEngines(queryText, 'REVENG', env),
      queryEngines(queryText, 'CHEM', env),
      queryEngines(queryText, 'OIL', env),
    ]);

    // Build structured competitive intelligence report from scraped data
    const lines = scrapedData.split('\n');
    const techStack = lines.filter(l => l.includes(':') && lines.indexOf(l) > lines.findIndex(l2 => l2.includes('Tech Stack')));
    const endpoints = lines.filter(l => l.startsWith('['));

    const sections: string[] = [
      `# COMPETITIVE INTELLIGENCE REPORT: ${competitorName}`,
      `Generated: ${new Date().toISOString()}`,
      ``,
      `## SCRAPED DATA SUMMARY`,
      scrapedData.slice(0, 4000),
      ``,
    ];

    // Doctrine-backed analysis
    if (revengMatches.length > 0) {
      sections.push(`## REVERSE ENGINEERING ANALYSIS (${revengMatches.length} doctrine matches)`);
      for (const m of revengMatches.slice(0, 3)) {
        sections.push(`### ${m.topic}`);
        sections.push(m.conclusion);
        sections.push(``);
      }
    }

    if (chemMatches.length > 0) {
      sections.push(`## CHEMICAL INDUSTRY CONTEXT (${chemMatches.length} doctrine matches)`);
      for (const m of chemMatches.slice(0, 3)) {
        sections.push(`### ${m.topic}`);
        sections.push(m.conclusion);
        sections.push(``);
      }
    }

    if (oilMatches.length > 0) {
      sections.push(`## OILFIELD INDUSTRY CONTEXT (${oilMatches.length} doctrine matches)`);
      for (const m of oilMatches.slice(0, 3)) {
        sections.push(`### ${m.topic}`);
        sections.push(m.conclusion);
        sections.push(``);
      }
    }

    sections.push(`## COMPETITIVE ASSESSMENT`);
    sections.push(`- Doctrine sources queried: REVENG (${revengMatches.length}), CHEM (${chemMatches.length}), OIL (${oilMatches.length})`);
    sections.push(`- Total intelligence items in scraped data: ${lines.length}`);
    sections.push(`- Exposed endpoints found: ${endpoints.length}`);
    sections.push(``);
    sections.push(`## RAW DOCTRINE MATCH COUNT: ${revengMatches.length + chemMatches.length + oilMatches.length}`);

    const report = sections.join('\n');
    log('info', `RevEng report generated for ${competitorName}`, {
      reveng: revengMatches.length, chem: chemMatches.length, oil: oilMatches.length,
      reportLength: report.length,
    });

    return report;
  } catch (err) {
    log('error', `RevEng failed for ${competitorName}`, { error: String(err) });
    return null;
  }
}

// ─── SCRAPE ORCHESTRATOR ───────────────────────────────────────────────────────

async function scrapeCompetitor(competitor: Competitor, env: Env): Promise<{ pagesScraped: number; intelExtracted: number; url: string | null }> {
  log('info', `Starting scrape: ${competitor.name}`, { priority: competitor.priority });

  // Find website URL
  let websiteUrl: string | null = null;

  // Check if we already have the URL cached
  const cachedUrl = await env.CACHE.get(`url:${competitor.name}`);
  if (cachedUrl) {
    websiteUrl = cachedUrl;
  } else {
    websiteUrl = await searchForWebsite(competitor);
    if (websiteUrl) {
      await env.CACHE.put(`url:${competitor.name}`, websiteUrl, { expirationTtl: 86400 * 30 });
    }
  }

  // Get or create competitor record
  let compRow = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(competitor.name).first<{ id: number }>();
  if (!compRow) {
    await env.DB.prepare('INSERT INTO competitors (name, website_url, priority, notes) VALUES (?, ?, ?, ?)').bind(competitor.name, websiteUrl, competitor.priority, competitor.notes).run();
    compRow = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(competitor.name).first<{ id: number }>();
  } else if (websiteUrl) {
    await env.DB.prepare('UPDATE competitors SET website_url = ?, updated_at = datetime(\'now\') WHERE id = ?').bind(websiteUrl, compRow.id).run();
  }

  if (!compRow || !websiteUrl) {
    log('warn', `No website found for ${competitor.name}`);
    return { pagesScraped: 0, intelExtracted: 0, url: null };
  }

  const compId = compRow.id;
  let totalPages = 0;
  let totalIntel = 0;

  // Scrape homepage
  const homepage = await scrapePage(websiteUrl);
  if (!homepage) {
    log('warn', `Failed to scrape homepage for ${competitor.name}`, { url: websiteUrl });
    return { pagesScraped: 0, intelExtracted: 0, url: websiteUrl };
  }

  // Store homepage scrape
  await env.DB.prepare(`INSERT INTO scrape_results (competitor_id, url, page_type, title, content_text, meta_description, meta_keywords, links_found, status_code, content_length)
    VALUES (?, ?, 'homepage', ?, ?, ?, ?, ?, ?, ?)`).bind(
    compId, websiteUrl, homepage.title, homepage.bodyText.slice(0, 50000),
    homepage.metaDescription, homepage.metaKeywords, homepage.links.length,
    homepage.statusCode, homepage.html.length
  ).run();
  totalPages++;

  // Extract and store intelligence from homepage
  const homeIntel = extractIntelligence(homepage);
  for (const item of homeIntel) {
    await env.DB.prepare('INSERT OR IGNORE INTO extracted_data (competitor_id, data_type, data_key, data_value, confidence, source_url) VALUES (?, ?, ?, ?, ?, ?)').bind(
      compId, item.dataType, item.key, item.value, item.confidence, websiteUrl
    ).run();
    totalIntel++;
  }

  // Store tech stack
  for (const sig of homepage.techSignals) {
    await env.DB.prepare('INSERT OR IGNORE INTO tech_stack (competitor_id, technology, category, evidence) VALUES (?, ?, ?, ?)').bind(
      compId, sig.technology, sig.category, sig.evidence
    ).run();
  }

  // Store contacts
  for (const email of homepage.emails) {
    await env.DB.prepare('INSERT OR IGNORE INTO contacts (competitor_id, contact_type, contact_value, source_url) VALUES (?, \'email\', ?, ?)').bind(compId, email, websiteUrl).run();
  }
  for (const phone of homepage.phones) {
    await env.DB.prepare('INSERT OR IGNORE INTO contacts (competitor_id, contact_type, contact_value, source_url) VALUES (?, \'phone\', ?, ?)').bind(compId, phone, websiteUrl).run();
  }

  // Crawl key subpages (about, services, products, contact, team)
  const keyPaths = ['/about', '/about-us', '/services', '/products', '/contact', '/contact-us', '/team', '/our-team', '/leadership', '/chemicals', '/solutions', '/water-treatment', '/lab-services'];
  const crawledUrls = new Set([websiteUrl]);

  // Also check links from homepage that look relevant
  const relevantLinks = homepage.links.filter(l => {
    const lower = l.toLowerCase();
    return keyPaths.some(p => lower.includes(p.replace('/', ''))) || lower.includes('service') || lower.includes('product') || lower.includes('about') || lower.includes('contact') || lower.includes('team') || lower.includes('chemical') || lower.includes('solution') || lower.includes('lab');
  }).slice(0, 15);

  const urlsToScrape = [
    ...keyPaths.map(p => websiteUrl + p),
    ...relevantLinks,
  ];

  for (const subUrl of urlsToScrape) {
    if (crawledUrls.has(subUrl) || totalPages >= 20) break;
    crawledUrls.add(subUrl);

    const subPage = await scrapePage(subUrl);
    if (!subPage || subPage.statusCode === 404) continue;

    const pageType = subUrl.toLowerCase().includes('about') ? 'about'
      : subUrl.toLowerCase().includes('service') ? 'services'
      : subUrl.toLowerCase().includes('product') ? 'products'
      : subUrl.toLowerCase().includes('contact') ? 'contact'
      : subUrl.toLowerCase().includes('team') ? 'team'
      : subUrl.toLowerCase().includes('lab') ? 'lab_services'
      : 'other';

    await env.DB.prepare(`INSERT INTO scrape_results (competitor_id, url, page_type, title, content_text, meta_description, meta_keywords, links_found, status_code, content_length)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(
      compId, subUrl, pageType, subPage.title, subPage.bodyText.slice(0, 50000),
      subPage.metaDescription, subPage.metaKeywords, subPage.links.length,
      subPage.statusCode, subPage.html.length
    ).run();
    totalPages++;

    const subIntel = extractIntelligence(subPage);
    for (const item of subIntel) {
      await env.DB.prepare('INSERT OR IGNORE INTO extracted_data (competitor_id, data_type, data_key, data_value, confidence, source_url) VALUES (?, ?, ?, ?, ?, ?)').bind(
        compId, item.dataType, item.key, item.value, item.confidence, subUrl
      ).run();
      totalIntel++;
    }

    for (const sig of subPage.techSignals) {
      await env.DB.prepare('INSERT OR IGNORE INTO tech_stack (competitor_id, technology, category, evidence) VALUES (?, ?, ?, ?)').bind(
        compId, sig.technology, sig.category, sig.evidence
      ).run();
    }

    for (const email of subPage.emails) {
      await env.DB.prepare('INSERT OR IGNORE INTO contacts (competitor_id, contact_type, contact_value, source_url) VALUES (?, \'email\', ?, ?)').bind(compId, email, subUrl).run();
    }
    for (const phone of subPage.phones) {
      await env.DB.prepare('INSERT OR IGNORE INTO contacts (competitor_id, contact_type, contact_value, source_url) VALUES (?, \'phone\', ?, ?)').bind(compId, phone, subUrl).run();
    }
  }

  // Probe for exposed endpoints
  const probeUrls = [
    '/robots.txt', '/sitemap.xml', '/.env', '/wp-json/wp/v2/posts', '/api', '/api/v1',
    '/graphql', '/swagger.json', '/openapi.json', '/.git/HEAD', '/admin', '/login',
    '/wp-admin', '/debug', '/status', '/health', '/config',
  ];

  for (const probePath of probeUrls) {
    try {
      const probeUrl = websiteUrl + probePath;
      const resp = await fetch(probeUrl, {
        method: 'GET',
        headers: { 'User-Agent': UA },
        redirect: 'follow',
        signal: AbortSignal.timeout(5000),
      });

      if (resp.ok) {
        const body = await resp.text();
        const severity = probePath.includes('.env') || probePath.includes('.git') ? 'critical'
          : probePath.includes('admin') || probePath.includes('config') ? 'high'
          : probePath.includes('api') || probePath.includes('swagger') ? 'medium'
          : 'info';

        await env.DB.prepare('INSERT OR IGNORE INTO exposed_endpoints (competitor_id, endpoint_url, endpoint_type, response_sample, severity) VALUES (?, ?, ?, ?, ?)').bind(
          compId, probeUrl, probePath.replace('/', ''), body.slice(0, 2000), severity
        ).run();
      }
    } catch { /* timeout or error, skip */ }
  }

  // Update competitor status
  await env.DB.prepare('UPDATE competitors SET status = \'scraped\', last_scraped = datetime(\'now\'), scrape_count = scrape_count + 1, updated_at = datetime(\'now\') WHERE id = ?').bind(compId).run();

  log('info', `Scrape complete: ${competitor.name}`, { pages: totalPages, intel: totalIntel, url: websiteUrl });
  return { pagesScraped: totalPages, intelExtracted: totalIntel, url: websiteUrl };
}

// ─── RUN REVERSE ENGINEERING ON ALL SCRAPED DATA ───────────────────────────────

async function runRevEngBatch(env: Env, batchLimit = 5): Promise<number> {
  // Find competitors with scrape data but no reveng reports yet (limited batch)
  const competitors = await env.DB.prepare(`
    SELECT c.id, c.name FROM competitors c
    WHERE c.scrape_count > 0
    AND c.id NOT IN (SELECT DISTINCT competitor_id FROM reveng_reports)
    LIMIT ?
  `).bind(batchLimit).all<{ id: number; name: string }>();
  log('info', `RevEng batch: ${competitors.results.length} competitors to process`);
  let reports = 0;

  for (const comp of competitors.results) {
    // Gather all scraped text for this competitor
    const pages = await env.DB.prepare('SELECT content_text, page_type FROM scrape_results WHERE competitor_id = ? ORDER BY scraped_at DESC LIMIT 10').bind(comp.id).all<{ content_text: string; page_type: string }>();
    const tech = await env.DB.prepare('SELECT technology, category FROM tech_stack WHERE competitor_id = ?').bind(comp.id).all<{ technology: string; category: string }>();
    const endpoints = await env.DB.prepare('SELECT endpoint_url, severity FROM exposed_endpoints WHERE competitor_id = ?').bind(comp.id).all<{ endpoint_url: string; severity: string }>();

    const dataBundle = [
      `Company: ${comp.name}`,
      `\nPages scraped:`,
      ...pages.results.map(p => `[${p.page_type}] ${p.content_text?.slice(0, 2000) || 'empty'}`),
      `\nTech Stack:`,
      ...tech.results.map(t => `${t.category}: ${t.technology}`),
      `\nExposed Endpoints:`,
      ...endpoints.results.map(e => `[${e.severity}] ${e.endpoint_url}`),
    ].join('\n');

    const report = await runReverseEngineering(comp.name, dataBundle, env);
    if (report) {
      await env.DB.prepare('INSERT INTO reveng_reports (competitor_id, engine_id, report_type, summary, full_report) VALUES (?, ?, ?, ?, ?)').bind(
        comp.id, 'reverse_engineering', 'full_analysis', report.slice(0, 500), report
      ).run();
      reports++;
    }

    // Update status
    await env.DB.prepare("UPDATE competitors SET status = 'analyzed', updated_at = datetime('now') WHERE id = ?").bind(comp.id).run();
  }

  return reports;
}

// ─── INGEST TO SHARED BRAIN ────────────────────────────────────────────────────

async function ingestToBrain(content: string, tags: string[], env: Env): Promise<void> {
  try {
    await env.SHARED_BRAIN.fetch('https://brain/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instance_id: 'permian-pulse-scraper', role: 'assistant', content, importance: 7, tags }),
    });
  } catch { /* best effort */ }
}

// ─── API ROUTES ────────────────────────────────────────────────────────────────

async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;

  // CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': '*' } });
  }

  // Health
  if (path === '/health') {
    const compCount = await env.DB.prepare('SELECT COUNT(*) as c FROM competitors').first<{ c: number }>();
    const scrapeCount = await env.DB.prepare('SELECT COUNT(*) as c FROM scrape_results').first<{ c: number }>();
    return json({
      status: 'healthy',
      worker: 'permian-pulse-scraper',
      version: env.WORKER_VERSION,
      competitors: compCount?.c || 0,
      pages_scraped: scrapeCount?.c || 0,
      timestamp: new Date().toISOString(),
    });
  }

  // Stats
  if (path === '/stats') {
    const competitors = await env.DB.prepare('SELECT name, website_url, priority, status, last_scraped, scrape_count FROM competitors ORDER BY priority, name').all();
    const totalPages = await env.DB.prepare('SELECT COUNT(*) as c FROM scrape_results').first<{ c: number }>();
    const totalIntel = await env.DB.prepare('SELECT COUNT(*) as c FROM extracted_data').first<{ c: number }>();
    const totalTech = await env.DB.prepare('SELECT COUNT(*) as c FROM tech_stack').first<{ c: number }>();
    const totalEndpoints = await env.DB.prepare('SELECT COUNT(*) as c FROM exposed_endpoints').first<{ c: number }>();
    const totalReports = await env.DB.prepare('SELECT COUNT(*) as c FROM reveng_reports').first<{ c: number }>();
    const totalContacts = await env.DB.prepare('SELECT COUNT(*) as c FROM contacts').first<{ c: number }>();
    return json({
      competitors: competitors.results,
      totals: {
        competitors: competitors.results.length,
        pages_scraped: totalPages?.c || 0,
        intel_extracted: totalIntel?.c || 0,
        tech_signals: totalTech?.c || 0,
        exposed_endpoints: totalEndpoints?.c || 0,
        reveng_reports: totalReports?.c || 0,
        contacts: totalContacts?.c || 0,
      },
    });
  }

  // Get competitor detail
  if (path.startsWith('/competitor/')) {
    const name = decodeURIComponent(path.replace('/competitor/', ''));
    const comp = await env.DB.prepare('SELECT * FROM competitors WHERE name = ?').bind(name).first();
    if (!comp) return json({ error: 'Competitor not found' }, 404);
    const pages = await env.DB.prepare('SELECT url, page_type, title, status_code, scraped_at FROM scrape_results WHERE competitor_id = ? ORDER BY scraped_at DESC').bind(comp.id).all();
    const intel = await env.DB.prepare('SELECT data_type, data_key, data_value, confidence FROM extracted_data WHERE competitor_id = ?').bind(comp.id).all();
    const tech = await env.DB.prepare('SELECT technology, category, evidence FROM tech_stack WHERE competitor_id = ?').bind(comp.id).all();
    const endpoints = await env.DB.prepare('SELECT endpoint_url, severity, response_sample FROM exposed_endpoints WHERE competitor_id = ?').bind(comp.id).all();
    const reports = await env.DB.prepare('SELECT report_type, summary, generated_at FROM reveng_reports WHERE competitor_id = ? ORDER BY generated_at DESC').bind(comp.id).all();
    const contacts = await env.DB.prepare('SELECT contact_type, contact_value, source_url FROM contacts WHERE competitor_id = ?').bind(comp.id).all();
    const products = await env.DB.prepare('SELECT product_name, category, description FROM products WHERE competitor_id = ?').bind(comp.id).all();
    return json({ competitor: comp, pages: pages.results, intelligence: intel.results, tech_stack: tech.results, exposed_endpoints: endpoints.results, reveng_reports: reports.results, contacts: contacts.results, products: products.results });
  }

  // Trigger scrape (manual)
  if (path === '/scrape' && request.method === 'POST') {
    const body = await request.json() as { name?: string; priority?: string };
    const targets = body.name
      ? COMPETITORS.filter(c => c.name.toLowerCase().includes((body.name || '').toLowerCase()))
      : body.priority
        ? COMPETITORS.filter(c => c.priority === body.priority)
        : COMPETITORS;

    if (targets.length === 0) return json({ error: 'No matching competitors' }, 404);

    const results: Record<string, unknown>[] = [];
    for (const target of targets) {
      const result = await scrapeCompetitor(target, env);
      results.push({ name: target.name, ...result });
    }

    // Ingest summary to brain
    const summary = `COMPETITOR SCRAPE: ${results.length} companies scraped. ${results.reduce((a, r) => a + ((r.pagesScraped as number) || 0), 0)} pages, ${results.reduce((a, r) => a + ((r.intelExtracted as number) || 0), 0)} intel items extracted.`;
    await ingestToBrain(summary, ['competitor_scrape', 'permian_pulse'], env);

    return json({ scraped: results.length, results });
  }

  // Debug reveng query
  if (path === '/reveng/debug') {
    const competitors = await env.DB.prepare(`
      SELECT c.id, c.name, c.scrape_count FROM competitors c
      WHERE c.scrape_count > 0
      AND c.id NOT IN (SELECT DISTINCT competitor_id FROM reveng_reports)
    `).all();
    // Test engine runtime
    let engineTest = 'not_tested';
    try {
      const resp = await env.ENGINE_RUNTIME.fetch('https://engine/health', {
        headers: { 'X-Echo-API-Key': env.ECHO_API_KEY || '' },
      });
      engineTest = `status=${resp.status} body=${(await resp.text()).slice(0, 200)}`;
    } catch (e) {
      engineTest = `error: ${String(e)}`;
    }
    return json({ pending_reveng: competitors.results, engine_runtime: engineTest, echo_api_key_set: !!env.ECHO_API_KEY });
  }

  // Trigger reverse engineering for a single competitor (test)
  if (path === '/reveng/test' && request.method === 'POST') {
    const body = await request.json() as { name?: string };
    const name = body.name || 'Champion X';
    const comp = await env.DB.prepare('SELECT id, name FROM competitors WHERE name = ?').bind(name).first<{ id: number; name: string }>();
    if (!comp) return json({ error: 'Competitor not found' }, 404);

    const pages = await env.DB.prepare('SELECT content_text, page_type FROM scrape_results WHERE competitor_id = ? ORDER BY scraped_at DESC LIMIT 10').bind(comp.id).all<{ content_text: string; page_type: string }>();
    const tech = await env.DB.prepare('SELECT technology, category FROM tech_stack WHERE competitor_id = ?').bind(comp.id).all<{ technology: string; category: string }>();
    const endpoints = await env.DB.prepare('SELECT endpoint_url, severity FROM exposed_endpoints WHERE competitor_id = ?').bind(comp.id).all<{ endpoint_url: string; severity: string }>();

    const dataBundle = [
      `Company: ${comp.name}`,
      `\nPages scraped:`,
      ...pages.results.map(p => `[${p.page_type}] ${p.content_text?.slice(0, 2000) || 'empty'}`),
      `\nTech Stack:`,
      ...tech.results.map(t => `${t.category}: ${t.technology}`),
      `\nExposed Endpoints:`,
      ...endpoints.results.map(e => `[${e.severity}] ${e.endpoint_url}`),
    ].join('\n');

    try {
      const report = await runReverseEngineering(comp.name, dataBundle, env);
      if (report) {
        await env.DB.prepare('INSERT INTO reveng_reports (competitor_id, engine_id, report_type, summary, full_report) VALUES (?, ?, ?, ?, ?)').bind(
          comp.id, 'reverse_engineering', 'full_analysis', report.slice(0, 500), report
        ).run();
      }
      return json({ name: comp.name, report_generated: !!report, report_length: report?.length || 0, data_bundle_length: dataBundle.length, pages_found: pages.results.length, preview: report?.slice(0, 500) });
    } catch (err) {
      return json({ error: String(err), stack: (err as Error).stack, data_bundle_length: dataBundle.length }, 500);
    }
  }

  // Trigger reverse engineering batch (processes up to 5 at a time to stay under CPU limits)
  if (path === '/reveng' && request.method === 'POST') {
    const body = await request.json().catch(() => ({})) as { limit?: number };
    const batchLimit = body.limit || 5;
    const reports = await runRevEngBatch(env, batchLimit);
    return json({ reports_generated: reports });
  }

  // ─── PRICING INTELLIGENCE REPORT ──────────────────────────────────────────────
  if (path === '/pricing-intel') {
    // Aggregate all pricing/product/packaging/certification data across competitors
    const pricingSignals = await env.DB.prepare(`
      SELECT ed.data_type, ed.data_key, ed.data_value, ed.confidence, ed.source_url, c.name as competitor_name
      FROM extracted_data ed JOIN competitors c ON ed.competitor_id = c.id
      WHERE ed.data_type IN ('pricing_signal', 'chemical_product', 'packaging_info', 'service_area', 'certification')
      ORDER BY ed.data_type, c.name
    `).all<{ data_type: string; data_key: string; data_value: string; confidence: number; source_url: string; competitor_name: string }>();

    // Group by type
    const grouped: Record<string, Array<{ competitor: string; value: string; confidence: number; source: string }>> = {};
    for (const row of pricingSignals.results) {
      if (!grouped[row.data_type]) grouped[row.data_type] = [];
      grouped[row.data_type].push({ competitor: row.competitor_name, value: row.data_value, confidence: row.confidence, source: row.source_url });
    }

    // Competitor chemical product matrix
    const chemMatrix: Record<string, string[]> = {};
    for (const item of (grouped['chemical_product'] || [])) {
      if (!chemMatrix[item.competitor]) chemMatrix[item.competitor] = [];
      const val = item.value.toLowerCase();
      if (!chemMatrix[item.competitor].includes(val)) chemMatrix[item.competitor].push(val);
    }

    // Service area overlap analysis
    const areaMap: Record<string, string[]> = {};
    for (const item of (grouped['service_area'] || [])) {
      if (!areaMap[item.competitor]) areaMap[item.competitor] = [];
      areaMap[item.competitor].push(item.value);
    }

    // Query CHEM engines for competitive analysis
    let chemAnalysis: EngineMatch[] = [];
    const chemProducts = Object.values(chemMatrix).flat();
    if (chemProducts.length > 0) {
      const uniqueChems = [...new Set(chemProducts)].slice(0, 20);
      chemAnalysis = await queryEngines(
        `Competitive analysis of oilfield chemical products: ${uniqueChems.join(', ')}. Which companies have advantages in formulation, delivery, or pricing?`,
        'CHEM', env
      );
    }

    return json({
      total_signals: pricingSignals.results.length,
      by_type: {
        pricing_signals: (grouped['pricing_signal'] || []).length,
        chemical_products: (grouped['chemical_product'] || []).length,
        packaging_info: (grouped['packaging_info'] || []).length,
        service_areas: (grouped['service_area'] || []).length,
        certifications: (grouped['certification'] || []).length,
      },
      pricing_signals: grouped['pricing_signal'] || [],
      chemical_product_matrix: chemMatrix,
      service_area_map: areaMap,
      certifications: grouped['certification'] || [],
      packaging: grouped['packaging_info'] || [],
      chem_engine_analysis: chemAnalysis.map(m => ({ topic: m.topic, conclusion: m.conclusion })),
    });
  }

  // ─── DEEP PRODUCT SCRAPE ───────────────────────────────────────────────────────
  if (path === '/scrape-products' && request.method === 'POST') {
    const body = await request.json().catch(() => ({})) as { name?: string; max_pages?: number };
    const maxPages = body.max_pages || 30;

    // Get competitors to deep-scrape (all with websites, or specific one)
    const compQuery = body.name
      ? env.DB.prepare('SELECT id, name, website_url FROM competitors WHERE name = ? AND website_url IS NOT NULL').bind(body.name)
      : env.DB.prepare('SELECT id, name, website_url FROM competitors WHERE website_url IS NOT NULL AND scrape_count > 0');
    const competitors = await compQuery.all<{ id: number; name: string; website_url: string }>();

    const results: Array<{ name: string; product_pages: number; new_intel: number }> = [];

    for (const comp of competitors.results) {
      let productPages = 0;
      let newIntel = 0;

      // Get already-scraped URLs to avoid duplicates
      const existing = await env.DB.prepare('SELECT url FROM scrape_results WHERE competitor_id = ?').bind(comp.id).all<{ url: string }>();
      const scraped = new Set(existing.results.map(r => r.url));

      // Get all links from existing scrape results
      const pageResults = await env.DB.prepare('SELECT content_text FROM scrape_results WHERE competitor_id = ? LIMIT 10').bind(comp.id).all<{ content_text: string }>();

      // Product/catalog page patterns to look for
      const productPathPatterns = [
        '/products', '/catalog', '/chemicals', '/chemical-solutions', '/our-products',
        '/product-line', '/product-catalog', '/portfolio', '/offerings', '/specialty-chemicals',
        '/production-chemicals', '/completion-chemicals', '/drilling-chemicals', '/water-treatment',
        '/scale-inhibitor', '/corrosion-inhibitor', '/demulsifier', '/biocide', '/h2s-scavenger',
        '/flow-assurance', '/stimulation', '/acidizing', '/pipeline-chemicals',
        '/sds', '/safety-data-sheets', '/msds', '/technical-data',
      ];

      // Build URLs to try
      const urlsToTry: string[] = [];
      for (const p of productPathPatterns) {
        const url = comp.website_url.replace(/\/$/, '') + p;
        if (!scraped.has(url)) urlsToTry.push(url);
      }

      // Also parse links from existing pages for product-related URLs
      for (const page of pageResults.results) {
        const linkRe = /href=["'](\/[^"']*(?:product|chemical|catalog|solution|treatment|inhibitor|scavenger|sds|technical)[^"']*)/gi;
        let linkMatch;
        while ((linkMatch = linkRe.exec(page.content_text || '')) !== null) {
          const fullUrl = comp.website_url.replace(/\/$/, '') + linkMatch[1];
          if (!scraped.has(fullUrl) && !urlsToTry.includes(fullUrl)) {
            urlsToTry.push(fullUrl);
          }
        }
      }

      // Scrape product pages
      for (const subUrl of urlsToTry.slice(0, maxPages)) {
        const subPage = await scrapePage(subUrl);
        if (!subPage || subPage.statusCode === 404 || subPage.statusCode === 403) continue;
        if (subPage.bodyText.length < 100) continue;

        // Classify page type
        const lower = subUrl.toLowerCase();
        const pageType = lower.includes('sds') || lower.includes('safety-data') || lower.includes('msds') ? 'sds'
          : lower.includes('technical') ? 'technical_data'
          : 'product_detail';

        await env.DB.prepare(`INSERT OR IGNORE INTO scrape_results (competitor_id, url, page_type, title, content_text, meta_description, meta_keywords, links_found, status_code, content_length)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(
          comp.id, subUrl, pageType, subPage.title, subPage.bodyText.slice(0, 50000),
          subPage.metaDescription, subPage.metaKeywords, subPage.links.length,
          subPage.statusCode, subPage.html.length
        ).run();
        productPages++;

        // Extract intel with enhanced patterns
        const subIntel = extractIntelligence(subPage);
        for (const item of subIntel) {
          await env.DB.prepare('INSERT OR IGNORE INTO extracted_data (competitor_id, data_type, data_key, data_value, confidence, source_url) VALUES (?, ?, ?, ?, ?, ?)').bind(
            comp.id, item.dataType, item.key, item.value, item.confidence, subUrl
          ).run();
          newIntel++;
        }

        // Extract product names from page titles and headings
        if (subPage.title && !subPage.title.toLowerCase().includes('404')) {
          await env.DB.prepare('INSERT OR IGNORE INTO products (competitor_id, product_name, category, description) VALUES (?, ?, ?, ?)').bind(
            comp.id, subPage.title.slice(0, 200), pageType, subPage.metaDescription || subPage.bodyText.slice(0, 300)
          ).run();
        }
      }

      // Update scrape count
      if (productPages > 0) {
        await env.DB.prepare("UPDATE competitors SET scrape_count = scrape_count + 1, last_scraped = datetime('now'), updated_at = datetime('now') WHERE id = ?").bind(comp.id).run();
      }

      results.push({ name: comp.name, product_pages: productPages, new_intel: newIntel });
    }

    // Ingest summary
    const totalProductPages = results.reduce((a, r) => a + r.product_pages, 0);
    const totalNewIntel = results.reduce((a, r) => a + r.new_intel, 0);
    await ingestToBrain(
      `PRODUCT DEEP-SCRAPE: ${results.length} competitors, ${totalProductPages} product pages, ${totalNewIntel} new intel items extracted (pricing, chemicals, packaging, certs)`,
      ['product_scrape', 'pricing_intel', 'permian_pulse'], env
    );

    return json({ competitors_processed: results.length, total_product_pages: totalProductPages, total_new_intel: totalNewIntel, results });
  }

  // ─── FULL REPORT DATA (for dashboard) ───────────────────────────────────────
  if (path === '/report-data') {
    // All competitors with full details
    const competitors = await env.DB.prepare(`
      SELECT id, name, website_url, priority, status, last_scraped, scrape_count, notes
      FROM competitors ORDER BY priority, name
    `).all();

    // All extracted intelligence grouped by competitor
    const allIntel = await env.DB.prepare(`
      SELECT ed.data_type, ed.data_key, ed.data_value, ed.confidence, ed.source_url, ed.competitor_id, c.name as competitor_name
      FROM extracted_data ed JOIN competitors c ON ed.competitor_id = c.id
      ORDER BY c.name, ed.data_type
    `).all();

    // All tech stack (deduplicated per competitor)
    const allTech = await env.DB.prepare(`
      SELECT DISTINCT ts.technology, ts.category, ts.competitor_id, c.name as competitor_name
      FROM tech_stack ts JOIN competitors c ON ts.competitor_id = c.id
      ORDER BY c.name, ts.category
    `).all();

    // All exposed endpoints
    const allEndpoints = await env.DB.prepare(`
      SELECT ee.endpoint_url, ee.severity, ee.response_sample, ee.competitor_id, c.name as competitor_name
      FROM exposed_endpoints ee JOIN competitors c ON ee.competitor_id = c.id
      ORDER BY ee.severity DESC, c.name
    `).all();

    // All reveng reports
    const allReports = await env.DB.prepare(`
      SELECT rr.report_type, rr.summary, rr.full_report, rr.generated_at, rr.competitor_id, c.name as competitor_name
      FROM reveng_reports rr JOIN competitors c ON rr.competitor_id = c.id
      ORDER BY rr.generated_at DESC
    `).all();

    // All OSINT findings from Prometheus scans
    const allOsint = await env.DB.prepare(`
      SELECT co.competitor_id, co.domain, co.scan_type, co.finding_type, co.finding_value, co.severity, co.details, co.source_tool, co.scanned_at, c.name as competitor_name
      FROM competitor_osint co JOIN competitors c ON co.competitor_id = c.id
      ORDER BY co.severity DESC, c.name
    `).all();

    // All contacts (deduplicated, filtered — exclude garbage phone numbers)
    const allContacts = await env.DB.prepare(`
      SELECT DISTINCT ct.contact_type, ct.contact_value, ct.competitor_id, c.name as competitor_name
      FROM contacts ct JOIN competitors c ON ct.competitor_id = c.id
      WHERE (ct.contact_type = 'email' AND ct.contact_value LIKE '%@%.%')
         OR (ct.contact_type = 'phone' AND LENGTH(REPLACE(REPLACE(REPLACE(REPLACE(ct.contact_value, '-', ''), ' ', ''), '(', ''), ')', '')) BETWEEN 10 AND 11)
         OR ct.contact_type NOT IN ('email', 'phone')
      ORDER BY c.name, ct.contact_type
    `).all();

    // All products
    const allProducts = await env.DB.prepare(`
      SELECT p.product_name, p.category, p.description, p.competitor_id, c.name as competitor_name
      FROM products p JOIN competitors c ON p.competitor_id = c.id
      ORDER BY c.name, p.product_name
    `).all();

    // Chemical formulations (SDS data)
    const allFormulations = await env.DB.prepare(`
      SELECT cf.product_name, cf.manufacturer, cf.product_type, cf.cas_number, cf.chemical_name,
             cf.concentration_min, cf.concentration_max, cf.concentration_unit, cf.source_document,
             cf.source_url, cf.confidence, cf.competitor_id, c.name as competitor_name
      FROM chemical_formulations cf LEFT JOIN competitors c ON cf.competitor_id = c.id
      ORDER BY cf.product_name, cf.chemical_name
    `).all();

    // Market intelligence
    const allMarketIntel = await env.DB.prepare(`
      SELECT category, metric_name, metric_value, unit, source, source_url, year, confidence, notes
      FROM market_intel ORDER BY category, metric_name
    `).all();

    // Patents
    const allPatents = await env.DB.prepare(`
      SELECT patent_number, title, assignee, filing_date, grant_date, abstract, key_claims,
             chemical_components, relevance, source_url
      FROM patents ORDER BY filing_date DESC
    `).all();

    // Pages scraped summary (not full content — too large)
    const pageSummary = await env.DB.prepare(`
      SELECT competitor_id, c.name as competitor_name, COUNT(*) as pages, GROUP_CONCAT(DISTINCT page_type) as page_types
      FROM scrape_results sr JOIN competitors c ON sr.competitor_id = c.id
      GROUP BY competitor_id
    `).all();

    // Intel counts per competitor
    const intelCounts = await env.DB.prepare(`
      SELECT competitor_id, COUNT(*) as intel_count
      FROM extracted_data GROUP BY competitor_id
    `).all();
    const intelCountMap: Record<number, number> = {};
    for (const row of intelCounts.results as Array<{ competitor_id: number; intel_count: number }>) {
      intelCountMap[row.competitor_id] = row.intel_count;
    }

    // Enrich pages summary with intel counts
    const enrichedPages = (pageSummary.results as Array<{ competitor_id: number; competitor_name: string; pages: number; page_types: string }>).map(p => ({
      ...p,
      intel_count: intelCountMap[p.competitor_id] || 0,
    }));

    // Totals
    const totalPages = await env.DB.prepare('SELECT COUNT(*) as c FROM scrape_results').first<{ c: number }>();
    const totalIntel = await env.DB.prepare('SELECT COUNT(*) as c FROM extracted_data').first<{ c: number }>();

    // Build chemical product matrix
    const chemMatrix: Record<string, string[]> = {};
    const serviceAreaMap: Record<string, string[]> = {};
    const certMap: Record<string, string[]> = {};
    for (const row of allIntel.results as Array<{ data_type: string; data_value: string; competitor_name: string }>) {
      if (row.data_type === 'chemical_product') {
        if (!chemMatrix[row.competitor_name]) chemMatrix[row.competitor_name] = [];
        const v = row.data_value.toLowerCase();
        if (!chemMatrix[row.competitor_name].includes(v)) chemMatrix[row.competitor_name].push(v);
      }
      if (row.data_type === 'service_area') {
        if (!serviceAreaMap[row.competitor_name]) serviceAreaMap[row.competitor_name] = [];
        if (!serviceAreaMap[row.competitor_name].includes(row.data_value)) serviceAreaMap[row.competitor_name].push(row.data_value);
      }
      if (row.data_type === 'certification') {
        if (!certMap[row.competitor_name]) certMap[row.competitor_name] = [];
        if (!certMap[row.competitor_name].includes(row.data_value)) certMap[row.competitor_name].push(row.data_value);
      }
    }

    // Group tech stack by competitor
    const techByCompetitor: Record<string, Array<{ technology: string; category: string }>> = {};
    for (const row of allTech.results as Array<{ technology: string; category: string; competitor_name: string }>) {
      if (!techByCompetitor[row.competitor_name]) techByCompetitor[row.competitor_name] = [];
      techByCompetitor[row.competitor_name].push({ technology: row.technology, category: row.category });
    }

    // Group endpoints by competitor
    const endpointsByCompetitor: Record<string, Array<{ url: string; severity: string }>> = {};
    for (const row of allEndpoints.results as Array<{ endpoint_url: string; severity: string; competitor_name: string }>) {
      if (!endpointsByCompetitor[row.competitor_name]) endpointsByCompetitor[row.competitor_name] = [];
      endpointsByCompetitor[row.competitor_name].push({ url: row.endpoint_url, severity: row.severity });
    }

    // Group contacts by competitor
    const contactsByCompetitor: Record<string, Array<{ type: string; value: string }>> = {};
    for (const row of allContacts.results as Array<{ contact_type: string; contact_value: string; competitor_name: string }>) {
      if (!contactsByCompetitor[row.competitor_name]) contactsByCompetitor[row.competitor_name] = [];
      contactsByCompetitor[row.competitor_name].push({ type: row.contact_type, value: row.contact_value });
    }

    // Group products by competitor
    const productsByCompetitor: Record<string, Array<{ name: string; category: string; description: string }>> = {};
    for (const row of allProducts.results as Array<{ product_name: string; category: string; description: string; competitor_name: string }>) {
      if (!productsByCompetitor[row.competitor_name]) productsByCompetitor[row.competitor_name] = [];
      productsByCompetitor[row.competitor_name].push({ name: row.product_name, category: row.category, description: row.description });
    }

    // Group reveng reports by competitor
    const revengByCompetitor: Record<string, Array<{ type: string; summary: string; full_report: string; generated_at: string }>> = {};
    for (const row of allReports.results as Array<{ report_type: string; summary: string; full_report: string; generated_at: string; competitor_name: string }>) {
      if (!revengByCompetitor[row.competitor_name]) revengByCompetitor[row.competitor_name] = [];
      revengByCompetitor[row.competitor_name].push({ type: row.report_type, summary: row.summary, full_report: row.full_report, generated_at: row.generated_at });
    }

    // Group formulations by product
    const formulationsByProduct: Record<string, Array<{ cas_number: string; chemical_name: string; min: number; max: number; unit: string }>> = {};
    const formulationMeta: Record<string, { manufacturer: string; product_type: string; source: string; competitor: string }> = {};
    for (const row of allFormulations.results as Array<any>) {
      const key = row.product_name;
      if (!formulationsByProduct[key]) formulationsByProduct[key] = [];
      formulationsByProduct[key].push({
        cas_number: row.cas_number, chemical_name: row.chemical_name,
        min: row.concentration_min, max: row.concentration_max, unit: row.concentration_unit
      });
      if (!formulationMeta[key]) {
        formulationMeta[key] = { manufacturer: row.manufacturer, product_type: row.product_type, source: row.source_document, competitor: row.competitor_name };
      }
    }

    // Group OSINT by competitor
    const osintByCompetitor: Record<string, Array<{ domain: string; scan_type: string; finding_type: string; finding_value: string; severity: string; source_tool: string }>> = {};
    const osintBySeverity: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const row of allOsint.results as Array<any>) {
      if (!osintByCompetitor[row.competitor_name]) osintByCompetitor[row.competitor_name] = [];
      osintByCompetitor[row.competitor_name].push({
        domain: row.domain, scan_type: row.scan_type, finding_type: row.finding_type,
        finding_value: row.finding_value, severity: row.severity, source_tool: row.source_tool
      });
      const sev = (row.severity || 'info').toLowerCase();
      osintBySeverity[sev] = (osintBySeverity[sev] || 0) + 1;
    }

    // Group market intel by category
    const marketByCategory: Record<string, Array<any>> = {};
    for (const row of allMarketIntel.results as Array<any>) {
      if (!marketByCategory[row.category]) marketByCategory[row.category] = [];
      marketByCategory[row.category].push(row);
    }

    return json({
      generated_at: new Date().toISOString(),
      totals: {
        competitors: competitors.results.length,
        pages_scraped: totalPages?.c || 0,
        intel_extracted: totalIntel?.c || 0,
        tech_signals: allTech.results.length,
        exposed_endpoints: allEndpoints.results.length,
        reveng_reports: allReports.results.length,
        contacts: allContacts.results.length,
        products: allProducts.results.length,
        formulations: allFormulations.results.length,
        market_intel: allMarketIntel.results.length,
        patents: allPatents.results.length,
        osint_findings: allOsint.results.length,
      },
      competitors: competitors.results,
      pages_by_competitor: enrichedPages,
      chemical_product_matrix: chemMatrix,
      service_area_map: serviceAreaMap,
      certification_map: certMap,
      tech_by_competitor: techByCompetitor,
      endpoints_by_competitor: endpointsByCompetitor,
      contacts_by_competitor: contactsByCompetitor,
      products_by_competitor: productsByCompetitor,
      reveng_by_competitor: revengByCompetitor,
      formulations_by_product: formulationsByProduct,
      formulation_meta: formulationMeta,
      market_intel_by_category: marketByCategory,
      patents: allPatents.results,
      osint_by_competitor: osintByCompetitor,
      osint_by_severity: osintBySeverity,
    });
  }

  // Init DB
  if (path === '/init') {
    const statements = SCHEMA.split(';').map(s => s.trim()).filter(s => s.length > 0);
    for (const stmt of statements) {
      await env.DB.prepare(stmt).run();
    }
    return json({ status: 'initialized', tables: statements.length });
  }

  // List registered competitors with D1 intel counts
  if (path === '/competitors') {
    const dbCompetitors = await env.DB.prepare(`
      SELECT c.*,
        (SELECT COUNT(*) FROM chemical_formulations WHERE competitor_id = c.id) as formulation_count,
        (SELECT COUNT(*) FROM patents WHERE competitor_id = c.id) as patent_count,
        (SELECT COUNT(*) FROM competitor_osint WHERE competitor_id = c.id) as osint_count,
        (SELECT COUNT(*) FROM competitor_financials WHERE competitor_id = c.id) as financial_count,
        (SELECT COUNT(*) FROM market_intel WHERE competitor_id = c.id) as market_intel_count
      FROM competitors c ORDER BY c.priority DESC, c.name
    `).all();
    return json({ competitors: dbCompetitors.results, registry: COMPETITORS, count: dbCompetitors.results.length });
  }

  // ─── COMPETITOR OSINT (Prometheus scans, WHOIS, subdomains, IPs) ─────────
  if (path === '/competitor-osint') {
    const competitorId = url.searchParams.get('competitor_id');
    const severity = url.searchParams.get('severity');
    let query = `SELECT co.*, c.name as competitor_name FROM competitor_osint co LEFT JOIN competitors c ON co.competitor_id = c.id`;
    const conditions: string[] = [];
    const params: (string | number)[] = [];
    if (competitorId) { conditions.push('co.competitor_id = ?'); params.push(Number(competitorId)); }
    if (severity) { conditions.push('co.severity = ?'); params.push(severity); }
    if (conditions.length) query += ' WHERE ' + conditions.join(' AND ');
    query += ' ORDER BY CASE co.severity WHEN \'critical\' THEN 0 WHEN \'high\' THEN 1 WHEN \'medium\' THEN 2 WHEN \'low\' THEN 3 ELSE 4 END, co.competitor_id';
    const stmt = env.DB.prepare(query);
    const rows = params.length ? await stmt.bind(...params).all() : await stmt.all();
    return json({ osint: rows.results, count: rows.results.length });
  }

  // ─── COMPETITOR FINANCIALS ───────────────────────────────────────────────
  if (path === '/competitor-financials') {
    const rows = await env.DB.prepare(`
      SELECT cf.*, c.name as competitor_name FROM competitor_financials cf
      LEFT JOIN competitors c ON cf.competitor_id = c.id
      ORDER BY cf.revenue DESC
    `).all();
    return json({ financials: rows.results, count: rows.results.length });
  }

  // ─── ALL INTEL SUMMARY (single endpoint for dashboard) ──────────────────
  if (path === '/intel-summary') {
    const [competitors, formulations, patents, marketIntel, osint, financials] = await Promise.all([
      env.DB.prepare(`SELECT * FROM competitors ORDER BY name`).all(),
      env.DB.prepare(`SELECT cf.*, c.name as competitor_name FROM chemical_formulations cf LEFT JOIN competitors c ON cf.competitor_id = c.id ORDER BY cf.product_name`).all(),
      env.DB.prepare(`SELECT * FROM patents ORDER BY filing_date DESC`).all(),
      env.DB.prepare(`SELECT * FROM market_intel ORDER BY category`).all(),
      env.DB.prepare(`SELECT co.*, c.name as competitor_name FROM competitor_osint co LEFT JOIN competitors c ON co.competitor_id = c.id ORDER BY co.severity`).all(),
      env.DB.prepare(`SELECT cf.*, c.name as competitor_name FROM competitor_financials cf LEFT JOIN competitors c ON cf.competitor_id = c.id ORDER BY cf.revenue DESC`).all(),
    ]);
    return json({
      generated_at: new Date().toISOString(),
      totals: {
        competitors: competitors.results.length,
        formulations: formulations.results.length,
        patents: patents.results.length,
        market_intel: marketIntel.results.length,
        osint: osint.results.length,
        financials: financials.results.length,
      },
      competitors: competitors.results,
      formulations: formulations.results,
      patents: patents.results,
      market_intel: marketIntel.results,
      osint: osint.results,
      financials: financials.results,
    });
  }

  // ─── CHEMICAL FORMULATIONS (SDS data) ──────────────────────────────────────
  if (path === '/formulations') {
    const rows = await env.DB.prepare(`
      SELECT cf.*, c.name as competitor_name FROM chemical_formulations cf
      LEFT JOIN competitors c ON cf.competitor_id = c.id
      ORDER BY cf.product_name, cf.chemical_name
    `).all();
    return json({ formulations: rows.results, count: rows.results.length });
  }

  // ─── MARKET INTELLIGENCE ───────────────────────────────────────────────────
  if (path === '/market-intel') {
    const rows = await env.DB.prepare(`SELECT * FROM market_intel ORDER BY category, metric_name`).all();
    return json({ market_intel: rows.results, count: rows.results.length });
  }

  // ─── PATENTS ───────────────────────────────────────────────────────────────
  if (path === '/patents') {
    const rows = await env.DB.prepare(`SELECT * FROM patents ORDER BY filing_date DESC`).all();
    return json({ patents: rows.results, count: rows.results.length });
  }

  // ─── INTEL COLLECTION TRIGGER ───────────────────────────────────────────────
  if (path === '/collect-intel' && request.method === 'POST') {
    const body = await request.json().catch(() => ({})) as { sources?: string[] };
    const results = await runIntelCollection(env, body.sources);
    const totalCollected = Object.values(results).reduce((a, r) => a + r.collected, 0);
    const totalErrors = Object.values(results).reduce((a, r) => a + r.errors.length, 0);
    return json({
      total_collected: totalCollected,
      total_errors: totalErrors,
      by_source: results,
    });
  }

  // ─── INDIVIDUAL SOURCE TRIGGERS ───────────────────────────────────────────
  if (path === '/collect/sec-edgar' && request.method === 'POST') {
    const result = await collectSECEdgar(env);
    return json(result);
  }
  if (path === '/collect/google-news' && request.method === 'POST') {
    const result = await collectGoogleNews(env);
    return json(result);
  }
  if (path === '/collect/pubchem' && request.method === 'POST') {
    const result = await collectPubChem(env);
    return json(result);
  }
  if (path === '/collect/securitytrails' && request.method === 'POST') {
    const result = await collectSecurityTrails(env);
    return json(result);
  }
  if (path === '/collect/patents' && request.method === 'POST') {
    const result = await collectPatents(env);
    return json(result);
  }
  if (path === '/collect/newsapi' && request.method === 'POST') {
    const result = await collectNewsAPI(env);
    return json(result);
  }
  if (path === '/collect/usaspending' && request.method === 'POST') {
    const result = await collectUSASpending(env);
    return json(result);
  }
  if (path === '/collect/sam-gov' && request.method === 'POST') {
    const result = await collectSAMGov(env);
    return json(result);
  }
  if (path === '/collect/distributors' && request.method === 'POST') {
    const result = await collectDistributorPricing(env);
    return json(result);
  }

  // ─── PRICING DATA ──────────────────────────────────────────────────────────
  if (path === '/pricing') {
    const vendor = url.searchParams.get('vendor');
    const category = url.searchParams.get('category');
    const limit = parseInt(url.searchParams.get('limit') || '100');

    let query = 'SELECT pd.*, c.name as competitor_name FROM pricing_data pd LEFT JOIN competitors c ON pd.competitor_id = c.id';
    const conditions: string[] = [];
    const params: (string | number)[] = [];

    if (vendor) { conditions.push('pd.vendor LIKE ?'); params.push(`%${vendor}%`); }
    if (category) { conditions.push('pd.product_category = ?'); params.push(category); }
    if (conditions.length) query += ' WHERE ' + conditions.join(' AND ');
    query += ' ORDER BY pd.price DESC LIMIT ?';
    params.push(limit);

    const stmt = env.DB.prepare(query);
    const rows = await stmt.bind(...params).all();

    // Summary stats
    const totalValue = (rows.results as Array<{ price: number }>).reduce((a, r) => a + (r.price || 0), 0);
    const vendors = [...new Set((rows.results as Array<{ vendor: string }>).map(r => r.vendor).filter(Boolean))];
    const categories = [...new Set((rows.results as Array<{ product_category: string }>).map(r => r.product_category).filter(Boolean))];

    return json({
      pricing: rows.results,
      count: rows.results.length,
      total_contract_value: totalValue,
      unique_vendors: vendors.length,
      vendors,
      categories,
    });
  }

  // ─── INGEST PRICING (from local Python collector) ─────────────────────────
  if (path === '/ingest-pricing' && request.method === 'POST') {
    const body = await request.json() as { records: Array<{
      product_name?: string; product_category?: string; price?: number;
      price_unit?: string; source?: string; source_url?: string;
      contract_number?: string; buyer?: string; vendor?: string;
      award_date?: string; confidence?: number; notes?: string;
      competitor_name?: string;
    }> };

    if (!body.records || !Array.isArray(body.records)) {
      return json({ error: 'Missing records array' }, 400);
    }

    let inserted = 0;
    let errors = 0;

    for (const r of body.records) {
      try {
        // Match competitor_name to competitor_id
        let competitorId: number | null = null;
        if (r.competitor_name) {
          const comp = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?')
            .bind(r.competitor_name).first<{ id: number }>();
          if (comp) competitorId = comp.id;
        }

        await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
          (competitor_id, product_name, product_category, price, price_unit, source, source_url,
           contract_number, buyer, vendor, award_date, confidence, notes)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
          .bind(
            competitorId,
            (r.product_name || 'Unknown')?.slice(0, 200),
            r.product_category || 'unknown',
            r.price || 0,
            r.price_unit || 'USD',
            r.source || 'local_collector',
            r.source_url || '',
            r.contract_number || '',
            r.buyer || '',
            r.vendor || '',
            r.award_date || '',
            r.confidence || 0.5,
            r.notes || '',
          ).run();
        inserted++;
      } catch (e: unknown) {
        errors++;
      }
    }

    return json({ inserted, errors, total: body.records.length });
  }

  // ─── INGEST COMPETITOR PRODUCTS (catalog data from scraping) ─────────────
  if (path === '/ingest-products' && request.method === 'POST') {
    const body = await request.json() as { records: Array<{
      competitor_name: string; finding_type: string; finding_value: string;
      details?: string; scan_type?: string;
    }> };

    if (!body.records || !Array.isArray(body.records)) {
      return json({ error: 'Missing records array' }, 400);
    }

    let inserted = 0;
    for (const r of body.records) {
      try {
        const comp = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?')
          .bind(r.competitor_name).first<{ id: number }>();
        if (!comp) continue;

        await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
          (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool, scanned_at)
          VALUES (?, ?, ?, ?, ?, 'info', ?, 'web_scrape', datetime('now'))`)
          .bind(comp.id, '', r.scan_type || 'product_catalog', r.finding_type, r.finding_value, r.details || '')
          .run();
        inserted++;
      } catch { /* skip */ }
    }
    return json({ inserted, total: body.records.length });
  }

  // ─── CLEANUP OSINT (remove noise, keep actionable intel) ─────────────────
  if (path === '/cleanup-osint' && request.method === 'POST') {
    // Delete duplicate subdomains, missing_security_header noise, and junk values
    const noiseTypes = ['missing_security_header'];
    const noiseValues = ['United States', 'Content-Security-Policy', 'X-XSS-Protection',
      'X-Frame-Options', 'X-Content-Type-Options', 'Strict-Transport-Security',
      '0', '', 'None', 'null', 'unsigned'];

    // 1. Delete noise finding_types
    const r1 = await env.DB.prepare(
      `DELETE FROM competitor_osint WHERE finding_type IN ('missing_security_header')`
    ).run();

    // 2. Delete noise finding_values
    const r2 = await env.DB.prepare(
      `DELETE FROM competitor_osint WHERE finding_value IN ('United States','Content-Security-Policy','X-XSS-Protection','X-Frame-Options','X-Content-Type-Options','Strict-Transport-Security','0','','None','null','unsigned')`
    ).run();

    // 3. Deduplicate: keep lowest ID per (competitor_id, finding_type, finding_value)
    const r3 = await env.DB.prepare(`
      DELETE FROM competitor_osint WHERE id NOT IN (
        SELECT MIN(id) FROM competitor_osint GROUP BY competitor_id, finding_type, finding_value
      )
    `).run();

    // 4. Delete bulk subdomain records (keep only categorized ones like subdomain_api, subdomain_dev, etc.)
    const r4 = await env.DB.prepare(
      `DELETE FROM competitor_osint WHERE finding_type = 'subdomain' AND scan_type IN ('subfinder','harvester','theHarvester')`
    ).run();

    const remaining = await env.DB.prepare('SELECT COUNT(*) as cnt FROM competitor_osint').first<{cnt: number}>();

    return json({
      cleaned: true,
      deleted_noise_types: r1.meta?.changes || 0,
      deleted_noise_values: r2.meta?.changes || 0,
      deleted_duplicates: r3.meta?.changes || 0,
      deleted_bulk_subdomains: r4.meta?.changes || 0,
      remaining: remaining?.cnt || 0,
    });
  }

  // ─── NEWS INTEL ───────────────────────────────────────────────────────────
  if (path === '/news') {
    const competitorId = url.searchParams.get('competitor_id');
    const limit = parseInt(url.searchParams.get('limit') || '50');
    let query = `SELECT ni.*, c.name as competitor_name FROM news_intel ni LEFT JOIN competitors c ON ni.competitor_id = c.id`;
    if (competitorId) query += ` WHERE ni.competitor_id = ${parseInt(competitorId)}`;
    query += ` ORDER BY ni.published_at DESC LIMIT ${limit}`;
    const rows = await env.DB.prepare(query).all();
    return json({ news: rows.results, count: rows.results.length });
  }

  // ─── INTEL COLLECTION LOG ─────────────────────────────────────────────────
  if (path === '/collection-log') {
    const rows = await env.DB.prepare(`SELECT * FROM intel_collection_log ORDER BY id DESC LIMIT 50`).all();
    return json({ log: rows.results, count: rows.results.length });
  }

  return json({ error: 'Not found', endpoints: [
    '/health', '/stats', '/competitors', '/competitor/:name',
    '/scrape', '/scrape-products', '/pricing-intel',
    '/reveng', '/reveng/test', '/reveng/debug', '/init',
    '/formulations', '/market-intel', '/patents',
    '/competitor-osint', '/competitor-financials',
    '/intel-summary', '/report-data', '/news', '/collection-log',
    '/collect-intel', '/collect/sec-edgar', '/collect/google-news',
    '/collect/pubchem', '/collect/securitytrails', '/collect/patents', '/collect/newsapi',
    '/collect/usaspending', '/collect/sam-gov', '/collect/distributors', '/pricing',
    '/ingest-pricing'
  ] }, 404);
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTOMATED INTEL COLLECTION — 6 EXTERNAL SOURCES
// SEC EDGAR (free) | Google News RSS (free) | PubChem (free)
// SecurityTrails (API key) | USPTO Patents (free) | FracFocus (free)
// ═══════════════════════════════════════════════════════════════════════════════

// SEC EDGAR CIK mappings for public Permian Basin chemical companies
const SEC_CIKS: Record<string, string> = {
  'Champion X': '0001723089',       // CHX — top competitor
  'Ecolab': '0000031462',           // ECL — parent/related
  'Halliburton': '0000045012',      // HAL — major player
  'Cactus Well Head': '0001699136', // WHD — Permian Basin
  'Select Water': '0001693256',     // WTTR — water services
  'Solaris Oilfield': '0001697500', // SOI — Permian Basin
  'Flotek Industries': '0000928054', // FTK — oilfield chemistry
  'Newpark Resources': '0000071829', // NR — fluids & chemicals
  'ChampionX (alt)': '0001723089',
};

// Map SEC companies to our competitor registry
const SEC_TO_COMPETITOR: Record<string, string> = {
  'Champion X': 'Champion X',
  'ChampionX (alt)': 'Champion X',
  'Halliburton': 'Halliburton',
  'Flotek Industries': 'Flotek Industries',
};

// ─── SEC EDGAR COLLECTOR ─────────────────────────────────────────────────────

async function collectSECEdgar(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('sec_edgar', 'financials', 'running')`).run();

  for (const [companyName, cik] of Object.entries(SEC_CIKS)) {
    try {
      // SEC EDGAR XBRL API — no auth needed, just User-Agent
      const url = `https://data.sec.gov/api/xbrl/companyfacts/CIK${cik}.json`;
      const resp = await fetch(url, {
        headers: {
          'User-Agent': 'EchoPrimeTech bobbymcwilliams@echo-op.com',
          'Accept': 'application/json',
        },
        signal: AbortSignal.timeout(15000),
      });

      if (!resp.ok) {
        errors.push(`SEC EDGAR ${companyName}: HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as {
        entityName: string;
        facts: {
          'us-gaap'?: Record<string, {
            label: string;
            units: Record<string, Array<{
              val: number;
              end: string;
              fy: number;
              fp: string;
              form: string;
              filed: string;
            }>>;
          }>;
          dei?: Record<string, {
            units: Record<string, Array<{
              val: number | string;
              end: string;
              fy: number;
              fp: string;
              form: string;
            }>>;
          }>;
        };
      };

      const entityName = data.entityName || companyName;

      // Find competitor_id if this maps to one of our tracked competitors
      const matchedCompetitor = SEC_TO_COMPETITOR[companyName];
      let competitorId: number | null = null;
      if (matchedCompetitor) {
        const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(matchedCompetitor).first<{ id: number }>();
        competitorId = row?.id || null;
      }

      // Extract key financial metrics
      const gaap = data.facts?.['us-gaap'] || {};

      // Revenue
      const revenueKey = gaap['Revenues'] || gaap['RevenueFromContractWithCustomerExcludingAssessedTax'] || gaap['SalesRevenueNet'];
      if (revenueKey) {
        const usdEntries = revenueKey.units?.['USD'] || [];
        // Get annual (10-K) filings, last 3 years
        const annuals = usdEntries
          .filter(e => e.form === '10-K' && e.fp === 'FY')
          .sort((a, b) => b.fy - a.fy)
          .slice(0, 3);

        for (const entry of annuals) {
          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_financials
            (competitor_id, fiscal_year, revenue, segment, key_metrics, source)
            VALUES (?, ?, ?, ?, ?, ?)`).bind(
            competitorId, entry.fy, String(entry.val), `${entityName} (CIK: ${cik})`,
            `Filing: ${entry.form} | Filed: ${entry.filed}`,
            `SEC EDGAR | https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}&type=10-K`
          ).run();
          collected++;
        }
      }

      // Net Income
      const netIncomeKey = gaap['NetIncomeLoss'];
      if (netIncomeKey) {
        const usdEntries = netIncomeKey.units?.['USD'] || [];
        const annuals = usdEntries
          .filter(e => e.form === '10-K' && e.fp === 'FY')
          .sort((a, b) => b.fy - a.fy)
          .slice(0, 3);

        for (const entry of annuals) {
          await env.DB.prepare(`INSERT OR IGNORE INTO market_intel
            (category, metric_name, metric_value, unit, source, source_url, year, confidence)
            VALUES ('financials', ?, ?, 'USD', 'SEC EDGAR 10-K', ?, ?, 0.95)`).bind(
            `${entityName}_net_income`, String(entry.val),
            `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}&type=10-K`,
            String(entry.fy)
          ).run();
          collected++;
        }
      }

      // Employee count from DEI
      const dei = data.facts?.dei || {};
      const empKey = dei['EntityNumberOfEmployees'];
      if (empKey) {
        const entries = empKey.units?.['pure'] || empKey.units?.['employees'] || [];
        const latest = entries
          .filter(e => e.form === '10-K')
          .sort((a, b) => b.fy - a.fy)
          .slice(0, 1);

        for (const entry of latest) {
          if (competitorId) {
            await env.DB.prepare(`UPDATE competitors SET notes = notes || ' | Employees: ' || ? WHERE id = ? AND notes NOT LIKE '%Employees:%'`).bind(
              String(entry.val), competitorId
            ).run();
          }
          await env.DB.prepare(`INSERT OR IGNORE INTO market_intel
            (category, metric_name, metric_value, unit, source, source_url, year, confidence)
            VALUES ('workforce', ?, ?, 'employees', 'SEC EDGAR DEI', ?, ?, 0.9)`).bind(
            `${entityName}_employee_count`, String(entry.val),
            `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}`,
            String(entry.fy)
          ).run();
          collected++;
        }
      }

      // SIC code (industry classification)
      const sicKey = dei['EntityCommonStockSharesOutstanding'] || dei['EntityRegistrantName'];
      // Get SIC from company search
      const searchUrl = `https://efts.sec.gov/LATEST/search-index?q=%22${encodeURIComponent(entityName)}%22&dateRange=custom&startdt=2024-01-01&forms=10-K`;
      try {
        const searchResp = await fetch(`https://efts.sec.gov/LATEST/search-index?q=%22${cik}%22&forms=10-K`, {
          headers: { 'User-Agent': 'EchoPrimeTech bobbymcwilliams@echo-op.com' },
          signal: AbortSignal.timeout(8000),
        });
        // Best effort - SIC data may not always be available
      } catch { /* skip */ }

      log('info', `SEC EDGAR collected: ${entityName}`, { cik, records: collected });

    } catch (err) {
      errors.push(`SEC EDGAR ${companyName}: ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'sec_edgar' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── GOOGLE NEWS RSS COLLECTOR ───────────────────────────────────────────────

async function collectGoogleNews(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('google_news', 'news', 'running')`).run();

  // Build search queries for each competitor + industry terms
  const searchQueries = [
    // Company-specific queries
    ...COMPETITORS.filter(c => c.priority === 'high').map(c => ({
      query: `"${c.name}" oilfield chemicals`,
      competitorName: c.name,
    })),
    // Industry-wide queries
    { query: 'Permian Basin oilfield chemicals market', competitorName: null as string | null },
    { query: 'oilfield water treatment chemicals Texas', competitorName: null },
    { query: 'Permian Basin production chemicals company', competitorName: null },
    { query: 'oilfield chemical company acquisition merger Permian', competitorName: null },
  ];

  for (const { query, competitorName } of searchQueries) {
    try {
      // Google News RSS feed - no API key needed
      const rssUrl = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-US&gl=US&ceid=US:en`;
      const resp = await fetch(rssUrl, {
        headers: { 'User-Agent': UA },
        signal: AbortSignal.timeout(10000),
      });

      if (!resp.ok) {
        errors.push(`Google News "${query}": HTTP ${resp.status}`);
        continue;
      }

      const xml = await resp.text();

      // Parse RSS XML for items
      const items = parseRSSItems(xml);

      // Find competitor_id
      let competitorId: number | null = null;
      if (competitorName) {
        const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(competitorName).first<{ id: number }>();
        competitorId = row?.id || null;
      }

      for (const item of items.slice(0, 10)) {
        // Check if we already have this URL
        const existing = await env.DB.prepare('SELECT id FROM news_intel WHERE url = ?').bind(item.link).first();
        if (existing) continue;

        // Determine sentiment from title keywords
        const sentiment = detectNewsSentiment(item.title);

        // Check if any competitor is mentioned
        let matchedCompId = competitorId;
        if (!matchedCompId) {
          for (const comp of COMPETITORS) {
            if (item.title.toLowerCase().includes(comp.name.toLowerCase())) {
              const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
              matchedCompId = row?.id || null;
              break;
            }
          }
        }

        await env.DB.prepare(`INSERT OR IGNORE INTO news_intel
          (competitor_id, headline, source_name, published_at, url, snippet, sentiment, relevance)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).bind(
          matchedCompId, item.title, item.source, item.pubDate, item.link,
          item.description?.slice(0, 500) || '', sentiment, competitorName ? 0.8 : 0.5
        ).run();
        collected++;

        // Also store as market intel if industry-relevant
        if (!competitorName && item.title.length > 10) {
          await env.DB.prepare(`INSERT OR IGNORE INTO market_intel
            (category, metric_name, metric_value, source, source_url, year, confidence, notes)
            VALUES ('news', 'headline', ?, 'Google News RSS', ?, ?, 0.6, ?)`).bind(
            item.title, item.link, new Date().getFullYear().toString(), item.description?.slice(0, 300) || ''
          ).run();
        }
      }

    } catch (err) {
      errors.push(`Google News "${query}": ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'google_news' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

function parseRSSItems(xml: string): Array<{ title: string; link: string; description: string; pubDate: string; source: string }> {
  const items: Array<{ title: string; link: string; description: string; pubDate: string; source: string }> = [];
  const itemRegex = /<item>([\s\S]*?)<\/item>/gi;
  let match;

  while ((match = itemRegex.exec(xml)) !== null) {
    const itemXml = match[1];
    const title = extractXmlTag(itemXml, 'title');
    const link = extractXmlTag(itemXml, 'link');
    const description = extractXmlTag(itemXml, 'description');
    const pubDate = extractXmlTag(itemXml, 'pubDate');
    const source = extractXmlTag(itemXml, 'source') || 'Google News';

    if (title && link) {
      items.push({ title: decodeHTMLEntities(title), link, description: decodeHTMLEntities(description), pubDate, source });
    }
  }

  return items;
}

function extractXmlTag(xml: string, tag: string): string {
  const m = xml.match(new RegExp(`<${tag}[^>]*>(?:<!\\[CDATA\\[)?([\\s\\S]*?)(?:\\]\\]>)?<\\/${tag}>`, 'i'));
  return m ? m[1].trim() : '';
}

function decodeHTMLEntities(text: string): string {
  return text
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'");
}

function parsePatentRSS(xml: string): Array<{ patentNumber: string; title: string; link: string; abstract: string; assignee: string; filingDate: string }> {
  const patents: Array<{ patentNumber: string; title: string; link: string; abstract: string; assignee: string; filingDate: string }> = [];
  const itemRegex = /<item>([\s\S]*?)<\/item>/gi;
  let match;

  while ((match = itemRegex.exec(xml)) !== null) {
    const itemXml = match[1];
    const title = decodeHTMLEntities(extractXmlTag(itemXml, 'title'));
    const link = extractXmlTag(itemXml, 'link');
    const description = decodeHTMLEntities(extractXmlTag(itemXml, 'description'));

    // Extract patent number from link (e.g., https://patents.google.com/patent/US12345678B2/en)
    const patNumMatch = link.match(/patent\/([A-Z]{2}\d+[A-Z]\d*)/);
    const patentNumber = patNumMatch ? patNumMatch[1] : '';

    // Try to extract assignee from description
    const assigneeMatch = description.match(/(?:Assignee|Applicant)[:\s]*([^<\n,]+)/i);
    const assignee = assigneeMatch ? assigneeMatch[1].trim() : '';

    // Try to extract filing date
    const dateMatch = description.match(/(?:Filed|Filing date)[:\s]*(\d{4}-\d{2}-\d{2}|\w+\s+\d+,?\s*\d{4})/i);
    const filingDate = dateMatch ? dateMatch[1] : '';

    if (patentNumber && title) {
      patents.push({
        patentNumber,
        title,
        link,
        abstract: description.replace(/<[^>]+>/g, ' ').slice(0, 2000),
        assignee,
        filingDate,
      });
    }
  }

  return patents;
}

function detectNewsSentiment(title: string): string {
  const lower = title.toLowerCase();
  const positive = ['growth', 'expand', 'profit', 'acquisition', 'partnership', 'launch', 'record', 'award', 'innovation', 'invest'];
  const negative = ['layoff', 'decline', 'loss', 'lawsuit', 'fine', 'penalty', 'spill', 'violation', 'recall', 'bankrupt', 'shutdown'];
  if (positive.some(w => lower.includes(w))) return 'positive';
  if (negative.some(w => lower.includes(w))) return 'negative';
  return 'neutral';
}

// ─── PUBCHEM CHEMICAL DATA COLLECTOR ─────────────────────────────────────────

// Key oilfield chemicals to look up in PubChem
const OILFIELD_CHEMICALS = [
  { name: 'Glutaraldehyde', cid: '3485', type: 'biocide', application: 'water treatment' },
  { name: 'THPS', cid: '71316', type: 'biocide', application: 'H2S scavenger + biocide' },
  { name: 'Acrolein', cid: '7847', type: 'biocide', application: 'biocide + scale' },
  { name: 'DBNPA', cid: '22671', type: 'biocide', application: 'non-oxidizing biocide' },
  { name: 'Methanol', cid: '887', type: 'hydrate_inhibitor', application: 'hydrate prevention' },
  { name: 'Ethylene glycol', cid: '174', type: 'hydrate_inhibitor', application: 'MEG hydrate inhibitor' },
  { name: 'Polyacrylamide', cid: '73082', type: 'friction_reducer', application: 'fracturing fluid' },
  { name: 'Guar gum', cid: '24846', type: 'gelling_agent', application: 'fracturing fluid' },
  { name: 'Citric acid', cid: '311', type: 'iron_control', application: 'iron chelation' },
  { name: 'EDTA', cid: '6049', type: 'chelating_agent', application: 'scale treatment' },
  { name: 'Hydrochloric acid', cid: '313', type: 'acid', application: 'acidizing' },
  { name: 'Sodium hypochlorite', cid: '23665760', type: 'oxidizing_biocide', application: 'water treatment' },
  { name: 'Sodium bisulfite', cid: '23665763', type: 'oxygen_scavenger', application: 'corrosion control' },
  { name: 'Phosphonate', cid: '1004', type: 'scale_inhibitor', application: 'scale prevention' },
  { name: 'Triazine', cid: '9260', type: 'h2s_scavenger', application: 'H2S removal' },
  { name: 'Isopropanol', cid: '3776', type: 'solvent', application: 'paraffin treatment' },
  { name: 'Xylene', cid: '7237', type: 'solvent', application: 'paraffin/asphaltene solvent' },
  { name: 'Toluene', cid: '1140', type: 'solvent', application: 'aromatic solvent' },
  { name: 'Potassium chloride', cid: '4873', type: 'clay_stabilizer', application: 'clay control' },
  { name: 'Ammonium persulfate', cid: '62648', type: 'breaker', application: 'gel breaker' },
];

async function collectPubChem(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('pubchem', 'chemicals', 'running')`).run();

  for (const chem of OILFIELD_CHEMICALS) {
    try {
      // Check cache to avoid hammering PubChem
      const cacheKey = `pubchem:${chem.cid}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      // PubChem PUG REST API — free, no auth
      const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${chem.cid}/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES,IsomericSMILES,InChI,XLogP,ExactMass/JSON`;
      const resp = await fetch(url, {
        headers: { 'User-Agent': UA },
        signal: AbortSignal.timeout(10000),
      });

      if (!resp.ok) {
        errors.push(`PubChem ${chem.name}: HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as {
        PropertyTable: {
          Properties: Array<{
            CID: number;
            MolecularFormula: string;
            MolecularWeight: number;
            IUPACName: string;
            CanonicalSMILES: string;
            XLogP: number;
            ExactMass: number;
          }>;
        };
      };

      const props = data.PropertyTable?.Properties?.[0];
      if (!props) continue;

      // Get CAS number from synonyms
      let casNumber = '';
      try {
        const synResp = await fetch(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${chem.cid}/synonyms/JSON`, {
          headers: { 'User-Agent': UA },
          signal: AbortSignal.timeout(8000),
        });
        if (synResp.ok) {
          const synData = await synResp.json() as { InformationList: { Information: Array<{ Synonym: string[] }> } };
          const synonyms = synData.InformationList?.Information?.[0]?.Synonym || [];
          const casMatch = synonyms.find(s => /^\d{1,7}-\d{2}-\d$/.test(s));
          if (casMatch) casNumber = casMatch;
        }
      } catch { /* skip */ }

      // Store as chemical formulation reference data
      await env.DB.prepare(`INSERT OR IGNORE INTO chemical_formulations
        (competitor_id, product_name, manufacturer, product_type, cas_number, chemical_name,
         source_document, source_url, confidence)
        VALUES (NULL, ?, 'PubChem Reference', ?, ?, ?, 'PubChem CID ${chem.cid}: MW=${props.MolecularWeight}, Formula=${props.MolecularFormula}, IUPAC=${props.IUPACName}',
         ?, 0.95)`).bind(
        chem.name, chem.type, casNumber, props.IUPACName || chem.name,
        `https://pubchem.ncbi.nlm.nih.gov/compound/${chem.cid}`
      ).run();
      collected++;

      // Store key properties as market intel
      await env.DB.prepare(`INSERT OR IGNORE INTO market_intel
        (category, metric_name, metric_value, unit, source, source_url, confidence, notes)
        VALUES ('chemical_reference', ?, ?, ?, 'PubChem', ?, 0.95, ?)`).bind(
        `${chem.name}_molecular_weight`, String(props.MolecularWeight), 'g/mol',
        `https://pubchem.ncbi.nlm.nih.gov/compound/${chem.cid}`,
        `Application: ${chem.application} | Formula: ${props.MolecularFormula} | CAS: ${casNumber}`
      ).run();
      collected++;

      // Cache for 7 days (PubChem data doesn't change often)
      await env.CACHE.put(cacheKey, JSON.stringify({ collected: true, cas: casNumber }), { expirationTtl: 604800 });

      log('info', `PubChem collected: ${chem.name}`, { cid: chem.cid, cas: casNumber, mw: props.MolecularWeight });

    } catch (err) {
      errors.push(`PubChem ${chem.name}: ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'pubchem' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── SECURITYTRAILS DNS/SUBDOMAIN COLLECTOR ──────────────────────────────────

async function collectSecurityTrails(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  const apiKey = env.SECURITYTRAILS_API_KEY;
  if (!apiKey) {
    return { collected: 0, errors: ['SECURITYTRAILS_API_KEY not configured'] };
  }

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('securitytrails', 'osint', 'running')`).run();

  // Get domains from competitors that have websites
  const competitorsWithSites = await env.DB.prepare('SELECT id, name, website_url FROM competitors WHERE website_url IS NOT NULL').all<{ id: number; name: string; website_url: string }>();

  for (const comp of competitorsWithSites.results) {
    try {
      // Extract domain from URL
      let domain: string;
      try {
        domain = new URL(comp.website_url).hostname.replace('www.', '');
      } catch {
        continue;
      }

      // Check cache (scan weekly)
      const cacheKey = `st:${domain}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      // 1. Get domain details
      const detailResp = await fetch(`https://api.securitytrails.com/v1/domain/${domain}`, {
        headers: { 'APIKEY': apiKey, 'Accept': 'application/json' },
        signal: AbortSignal.timeout(10000),
      });

      if (detailResp.ok) {
        const detail = await detailResp.json() as {
          hostname: string;
          current_dns: {
            a?: { values: Array<{ ip: string }> };
            mx?: { values: Array<{ hostname: string; priority: number }> };
            ns?: { values: Array<{ nameserver: string }> };
            txt?: { values: Array<{ value: string }> };
          };
          alexa_rank?: number;
        };

        // Store DNS records as OSINT
        const dns = detail.current_dns || {};

        // A records (IP addresses)
        for (const a of (dns.a?.values || [])) {
          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
            (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
            VALUES (?, ?, 'dns', 'a_record', ?, 'info', 'IP address hosting', 'SecurityTrails')`).bind(
            comp.id, domain, a.ip
          ).run();
          collected++;
        }

        // MX records (email infrastructure)
        for (const mx of (dns.mx?.values || [])) {
          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
            (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
            VALUES (?, ?, 'dns', 'mx_record', ?, 'info', ?, 'SecurityTrails')`).bind(
            comp.id, domain, mx.hostname, `Priority: ${mx.priority} — reveals email provider`
          ).run();
          collected++;
        }

        // NS records (DNS provider)
        for (const ns of (dns.ns?.values || [])) {
          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
            (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
            VALUES (?, ?, 'dns', 'ns_record', ?, 'info', 'Nameserver — reveals DNS provider', 'SecurityTrails')`).bind(
            comp.id, domain, ns.nameserver
          ).run();
          collected++;
        }

        // TXT records (SPF, DKIM, verification records — can reveal services)
        for (const txt of (dns.txt?.values || [])) {
          const severity = txt.value.includes('v=spf') ? 'info'
            : txt.value.includes('google-site-verification') || txt.value.includes('facebook-domain-verification') ? 'low'
            : txt.value.includes('_dmarc') ? 'info'
            : 'info';
          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
            (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
            VALUES (?, ?, 'dns', 'txt_record', ?, ?, 'TXT record — may reveal third-party services', 'SecurityTrails')`).bind(
            comp.id, domain, txt.value.slice(0, 500), severity
          ).run();
          collected++;
        }
      }

      // 2. Get subdomains
      const subResp = await fetch(`https://api.securitytrails.com/v1/domain/${domain}/subdomains?children_only=false`, {
        headers: { 'APIKEY': apiKey, 'Accept': 'application/json' },
        signal: AbortSignal.timeout(10000),
      });

      if (subResp.ok) {
        const subData = await subResp.json() as { subdomains: string[]; endpoint: string };
        const subdomains = subData.subdomains || [];

        for (const sub of subdomains.slice(0, 50)) {
          const fullSub = `${sub}.${domain}`;
          const severity = ['admin', 'staging', 'dev', 'test', 'internal', 'vpn', 'api', 'portal'].some(s => sub.includes(s)) ? 'medium'
            : ['mail', 'smtp', 'imap', 'pop', 'exchange'].some(s => sub.includes(s)) ? 'low'
            : 'info';

          await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
            (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
            VALUES (?, ?, 'subdomain', 'subdomain', ?, ?, ?, 'SecurityTrails')`).bind(
            comp.id, domain, fullSub, severity,
            severity === 'medium' ? 'Potentially sensitive subdomain — may expose internal infrastructure' : 'Subdomain enumeration'
          ).run();
          collected++;
        }

        log('info', `SecurityTrails: ${domain}`, { subdomains: subdomains.length, dns_records: collected });
      }

      // 3. WHOIS data
      const whoisResp = await fetch(`https://api.securitytrails.com/v1/domain/${domain}/whois`, {
        headers: { 'APIKEY': apiKey, 'Accept': 'application/json' },
        signal: AbortSignal.timeout(10000),
      });

      if (whoisResp.ok) {
        const whois = await whoisResp.json() as {
          result?: {
            registrar?: string;
            created_date?: string;
            expires_date?: string;
            contacts?: {
              registrant?: Array<{ organization?: string; email?: string; country?: string }>;
            };
          };
        };

        const w = whois.result;
        if (w) {
          if (w.registrar) {
            await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
              (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
              VALUES (?, ?, 'whois', 'registrar', ?, 'info', ?, 'SecurityTrails')`).bind(
              comp.id, domain, w.registrar,
              `Created: ${w.created_date || 'N/A'} | Expires: ${w.expires_date || 'N/A'}`
            ).run();
            collected++;
          }

          const registrant = w.contacts?.registrant?.[0];
          if (registrant?.organization) {
            await env.DB.prepare(`INSERT OR IGNORE INTO competitor_osint
              (competitor_id, domain, scan_type, finding_type, finding_value, severity, details, source_tool)
              VALUES (?, ?, 'whois', 'registrant_org', ?, 'info', ?, 'SecurityTrails')`).bind(
              comp.id, domain, registrant.organization, `Country: ${registrant.country || 'N/A'}`
            ).run();
            collected++;
          }
        }
      }

      // Cache for 7 days
      await env.CACHE.put(cacheKey, JSON.stringify({ scanned: true, date: new Date().toISOString() }), { expirationTtl: 604800 });

    } catch (err) {
      errors.push(`SecurityTrails ${comp.name}: ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'securitytrails' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── USPTO PATENT COLLECTOR ─────────────────────────────────────────────────

const PATENT_SEARCH_TERMS = [
  'oilfield chemical treatment',
  'scale inhibitor composition',
  'corrosion inhibitor oilfield',
  'biocide water treatment oil',
  'demulsifier composition petroleum',
  'H2S scavenger oilfield',
  'friction reducer hydraulic fracturing',
  'paraffin inhibitor well',
  'produced water treatment',
  'enhanced oil recovery chemical',
];

async function collectPatents(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('uspto', 'patents', 'running')`).run();

  for (const searchTerm of PATENT_SEARCH_TERMS) {
    try {
      // Check cache
      const cacheKey = `patent:${searchTerm.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      // USPTO PatFT search (scrape the search results page)
      const searchUrl = `https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p=1&u=%2Fnetahtml%2FPTO%2Fsearch-bool.html&r=0&f=S&l=50&TERM1=${encodeURIComponent(searchTerm)}&FIELD1=ABTX&co1=AND&TERM2=&FIELD2=&d=PTXT`;
      const resp = await fetch(searchUrl, {
        headers: { 'User-Agent': UA, 'Accept': 'text/html' },
        signal: AbortSignal.timeout(15000),
      });

      if (!resp.ok) {
        errors.push(`USPTO PatFT "${searchTerm}": HTTP ${resp.status}`);
        continue;
      }

      const html = await resp.text();
      // Extract patent numbers and titles from HTML search results
      const patentEntries: Array<{ patentNumber: string; title: string }> = [];
      const patRegex = /href="\/netacgi\/nph-Parser[^"]*?\/([0-9,]+)"[^>]*>([0-9,]+)<\/a>\s*\n?\s*([^<\n]+)/gi;
      let patMatch;
      while ((patMatch = patRegex.exec(html)) !== null) {
        patentEntries.push({
          patentNumber: patMatch[2].replace(/,/g, ''),
          title: patMatch[3].trim(),
        });
      }

      // Also try simpler pattern
      if (patentEntries.length === 0) {
        const simpleRegex = /(\d{7,10})\s*[-–]\s*([^<\n]{10,200})/g;
        let simMatch;
        while ((simMatch = simpleRegex.exec(html)) !== null) {
          patentEntries.push({
            patentNumber: simMatch[1],
            title: simMatch[2].trim(),
          });
        }
      }

      if (patentEntries.length === 0) continue;

      for (const patent of patentEntries.slice(0, 20)) {
        const assignee = 'Unknown';

        // Check if assignee matches a competitor
        let competitorId: number | null = null;
        for (const comp of COMPETITORS) {
          if (assignee.toLowerCase().includes(comp.name.toLowerCase()) ||
              comp.name.toLowerCase().includes(assignee.toLowerCase().split(' ')[0])) {
            const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
            competitorId = row?.id || null;
            break;
          }
        }

        // Extract chemical components from title
        const chemComponents: string[] = [];
        const chemPatterns = [
          /\b(glutaraldehyde|THPS|acrolein|biocide|surfactant|demulsifier|inhibitor|chelat|polyacrylamide|guar|methanol|glycol|HCl|citric acid|EDTA|triazine|phosphonate)\b/gi,
        ];
        for (const re of chemPatterns) {
          const matches = patent.title?.match(re) || [];
          chemComponents.push(...matches.map(m => m.toLowerCase()));
        }

        // Determine relevance
        const relevance = chemComponents.length > 1 ? 'high'
          : chemComponents.length > 0 ? 'medium'
          : 'low';

        await env.DB.prepare(`INSERT OR IGNORE INTO patents
          (patent_number, title, assignee, filing_date, abstract, key_claims, chemical_components, relevance, source_url)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(
          patent.patentNumber, patent.title, assignee,
          '', '',
          `Search: ${searchTerm}`,
          chemComponents.length > 0 ? [...new Set(chemComponents)].join(', ') : null,
          relevance,
          `https://patents.google.com/patent/US${patent.patentNumber}`
        ).run();
        collected++;
      }

      // Cache for 3 days
      await env.CACHE.put(cacheKey, JSON.stringify({ count: data.patents.length }), { expirationTtl: 259200 });

      log('info', `USPTO patents collected for: ${searchTerm}`, { count: data.patents?.length || 0 });

    } catch (err) {
      errors.push(`USPTO "${searchTerm}": ${String(err)}`);
    }
  }

  // Also search by competitor assignee name
  for (const comp of COMPETITORS.filter(c => c.priority === 'high')) {
    try {
      const cacheKey = `patent_assignee:${comp.name.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      const assigneeSearchUrl = `https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p=1&u=%2Fnetahtml%2FPTO%2Fsearch-bool.html&r=0&f=S&l=50&TERM1=${encodeURIComponent(comp.name)}&FIELD1=ASNM&co1=AND&TERM2=chemical&FIELD2=ABTX&d=PTXT`;

      const resp = await fetch(assigneeSearchUrl, {
        headers: { 'User-Agent': UA, 'Accept': 'text/html' },
        signal: AbortSignal.timeout(15000),
      });

      if (!resp.ok) continue;

      const html = await resp.text();
      const assigneeEntries: Array<{ patentNumber: string; title: string }> = [];
      const patRegex2 = /(\d{7,10})\s*[-–]\s*([^<\n]{10,200})/g;
      let m2;
      while ((m2 = patRegex2.exec(html)) !== null) {
        assigneeEntries.push({ patentNumber: m2[1], title: m2[2].trim() });
      }

      for (const entry of assigneeEntries.slice(0, 20)) {
        await env.DB.prepare(`INSERT OR IGNORE INTO patents
          (patent_number, title, assignee, filing_date, abstract, relevance, source_url)
          VALUES (?, ?, ?, ?, ?, 'high', ?)`).bind(
          entry.patentNumber, entry.title, comp.name,
          '', '',
          `https://patents.google.com/patent/US${entry.patentNumber}`
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, 'done', { expirationTtl: 259200 });

    } catch (err) {
      errors.push(`USPTO assignee ${comp.name}: ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'uspto' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── NEWSAPI COLLECTOR (if key available) ────────────────────────────────────

async function collectNewsAPI(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  const apiKey = env.NEWSAPI_KEY;
  if (!apiKey) {
    return { collected: 0, errors: ['NEWSAPI_KEY not configured — skipping'] };
  }

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('newsapi', 'news', 'running')`).run();

  const queries = [
    'Permian Basin oilfield chemicals',
    'oilfield water treatment Texas',
    'oilfield chemical company acquisition',
  ];

  for (const query of queries) {
    try {
      const cacheKey = `newsapi:${query.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      const url = `https://newsapi.org/v2/everything?q=${encodeURIComponent(query)}&sortBy=publishedAt&pageSize=20&language=en&apiKey=${apiKey}`;
      const resp = await fetch(url, {
        headers: { 'User-Agent': UA },
        signal: AbortSignal.timeout(10000),
      });

      if (!resp.ok) {
        errors.push(`NewsAPI "${query}": HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as {
        articles: Array<{
          title: string;
          description: string;
          url: string;
          publishedAt: string;
          source: { name: string };
        }>;
      };

      for (const article of (data.articles || [])) {
        // Match to competitor
        let competitorId: number | null = null;
        for (const comp of COMPETITORS) {
          if ((article.title + ' ' + article.description).toLowerCase().includes(comp.name.toLowerCase())) {
            const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
            competitorId = row?.id || null;
            break;
          }
        }

        const sentiment = detectNewsSentiment(article.title);

        await env.DB.prepare(`INSERT OR IGNORE INTO news_intel
          (competitor_id, headline, source_name, published_at, url, snippet, sentiment, relevance)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).bind(
          competitorId, article.title, article.source?.name || 'NewsAPI',
          article.publishedAt, article.url, article.description?.slice(0, 500) || '',
          sentiment, competitorId ? 0.8 : 0.5
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, 'done', { expirationTtl: 43200 }); // 12 hours

    } catch (err) {
      errors.push(`NewsAPI "${query}": ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'newsapi' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── USASPENDING.GOV PRICING COLLECTOR ───────────────────────────────────────
// Federal contract awards for oilfield chemicals — actual prices paid by government

const USASPENDING_NAICS = [
  '325998', // All Other Miscellaneous Chemical Product and Preparation Manufacturing
  '325199', // All Other Basic Organic Chemical Manufacturing
  '325180', // Other Basic Inorganic Chemical Manufacturing
  '325611', // Soap and Other Detergent Manufacturing (includes industrial surfactants)
  '324199', // All Other Petroleum and Coal Products Manufacturing
  '213112', // Support Activities for Oil and Gas Operations
];

const USASPENDING_KEYWORDS = [
  'oilfield chemicals',
  'production chemicals',
  'water treatment chemicals oil',
  'corrosion inhibitor oilfield',
  'scale inhibitor oil gas',
  'biocide water treatment',
  'demulsifier oil production',
  'H2S scavenger',
  'drilling fluid chemicals',
  'completion chemicals',
  'fracturing chemicals',
  'well stimulation chemicals',
  'methanol oilfield',
  'glycol dehydration',
];

async function collectUSASpending(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('usaspending', 'pricing', 'running')`).run();

  // 1. Search by NAICS codes for chemical manufacturers
  for (const naics of USASPENDING_NAICS.slice(0, 3)) {
    try {
      const cacheKey = `usaspend:naics:${naics}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      // USASpending Award Search API — free, no auth
      const resp = await fetch('https://api.usaspending.gov/api/v2/search/spending_by_award/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'User-Agent': UA },
        body: JSON.stringify({
          filters: {
            naics_codes: [naics],
            time_period: [{ start_date: '2022-01-01', end_date: '2026-12-31' }],
            award_type_codes: ['A', 'B', 'C', 'D'], // Contracts
          },
          fields: [
            'Award ID', 'Recipient Name', 'Description',
            'Award Amount', 'Total Obligation',
            'Start Date', 'End Date', 'Awarding Agency',
            'Awarding Sub Agency', 'Contract Award Type',
            'generated_internal_id',
          ],
          limit: 50,
          page: 1,
          sort: 'Award Amount',
          order: 'desc',
        }),
        signal: AbortSignal.timeout(20000),
      });

      if (!resp.ok) {
        errors.push(`USASpending NAICS ${naics}: HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as {
        results: Array<{
          'Award ID': string;
          'Recipient Name': string;
          'Description': string;
          'Award Amount': number;
          'Total Obligation': number;
          'Start Date': string;
          'End Date': string;
          'Awarding Agency': string;
          'Contract Award Type': string;
          generated_internal_id: string;
        }>;
        page_metadata: { total: number };
      };

      for (const award of (data.results || [])) {
        const desc = (award['Description'] || '').toLowerCase();
        // Filter for oilfield/chemical-related awards
        const isRelevant = ['chemical', 'inhibitor', 'biocide', 'treatment', 'oilfield', 'petroleum',
          'drilling', 'well service', 'production chem', 'water treatment', 'corrosion', 'scale',
          'methanol', 'glycol', 'solvent', 'acid', 'surfactant'].some(kw => desc.includes(kw));

        if (!isRelevant && !['325998', '325199', '325180'].includes(naics)) continue;

        // Match vendor to competitor
        let competitorId: number | null = null;
        const vendorName = award['Recipient Name'] || '';
        for (const comp of COMPETITORS) {
          if (vendorName.toLowerCase().includes(comp.name.toLowerCase()) ||
              comp.name.toLowerCase().includes(vendorName.toLowerCase().split(' ')[0])) {
            const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
            competitorId = row?.id || null;
            break;
          }
        }

        await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
          (competitor_id, product_name, product_category, price, price_unit, source, source_url,
           contract_number, buyer, vendor, award_date, confidence, notes)
          VALUES (?, ?, ?, ?, 'USD contract value', 'USASpending.gov', ?, ?, ?, ?, ?, ?, ?)`).bind(
          competitorId,
          award['Description']?.slice(0, 200) || 'Chemical supply contract',
          `NAICS ${naics}`,
          award['Award Amount'] || award['Total Obligation'] || 0,
          `https://www.usaspending.gov/award/${award.generated_internal_id || award['Award ID']}`,
          award['Award ID'] || '',
          award['Awarding Agency'] || '',
          vendorName,
          award['Start Date'] || '',
          0.9,
          `Period: ${award['Start Date'] || '?'} to ${award['End Date'] || '?'} | Type: ${award['Contract Award Type'] || 'N/A'}`
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, JSON.stringify({ count: data.results?.length || 0 }), { expirationTtl: 86400 });
      log('info', `USASpending NAICS ${naics}: ${data.results?.length || 0} awards`, { total: data.page_metadata?.total });

    } catch (err) {
      errors.push(`USASpending NAICS ${naics}: ${String(err)}`);
    }
  }

  // 2. Keyword searches for oilfield chemical contracts
  for (const keyword of USASPENDING_KEYWORDS.slice(0, 6)) {
    try {
      const cacheKey = `usaspend:kw:${keyword.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      const resp = await fetch('https://api.usaspending.gov/api/v2/search/spending_by_award/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'User-Agent': UA },
        body: JSON.stringify({
          filters: {
            keywords: [keyword],
            time_period: [{ start_date: '2023-01-01', end_date: '2026-12-31' }],
            award_type_codes: ['A', 'B', 'C', 'D'],
          },
          fields: [
            'Award ID', 'Recipient Name', 'Description',
            'Award Amount', 'Total Obligation',
            'Start Date', 'End Date', 'Awarding Agency',
            'generated_internal_id',
          ],
          limit: 25,
          page: 1,
          sort: 'Award Amount',
          order: 'desc',
        }),
        signal: AbortSignal.timeout(20000),
      });

      if (!resp.ok) {
        errors.push(`USASpending "${keyword}": HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as { results: Array<any>; page_metadata: { total: number } };

      for (const award of (data.results || [])) {
        let competitorId: number | null = null;
        const vendorName = award['Recipient Name'] || '';
        for (const comp of COMPETITORS) {
          if (vendorName.toLowerCase().includes(comp.name.toLowerCase())) {
            const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
            competitorId = row?.id || null;
            break;
          }
        }

        await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
          (competitor_id, product_name, product_category, price, price_unit, source, source_url,
           contract_number, buyer, vendor, award_date, confidence, notes)
          VALUES (?, ?, 'oilfield_chemicals', ?, 'USD contract value', 'USASpending.gov', ?, ?, ?, ?, ?, 0.85, ?)`).bind(
          competitorId,
          award['Description']?.slice(0, 200) || keyword,
          award['Award Amount'] || award['Total Obligation'] || 0,
          `https://www.usaspending.gov/award/${award.generated_internal_id || award['Award ID']}`,
          award['Award ID'] || '',
          award['Awarding Agency'] || '',
          vendorName,
          award['Start Date'] || '',
          `Keyword: ${keyword} | Period: ${award['Start Date'] || '?'} to ${award['End Date'] || '?'}`
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, JSON.stringify({ count: data.results?.length || 0 }), { expirationTtl: 86400 });

    } catch (err) {
      errors.push(`USASpending "${keyword}": ${String(err)}`);
    }
  }

  // 3. Search specifically for our tracked competitors as vendors
  for (const comp of COMPETITORS.filter(c => c.priority === 'high')) {
    try {
      const cacheKey = `usaspend:vendor:${comp.name.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      const resp = await fetch('https://api.usaspending.gov/api/v2/search/spending_by_award/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'User-Agent': UA },
        body: JSON.stringify({
          filters: {
            recipient_search_text: [comp.name],
            time_period: [{ start_date: '2022-01-01', end_date: '2026-12-31' }],
            award_type_codes: ['A', 'B', 'C', 'D'],
          },
          fields: [
            'Award ID', 'Recipient Name', 'Description',
            'Award Amount', 'Total Obligation',
            'Start Date', 'End Date', 'Awarding Agency',
            'generated_internal_id',
          ],
          limit: 50,
          page: 1,
          sort: 'Award Amount',
          order: 'desc',
        }),
        signal: AbortSignal.timeout(20000),
      });

      if (!resp.ok) continue;

      const data = await resp.json() as { results: Array<any> };
      const compRow = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();

      for (const award of (data.results || [])) {
        await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
          (competitor_id, product_name, product_category, price, price_unit, source, source_url,
           contract_number, buyer, vendor, award_date, confidence, notes)
          VALUES (?, ?, 'competitor_contract', ?, 'USD contract value', 'USASpending.gov', ?, ?, ?, ?, ?, 0.95, ?)`).bind(
          compRow?.id || null,
          award['Description']?.slice(0, 200) || `${comp.name} contract`,
          award['Award Amount'] || award['Total Obligation'] || 0,
          `https://www.usaspending.gov/award/${award.generated_internal_id || award['Award ID']}`,
          award['Award ID'] || '',
          award['Awarding Agency'] || '',
          award['Recipient Name'] || comp.name,
          award['Start Date'] || '',
          `Direct competitor search: ${comp.name}`
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, JSON.stringify({ count: data.results?.length || 0 }), { expirationTtl: 86400 });

    } catch (err) {
      errors.push(`USASpending vendor ${comp.name}: ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'usaspending' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── SAM.GOV CONTRACT OPPORTUNITIES COLLECTOR ────────────────────────────────

async function collectSAMGov(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('sam_gov', 'pricing', 'running')`).run();

  // SAM.gov Opportunities API — free, requires API key
  // For now, search via the public API (no key needed for basic search)
  const searchTerms = [
    'oilfield chemical',
    'production chemicals oil gas',
    'water treatment chemicals petroleum',
    'well service chemicals',
    'corrosion inhibitor petroleum',
  ];

  for (const term of searchTerms) {
    try {
      const cacheKey = `sam:${term.replace(/\s+/g, '_')}`;
      const cached = await env.CACHE.get(cacheKey);
      if (cached) continue;

      // SAM.gov public search — scrape the search results
      const searchUrl = `https://sam.gov/api/prod/sgs/v1/search/?index=opp&q=${encodeURIComponent(term)}&page=0&sort=-modifiedDate&size=25&mode=search&is_active=true`;
      const resp = await fetch(searchUrl, {
        headers: { 'User-Agent': UA, 'Accept': 'application/json' },
        signal: AbortSignal.timeout(15000),
      });

      if (!resp.ok) {
        errors.push(`SAM.gov "${term}": HTTP ${resp.status}`);
        continue;
      }

      const data = await resp.json() as {
        _embedded?: {
          results?: Array<{
            _id: string;
            title: string;
            description: string;
            organizationHierarchy?: Array<{ name: string }>;
            modifiedDate: string;
            postedDate: string;
            type: string;
            naicsCode?: string;
            classificationCode?: string;
            award?: {
              amount?: number;
              awardee?: { name: string };
              date?: string;
            };
          }>;
        };
        page?: { totalElements: number };
      };

      const results = data._embedded?.results || [];

      for (const opp of results) {
        const desc = (opp.description || '').toLowerCase();
        const isChemical = ['chemical', 'inhibitor', 'biocide', 'treatment', 'solvent', 'acid', 'surfactant',
          'methanol', 'glycol', 'drilling fluid', 'completion fluid'].some(kw => desc.includes(kw) || (opp.title || '').toLowerCase().includes(kw));

        if (!isChemical) continue;

        const amount = opp.award?.amount || 0;
        const vendor = opp.award?.awardee?.name || '';
        const buyer = opp.organizationHierarchy?.map(o => o.name).join(' > ') || '';

        // Match vendor to competitor
        let competitorId: number | null = null;
        if (vendor) {
          for (const comp of COMPETITORS) {
            if (vendor.toLowerCase().includes(comp.name.toLowerCase())) {
              const row = await env.DB.prepare('SELECT id FROM competitors WHERE name = ?').bind(comp.name).first<{ id: number }>();
              competitorId = row?.id || null;
              break;
            }
          }
        }

        await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
          (competitor_id, product_name, product_category, price, price_unit, source, source_url,
           contract_number, buyer, vendor, award_date, confidence, notes)
          VALUES (?, ?, 'government_contract', ?, 'USD', 'SAM.gov', ?, ?, ?, ?, ?, ?, ?)`).bind(
          competitorId,
          opp.title?.slice(0, 200) || term,
          amount,
          `https://sam.gov/opp/${opp._id}/view`,
          opp._id || '',
          buyer,
          vendor,
          opp.award?.date || opp.postedDate || '',
          amount > 0 ? 0.9 : 0.5,
          `Type: ${opp.type || 'N/A'} | NAICS: ${opp.naicsCode || 'N/A'} | Posted: ${opp.postedDate || 'N/A'}`
        ).run();
        collected++;
      }

      await env.CACHE.put(cacheKey, JSON.stringify({ count: results.length }), { expirationTtl: 86400 });

    } catch (err) {
      errors.push(`SAM.gov "${term}": ${String(err)}`);
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'sam_gov' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── CHEMICAL COMMODITY PRICING COLLECTOR ────────────────────────────────────
// Scrape bulk chemical distributors who DO publish pricing

const DISTRIBUTOR_TARGETS = [
  {
    name: 'ChemWorld',
    baseUrl: 'https://www.chemworld.com',
    searchPaths: [
      '/water-treatment-chemicals.html',
      '/industrial-chemicals.html',
      '/corrosion-inhibitors.html',
      '/biocides-algaecides.html',
      '/scale-inhibitors.html',
    ],
  },
  {
    name: 'Brenntag',
    baseUrl: 'https://www.brenntag.com',
    searchPaths: [
      '/en-us/products/oil-and-gas/',
    ],
  },
];

async function collectDistributorPricing(env: Env): Promise<{ collected: number; errors: string[] }> {
  const startTime = Date.now();
  const errors: string[] = [];
  let collected = 0;

  await env.DB.prepare(`INSERT INTO intel_collection_log (source, collection_type, status) VALUES ('distributors', 'pricing', 'running')`).run();

  for (const dist of DISTRIBUTOR_TARGETS) {
    for (const searchPath of dist.searchPaths) {
      try {
        const cacheKey = `dist:${dist.name}:${searchPath}`;
        const cached = await env.CACHE.get(cacheKey);
        if (cached) continue;

        const url = dist.baseUrl + searchPath;
        const resp = await fetch(url, {
          headers: { 'User-Agent': UA, 'Accept': 'text/html' },
          signal: AbortSignal.timeout(15000),
        });

        if (!resp.ok) {
          errors.push(`${dist.name} ${searchPath}: HTTP ${resp.status}`);
          continue;
        }

        const html = await resp.text();
        const text = extractText(html);

        // Extract pricing patterns from distributor pages
        const pricePatterns = [
          // "$XX.XX / gallon" style
          /([A-Za-z][A-Za-z\s-]{3,50})\s*[-–—]\s*\$\s*([\d,]+(?:\.\d{2})?)\s*(?:\/|per)\s*(gallon|gal|barrel|bbl|drum|tote|lb|kg|liter|ton|pail|case|each|unit)/gi,
          // "Product Name ... $XX.XX"
          /([A-Za-z][A-Za-z\s-]{3,50})\s+\$\s*([\d,]+(?:\.\d{2})?)/gi,
          // Price range: "$XX - $YY per unit"
          /([A-Za-z][A-Za-z\s-]{3,50})\s*\$\s*([\d,]+(?:\.\d{2})?)\s*[-–to]+\s*\$\s*([\d,]+(?:\.\d{2})?)\s*(?:\/|per)\s*(gallon|gal|barrel|drum|lb|kg|liter|ton)/gi,
          // "Starting at $XX.XX"
          /([A-Za-z][A-Za-z\s-]{3,50})\s*(?:starting at|from|as low as)\s*\$\s*([\d,]+(?:\.\d{2})?)/gi,
        ];

        for (const re of pricePatterns) {
          let match;
          while ((match = re.exec(text)) !== null) {
            const productName = match[1].trim();
            const price = parseFloat(match[2].replace(/,/g, ''));
            const unit = match[3] || 'each';

            if (price > 0 && price < 100000 && productName.length > 3) {
              // Categorize the product
              const lower = productName.toLowerCase();
              const category = lower.includes('inhibitor') ? 'inhibitor'
                : lower.includes('biocide') || lower.includes('algaecide') ? 'biocide'
                : lower.includes('acid') ? 'acid'
                : lower.includes('solvent') || lower.includes('methanol') || lower.includes('glycol') ? 'solvent'
                : lower.includes('surfactant') ? 'surfactant'
                : lower.includes('breaker') || lower.includes('gel') ? 'fracturing'
                : 'general';

              await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
                (product_name, product_category, price, price_unit, source, source_url, vendor, confidence, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0.8, ?)`).bind(
                productName, category, price, `USD/${unit}`, `${dist.name} distributor`,
                url, dist.name, `Retail/wholesale pricing from ${dist.name}`
              ).run();
              collected++;
            }
          }
        }

        // Also look for structured product data (JSON-LD, data attributes)
        const jsonLdMatch = html.match(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi);
        if (jsonLdMatch) {
          for (const script of jsonLdMatch) {
            try {
              const jsonStr = script.replace(/<\/?script[^>]*>/gi, '');
              const jsonData = JSON.parse(jsonStr) as any;
              if (jsonData['@type'] === 'Product' || jsonData['@type'] === 'ItemList') {
                const products = jsonData.itemListElement || [jsonData];
                for (const prod of products) {
                  const offer = prod.offers || prod.offer;
                  if (offer?.price) {
                    await env.DB.prepare(`INSERT OR IGNORE INTO pricing_data
                      (product_name, product_category, price, price_unit, source, source_url, vendor, confidence, notes)
                      VALUES (?, 'structured_data', ?, ?, ?, ?, ?, 0.9, 'JSON-LD structured data')`).bind(
                      prod.name?.slice(0, 200) || 'Unknown product',
                      parseFloat(offer.price), offer.priceCurrency || 'USD',
                      `${dist.name} distributor`, url, dist.name
                    ).run();
                    collected++;
                  }
                }
              }
            } catch { /* invalid JSON-LD, skip */ }
          }
        }

        await env.CACHE.put(cacheKey, 'done', { expirationTtl: 86400 * 3 });

      } catch (err) {
        errors.push(`${dist.name} ${searchPath}: ${String(err)}`);
      }
    }
  }

  const duration = Date.now() - startTime;
  await env.DB.prepare(`UPDATE intel_collection_log SET records_collected = ?, errors = ?, duration_ms = ?, completed_at = datetime('now'), status = 'completed' WHERE source = 'distributors' AND status = 'running' ORDER BY id DESC LIMIT 1`).bind(
    collected, errors.length > 0 ? errors.join('; ') : null, duration
  ).run();

  return { collected, errors };
}

// ─── MASTER INTEL COLLECTION ORCHESTRATOR ────────────────────────────────────

async function runIntelCollection(env: Env, sources?: string[]): Promise<Record<string, { collected: number; errors: string[] }>> {
  const results: Record<string, { collected: number; errors: string[] }> = {};

  const allSources = sources || ['sec_edgar', 'google_news', 'pubchem', 'securitytrails', 'patents', 'newsapi', 'usaspending', 'sam_gov', 'distributors'];

  // Run collections (sequentially to stay within CPU limits)
  for (const source of allSources) {
    try {
      switch (source) {
        case 'sec_edgar':
          results.sec_edgar = await collectSECEdgar(env);
          break;
        case 'google_news':
          results.google_news = await collectGoogleNews(env);
          break;
        case 'pubchem':
          results.pubchem = await collectPubChem(env);
          break;
        case 'securitytrails':
          results.securitytrails = await collectSecurityTrails(env);
          break;
        case 'patents':
          results.patents = await collectPatents(env);
          break;
        case 'newsapi':
          results.newsapi = await collectNewsAPI(env);
          break;
        case 'usaspending':
          results.usaspending = await collectUSASpending(env);
          break;
        case 'sam_gov':
          results.sam_gov = await collectSAMGov(env);
          break;
        case 'distributors':
          results.distributors = await collectDistributorPricing(env);
          break;
      }
    } catch (err) {
      results[source] = { collected: 0, errors: [String(err)] };
    }
  }

  // Ingest summary to shared brain
  const totalCollected = Object.values(results).reduce((a, r) => a + r.collected, 0);
  const totalErrors = Object.values(results).reduce((a, r) => a + r.errors.length, 0);
  await ingestToBrain(
    `INTEL COLLECTION CYCLE: ${totalCollected} records from ${allSources.length} sources. Errors: ${totalErrors}. Sources: ${allSources.join(', ')}`,
    ['intel_collection', 'permian_pulse', 'automated'], env
  );

  return results;
}

// ─── CRON HANDLER ──────────────────────────────────────────────────────────────

async function handleCron(env: Env): Promise<void> {
  log('info', 'Cron triggered — running competitor scrape + intel collection cycle');

  // Phase 1: Website scraping (existing)
  const priorities: Array<'high' | 'medium' | 'low'> = ['high', 'medium', 'low'];
  let totalScraped = 0;

  for (const priority of priorities) {
    const targets = COMPETITORS.filter(c => c.priority === priority);
    for (const target of targets) {
      const cached = await env.CACHE.get(`scraped:${target.name}`);
      if (cached) continue;

      await scrapeCompetitor(target, env);
      await env.CACHE.put(`scraped:${target.name}`, 'true', { expirationTtl: 86400 });
      totalScraped++;
    }
  }

  // Phase 2: Reverse engineering on newly scraped
  if (totalScraped > 0) {
    await runRevEngBatch(env);
  }

  // Phase 3: Automated intel collection from external sources
  // Rotate sources — run 2-3 per cron cycle to stay within CPU limits
  const hour = new Date().getUTCHours();
  let intelSources: string[];

  if (hour === 0 || hour === 12) {
    // Full collection at midnight and noon UTC
    intelSources = ['sec_edgar', 'google_news', 'patents'];
  } else if (hour === 6) {
    // Morning: OSINT + chemicals
    intelSources = ['securitytrails', 'pubchem'];
  } else if (hour === 18) {
    // Evening: news + any missed
    intelSources = ['google_news', 'newsapi'];
  } else {
    // Default: news only (lightweight)
    intelSources = ['google_news'];
  }

  const intelResults = await runIntelCollection(env, intelSources);
  const totalIntelCollected = Object.values(intelResults).reduce((a, r) => a + r.collected, 0);

  log('info', `Cron complete — scraped ${totalScraped} competitors, collected ${totalIntelCollected} intel records`, { sources: intelSources });
}

// ─── MAIN EXPORT ───────────────────────────────────────────────────────────────

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    try {
      return await handleRequest(request, env);
    } catch (err) {
      log('error', 'Unhandled error', { error: String(err), stack: (err as Error).stack });
      return json({ error: 'Internal server error', message: String(err) }, 500);
    }
  },

  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(handleCron(env));
  },
};
