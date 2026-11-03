#!/usr/bin/env python3
"""Builds contrib-ripple.svg: an animated version of your GitHub contribution graph.
Reads your PUBLIC contribution calendar (no token needed). Standard library only."""
import argparse, re, sys, time, urllib.request, datetime

SLATE, LINE, L0 = "#2A363B", "#435259", "#34444A"
SAGE, PEACH, CORAL, RED = "#99B898", "#FECEAB", "#FF847C", "#E84A5F"
MUTED, DIM = "#A3B2AB", "#7C8D86"
LEVELS = [L0, SAGE, PEACH, CORAL, RED]


def fetch(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    err = None
    for _ in range(3):
        try:
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        except Exception as e:  # retry a few times
            err = e
            time.sleep(3)
    raise err


def parse(html):
    cells = {}
    for m in re.finditer(
        r'<td[^>]*?data-date="([\d-]+)"[^>]*?id="contribution-day-component-(\d+)-(\d+)"[^>]*?data-level="(\d)"', html
    ):
        date, row, col, level = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        cells[(row, col)] = {"date": date, "level": level, "count": 0}
    for m in re.finditer(
        r'for="contribution-day-component-(\d+)-(\d+)"[^>]*>\s*(No|\d[\d,]*)\s+contribution', html
    ):
        key = (int(m.group(1)), int(m.group(2)))
        if key in cells and m.group(3) != "No":
            cells[key]["count"] = int(m.group(3).replace(",", ""))
    if not cells:
        raise SystemExit("Could not read the contribution calendar.")
    total = None
    t = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", html)
    if t:
        total = int(t.group(1).replace(",", ""))
    return cells, total


def streaks(cells):
    days = sorted(cells.values(), key=lambda c: c["date"])
    active = [d["level"] > 0 or d["count"] > 0 for d in days]
    best = run = 0
    for a in active:
        run = run + 1 if a else 0
        best = max(best, run)
    i = len(active) - 1
    if i >= 0 and not active[i]:
        i -= 1  # today may still be empty
    cur = 0
    while i >= 0 and active[i]:
        cur += 1
        i -= 1
    return best, cur, sum(active)


def build(cells, total):
    ncols = max(c for _, c in cells) + 1
    pitch, size = 16, 12
    gw = ncols * pitch - (pitch - size)
    W, H = 900, 280
    x0, y0 = (W - gw) / 2, 80
    best, cur, active_days = streaks(cells)
    if total is None:
        total = sum(c["count"] for c in cells.values())

    css = f"""
.s{{font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif}}
@keyframes lift{{0%,16%,100%{{transform:translateY(0)}}8%{{transform:translateY(-4px)}}}}
@keyframes sweep{{from{{transform:translateX(-90px)}}to{{transform:translateX({W+10}px)}}}}
@keyframes ring{{0%{{transform:scale(.7);opacity:.85}}65%{{transform:scale(4.4);opacity:0}}100%{{transform:scale(4.4);opacity:0}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.col{{animation:lift 7s ease-in-out infinite}}
.wave{{animation:sweep 7s linear infinite}}
.rp{{transform-box:fill-box;transform-origin:center;animation:ring 6s ease-out infinite;fill:none;stroke-width:1.6}}
.st{{animation:rise .8s ease-out both}}
"""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f"<style>{css}</style>",
           f'<defs><linearGradient id="wv" x1="0" x2="1"><stop offset="0" stop-color="{PEACH}" stop-opacity="0"/>'
           f'<stop offset=".5" stop-color="{PEACH}" stop-opacity=".22"/><stop offset="1" stop-color="{PEACH}" stop-opacity="0"/></linearGradient>'
           f'<clipPath id="pn"><rect width="{W}" height="{H}" rx="14"/></clipPath></defs>',
           f'<g clip-path="url(#pn)"><rect width="{W}" height="{H}" fill="{SLATE}"/>',
           f'<text class="s" x="28" y="36" font-size="16" font-weight="600" fill="{PEACH}">contribution pulse</text>',
           f'<text class="s" x="28" y="55" font-size="12" fill="{DIM}">your last 12 months on GitHub · updates daily</text>']

    # legend
    lx = W - 28 - (5 * 16 + 70)
    out.append(f'<text class="s" x="{lx}" y="40" font-size="11" fill="{DIM}">less</text>')
    for i, col in enumerate(LEVELS):
        out.append(f'<rect x="{lx+30+i*16}" y="30" width="12" height="12" rx="3" fill="{col}"/>')
    out.append(f'<text class="s" x="{lx+30+5*16+4}" y="40" font-size="11" fill="{DIM}">more</text>')

    # month labels
    last_m, last_x = None, -99
    for c in range(ncols):
        cell = next((cells[(r, c)] for r in range(7) if (r, c) in cells), None)
        if not cell:
            continue
        d = datetime.date.fromisoformat(cell["date"])
        if d.month != last_m:
            x = x0 + c * pitch
            if x - last_x >= 40:
                out.append(f'<text class="s" x="{x:.0f}" y="{y0-8}" font-size="10" fill="{DIM}">{d.strftime("%b").lower()}</text>')
                last_x = x
            last_m = d.month

    # grid: one group per column so the whole column lifts as the wave passes
    for c in range(ncols):
        cx = x0 + c * pitch + size / 2
        delay = (cx + 90) / (W + 100) * 7 - 0.55
        out.append(f'<g class="col" style="animation-delay:{delay:.2f}s">')
        for r in range(7):
            cell = cells.get((r, c))
            if not cell:
                continue
            out.append(f'<rect x="{x0+c*pitch:.0f}" y="{y0+r*pitch}" width="{size}" height="{size}" rx="3" fill="{LEVELS[cell["level"]]}"/>')
        out.append("</g>")

    # ripples from every active day
    for (r, c), cell in sorted(cells.items(), key=lambda kv: kv[0][1]):
        if cell["level"] == 0:
            continue
        cx, cy = x0 + c * pitch + size / 2, y0 + r * pitch + size / 2
        col = LEVELS[cell["level"]]
        d1 = ((c * 7 + r * 3) % 10) * 0.6
        for k, d in enumerate((d1, d1 + 3)):
            out.append(f'<circle class="rp" cx="{cx:.1f}" cy="{cy:.1f}" r="7" stroke="{col}" style="animation-delay:-{d:.1f}s"/>')

    out.append(f'<rect class="wave" x="0" y="{y0-12}" width="90" height="{7*pitch+20}" fill="url(#wv)"/>')

    # stats
    out.append(f'<path d="M28 216 H{W-28}" stroke="{LINE}"/>')
    stats = [(total, "contributions"), (active_days, "active days"), (best, "longest streak (days)"), (cur, "current streak (days)")]
    colors = [PEACH, SAGE, CORAL, RED]
    for i, (v, label) in enumerate(stats):
        x = 28 + i * 214
        out.append(f'<g class="st" style="animation-delay:{i*0.15:.2f}s"><text class="s" x="{x}" y="248" font-size="28" font-weight="700" fill="{colors[i]}">{v}</text>'
                   f'<text class="s" x="{x}" y="266" font-size="12" fill="{MUTED}">{label}</text></g>')
    out.append(f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{LINE}"/></svg>')
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="Shrexxx-sys")
    ap.add_argument("--out", default="contrib-ripple.svg")
    ap.add_argument("--html", help="read the calendar from a saved file instead of GitHub (testing)")
    a = ap.parse_args()
    html = open(a.html, encoding="utf-8").read() if a.html else fetch(a.user)
    cells, total = parse(html)
    svg = build(cells, total)
    open(a.out, "w", encoding="utf-8").write(svg)
    print("wrote", a.out, "| days:", len(cells), "| total:", total)
