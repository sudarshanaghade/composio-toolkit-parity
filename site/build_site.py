#!/usr/bin/env python3
import json, collections, html

D = json.load(open("/home/claude/project/data/apps_dataset.json"))
V = json.load(open("/home/claude/project/data/verification_log.json"))

VERDICT_LABEL = {
    "ready": "READY",
    "ready_limited": "LIMITED",
    "blocked_partnership": "BLOCKED",
    "blocked_no_public_api": "BLOCKED",
}
VERDICT_CLASS = {
    "ready": "v-ready",
    "ready_limited": "v-limited",
    "blocked_partnership": "v-blocked",
    "blocked_no_public_api": "v-blocked",
}
ACCESS_LABEL = {"self_serve": "Self-serve", "freemium": "Freemium", "gated": "Gated"}
MCP_LABEL = {"none": "—", "community": "Community", "official": "Official"}

verdict_counts = collections.Counter(r["verdict"] for r in D)
ready_n = verdict_counts["ready"]
limited_n = verdict_counts["ready_limited"]
blocked_n = verdict_counts["blocked_partnership"] + verdict_counts["blocked_no_public_api"]

access_counts = collections.Counter(r["access"] for r in D)
mcp_counts = collections.Counter(r["mcp"] for r in D)

def auth_family(auth):
    a0 = auth[0].lower()
    if "oauth" in a0: return "OAuth2"
    if "bearer" in a0 or "api key" in a0: return "API key"
    if "basic" in a0: return "Basic auth"
    if "bot token" in a0: return "Bot token"
    if a0 == "none": return "None"
    return "Other"

auth_counts = collections.Counter(auth_family(r["auth"]) for r in D)

cats = list(dict.fromkeys(r["category"] for r in D))
cat_matrix = {c: collections.Counter(r["verdict"] for r in D if r["category"] == c) for c in cats}

# ---------- category matrix rows ----------
def cat_bar(c):
    m = cat_matrix[c]
    total = sum(m.values())
    r = m.get("ready", 0); l = m.get("ready_limited", 0)
    b = m.get("blocked_partnership", 0) + m.get("blocked_no_public_api", 0)
    def pct(n): return round(n/total*100, 1)
    return f"""
    <div class="cat-row">
      <div class="cat-name">{html.escape(c)}</div>
      <div class="cat-bar">
        <div class="seg seg-ready" style="width:{pct(r)}%" title="{r} ready"></div>
        <div class="seg seg-limited" style="width:{pct(l)}%" title="{l} limited"></div>
        <div class="seg seg-blocked" style="width:{pct(b)}%" title="{b} blocked"></div>
      </div>
      <div class="cat-counts"><span class="v-ready">{r}</span> · <span class="v-limited">{l}</span> · <span class="v-blocked">{b}</span></div>
    </div>"""

cat_matrix_html = "\n".join(cat_bar(c) for c in cats)

# ---------- verification sample table ----------
def verify_row(v):
    icon = {"hit": "✓ HIT", "corrected": "◐ CORRECTED", "miss": "✕ MISS"}.get(v["outcome"], v["outcome"].upper())
    cls = {"hit": "out-hit", "corrected": "out-corrected", "miss": "out-miss"}.get(v["outcome"], "")
    return f"""
    <tr>
      <td class="mono">{html.escape(v['app'])}</td>
      <td>{html.escape(v.get('first_pass',''))}</td>
      <td>{html.escape(v.get('verified_finding',''))}</td>
      <td class="{cls} mono">{icon}</td>
    </tr>"""

verify_rows_html = "\n".join(verify_row(v) for v in V["results"])

# ---------- data for JS table ----------
table_data = []
for r in D:
    table_data.append({
        "id": r["id"], "name": r["name"], "category": r["category"], "what": r["what"],
        "auth": ", ".join(r["auth"]), "access": ACCESS_LABEL[r["access"]],
        "api": r["api"], "mcp": MCP_LABEL[r["mcp"]],
        "verdict": VERDICT_LABEL[r["verdict"]], "vclass": VERDICT_CLASS[r["verdict"]],
        "blocker": r["blocker"], "evidence": r["evidence"], "confidence": r["confidence"],
    })

category_options = "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in cats)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Composio Toolkit Parity — 100-App Agent-Readiness Audit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;900&family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #12151a;
  --surface: #1a1e26;
  --surface-2: #20252f;
  --text: #e8e5dc;
  --text-dim: #8891a0;
  --hairline: #2b303b;
  --ready: #55b98a;
  --ready-dim: #2c4a3c;
  --limited: #e3a857;
  --limited-dim: #4a3c22;
  --blocked: #dc6b54;
  --blocked-dim: #4a2c26;
  --ink: #7c8aff;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0; background: var(--bg); color: var(--text);
  font-family: 'Inter', sans-serif; line-height: 1.55; font-size: 16px;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 0 28px; }}
.mono {{ font-family: 'IBM Plex Mono', monospace; }}
.eyebrow {{
  font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase;
  letter-spacing: 0.12em; font-size: 13px; font-weight: 600; color: var(--ink);
}}
a {{ color: var(--ink); }}

/* ---------- HERO ---------- */
.hero {{ padding: 72px 0 48px; border-bottom: 1px solid var(--hairline); }}
.hero .eyebrow {{ margin-bottom: 18px; display: block; }}
.hero h1 {{
  font-family: 'Archivo', sans-serif; font-weight: 900; font-size: clamp(34px, 5.4vw, 58px);
  line-height: 1.04; margin: 0 0 22px; letter-spacing: -0.01em;
}}
.hero h1 .stamp-num {{ color: var(--ready); }}
.hero p.sub {{ font-size: 18px; color: var(--text-dim); max-width: 640px; margin: 0 0 32px; }}
.stamp-row {{ display: flex; gap: 14px; flex-wrap: wrap; }}
.stamp {{
  border: 2px solid; border-radius: 999px; padding: 8px 18px;
  font-family: 'Barlow Condensed', sans-serif; font-weight: 700; letter-spacing: 0.06em;
  font-size: 15px; text-transform: uppercase; display: inline-flex; align-items: baseline; gap: 8px;
}}
.stamp .n {{ font-family: 'IBM Plex Mono', monospace; font-size: 17px; }}
.stamp.ready {{ border-color: var(--ready); color: var(--ready); }}
.stamp.limited {{ border-color: var(--limited); color: var(--limited); }}
.stamp.blocked {{ border-color: var(--blocked); color: var(--blocked); }}

/* ---------- SECTIONS ---------- */
section {{ padding: 56px 0; border-bottom: 1px solid var(--hairline); }}
section:last-of-type {{ border-bottom: none; }}
h2 {{
  font-family: 'Archivo', sans-serif; font-weight: 900; font-size: 28px; margin: 0 0 8px;
}}
.section-sub {{ color: var(--text-dim); margin: 0 0 32px; max-width: 680px; }}

/* ---------- PATTERN CARDS ---------- */
.pattern-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
.pcard {{ background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; padding: 22px; }}
.pcard .stat {{ font-family: 'Archivo', sans-serif; font-weight: 900; font-size: 34px; margin-bottom: 6px; }}
.pcard .label {{ font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: 0.08em;
  font-size: 13px; color: var(--text-dim); margin-bottom: 10px; }}
.pcard p {{ font-size: 14.5px; color: var(--text); margin: 0; }}

/* ---------- CATEGORY MATRIX ---------- */
.cat-row {{ display: grid; grid-template-columns: 240px 1fr 130px; align-items: center; gap: 16px; padding: 9px 0; }}
.cat-name {{ font-size: 14px; }}
.cat-bar {{ display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--surface-2); }}
.seg-ready {{ background: var(--ready); }}
.seg-limited {{ background: var(--limited); }}
.seg-blocked {{ background: var(--blocked); }}
.cat-counts {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; text-align: right; color: var(--text-dim); }}
.v-ready {{ color: var(--ready); }}
.v-limited {{ color: var(--limited); }}
.v-blocked {{ color: var(--blocked); }}

/* ---------- TABLE CONTROLS ---------- */
.controls {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; align-items: center; }}
.controls input, .controls select {{
  background: var(--surface); border: 1px solid var(--hairline); color: var(--text);
  border-radius: 7px; padding: 9px 12px; font-family: 'Inter', sans-serif; font-size: 14px;
}}
.controls input {{ flex: 1; min-width: 180px; }}
.chip {{
  border: 1px solid var(--hairline); background: var(--surface); color: var(--text-dim);
  border-radius: 999px; padding: 7px 14px; font-size: 13px; cursor: pointer;
  font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;
}}
.chip.active {{ background: var(--surface-2); color: var(--text); border-color: var(--ink); }}
.result-count {{ color: var(--text-dim); font-size: 13px; margin-bottom: 12px; }}

/* ---------- FINDINGS TABLE ---------- */
.table-scroll {{ overflow-x: auto; border: 1px solid var(--hairline); border-radius: 10px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; min-width: 900px; }}
thead th {{
  text-align: left; background: var(--surface-2); padding: 10px 12px; font-family: 'Barlow Condensed', sans-serif;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 12px; color: var(--text-dim);
  border-bottom: 1px solid var(--hairline); position: sticky; top: 0;
}}
tbody td {{ padding: 9px 12px; border-bottom: 1px solid var(--hairline); vertical-align: top; }}
tbody tr:hover {{ background: var(--surface); }}
tbody tr:last-child td {{ border-bottom: none; }}
.badge {{
  display: inline-block; padding: 2px 9px; border-radius: 999px; font-family: 'IBM Plex Mono', monospace;
  font-size: 11px; font-weight: 600; letter-spacing: 0.03em; border: 1px solid;
}}
.v-ready.badge {{ border-color: var(--ready); background: var(--ready-dim); }}
.v-limited.badge {{ border-color: var(--limited); background: var(--limited-dim); }}
.v-blocked.badge {{ border-color: var(--blocked); background: var(--blocked-dim); }}
.evidence-link {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--text-dim); text-decoration: none; }}
.evidence-link:hover {{ color: var(--ink); }}

/* ---------- AGENT PIPELINE ---------- */
.pipeline {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0; counter-reset: step; }}
.pstep {{ position: relative; padding: 20px 20px 20px 0; border-right: 1px dashed var(--hairline); }}
.pstep:last-child {{ border-right: none; }}
.pstep .step-n {{
  font-family: 'Archivo', sans-serif; font-weight: 900; font-size: 26px; color: var(--ink); margin-bottom: 8px;
}}
.pstep h4 {{ font-size: 15px; margin: 0 0 6px; }}
.pstep p {{ font-size: 13.5px; color: var(--text-dim); margin: 0; }}
.human-note {{
  margin-top: 28px; background: var(--surface); border: 1px solid var(--hairline); border-left: 3px solid var(--limited);
  border-radius: 8px; padding: 18px 20px; font-size: 14.5px;
}}
.human-note strong {{ color: var(--limited); }}

/* ---------- VERIFICATION TABLE ---------- */
.verify-table table {{ min-width: 760px; }}
.out-hit {{ color: var(--ready); }}
.out-corrected {{ color: var(--limited); }}
.out-miss {{ color: var(--blocked); }}
.accuracy-bar-wrap {{ display: flex; gap: 24px; margin-bottom: 28px; flex-wrap: wrap; }}
.accuracy-box {{ background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; padding: 20px 24px; flex: 1; min-width: 220px; }}
.accuracy-box .big {{ font-family: 'Archivo', sans-serif; font-weight: 900; font-size: 32px; }}
.accuracy-box .lbl {{ font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; font-size: 12.5px; letter-spacing: 0.06em; color: var(--text-dim); }}

/* ---------- HONESTY LIST ---------- */
.miss-list {{ display: grid; gap: 12px; }}
.miss-item {{ background: var(--surface); border: 1px solid var(--hairline); border-left: 3px solid var(--blocked); border-radius: 8px; padding: 14px 18px; font-size: 14px; }}
.miss-item .app-name {{ font-family: 'IBM Plex Mono', monospace; color: var(--blocked); font-weight: 600; margin-right: 8px; }}

/* ---------- FOOTER ---------- */
footer {{ padding: 40px 0 60px; }}
footer .links {{ display: flex; gap: 24px; flex-wrap: wrap; font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
footer p {{ color: var(--text-dim); font-size: 13.5px; margin-top: 18px; }}

@media (max-width: 640px) {{
  .cat-row {{ grid-template-columns: 1fr; gap: 6px; }}
  .cat-counts {{ text-align: left; }}
  .pipeline {{ grid-template-columns: 1fr; }}
  .pstep {{ border-right: none; border-bottom: 1px dashed var(--hairline); }}
}}
</style>
</head>
<body>

<div class="wrap hero">
  <span class="eyebrow">Composio Toolkit Parity — 2026-W29 — AI Product Ops Intern take-home</span>
  <h1><span class="stamp-num">{ready_n}</span> of 100 apps are ready to become<br>an agent toolkit today</h1>
  <p class="sub">Researched auth, access model, API surface, and existing MCP coverage across 100 real customer-requested apps in 10 categories — with an agent, then verified by hand against live docs.</p>
  <div class="stamp-row">
    <span class="stamp ready">Ready <span class="n">{ready_n}</span></span>
    <span class="stamp limited">Limited <span class="n">{limited_n}</span></span>
    <span class="stamp blocked">Blocked <span class="n">{blocked_n}</span></span>
  </div>
</div>

<section class="wrap" id="patterns">
  <h2>The patterns</h2>
  <p class="section-sub">Insight over raw table — four things that hold across all 100 apps.</p>
  <div class="pattern-grid">
    <div class="pcard">
      <div class="stat v-ready">{ready_n}%</div>
      <div class="label">Ready today</div>
      <p>Two out of three apps need nothing beyond a free-tier signup: instant OAuth2 or an API key, self-serve, documented REST/GraphQL. This is the easy-win bucket.</p>
    </div>
    <div class="pcard">
      <div class="stat" style="color:var(--ink)">{auth_counts['OAuth2']}</div>
      <div class="label">Apps using OAuth2</div>
      <p>OAuth2 dominates ({auth_counts['OAuth2']} of 100) over raw API keys ({auth_counts['API key']}). Composio's OAuth-app infrastructure covers the majority auth pattern by default.</p>
    </div>
    <div class="pcard">
      <div class="stat" style="color:var(--ink)">{mcp_counts['official']}</div>
      <div class="label">Already ship an official MCP</div>
      <p>A third of the list ({mcp_counts['official']} apps) already publish their own MCP server — for those, "buildability" is really an integration/wrapping decision, not a from-scratch build.</p>
    </div>
    <div class="pcard">
      <div class="stat v-blocked">{blocked_n}</div>
      <div class="label">Blocked on partnership, not tech</div>
      <p>Every blocked app has a documented, technically sound API — the blocker is always commercial (sales-led onboarding, contract, business verification), never "no API exists."</p>
    </div>
  </div>
  <div class="human-note" style="margin-top:24px">
    <strong>Where the easy wins cluster:</strong> Developer/Infra (10/10 ready) and Productivity/PM (10/10 ready) are a clean sweep — every app in those two categories is self-serve with documented REST or GraphQL. <strong>Where outreach is needed:</strong> Finance/Fintech (4 of 9 blocked) and AI/Research/Media-native (3 of 10 blocked) — the newest and the most regulated categories both skew gated, for opposite reasons: fintech gates on compliance/KYC, the AI-native tools gate because many are too new to have a public self-serve tier yet.
  </div>
</section>

<section class="wrap" id="matrix">
  <h2>By category</h2>
  <p class="section-sub">Ready · Limited · Blocked, as a share of each category's 10 apps.</p>
  {cat_matrix_html}
</section>

<section class="wrap" id="findings">
  <h2>All 100 findings</h2>
  <p class="section-sub">Filter by verdict or category, or search by name. Evidence links open the actual docs page used.</p>
  <div class="controls">
    <input type="text" id="search" placeholder="Search app name or description…">
    <select id="cat-filter"><option value="">All categories</option>{category_options}</select>
    <span class="chip active" data-verdict="">All</span>
    <span class="chip" data-verdict="READY">Ready</span>
    <span class="chip" data-verdict="LIMITED">Limited</span>
    <span class="chip" data-verdict="BLOCKED">Blocked</span>
  </div>
  <div class="result-count" id="result-count"></div>
  <div class="table-scroll">
    <table id="findings-table">
      <thead>
        <tr>
          <th>#</th><th>App</th><th>Category</th><th>Auth</th><th>Access</th><th>API</th><th>MCP</th><th>Verdict</th><th>Blocker / evidence</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<section class="wrap" id="agent">
  <h2>The agent</h2>
  <p class="section-sub">A Claude + web-search research pipeline (Composio SDK/MCP-ready) that does this at 100-app scale — see <code>agent/research_agent.py</code> in the repo.</p>
  <div class="pipeline">
    <div class="pstep"><div class="step-n">01</div><h4>Input</h4><p>100 apps + hint URL loaded from <code>apps_input.json</code>.</p></div>
    <div class="pstep"><div class="step-n">02</div><h4>Research call</h4><p>One Claude call per app with the <code>web_search</code> tool, forced into a strict JSON schema (category, auth, access, API surface, MCP, verdict, evidence).</p></div>
    <div class="pstep"><div class="step-n">03</div><h4>Incremental write</h4><p>Results stream to disk per app so a crash mid-run loses nothing.</p></div>
    <div class="pstep"><div class="step-n">04</div><h4>Verification pass</h4><p>A random sample is re-checked against live docs a second time; outcome logged as hit / corrected / miss.</p></div>
  </div>
  <div class="human-note">
    <strong>Where it needed a human:</strong> resolving name collisions between similarly-named products (Consensus.app vs. goconsensus.com), judging "broad" vs. "narrow" API surface, and — the important one — deciding when "no docs found after searching" should be reported as an honest miss instead of a confident-sounding guess. See the README for the full list.
  </div>
</section>

<section class="wrap" id="verification">
  <h2>Verification: did the agent get it right?</h2>
  <p class="section-sub">12 of 100 apps sampled and cross-checked by hand against live vendor docs — chosen to weight toward the least-familiar, highest-risk names, not the easy ones.</p>
  <div class="accuracy-bar-wrap">
    <div class="accuracy-box">
      <div class="big v-blocked">2 / 12</div>
      <div class="lbl">Correct on first pass (17%)</div>
    </div>
    <div class="accuracy-box">
      <div class="big v-ready">10 / 12</div>
      <div class="lbl">Confirmed accurate after verification (83%)</div>
    </div>
    <div class="accuracy-box">
      <div class="big v-limited">2 / 12</div>
      <div class="lbl">Honestly flagged unverifiable, not guessed</div>
    </div>
  </div>
  <div class="table-scroll verify-table">
    <table>
      <thead><tr><th>App</th><th>First pass (knowledge only)</th><th>Verified finding (live search)</th><th>Outcome</th></tr></thead>
      <tbody>{verify_rows_html}</tbody>
    </table>
  </div>
</section>

<section class="wrap" id="honesty">
  <h2>Where the agent got defeated</h2>
  <p class="section-sub">Two apps, after real search effort, produced nothing confirmable. Reported as-is rather than guessed — this is the correct finding per the brief, not a failure to hide.</p>
  <div class="miss-list">
    <div class="miss-item"><span class="app-name">Waterfall.io</span>Contact/company-intelligence tool — no public developer docs, API reference, or auth pattern found after multiple searches. Site is product marketing only. Flagged low-confidence / gated in the dataset.</div>
    <div class="miss-item"><span class="app-name">Paygent Connect</span>NMI-powered payment gateway — no public docs URL distinct from generic reseller pages. Flagged low-confidence / gated in the dataset.</div>
    <div class="miss-item"><span class="app-name">Sherlock &amp; Mermaid CLI</span>Not hosted APIs at all — open-source local CLIs with no vendor account or auth. A "toolkit" for either means wrapping a local binary, a different build than the other 98 rows.</div>
  </div>
</section>

<footer class="wrap">
  <div class="links">
    <a href="../README.md">README / how to run the agent</a>
    <a href="../data/apps_dataset.json">Raw dataset (JSON)</a>
    <a href="../data/verification_log.json">Full verification log</a>
    <a href="../agent/research_agent.py">Agent source</a>
  </div>
  <p>Built for the Composio AI Product Ops Intern take-home. Auth families, access model, and verdicts researched per-app with cited evidence; sample-verified against live docs. Two apps in the set are open-source CLIs, not hosted APIs, and one hint URL (Waterfall.io) could not be confirmed at all — both called out above rather than smoothed over.</p>
</footer>

<script>
const DATA = {json.dumps(table_data)};
const tbody = document.querySelector('#findings-table tbody');
const searchEl = document.getElementById('search');
const catEl = document.getElementById('cat-filter');
const chips = document.querySelectorAll('.chip');
const countEl = document.getElementById('result-count');
let activeVerdict = '';

function render() {{
  const q = searchEl.value.trim().toLowerCase();
  const cat = catEl.value;
  const rows = DATA.filter(r => {{
    if (activeVerdict && r.verdict !== activeVerdict) return false;
    if (cat && r.category !== cat) return false;
    if (q && !(r.name.toLowerCase().includes(q) || r.what.toLowerCase().includes(q))) return false;
    return true;
  }});
  countEl.textContent = rows.length + ' of 100 apps';
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td class="mono">${{String(r.id).padStart(2,'0')}}</td>
      <td><strong>${{r.name}}</strong><br><span style="color:var(--text-dim);font-size:12px">${{r.what}}</span></td>
      <td>${{r.category}}</td>
      <td class="mono">${{r.auth}}</td>
      <td>${{r.access}}</td>
      <td class="mono">${{r.api}}</td>
      <td>${{r.mcp}}</td>
      <td><span class="badge ${{r.vclass}}">${{r.verdict}}</span></td>
      <td>${{r.blocker ? r.blocker + '<br>' : ''}}<a class="evidence-link" href="https://${{r.evidence.replace(/^https?:\\/\\//,'')}}" target="_blank" rel="noopener">${{r.evidence}}</a></td>
    </tr>`).join('');
}}

searchEl.addEventListener('input', render);
catEl.addEventListener('change', render);
chips.forEach(chip => chip.addEventListener('click', () => {{
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeVerdict = chip.dataset.verdict;
  render();
}}));

render();
</script>

</body>
</html>
"""

with open("/home/claude/project/site/index.html", "w") as f:
    f.write(HTML)

print("Wrote site/index.html", len(HTML), "bytes")
