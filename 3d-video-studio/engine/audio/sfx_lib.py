# Sound effects for /3d-video-studio Shorts, all synthesized in numpy (no samples, no downloads). Built on dsp.py and the
# generic generators in sfx_core.py (both MIT, see LICENSE-third-party.txt).
#
# SOUNDS maps a cue name to (generator, naive level, kind):
#   generator(r, **opts) -> mono (n,) or stereo (2, n) array at 48 kHz
#   naive level: LU relative to the voice (max momentary loudness for events, integrated for beds); the mix places
#                events SFX_DB (-6 dB) under it, like the reference shorts' "SFX clearly under the voice" balance
#   kind: 'event' (one-shot) or 'bed' (ambience; the mix loops/crops it to the requested span)
# Add a new sound: write a generator here, register it in SOUNDS, list it in engine/API.md ("Sound").
import numpy as np
from dsp import (SR, TAU, ns, tt, rng, lp, hp, bp, peq, resbank, colored, smooth_noise, fades, shape, phase, modal, pan, st, widen)
import sfx_core as G


def _put(buf, x, t, g=1.0):
    x = np.asarray(x, float)
    i = ns(t)
    if x.ndim == 1:
        a, b = max(0, i), min(buf.shape[-1], i + len(x))
        if b > a:
            if buf.ndim == 1: buf[a:b] += g * x[a - i:b - i]
            else: buf[:, a:b] += g * x[None, a - i:b - i]
    else:
        a, b = max(0, i), min(buf.shape[-1], i + x.shape[1])
        if b > a: buf[:, a:b] += g * x[:, a - i:b - i]


def _env(t, att, dur, rel):
    return np.clip(t / max(att, 1e-4), 0, 1) * np.clip((dur - t) / max(rel, 1e-4), 0, 1)


# ================================================================ cars
def brake_squeal(r, dur=0.9, f0=None):
    """brake pads squealing: a jittery whistle around 2.4-3.4 kHz with partials + tyre hiss"""
    f0 = f0 or r.uniform(2400, 3400)
    n, t = ns(dur), tt(dur)
    f = f0 * (1 + 0.04 * np.sin(TAU * r.uniform(5, 9) * t)) * (1 - 0.06 * t / dur) + 50 * smooth_noise(n, r, 14)
    ph = phase(f)
    tone = np.sin(ph) + 0.35 * np.sin(2 * ph + 1) + 0.12 * np.sin(3 * ph + 2)
    am = 0.7 + 0.3 * smooth_noise(n, r, 25)
    hiss = bp(r.standard_normal(n), 1500, 7000, 1) * 0.3
    return fades((tone * am * 0.6 + hiss) * _env(t, 0.04, dur, 0.2), 0.002, 0.05)


def tyre_screech(r, dur=1.2):
    """tyres skidding: a fluttering harmonic squeal (~1 kHz) over rough rubber roar"""
    n, t = ns(dur), tt(dur)
    f = r.uniform(950, 1250) * (1 - 0.12 * t / dur) * (1 + 0.03 * smooth_noise(n, r, 8))
    ph = phase(f)
    tone = sum(a * np.sin(k * ph + r.uniform(0, TAU)) for k, a in [(1, 1), (2, .6), (3, .35), (4, .2)])
    flutter = 0.55 + 0.45 * np.abs(np.sin(phase(r.uniform(30, 45) + 5 * smooth_noise(n, r, 3))))
    roar = bp(r.standard_normal(n), 600, 4000, 2) * 0.7
    return fades((tone * 0.5 + roar) * flutter * _env(t, 0.05, dur, 0.3), 0.002, 0.05)


PANEL = [(170, 7, 1.0), (300, 9, 0.9), (510, 11, 0.75), (860, 13, 0.55), (1380, 15, 0.4), (2250, 17, 0.28), (3600, 19, 0.15)]


def glass_tinkle(r, dur=1.0, amount=1.0):
    """safety glass and plastic bits falling: a cloud of bright clinks thinning out"""
    y = G.rattle(dur, r, 70 * amount, np.exp(-np.linspace(0, 1, ns(dur)) * 3.5))
    for k in range(int(4 * amount)):
        _put(y, G.clink(r, r.uniform(3500, 6500), 0.25, 1.3) * r.uniform(0.5, 1.0), r.uniform(0.02, dur * 0.6))
    return y


def crunch(r, size=1.0, glass=1.0):
    """rear-end crash: body thump, metal crumple through panel modes, plastic crack, debris + glass"""
    dur = 2.0
    n, t = ns(dur), tt(dur)
    nz = r.standard_normal(n)
    y = np.exp(-t / 0.13) * np.sin(phase(68 * (1 + 0.9 * np.exp(-t / 0.02)))) * 2.0 * size
    y += bp(nz, 250, 9000, 2) * np.exp(-t / 0.05) * 1.6
    metal = resbank(nz * np.exp(-t / 0.09), [(f * r.uniform(0.92, 1.08), q, g) for f, q, g in PANEL])
    y += metal / (np.abs(metal).max() + 1e-9) * 1.1
    crumple = G.creak(0.5, r, 85, 30, modes=PANEL, shape_pts=[(0, 1), (0.3, 0.8), (1, 0)], rough=0.35, noise=0.25)
    _put(y, crumple / (np.abs(crumple).max() + 1e-9) * 0.7, 0.01)
    _put(y, G.rattle(1.3, r, 45, np.exp(-np.linspace(0, 1, ns(1.3)) * 3), heavy=True) * 0.6, 0.05)
    if glass: _put(y, glass_tinkle(r, 1.1, glass) * 0.7, 0.04)
    return fades(y, 0.0, 0.2)


def horn(r, dur=0.55, f=(415.0, 523.0)):
    """car horn: two buzzy tones, a little nasal"""
    t = tt(dur)
    y = np.zeros(len(t))
    for f0 in f:
        ph = phase(f0 * (1 + 0.004 * np.sin(TAU * 6 * t)))
        y += sum(np.sin(k * ph) / k ** 0.85 for k in range(1, 14))
    y = peq(lp(y, 3800), 1800, 6, 1.2)
    return fades(y * _env(t, 0.015, dur, 0.04), 0.002, 0.03)


def horn_short(r):
    y = np.zeros(ns(0.5)); _put(y, horn(r, 0.14), 0); _put(y, horn(r, 0.2), 0.2); return y


def engine_pass(r, dur=2.4, v=24.0, d0=3.5, f0=46.0, side=1.0):
    """a car driving past: engine harmonics + tyre roar with Doppler, distance gain and a moving pan (stereo)"""
    n, t = ns(dur), tt(dur)
    x = v * (t - dur / 2)
    dist = np.sqrt(x ** 2 + d0 ** 2)
    fac = 343.0 / (343.0 + v * x / dist)
    ph = phase(f0 * fac * (1 + 0.02 * smooth_noise(n, r, 2)))
    y = sum(a * np.sin(k * ph + r.uniform(0, TAU)) for k, a in [(1, 1), (2, .8), (3, .6), (4, .45), (6, .3), (8, .2)])
    y = y + bp(colored(n, r, 1.0), 90, 1500, 1) * 1.4
    y *= (d0 / dist) ** 1.2
    th = (np.clip(side * x / 12.0, -1, 1) + 1) * np.pi / 4
    return fades(np.stack([y * np.cos(th), y * np.sin(th)]) * np.sqrt(2), 0.05, 0.2)


def engine_rev(r, dur=1.0):
    """engine revving up: harmonics gliding up with growl"""
    n, t = ns(dur), tt(dur)
    f = 40 + 60 * (t / dur) ** 0.7
    ph = phase(f * (1 + 0.03 * smooth_noise(n, r, 9)))
    y = sum(a * np.sin(k * ph) for k, a in [(1, 1), (2, .9), (3, .7), (4, .5), (6, .35)])
    y += bp(colored(n, r, 0.8), 100, 2000, 1) * 0.6 * (t / dur)
    return fades(y * _env(t, 0.08, dur, 0.25), 0.01, 0.05)


def car_door(r):
    """car door shutting: latch click + heavy thump"""
    dur = 0.6
    t = tt(dur)
    y = np.exp(-t / 0.06) * np.sin(phase(90 * (1 + 0.4 * np.exp(-t / 0.01)))) * 1.4
    y += lp(r.standard_normal(len(t)), 900) * np.exp(-t / 0.03) * 0.8
    _put(y, G.clink(r, 2200, 0.06) * 0.5, 0.0)
    return fades(y, 0, 0.05)


def seatbelt(r):
    y = np.zeros(ns(0.25)); _put(y, G.clink(r, 2600, 0.08), 0); _put(y, G.clink(r, 1900, 0.1), 0.06); return y


def road_bed(dur, r, level=1.0):
    """roadside air: distant traffic roar, breeze, an occasional car passing far away"""
    n = ns(dur)
    out = G.breeze(dur, r, 0.6, 0.15, 800)
    roar = lp(colored(n, r, 1.6), 500, 2) * (0.75 + 0.25 * smooth_noise(n, r, 0.2))
    out += st(roar) * 0.8
    tm = r.uniform(0.5, 3.0)
    while tm < dur - 1:
        _put(out, engine_pass(r, 3.0, r.uniform(18, 28), r.uniform(10, 25), r.uniform(40, 55), r.choice([-1, 1])) * 0.5, tm)
        tm += r.uniform(3.5, 7.0)
    return out * level


def car_interior_bed(dur, r):
    """inside a moving car: low engine drone, tyre rumble, a little wind on the glass"""
    n = ns(dur)
    t = np.arange(n) / SR
    ph = phase(38 * (1 + 0.015 * smooth_noise(n, r, 1.5)))
    eng = sum(a * np.sin(k * ph + r.uniform(0, TAU)) for k, a in [(1, 1), (2, .7), (3, .35), (4, .2)])
    rum = lp(colored(n, r, 2.0), 220, 2)
    wind = bp(colored(n, r, 0.8), 600, 3000, 1) * 0.25 * (0.8 + 0.2 * smooth_noise(n, r, 0.4))
    m = (eng * 0.6 + rum * 1.2 + wind)
    return widen(m, r, 9, 0.6)


# ================================================================ money, office, home
def cash_register(r):
    """'ka-ching': two key clacks, the bell, the drawer sliding out, coins"""
    dur = 1.5
    y = np.zeros(ns(dur))
    for t0 in (0.0, 0.07):
        tc = tt(0.05); _put(y, bp(r.standard_normal(len(tc)), 900, 5000, 2) * np.exp(-tc / 0.006) * 1.2, t0)
    for f0 in (2093.0, 2637.0):
        _put(y, modal(1.2, [(f0, 1.0, 0.45), (f0 * 2.76, 0.4, 0.2), (f0 * 5.4, 0.18, 0.08)], r) * 0.7, 0.12)
    td = tt(0.3)
    drawer = shape(r.standard_normal(len(td)), lambda T, F: np.exp(-0.5 * (np.log2(np.maximum(F[:, None], 20) / (400 + 1800 * T[None, :] / 0.3)) / 0.9) ** 2), 512, 128)
    _put(y, drawer * np.sin(np.pi * td / 0.3) * 0.5, 0.2)
    _put(y, G.rattle(0.5, r, 50) * 0.45, 0.32)
    return fades(y, 0, 0.1)


def coins(r, dur=0.8):
    return G.rattle(dur, r, 55, np.exp(-np.linspace(0, 1, ns(dur)) * 2))


def paper_flutter(r, dur=1.2, rate=55):
    """banknotes / papers flapping: short bright noise flaps"""
    y = np.zeros(ns(dur))
    for _ in range(int(rate * dur)):
        L = r.uniform(0.006, 0.02); tl = tt(L)
        f = r.uniform(900, 4000)
        _put(y, bp(r.standard_normal(len(tl)), f * 0.6, f * 1.6, 1) * np.sin(np.pi * tl / L) * r.uniform(0.3, 1.0), r.uniform(0, dur - L))
    return y * np.interp(np.arange(len(y)), [0, len(y) * 0.2, len(y)], [0.3, 1, 0.2])


def cash_burst(r):
    """the cash-burst transition: a big whoosh, notes flapping, a register 'ka-ching' at the peak"""
    y = np.zeros((2, ns(1.8)))
    _put(y, widen(G.whoosh(1.0, r, peak=0.28, f_lo=300, f_hi=2600, width=0.8, tail=0.3, air=0.25), r, 11, 0.8), 0.0)
    _put(y, widen(paper_flutter(r, 1.3, 70), r, 7, 1.0) * 0.8, 0.15)
    _put(y, cash_register(r) * 0.8, 0.25)
    return y


def paper_burst(r):
    y = np.zeros((2, ns(1.6)))
    _put(y, widen(G.whoosh(0.9, r, peak=0.25, f_lo=400, f_hi=3000, width=0.8, tail=0.28, air=0.3), r, 11, 0.8), 0.0)
    _put(y, widen(paper_flutter(r, 1.3, 90), r, 7, 1.0), 0.1)
    return y


def phone_ring(r, rings=2):
    """old desk phone: a bell hammered at ~20 Hz for 0.8 s, twice"""
    y = np.zeros(ns(rings * 1.6))
    for k in range(rings):
        for j in range(16):
            _put(y, modal(0.09, [(1250, 1.0, 0.05), (1250 * 2.3, 0.4, 0.03), (1250 * 3.9, 0.2, 0.02)], r) * (0.8 + 0.2 * (j % 2)), k * 1.6 + j * 0.05)
    return y


def stamp(r):
    """rubber stamp / folder slapped on a desk"""
    t = tt(0.35)
    y = np.exp(-t / 0.05) * np.sin(phase(120 * (1 + 0.5 * np.exp(-t / 0.008)))) + bp(r.standard_normal(len(t)), 300, 3000, 1) * np.exp(-t / 0.015) * 0.8
    return fades(y, 0, 0.05)


def keyboard(r, dur=1.2, rate=9):
    y = np.zeros(ns(dur))
    for _ in range(int(rate * dur)):
        tl = tt(0.03); _put(y, bp(r.standard_normal(len(tl)), 1500, 6000, 1) * np.exp(-tl / 0.004) * r.uniform(0.4, 1.0), r.uniform(0, dur - 0.03))
    return y


def room_bed(dur, r, hum=1.0):
    """quiet room tone: soft air, a 60 Hz fridge/light hum"""
    n = ns(dur)
    t = np.arange(n) / SR
    air = lp(colored(n, r, 1.2), 1200, 1) * 0.5
    h = (np.sin(TAU * 60 * t) + 0.4 * np.sin(TAU * 120 * t) + 0.15 * np.sin(TAU * 180 * t)) * 0.06 * hum
    return widen(air + h, r, 13, 0.7)


def tv_bed(dur, r):
    """a TV in the room: muffled talk (formant babble) under room tone"""
    y = st(G.babble(dur, r, 120, 1.0, 4.5, 0.85))
    return st(lp(y[0], 2500)) * 0.6 + room_bed(dur, r, 0.5)


# ================================================================ bodies and faces
def oof(r, kind="oof", base=None):
    return G.oof(r, kind, base)


def groan(r, dur=0.9, base=None):
    """a fake-injury groan: 'ohhh-uhh' falling"""
    base = base or r.uniform(110, 140)
    n = ns(dur); t = np.arange(n) / SR
    f0 = base * np.interp(t, [0, 0.15, dur], [1.15, 1.25, 0.8])
    forms = G.vowel_track(n, [(0, "o"), (dur * 0.5, "U"), (dur, "u")])
    amp = np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.2, 0, 1) * (1 + 0.15 * np.sin(TAU * 5.5 * t))
    return fades(G.vox(f0, forms, amp, r, 1.0, tilt=1.1, breath=0.3), 0.003, 0.05)


def neck_crack(r):
    """three bone cracks (the fake-neck gag)"""
    y = np.zeros(ns(0.3))
    for t0 in (0.0, 0.06, 0.1):
        tl = tt(0.04)
        c = hp(r.standard_normal(len(tl)), 1200) * np.exp(-tl / 0.0015) + modal(0.04, [(r.uniform(900, 1600), 0.6, 0.006), (r.uniform(2200, 3200), 0.3, 0.004)], r)
        _put(y, c * r.uniform(0.7, 1.0), t0)
    return y


def chomp(r):
    """a big bite into a burger: crunchy burst + wet click"""
    t = tt(0.3)
    y = bp(r.standard_normal(len(t)), 700, 6000, 1) * np.exp(-t / 0.03) * (0.6 + 0.4 * (np.random.default_rng(1).random(len(t)) > 0.7))
    _put(y, modal(0.05, [(380, 0.8, 0.01)], r), 0.02)
    return fades(y, 0, 0.05)


def sip(r, dur=0.7):
    """slurping hot tea, then a soft 'ahh'-like gulp"""
    n = ns(dur); t = np.arange(n) / SR
    fc = 800 + 1600 * (0.5 + 0.5 * np.sin(TAU * 3.0 * t))
    y = shape(r.standard_normal(n), lambda T, F: np.exp(-0.5 * (np.log2(np.maximum(F[:, None], 20) / np.interp(T, t, fc)[None, :]) / 0.5) ** 2), 512, 128)
    y *= _env(t, 0.05, dur * 0.75, 0.1) * 0.8
    _put(y, modal(0.15, [(210, 1.0, 0.04), (420, 0.3, 0.02)], r) * 0.8, dur * 0.8)
    return y


def tap(r, n=2):
    """a fingertip tapping plastic (the dash cam)"""
    y = np.zeros(ns(0.4))
    for k in range(n):
        _put(y, modal(0.06, [(950, 1.0, 0.01), (1650, 0.5, 0.007), (2700, 0.25, 0.004)], r) + hp(r.standard_normal(ns(0.06)), 2000) * np.exp(-tt(0.06) / 0.001) * 0.4, k * 0.16)
    return y


def knock(r, n=3):
    """knuckles on a car window"""
    y = np.zeros(ns(0.6))
    for k in range(n):
        _put(y, modal(0.08, [(1900, 1.0, 0.012), (3400, 0.5, 0.008), (700, 0.6, 0.02)], r), k * 0.17)
    return y


# ================================================================ dash cam and rain
def camera_beep(r, n=2, f=2600.0):
    y = np.zeros(ns(0.5))
    for k in range(n):
        tl = tt(0.07); _put(y, np.sin(TAU * f * tl) * _env(tl, 0.004, 0.07, 0.01), k * 0.12)
    return y


def rewind(r, dur=0.6):
    """tape rewind: a whirring tone sweeping up with chatter"""
    n = ns(dur); t = np.arange(n) / SR
    f = 250 * (12 ** (t / dur))
    ph = phase(f)
    y = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sign(np.sin(3 * ph)) * 0.3) * 0.5
    y += bp(r.standard_normal(n), 2000, 8000, 1) * 0.2 * (0.5 + 0.5 * (np.sin(TAU * 40 * t) > 0))
    return fades(lp(y, 6000) * _env(t, 0.03, dur, 0.06), 0.003, 0.03)


def wiper(r, dur=0.7):
    """one wiper stroke: motor whir, a rubber squeak across the glass, the soft thunk at the end"""
    y = np.zeros(ns(dur + 0.2))
    t = tt(dur)
    _put(y, lp(colored(len(t), r, 1.0), 400, 2) * np.sin(np.pi * t / dur) * 0.5, 0)
    sq = G.creak(dur * 0.85, r, 420, 260, modes=[(1350, 18, 1.0), (2700, 20, 0.5), (4100, 22, 0.25)], shape_pts=[(0, 0), (0.2, 1), (0.8, 0.8), (1, 0)], rough=0.08, noise=0.02)
    _put(y, sq / (np.abs(sq).max() + 1e-9) * 0.6, 0.05)
    tl = tt(0.12); _put(y, np.exp(-tl / 0.03) * np.sin(phase(140 + 0 * tl)) * 0.7, dur)
    return y


def rain_bed(dur, r, close=1.0, on_glass=0.0):
    """rain: a hiss of drops, patter on the road and roof, drips; on_glass adds close drops hitting the windshield"""
    n = ns(dur)
    out = np.zeros((2, n))
    for ch in range(2):
        hiss = bp(colored(n, r, 0.5), 900, 9000, 1) * (0.8 + 0.2 * smooth_noise(n, r, 0.3))
        patter = G.bubbles(dur, r, 260 * close + 40, 1800, 7000, (0.002, 0.008), rise=(2, 8)) * 0.6
        rum = lp(colored(n, r, 1.8), 300, 2) * 0.4
        out[ch] = hiss * 0.7 + patter + rum
    if on_glass:
        drops = G.bubbles(dur, r, 25 * on_glass, 600, 2500, (0.004, 0.015), rise=(1, 4)) * 0.9
        out += widen(drops, r, 5, 1.0) * on_glass
    return out


def night_bed(dur, r):
    """night air: crickets, a soft breeze, very distant traffic"""
    n = ns(dur)
    out = G.breeze(dur, r, 0.35, 0.12, 600)
    cr = G.crickets(dur, r, 4)
    out += pan(cr * 0.18, 0.4) + pan(G.crickets(dur, r, 3) * 0.12, -0.5)
    out += st(lp(colored(n, r, 1.8), 300, 2)) * 0.25
    return out


def day_bed(dur, r):
    """daytime outdoors (suburb, roadside): breeze, birds, distant traffic"""
    out = road_bed(dur, r, 0.8)
    out += pan(G.bird_chirps(dur, r, 0.45, "sparrow") * 0.08, 0.5) + pan(G.bird_chirps(dur, r, 0.3, "blackbird") * 0.06, -0.6)
    return out


# ================================================================ comedy accents and transitions
def whoosh(r, dur=0.6):
    return widen(G.whoosh(dur, r, peak=dur * 0.4, f_lo=300, f_hi=2400, width=0.8, tail=dur * 0.35, air=0.2), r, 11, 0.8)


def whoosh_soft(r):
    return widen(G.whoosh(0.7, r, peak=0.3, f_lo=250, f_hi=1400, width=0.9, tail=0.3, air=0.05), r, 11, 0.8) * 0.6


def record_scratch(r, dur=0.42):
    """record scratch before a 'But' turn: a pitch-swept noisy tone that zips down then back up"""
    n = ns(dur); t = np.arange(n) / SR
    f = np.interp(t, [0, 0.12, 0.2, dur], [1800, 280, 260, 1500])
    ph = phase(f)
    y = np.sign(np.sin(ph)) * 0.25 + np.sin(ph) * 0.5 + np.sin(2 * ph) * 0.2
    y += shape(r.standard_normal(n), lambda T, F: np.exp(-0.5 * (np.log2(np.maximum(F[:, None], 20) / (np.interp(T, t, f)[None, :] * 2)) / 0.6) ** 2), 512, 128) * 0.8
    return fades(lp(y, 7000) * _env(t, 0.01, dur, 0.05), 0.002, 0.02)


def pop(r):
    t = tt(0.12)
    y = np.sin(phase(500 + 1400 * (t / 0.12) ** 0.5)) * np.exp(-t / 0.03) + hp(r.standard_normal(len(t)), 2000) * np.exp(-t / 0.002) * 0.5
    return fades(y, 0, 0.02)


def boing(r, dur=0.7, f0=180.0):
    """cartoon spring"""
    n = ns(dur); t = np.arange(n) / SR
    f = f0 * (1 + 0.45 * np.sin(TAU * 14 * t) * np.exp(-t / 0.25)) * (1 + 0.6 * np.exp(-t / 0.05))
    y = np.sin(phase(f)) + 0.3 * np.sin(2 * phase(f))
    return fades(y * np.exp(-t / 0.25), 0.002, 0.05)


def ding(r, f0=1568.0):
    """a bright bell for a punchline"""
    return modal(1.8, [(f0, 1.0, 0.7), (f0 * 2.0, 0.35, 0.4), (f0 * 2.76, 0.3, 0.25), (f0 * 5.4, 0.12, 0.08)], r)


def thud(r):
    t = tt(0.4)
    return fades(np.exp(-t / 0.08) * np.sin(phase(75 * (1 + 0.6 * np.exp(-t / 0.01)))) + lp(r.standard_normal(len(t)), 600) * np.exp(-t / 0.02) * 0.6, 0, 0.05)


SOUNDS = {
    # cars
    "brake_squeal": (brake_squeal, -4, "event"), "tyre_screech": (tyre_screech, -4, "event"), "crunch": (crunch, 0, "event"),
    "glass_tinkle": (glass_tinkle, -8, "event"), "horn": (horn, -5, "event"), "horn_short": (horn_short, -6, "event"),
    "engine_pass": (engine_pass, -7, "event"), "engine_rev": (engine_rev, -7, "event"), "car_door": (car_door, -6, "event"),
    "seatbelt": (seatbelt, -10, "event"),
    # money / office / home
    "cash_register": (cash_register, -3, "event"), "coins": (coins, -8, "event"), "paper_flutter": (paper_flutter, -9, "event"),
    "cash_burst": (cash_burst, -2, "event"), "paper_burst": (paper_burst, -4, "event"), "phone_ring": (phone_ring, -6, "event"),
    "stamp": (stamp, -6, "event"), "keyboard": (keyboard, -12, "event"),
    # bodies
    "oof": (oof, -6, "event"), "groan": (groan, -7, "event"), "neck_crack": (neck_crack, -6, "event"), "chomp": (chomp, -8, "event"),
    "sip": (sip, -8, "event"), "tap": (tap, -6, "event"), "knock": (knock, -6, "event"),
    # dash cam
    "camera_beep": (camera_beep, -8, "event"), "rewind": (rewind, -6, "event"), "wiper": (wiper, -7, "event"),
    # accents and transitions
    "whoosh": (whoosh, -6, "event"), "whoosh_soft": (whoosh_soft, -14, "event"), "record_scratch": (record_scratch, -2, "event"),
    "pop": (pop, -9, "event"), "boing": (boing, -6, "event"), "ding": (ding, -4, "event"), "thud": (thud, -6, "event"),
    # beds (integrated loudness relative to the voice; the mix fades them at shot edges)
    "day": (day_bed, -21, "bed"), "road": (road_bed, -19, "bed"), "night": (night_bed, -23, "bed"), "rain": (rain_bed, -17, "bed"),
    "rain_car": (lambda dur, r: rain_bed(dur, r, 0.7, 1.0) + car_interior_bed(dur, r) * 0.5, -16, "bed"),
    "car": (car_interior_bed, -19, "bed"), "room": (room_bed, -27, "bed"), "tv": (tv_bed, -24, "bed"), "none": (None, 0, "bed"),
}


def render(name, opts=None, seed=0, dur=None):
    """render one cue -> stereo (2, n)"""
    fn, _, kind = SOUNDS[name]
    if fn is None: return np.zeros((2, ns(dur or 0.1)))
    r = rng(seed)
    o = dict(opts or {})
    x = fn(dur, r) if kind == "bed" else fn(r, **o)
    return st(x)
