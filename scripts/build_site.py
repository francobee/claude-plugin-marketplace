#!/usr/bin/env python3
"""Render site/index.html (static, searchable catalog page) from marketplace.json + sidecars. Published via the pages workflow."""
import html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TIERS = {
    "1": ("T1", "prompt-only", "t1"),
    "2": ("T2", "read/config", "t2"),
    "3": ("T3", "code-executing", "t3"),
}

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__MARKET__ — Claude Code Plugin Marketplace</title>
<meta name="description" content="__DESC__">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0c100d; --panel:#12181420; --card:#131a15; --edge:#22302666;
  --ink:#d7e4da; --dim:#7d907f; --accent:#63e69f; --accent-ink:#0c100d;
  --t1:#63e69f; --t2:#e6c063; --t3:#f07a6a; --mono:'IBM Plex Mono',ui-monospace,monospace;
  --sans:'IBM Plex Sans',system-ui,sans-serif;
}
@media (prefers-color-scheme: light){
  :root{--bg:#f4f6f2; --card:#ffffff; --edge:#1d281f22; --ink:#1c241d; --dim:#5c6b5e;
        --accent:#0d7a43; --accent-ink:#f4f6f2; --t1:#0d7a43; --t2:#9a6d0b; --t3:#b53d2e;}
}
*{margin:0;box-sizing:border-box}
body{
  background:var(--bg); color:var(--ink); font-family:var(--sans);
  background-image:linear-gradient(var(--edge) 1px,transparent 1px),linear-gradient(90deg,var(--edge) 1px,transparent 1px);
  background-size:56px 56px; min-height:100vh;
}
main{max-width:1080px;margin:0 auto;padding:0 24px 96px}
header{padding:72px 0 40px}
.kicker{font-family:var(--mono);font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin-bottom:14px}
.kicker::before{content:"● ";animation:blink 2.4s step-end infinite}
@keyframes blink{50%{opacity:.25}}
h1{font-size:clamp(30px,5.5vw,52px);font-weight:700;letter-spacing:-.02em;line-height:1.05}
h1 .at{color:var(--accent);font-family:var(--mono);font-weight:500}
.sub{color:var(--dim);max-width:58ch;margin-top:14px;font-size:15.5px;line-height:1.55}
.gate{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px;font-family:var(--mono);font-size:11.5px}
.gate span{border:1px solid var(--edge);border-left:3px solid var(--accent);padding:5px 10px;color:var(--dim);background:var(--card)}
.bar{display:flex;gap:14px;align-items:center;margin:34px 0 22px;flex-wrap:wrap}
#q{
  flex:1;min-width:240px;background:var(--card);border:1px solid var(--edge);color:var(--ink);
  font-family:var(--mono);font-size:14px;padding:12px 16px;outline:none;
}
#q:focus{border-color:var(--accent)}
#q::placeholder{color:var(--dim)}
.count{font-family:var(--mono);font-size:12px;color:var(--dim)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:18px}
.card{
  background:var(--card);border:1px solid var(--edge);padding:22px;display:flex;flex-direction:column;gap:12px;
  animation:rise .5s cubic-bezier(.2,.8,.3,1) both;transition:transform .18s,border-color .18s;
}
.card:hover{transform:translateY(-3px);border-color:var(--accent)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}}
.card h2{font-size:18px;font-weight:600;letter-spacing:-.01em}
.card .name{font-family:var(--mono);font-size:12px;color:var(--dim)}
.badges{display:flex;gap:8px;flex-wrap:wrap;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em}
.badge{padding:3px 8px;border:1px solid currentColor}
.tier-t1{color:var(--t1)} .tier-t2{color:var(--t2)} .tier-t3{color:var(--t3)}
.badge.ver,.badge.cat{color:var(--dim)}
.desc{color:var(--dim);font-size:14px;line-height:1.5;flex:1}
.score{font-family:var(--mono);font-size:11px;color:var(--dim)}
.score b{color:var(--accent);font-weight:500}
.up a{color:var(--accent);text-decoration:none;font-family:var(--mono);font-size:12px}
.up a:hover{text-decoration:underline}
.install{display:flex;border:1px solid var(--edge);font-family:var(--mono);font-size:12px}
.install code{flex:1;padding:9px 12px;overflow-x:auto;white-space:nowrap;color:var(--ink)}
.install button{
  border:none;border-left:1px solid var(--edge);background:transparent;color:var(--accent);
  font-family:var(--mono);font-size:11px;padding:0 14px;cursor:pointer;letter-spacing:.08em
}
.install button:hover{background:var(--accent);color:var(--accent-ink)}
.empty{display:none;color:var(--dim);font-family:var(--mono);padding:48px 0;text-align:center}
footer{margin-top:64px;color:var(--dim);font-size:12.5px;font-family:var(--mono);border-top:1px solid var(--edge);padding-top:20px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
footer a{color:var(--accent);text-decoration:none}
</style>
</head>
<body>
<main>
<header>
  <div class="kicker">security-gated plugin registry</div>
  <h1>Claude Code plugins <span class="at">@__MARKET__</span></h1>
  <p class="sub">__DESC__</p>
  <div class="gate"><span>schema validated</span><span>risk-tier linted</span><span>secrets scanned</span><span>smoke tested</span><span>Claude security review</span><span>upstream watched</span></div>
</header>
<div class="bar">
  <input id="q" type="search" placeholder="filter plugins… name, tag, description" autocomplete="off">
  <div class="count"><span id="n">__COUNT__</span> / __COUNT__ plugins</div>
</div>
<div class="grid" id="grid">
__CARDS__
</div>
<p class="empty" id="empty">no plugins match — clear the filter or request one via a GitHub issue</p>
<footer>
  <span>generated __DATE__ by scripts/build_site.py — do not hand-edit</span>
  <span><a href="__REPO_URL__">repository</a> · <a href="__REPO_URL__/blob/main/CATALOG.md">markdown catalog</a></span>
</footer>
</main>
<script>
const q=document.getElementById('q'),cards=[...document.querySelectorAll('.card')],n=document.getElementById('n'),empty=document.getElementById('empty');
q.addEventListener('input',()=>{
  const t=q.value.toLowerCase();let vis=0;
  cards.forEach(c=>{const hit=c.dataset.search.includes(t);c.style.display=hit?'':'none';if(hit)vis++;});
  n.textContent=vis;empty.style.display=vis?'none':'block';
});
document.querySelectorAll('.install button').forEach(b=>b.addEventListener('click',()=>{
  navigator.clipboard.writeText(b.previousElementSibling.textContent).then(()=>{
    b.textContent='COPIED';setTimeout(()=>b.textContent='COPY',1200);
  });
}));
</script>
</body>
</html>
"""


def tier_badge(entry: dict) -> str:
    for t in entry.get("tags", []):
        m = re.match(r"^tier-([123])$", t)
        if m:
            label, desc, cls = TIERS[m.group(1)]
            return f'<span class="badge tier-{cls}">{label} {desc}</span>'
    return '<span class="badge cat">untiered</span>'


def scorecard_line(name: str) -> str:
    sidecar = REPO / "plugins" / name / ".scorecard.json"
    if not sidecar.is_file():
        return ""
    sc = json.loads(sidecar.read_text())
    mark = {True: "<b>✔</b>", False: "✗", None: "·"}
    bits = [f"scan {mark.get(sc.get('risk_lint'), '·')}", f"smoke {mark.get(sc.get('smoke_test'), '·')}"]
    if sc.get("llm_review") is not None:
        bits.append(f"LLM {mark[bool(sc['llm_review'])]}")
    if sc.get("upstream_fresh") is not None:
        bits.append("upstream <b>fresh</b>" if sc["upstream_fresh"] else "upstream drifted")
    when = f" — {sc['date']}" if sc.get("date") else ""
    return f'<div class="score">{" / ".join(bits)}{when}</div>'


def permissions_line(name: str) -> str:
    sidecar = REPO / "plugins" / name / ".permissions.json"
    if not sidecar.is_file():
        return ""
    p = json.loads(sidecar.read_text())
    bad = sum(1 for e in p.get("network_endpoints", []) if not e.get("allowlisted"))
    bits = [f"MCP {len(p.get('mcp_servers', []))}", f"hooks {len(p.get('hook_commands', []))}",
            f"shell {len(p.get('shell_commands', []))}",
            f"endpoints {len(p.get('network_endpoints', []))}" + (f" (<b>{bad} off-allowlist!</b>)" if bad else "")]
    return f'<div class="score">touches: {" · ".join(bits)}</div>'


def card(entry: dict, market: str, idx: int) -> str:
    name = entry["name"]
    e = lambda k, d="": html.escape(str(entry.get(k, d)))
    search = html.escape(" ".join([name, entry.get("displayName", ""), entry.get("description", ""),
                                   entry.get("category", ""), *entry.get("tags", []), *entry.get("keywords", [])]).lower(), quote=True)
    upstream = ""
    sidecar = REPO / "plugins" / name / ".upstream.json"
    if sidecar.is_file():
        repo = json.loads(sidecar.read_text()).get("repo", "")
        if repo:
            upstream = f'<div class="up">vendored from <a href="https://github.com/{html.escape(repo)}">{html.escape(repo)}</a></div>'
    return f"""<article class="card" style="animation-delay:{idx * 60}ms" data-search="{search}">
  <div><h2>{e('displayName') or html.escape(name)}</h2><div class="name">{html.escape(name)}</div></div>
  <div class="badges">{tier_badge(entry)}<span class="badge ver">v{e('version', '?')}</span><span class="badge cat">{e('category', '—')}</span></div>
  <p class="desc">{e('description')}</p>
  {scorecard_line(name)}{permissions_line(name)}{upstream}
  <div class="install"><code>/plugin install {html.escape(name)}@{html.escape(market)}</code><button type="button">COPY</button></div>
</article>"""


def _cfg(dotted: str) -> str:
    """Read a value from marketplace.config.yml, fail-soft to empty string."""
    try:
        import config_loader
        return str(config_loader.get(config_loader.load(REPO / "marketplace.config.yml"), dotted, "") or "")
    except Exception:
        return ""


def main() -> int:
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    market = _cfg("site.title") or mp.get("name", "internal")
    plugins = sorted(mp.get("plugins", []), key=lambda x: x["name"])
    slug = os.environ.get("GITHUB_REPOSITORY") or _cfg("company.github_repo") or "francobee/claude-plugin-marketplace"
    repo_url = f"https://github.com/{slug}"
    page = (TEMPLATE
            .replace("__MARKET__", html.escape(market))
            .replace("__DESC__", html.escape(mp.get("description", "")))
            .replace("__COUNT__", str(len(plugins)))
            .replace("__CARDS__", "\n".join(card(e, market, i) for i, e in enumerate(plugins)))
            .replace("__DATE__", date.today().isoformat())
            .replace("__REPO_URL__", repo_url))
    out = REPO / "site" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(f"site: wrote {out.relative_to(REPO)} ({len(plugins)} plugins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
