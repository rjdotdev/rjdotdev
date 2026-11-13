#!/usr/bin/env python3
"""Build the dossier profile assets. Fetches live stats, renders HTML -> PNG via headless Chrome."""
import json, re, os, subprocess, hashlib, math, datetime, urllib.request, base64, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
SRC, OUT, RENDER = ROOT/'_src', ROOT/'assets', ROOT/'_src'/'render'
RENDER.mkdir(exist_ok=True)
UA = {'User-Agent': 'rjdotdev-profile-build'}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode()

# ---------- live data ----------
user = json.loads(get('https://api.github.com/users/rjdotdev'))
html = get('https://github.com/users/rjdotdev/contributions')
cells = {}
for m in re.finditer(r'data-date="([\d-]+)" id="contribution-day-component-(\d+)-(\d+)" data-level="(\d)"', html):
    cells[(int(m[2]), int(m[3]))] = dict(date=m[1], row=int(m[2]), col=int(m[3]), level=int(m[4]), count=0)
for m in re.finditer(r'for="contribution-day-component-(\d+)-(\d+)"[^>]*>([^<]*)', html):
    n = re.match(r'(\d+) contribution', m[3]); k = (int(m[1]), int(m[2]))
    if n and k in cells: cells[k]['count'] = int(n[1])
days = sorted(cells.values(), key=lambda x: x['date'])
json.dump(days, open(OUT/'contrib.json', 'w'), indent=0)
total = sum(d['count'] for d in days); active = sum(1 for d in days if d['count'])
best = max(days, key=lambda d: d['count'])
streak = run = 0
for d in days:
    run = run + 1 if d['count'] else 0; streak = max(streak, run)
repos = {}
for full in ['openclaw/openclaw', 'volcengine/OpenViking', 'elie222/rakazo']:
    repos[full] = json.loads(get(f'https://api.github.com/repos/{full}'))
rk = json.loads(get('https://api.github.com/search/issues?q=repo:elie222/rakazo+is:pr+author:rjdotdev+is:merged&per_page=1'))['total_count']
created = datetime.date.fromisoformat(user['created_at'][:10]); today = datetime.date.today()
months = (today.year - created.year) * 12 + today.month - created.month - (today.day < created.day)
uptime = f"{months//12}Y {months%12}M"
stamp = today.strftime('%Y%m%d')
def kfmt(n): return f"{n/1000:.1f}k".replace('.0k', 'k') if n >= 1000 else str(n)
best_label = datetime.date.fromisoformat(best['date']).strftime('%d %b').upper()
stats = dict(total=total, active=active, best=best, streak=streak, repos=user['public_repos'],
             following=user['following'], followers=user['followers'], uptime=uptime, stamp=stamp, rakazo_merged=rk,
             stars={k: v['stargazers_count'] for k, v in repos.items()})
json.dump(stats, open(OUT/'stats.json', 'w'), indent=1, default=str)
print(stats)

import sys
SVG_ONLY = '--svg-only' in sys.argv
# ---------- avatar ----------
av = b'' if SVG_ONLY else urllib.request.urlopen(urllib.request.Request('https://github.com/rjdotdev.png?size=240', headers=UA), timeout=30).read()
if not SVG_ONLY: open(OUT/'avatar.png', 'wb').write(av)

def b64(p): return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()
BUST, EMBLEM, AVATAR = b64(OUT/'bust.png'), b64(OUT/'emblem.png'), b64(OUT/'avatar.png')

# ---------- palette ----------
NAVY, NAVY2, CREAM, TAN, BROWN, RUST, SLATE = '#1a2136', '#232c47', '#efe2c2', '#c9a46a', '#8a6a3e', '#c95634', '#8b8f9c'
STRIP = ['#3a3f52', '#c9a46a', '#e8b98a', '#efe2c2', '#a7a9b4', '#d98b5f', '#c95634', '#f3d9a4', '#6b7088', '#e9cfa0', '#b48a55', '#d8d2c4']

def barcode(seed, w, h, color):
    hx = hashlib.sha256(seed.encode()).digest() * 12; x = 0; i = 0; bars = []
    while x < w:
        bw = 1 + hx[i] % 3; gap = 1 + hx[i+1] % 3
        if x + bw > w: break
        bars.append(f'<rect x="{x}" y="0" width="{bw}" height="{h}" fill="{color}"/>'); x += bw + gap; i += 2
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(bars)}</svg>'
def wavy(w, h, color, period=10):
    pts = ' '.join(f'{x},{h/2 + (h/2-1)*math.sin(x/period*2*math.pi):.2f}' for x in range(0, w+1))
    return f'<svg width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/></svg>'
def signal(w, h, color):
    pts = []
    for x in range(w + 1):
        t = x / w; f = 1.5 + 9 * t * t; a = (h/2 - 1) * (0.35 + 0.65 * t)
        pts.append(f'{x},{h/2 + a*math.sin(x * f / w * 2 * math.pi * 3):.2f}')
    return f'<svg width="{w}" height="{h}"><polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>'
def strip(w, h):
    seg = w / len(STRIP)
    return f'<svg width="{w}" height="{h}">' + ''.join(f'<rect x="{i*seg:.2f}" y="0" width="{seg+0.5:.2f}" height="{h}" fill="{c}"/>' for i, c in enumerate(STRIP)) + f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" fill="none" stroke="{CREAM}" stroke-opacity=".5"/></svg>'

BASE_CSS = f"""
@font-face{{font-family:S;src:local('Source Serif Pro Semibold'),local('SourceSerifPro-Semibold');font-weight:600}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:transparent;-webkit-font-smoothing:antialiased}}
body{{font-family:'IBM Plex Mono',monospace;color:{CREAM}}}
.serif{{font-family:'Source Serif Pro',serif}}
.mono{{font-family:'IBM Plex Mono',monospace}}
.frame{{position:relative;overflow:hidden}}
.light .frame{{background:{NAVY};border-radius:18px}}
.light .frame:after{{content:'';position:absolute;inset:9px;border:1px solid rgba(239,226,194,.28);border-radius:11px;pointer-events:none}}
.lbl{{font-size:10px;letter-spacing:.28em;text-transform:uppercase;color:{TAN}}}
.row{{display:flex;align-items:baseline;gap:10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;line-height:21px}}
.row .k{{color:{CREAM};font-weight:600;white-space:nowrap}}
.row .lead{{flex:1;border-bottom:1px solid rgba(239,226,194,.30);transform:translateY(-4px)}}
.row .v{{color:{CREAM};text-transform:none;letter-spacing:.04em;white-space:nowrap}}
"""

def page(body, w, h, mode):
    return f"<!doctype html><html><head><meta charset=utf-8><style>{BASE_CSS}</style></head><body class='{mode}' style='width:{w}px;height:{h}px'>{body}</body></html>"

def hero(mode):
    W, H = 900, 520
    rows = [('Name', 'Suryaansh A. Jha (RJ)'), ('Handle', 'github.com/rjdotdev'), ('Signal', 'x.com/shinchanBOI01'), ('Focus', 'agents · TypeScript')]
    rows_html = ''.join(f"<div class='row'><span class='k'>{k}</span><span class='lead'></span><span class='v'>{v}</span></div>" for k, v in rows)
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='serif' style='position:absolute;left:150px;top:96px;font-family:"Noto Serif CJK JP";font-weight:600;font-size:400px;line-height:1;color:rgba(201,164,106,.13)'>動</div>
  <img src='{BUST}' style='position:absolute;right:6px;top:8px;height:{H-8}px'>
  <div style='position:absolute;right:20px;top:228px;width:420px;height:7px;background:linear-gradient(90deg,rgba(239,226,194,0),rgba(239,226,194,.55) 40%,rgba(239,226,194,.15) 80%,rgba(239,226,194,0));mix-blend-mode:screen'></div>
  <div style='position:absolute;right:20px;top:238px;width:300px;height:2px;background:linear-gradient(90deg,rgba(239,226,194,0),rgba(239,226,194,.4),rgba(239,226,194,0))'></div>
  <div class='lbl' style='position:absolute;left:24px;top:40px;bottom:40px;writing-mode:vertical-rl;transform:rotate(180deg);text-align:center;white-space:nowrap;letter-spacing:.2em;font-size:9px;color:rgba(239,226,194,.55)'>Suryaansh A. Jha &nbsp;·&nbsp; build {stamp[:4]}.{stamp[4:6]} &nbsp;·&nbsp; software that acts</div>
  <div class='lbl' style='position:absolute;left:62px;top:38px'>· profile dossier</div>
  <!-- wordmark is composited per-frame by _src/kinetic.py -->
  <div class='serif' style='position:absolute;left:60px;top:96px;font-weight:700;font-size:72px;line-height:1;color:{TAN};letter-spacing:-1px'>rj</div>
  <div class='mono' style='position:absolute;left:62px;top:196px;font-size:13px;color:{CREAM};letter-spacing:.06em'>@rjdotdev &nbsp;·</div>
  <div class='serif' style='position:absolute;left:62px;top:218px;font-style:italic;font-weight:600;font-size:20px;color:{CREAM}'>Building agentic tools — software that acts.</div>
  <div style='position:absolute;left:62px;top:250px;width:6px;height:6px;border-radius:50%;background:{TAN}'></div>
  <div style='position:absolute;left:62px;top:300px;width:350px'>{rows_html}</div>
  <div style='position:absolute;left:62px;top:396px'>{wavy(350, 10, TAN)}</div>
  <div class='mono' style='position:absolute;left:62px;top:414px;font-size:11px;letter-spacing:.12em;color:{CREAM}'>{total} CONTRIB · {active} ACTIVE DAYS · {user['public_repos']} PUBLIC REPOS</div>
  <div style='position:absolute;left:62px;top:436px'>{strip(350, 12)}</div>
  <div style='position:absolute;left:62px;top:454px'>{barcode('rjdotdev'+stamp, 350, 24, TAN)}</div>
  <div class='lbl' style='position:absolute;left:62px;top:484px;font-size:9px;color:{CREAM}'>RJDOTDEV-{stamp}</div>
  <div class='lbl' style='position:absolute;right:186px;top:458px;font-size:9px'>signal</div>
  <div style='position:absolute;right:30px;top:472px'>{signal(196, 24, TAN)}</div>
  <div class='lbl' style='position:absolute;right:30px;top:458px;font-size:9px;color:{CREAM}'>uptime {uptime}</div>
</div>""", W, H, mode), W, H

def fastfetch(mode):
    W, H = 900, 330
    info = [('Host', 'Suryaansh A. Jha (RJ)'), ('OS', 'agent tooling / TypeScript'), ('Shell', 'zsh · browsers · sandboxes'),
            ('Stack', 'TS · Node · Python · agents'), ('Repos', f"{user['public_repos']} public"),
            ('Contrib', f"{total} · last year"), ('Streak', f"{streak} days · best {best['count']} on {best_label.title()}"),
            ('Uptime', f"{uptime.lower()} on GitHub")]
    rows = ''.join(f"<div class='row' style='line-height:22px'><span class='k' style='width:74px;color:{TAN}'>{k}</span><span class='v'>{v}</span></div>" for k, v in info)
    blocks = ''.join(f"<span style='display:inline-block;width:26px;height:14px;background:{c}'></span>" for c in STRIP[:10])
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='mono' style='position:absolute;left:40px;top:28px;font-size:13px;color:{CREAM}'><span style='color:{TAN}'>rj@github</span> <span style='opacity:.5'>~</span> $ fastfetch</div>
  <img src='{EMBLEM}' style='position:absolute;left:66px;top:58px;height:258px'>
  <div style='position:absolute;left:330px;top:62px;width:520px'>
    <div style='display:flex;align-items:center;gap:14px;margin-bottom:8px'>
      <img src='{AVATAR}' style='width:42px;height:42px;border-radius:50%;border:1px solid {TAN};object-fit:cover'>
      <div><div class='serif' style='font-weight:700;font-size:24px;line-height:1;color:{CREAM}'>rj<span style='color:{TAN}'>@</span>github</div>
      <div class='lbl' style='font-size:9px;margin-top:4px'>specimen · rjdotdev · {stamp}</div></div>
    </div>
    <div style='border-top:1px solid rgba(239,226,194,.3);margin:6px 0 8px;width:440px'></div>
    {rows}
    <div style='margin-top:12px;font-size:0'>{blocks}</div>
  </div>
  <div style='position:absolute;right:34px;top:30px'>{barcode('ff'+stamp, 120, 14, 'rgba(201,164,106,.8)')}</div>
</div>""", W, H, mode), W, H

PROJ = [
    ('01', 'openclaw', 'openclaw/openclaw', 'The AI that really does things.<br>Any OS, any platform.', None),
    ('02', 'OpenViking', 'volcengine/OpenViking', 'Self-evolving context database<br>for AI agents.', None),
    ('03', 'rakazo', 'elie222/rakazo', 'Open-source agent you run your way —<br>pick your own model &amp; sandbox.', f'{rk} merged'),
]
def card(i, mode):
    idx, name, full, desc, extra = PROJ[i]; W, H = 292, 168
    meta = f"★ {kfmt(stats['stars'][full])}" + (f" &nbsp;·&nbsp; {extra}" if extra else '')
    border = '' if mode == 'light' else f"border-top:1px solid rgba(239,226,194,.45);"
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div style='position:absolute;left:20px;right:20px;top:18px;{border}padding-top:12px;display:flex;justify-content:space-between'>
    <span class='lbl' style='font-size:9px'>{idx} / ls ./public</span>
    {barcode(name, 54, 10, 'rgba(201,164,106,.75)')}
  </div>
  <div class='serif' style='position:absolute;left:20px;top:50px;font-weight:600;font-size:32px;color:{CREAM};letter-spacing:-.5px'>{name}<span style='color:{TAN}'>/</span></div>
  <div class='mono' style='position:absolute;left:20px;top:94px;font-size:11px;line-height:16px;color:rgba(239,226,194,.82)'>{desc}</div>
  <div class='lbl' style='position:absolute;left:20px;bottom:16px;font-size:9px;letter-spacing:.18em;color:{CREAM}'>{meta}</div>
  <div class='lbl' style='position:absolute;right:20px;bottom:16px;font-size:9px;letter-spacing:.18em'>{full.split('/')[0]} ↗</div>
</div>""", W, H, mode), W, H

def footer(mode):
    W, H = 900, 96
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div style='position:absolute;left:40px;right:40px;top:30px'>{wavy(820, 8, 'rgba(201,164,106,.7)', 14)}</div>
  <div style='position:absolute;left:40px;top:52px'>{barcode('end'+stamp, 240, 18, TAN)}</div>
  <div class='lbl' style='position:absolute;left:300px;top:56px;font-size:10px;color:{CREAM}'>end of dossier · status: building software that acts</div>
  <div class='lbl' style='position:absolute;right:40px;top:56px;font-size:10px'>● online</div>
</div>""", W, H, mode), W, H

def heatmap_svg(mode):
    cell, gap = 12, 3; cols = max(d['col'] for d in days) + 1
    left, top = 40, 66; W = left + cols * (cell + gap) + 30; H = top + 7 * (cell + gap) + 44
    lv = ['rgba(239,226,194,0.07)', '#5b4a31', '#8a6a3e', '#c9a46a', '#f1e3bf']
    parts = []
    if mode == 'light':
        parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="18" fill="{NAVY}"/><rect x="9.5" y="9.5" width="{W-19}" height="{H-19}" rx="11" fill="none" stroke="{CREAM}" stroke-opacity=".28"/>')
    else:
        pass  # dark: fully transparent, no tint
    F = "font-family=\"'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace\""
    parts.append(f'<text x="{left}" y="34" {F} font-size="13" fill="{CREAM}"><tspan fill="{TAN}">rj@github</tspan><tspan fill-opacity=".5"> ~</tspan> $ contrib --calendar</text>')
    parts.append(f'<text x="{W-30}" y="34" text-anchor="end" {F} font-size="10" letter-spacing="2.4" fill="{TAN}">{total} CONTRIBUTIONS · LAST YEAR</text>')
    seen = set()
    for d in days:
        x = left + d['col'] * (cell + gap); y = top + d['row'] * (cell + gap)
        mo = d['date'][:7]
        if d['row'] == 0 and mo not in seen and int(d['date'][8:]) <= 7:
            seen.add(mo); parts.append(f'<text x="{x}" y="{top-10}" {F} font-size="9" letter-spacing="1.5" fill="{CREAM}" fill-opacity=".6">{datetime.date.fromisoformat(d["date"]).strftime("%b").upper()}</text>')
        tip = f"{d['count']} contribution{'s' if d['count']!=1 else ''} on {d['date']}"
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{lv[d["level"]]}"><title>{tip}</title></rect>')
    for r, lab in [(1, 'MON'), (3, 'WED'), (5, 'FRI')]:
        parts.append(f'<text x="{left-8}" y="{top + r*(cell+gap) + 9}" text-anchor="end" {F} font-size="8" fill="{CREAM}" fill-opacity=".45">{lab}</text>')
    by = top + 7 * (cell + gap) + 22
    parts.append(f'<text x="{left}" y="{by}" {F} font-size="10" letter-spacing="1.6" fill="{CREAM}">{active} ACTIVE DAYS · LONGEST STREAK {streak} · BEST DAY {best["count"]} ({best_label})</text>')
    lx = W - 30 - 5 * (cell + gap) - 70
    parts.append(f'<text x="{lx}" y="{by}" {F} font-size="9" letter-spacing="1.5" fill="{CREAM}" fill-opacity=".6">LESS</text>')
    for i, c in enumerate(lv):
        parts.append(f'<rect x="{lx + 34 + i*(cell+gap)}" y="{by-10}" width="{cell}" height="{cell}" fill="{c}"/>')
    parts.append(f'<text x="{lx + 34 + 5*(cell+gap) + 4}" y="{by}" {F} font-size="9" letter-spacing="1.5" fill="{CREAM}" fill-opacity=".6">MORE</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year">' + ''.join(parts) + '</svg>'

def chrome_bin():
    import shutil
    env = os.environ.get('CHROME')
    cands = ([env] if env else []) + [
        'google-chrome-stable', 'google-chrome',
        '/opt/google/chrome/google-chrome', 'chromium', 'chromium-browser']
    for c in cands:
        if not c:
            continue
        path = c if (os.path.isabs(c) and os.access(c, os.X_OK)) else shutil.which(c)
        if path:
            return path
    raise SystemExit('headless Chrome not found (install google-chrome-stable or set CHROME)')

def install_fonts():
    """Register the vendored faces with fontconfig so Chrome matches the panel CSS."""
    dest = pathlib.Path.home() / '.local/share/fonts/rjdotdev-profile'
    dest.mkdir(parents=True, exist_ok=True)
    fonts = [p for p in (SRC/'fonts').iterdir() if p.suffix.lower() in {'.ttf', '.otf', '.ttc', '.otc'}]
    if not fonts:
        raise SystemExit('missing font files in _src/fonts')
    for src in fonts:
        data = src.read_bytes(); target = dest/src.name
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    subprocess.run(['fc-cache', '-f', str(dest)], check=True)
    expect = {
        'IBM Plex Mono': 'IBMPlexMono-Regular',
        'IBM Plex Mono:weight=600': 'IBMPlexMono-SemiBold',
        'Source Serif Pro:weight=700': 'SourceSerifPro-Bold',
        'Source Serif Pro:weight=600:italic': 'SourceSerifPro-SemiboldIt',
        'Noto Serif CJK JP:weight=600': 'NotoSerifCJKjp-SemiBold',
    }
    for spec, name in expect.items():
        out = subprocess.run(['fc-match', '-f', '%{file}', spec], check=True, capture_output=True, text=True).stdout
        if name not in out:
            raise SystemExit(f'fontconfig resolved {spec} to {out}, expected {name}')

def shoot(name, built):
    htmlsrc, w, h = built
    p = RENDER / f'{name}.html'; p.write_text(htmlsrc)
    subprocess.run([chrome_bin(), '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                    '--default-background-color=00000000', f'--window-size={w},{h}', f'--screenshot={OUT/(name+".png")}', p.as_uri()],
                   check=True, capture_output=True)
    from PIL import Image
    f = OUT/(name+'.png'); im = Image.open(f).convert('RGBA')
    if name.endswith('-light'):  # opaque navy cards: palette PNG is lossless-looking and ~6x smaller
        im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(f, optimize=True)
    else:  # transparent art: keep truecolor alpha
        im.save(f, optimize=True, compress_level=9)
    print('rendered', name)

if not SVG_ONLY:
    install_fonts()
    print('chrome', chrome_bin())
for mode in ['dark', 'light']:
    (OUT / f'contrib-{mode}.svg').write_text(heatmap_svg(mode))
    if SVG_ONLY: continue
    shoot(f'hero-{mode}-base', hero(mode))
    import kinetic; kinetic.build(OUT/f'hero-{mode}-base.png', OUT/f'hero-{mode}.png', CREAM)
    (OUT/'alt').mkdir(exist_ok=True)   # optional: same motion, wordmark at full ink instead of the 0.2 ghost
    kinetic.build(OUT/f'hero-{mode}-base.png', OUT/'alt'/f'hero-{mode}-solid.png', CREAM, text_a=1.0)
    (OUT/f'hero-{mode}-base.png').replace(RENDER/f'hero-{mode}-base.png')
    shoot(f'fastfetch-{mode}', fastfetch(mode))
    shoot(f'footer-{mode}', footer(mode))
    for i in range(3): shoot(f'public-{PROJ[i][1].lower()}-{mode}', card(i, mode))
print('done')
