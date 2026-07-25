"""
Reads stats_data.json (written by fetch_stats.py) and:
  1. Regenerates stats.svg, langs.svg, trophies.svg from templates using the
     real numbers.
  2. Patches the 4 stat-block values inside banner.svg / banner-light.svg
     in place (Repos / Commits / Stars / Followers) without touching
     anything else in those files - the name, layout, and decorations
     stay exactly as designed, only the live numbers move.
"""
import json
import re

with open("stats_data.json") as f:
    D = json.load(f)


def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


# ---------------------------------------------------------------------------
# stats.svg
# ---------------------------------------------------------------------------
def render_stats_svg():
    W, H = 480, 260
    rows = [
        ("Total Stars", fmt(D["stars"]), min(D["stars"] / 300, 1)),
        ("Total Commits", fmt(D["commits"]), min(D["commits"] / 3000, 1)),
        ("Total PRs", fmt(D["prs"]), min(D["prs"] / 150, 1)),
        ("Total Issues", fmt(D["issues"]), min(D["issues"] / 100, 1)),
        ("Public Repos", fmt(D["repos"]), min(D["repos"] / 60, 1)),
    ]
    RING_R = 62
    CIRC = 2 * 3.14159265 * RING_R
    PCT = max(0.08, min(D["rank_pct"], 1))

    rows_svg = []
    for i, (label, val, pct) in enumerate(rows):
        y = i * 34
        rows_svg.append(f'''
    <g transform="translate(210,{28+y})">
      <g class="row" style="animation-delay:{0.15*i+0.3:.2f}s">
        <text x="0" y="0" class="row-icon">&#9733;</text>
        <text x="20" y="0" class="row-label">{label}:</text>
        <text x="230" y="0" text-anchor="end" class="row-val">{val}</text>
        <rect x="0" y="8" width="230" height="5" rx="2.5" class="row-track"/>
        <rect x="0" y="8" width="{230*pct:.1f}" height="5" rx="2.5" class="row-fill" style="animation-delay:{0.15*i+0.6:.2f}s"/>
      </g>
    </g>''')

    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="sbg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#170a29"/><stop offset="100%" stop-color="#2c1148"/>
  </linearGradient>
  <linearGradient id="sring" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#ff5fc7"/><stop offset="100%" stop-color="#9b4bff"/>
  </linearGradient>
  <linearGradient id="sbar" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#ff5fc7"/><stop offset="100%" stop-color="#9b4bff"/>
  </linearGradient>
  <clipPath id="frameS"><rect width="{W}" height="{H}" rx="20"/></clipPath>
</defs>
<style>
  .card-bg {{ fill:url(#sbg); }}
  .row {{ opacity:0; transform-origin:0px 0px; animation: slideIn 0.6s ease forwards; }}
  @keyframes slideIn {{ from {{ opacity:0; transform: translateX(24px); }} to {{ opacity:1; transform: translateX(0); }} }}
  .row-icon {{ font-size:11px; fill:#ff9be0; }}
  .row-label {{ font-family:'Segoe UI',Arial,sans-serif; font-size:13px; fill:#c9b3e8; }}
  .row-val {{ font-family:'Segoe UI',Arial,sans-serif; font-size:13px; font-weight:700; fill:#ffffff; }}
  .row-track {{ fill:#3a1c58; }}
  .row-fill {{ fill:url(#sbar); width:0; animation: growW 1s cubic-bezier(.2,.8,.2,1) forwards; }}
  @keyframes growW {{ from {{ width:0; }} }}
  .ring-track {{ fill:none; stroke:#3a1c58; stroke-width:10; }}
  .ring-fill {{ fill:none; stroke:url(#sring); stroke-width:10; stroke-linecap:round;
    stroke-dasharray:{CIRC:.1f}; stroke-dashoffset:{CIRC:.1f};
    animation: ringGrow 1.6s cubic-bezier(.2,.8,.2,1) 0.2s forwards; transform:rotate(-90deg); transform-origin:105px 130px; }}
  @keyframes ringGrow {{ to {{ stroke-dashoffset:{CIRC*(1-PCT):.1f}; }} }}
  .rank-text {{ font-family:'Segoe UI',Arial,sans-serif; font-size:34px; font-weight:800; fill:#ffffff; opacity:0; animation: fadeIn 0.6s ease 1.4s forwards; }}
  .rank-sub {{ font-family:'Segoe UI',Arial,sans-serif; font-size:11px; fill:#c9b3e8; opacity:0; animation: fadeIn 0.6s ease 1.6s forwards; }}
  @keyframes fadeIn {{ to {{ opacity:1; }} }}
  .title {{ font-family:'Segoe UI',Arial,sans-serif; font-size:15px; font-weight:700; fill:#ff9be0; }}
</style>
<g clip-path="url(#frameS)">
  <rect width="{W}" height="{H}" class="card-bg"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="#6d3fae55" stroke-width="1.5"/>
  <text x="24" y="30" class="title">{D["name"]}'s GitHub Stats</text>
  <g transform="translate(0,10)">
    <circle cx="105" cy="130" r="{RING_R}" class="ring-track"/>
    <circle cx="105" cy="130" r="{RING_R}" class="ring-fill"/>
    <text x="105" y="122" text-anchor="middle" class="rank-text">{D["rank_letter"]}</text>
    <text x="105" y="145" text-anchor="middle" class="rank-sub">RANK</text>
  </g>
{''.join(rows_svg)}
</g>
</svg>'''


# ---------------------------------------------------------------------------
# langs.svg
# ---------------------------------------------------------------------------
def render_langs_svg():
    W, H = 420, 300
    langs = D["languages"] or [{"name": "N/A", "pct": 100.0, "color": "#9b4bff"}]
    BAR_X, BAR_Y, BAR_W, BAR_H = 24, 56, 372, 14

    segs, x = [], 0
    for i, lang in enumerate(langs):
        seg_w = BAR_W * lang["pct"] / 100
        segs.append(f'''
    <rect x="{x:.1f}" y="0" width="0" height="{BAR_H}" fill="{lang["color"]}" class="seg" style="--sw:{seg_w:.1f}px; animation-delay:{0.15*i+0.15:.2f}s"/>''')
        x += seg_w

    legend = []
    for i, lang in enumerate(langs):
        y = i * 32
        legend.append(f'''
    <g transform="translate(0,{y})">
      <g class="lg-row" style="animation-delay:{0.15*i+0.6:.2f}s">
        <circle cx="6" cy="0" r="5" fill="{lang["color"]}"/>
        <text x="20" y="4" class="lname">{lang["name"]}</text>
        <text x="372" y="4" text-anchor="end" class="lpct">{lang["pct"]:g}%</text>
      </g>
    </g>''')

    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="lbg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#170a29"/><stop offset="100%" stop-color="#2c1148"/>
  </linearGradient>
  <clipPath id="frameL"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <clipPath id="barClip"><rect width="{BAR_W}" height="{BAR_H}" rx="7"/></clipPath>
</defs>
<style>
  .title {{ font-family:'Segoe UI',Arial,sans-serif; font-size:15px; font-weight:700; fill:#ff9be0; }}
  .lname {{ font-family:'Segoe UI',Arial,sans-serif; font-size:13px; fill:#e6d9f7; }}
  .lpct {{ font-family:'Segoe UI',Arial,sans-serif; font-size:12.5px; font-weight:700; fill:#ffffff; }}
  .bar-track {{ fill:#3a1c58; }}
  .seg {{ animation: growSeg 0.9s cubic-bezier(.2,.8,.2,1) forwards; }}
  @keyframes growSeg {{ from {{ width:0; }} to {{ width: var(--sw); }} }}
  .lg-row {{ opacity:0; transform-origin:0px 0px; animation: legFade 0.5s ease forwards; }}
  @keyframes legFade {{ from {{ opacity:0; transform: translateX(-8px); }} to {{ opacity:1; transform: translateX(0); }} }}
</style>
<g clip-path="url(#frameL)">
  <rect width="{W}" height="{H}" fill="url(#lbg)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="#6d3fae55" stroke-width="1.5"/>
  <text x="24" y="30" class="title">Top Languages</text>
  <g transform="translate({BAR_X},{BAR_Y})">
    <rect width="{BAR_W}" height="{BAR_H}" rx="7" class="bar-track"/>
    <g clip-path="url(#barClip)">{''.join(segs)}</g>
  </g>
  <g transform="translate(24,100)">{''.join(legend)}</g>
</g>
</svg>'''


# ---------------------------------------------------------------------------
# trophies.svg
# ---------------------------------------------------------------------------
def rank_for(value, thresholds):
    for t, letter in thresholds:
        if value >= t:
            return letter
    return thresholds[-1][1]


def render_trophies_svg():
    CELL_W, CELL_H = 148, 150
    GAP = 10
    trophies = [
        ("\u2b50", "Stargazer", f'Stars {D["stars"]}', rank_for(D["stars"], [(200,"SSS"),(80,"S"),(30,"A"),(10,"B+"),(0,"B")]), "#ffd479"),
        ("\U0001F4BB", "Committer", f'Commits {fmt(D["commits"])}', rank_for(D["commits"], [(2000,"SSS"),(800,"S"),(300,"A"),(100,"B+"),(0,"B")]), "#7fe3ff"),
        ("\u2665", "Popular", f'Followers {D["followers"]}', rank_for(D["followers"], [(150,"SSS"),(60,"S"),(25,"A"),(10,"B+"),(0,"B")]), "#ff9be0"),
        ("\U0001F500", "Merger", f'PRs {D["prs"]}', rank_for(D["prs"], [(100,"SSS"),(40,"S"),(15,"A"),(5,"B+"),(0,"B")]), "#9b4bff"),
        ("\U0001F4E6", "Creator", f'Repos {D["repos"]}', rank_for(D["repos"], [(50,"SSS"),(25,"S"),(12,"A"),(5,"B+"),(0,"B")]), "#3ddc84"),
        ("\U0001F41B", "Debugger", f'Issues {D["issues"]}', rank_for(D["issues"], [(80,"SSS"),(30,"S"),(10,"A"),(3,"B+"),(0,"B")]), "#ff5fc7"),
    ]
    N = len(trophies)
    W = 10 * 2 + N * CELL_W + (N - 1) * GAP
    H = CELL_H + 20

    cells = []
    for i, (icon, label, sub, rank, color) in enumerate(trophies):
        x = 10 + i * (CELL_W + GAP)
        cells.append(f'''
    <g transform="translate({x},10)">
      <g class="tcell" style="animation-delay:{0.12*i+0.15:.2f}s">
        <rect width="{CELL_W}" height="{CELL_H}" rx="14" class="tcell-bg"/>
        <rect width="{CELL_W}" height="{CELL_H}" rx="14" fill="none" stroke="{color}55" stroke-width="1.3"/>
        <text x="16" y="30" font-size="20">{icon}</text>
        <text x="{CELL_W-14}" y="28" text-anchor="end" class="rank-letter" fill="{color}">{rank}</text>
        <text x="16" y="{CELL_H-46}" class="tname">{label}</text>
        <text x="16" y="{CELL_H-28}" class="tsub">{sub}</text>
        <rect x="16" y="{CELL_H-16}" width="{CELL_W-32}" height="4" rx="2" fill="{color}33"/>
        <rect x="16" y="{CELL_H-16}" width="0" height="4" rx="2" fill="{color}" class="tbar" style="--bw:{CELL_W-32}px; animation-delay:{0.12*i+0.5:.2f}s"/>
        <g clip-path="url(#cellClip{i})">
          <rect x="-70" y="0" width="{CELL_H*0.9:.0f}" height="{CELL_H}" class="shine" transform="rotate(18)"/>
        </g>
      </g>
    </g>''')

    clip_defs = "".join(
        f'<clipPath id="cellClip{i}"><rect width="{CELL_W}" height="{CELL_H}" rx="14"/></clipPath>' for i in range(N)
    )

    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="trbg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#1d0e34"/><stop offset="100%" stop-color="#2c1148"/>
  </linearGradient>
  <linearGradient id="trshine" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
    <stop offset="50%" stop-color="#ffffff" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
  </linearGradient>
  <clipPath id="frameTr"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  {clip_defs}
</defs>
<style>
  .tcell-bg {{ fill:url(#trbg); }}
  .tcell {{ opacity:0; transform-origin:{CELL_W/2}px {CELL_H/2}px; animation: popCell 0.55s cubic-bezier(.2,1.3,.4,1) forwards; }}
  @keyframes popCell {{
    0% {{ opacity:0; transform: scale(0.7) translateY(14px); }}
    70% {{ opacity:1; transform: scale(1.04) translateY(-2px); }}
    100% {{ opacity:1; transform: scale(1) translateY(0); }}
  }}
  .rank-letter {{ font-family:'Segoe UI',Arial,sans-serif; font-size:22px; font-weight:800; }}
  .tname {{ font-family:'Segoe UI',Arial,sans-serif; font-size:14px; font-weight:700; fill:#ffffff; }}
  .tsub {{ font-family:'Segoe UI',Arial,sans-serif; font-size:11px; fill:#b79fdb; }}
  .tbar {{ animation: growBar 0.9s cubic-bezier(.2,.8,.2,1) forwards; }}
  @keyframes growBar {{ from {{ width:0; }} to {{ width: var(--bw); }} }}
  .shine {{ fill:url(#trshine); animation: trSweep 3.4s ease-in-out infinite; }}
  @keyframes trSweep {{
    0% {{ transform: rotate(18deg) translateX(-90px); }}
    45% {{ transform: rotate(18deg) translateX(240px); }}
    100% {{ transform: rotate(18deg) translateX(240px); }}
  }}
</style>
<g clip-path="url(#frameTr)">
  <rect width="{W}" height="{H}" fill="url(#trbg)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="#6d3fae55" stroke-width="1.5"/>
{''.join(cells)}
</g>
</svg>'''


# ---------------------------------------------------------------------------
# banner.svg / banner-light.svg - patch just the 4 stat-block values in place
# ---------------------------------------------------------------------------
def patch_banner(path):
    try:
        with open(path) as f:
            svg = f.read()
    except FileNotFoundError:
        print(f"skip {path}: not found")
        return

    new_values = [fmt(D["repos"]), fmt(D["commits"]), fmt(D["stars"]), fmt(D["followers"])]
    pattern = re.compile(r'(class="sb-val">)([^<]*)(</text>)')
    matches = list(pattern.finditer(svg))
    if len(matches) != 4:
        print(f"WARNING: expected 4 sb-val values in {path}, found {len(matches)} - skipping patch to avoid corrupting the file.")
        return

    out = []
    last_end = 0
    for m, val in zip(matches, new_values):
        out.append(svg[last_end:m.start()])
        out.append(m.group(1) + val + m.group(3))
        last_end = m.end()
    out.append(svg[last_end:])
    with open(path, "w") as f:
        f.write("".join(out))
    print(f"patched {path} with {new_values}")


def main():
    with open("stats.svg", "w") as f:
        f.write(render_stats_svg())
    with open("langs.svg", "w") as f:
        f.write(render_langs_svg())
    with open("trophies.svg", "w") as f:
        f.write(render_trophies_svg())
    patch_banner("banner.svg")
    patch_banner("banner-light.svg")
    print("Done - stats.svg, langs.svg, trophies.svg regenerated; banners patched.")


if __name__ == "__main__":
    main()
