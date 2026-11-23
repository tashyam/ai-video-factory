# Sound for a /3d-video-studio project: synthesized SFX + ambience beds + original score under the user's voice, mixed to
# -14 LUFS integrated / -1.5 dBTP (the reference measures about -14 LUFS, heavily levelled, never silent).
#
#   python mix.py <project>            reads  <project>/audio/cues.json   (node film.mjs cues <project>)
#                                             <project>/audio/vo.wav       (the voice; any rate, mono or stereo)
#                                             <project>/audio/vo.words.json (word times: the music ducks under speech)
#                                      writes <project>/audio/mix.wav       (48 kHz, 24-bit stereo, exact video length)
#                                             <project>/audio/stems/{voice,music,sfx}.wav, <project>/audio/sound.md
#
# Level rules (from claude-animated-shorts' measured mix, MIT, and the reference loudness):
# - voice: gain only (no EQ, no compression);
# - events: their naive level (LU vs. the voice, sfx_lib.SOUNDS) minus 6 dB, measured as max momentary loudness;
# - beds: integrated level relative to the voice, faded in/out at shot edges;
# - music: about 9.5 LU under the voice, ducked another 5 dB while words are spoken (keyed by the word times);
# - master: gain to -14 LUFS, then a 4x-oversampled look-ahead limiter at -1.5 dBTP.
import json, os, sys, time
import numpy as np
from scipy import ndimage, signal
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from dsp import SR, ns, st, dbg, read_wav, write_wav, integrated, momentary_max, true_peak, lra, fades, lp
import sfx_lib as L
from score import score

TARGET, CEIL, SFX_DB, MUSIC_LU, DUCK_DB = -14.0, -1.5, -6.0, -9.5, -5.0


def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def load_voice(path, n):
    x, sr = read_wav(path)
    v = x.mean(0)
    if sr != SR:
        from math import gcd
        g = gcd(SR, sr); v = signal.resample_poly(v, SR // g, sr // g)
    out = np.zeros(n); out[:min(n, len(v))] = v[:n]
    return st(out)


def duck_curve(words, n, depth=DUCK_DB, pre=0.08, post=0.15, att=0.06, rel=0.45):
    ctrl = 1000; nc = int(n / SR * ctrl) + 2; va = np.zeros(nc)
    sp = []
    for w in words:
        s, e = float(w["s"]), float(w["e"])
        if sp and s - sp[-1][1] < 0.3: sp[-1][1] = max(sp[-1][1], e)
        else: sp.append([s, e])
    for s, e in sp: va[max(0, int((s - pre) * ctrl)): int((e + post) * ctrl)] = 1
    env = np.zeros(nc); e = 0.0; ka, kr = 1 - np.exp(-1 / (att * ctrl)), 1 - np.exp(-1 / (rel * ctrl))
    for i in range(nc): e += (va[i] - e) * (ka if va[i] > e else kr); env[i] = e
    return dbg(np.interp(np.arange(n) / SR, np.arange(nc) / ctrl, depth * env))


def limiter(x, ceil_db=CEIL, look=0.003, rel=0.08):
    c = dbg(ceil_db); n = x.shape[1]
    up = np.abs(signal.resample_poly(x, 4, 1, axis=-1)).max(0)
    pk = np.pad(up, (0, max(0, 4 * n - len(up))))[:4 * n].reshape(n, 4).max(1)
    gr = np.minimum(1.0, c / np.maximum(pk, 1e-12)); La = max(1, ns(look))
    g = ndimage.minimum_filter1d(gr, 2 * La + 1, mode="nearest")
    kr = 1 - np.exp(-1 / (rel * SR)); out = g.copy(); cur = 1.0
    idx = np.flatnonzero(g < 1.0)
    if len(idx):
        for i in range(idx[0], min(n, idx[-1] + ns(rel * 8))):
            cur = min(g[i], cur + (1 - cur) * kr); out[i] = cur
    out = np.minimum(ndimage.uniform_filter1d(out, 2 * La + 1, mode="nearest"), 1.0)
    return x * out[None, :], out


def main(proj):
    A = os.path.join(proj, "audio")
    cues = json.load(open(os.path.join(A, "cues.json"), encoding="utf-8"))
    dur = float(cues["dur"]); n = ns(dur)
    words = json.load(open(os.path.join(A, "vo.words.json"), encoding="utf-8"))
    words = words["words"] if isinstance(words, dict) else words
    voice = load_voice(os.path.join(A, "vo.wav"), n)
    Lv = integrated(voice)
    log(f"voice {Lv:.1f} LUFS, {dur:.2f} s, {len(cues['events'])} events, {len(cues['beds'])} beds")
    sfx = np.zeros((2, n)); rows = []
    # beds: render each span (plus 0.4 s fades), level relative to the voice
    for i, b in enumerate(cues["beds"]):
        kind = b["kind"]
        if kind == "none" or kind not in L.SOUNDS: continue
        t0, t1 = max(0.0, b["t0"] - 0.2), min(dur, b["t1"] + 0.2)
        x = L.render(kind, seed=100 + i, dur=t1 - t0)[:, :ns(t1 - t0)]
        Lb = integrated(x)
        g = dbg(Lv + L.SOUNDS[kind][1] + b.get("gain", 0) - Lb) if np.isfinite(Lb) else 0
        x = fades(x * g, 0.35, 0.35)
        a = ns(t0); sfx[:, a:a + x.shape[1]] += x[:, :n - a]
        rows.append((t0, kind, "bed", f"{L.SOUNDS[kind][1] + b.get('gain', 0):+.0f} LU", b.get("why", "")))
    # events
    for i, e in enumerate(sorted(cues["events"], key=lambda e: e["t"])):
        name = e["name"]
        if name not in L.SOUNDS: log("unknown sound", name); continue
        x = L.render(name, e.get("args"), seed=1000 + i)
        Lm = momentary_max(x)
        lvl = L.SOUNDS[name][1] + SFX_DB + e.get("gain", 0)
        if np.isfinite(Lm): x = x * dbg(Lv + lvl - Lm)
        p = float(e.get("pan", 0))
        if p: x = np.stack([x[0] * np.sqrt(max(0, 1 - p)), x[1] * np.sqrt(max(0, 1 + p))])
        a = ns(max(0.0, e["t"])); m = min(x.shape[1], n - a)
        if m > 0: sfx[:, a:a + m] += x[:, :m]
        rows.append((e["t"], name, "event", f"{lvl:+.0f} LU", e.get("why", "auto" if e.get("auto") else "")))
    # music
    M = cues.get("music") or {}
    music = np.zeros((2, n))
    if M.get("on", True):
        acts = [(a["t0"], a["t1"], a["mood"]) for a in M.get("acts", [])] or [(0, dur, "day")]
        music = score(dur, acts, M.get("stops", []), M.get("tag"), M.get("bpm", 112), M.get("seed", 7))[:, :n]
        if music.shape[1] < n: music = np.pad(music, ((0, 0), (0, n - music.shape[1])))
        Lm = integrated(music)
        if np.isfinite(Lm): music *= dbg(Lv + MUSIC_LU + M.get("gain", 0) - Lm)
        music *= duck_curve(words, n)[None, :]
    mix = voice + music + sfx
    g = dbg(TARGET - integrated(mix)); mix *= g
    mix, gr = limiter(mix)
    os.makedirs(os.path.join(A, "stems"), exist_ok=True)
    write_wav(os.path.join(A, "mix.wav"), mix)
    for nm, x in (("voice", voice), ("music", music), ("sfx", sfx)): write_wav(os.path.join(A, "stems", nm + ".wav"), x * g)
    I, tp, lr = integrated(mix), true_peak(mix), lra(mix)
    rep = [f"# Sound for {os.path.basename(os.path.abspath(proj))}", "",
           f"- mix.wav: {dur:.3f} s, 48 kHz, 24-bit stereo. Integrated **{I:.1f} LUFS**, true peak **{tp:.1f} dBTP**, LRA {lr:.1f} LU,"
           f" limiter max reduction {-20 * np.log10(gr.min() + 1e-12):.1f} dB.",
           f"- stems at mix gain: voice {integrated(voice * g):.1f}, music {integrated(music * g) if music.any() else float('nan'):.1f}, sfx {integrated(sfx * g):.1f} LUFS.",
           "", "| t (s) | sound | kind | level | note |", "|---|---|---|---|---|"]
    rep += [f"| {t:.2f} | {nm} | {k} | {lv} | {w} |" for t, nm, k, lv, w in sorted(rows)]
    open(os.path.join(A, "sound.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    log(f"mix.wav  {I:.1f} LUFS  {tp:.1f} dBTP  LRA {lr:.1f}")


if __name__ == "__main__":
    main(sys.argv[1])
