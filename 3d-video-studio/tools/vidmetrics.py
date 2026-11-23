"""Shared video measurement for /3d-video-studio: the numbers a finished Short is judged by against its reference.

    import vidmetrics as vm
    raw = vm.measure('video.mp4')                   # decode + per-frame metrics + transitions + setups (~1 min)
    s = vm.summarize(raw, acts=[0, 18.5, 43.6, 62.2]) # judged numbers; t0=, t1= for a stretch of the video

Used by ref_profile.py, compare_video.py and video_qa.py. Not a CLI. numpy + PIL + ffmpeg/ffprobe only.

measure() decodes the video once at 180x320 and once at full resolution, 1 frame per second, and returns
  perframe   per frame: diff (mean abs luma change, 0-255), tx, ty (camera pan, px at 1080 wide, per frame),
             zoom (scale change per frame), roll (deg per frame), resid (object motion), col (Hasler-Susstrunk
             colourfulness), sat (HSV saturation), lum (luma), edge (edge density at 180x320)
  samples    1 per second at full res: sharp (Laplacian variance, caption band left out), caption h / y / outline
  transitions  cut (1-frame change), blend (a broken cut: 1-2 frames that are a 30-70% mix of the shots either side),
             dissolve (linear blend over 3+ frames, with frame count and alpha curve), gradual (in-world: fly-through,
             burst, wipe: colour histogram moves a lot within 0.3 s but no cut or dissolve explains it)
  setups     camera setups between transitions
  loudness   I (LUFS), LRA (LU), true peak (dBTP)
"""
import json, os, re, subprocess
import numpy as np

FPS = 30
W, H = 180, 320              # motion / colour / sheets
CAP_BAND = (1250, 1450)      # rows (of 1920) left out of sharpness: captions sit here
CAP_SEARCH = (0.60, 0.80)    # caption search band, share of height

# detector settings (tuned on the dash-cam reference and cars_watching_the_road)
CUT_DIFF = 18.0              # mean abs RGB change at 90x160 for a hard cut
CUT_ISO = 3.5                # ... and this many times the local median change
BLEND_RMS = 25.0             # rms change across a blended frame that counts as a shot change
DIS_H = (3, 5, 8, 12, 16)    # half-widths tried by the dissolve scan
GRAD_THR = 0.35              # histogram distance over GRAD_G frames for a gradual (in-world) transition
GRAD_G = 9                   # 0.3 s
DIS_MIN_HIST = 0.25          # a dissolve joins two different pictures (histogram distance of its end frames)
DIS_MAX_FIT90 = 0.55         # ... and its middle frame is a clean blend of them at 90x160


# ---------------------------------------------------------------- decoding
def probe(v):
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                    'stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration',
                                    '-of', 'json', v], capture_output=True, text=True, check=True).stdout)
    vs = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    a, b = vs['r_frame_rate'].split('/')
    return dict(w=int(vs['width']), h=int(vs['height']), fps=float(a) / float(b), dur=float(pr['format']['duration']),
                audio=any(s['codec_type'] == 'audio' for s in pr['streams']))


def decode(v, w=W, h=H, gray=False, vf_pre=None, ss=None, frames=None):
    """All frames (or `frames` from `ss` seconds) as uint8 (n, h, w[, 3])."""
    vf = (vf_pre + ',' if vf_pre else '') + f'scale={w}:{h}:flags=area'
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None:
        cmd += ['-ss', f'{max(0.0, ss):.4f}']
    cmd += ['-i', v]
    if frames:
        cmd += ['-frames:v', str(frames)]
    cmd += ['-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'gray' if gray else 'rgb24', '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    shape = (-1, h, w) if gray else (-1, h, w, 3)
    return np.frombuffer(raw, np.uint8).reshape(shape)


def grab(v, t, w, h=None):
    """One frame at t seconds (PIL image)."""
    from PIL import Image
    h = h or w * 16 // 9
    a = decode(v, w, h, ss=t + 0.001, frames=1)
    return Image.fromarray(a[0]) if len(a) else Image.new('RGB', (w, h))


# ---------------------------------------------------------------- per-frame metrics
_BS = 64
_BX = [8, 58, 108]
_BY = [16, 90, 164, 238]
_WIN = np.outer(np.hanning(_BS), np.hanning(_BS)).astype(np.float32)
_CTR = np.array([(x + _BS / 2 - W / 2, y + _BS / 2 - H / 2) for y in _BY for x in _BX], np.float32)


def _block_fft(g):
    """g (m, H, W) float32 -> block FFTs (m, 12, 64, 64), block std (m, 12)."""
    B = np.stack([g[:, y:y + _BS, x:x + _BS] for y in _BY for x in _BX], 1)
    sd = B.std((2, 3))
    B = (B - B.mean((2, 3), keepdims=True)) * _WIN
    return np.fft.fft2(B), sd


def _shifts(Fa, Fb):
    """Phase correlation of block FFTs: shift of b relative to a, peak height. (m, 12) each."""
    R = Fb * np.conj(Fa)
    R /= np.abs(R) + 1e-6
    r = np.fft.ifft2(R).real.astype(np.float32)
    m, nb = r.shape[:2]
    flat = r.reshape(m, nb, -1)
    i = flat.argmax(-1)
    yy, xx = np.divmod(i, _BS)
    pk = np.take_along_axis(flat, i[..., None], -1)[..., 0]

    def at(dy, dx):
        return np.take_along_axis(flat, (((yy + dy) % _BS) * _BS + (xx + dx) % _BS)[..., None], -1)[..., 0]

    def sub(a, p, q):
        d = a - 2 * p + q
        return np.where(np.abs(d) < 1e-9, 0, 0.5 * (a - q) / np.where(np.abs(d) < 1e-9, 1, d))

    dy = np.where(yy < _BS // 2, yy, yy - _BS) + sub(at(-1, 0), pk, at(1, 0))
    dx = np.where(xx < _BS // 2, xx, xx - _BS) + sub(at(0, -1), pk, at(0, 1))
    return dx, dy, pk


def frame_metrics(rgb):
    """rgb uint8 (n, 320, 180, 3) -> dict of per-frame numpy arrays."""
    n = len(rgb)
    out = {k: np.full(n, np.nan, np.float32) for k in ('diff', 'tx', 'ty', 'zoom', 'roll', 'resid', 'col', 'sat', 'lum', 'edge')}
    out['diff'][0] = 0
    scale = 1080 / W
    lw = np.array([0.299, 0.587, 0.114], np.float32)
    prev_g = prev_F = prev_sd = None
    CH = 128
    for c0 in range(0, n, CH):
        f = rgb[c0:c0 + CH].astype(np.float32)
        R, G, B = f[..., 0], f[..., 1], f[..., 2]
        rg = (R - G).reshape(len(f), -1); yb = (0.5 * (R + G) - B).reshape(len(f), -1)
        out['col'][c0:c0 + len(f)] = np.sqrt(rg.std(1) ** 2 + yb.std(1) ** 2) + 0.3 * np.sqrt(rg.mean(1) ** 2 + yb.mean(1) ** 2)
        mx = f.max(-1); mn = f.min(-1)
        out['sat'][c0:c0 + len(f)] = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0).reshape(len(f), -1).mean(1)
        g = f @ lw
        out['lum'][c0:c0 + len(f)] = g.reshape(len(f), -1).mean(1)
        gx = np.abs(np.diff(g, axis=2))[:, :-1]; gy = np.abs(np.diff(g, axis=1))[:, :, :-1]
        out['edge'][c0:c0 + len(f)] = ((gx + gy) > 24).reshape(len(f), -1).mean(1)
        Fb, sd = _block_fft(g)
        if prev_g is not None:
            gg = np.concatenate([prev_g[None], g]); FF = np.concatenate([prev_F[None], Fb]); SS = np.concatenate([prev_sd[None], sd])
        else:
            gg, FF, SS = g, Fb, sd
        d = np.abs(np.diff(gg, axis=0)).reshape(len(gg) - 1, -1).mean(1)
        k0 = c0 if prev_g is not None else 1
        out['diff'][k0:k0 + len(d)] = d
        dx, dy, pk = _shifts(FF[:-1], FF[1:])
        ok = (SS[:-1] >= 3) & (pk >= 0.08)
        for j in range(len(d)):
            k = k0 + j
            sel = ok[j]
            if sel.sum() < 4:
                continue
            P = _CTR[sel]; m = len(P)
            M = np.zeros((2 * m, 4), np.float32); bv = np.zeros(2 * m, np.float32)
            M[0::2] = np.c_[np.ones(m), np.zeros(m), P[:, 0], -P[:, 1]]
            M[1::2] = np.c_[np.zeros(m), np.ones(m), P[:, 1], P[:, 0]]
            bv[0::2] = dx[j][sel]; bv[1::2] = dy[j][sel]
            sol = np.linalg.lstsq(M, bv, rcond=None)[0]
            r = M @ sol - bv
            out['tx'][k] = sol[0] * scale; out['ty'][k] = sol[1] * scale
            out['zoom'][k] = 1 + sol[2]; out['roll'][k] = np.degrees(sol[3])
            out['resid'][k] = np.sqrt((r ** 2).mean()) * scale
        prev_g, prev_F, prev_sd = g[-1], Fb[-1], sd[-1]
    return out


# ---------------------------------------------------------------- transitions
def _small(rgb):
    """180x320 -> 90x160 float32 flat (n, 43200)."""
    n = len(rgb)
    out = np.empty((n, (H // 2) * (W // 2) * 3), np.float32)
    for c0 in range(0, n, 256):
        f = rgb[c0:c0 + 256].astype(np.float32)
        f = f.reshape(len(f), H // 2, 2, W // 2, 2, 3).mean((2, 4))
        out[c0:c0 + len(f)] = f.reshape(len(f), -1)
    return out


def _rms(a, axis=-1):
    return np.sqrt((a * a).mean(axis))


def _hist_change(rgb, G=GRAD_G):
    """Colour histogram distance (0-1) between frame k-G and k, at 36x64, 512 bins."""
    n = len(rgb)
    h = np.empty((n, 512), np.float32)
    for c0 in range(0, n, 256):
        f = rgb[c0:c0 + 256].reshape(-1, 64, 5, 36, 5, 3).mean((2, 4)).astype(np.uint8) // 32
        idx = (f[..., 0].astype(np.int32) * 64 + f[..., 1] * 8 + f[..., 2]).reshape(len(f), -1)
        for j, r in enumerate(idx):
            h[c0 + j] = np.bincount(r, minlength=512)
    h /= 36 * 64
    d = np.zeros(n, np.float32)
    d[G:] = 0.5 * np.abs(h[G:] - h[:-G]).sum(1)
    return d


def detect_blends(F, d1=None, r1=None):
    """Broken hard cuts: 1 or 2 frames that are a 30-70% mix of the frames either side, with the change confined
    to them (motion-blur sub-frames averaged across a shot boundary). F: flat 90x160 float frames (_small()).
    Frames inside a real dissolve are not reported: the frames either side of a blend must be pure shots."""
    n = len(F)
    if d1 is None:
        d1 = np.r_[0, np.abs(np.diff(F, axis=0)).mean(1)].astype(np.float32)
    if r1 is None:
        r1 = np.r_[0, _rms(np.diff(F, axis=0))].astype(np.float32)
    blends = []
    taken = set()
    for k in range(3, n - 3):
        if k in taken or max(d1[k], d1[k + 1]) < 6:
            continue
        best = None
        for L in (1, 2):                       # number of mixed frames
            if k + L + 2 >= n:
                continue
            A, B = F[k - 1], F[k + L]
            BA = B - A
            span = float(_rms(BA))
            if span < BLEND_RMS:
                continue
            # change outside the mixed frames must be small next to the change across them
            out_ch = max(r1[k - 1], r1[k + L + 1])
            if out_ch * 2.5 > span:
                continue
            # the frames either side must be pure shots (not the tails of a short dissolve):
            # against endpoints 2 frames further out, k-1 sits near alpha 0 and k+L near alpha 1
            A2, B2 = F[k - 3], F[k + L + 2]
            W2 = B2 - A2
            n2 = float((W2 * W2).mean())
            if n2 < 1e-6:
                continue
            p0 = float(((A - A2) * W2).mean() / n2); p1 = float(((B - A2) * W2).mean() / n2)
            if p0 > 0.12 or p1 < 0.88:
                continue
            nab = float((BA * BA).mean())
            als, ok = [], True
            for j in range(L):
                C = F[k + j]
                a = float(((C - A) * BA).mean() / nab)
                res = float(_rms(C - A - a * BA))
                near = min(float(_rms(C - A)), float(_rms(C - B)))
                if not (0.15 < a < 0.85) or res > 0.6 * near:
                    ok = False; break
                als.append(a)
            if ok and any(0.3 <= a <= 0.7 for a in als):
                if best is None or L < best[0]:
                    best = (L, als, span)
        if best:
            L, als, span = best
            blends.append(dict(kind='blend', f=k, frames=L, alpha=[round(a, 2) for a in als], span=[k, k + L - 1],
                               t=round(k / FPS, 3), shot=k + L))
            taken.update(range(k, k + L + 1))
    return blends


def detect_transitions(rgb):
    """Cuts, blended cut frames, dissolves and gradual (in-world) transitions. Frame numbers are 0-based."""
    F = _small(rgb)
    n = len(F)
    d1 = np.r_[0, np.abs(np.diff(F, axis=0)).mean(1)].astype(np.float32)   # mean abs RGB change
    r1 = np.r_[0, _rms(np.diff(F, axis=0))].astype(np.float32)               # rms change

    blends = detect_blends(F, d1, r1)

    # --- hard cuts: an isolated spike, not part of a blend
    blendf = set()
    for b in blends:
        blendf.update(range(b['span'][0], b['span'][1] + 2))
    cuts = []
    for k in range(1, n):
        if k in blendf:
            continue
        nb = np.r_[d1[max(1, k - 6):k], d1[k + 1:k + 7]]
        if d1[k] > CUT_DIFF and d1[k] > CUT_ISO * (np.median(nb) + 1):
            cuts.append(k)
    hard = sorted(set(cuts) | {b['span'][1] + 1 for b in blends})
    hc = np.zeros(n + 1, np.int32)
    for c in hard:
        hc[c] += 1
    hcum = np.cumsum(hc)

    # --- dissolves: frame k explained by a linear blend of k-h and k+h (fitted at 45x80, which tolerates
    # the shots' own motion; the extent is then measured at 90x160)
    Fs = F.reshape(n, H // 4, 2, W // 4, 2, 3).mean((2, 4)).reshape(n, -1)
    cand = {}
    for h in DIS_H:
        for c0 in range(h, n - h, 256):
            ks = np.arange(c0, min(c0 + 256, n - h))
            A, B, C = Fs[ks - h], Fs[ks + h], Fs[ks]
            BA = B - A
            nab = (BA * BA).mean(1)
            CA = C - A
            a = (CA * BA).mean(1) / np.maximum(nab, 1e-6)
            res = _rms(CA - a[:, None] * BA)
            ref = np.minimum(_rms(CA), _rms(C - B))
            ratio = res / (ref + 1e-6)
            inside = hcum[ks + h] - hcum[ks - h] > 0           # a hard cut in (k-h, k+h]
            good = (nab >= 25 ** 2) & ~inside & (a > 0.15) & (a < 0.85) & (ratio < 0.45)
            for k, rt, al in zip(ks[good], ratio[good], a[good]):
                k = int(k)
                if k not in cand or cand[k][1] > rt:
                    cand[k] = (h, float(rt), float(al))
    groups = []
    for k in sorted(cand):
        if groups and k - groups[-1][-1] <= 3:
            groups[-1].append(k)
        else:
            groups.append([k])
    dissolves = []
    for g in groups:
        if len(g) < 2:
            continue
        c = min(g, key=lambda k: cand[k][1])
        lo = g[0] - cand[g[0]][0]
        hi = g[-1] + cand[g[-1]][0]
        d = _dissolve_extent(F, r1, c, lo, hi, hard, cand[c][1])
        # a dissolve joins two different pictures and is a clean blend at 90x160 too; slow pushes, lighting
        # changes and props moving inside one shot fail one of these
        if d['hist'] >= DIS_MIN_HIST and d['fit90'] <= DIS_MAX_FIT90:
            dissolves.append(d)
    # drop overlapping duplicates (keep the better fit)
    dissolves.sort(key=lambda d: d['fit'])
    keep = []
    for d in dissolves:
        if all(d['span'][1] < e['span'][0] - 2 or d['span'][0] > e['span'][1] + 2 for e in keep):
            keep.append(d)
    dissolves = sorted(keep, key=lambda d: d['span'][0])

    # --- gradual (in-world) transitions: big histogram change in 0.3 s that nothing above explains
    hd = _hist_change(rgb)
    known = [(c - 2, c + 2) for c in hard] + [(d['span'][0] - 3, d['span'][1] + 3) for d in dissolves]
    gradual = []
    for k in range(GRAD_G, n):
        if hd[k] <= GRAD_THR or hd[k] < hd[max(0, k - 15):k + 16].max():
            continue
        a_, b_ = k - GRAD_G, k                # the change happens between these frames
        if any(a_ - 3 <= y and b_ + 3 >= x for x, y in known):
            continue
        if gradual and k - gradual[-1]['peak'] < 20:
            continue
        # extent: frames around the peak where the 1-frame change is raised
        w0, w1 = max(1, a_ - 6), min(n - 1, b_ + 6)
        loc = r1[w0:w1 + 1]
        thr = 0.25 * loc.max()
        idx = np.nonzero(loc > thr)[0]
        s, e = w0 + int(idx[0]), w0 + int(idx[-1])
        gradual.append(dict(kind='gradual', peak=int(k), span=[s, e], frames=e - s + 1, hist=round(float(hd[k]), 3),
                            shot=int(round((s + e) / 2)), t=round((s + e) / 2 / FPS, 3)))

    tr = [dict(kind='cut', f=c, span=[c, c], frames=1, shot=c, t=round(c / FPS, 3), diff=round(float(d1[c]), 1))
          for c in cuts]
    tr = _merge(tr + dissolves + gradual)
    tr += blends
    tr.sort(key=lambda x: x['shot'])
    return tr, dict(d1=d1, r1=r1, hd=hd)


def _merge(tr, gap=6):
    """Transitions that touch are one event: a cut into a cash burst, the two halves of a burst, two cut frames in a
    row (a very short mix). The merged event is gradual if either part is; blends are never merged (always reported)."""
    tr = sorted(tr, key=lambda x: x['span'][0])
    out = []
    for x in tr:
        if out and x['span'][0] - out[-1]['span'][1] <= gap:
            p = out[-1]
            s, e = p['span'][0], max(p['span'][1], x['span'][1])
            kinds = {p['kind'], x['kind']}
            if 'gradual' in kinds or kinds == {'cut', 'dissolve'}:
                m = dict(kind='gradual', hist=max(p.get('hist', 0), x.get('hist', 0)), parts=[p['kind'], x['kind']])
            elif kinds == {'cut'}:
                m = dict(kind='cut', f=p['f'], parts=['cut', 'cut'])
            else:                                   # two dissolves: keep the better fitted one's curve
                m = dict(min((p, x), key=lambda d: d['fit']))
            m.update(span=[s, e], frames=e - s + 1, shot=int(round((s + e) / 2)) if m['kind'] != 'cut' else p['shot'])
            m['t'] = round(m['shot'] / FPS, 3)
            out[-1] = m
        else:
            out.append(x)
    return out


def _hdist(a, b):
    """Colour histogram distance (0-1, 512 bins) of two flat 90x160 RGB frames."""
    def h(f):
        q = f.reshape(-1, 3).astype(np.int32) // 32
        return np.bincount(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], minlength=512) / len(q)
    return 0.5 * float(np.abs(h(a) - h(b)).sum())


def _dissolve_extent(F, r1, c, lo, hi, hard, fit):
    """Frame count and alpha curve of a dissolve found around frame c ([lo, hi] = frames the scan used).
    Endpoints are pushed out to where the 1-frame change drops back to the shots' own motion, then the alpha of every
    frame between them is the projection onto (B - A); mixed frames are those with alpha in (0.03, 0.97)."""
    n = len(F)
    lim0 = max([x for x in hard if x <= c] + [0]); lim1 = min([x for x in hard if x > c] + [n]) - 1
    lo, hi = max(lo, lim0), min(hi, lim1)
    # widen while the per-frame change near the edge is still well above the motion outside
    for _ in range(12):
        base = np.median(r1[max(lim0 + 1, lo - 6):lo]) if lo - 1 > lim0 else 0
        if lo - 1 > lim0 and r1[lo] > 1.6 * base + 1.0:
            lo -= 1
        else:
            break
    for _ in range(12):
        base = np.median(r1[hi + 2:min(lim1, hi + 7) + 1]) if hi + 1 < lim1 else 0
        if hi + 1 < lim1 and r1[hi + 1] > 1.6 * base + 1.0:
            hi += 1
        else:
            break
    A, B = F[lo], F[hi]
    BA = B - A
    nab = float((BA * BA).mean())
    al = [(k, float(((F[k] - A) * BA).mean() / nab)) for k in range(lo, hi + 1)]
    # walk out from the centre so noise at the far ends does not stretch it
    ci = c - lo
    s = lo
    for i in range(ci, -1, -1):
        if al[i][1] <= 0.03:
            s = al[i][0] + 1; break
    e = hi
    for i in range(ci, len(al)):
        if al[i][1] >= 0.97:
            e = al[i][0] - 1; break
    s, e = min(s, c), max(e, c)
    curve = [round(a, 2) for k, a in al if s <= k <= e]
    # checks: histogram distance between the frames just outside, blend fit of the middle frame against them
    A, B = F[max(0, s - 1)], F[min(n - 1, e + 1)]
    BA = B - A
    C = F[(s + e) // 2]
    a = float(((C - A) * BA).mean() / max(1e-6, float((BA * BA).mean())))
    fit90 = float(_rms(C - A - a * BA)) / (min(float(_rms(C - A)), float(_rms(C - B))) + 1e-6)
    return dict(kind='dissolve', span=[s, e], frames=e - s + 1, alpha=curve, fit=round(fit, 3), fit90=round(fit90, 3),
                hist=round(_hdist(A, B), 3),
                shot=int(round((s + e) / 2)), t=round((s + e) / 2 / FPS, 3), t0=round(s / FPS, 3), t1=round(e / FPS, 3))


def segment(n, trans, min_len=8):
    """Camera setups from transitions. Each setup: a, b (frames, b exclusive), how it starts."""
    tr = sorted(trans, key=lambda x: x['shot'])
    prio = {'cut': 0, 'blend': 0, 'dissolve': 1, 'gradual': 2}
    keep = []
    for x in tr:
        if keep and x['shot'] - keep[-1]['shot'] < min_len:
            if prio[x['kind']] < prio[keep[-1]['kind']]:
                keep[-1] = x
            continue
        if x['shot'] < min_len or x['shot'] > n - min_len:
            continue
        keep.append(x)
    bounds = [0] + [x['shot'] for x in keep] + [n]
    setups = []
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        x = keep[i - 1] if i else None
        inn = {'kind': 'start'} if x is None else {k: x[k] for k in ('kind', 'frames', 'span') if k in x}
        if x is not None and 'alpha' in x:
            inn['alpha'] = x['alpha']
        setups.append(dict(n=i + 1, a=a, b=b, t0=round(a / FPS, 3), t1=round(b / FPS, 3), dur=round((b - a) / FPS, 3), **{'in': inn}))
    return setups


# ---------------------------------------------------------------- full-res samples: sharpness + captions
def full_res_samples(v, info):
    """1 frame per second at full resolution (gray): sharpness and caption measurements."""
    w, h = info['w'], info['h']
    g = decode(v, w, h, gray=True, vf_pre='fps=1')
    sy = h / 1920
    c0, c1 = int(CAP_BAND[0] * sy), int(CAP_BAND[1] * sy)
    out = []
    for i, f in enumerate(g):
        f32 = f.astype(np.float32)
        lap = 4 * f32[1:-1, 1:-1] - f32[:-2, 1:-1] - f32[2:, 1:-1] - f32[1:-1, :-2] - f32[1:-1, 2:]
        keep = np.r_[lap[:c0 - 1], lap[c1 - 1:]]
        d = dict(t=float(i), sharp=round(float(keep.var()), 1))
        d.update(caption(f))
        out.append(d)
    return out


def _runs(mask):
    """Run lengths of True along axis 1: array same shape giving the length of the run each pixel is in."""
    hgt, wid = mask.shape
    out = np.zeros(mask.shape, np.int32)
    m = np.pad(mask, ((0, 0), (1, 1))).astype(np.int8)
    dm = np.diff(m, axis=1)
    for y in range(hgt):
        st = np.nonzero(dm[y] == 1)[0]; en = np.nonzero(dm[y] == -1)[0]
        for a, b in zip(st, en):
            out[y, a:b] = b - a
    return out


def caption(g):
    """White text with a black outline in 60-80% of the height of a gray frame.
    Returns cap_h (text height px, scaled to 1920 tall), cap_y (centre, share of height), cap_ol (outline px) or {}."""
    hgt, wid = g.shape
    y0, y1 = int(CAP_SEARCH[0] * hgt), int(CAP_SEARCH[1] * hgt)
    b = g[y0:y1].astype(np.int16)
    white = b > 215
    dark = b < 60
    wr = _runs(white)
    white &= wr <= 0.045 * wid                       # strokes, not heads or sky
    # a text pixel has a dark pixel close by on the left and on the right (the outline)
    R = int(0.012 * wid) + 2
    dk = np.pad(dark, ((0, 0), (R, R)))
    cs = np.cumsum(dk, axis=1, dtype=np.int32)
    cs = np.pad(cs, ((0, 0), (1, 0)))
    x = np.arange(wid)
    left = cs[:, x + R] - cs[:, x]                   # dark in [x-R, x)
    right = cs[:, x + 2 * R + 1] - cs[:, x + R + 1]  # dark in (x, x+R]
    txt = white & (left > 0) & (right > 0)
    rows = txt.sum(1)
    on = rows >= max(6, int(0.006 * wid))
    if on.sum() < 8:
        return {}
    # blocks of text rows (gaps up to 8 px), pick the one with most text pixels
    ys = np.nonzero(on)[0]
    blocks, cur = [], [ys[0], ys[0]]
    for y in ys[1:]:
        if y - cur[1] <= max(8, int(0.004 * hgt)):
            cur[1] = y
        else:
            blocks.append(cur); cur = [y, y]
    blocks.append(cur)
    blk = max(blocks, key=lambda bb: rows[bb[0]:bb[1] + 1].sum())
    th = blk[1] - blk[0] + 1
    if th < 0.012 * hgt or th > 0.055 * hgt:          # one line of 72-75 px type is about 40-100 px tall
        return {}
    cols = np.nonzero(txt[blk[0]:blk[1] + 1].any(0))[0]
    if cols[-1] - cols[0] < 1.2 * th:               # a word is wider than tall
        return {}
    # outline width: dark run length just outside text strokes, along rows in the block
    sub_w = white[blk[0]:blk[1] + 1]; sub_d = dark[blk[0]:blk[1] + 1]
    dr = _runs(sub_d)
    edge = sub_w[:, :-1] & sub_d[:, 1:]
    ol = dr[:, 1:][edge]
    ol = ol[ol <= 0.03 * wid]
    sc = 1920 / hgt
    return dict(cap_h=round(float(th * sc), 1), cap_y=round(float((y0 + (blk[0] + blk[1]) / 2) / hgt), 4),
                cap_ol=round(float(np.median(ol)) * sc, 1) if len(ol) > 10 else None)


# ---------------------------------------------------------------- audio
def loudness(v):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', v, '-map', '0:a:0', '-af', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    tail = r[r.rfind('Summary:'):]
    g = lambda p: (lambda m: float(m[-1]) if m else None)(re.findall(p, tail))
    return dict(I=g(r'I:\s+(-?[\d.]+) LUFS'), LRA=g(r'LRA:\s+([\d.]+) LU'), TP=g(r'Peak:\s+(-?[\d.inf]+) dBFS'))


def load_words(path):
    w = json.load(open(path, encoding='utf-8'))
    if isinstance(w, dict):
        w = w.get('words') or w.get('segments') or []
    return [x for x in w if str(x.get('w', x.get('word', ''))).strip()]


# ---------------------------------------------------------------- measure / summarize
def measure(v, keep_frames=True):
    info = probe(v)
    rgb = decode(v)
    pf = frame_metrics(rgb)
    trans, aux = detect_transitions(rgb)
    setups = segment(len(rgb), trans)
    samples = full_res_samples(v, info)
    lo = loudness(v) if info['audio'] else dict(I=None, LRA=None, TP=None)
    raw = dict(video=os.path.abspath(v), info=info, n=len(rgb), perframe=pf, transitions=trans, setups=setups,
               samples=samples, loudness=lo)
    if keep_frames:
        raw['rgb'] = rgb
    return raw


def raw_to_json(raw):
    """Per-frame arrays as rounded lists (for profile.json)."""
    pf = {}
    for k, a in raw['perframe'].items():
        dig = 5 if k == 'zoom' else 4 if k in ('sat', 'edge', 'roll') else 2
        pf[k] = [None if not np.isfinite(x) else round(float(x), dig) for x in a]
    return pf


def json_to_perframe(pf):
    return {k: np.array([np.nan if x is None else x for x in a], np.float32) for k, a in pf.items()}


def _still_mask(pf, a, b):
    tx, ty, z, ro = pf['tx'][a:b], pf['ty'][a:b], pf['zoom'][a:b], pf['roll'][a:b]
    ok = np.isfinite(tx)
    sp = np.hypot(tx, ty)
    st = ok & (sp < 0.6) & (np.abs(z - 1) < 0.0006) & (np.abs(ro) < 0.03)
    return st, ok


def summarize(raw, acts=None, t0=None, t1=None, still_share=0.8, device_view_s=1.5):
    """Judged numbers. acts: list of act boundaries in seconds (default thirds). t0/t1: only that stretch."""
    pf, n = raw['perframe'], raw['n']
    dur = n / FPS
    a0 = 0 if t0 is None else max(0, int(round(t0 * FPS)))
    a1 = n if t1 is None else min(n, int(round(t1 * FPS)))
    T0, T1 = a0 / FPS, a1 / FPS
    trans = [x for x in raw['transitions'] if a0 <= x['shot'] < a1]
    tframes = set()
    for x in raw['transitions']:
        tframes.update(range(x['span'][0] - 2, x['span'][1] + 3))
    # setups clipped to the stretch
    setups = []
    still_all, _ = _still_mask(pf, 0, n)
    for s in raw['setups']:
        a, b = max(s['a'], a0), min(s['b'], a1)
        if b - a < 3:
            continue
        inner = [k for k in range(a + 1, b) if k not in tframes] or list(range(a + 1, b))
        idx = np.array(inner)
        tx, ty = pf['tx'][idx], pf['ty'][idx]
        ok = np.isfinite(tx)
        st = still_all[idx]
        sp = np.hypot(tx, ty)
        g = lambda arr: float(np.nanmean(arr)) if np.isfinite(arr).any() else None
        setups.append(dict(n=s['n'], a=a, b=b, t0=round(a / FPS, 2), t1=round(b / FPS, 2), dur=round((b - a) / FPS, 2),
                           **{'in': s['in'] if s['a'] >= a0 else {'kind': 'clipped'}},
                           pan=round(g(sp) * FPS, 1) if ok.any() else None,
                           zoom=round(g(pf['zoom'][idx] - 1) * FPS * 100, 2) if ok.any() else None,
                           roll=round(g(pf['roll'][idx]) * FPS, 2) if ok.any() else None,
                           still=round(float(st[ok].mean()), 3) if ok.any() else None,
                           resid=round(g(pf['resid'][idx]), 2) if ok.any() else None,
                           col=round(float(pf['col'][a:b].mean()), 1), sat=round(float(pf['sat'][a:b].mean()), 3),
                           lum=round(float(pf['lum'][a:b].mean()), 1), edge=round(float(pf['edge'][a:b].mean()), 4)))
    lens = [s['dur'] for s in setups]
    dis = [x['frames'] for x in trans if x['kind'] == 'dissolve']
    # dead-still camera: setups mostly still; one setup up to 1.5 s (the device / dashcam view) is allowed
    stills = sorted([s for s in setups if s['still'] is not None and s['still'] > still_share], key=lambda s: s['dur'])
    allowed = next((s for s in stills if s['dur'] <= device_view_s), None)
    dead = [s for s in stills if s is not allowed]
    # acts
    if t0 is not None or t1 is not None:
        acts = [T0, T1]
    elif not acts:
        acts = [0, dur / 3, 2 * dur / 3, dur]
    sm = raw['samples']
    act = []
    for i, (x, y) in enumerate(zip(acts[:-1], acts[1:])):
        fa, fb = int(round(x * FPS)), min(n, int(round(y * FPS)))
        sh = [q['sharp'] for q in sm if x <= q['t'] < y]
        act.append(dict(act=i + 1, t0=x, t1=y, col=round(float(pf['col'][fa:fb].mean()), 1),
                        sat=round(float(pf['sat'][fa:fb].mean()), 3), lum=round(float(pf['lum'][fa:fb].mean()), 1),
                        edge=round(float(pf['edge'][fa:fb].mean()), 4),
                        sharp=round(float(np.median(sh)), 1) if sh else None))
    caps = [q for q in sm if T0 <= q['t'] < T1 and q.get('cap_h')]
    med = lambda k: (round(float(np.median([q[k] for q in caps if q.get(k) is not None])), 3)
                     if any(q.get(k) is not None for q in caps) else None)
    d = pf['diff'][max(a0, 1):a1]
    out = dict(
        t0=round(T0, 3), t1=round(T1, 3), duration=round(T1 - T0, 3), n_setups=len(setups),
        setup_mean=round(float(np.mean(lens)), 2) if lens else None,
        setup_median=round(float(np.median(lens)), 2) if lens else None,
        cuts=sum(x['kind'] == 'cut' for x in trans),
        blends=[dict(f=x['f'], t=x['t'], frames=x['frames'], alpha=x['alpha']) for x in trans if x['kind'] == 'blend'],
        dissolves=[dict(t0=x['t0'], t1=x['t1'], frames=x['frames'], alpha=x['alpha']) for x in trans if x['kind'] == 'dissolve'],
        dissolve_frames=dict(min=min(dis), median=float(np.median(dis)), max=max(dis)) if dis else None,
        gradual=[dict(t=x['t'], frames=x['frames']) for x in trans if x['kind'] == 'gradual'],
        dead_still_s=round(sum(s['dur'] for s in dead), 2),
        dead_still=[f"{s['t0']:.2f}-{s['t1']:.2f}" for s in sorted(dead, key=lambda s: s['t0'])],
        diff_median=round(float(np.median(d)), 2) if len(d) else None,
        acts=act,
        caption=dict(h=med('cap_h'), y=med('cap_y'), outline=med('cap_ol'), share=round(len(caps) / max(1, sum(T0 <= q['t'] < T1 for q in sm)), 2)),
        setups=setups)
    if t0 is None and t1 is None:
        out['loudness'] = raw['loudness']
    return out


# ---------------------------------------------------------------- sheets
def font(size):
    from PIL import ImageFont
    for f in ('C:/Windows/Fonts/arialbd.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def tile(imgs, labels, cols, out, tw, lh=18, bg=(28, 28, 28), fs=13, row_labels=None, quality=82):
    """Grid of PIL images (all resized to tw wide, 9:16), label above each."""
    from PIL import Image, ImageDraw
    th = tw * 16 // 9
    rows = (len(imgs) + cols - 1) // cols
    S = Image.new('RGB', (cols * (tw + 3) + 3, rows * (th + lh + 3) + 3), bg)
    d = ImageDraw.Draw(S); f = font(fs)
    for i, (im, lb) in enumerate(zip(imgs, labels)):
        x = 3 + (i % cols) * (tw + 3); y = 3 + (i // cols) * (th + lh + 3)
        if im.size != (tw, th):
            im = im.resize((tw, th), Image.LANCZOS)
        S.paste(im, (x, y + lh)); d.text((x + 2, y + 2), lb, fill=(255, 230, 80), font=f)
    S.save(out, quality=quality)
    return S.size


def from_rgb(raw, k):
    from PIL import Image
    return Image.fromarray(raw['rgb'][min(max(0, k), raw['n'] - 1)])


def beats_sheet(raw, setups, out, tw=160):
    imgs, labs = [], []
    for s in setups:
        a, b = s['a'], s['b']
        for lab, k in (('start', a + 2), ('mid', (a + b) // 2), ('end', b - 3)):
            imgs.append(from_rgb(raw, k)); labs.append(f"#{s['n']} {lab} {k / FPS:.2f}")
    return tile(imgs, labs, 9, out, tw, fs=12)


def transition_strips(raw, trans, out_dir, prefix='', tw=96, per_row=13):
    """One JPEG per transition: every frame through it, labelled with frame numbers."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for x in trans:
        s, e = x['span']
        pad = 3 if x['kind'] in ('cut', 'blend') else 4
        a, b = max(0, s - pad), min(raw['n'] - 1, e + pad)
        ks = list(range(a, b + 1))
        labs = [f'f{k}' + ('*' if s <= k <= e and x['kind'] != 'cut' else '') for k in ks]
        labs[0] = f"{x['kind'][:4]} {labs[0]}"
        p = os.path.join(out_dir, f"{prefix}{x['t']:06.2f}_{x['kind']}.jpg")
        tile([from_rgb(raw, k) for k in ks], labs, min(per_row, len(ks)), p, tw, lh=15, fs=11)
        paths.append(p)
    return paths


def setup_frame_name(s):
    return f"s{s['n']:02d}_{s['t0']:05.2f}.jpg"


# ---------------------------------------------------------------- profile (used by ref_profile.py and compare_video.py)
def build_profile(v, out_dir, acts=None, words=None, frames=True, sheets=True):
    """Measure v and write out_dir/profile.json (+ beats.jpg, transitions/*.jpg, frames/*.jpg).
    Returns (raw, profile dict). raw keeps the decoded 180x320 frames for further sheets."""
    import time
    t = time.time()
    os.makedirs(out_dir, exist_ok=True)
    raw = measure(v)
    dur = raw['n'] / FPS
    if not acts:
        acts = [0, round(dur / 3, 2), round(2 * dur / 3, 2), round(dur, 2)]
    s = summarize(raw, acts)
    setups = s.pop('setups')
    wd = None
    if words:
        w = load_words(words)
        wd = dict(n=len(w), wps=round(len(w) / dur, 2))
    if frames:
        fd = os.path.join(out_dir, 'frames'); os.makedirs(fd, exist_ok=True)
        for f in os.listdir(fd):
            if f.endswith('.jpg'):
                os.remove(os.path.join(fd, f))
        for st in setups:
            name = setup_frame_name(st)
            grab(v, (st['a'] + st['b']) / 2 / FPS, 540, 960).save(os.path.join(fd, name), quality=80)
            st['frame'] = 'frames/' + name
    if sheets:
        beats_sheet(raw, setups, os.path.join(out_dir, 'beats.jpg'))
        td = os.path.join(out_dir, 'transitions'); os.makedirs(td, exist_ok=True)
        for f in os.listdir(td):
            if f.endswith('.jpg'):
                os.remove(os.path.join(td, f))
        transition_strips(raw, raw['transitions'], td)
    prof = dict(version=1, video=os.path.basename(v), source=os.path.abspath(v), acts=acts, summary=s, setups=setups, words=wd,
                raw=dict(n=raw['n'], info=raw['info'], perframe=raw_to_json(raw), transitions=raw['transitions'],
                         setups=raw['setups'], samples=raw['samples'], loudness=raw['loudness']))
    with open(os.path.join(out_dir, 'profile.json'), 'w', encoding='utf-8') as f:
        json.dump(prof, f, separators=(',', ':'))
    prof['seconds'] = round(time.time() - t, 1)
    return raw, prof


def load_profile(path):
    """profile.json (or its folder) -> (profile dict, raw dict usable by summarize())."""
    if os.path.isdir(path):
        path = os.path.join(path, 'profile.json')
    prof = json.load(open(path, encoding='utf-8'))
    r = prof['raw']
    raw = dict(n=r['n'], info=r['info'], perframe=json_to_perframe(r['perframe']), transitions=r['transitions'],
               setups=r['setups'], samples=r['samples'], loudness=r['loudness'])
    prof['_dir'] = os.path.dirname(os.path.abspath(path))
    return prof, raw


def _f(x, fmt='{}'):
    return '-' if x is None else fmt.format(x)


def text_summary(s, words=None, setups=None):
    """Short text block for the console."""
    L = [f"duration {s['duration']:.1f} s, {s['n_setups']} setups (mean {s['setup_mean']} s, median {s['setup_median']} s)",
         f"transitions: {s['cuts']} cuts, {len(s['dissolves'])} dissolves, {len(s['gradual'])} gradual (in-world), "
         f"{len(s['blends'])} blended frames at cuts"
         + (' at ' + ', '.join(f"f{b['f']} {b['t']:.2f}s" for b in s['blends']) if s['blends'] else '')]
    if s['dissolve_frames']:
        d = s['dissolve_frames']
        L.append(f"dissolve frames min {d['min']} median {d['median']:g} max {d['max']}: "
                 + ' '.join(str(x['frames']) for x in s['dissolves']))
    L.append(f"dead-still camera {s['dead_still_s']} s {s['dead_still']}; median frame change {s['diff_median']}")
    for a in s['acts']:
        L.append(f"act {a['act']} {a['t0']:.1f}-{a['t1']:.1f}: colourfulness {a['col']} sat {a['sat']} luma {a['lum']} "
                 f"edge {a['edge']} sharp {a['sharp']}")
    c = s['caption']
    L.append(f"caption: text {c['h']} px, centre {c['y']} of height, outline ~{c['outline']} px, "
             f"found on {c['share'] * 100:.0f}% of samples")
    if s.get('loudness'):
        lo = s['loudness']
        L.append(f"loudness {lo['I']} LUFS, LRA {lo['LRA']} LU, true peak {lo['TP']} dBTP")
    if words:
        L.append(f"words {words['n']}, {words['wps']} words/s")
    if setups:
        L.append(' #  start   dur  in           pan px/s  zoom %/s  roll deg/s  still')
        for st in setups:
            inn = st['in']['kind'] + (f" {st['in']['frames']}f" if st['in'].get('frames', 1) > 1 else '')
            L.append(f"{st['n']:2d} {st['t0']:6.2f} {st['dur']:5.2f}  {inn:12s} {_f(st['pan']):>8} {_f(st['zoom']):>9} "
                     f"{_f(st['roll']):>11}  {_f(st['still'])}")
    return '\n'.join(L)
