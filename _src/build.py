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
OFFLINE = '--offline' in sys.argv
SVG_ONLY = '--svg-only' in sys.argv
LIGHT_ONLY = '--light-only' in sys.argv
DARK_ONLY = '--dark-only' in sys.argv
SKIP_HERO = '--skip-hero' in sys.argv

if OFFLINE and (OUT/'stats.json').exists() and (OUT/'contrib.json').exists():
    stats = json.load(open(OUT/'stats.json'))
    days = json.load(open(OUT/'contrib.json'))
    total, active, streak = stats['total'], stats['active'], stats['streak']
    best = stats['best']; rk = stats['rakazo_merged']; stamp = stats['stamp']; uptime = stats['uptime']
    user = dict(public_repos=stats['repos'], following=stats['following'], followers=stats['followers'])
    print('offline stats', stats)
else:
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
    stats = dict(total=total, active=active, best=best, streak=streak, repos=user['public_repos'],
                 following=user['following'], followers=user['followers'], uptime=uptime, stamp=stamp, rakazo_merged=rk,
                 stars={k: v['stargazers_count'] for k, v in repos.items()})
    json.dump(stats, open(OUT/'stats.json', 'w'), indent=1, default=str)
    print(stats)

def kfmt(n): return f"{n/1000:.1f}k".replace('.0k', 'k') if n >= 1000 else str(n)
best_label = datetime.date.fromisoformat(best['date']).strftime('%d %b').upper()

# ---------- avatar ----------
av = b'' if SVG_ONLY else urllib.request.urlopen(urllib.request.Request('https://github.com/rjdotdev.png?size=240', headers=UA), timeout=30).read() if not OFFLINE else open(OUT/'avatar.png','rb').read()
if not SVG_ONLY and not OFFLINE: open(OUT/'avatar.png', 'wb').write(av)

def b64(p): return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()
BUST, EMBLEM, AVATAR = b64(OUT/'bust.png'), b64(OUT/'emblem.png'), b64(OUT/'avatar.png')
# Light panels: soft charcoal/sepia sculpture designed for paper (not an invert of cream bust)
BUST_LIGHT = b64(OUT/'bust-light.png') if (OUT/'bust-light.png').exists() else BUST
EMBLEM_LIGHT = b64(OUT/'emblem-light.png') if (OUT/'emblem-light.png').exists() else EMBLEM

# ---------- palette ----------
# Dark: cream ink on transparent (sits on GitHub dark #0d1117)
# Light: warm charcoal/sepia ink on cream paper (matches approved hero sculpture)
NAVY, NAVY2, CREAM, TAN, BROWN, RUST, SLATE = '#1a2136', '#232c47', '#efe2c2', '#c9a46a', '#8a6a3e', '#c95634', '#8b8f9c'
PAPER, PAPER2 = '#f4ecdf', '#ebe3d4'          # warm dossier stock
INK = '#2f2922'                               # warm charcoal (hero family), not cold navy
MUTED = '#6a5f52'                             # soft taupe secondary
ACCENT_L = '#a67c3d'                          # restrained tan, readable on paper
RUST_L = '#b45a3a'                            # muted rust accent for paper
STRIP = ['#3a3f52', '#c9a46a', '#e8b98a', '#efe2c2', '#a7a9b4', '#d98b5f', '#c95634', '#f3d9a4', '#6b7088', '#e9cfa0', '#b48a55', '#d8d2c4']
STRIP_L = ['#3a3228', '#a67c3d', '#c9a46a', '#d8c49a', '#8b8478', '#c9845a', '#b45a3a', '#e0c48a', '#6b6458', '#d4c4a0', '#8a6a3e', '#b8aea0']

def theme(mode):
    if mode == 'light':
        return dict(
            mode='light', paper=PAPER, ink=INK, muted=MUTED, accent=ACCENT_L, cream=CREAM, rust=RUST_L,
            ink_soft='rgba(47,41,34,.72)', ink_faint='rgba(47,41,34,.48)',
            line='rgba(47,41,34,.20)', line_soft='rgba(47,41,34,.11)',
            strip=STRIP_L, kinetic=INK,
            # heatmap: paper-empty → tan → rust-brown → deep sepia (clear steps on cream)
            heat=['#ddd3c2', '#c9b48a', '#a67c3d', '#7a5a32', '#3a2a18'],
        )
    return dict(
        mode='dark', paper='transparent', ink=CREAM, muted='rgba(239,226,194,.78)', accent=TAN, cream=CREAM,
        ink_soft='rgba(239,226,194,.82)', ink_faint='rgba(239,226,194,.55)',
        line='rgba(239,226,194,.30)', line_soft='rgba(239,226,194,.18)',
        strip=STRIP, kinetic=CREAM,
        heat=['rgba(239,226,194,0.07)', '#5b4a31', '#8a6a3e', '#c9a46a', '#f1e3bf'],
    )

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
def strip(w, h, t):
    colors = t['strip']; seg = w / len(colors)
    stroke = t['ink'] if t['mode'] == 'light' else CREAM
    op = '.28' if t['mode'] == 'light' else '.5'
    return f'<svg width="{w}" height="{h}">' + ''.join(f'<rect x="{i*seg:.2f}" y="0" width="{seg+0.5:.2f}" height="{h}" fill="{c}"/>' for i, c in enumerate(colors)) + f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" fill="none" stroke="{stroke}" stroke-opacity="{op}"/></svg>'

def base_css(t):
    frame_light = f".light .frame{{background:{t['paper']};border-radius:18px;box-shadow:0 1px 2px rgba(47,41,34,.07)}}" if t['mode']=='light' else ".light .frame{}"
    frame_after = f".light .frame:after{{content:'';position:absolute;inset:9px;border:1px solid {t['line']};border-radius:11px;pointer-events:none}}" if t['mode']=='light' else ""
    return f"""
@font-face{{font-family:S;src:local('Source Serif Pro Semibold'),local('SourceSerifPro-Semibold');font-weight:600}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:transparent;-webkit-font-smoothing:antialiased}}
body{{font-family:'IBM Plex Mono',monospace;color:{t['ink']}}}
.serif{{font-family:'Source Serif Pro',serif}}
.mono{{font-family:'IBM Plex Mono',monospace}}
.frame{{position:relative;overflow:hidden}}
{frame_light}
{frame_after}
.lbl{{font-size:10px;letter-spacing:.28em;text-transform:uppercase;color:{t['accent']}}}
.row{{display:flex;align-items:baseline;gap:10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;line-height:21px}}
.row .k{{color:{t['ink']};font-weight:600;white-space:nowrap}}
.row .lead{{flex:1;border-bottom:1px solid {t['line']};transform:translateY(-4px)}}
.row .v{{color:{t['ink']};text-transform:none;letter-spacing:.04em;white-space:nowrap}}
"""

def page(body, w, h, mode):
    t = theme(mode)
    return f"<!doctype html><html><head><meta charset=utf-8><style>{base_css(t)}</style></head><body class='{mode}' style='width:{w}px;height:{h}px'>{body}</body></html>"

def hero(mode):
    t = theme(mode); W, H = 900, 620
    rows = [('Name', 'Suryaansh A. Jha (RJ)'), ('Handle', 'github.com/rjdotdev'), ('Signal', 'x.com/shinchanBOI01'),
            ('Focus', 'agents · TypeScript'), ('Stage', 'early builder · public tools')]
    rows_html = ''.join(f"<div class='row'><span class='k'>{k}</span><span class='lead'></span><span class='v'>{v}</span></div>" for k, v in rows)
    # light: soft ink wash (no screen blend). dark: keep cream light streaks with screen.
    if mode == 'light':
        wash = f"""
  <div style='position:absolute;right:20px;top:248px;width:420px;height:7px;background:linear-gradient(90deg,rgba(26,33,54,0),rgba(26,33,54,.18) 40%,rgba(26,33,54,.06) 80%,rgba(26,33,54,0))'></div>
  <div style='position:absolute;right:20px;top:258px;width:300px;height:2px;background:linear-gradient(90deg,rgba(26,33,54,0),rgba(26,33,54,.14),rgba(26,33,54,0))'></div>"""
        kanji = f'rgba(26,33,54,.08)'
        spine = t['ink_faint']
    else:
        wash = f"""
  <div style='position:absolute;right:20px;top:248px;width:420px;height:7px;background:linear-gradient(90deg,rgba(239,226,194,0),rgba(239,226,194,.55) 40%,rgba(239,226,194,.15) 80%,rgba(239,226,194,0));mix-blend-mode:screen'></div>
  <div style='position:absolute;right:20px;top:258px;width:300px;height:2px;background:linear-gradient(90deg,rgba(239,226,194,0),rgba(239,226,194,.4),rgba(239,226,194,0))'></div>"""
        kanji = 'rgba(201,164,106,.13)'
        spine = 'rgba(239,226,194,.55)'
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='serif' style='position:absolute;left:150px;top:110px;font-family:"Noto Serif CJK JP";font-weight:600;font-size:440px;line-height:1;color:{kanji}'>動</div>
  <img src='{BUST_LIGHT if mode == "light" else BUST}' style='position:absolute;right:6px;top:18px;height:{H-26}px'>
  {wash}
  <div class='lbl' style='position:absolute;left:24px;top:48px;bottom:48px;writing-mode:vertical-rl;transform:rotate(180deg);text-align:center;white-space:nowrap;letter-spacing:.2em;font-size:9px;color:{spine}'>Suryaansh A. Jha &nbsp;·&nbsp; build {stamp[:4]}.{stamp[4:6]} &nbsp;·&nbsp; software that acts</div>
  <div class='lbl' style='position:absolute;left:62px;top:42px'>· profile dossier</div>
  <!-- wordmark is composited per-frame by _src/kinetic.py -->
  <div class='serif' style='position:absolute;left:60px;top:108px;font-weight:700;font-size:78px;line-height:1;color:{t["accent"]};letter-spacing:-1px'>rj</div>
  <div class='mono' style='position:absolute;left:62px;top:214px;font-size:13px;color:{t["ink"]};letter-spacing:.06em'>@rjdotdev &nbsp;·</div>
  <div class='serif' style='position:absolute;left:62px;top:238px;font-style:italic;font-weight:600;font-size:22px;color:{t["ink"]}'>Building agentic tools - software that acts.</div>
  <div style='position:absolute;left:62px;top:274px;width:6px;height:6px;border-radius:50%;background:{t["accent"]}'></div>
  <div style='position:absolute;left:62px;top:318px;width:360px'>{rows_html}</div>
  <div style='position:absolute;left:62px;top:448px'>{wavy(360, 10, t["accent"])}</div>
  <div class='mono' style='position:absolute;left:62px;top:468px;font-size:12px;letter-spacing:.12em;color:{t["ink"]}'>{total} CONTRIB · {active} ACTIVE DAYS · {user['public_repos']} PUBLIC REPOS</div>
  <div class='mono' style='position:absolute;left:62px;top:490px;font-size:11px;letter-spacing:.1em;color:{t["ink_soft"]}'>STREAK {streak} · BEST {best['count']} ({best_label}) · RAKAZO {rk} MERGED</div>
  <div style='position:absolute;left:62px;top:516px'>{strip(360, 12, t)}</div>
  <div style='position:absolute;left:62px;top:536px'>{barcode('rjdotdev'+stamp, 360, 28, t["accent"])}</div>
  <div class='lbl' style='position:absolute;left:62px;top:576px;font-size:9px;color:{t["ink"]}'>RJDOTDEV-{stamp}</div>
  <div class='lbl' style='position:absolute;right:186px;top:548px;font-size:9px'>signal</div>
  <div style='position:absolute;right:30px;top:562px'>{signal(196, 28, t["accent"])}</div>
  <div class='lbl' style='position:absolute;right:30px;top:548px;font-size:9px;color:{t["ink"]}'>uptime {uptime}</div>
</div>""", W, H, mode), W, H

def fastfetch(mode):
    t = theme(mode); W, H = 900, 420
    info = [('Host', 'Suryaansh A. Jha (RJ)'), ('OS', 'agent tooling / TypeScript'), ('Shell', 'zsh · browsers · sandboxes'),
            ('Stack', 'TS · Node · Python · agents'), ('Repos', f"{user['public_repos']} public"),
            ('Contrib', f"{total} · last year"), ('Streak', f"{streak} days · best {best['count']} on {best_label.title()}"),
            ('Merged', f"{rk} on elie222/rakazo"), ('Uptime', f"{uptime.lower()} on GitHub"),
            ('Mode', 'early builder · agentic tools')]
    rows = ''.join(f"<div class='row' style='line-height:24px'><span class='k' style='width:78px;color:{t['accent']}'>{k}</span><span class='v'>{v}</span></div>" for k, v in info)
    blocks = ''.join(f"<span style='display:inline-block;width:28px;height:16px;background:{c}'></span>" for c in t['strip'][:10])
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='mono' style='position:absolute;left:40px;top:30px;font-size:14px;color:{t["ink"]}'><span style='color:{t["accent"]}'>rj@github</span> <span style='opacity:.5'>~</span> $ fastfetch</div>
  <img src='{EMBLEM_LIGHT if mode == "light" else EMBLEM}' style='position:absolute;left:58px;top:72px;height:310px'>
  <div style='position:absolute;left:330px;top:68px;width:530px'>
    <div style='display:flex;align-items:center;gap:14px;margin-bottom:10px'>
      <img src='{AVATAR}' style='width:48px;height:48px;border-radius:50%;border:1px solid {t["accent"]};object-fit:cover'>
      <div><div class='serif' style='font-weight:700;font-size:26px;line-height:1;color:{t["ink"]}'>rj<span style='color:{t["accent"]}'>@</span>github</div>
      <div class='lbl' style='font-size:9px;margin-top:5px'>specimen · rjdotdev · {stamp}</div></div>
    </div>
    <div style='border-top:1px solid {t["line"]};margin:8px 0 10px;width:460px'></div>
    {rows}
    <div style='margin-top:16px;font-size:0'>{blocks}</div>
  </div>
  <div style='position:absolute;right:34px;top:32px'>{barcode('ff'+stamp, 140, 16, t["accent"])}</div>
</div>""", W, H, mode), W, H

PROJ = [
    ('01', 'openclaw', 'openclaw/openclaw', 'The AI that really does things.<br>Any OS, any platform.', None),
    ('02', 'OpenViking', 'volcengine/OpenViking', 'Self-evolving context database<br>for AI agents.', None),
    ('03', 'rakazo', 'elie222/rakazo', 'Open-source agent you run your way.<br>Pick your own model &amp; sandbox.', f'{rk} merged'),
]
def card(i, mode):
    t = theme(mode); idx, name, full, desc, extra = PROJ[i]; W, H = 292, 220
    meta = f"★ {kfmt(stats['stars'][full])}" + (f" &nbsp;·&nbsp; {extra}" if extra else '')
    if mode == 'light':
        border = f"border-top:1px solid {t['line']};"
        owner_c = t['muted']
    else:
        border = "border-top:1px solid rgba(239,226,194,.45);"
        owner_c = t['accent']
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div style='position:absolute;left:20px;right:20px;top:22px;{border}padding-top:14px;display:flex;justify-content:space-between'>
    <span class='lbl' style='font-size:9px'>{idx} / ls ./public</span>
    {barcode(name, 64, 12, t["accent"])}
  </div>
  <div class='serif' style='position:absolute;left:20px;top:62px;font-weight:600;font-size:34px;color:{t["ink"]};letter-spacing:-.5px'>{name}<span style='color:{t["accent"]}'>/</span></div>
  <div class='mono' style='position:absolute;left:20px;top:112px;right:20px;font-size:12px;line-height:18px;color:{t["ink_soft"]}'>{desc}</div>
  <div style='position:absolute;left:20px;bottom:48px;right:20px'>{wavy(252, 8, t["accent"], 12)}</div>
  <div class='lbl' style='position:absolute;left:20px;bottom:22px;font-size:9px;letter-spacing:.18em;color:{t["ink"]}'>{meta}</div>
  <div class='lbl' style='position:absolute;right:20px;bottom:22px;font-size:9px;letter-spacing:.18em;color:{owner_c}'>{full.split('/')[0]} ↗</div>
</div>""", W, H, mode), W, H

def footer(mode):
    t = theme(mode); W, H = 900, 160
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='lbl' style='position:absolute;left:40px;top:28px;font-size:10px;letter-spacing:.28em'>· transmission end</div>
  <div class='lbl' style='position:absolute;right:40px;top:28px;font-size:10px;color:{t["ink"]}'>RJDOTDEV-{stamp}</div>
  <div style='position:absolute;left:40px;right:40px;top:52px'>{wavy(820, 10, t["accent"], 14)}</div>
  <div style='position:absolute;left:40px;top:78px'>{barcode('end'+stamp, 280, 22, t["accent"])}</div>
  <div style='position:absolute;left:340px;top:78px'>{strip(240, 22, t)}</div>
  <div style='position:absolute;right:40px;top:78px'>{signal(200, 22, t["accent"])}</div>
  <div class='lbl' style='position:absolute;left:40px;top:116px;font-size:11px;color:{t["ink"]}'>end of dossier · status: building software that acts</div>
  <div class='lbl' style='position:absolute;left:40px;top:136px;font-size:10px;letter-spacing:.16em;color:{t["ink_soft"]}'>github.com/rjdotdev · x.com/shinchanBOI01</div>
  <div class='lbl' style='position:absolute;right:40px;top:124px;font-size:11px;color:{t.get("rust", t["accent"])}'>● online</div>
</div>""", W, H, mode), W, H


def telemetry(mode):
    """Full-width status strip. Densifies the overview column between projects and heatmap."""
    t = theme(mode); W, H = 900, 150
    metrics = [
        (str(total), 'CONTRIB'),
        (str(active), 'ACTIVE'),
        (str(streak), 'STREAK'),
        (str(best['count']), 'BEST DAY'),
        (str(rk), 'RAKAZO'),
        (str(user['public_repos']), 'REPOS'),
        (uptime, 'UPTIME'),
    ]
    parts = []
    for i, (v, lab) in enumerate(metrics):
        br = f"border-right:1px solid {t['line_soft']};" if i < len(metrics) - 1 else ""
        parts.append(
            f"<div style='flex:1;text-align:center;{br}padding:8px 4px'>"
            f"<div class='serif' style='font-weight:700;font-size:28px;line-height:1;color:{t['ink']}'>{v}</div>"
            f"<div class='lbl' style='margin-top:10px;font-size:9px;letter-spacing:.22em'>{lab}</div></div>"
        )
    cells = ''.join(parts)
    return page(f"""
<div class='frame' style='width:{W}px;height:{H}px'>
  <div class='mono' style='position:absolute;left:40px;top:22px;font-size:13px;color:{t["ink"]}'><span style='color:{t["accent"]}'>rj@github</span> <span style='opacity:.5'>~</span> $ status --telemetry</div>
  <div style='position:absolute;right:40px;top:24px'>{barcode('tel'+stamp, 160, 12, t["accent"])}</div>
  <div style='position:absolute;left:28px;right:28px;top:58px;display:flex;align-items:stretch'>{cells}</div>
  <div style='position:absolute;left:40px;right:40px;bottom:22px'>{strip(820, 8, t)}</div>
</div>""", W, H, mode), W, H

def heatmap_svg(mode):
    t = theme(mode)
    cell, gap = 14, 4; cols = max(d['col'] for d in days) + 1
    left, top = 44, 78; W = left + cols * (cell + gap) + 36; H = top + 7 * (cell + gap) + 56
    lv = t['heat']
    parts = []
    if mode == 'light':
        parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="18" fill="{t["paper"]}"/>'
                     f'<rect x="9.5" y="9.5" width="{W-19}" height="{H-19}" rx="11" fill="none" stroke="{t["ink"]}" stroke-opacity=".18"/>')
    else:
        pass  # dark: fully transparent, no tint
    F = "font-family=\"'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace\""
    parts.append(f'<text x="{left}" y="38" {F} font-size="14" fill="{t["ink"]}"><tspan fill="{t["accent"]}">rj@github</tspan><tspan fill-opacity=".5"> ~</tspan> $ contrib --calendar</text>')
    parts.append(f'<text x="{W-36}" y="38" text-anchor="end" {F} font-size="11" letter-spacing="2.4" fill="{t["accent"]}">{total} CONTRIBUTIONS · LAST YEAR</text>')
    seen = set()
    for d in days:
        x = left + d['col'] * (cell + gap); y = top + d['row'] * (cell + gap)
        mo = d['date'][:7]
        if d['row'] == 0 and mo not in seen and int(d['date'][8:]) <= 7:
            seen.add(mo); parts.append(f'<text x="{x}" y="{top-10}" {F} font-size="9" letter-spacing="1.5" fill="{t["ink"]}" fill-opacity=".55">{datetime.date.fromisoformat(d["date"]).strftime("%b").upper()}</text>')
        tip = f"{d['count']} contribution{'s' if d['count']!=1 else ''} on {d['date']}"
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{lv[d["level"]]}"><title>{tip}</title></rect>')
    for r, lab in [(1, 'MON'), (3, 'WED'), (5, 'FRI')]:
        parts.append(f'<text x="{left-8}" y="{top + r*(cell+gap) + 9}" text-anchor="end" {F} font-size="8" fill="{t["ink"]}" fill-opacity=".45">{lab}</text>')
    by = top + 7 * (cell + gap) + 28
    parts.append(f'<text x="{left}" y="{by}" {F} font-size="10" letter-spacing="1.6" fill="{t["ink"]}">{active} ACTIVE DAYS · LONGEST STREAK {streak} · BEST DAY {best["count"]} ({best_label})</text>')
    lx = W - 30 - 5 * (cell + gap) - 70
    parts.append(f'<text x="{lx}" y="{by}" {F} font-size="9" letter-spacing="1.5" fill="{t["ink"]}" fill-opacity=".55">LESS</text>')
    for i, c in enumerate(lv):
        parts.append(f'<rect x="{lx + 34 + i*(cell+gap)}" y="{by-10}" width="{cell}" height="{cell}" fill="{c}"/>')
    parts.append(f'<text x="{lx + 34 + 5*(cell+gap) + 4}" y="{by}" {F} font-size="9" letter-spacing="1.5" fill="{t["ink"]}" fill-opacity=".55">MORE</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year">' + ''.join(parts) + '</svg>'

CHROME = 'google-chrome'
def shoot(name, built):
    htmlsrc, w, h = built
    p = RENDER / f'{name}.html'; p.write_text(htmlsrc)
    subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                    '--default-background-color=00000000', f'--window-size={w},{h}', f'--screenshot={OUT/(name+".png")}', p.as_uri()],
                   check=True, capture_output=True)
    from PIL import Image
    f = OUT/(name+'.png'); im = Image.open(f).convert('RGBA')
    if name.endswith('-light') and not name.startswith('fastfetch'):
        # opaque paper cards: palette PNG is small; skip fastfetch (halftone dots need truecolor)
        im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(f, optimize=True)
    else:  # transparent art + light fastfetch: keep truecolor
        im.save(f, optimize=True, compress_level=9)
    print('rendered', name)

modes = ['dark', 'light']
if LIGHT_ONLY: modes = ['light']
if DARK_ONLY: modes = ['dark']

for mode in modes:
    (OUT / f'contrib-{mode}.svg').write_text(heatmap_svg(mode))
    if SVG_ONLY: continue
    if not SKIP_HERO:
        shoot(f'hero-{mode}-base', hero(mode))
        import kinetic; kinetic.build(OUT/f'hero-{mode}-base.png', OUT/f'hero-{mode}.png', theme(mode)['kinetic'])
        (OUT/'alt').mkdir(exist_ok=True)   # optional: same motion, wordmark at full ink instead of the 0.2 ghost
        kinetic.build(OUT/f'hero-{mode}-base.png', OUT/'alt'/f'hero-{mode}-solid.png', theme(mode)['kinetic'], text_a=1.0)
        (OUT/f'hero-{mode}-base.png').replace(RENDER/f'hero-{mode}-base.png')
    else:
        print('skip hero', mode)
    shoot(f'fastfetch-{mode}', fastfetch(mode))
    shoot(f'telemetry-{mode}', telemetry(mode))
    shoot(f'footer-{mode}', footer(mode))
    for i in range(3): shoot(f'public-{PROJ[i][1].lower()}-{mode}', card(i, mode))
print('done')
