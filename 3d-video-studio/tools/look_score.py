"""Pixel half of the look check: measure frames against the house-look targets (look/targets.json).

    python tools/look_score.py <frame.jpg> ... [--regions regions.json] [--targets look/targets.json] [--json]
    python tools/look_score.py --measure <ref.png> ...       print the raw numbers (how targets.json was made)

targets.json holds the target ranges (made with --measure on reference frames).
`film.mjs lookcheck` calls this with regions.json (head circles and in-focus / background tiles found by raycasting the
scene), so it can also score blur depth and head brightness, which a flat picture alone cannot tell.
Metrics (frame scaled to 1080 wide):
  sat     mean saturation of pixels brighter than 20 %               (colour)
  ink     share of dark LINE pixels (luma < 0.17, sat < 0.55, and 0.3 brighter within 4 px), caption band left out  (outlines)
  empty   share of 60 px tiles that are flat (luma std < 0.03, no ink) (dressing density: empty wall or sky)
  gloss   share of soft highlight pixels in the lower 60 %: luma 0.10+ over the 31 px local mean, low saturation (gloss)
  vig     corner luma / centre luma                                   (light falloff)
  blur    share of background detail the lens blur keeps (|Laplacian| with blur / without, same frame rendered
          sharp by lookcheck), from regions; `subj` the same for the in-focus tiles (should stay near 1)   (depth)
  head    head luma percentile in the frame, from regions             (faces brightest)
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = os.path.join(HERE, '..', 'look', 'targets.json')


def load(path):
    im = Image.open(path).convert('RGB')
    if im.width != 1080: im = im.resize((1080, round(im.height * 1080 / im.width)), Image.LANCZOS)
    return im


def lap_of(im):
    a = np.asarray(im, dtype=np.float32) / 255.0
    l = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return np.abs(4 * l[1:-1, 1:-1] - l[:-2, 1:-1] - l[2:, 1:-1] - l[1:-1, :-2] - l[1:-1, 2:])


def measure(im, reg=None, sharp_im=None):
    a = np.asarray(im, dtype=np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    H, W = luma.shape
    m = {}
    bright = mx > 0.2
    m['sat'] = float(sat[bright].mean()) if bright.any() else 0.0
    dark = (luma < 0.17) & (sat < 0.55)
    near_max = np.asarray(Image.fromarray((luma * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)), dtype=np.float32) / 255.0
    ink = dark & (near_max - luma > 0.3)   # a LINE: dark, with something bright within 4 px (large dark areas do not count)
    keep = np.ones(H, bool); keep[int(H * 0.62):int(H * 0.8)] = False   # leave out the caption band (its black text stroke is not set ink)
    m['ink'] = float(ink[keep].mean())
    T = 60; flat = 0; n = 0
    for y in range(0, H - T + 1, T):
        for x in range(0, W - T + 1, T):
            t = luma[y:y + T, x:x + T]; n += 1
            if t.std() < 0.03 and not dark[y:y + T, x:x + T].any() and t.mean() > 0.12: flat += 1
    m['empty'] = flat / max(1, n)
    loc = np.asarray(Image.fromarray((luma * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(15)), dtype=np.float32) / 255.0
    hi = (luma - loc > 0.10) & (sat < 0.35) & (luma > 0.55)
    m['gloss'] = float(hi[int(H * 0.4):].mean())
    ch, cw = int(H * 0.1), int(W * 0.15)
    corners = np.concatenate([luma[:ch, :cw].ravel(), luma[:ch, -cw:].ravel(), luma[-ch:, :cw].ravel(), luma[-ch:, -cw:].ravel()])
    cen = luma[int(H * 0.35):int(H * 0.65), int(W * 0.35):int(W * 0.65)]
    m['vig'] = float(corners.mean() / max(1e-3, cen.mean()))
    if reg:
        if sharp_im is not None:
            lb, ls = lap_of(im), lap_of(sharp_im)
            def kept(tiles):   # median over tiles that have detail when sharp: blurred detail / sharp detail
                v = []
                for x0, y0, x1, y1 in tiles:
                    s0 = ls[max(0, y0 - 1):y1 - 1, max(0, x0 - 1):x1 - 1].mean()
                    if s0 > 0.004: v.append(lb[max(0, y0 - 1):y1 - 1, max(0, x0 - 1):x1 - 1].mean() / s0)
                return float(np.median(v)) if v else None
            b, f = kept(reg.get('background', [])), kept(reg.get('focus', []))
            if b is not None: m['blur'] = b
            if f is not None: m['subj'] = f
        hs = []
        for cx, cy, rad in reg.get('heads', []):
            yy, xx = np.ogrid[:H, :W]; mask = (xx - cx) ** 2 + (yy - cy) ** 2 < (rad * 0.55) ** 2
            if mask.sum() > 50: hs.append(float((luma < np.median(luma[mask])).mean()))
        if hs: m['head'] = min(hs)
    return m


def score(m, tg, kind, mood=None):
    """0..10 per checklist area. Each metric scores 10 inside [lo, hi] and loses points with distance outside it."""
    def s(v, lo, hi, span):
        if v is None: return None
        d = lo - v if v < lo else v - hi if v > hi else 0
        return max(0.0, round(10 - 10 * d / span, 1))
    T = {**tg[kind], **tg.get(kind + '_' + str(mood), {})}
    names = {'sat': 'colour', 'ink': 'outlines', 'empty': 'density', 'gloss': 'gloss', 'blur': 'depth', 'head': 'faces'}
    out = {area: s(m[k], *T[k]) for k, area in names.items() if k in T and k in m}
    if 'subj' in m and 'depth' in out: out['depth'] = min(out['depth'], s(m['subj'], 0.8, 1.2, 0.3))   # the subject must stay sharp
    return out


def main(argv):
    if argv and argv[0] == '--measure':
        for p in argv[1:]: print(os.path.basename(p), {k: round(v, 4) for k, v in measure(load(p)).items()})
        return
    as_json = '--json' in argv; argv = [a for a in argv if a != '--json']
    reg_path = tg_path = None
    if '--regions' in argv: i = argv.index('--regions'); reg_path = argv[i + 1]; del argv[i:i + 2]
    if '--targets' in argv: i = argv.index('--targets'); tg_path = argv[i + 1]; del argv[i:i + 2]
    tg = json.load(open(tg_path or TARGETS, encoding='utf8'))
    regions = json.load(open(reg_path, encoding='utf8')) if reg_path else {}
    rows = []
    for p in argv:
        reg = regions.get(os.path.basename(p), {})
        kind = reg.get('kind', 'indoor')
        sharp = load(os.path.join(os.path.dirname(p), reg['sharp'])) if reg.get('sharp') else None
        m = measure(load(p), reg, sharp)
        sc = score(m, tg, kind, reg.get('mood'))
        rows.append({'frame': os.path.basename(p), 'kind': kind, 'metrics': {k: round(v, 4) for k, v in m.items()}, 'scores': sc})
    if as_json: print(json.dumps(rows, indent=1)); return
    for r in rows:
        sc = '  '.join(f"{k} {v:.0f}" if v is not None else f"{k} -" for k, v in r['scores'].items())
        low = [k for k, v in r['scores'].items() if v is not None and v < 8]
        print(f"{r['frame']:<22} {r['kind']:<7} {sc}" + (f"   LOW: {', '.join(low)}" if low else ''))
        print(' ' * 31 + '  '.join(f"{k}={v}" for k, v in r['metrics'].items()))


if __name__ == '__main__':
    main(sys.argv[1:])
