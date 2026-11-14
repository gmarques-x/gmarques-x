#!/usr/bin/env python3
"""Render the profile's field-notes cards as SVG, in Everforest dark and light.

    python3 scripts/render.py --out dist                 # live data (needs GITHUB_TOKEN)
    python3 scripts/render.py --out dist --sample        # sample data, marked as such

Writes specimen-{dark,light}.svg and stats-{dark,light}.svg.
Standard library only, so it runs on a plain GitHub Actions runner.
"""
import argparse
import base64
import datetime as dt
import json
import math
import os
import pathlib
import urllib.request
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGIN = os.environ.get("PROFILE_LOGIN", "gmarques-x")

# Everforest (github.com/sainnhe/everforest), dark medium and light medium.
# Every colour must be in scripts/everforest.json (scripts/check_palette.py checks).
THEMES = {
    "dark": {
        "paper": "#2D353B",   # bg0
        "grid": "#343F44",    # bg1
        "rule": "#4F585E",    # bg4
        "ink": "#D3C6AA",     # fg
        "muted": "#9DA9A0",   # grey2
        "faint": "#859289",   # grey1
        "accent": "#A7C080",  # green
        "cursor": "#DBBC7F",  # yellow
        "dots": ["#425047", "#83C092", "#A7C080", "#DBBC7F"],
        "langs": ["#A7C080", "#83C092", "#7FBBB3", "#D699B6", "#DBBC7F", "#E69875", "#E67E80"],
    },
    "light": {
        "paper": "#FDF6E3",   # bg0
        "grid": "#F4F0D9",    # bg1
        "rule": "#E0DCC7",    # bg4
        "ink": "#5C6A72",     # fg, the light scheme's text colour
        "muted": "#5C6A72",   # fg: no light grey is dark enough for small notes
        "faint": "#829181",   # grey2, the scheme's darkest grey (its "dim")
        "accent": "#8DA101",  # green
        "cursor": "#DFA000",  # yellow
        "dots": ["#5C6A72", "#35A77C", "#8DA101", "#DFA000"],
        "langs": ["#8DA101", "#35A77C", "#3A94C5", "#DF69BA", "#DFA000", "#F57D26", "#F85552"],
    },
}


W = 840


def font_css():
    fonts = ROOT / "assets" / "fonts"
    css = []
    for weight, name in ((400, "regular"), (700, "bold")):
        data = (fonts / f"jetbrains-mono-{name}.woff2.b64").read_text().strip()
        css.append(
            "@font-face{font-family:'JBM';font-weight:%d;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}" % (weight, data)
        )
    return "".join(css)


FONT_CSS = None


def frame(theme, height, title, right_label, body, sample):
    """Shared paper, grid, corner brackets and figure label."""
    global FONT_CSS
    FONT_CSS = FONT_CSS or font_css()
    t = THEMES[theme]
    b = 22  # bracket inset
    L = 16  # bracket arm length
    brackets = "".join(
        f'<path d="M{x} {y + dy * L} V{y} H{x + dx * L}" />'
        for x, y, dx, dy in ((b, b, 1, 1), (W - b, b, -1, 1), (b, height - b, 1, -1), (W - b, height - b, -1, -1))
    )
    right_fill = t["faint"]
    if sample:  # make sample renders impossible to mistake for real data
        right_label, right_fill = "SAMPLE DATA", t["cursor"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<style>{FONT_CSS}
text{{font-family:'JBM','JetBrains Mono','SF Mono',Menlo,Consolas,monospace;}}
.lbl{{font-size:11px;font-weight:700;letter-spacing:1.6px;}}
.val{{font-size:15px;}}
</style>
<defs>
  <pattern id="g" width="20" height="20" patternUnits="userSpaceOnUse">
    <path d="M20 0H0V20" fill="none" stroke="{t['grid']}" stroke-width="1"/>
  </pattern>
</defs>
<rect width="{W}" height="{height}" rx="14" fill="{t['paper']}"/>
<rect x="1" y="1" width="{W - 2}" height="{height - 2}" rx="13" fill="url(#g)" stroke="{t['rule']}" stroke-width="1"/>
<g fill="none" stroke="{t['accent']}" stroke-width="2" stroke-linecap="square">{brackets}</g>
<text x="40" y="50" class="lbl" fill="{t['accent']}">{escape(title.upper())}</text>
<text x="{W - 40}" y="50" class="lbl" fill="{right_fill}" text-anchor="end">{escape(right_label)}</text>
{body}
</svg>
"""


def tree_rings(t, cx, cy, r_max, count):
    """A tree cross-section: wobbly concentric rings, cracks, bark and a marked pith."""
    out = []
    for i in range(count):
        r = r_max * (i + 1) / count
        pts = []
        for k in range(73):
            a = 2 * math.pi * k / 72
            wob = 1 + 0.035 * math.sin(3 * a + i) + 0.02 * math.sin(7 * a + 2 * i) + 0.012 * math.sin(13 * a)
            pts.append(f"{cx + r * wob * math.cos(a):.1f},{cy + r * wob * math.sin(a):.1f}")
        width = 1.6 if i == count - 1 else 0.9
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{t["ink"]}" stroke-width="{width}" stroke-opacity="{0.55 if i < count - 1 else 0.85}"/>')
    # bark: short outward ticks
    ticks = []
    for k in range(120):
        a = 2 * math.pi * k / 120
        r0 = r_max * (1.03 + 0.02 * math.sin(5 * a))
        r1 = r0 + 4 + 3 * (0.5 + 0.5 * math.sin(11 * a))
        ticks.append(f"M{cx + r0 * math.cos(a):.1f} {cy + r0 * math.sin(a):.1f}L{cx + r1 * math.cos(a):.1f} {cy + r1 * math.sin(a):.1f}")
    out.append(f'<path d="{"".join(ticks)}" stroke="{t["ink"]}" stroke-opacity="0.45" stroke-width="0.9"/>')
    # radial cracks
    for a, frac in ((-0.6, 0.85), (2.35, 0.7), (1.2, 0.45)):
        out.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + r_max * frac * math.cos(a):.1f}" y2="{cy + r_max * frac * math.sin(a):.1f}" '
            f'stroke="{t["ink"]}" stroke-opacity="0.5" stroke-width="1" stroke-dasharray="3 2"/>'
        )
    out.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="{t["accent"]}" stroke-width="1.5"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="2.6" fill="{t["ink"]}"/>')
    return "".join(out)


def specimen(theme, d, sample):
    t = THEMES[theme]
    h = 356
    since = d["created"][:4]
    rows = [
        ("HABITAT", "macOS · Everforest, six schemes"),
        ("GROWING", "Project Grove, set up by one installer"),
        ("APPS", "Grove Keys · Grove Explorer · Grove Themes"),
        ("TERMINAL", "Ghostty · zsh · Starship"),
        ("DESKTOP", "AeroSpace · SketchyBar · wallpapers"),
        ("FIELD KIT", "JetBrains Mono · SF Pro · a Claude Code mod"),
        ("SINCE", f"{since} · {d['repos']} public repo{'' if d['repos'] == 1 else 's'}"),
    ]
    body = [
        f'<text x="40" y="104" font-size="34" font-weight="700" fill="{t["accent"]}">&gt;</text>',
        f'<text x="82" y="104" font-size="34" font-weight="700" fill="{t["ink"]}">{escape(LOGIN)}</text>',
        f'<rect x="{82 + len(LOGIN) * 20.4 + 6:.0f}" y="76" width="14" height="34" fill="{t["cursor"]}"/>',
    ]
    for i, (k, v) in enumerate(rows):
        y = 144 + i * 24
        body.append(f'<text x="40" y="{y}" class="lbl" fill="{t["faint"]}">{k}</text>')
        body.append(f'<text x="160" y="{y}" class="val" fill="{t["ink"]}">{escape(v)}</text>')
    for i, c in enumerate(t["dots"]):
        body.append(f'<circle cx="{48 + i * 22}" cy="{h - 44}" r="7" fill="{c}"/>')

    cx, cy, rmax = 670, 176, 82
    rings = 6 + min(d["repos"], 10)
    body.append(tree_rings(t, cx, cy, rmax, rings))
    # dimension line under the cross-section, like the avatar
    y = cy + rmax + 26
    x0, x1 = cx - rmax, cx + rmax
    body.append(
        f'<g stroke="{t["accent"]}" stroke-width="1.2" fill="{t["accent"]}">'
        f'<line x1="{x0}" y1="{y}" x2="{cx - 34}" y2="{y}"/><line x1="{cx + 34}" y1="{y}" x2="{x1}" y2="{y}"/>'
        f'<path d="M{x0} {y}l7 -4v8z"/><path d="M{x1} {y}l-7 -4v8z"/>'
        f'<line x1="{x0}" y1="{y - 7}" x2="{x0}" y2="{y + 7}"/><line x1="{x1}" y1="{y - 7}" x2="{x1}" y2="{y + 7}"/></g>'
        f'<text x="{cx}" y="{y + 4}" text-anchor="middle" font-size="12" fill="{t["accent"]}">{rings} rings</text>'
    )
    return frame(theme, h, "Field notes · Fig.02 · specimen", "PINUS SYLVESTRIS", "\n".join(body), sample)


def stats(theme, d, sample):
    t = THEMES[theme]
    h = 250
    metrics = [
        ("CONTRIBUTIONS", d["contributions"], "past year"),
        ("COMMITS", d["commits"], "past year"),
        ("PULL REQUESTS", d["prs"], "past year"),
        ("STARS EARNED", d["stars"], "all repos"),
        ("PUBLIC REPOS", d["repos"], "owned"),
        ("FOLLOWERS", d["followers"], "people"),
    ]
    body = []
    for i, (label, value, note) in enumerate(metrics):
        col, row = i % 3, i // 3
        x, y = 40 + col * 138, 98 + row * 74
        body.append(f'<text x="{x}" y="{y}" class="lbl" fill="{t["faint"]}">{label}</text>')
        body.append(f'<text x="{x}" y="{y + 30}" font-size="26" font-weight="700" fill="{t["ink"]}">{value:,}</text>')
        body.append(f'<text x="{x}" y="{y + 48}" font-size="11" fill="{t["muted"]}">{note}</text>')

    # languages
    lx, lw = 480, 320
    body.append(f'<line x1="{lx - 22}" y1="80" x2="{lx - 22}" y2="{h - 40}" stroke="{t["rule"]}" stroke-width="1"/>')
    body.append(f'<text x="{lx}" y="98" class="lbl" fill="{t["faint"]}">TOP LANGUAGES</text>')
    # Shares are of the top five; a trace that would print as 0.0% is left out.
    langs = d["languages"][:5]
    total = sum(s for _, s in langs)
    langs = [(n, s) for n, s in langs if 100 * s / total >= 0.05] if total else []
    total = sum(s for _, s in langs)
    if not total:
        body.append(f'<text x="{lx}" y="132" class="val" fill="{t["muted"]}">No specimens collected yet.</text>')
    else:
        x = lx
        for i, (name, size) in enumerate(langs):
            w = lw * size / total
            body.append(f'<rect x="{x:.1f}" y="112" width="{max(w - 2, 1):.1f}" height="10" rx="2" fill="{t["langs"][i]}"/>')
            x += w
        for i, (name, size) in enumerate(langs):
            y = 150 + i * 20
            body.append(f'<circle cx="{lx + 5}" cy="{y - 4}" r="5" fill="{t["langs"][i]}"/>')
            body.append(f'<text x="{lx + 18}" y="{y}" font-size="13" fill="{t["ink"]}">{escape(name)}</text>')
            body.append(f'<text x="{lx + lw}" y="{y}" font-size="13" text-anchor="end" fill="{t["muted"]}">{100 * size / total:.1f}%</text>')
    updated = dt.date.today().strftime("UPDATED %d %b %Y").upper()
    return frame(theme, h, "Field notes · Fig.03 · measurements", updated, "\n".join(body), sample)


QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    if "errors" in res:
        raise SystemExit(f"GitHub API error: {res['errors']}")
    u = res["data"]["user"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = u["contributionsCollection"]
    return {
        "created": u["createdAt"],
        "followers": u["followers"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "languages": sorted(langs.items(), key=lambda kv: -kv[1]),
    }


SAMPLE = {
    "created": "2026-11-09T00:00:00Z",
    "followers": 3,
    "repos": 2,
    "stars": 1,
    "contributions": 42,
    "commits": 37,
    "prs": 2,
    "languages": [("Shell", 9200), ("JavaScript", 3100), ("Python", 2400), ("HTML", 1800), ("CSS", 4)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--sample", action="store_true", help="use sample data (marked on the cards)")
    a = ap.parse_args()
    data = SAMPLE if a.sample else fetch()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (out / f"specimen-{theme}.svg").write_text(specimen(theme, data, a.sample))
        (out / f"stats-{theme}.svg").write_text(stats(theme, data, a.sample))
    print(f"wrote 4 cards to {out}/")


if __name__ == "__main__":
    main()
