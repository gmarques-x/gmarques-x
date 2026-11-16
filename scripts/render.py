#!/usr/bin/env python3
"""Render the profile's field-notes cards as SVG, in Atlas Night and Atlas Paper.

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

# Atlas Paper (light) and Atlas Night (dark), Project Grove's field-atlas palettes.
# Every colour must be in scripts/atlas.json (scripts/check_palette.py checks).
# Orange is for marks only (corner brackets, prompt, cursor, snake), never small text.
THEMES = {
    "dark": {
        "paper": "#1F272A",   # Night bg0
        "grid": "#272E2F",    # the kit's grid line mixed onto Night
        "rule": "#434E52",    # bg4
        "ink": "#EFE6D2",     # fg
        "muted": "#D9CFBA",   # grey2
        "faint": "#A9A08C",   # grey1, the label ink
        "accent": "#F07A1F",  # the marker orange
        "cursor": "#F07A1F",  # the marker orange
        "dots": ["#434E52", "#86D6C9", "#AED58A", "#E8CB6C"],
        "langs": ["#AED58A", "#86D6C9", "#93C0E3", "#DDA6D6", "#E8CB6C", "#D8CBAE", "#AEB6D6"],
    },
    "light": {
        "paper": "#E6D7B2",   # Paper bg_dim
        "grid": "#DECEA9",    # the kit's grid line mixed onto Paper
        "rule": "#D9C79E",    # bg4
        "ink": "#2E261B",     # fg
        "muted": "#5A4328",   # grey2, the label ink
        "faint": "#5A4328",   # grey2: grey1 (#7A6347) is only 3.98:1 on this paper
        "accent": "#F07A1F",  # the marker orange
        "cursor": "#F07A1F",  # the marker orange
        "dots": ["#C9B48C", "#1A625B", "#3B6027", "#6A530E"],
        "langs": ["#3B6027", "#1A625B", "#2B5576", "#713F6C", "#6A530E", "#3A2F22", "#2C3350"],
    },
}


W = 840


def font_css():
    """JetBrains Mono for the figures; IM Fell English for what the surveyor writes:
    'Fell' (italic) for the notes, 'FellSC' (small caps) for the labels."""
    fonts = ROOT / "assets" / "fonts"
    faces = (
        ("JBM", "normal", 400, "jetbrains-mono-regular"),
        ("JBM", "normal", 700, "jetbrains-mono-bold"),
        ("Fell", "italic", 400, "im-fell-english-italic"),
        ("FellSC", "normal", 400, "im-fell-english-sc"),
    )
    css = []
    for family, style, weight, name in faces:
        data = (fonts / f"{name}.woff2.b64").read_text().strip()
        css.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%d;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}" % (family, style, weight, data)
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
        right_label, right_fill = "Sample data", t["ink"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<style>{FONT_CSS}
text{{font-family:'JBM','JetBrains Mono','SF Mono',Menlo,Consolas,monospace;}}
.sc{{font-family:'FellSC','IM FELL English SC',Georgia,serif;font-size:16px;letter-spacing:0.6px;}}
.it{{font-family:'Fell','IM FELL English',Georgia,serif;font-style:italic;font-size:18px;}}
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
<text x="40" y="52" class="sc" fill="{t['faint']}">{escape(title)}</text>
<text x="{W - 40}" y="52" class="sc" fill="{right_fill}" text-anchor="end">{escape(right_label)}</text>
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
        ("HABITAT", "macOS · Atlas Paper and Night, grown from Everforest"),
        ("GROWING", "Project Grove, set up by one installer"),
        ("APPS", "Grove Keys · Grove Explorer · Grove Themes"),
        ("TERMINAL", "Ghostty · zsh · Starship"),
        ("DESKTOP", "AeroSpace · SketchyBar · wallpapers"),
        ("FIELD KIT", "JetBrains Mono · SF Pro · a Claude Code mod"),
        ("SINCE", f"{since} · {d['repos']} public repo{'' if d['repos'] == 1 else 's'}"),
    ]
    body = [
        # the prompt is a mark, drawn rather than typed, so it may be orange
        f'<path d="M44 80 L62 92 L44 104" fill="none" stroke="{t["accent"]}" stroke-width="4.5" stroke-linecap="square"/>',
        f'<text x="82" y="104" font-size="34" font-weight="700" fill="{t["ink"]}">{escape(LOGIN)}</text>',
        f'<rect x="{82 + len(LOGIN) * 20.4 + 6:.0f}" y="76" width="14" height="34" fill="{t["cursor"]}"/>',
    ]
    for i, (k, v) in enumerate(rows):
        y = 144 + i * 24
        body.append(f'<text x="40" y="{y}" class="sc" fill="{t["faint"]}">{k.title()}</text>')
        if k == "HABITAT":  # the one line in the surveyor's hand
            body.append(f'<text x="160" y="{y}" class="it" fill="{t["ink"]}">{escape(v)}</text>')
        else:
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
        f'<text x="{cx}" y="{y + 4}" text-anchor="middle" font-size="12" fill="{t["ink"]}">{rings} rings</text>'
    )
    return frame(theme, h, "Field Notes · Fig.02 · Specimen", "Pinus sylvestris", "\n".join(body), sample)


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
        body.append(f'<text x="{x}" y="{y}" class="sc" fill="{t["faint"]}">{label.title()}</text>')
        body.append(f'<text x="{x}" y="{y + 30}" font-size="26" font-weight="700" fill="{t["ink"]}">{value:,}</text>')
        body.append(f'<text x="{x}" y="{y + 48}" font-size="11" fill="{t["muted"]}">{note}</text>')

    # languages
    lx, lw = 480, 320
    body.append(f'<line x1="{lx - 22}" y1="80" x2="{lx - 22}" y2="{h - 40}" stroke="{t["rule"]}" stroke-width="1"/>')
    body.append(f'<text x="{lx}" y="98" class="sc" fill="{t["faint"]}">Top Languages</text>')
    # Shares are of the top five; a trace that would print as 0.0% is left out.
    langs = d["languages"][:5]
    total = sum(s for _, s in langs)
    langs = [(n, s) for n, s in langs if 100 * s / total >= 0.05] if total else []
    total = sum(s for _, s in langs)
    if not total:
        body.append(f'<text x="{lx}" y="132" class="it" fill="{t["muted"]}">No specimens collected yet.</text>')
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
    updated = dt.date.today().strftime("Updated %d %b %Y")
    return frame(theme, h, "Field Notes · Fig.03 · Measurements", updated, "\n".join(body), sample)


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
