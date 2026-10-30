#!/usr/bin/env python3
"""Render the profile README cards from live GitHub data.

Writes assets/cover.svg, the PR timeline rows and the Pages copy. Needs GITHUB_TOKEN.
Runs once a day from .github/workflows/refresh.yml.
"""

import datetime as dt
import json
import math
import os
import pathlib
import re
import shutil
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
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "line": "#d0d7de", "grid": "#eaeef2", "accent": "#b5652a",
              "palette": ["#b5652a", "#c2416e", "#0f8a7a", "#7c5cd6", "#1f6feb", "#9a6700"]},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "line": "#30363d", "grid": "#21262d", "accent": "#f0a35e",
             "palette": ["#f0a35e", "#e7709a", "#56d4bc", "#b392f0", "#6cb6ff", "#e3b341"]},
}


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
    """Contribution calendar on a sleeve, with a spinning disc. Same dark artwork in both themes."""
    orgs = len({r.split("/")[0] for r, *_ in prs})
    levels = ["#221a3a", "#4a2c5e", "#a23f6d", "#e0703f", "#f6c177"]
    tiles = "".join(  # one square per day, 19 days per column, last 361 days
        f'<rect x="{22 + (i // 19) * 13.6:.1f}" y="{22 + (i % 19) * 13.6:.1f}" width="11.6" height="11.6" rx="2.5" '
        f'fill="{levels[0 if not n else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4]}"/>'
        for i, n in enumerate(days[-361:]))
    grooves = "".join(f'<circle cx="318" cy="150" r="{r}" fill="none" stroke="#1f1f1f"/>' for r in range(48, 124, 5))
    marks = "".join(  # uneven groove highlights, so the spin is visible
        f'<path d="M{318 + r} 150A{r} {r} 0 0 1 {318 + r * math.cos(a):.1f} {150 + r * math.sin(a):.1f}" '
        f'fill="none" stroke="#3a3a3a" stroke-width="1.5"/>' for r, a in ((58, 1.1), (76, 2.0), (94, 0.8), (112, 1.6)))
    stats = [(len(prs), "merged PRs"), (orgs, "orgs"), (f"{total:,}", "contributions"), (longest_run(days), "day streak")]
    cells = "".join(
        f'<text x="{472 + i * 90}" y="226" font-family="{SANS}" font-size="24" font-weight="700" fill="#f5efe6">{v}</text>'
        f'<text x="{472 + i * 90}" y="246" font-family="{MONO}" font-size="9.5" letter-spacing=".5" fill="#8a8178">'
        f"{label.upper()}</text>" for i, (v, label) in enumerate(stats))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="300" viewBox="0 0 {W} 300" role="img" '
        f'aria-label="Divyanshu Choudhury, open-source systems engineer. {len(prs)} merged upstream PRs in {orgs} orgs.">'
        '<defs><clipPath id="sleeve"><rect x="20" y="20" width="260" height="260" rx="4"/></clipPath></defs>'
        f'<rect width="{W}" height="300" rx="12" fill="#14110f"/>'
        f'<circle cx="318" cy="150" r="125" fill="#0b0b0b"/>'
        f'<g>{grooves}{marks}<circle cx="318" cy="150" r="42" fill="#f0a35e"/>'
        f'<text x="318" y="140" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="700" fill="#14110f">DC15</text>'
        '<circle cx="318" cy="170" r="2.5" fill="#14110f"/>'
        '<animateTransform attributeName="transform" type="rotate" from="0 318 150" to="360 318 150" dur="8s" repeatCount="indefinite"/></g>'
        '<path d="M318 40A110 110 0 0 1 420 115" fill="none" stroke="#fff" stroke-opacity=".07" stroke-width="18"/>'
        '<circle cx="318" cy="150" r="4" fill="#14110f"/>'
        '<rect x="20" y="20" width="260" height="260" rx="4" fill="#1b1530"/>'
        f'<g clip-path="url(#sleeve)">{tiles}<rect x="20" y="246" width="260" height="34" fill="#0d0a14" opacity=".8"/></g>'
        f'<text x="36" y="267" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="#fff" opacity=".8">361 DAYS OF CONTRIBUTIONS</text>'
        f'<text x="472" y="76" font-family="{MONO}" font-size="11" letter-spacing="2" fill="#f0a35e">OPEN-SOURCE SYSTEMS ENGINEER</text>'
        f'<text x="472" y="114" font-family="{SANS}" font-size="30" font-weight="700" fill="#f5efe6">Divyanshu Choudhury</text>'
        f'<text x="472" y="144" font-family="{SERIF}" font-size="19" font-style="italic" fill="#e0b885">Observability, databases and build tooling</text>'
        f'<text x="472" y="172" font-family="{MONO}" font-size="10.5" fill="#8a8178">JABALPUR, INDIA · GSOC 2026 AT INCF / EBRAINS</text>'
        f'<text x="472" y="192" font-family="{MONO}" font-size="9.5" fill="#6f665e">LEFT: ONE SQUARE PER DAY OF CONTRIBUTIONS</text>'
        f"{cells}</svg>\n"
    )


def svg(h, label, body, t, scope="", frame=True):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
        f'role="img" aria-label="{escape(label)}">'
        f'<style>{scope}text{{font-family:{SANS};fill:{t["fg"]}}}{scope}.m{{font-family:{MONO}}}{scope}.mu{{fill:{t["muted"]}}}</style>'
        + (f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="10" fill="none" stroke="{t["line"]}"/>' if frame else "")
        + f"{body}</svg>\n"
    )


X0, X1 = 240, 760


def timeline(prs):
    """Lanes (one per org, busiest first), month starts and an x position function."""
    lanes = defaultdict(list)
    for pr in prs:
        lanes[pr[0].split("/")[0]].append(pr)
    order = sorted(lanes, key=lambda o: (-len(lanes[o]), lanes[o][0][1]))
    next_month = lambda d: dt.date(d.year + d.month // 12, d.month % 12 + 1, 1)
    start, end = dt.date(prs[0][1].year, prs[0][1].month, 1), next_month(dt.date.today())
    months = [start]
    while next_month(months[-1]) < end:
        months.append(next_month(months[-1]))
    pos = lambda d: X0 + (X1 - X0) * (d - start).days / (end - start).days
    return lanes, order, months, pos


def head(prs, order, months, pos, t, grid_to):
    out = [
        '<text x="24" y="38" font-size="16" font-weight="600">Merged pull requests in other projects</text>',
        f'<text x="816" y="38" text-anchor="end" font-size="12" class="m mu">'
        f"{len(prs)} PRs · {len({p[0] for p in prs})} repos · {len(order)} orgs</text>",
    ]
    for m in months:
        x = pos(m)
        if m.month == 1 or m == months[0]:
            out.append(f'<text x="{x + 5:.1f}" y="60" font-size="11" font-weight="600" class="m mu">{m.year}</text>')
        out.append(f'<line x1="{x:.1f}" y1="64" x2="{x:.1f}" y2="{grid_to}" stroke="{t["grid"]}"/>'
                   f'<text x="{x + 5:.1f}" y="76" font-size="11" class="m mu">{m:%b}</text>')
    return out


def lane(org, prs, y, pos, t, color, links=False):
    """One org: a soft band from its first to its last merged PR, a dot per PR, and a count badge."""
    names = sorted({p[0] for p in prs})
    label = escape(names[0]) if len(names) == 1 else f'{escape(org)}<tspan class="mu"> {len(names)} repos</tspan>'
    xs, last = [], -99
    for p in prs:
        last = max(pos(p[1]), last + 7)  # nudge PRs merged the same week so each stays visible
        xs.append(last)
    out = [f'<text x="24" y="{y + 4}" font-size="12.5" class="m">{label}</text>',
           f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" stroke="{t["grid"]}"/>',
           f'<rect x="{xs[0] - 9:.1f}" y="{y - 9}" width="{xs[-1] - xs[0] + 18:.1f}" height="18" rx="9" fill="{color}" opacity=".16"/>']
    for x, (repo, day, num, title, url) in zip(xs, prs):
        dot = f'<circle class="dot" cx="{x:.1f}" cy="{y}" r="5" fill="{color}" stroke="{t["bg"]}" stroke-width="1.5"/>'
        if links:
            dot = (f'<a href="{escape(url)}" target="_blank" rel="noopener" data-pr="{escape(repo)} #{num}" '
                   f'data-title="{escape(title)}" data-date="{day:%d %b %Y}">'
                   f'<circle class="hit" cx="{x:.1f}" cy="{y}" r="11"/>{dot}</a>')
        out.append(dot)
    out.append(f'<rect x="778" y="{y - 9}" width="30" height="18" rx="9" fill="{color}" opacity=".16"/>'
               f'<text x="793" y="{y + 4}" text-anchor="middle" font-size="12" font-weight="700" class="m" '
               f'style="fill:{color}">{len(prs)}</text>'
               f'<text x="830" y="{y + 4}" text-anchor="end" font-size="12" class="mu">↗</text>')
    return out


def upstream_card(prs, t, links=False, scope=""):
    """The whole timeline as one card. With links, every dot opens its PR (for the Pages copy)."""
    lanes, order, months, pos = timeline(prs)
    top, step = 100, 30
    h = top + len(order) * step
    body = head(prs, order, months, pos, t, h - 14)
    for i, org in enumerate(order):
        body += lane(org, lanes[org], top + i * step, pos, t, t["palette"][i % len(t["palette"])], links)
    return svg(h, f"{len(prs)} merged pull requests in upstream repositories", "".join(body), t, scope)


def org_link(org, prs):
    """GitHub's own list of my merged PRs in this org."""
    repos = {p[0] for p in prs}
    q = f"is:pr is:merged author:{USER}"
    if len(repos) == 1:
        return f"https://github.com/{repos.pop()}/pulls?q={urllib.parse.quote_plus(q)}"
    return f"https://github.com/search?q={urllib.parse.quote_plus(q + ' org:' + org)}&type=pullrequests"


def upstream_rows(prs, out):
    """The timeline split into a header and one image per org, so each row in the README can be a link.

    Writes the images into out and returns the HTML that stacks them.
    """
    lanes, order, months, pos = timeline(prs)
    for theme, t in THEMES.items():
        (out / f"head-{theme}.svg").write_text(
            svg(88, "Merged pull requests in other projects, by month", "".join(head(prs, order, months, pos, t, 88)), t, frame=False))
        for i, org in enumerate(order):
            color = t["palette"][i % len(t["palette"])]
            (out / f"{org}-{theme}.svg").write_text(
                svg(30, f"{org}: {len(lanes[org])} merged PRs", "".join(lane(org, lanes[org], 15, pos, t, color)), t, frame=False))
    pic = lambda name, alt: (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/upstream/{name}-dark.svg">'
                             f'<img alt="{escape(alt)}" src="assets/upstream/{name}-light.svg" width="100%"></picture>')
    rows = [pic("head", "Merged pull requests in other projects, by month")]
    rows += [f'<a href="{escape(org_link(org, lanes[org]))}">{pic(org, f"{org}: {len(lanes[org])} merged PRs")}</a>'
             for org in order]
    return "\n".join(rows)


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
    rows = out / "upstream"
    shutil.rmtree(rows, ignore_errors=True)
    rows.mkdir()
    readme = ROOT / "README.md"
    block = f"<!-- timeline:start -->\n{upstream_rows(prs, rows)}\n<!-- timeline:end -->"
    readme.write_text(re.sub(r"<!-- timeline:start -->.*<!-- timeline:end -->", lambda _: block, readme.read_text(), flags=re.S))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(page(prs))
    print(f"{total} contributions, {len(prs)} merged upstream PRs")


if __name__ == "__main__":
    main()
