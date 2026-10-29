#!/usr/bin/env python3
"""Render the profile README cards from live GitHub data.

Writes a light and a dark SVG per card into assets/. Needs GITHUB_TOKEN.
Runs once a day from .github/workflows/refresh.yml.
"""

import datetime as dt
import json
import os
import pathlib
import random
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from html import escape

USER = "DCchoudhury15"
ROOT = pathlib.Path(__file__).resolve().parent.parent
W = 840
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

THEMES = {
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "line": "#d0d7de", "grid": "#eaeef2", "accent": "#b5652a"},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "line": "#30363d", "grid": "#21262d", "accent": "#f0a35e"},
}

# (label, simple-icons slug); None draws a letter badge instead of a logo
STACK = [
    ("Languages", [("Go", "go"), ("C++", "cplusplus"), ("Python", "python"), ("TypeScript", "typescript"),
                   ("JavaScript", "javascript"), ("Bash", "gnubash")]),
    ("Data and infra", [("PostgreSQL", "postgresql"), ("Docker", "docker"), ("Kubernetes", "kubernetes"),
                        ("Helm", "helm"), ("Linux", "linux"), ("Spack", None)]),
    ("Observability", [("OpenTelemetry", "opentelemetry"), ("Jaeger", "jaeger"), ("Prometheus", "prometheus"),
                       ("SigNoz", None)]),
    ("Web and ML", [("Next.js", "nextdotjs"), ("React", "react"), ("tRPC", "trpc"), ("Tailwind CSS", "tailwindcss"),
                    ("PyTorch", "pytorch")]),
]

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
    """(repo full name, merge date) for every merged PR in repos the user does not own."""
    q = urllib.parse.quote(f"type:pr author:{USER} is:merged -user:{USER}")
    prs, page = [], 1
    while True:
        items = api(f"/search/issues?q={q}&per_page=100&page={page}")["items"]
        for it in items:
            merged = it["pull_request"].get("merged_at") or it["closed_at"]
            prs.append((it["repository_url"].split("/repos/")[1], dt.date.fromisoformat(merged[:10])))
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


def streaks(days):
    longest = run = 0
    for n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    # today does not break the streak until it is over
    current, tail = 0, days[:-1] if days and not days[-1] else days
    for n in reversed(tail):
        if not n:
            break
        current += 1
    return current, longest


def svg(h, label, body, t):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
        f'role="img" aria-label="{escape(label)}">'
        f'<style>text{{font-family:{SANS};fill:{t["fg"]}}}.m{{font-family:{MONO}}}.mu{{fill:{t["muted"]}}}</style>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="10" fill="none" stroke="{t["line"]}"/>'
        f"{body}</svg>\n"
    )


def stats_card(total, days, prs, t):
    current, longest = streaks(days)
    cells = [
        (f"{total:,}", "contributions, past year"),
        (str(len(prs)), "merged upstream PRs"),
        (str(len({r for r, _ in prs})), "upstream repos"),
        (f"{current} {'day' if current == 1 else 'days'}", "current streak"),
        (f"{longest} days", "longest streak"),
    ]
    cw = W / len(cells)
    body = []
    for i, (value, label) in enumerate(cells):
        cx = cw * i + cw / 2
        if i:
            body.append(f'<line x1="{cw * i:.0f}" y1="26" x2="{cw * i:.0f}" y2="78" stroke="{t["grid"]}"/>')
        body.append(
            f'<text x="{cx:.0f}" y="54" text-anchor="middle" font-size="28" font-weight="700">{value}</text>'
            f'<text x="{cx:.0f}" y="78" text-anchor="middle" font-size="13" class="mu">{label}</text>'
        )
    label = ", ".join(f"{v} {l}" for v, l in cells)
    return svg(104, label, "".join(body), t)


def upstream_card(prs, t):
    lanes = defaultdict(list)
    for repo, day in prs:
        lanes[repo.split("/")[0]].append((repo, day))
    order = sorted(lanes, key=lambda o: (-len(lanes[o]), lanes[o][0][1]))

    first = prs[0][1]
    start = dt.date(first.year, first.month, 1)
    today = dt.date.today()
    end = dt.date(today.year + today.month // 12, today.month % 12 + 1, 1)
    x0, x1 = 240, 776
    pos = lambda d: x0 + (x1 - x0) * (d - start).days / (end - start).days

    top, step = 92, 24
    h = top + len(order) * step + 4
    repos = len({r for r, _ in prs})
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
        names = sorted({r for r, _ in lanes[org]})
        label = escape(names[0]) if len(names) == 1 else f'{escape(org)}<tspan class="mu"> {len(names)} repos</tspan>'
        body.append(f'<text x="24" y="{y + 4}" font-size="12.5" class="m">{label}</text>')
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{t["grid"]}"/>')
        last = -99
        for _, day in lanes[org]:
            x = max(pos(day), last + 7)  # nudge PRs merged the same week so each stays visible
            last = x
            body.append(f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{t["accent"]}" stroke="{t["bg"]}" stroke-width="2"/>')
        body.append(f'<text x="816" y="{y + 4}" text-anchor="end" font-size="12.5" font-weight="600" class="m">'
                    f"{len(lanes[org])}</text>")
    return svg(h, f"{len(prs)} merged pull requests in {repos} upstream repositories", "".join(body), t)


def sky_card(prs):
    """Night sky header. Each constellation is an upstream org and each of its stars is one merged PR."""
    rnd = random.Random(15)  # fixed seed, so the sky only changes when the data does
    h = 260
    orgs = Counter(r.split("/")[0] for r, _ in prs)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
        f'aria-label="Divyanshu Choudhury, open-source systems engineer. {len(prs)} merged upstream PRs in {len(orgs)} orgs.">'
        '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070b1a"/>'
        '<stop offset=".7" stop-color="#151633"/><stop offset="1" stop-color="#3a2238"/></linearGradient>'
        '<radialGradient id="band"><stop offset="0" stop-color="#c9d4ff" stop-opacity=".16"/>'
        '<stop offset="1" stop-color="#c9d4ff" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="c"><rect width="{W}" height="{h}" rx="10"/></clipPath></defs><g clip-path="url(#c)">'
        f'<rect width="{W}" height="{h}" fill="url(#sky)"/>'
        '<ellipse cx="520" cy="110" rx="440" ry="55" transform="rotate(-14 520 110)" fill="url(#band)"/>'
    ]
    for _ in range(170):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, h - 30), rnd.choice((.4, .5, .6, .7, .9, 1.2))
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rnd.uniform(.25, .9):.2f}"/>')

    boxes = [(350, 26, 170, 70), (570, 20, 150, 80), (740, 66, 70, 90), (380, 132, 140, 50), (580, 140, 120, 48)]
    for (org, n), (bx, by, bw, bh) in zip(orgs.most_common(len(boxes)), boxes):
        pts = sorted((rnd.uniform(bx, bx + bw), rnd.uniform(by, by + bh)) for _ in range(n))
        out.append(f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="none" '
                   'stroke="#9fb0d8" stroke-opacity=".4" stroke-width=".8"/>')
        out += [f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4.5" fill="#ffd9a0" opacity=".18"/>'
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="1.8" fill="#fff4e0"/>' for x, y in pts]
        out.append(f'<text x="{bx}" y="{by + bh + 16}" font-family="{MONO}" font-size="10" letter-spacing="1" '
                   f'fill="#8f9cc0">{escape(org.upper())} · {n}</text>')

    for name, x, y in (("Taintward", 150, 72), ("IsoWatch", 250, 118)):
        out.append(f'<circle cx="{x}" cy="{y}" r="11" fill="#ffe7c2" opacity=".14"/>'
                   f'<path d="M{x} {y - 8}L{x + 1.8} {y - 1.8}L{x + 8} {y}L{x + 1.8} {y + 1.8}L{x} {y + 8}'
                   f'L{x - 1.8} {y + 1.8}L{x - 8} {y}L{x - 1.8} {y - 1.8}Z" fill="#ffe7c2"/>'
                   f'<text x="{x + 13}" y="{y + 4}" font-family="{SANS}" font-size="12" fill="#e9d9bf">{name}</text>')

    ridge = " ".join(f"{x},{rnd.uniform(222, 248):.0f}" for x in range(0, W + 70, 70))
    out += [
        f'<path d="M0 {h}L{ridge}L{W} {h}Z" fill="#05070f"/>',
        f'<text x="32" y="44" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="#f0a35e">'
        f'{len(prs)} MERGED PRS · {len(orgs)} ORGS</text>',
        f'<text x="32" y="184" font-family="{SANS}" font-size="30" font-weight="700" fill="#f5efe6">Divyanshu Choudhury</text>',
        f'<text x="32" y="208" font-family="{SANS}" font-size="13.5" fill="#aab4cc">open-source systems engineer · Jabalpur, India</text>',
        f'<text x="{W - 20}" y="{h - 12}" text-anchor="end" font-family="{MONO}" font-size="10" fill="#6f7aa0">'
        'each star in a constellation is one merged PR</text>',
        "</g></svg>\n",
    ]
    return "".join(out)


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable(color, t):
    """Brand color, or the text color when the brand color would vanish on this background."""
    lo, hi = sorted((luminance(color), luminance(t["bg"])))
    return color if (hi + 0.05) / (lo + 0.05) >= 2.2 else t["fg"]


def stack_card(icons, t):
    col_w, row_h = 384, 32
    body, y_top = [], 0
    for pair in (STACK[:2], STACK[2:]):
        rows_used = 1
        for c, (title, items) in enumerate(pair):
            cx, x, row = 24 + c * (col_w + 24), 24 + c * (col_w + 24), 0
            body.append(f'<text x="{cx}" y="{y_top + 36}" font-size="11" letter-spacing="1" class="m mu">'
                        f"{title.upper()}</text>")
            for name, slug in items:
                width = 26 + len(name) * 7.4 + 22
                if x + width > cx + col_w:
                    x, row = cx, row + 1
                y = y_top + 66 + row * row_h
                if slug:
                    icon = icons[slug]
                    body.append(f'<path transform="translate({x:.1f} {y - 14}) scale(0.75)" '
                                f'fill="{readable(icon["hex"], t)}" d="{icon["path"]}"/>')
                else:
                    body.append(f'<rect x="{x + 1:.1f}" y="{y - 13}" width="16" height="16" rx="4" fill="none" '
                                f'stroke="{t["muted"]}" stroke-width="1.5"/>'
                                f'<text x="{x + 9:.1f}" y="{y - 1}" text-anchor="middle" font-size="10" '
                                f'font-weight="700" class="m mu">{name[0]}</text>')
                body.append(f'<text x="{x + 26:.1f}" y="{y}" font-size="13.5">{escape(name)}</text>')
                x += width
            rows_used = max(rows_used, row + 1)
        y_top += 50 + rows_used * row_h
    names = ", ".join(n for _, items in STACK for n, _ in items)
    return svg(y_top + 10, f"Tools I use: {names}", "".join(body), t)


def main():
    prs = merged_upstream_prs()
    total, days = calendar()
    icons = json.loads((ROOT / "scripts" / "icons.json").read_text())
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    (out / "header.svg").write_text(sky_card(prs))
    for theme, t in THEMES.items():
        (out / f"stats-{theme}.svg").write_text(stats_card(total, days, prs, t))
        (out / f"upstream-{theme}.svg").write_text(upstream_card(prs, t))
        (out / f"stack-{theme}.svg").write_text(stack_card(icons, t))
    print(f"{total} contributions, {len(prs)} merged upstream PRs, streaks {streaks(days)}")


if __name__ == "__main__":
    main()
