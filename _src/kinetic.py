"""Kinetic epithets -- big ghosted words warping through a 1-bit Bayer dither dissolve.

Faithful port of the reference QML (all numbers below come straight from it, scaled
from its 210px display size to this panel's 136px):
  * words: lead word ACTUM, then POWER, BEAUTY, GRACE, RUIN, DEMISE, VOID (loop)
  * timeline: pause 1300ms -> mix 0->1 in 240ms (InQuad) -> idx++ -> mix 1->0 in 240ms (OutQuad)
  * text: display serif (Fraunces, Medium), ink at alpha 0.2, opacity 1 - mix,
          left-aligned, vertically centred in its box
  * warp: Scale{origin (0, h/2); xScale = fit*(1+0.1*sin(mix*pi)); yScale = 1-0.07*sin(mix*pi)}
  * burst: a separate layer over the glyphs -- cell 10 (drawn cell-1, so a 1px gutter),
           Bayer 4x4, threshold = mix*(0.3 + 0.7*sin((row+.5)/rows*pi)) (vertical falloff,
           densest mid-word), cells in ink at alpha 0.24, skipped while mix < 0.02;
           box = word width*fit + 6 by 0.82*size, raised 0.11*size from the box centre.
Output: one APNG (loops forever, single global palette), drawn at 2x."""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFont

WORDS = ['ACTUM', 'POWER', 'BEAUTY', 'GRACE', 'RUIN', 'DEMISE', 'VOID']
S = 2                                    # device scale of the hero render
K = 136 / 210                            # reference 210px display -> 136px on this 900px panel
FONT = '/usr/share/fonts/truetype/sand-box/google/Fraunces/Fraunces-VariableFont_SOFT,WONK,opsz,wght.ttf'
SIZE = round(210 * K * S)
BOX = (136 * S, 36 * S, round(800 * K * S), round(180 * K * S))   # x, y, w, h of the epithet box (1x: 136,36 518x117)
CELL = max(2, round(10 * K * S))
CLIP_R = 620 * S                         # the bust eats the right edge of long words
TEXT_A, BURST_A = 0.20, 0.24
HOLD, HALF, STEP = 1300, 240, 30         # ms
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float)

font = ImageFont.truetype(FONT, SIZE)
font.set_variation_by_axes([144, 500, 0, 0])   # opsz, wght (Medium), SOFT, WONK

def _word(word):
    l, t, r, b = font.getbbox(word, anchor='lm')
    im = Image.new('L', (r - l + 4, b - t + 4), 0)
    ImageDraw.Draw(im).text((2 - l, 2 - t), word, font=font, fill=255, anchor='lm')
    return im, l - 2, t - 2, font.getlength(word)

def layer(word, mix, rgb, text_a=TEXT_A):
    bx, by, bw, bh = BOX
    W, H = CLIP_R - bx + 40 * S, bh + 40 * S
    oy = by - 20 * S                                  # layer origin (some headroom for the warp)
    a = np.zeros((H, W), float)
    m, ol, ot, iw = _word(word)
    fit = min(1.0, bw / max(1.0, iw))
    s = math.sin(mix * math.pi)
    sx, sy = fit * (1 + 0.1 * s), 1 - 0.07 * s
    w, h = max(1, round(m.width * sx)), max(1, round(m.height * sy))
    m = m.resize((w, h), Image.LANCZOS)
    cy = by + bh / 2 - oy                             # scale origin: (box left, box centre)
    px, py = round(ol * sx), round(cy + ot * sy)
    g = np.asarray(m, float) / 255 * text_a * (1 - mix)
    x0, y0, x1, y1 = max(0, px), max(0, py), min(W, px + w), min(H, py + h)
    a[y0:y1, x0:x1] = g[y0 - py:y1 - py, x0 - px:x1 - px]
    if mix >= 0.02:                                   # the dither burst (not warped)
        dw, dh = math.ceil(iw * fit) + 6 * S, math.ceil(SIZE * 0.82)
        dy0 = round(cy - 0.11 * SIZE - dh / 2)
        cols, rows = -(-dw // CELL), -(-dh // CELL)
        for gy in range(rows):
            thr = mix * (0.3 + 0.7 * math.sin((gy + 0.5) / rows * math.pi))
            for gx in range(cols):
                if (BAYER[gy % 4, gx % 4] + 0.5) / 16 < thr:
                    yA, xA = dy0 + gy * CELL, gx * CELL
                    blk = a[max(0, yA):max(0, yA + CELL - 1), xA:xA + CELL - 1]
                    blk[:] = BURST_A + blk * (1 - BURST_A)   # source-over of ink@0.24
    a[:, CLIP_R - bx:] = 0
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = rgb; out[..., 3] = np.clip(a * 255 + .5, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA'), (bx, oy)

def frame(base, word, mix, rgb, text_a=TEXT_A):
    im = base.copy(); L, pos = layer(word, mix, rgb, text_a); im.alpha_composite(L, pos); return im

def shared_palette(frames, n=256):
    """One global RGBA palette for every frame (APNG has a single PLTE/tRNS)."""
    from scipy.spatial import cKDTree
    bx, by, bw, bh = BOX
    region = (bx, by - 20 * S, CLIP_R + 40 * S, by + bh + 20 * S)
    samples = [frames[0]] + [f.crop(region) for f in frames[1::3]]
    W = max(s.width for s in samples); H = sum(s.height for s in samples)
    mont = Image.new('RGBA', (W, H)); y = 0
    for s in samples: mont.paste(s, (0, y)); y += s.height
    q = mont.quantize(n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette('RGBA')[:4 * n], float).reshape(-1, 4)
    wts = np.array([1, 1, 1, 1.5])
    tree = cKDTree(pal * wts)
    pal_rgb = pal[:, :3].astype(np.uint8).flatten().tolist(); alpha = bytes(pal[:, 3].astype(np.uint8).tolist())
    cache, out = {}, []
    for f in frames:
        a = np.asarray(f, np.uint32)
        key = (a[..., 0] << 24) | (a[..., 1] << 16) | (a[..., 2] << 8) | a[..., 3]
        u, inv = np.unique(key.ravel(), return_inverse=True)
        miss = [k for k in u.tolist() if k not in cache]
        if miss:
            mk = np.array(miss, np.uint64)
            cols = np.stack([(mk >> 24) & 255, (mk >> 16) & 255, (mk >> 8) & 255, mk & 255], 1).astype(float)
            _, idx = tree.query(cols * wts)
            cache.update(zip(miss, idx.tolist()))
        lut = np.array([cache[k] for k in u.tolist()], np.uint8)
        p = Image.fromarray(lut[inv].reshape(key.shape), 'P')
        p.putpalette(pal_rgb); p.info['transparency'] = alpha
        out.append(p)
    return out

def build(base_path, out_path, ink='#efe2c2', words=WORDS, text_a=TEXT_A):
    rgb = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5))
    base = Image.open(base_path).convert('RGBA')
    n = HALF // STEP
    frames, durs = [], []
    for i, w in enumerate(words):
        nxt = words[(i + 1) % len(words)]
        frames.append(frame(base, w, 0, rgb, text_a)); durs.append(HOLD)          # PauseAnimation 1300
        for k in range(1, n + 1):                                         # 0 -> 1, InQuad
            t = k / n; frames.append(frame(base, w, t * t, rgb, text_a)); durs.append(STEP)
        for k in range(1, n):                                             # idx++, 1 -> 0, OutQuad
            t = k / n; frames.append(frame(base, nxt, 1 - (1 - (1 - t) ** 2), rgb, text_a)); durs.append(STEP)
    frames = shared_palette(frames)
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=durs, loop=0,
                   disposal=0, blend=0, optimize=False, compress_level=9)
