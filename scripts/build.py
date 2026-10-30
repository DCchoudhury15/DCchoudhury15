#!/usr/bin/env python3
"""Render the profile README as a record sleeve, from live GitHub data.

Writes assets/cover.svg plus a light and a dark tracklist. Needs GITHUB_TOKEN.
Runs once a day from .github/workflows/refresh.yml.
"""

import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request
from collections import defaultdict
from html import escape

USER = "DCchoudhury15"
ROOT = pathlib.Path(__file__).resolve().parent.parent
W = 840
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SERIF = "Georgia,'Times New Roman',serif"

THEMES = {
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "line": "#d0d7de", "grid": "#eaeef2", "accent": "#b5652a"},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "line": "#30363d", "grid": "#21262d", "accent": "#f0a35e"},
}

SIDE_A = [  # (track, genre)
    ("GSoC 2026 · INCF / EBRAINS", "Spack, HPC"),
    ("Taintward", "Python"),
    ("IsoWatch", "Go"),
    ("Chat-AI", "TypeScript"),
    ("AudioVisualizer", "PyTorch"),
    ("Portfolio", "WebGL"),
]
CREDITS = "Go · C++ · Python · TypeScript · PostgreSQL · Docker · Kubernetes · OpenTelemetry · Jaeger · Next.js"


def api(path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data


def merged_upstream_prs():
    """(repo full name, merge date, PR number, title, url) for every merged PR in repos the user does not own, oldest first."""
    q = urllib.parse.quote(f"type:pr author:{USER} is:merged -user:{USER}")
    prs, page = [], 1
    while True:
        items = api(f"/search/issues?q={q}&per_page=100&page={page}")["items"]
        for it in items:
            merged = it["pull_request"].get("merged_at") or it["closed_at"]
            prs.append((it["repository_url"].split("/repos/")[1], dt.date.fromisoformat(merged[:10]), it["number"],
                        it["title"], it["html_url"]))
        if len(items) < 100:
            return sorted(prs, key=lambda p: p[1])
        page += 1


def calendar():
    query = ("query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{"
             "totalContributions weeks{contributionDays{contributionCount}}}}}}")
    cal = api("/graphql", {"query": query, "variables": {"u": USER}})
    cal = cal["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], days


def longest_run(days):
    best = run = 0
    for n in days:
        run = run + 1 if n else 0
        best = max(best, run)
    return best


def cover(prs, total, days):
    """Album sleeve with the record sliding out. Same dark artwork in both themes."""
    orgs = len({r.split("/")[0] for r, *_ in prs})
    levels = ["#221a3a", "#4a2c5e", "#a23f6d", "#e0703f", "#f6c177"]
    tiles = "".join(  # one square per day, 19 days per column, last 361 days
        f'<rect x="{22 + (i // 19) * 13.6:.1f}" y="{22 + (i % 19) * 13.6:.1f}" width="11.6" height="11.6" rx="2.5" '
        f'fill="{levels[0 if not n else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4]}"/>'
        for i, n in enumerate(days[-361:]))
    grooves = "".join(f'<circle cx="318" cy="150" r="{r}" fill="none" stroke="#1f1f1f"/>' for r in range(48, 124, 5))
    stats = [(len(prs), "tracks"), (orgs, "labels"), (f"{total:,}", "plays"), (longest_run(days), "day streak")]
    cells = "".join(
        f'<text x="{472 + i * 90}" y="226" font-family="{SANS}" font-size="24" font-weight="700" fill="#f5efe6">{v}</text>'
        f'<text x="{472 + i * 90}" y="246" font-family="{MONO}" font-size="9.5" letter-spacing=".5" fill="#8a8178">'
        f"{label.upper()}</text>" for i, (v, label) in enumerate(stats))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="300" viewBox="0 0 {W} 300" role="img" '
        f'aria-label="Divyanshu Choudhury, Open Source, Vol. 1. {len(prs)} merged upstream PRs in {orgs} orgs.">'
        '<defs>'
        '<clipPath id="sleeve"><rect x="20" y="20" width="260" height="260" rx="4"/></clipPath></defs>'
        f'<rect width="{W}" height="300" rx="12" fill="#14110f"/>'
        f'<circle cx="318" cy="150" r="125" fill="#0b0b0b"/>{grooves}'
        '<path d="M318 40A110 110 0 0 1 420 115" fill="none" stroke="#fff" stroke-opacity=".07" stroke-width="18"/>'
        '<circle cx="318" cy="150" r="42" fill="#f0a35e"/>'
        f'<text x="318" y="140" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="700" fill="#14110f">DC15</text>'
        f'<text x="318" y="170" text-anchor="middle" font-family="{MONO}" font-size="7" fill="#14110f">33 RPM</text>'
        '<circle cx="318" cy="150" r="4" fill="#14110f"/>'
        '<rect x="20" y="20" width="260" height="260" rx="4" fill="#1b1530"/>'
        f'<g clip-path="url(#sleeve)">{tiles}<rect x="20" y="246" width="260" height="34" fill="#0d0a14" opacity=".8"/></g>'
        f'<text x="36" y="264" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="#fff" opacity=".8">OPEN SOURCE · VOL. 1</text>'
        f'<text x="472" y="76" font-family="{MONO}" font-size="11" letter-spacing="2" fill="#f0a35e">NOW PLAYING</text>'
        f'<text x="472" y="114" font-family="{SANS}" font-size="30" font-weight="700" fill="#f5efe6">Divyanshu Choudhury</text>'
        f'<text x="472" y="144" font-family="{SERIF}" font-size="19" font-style="italic" fill="#e0b885">Open Source, Vol. 1</text>'
        f'<text x="472" y="172" font-family="{MONO}" font-size="10.5" fill="#8a8178">JABALPUR RECORDS · SYSTEMS AND OBSERVABILITY</text>'
        f'<text x="472" y="192" font-family="{MONO}" font-size="9.5" fill="#6f665e">COVER ART: ONE SQUARE PER DAY OF CONTRIBUTIONS</text>'
        f"{cells}</svg>\n"
    )


def svg(h, label, body, t, scope=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
        f'role="img" aria-label="{escape(label)}">'
        f'<style>{scope}text{{font-family:{SANS};fill:{t["fg"]}}}{scope}.m{{font-family:{MONO}}}{scope}.mu{{fill:{t["muted"]}}}</style>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="10" fill="none" stroke="{t["line"]}"/>'
        f"{body}</svg>\n"
    )


def upstream_card(prs, t, links=False, scope=""):
    """Merged PRs by month, one lane per org. With links, every dot opens its PR (for the Pages copy)."""
    lanes = defaultdict(list)
    for pr in prs:
        lanes[pr[0].split("/")[0]].append(pr)
    order = sorted(lanes, key=lambda o: (-len(lanes[o]), lanes[o][0][1]))

    first = prs[0][1]
    start = dt.date(first.year, first.month, 1)
    today = dt.date.today()
    end = dt.date(today.year + today.month // 12, today.month % 12 + 1, 1)
    x0, x1 = 240, 776
    pos = lambda d: x0 + (x1 - x0) * (d - start).days / (end - start).days

    top, step = 92, 24
    h = top + len(order) * step + 4
    repos = len({p[0] for p in prs})
    body = [
        '<text x="24" y="38" font-size="16" font-weight="600">Merged pull requests in other projects</text>',
        f'<text x="816" y="38" text-anchor="end" font-size="12" class="m mu">'
        f"{len(prs)} PRs · {repos} repos · {len(order)} orgs</text>",
    ]
    month = start
    while month < end:
        x = pos(month)
        if month.month == 1 or month == start:
            body.append(f'<text x="{x + 5:.1f}" y="60" font-size="11" font-weight="600" class="m mu">{month.year}</text>')
        body.append(f'<line x1="{x:.1f}" y1="64" x2="{x:.1f}" y2="{h - 14}" stroke="{t["grid"]}"/>')
        body.append(f'<text x="{x + 5:.1f}" y="76" font-size="11" class="m mu">{month:%b}</text>')
        month = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)

    for i, org in enumerate(order):
        y = top + i * step
        names = sorted({p[0] for p in lanes[org]})
        label = escape(names[0]) if len(names) == 1 else f'{escape(org)}<tspan class="mu"> {len(names)} repos</tspan>'
        body.append(f'<text x="24" y="{y + 4}" font-size="12.5" class="m">{label}</text>')
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{t["grid"]}"/>')
        last = -99
        for repo, day, num, title, url in lanes[org]:
            x = max(pos(day), last + 7)  # nudge PRs merged the same week so each stays visible
            last = x
            dot = f'<circle class="dot" cx="{x:.1f}" cy="{y}" r="5" fill="{t["accent"]}" stroke="{t["bg"]}" stroke-width="2"/>'
            if links:
                dot = (f'<a href="{escape(url)}" target="_blank" rel="noopener" data-pr="{escape(repo)} #{num}" '
                       f'data-title="{escape(title)}" data-date="{day:%d %b %Y}">'
                       f'<circle class="hit" cx="{x:.1f}" cy="{y}" r="11"/>{dot}</a>')
            body.append(dot)
        body.append(f'<text x="816" y="{y + 4}" text-anchor="end" font-size="12.5" font-weight="600" class="m">'
                    f"{len(lanes[org])}</text>")
    return svg(h, f"{len(prs)} merged pull requests in {repos} upstream repositories", "".join(body), t, scope)


def track(x0, x1, y, no, title, note, t):
    return (f'<text x="{x0}" y="{y}" font-size="11" class="m mu">{no}</text>'
            f'<text x="{x0 + 30}" y="{y}" font-size="13.5">{escape(title)}</text>'
            f'<text x="{x1}" y="{y}" text-anchor="end" font-size="11" class="m mu">{escape(note)}</text>'
            f'<line x1="{x0}" y1="{y + 11}" x2="{x1}" y2="{y + 11}" stroke="{t["grid"]}"/>')


def tracklist(prs, t):
    top, step = 80, 32
    h = top + len(SIDE_A) * step + 40
    accent = f'class="m" font-size="11" letter-spacing="1.5" style="fill:{t["accent"]}"'
    body = [
        f'<text x="28" y="44" {accent}>SIDE A · ORIGINALS</text>',
        f'<text x="448" y="44" {accent}>SIDE B · UPSTREAM SESSIONS ({len(prs)})</text>',
        f'<line x1="420" y1="28" x2="420" y2="{h - 52}" stroke="{t["line"]}"/>',
        f'<line x1="0" y1="{h - 44}" x2="{W}" y2="{h - 44}" stroke="{t["line"]}"/>',
        f'<text x="28" y="{h - 17}" {accent}>CREDITS</text>',
        f'<text x="110" y="{h - 17}" font-size="12.5" class="mu">{escape(CREDITS)}</text>',
    ]
    for i, (title, genre) in enumerate(SIDE_A):
        body.append(track(28, 396, top + i * step, f"A{i + 1}", title, genre, t))
    for i, (repo, day, num, *_) in enumerate(prs[::-1][:len(SIDE_A)]):
        name = repo.split("/")[1].replace("opentelemetry", "otel")
        name = name if len(name) <= 26 else name[:25] + "…"
        body.append(track(448, 812, top + i * step, f"B{i + 1}", f"{name} #{num}", f"{day:%b %Y}", t))
    return svg(h, "Tracklist: my projects, and my latest merged upstream pull requests", "".join(body), t)


def page(prs):
    """Interactive copy of the timeline for GitHub Pages: hover a dot to see the PR, click to open it."""
    cards = "".join(f'<div class="{theme}">{upstream_card(prs, t, links=True, scope=f".{theme} ")}</div>'
                    for theme, t in THEMES.items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Merged upstream PRs</title>
<style>
body{{margin:0;padding:32px 16px;background:#fff;font-family:{SANS}}}
main{{max-width:840px;margin:auto}} svg{{width:100%;height:auto;display:block}} .dark{{display:none}}
.hit{{fill:transparent}} a:hover .dot{{r:8}} p{{color:#59636e;font-size:14px}} p a{{color:inherit}}
#tip{{position:fixed;display:none;pointer-events:none;max-width:320px;padding:8px 10px;border-radius:6px;
font-size:13px;line-height:1.4;background:#1f2328;color:#fff;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
#tip b{{display:block;font:12px {MONO};opacity:.75}}
@media (prefers-color-scheme:dark){{body{{background:#0d1117}} .light{{display:none}} .dark{{display:block}}
p{{color:#9198a1}} #tip{{background:#e6edf3;color:#0d1117}}}}
</style></head><body><main>{cards}
<p>Hover a dot to see the pull request, click to open it. Updated daily.
<a href="https://github.com/{USER}">Back to profile</a></p></main><div id="tip"></div>
<script>
const tip = document.getElementById("tip");
for (const a of document.querySelectorAll("a[data-pr]")) {{
  a.addEventListener("mousemove", e => {{
    const head = document.createElement("b");
    head.textContent = a.dataset.pr + " · " + a.dataset.date;
    tip.replaceChildren(head, a.dataset.title);
    tip.style.display = "block";
    tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = e.clientY + 14 + "px";
  }});
  a.addEventListener("mouseleave", () => tip.style.display = "none");
}}
</script></body></html>
"""


def main():
    prs = merged_upstream_prs()
    total, days = calendar()
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    (out / "cover.svg").write_text(cover(prs, total, days))
    for theme, t in THEMES.items():
        (out / f"tracklist-{theme}.svg").write_text(tracklist(prs, t))
        (out / f"upstream-{theme}.svg").write_text(upstream_card(prs, t))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(page(prs))
    print(f"{total} contributions, {len(prs)} merged upstream PRs")


if __name__ == "__main__":
    main()
