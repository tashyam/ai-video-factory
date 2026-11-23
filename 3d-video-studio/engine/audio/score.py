# Original comedy score for /3d-video-studio Shorts, composed by rule and synthesized with instruments.py (MIT, see
# LICENSE-third-party.txt). One "sneaky schemer" theme in D minor (i i iv V), arranged per colour act:
#   day   : pizzicato bass + pizzicato melody, glockenspiel accents, light snare on 2 and 4 (bouncy, sly)
#   night : walking pizz bass, vibraphone melody, brushes (cool, jazzy; the scheme at its peak)
#   rain  : warm pad chords, music box melody at half density, bass on the downbeat only (quiet, the turn)
# Stops: the music drops out ~0.45 s before each "But" turn (a beat of silence sells the turn) and comes back on the
# next bar line. Tag: a major-key sting (D major arpeggio, timpani, cymbal) on the tag sentence, then a short tail.
# Everything sits on one beat grid from t = 0 (bpm), so cuts and sound effects can be placed on beats if wanted.
import numpy as np
from dsp import SR, ns, rng, pan, fades, make_ir, convolve_st, lp
import instruments as I

PROG = [(38, [62, 65, 69]), (38, [62, 65, 69]), (43, [62, 67, 70]), (45, [61, 64, 69])]    # bass root, chord (Dm Dm Gm A)
BASS = [[0, 7, 3, 7], [0, 7, 3, 7], [0, 7, 3, 7], [0, 7, 4, 7]]                            # semitones above the root
MEL = [  # eighth notes per bar, None = rest (tiptoe motif)
    [62, None, 64, None, 65, 64, 62, None], [61, None, 62, None, None, None, None, None],
    [67, None, 69, None, 70, 69, 67, None], [64, None, 61, None, 57, None, None, None]]
MEL_B = [  # answer phrase for the second half of each 8-bar block
    [69, None, 70, 69, 67, None, 65, None], [64, None, 65, None, 62, None, None, None],
    [70, None, 69, None, 67, None, 65, 64], [64, None, 65, None, 64, 61, 57, None]]


def _add(buf, x, t, g=1.0, p=0.0):
    x = pan(x, p) if np.ndim(x) == 1 else x
    i = ns(t)
    a, b = max(0, i), min(buf.shape[1], i + x.shape[1])
    if b > a:
        buf[:, a:b] += g * x[:, a - i:b - i]


def score(dur, acts, stops=(), tag=None, bpm=112, seed=7):
    """acts: [(t0, t1, 'day'|'night'|'rain')]; stops: times of the 'But' turns; tag: time of the tag sentence"""
    r = rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    out = np.zeros((2, ns(dur + 3)))
    mood_at = lambda t: next((m for a, b, m in acts if a <= t < b), acts[-1][2] if acts else "day")
    silent = [(s - 0.45, s + 0.05) for s in stops]
    resume = [np.ceil((s + 0.05) / bar) * bar for s in stops]          # restart on the next bar line
    end = tag if tag is not None else dur
    def muted(t):
        return any(a <= t < res for (a, _), res in zip(silent, resume)) or t >= end - 0.05
    nb = int(np.ceil(end / bar)) + 1
    for k in range(nb):
        t0 = k * bar
        if t0 >= end: break
        m = mood_at(t0)
        root, chord = PROG[k % 4]
        mel = (MEL_B if (k // 4) % 2 else MEL)[k % 4]
        # bass
        for j, semi in enumerate(BASS[k % 4]):
            tb = t0 + j * beat
            if muted(tb) or (m == "rain" and j > 0): continue
            f = I.m2f(root + semi)
            _add(out, I.pluck(f, 0.85 if j == 0 else 0.65, r, dur=0.45 if m != "rain" else 1.4, bright=0.35), tb, 0.9)
        # chords
        if m == "rain" and not muted(t0):
            _add(out, I.pad([I.m2f(n - 12) for n in chord], bar * 0.95, 0.5, r, att=0.4, rel=0.6, warm=800), t0, 0.55)
        # melody
        for j, note in enumerate(mel):
            if note is None: continue
            tm = t0 + j * beat / 2
            if muted(tm): continue
            if m == "day":
                _add(out, I.pluck(I.m2f(note + 12), 0.6, r, dur=0.3, bright=0.6), tm, 0.55, 0.25)
                if j == 0: _add(out, I.glock(I.m2f(note + 12), 0.45, r, dur=1.0), tm, 0.22, -0.3)
            elif m == "night":
                _add(out, I.vibes(I.m2f(note), 0.55, r, dur=0.9, damp=0.35), tm + (beat * 0.08 if j % 2 else 0), 0.6, 0.2)
            elif j % 4 == 0:
                _add(out, I.musicbox(I.m2f(note + 12), 0.5, r, dur=1.4), tm, 0.5, 0.15)
        # percussion
        for j in range(4):
            tp = t0 + j * beat
            if muted(tp): continue
            if m == "day" and j in (1, 3): _add(out, I.snare(0.25, r, dur=0.18, snappy=0.6), tp, 0.25, 0.1)
            if m == "night":
                _add(out, I.brush(0.35 if j in (1, 3) else 0.2, r, dur=0.3, swish=j in (1, 3)), tp, 0.3, -0.1)
    # the tag sting: D major arpeggio on glock + vibes, timpani, cymbal, held pad
    if tag is not None:
        for j, note in enumerate([62, 66, 69, 74, 78]):
            _add(out, I.glock(I.m2f(note + 12), 0.6, r, dur=1.8), tag + j * 0.07, 0.4, -0.2 + 0.1 * j)
            _add(out, I.vibes(I.m2f(note), 0.5, r, dur=2.0), tag + j * 0.07, 0.35, 0.2 - 0.1 * j)
        _add(out, I.timpani(I.m2f(38), 0.8, r, dur=2.2), tag, 0.7)
        _add(out, I.cymbal(0.5, r, dur=2.4), tag + 0.02, 0.3)
        _add(out, I.pad([I.m2f(n) for n in (50, 54, 57, 62)], 2.2, 0.55, r, att=0.05, rel=1.0, warm=1400), tag, 0.5)
    # a little room
    wet = convolve_st(out, make_ir(1.1, seed + 3, pre=0.01, hf=1.3))
    out = out + 0.16 * lp(wet, 6000)
    return fades(out[:, : ns(dur)], 0.0, 0.3)
