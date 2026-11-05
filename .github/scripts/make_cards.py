"""Render GitHub stats + top-languages cards (One Dark theme) as SVG.

Uses only public data from the GitHub REST API. In Actions, GITHUB_TOKEN is
passed for a higher rate limit; locally it also works without a token.

    python .github/scripts/make_cards.py iZHENGjy
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "iZHENGjy"
OUT = Path(__file__).resolve().parents[2] / "cards"
TOKEN = os.environ.get("GITHUB_TOKEN")

BG, TITLE, TEXT, ICON, MUTED = "#282c34", "#e4bf7a", "#df6d74", "#8eb573", "#abb2bf"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#663399", "Shell": "#89e051", "PowerShell": "#012456", "Jupyter Notebook": "#DA5B0B",
    "MATLAB": "#e16737", "C": "#555555", "C++": "#f34b7d", "TeX": "#3D6117",
}


def api(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": accept, "User-Agent": f"{USER}-profile-cards"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100&type=owner") if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in repos)

    since = (date.today() - timedelta(days=365)).isoformat()
    q = urllib.parse.quote(f"author:{USER} committer-date:>={since}")
    commits = api(f"/search/commits?q={q}&per_page=1")["total_count"]
    prs = api(f"/search/issues?q={urllib.parse.quote(f'author:{USER} type:pr')}&per_page=1")["total_count"]

    langs = {}
    for r in repos:
        for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[lang] = langs.get(lang, 0) + n
    return {
        "name": user.get("name") or USER,
        "repos": len(repos), "stars": stars, "followers": user["followers"],
        "commits": commits, "prs": prs, "langs": langs,
    }


def stats_svg(s):
    rows = [("Public repos", s["repos"]), ("Total stars", s["stars"]),
            ("Commits (last year)", s["commits"]), ("Pull requests", s["prs"]),
            ("Followers", s["followers"])]
    w, h = 400, 60 + 25 * len(rows)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="{escape(s["name"])} GitHub stats">',
           f'<rect width="{w}" height="{h}" rx="6" fill="{BG}"/>',
           f'<text x="25" y="35" font-family="{FONT}" font-size="18" font-weight="600" '
           f'fill="{TITLE}">{escape(s["name"])}\'s GitHub Stats</text>']
    for i, (label, value) in enumerate(rows):
        y = 70 + 25 * i
        out.append(f'<circle cx="31" cy="{y - 5}" r="4" fill="{ICON}"/>')
        out.append(f'<text x="45" y="{y}" font-family="{FONT}" font-size="14" font-weight="600" '
                   f'fill="{TEXT}">{label}:</text>')
        out.append(f'<text x="250" y="{y}" font-family="{FONT}" font-size="14" font-weight="700" '
                   f'fill="{MUTED}">{value:,}</text>')
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(langs, top=6):
    total = sum(langs.values()) or 1
    items = sorted(langs.items(), key=lambda kv: -kv[1])[:top]
    w = 300
    h = 90 + 25 * ((len(items) + 1) // 2)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           'role="img" aria-label="Most used languages">',
           f'<rect width="{w}" height="{h}" rx="6" fill="{BG}"/>',
           f'<text x="25" y="35" font-family="{FONT}" font-size="18" font-weight="600" '
           f'fill="{TITLE}">Most Used Languages</text>',
           '<clipPath id="bar"><rect x="25" y="52" width="250" height="8" rx="4"/></clipPath>',
           '<g clip-path="url(#bar)">']
    x = 25.0
    for lang, n in items:
        bw = 250 * n / total
        out.append(f'<rect x="{x:.2f}" y="52" width="{bw:.2f}" height="8" '
                   f'fill="{LANG_COLORS.get(lang, "#858585")}"/>')
        x += bw
    out.append("</g>")
    for i, (lang, n) in enumerate(items):
        cx, cy = 25 + 135 * (i % 2), 85 + 25 * (i // 2)
        out.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{LANG_COLORS.get(lang, "#858585")}"/>')
        out.append(f'<text x="{cx + 15}" y="{cy}" font-family="{FONT}" font-size="11" '
                   f'fill="{MUTED}">{escape(lang)} {100 * n / total:.1f}%</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    s = collect()
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_svg(s), encoding="utf-8")
    (OUT / "top-langs.svg").write_text(langs_svg(s["langs"]), encoding="utf-8")
    print({k: v for k, v in s.items() if k != "langs"}, sorted(s["langs"], key=s["langs"].get)[::-1])


if __name__ == "__main__":
    main()
