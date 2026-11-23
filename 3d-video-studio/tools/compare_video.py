#!/usr/bin/env python3
"""Judge a finished (or preview) video against a reference profile made by ref_profile.py.

    compare_video.py <ours.mp4> <profile_dir> <out_dir> [--words words.json] [--acts 0,21.04,48.93,71.2]
                     [--range <t0> <t1>]

Measures our video the same way as the reference (vidmetrics.py), prints a PASS / WARN / FAIL table and writes into
<out_dir>:
  compare.md      the table plus details: blended frames, dissolve lengths, dead-still setups, acts, our setups
  profile.json    our own profile (same format as the reference's)
  pairs_N.jpg     reference middle frame of each setup on top, ours below at the same share of runtime, 7 per sheet
  beats.jpg       start / middle / end of each of our setups
  transitions/    every frame through each of our transitions (frame numbers on tiles, * = mixed frame)
--acts   our colour-act boundaries in seconds (default thirds). The reference's acts come from its profile.
--range  compare only t0..t1 seconds of the reference with the same stretch of ours (e.g. the hook preview:
         --range 0 5). If our file is about t1 - t0 long it is taken to be that stretch already (a preview render).
         Whole-video checks (duration, setup count and length, loudness, words/s, act-to-act colour) are skipped;
         blended cuts, dissolve lengths, dead-still camera, motion, detail, colour and captions are judged.
Exit code 1 if any FAIL. Thresholds are in T below. Takes about 1 min 20 s for a 70 s video (10 s for a 5 s preview).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import vidmetrics as vm  # noqa: E402

# Tune here. Ratios are ours / reference.
T = dict(
    blend_any_fail=True,          # any blended frame at a cut (broken hard cut) = FAIL
    dissolve_median_frames=2,     # median dissolve length further than this from the reference median = FAIL (ours 12 vs ref 9 must fail)
    dissolve_over_ref_max=4,      # any dissolve longer than the reference ceiling + this = WARN
    ref_ignore_longest=1,         # the reference's longest dissolve (the reveal) does not set the ceiling
    still_share=0.8,              # a setup is dead-still if this share of its frames has no camera move
    device_view_s=1.5,            # one dead-still setup up to this long is allowed (the device / dashcam view)
    dead_still_fail_s=1.5,        # more dead-still seconds than this = FAIL
    motion_fail=0.6, motion_warn=0.8,     # median frame-to-frame change
    detail_fail=0.5, detail_warn=0.7,     # edge density and sharpness per act
    col_fail=0.40, col_warn=0.25,         # colourfulness per act, +- share
    col_ratio_warn=0.2,           # act-3 / act-1 colourfulness ratio off by more than this = WARN
    sat_over_warn=0.08,           # saturation more than this above the reference in an act = WARN (purple wash)
    setups_warn=0.25,             # setup count and median setup length, +- share
    duration_warn=0.10,           # +- share
    wps_min=3.5, wps_max=4.1,     # words per second outside = FAIL
    lufs_fail=1.0,                # integrated loudness further than this (LU) = FAIL
    lra_over_warn=1.5,            # loudness range more than this above the reference = WARN
    cap_h_warn=0.20,              # caption text height +- share = WARN
    cap_y_warn=0.04,              # caption centre further than this share of the height = WARN
    pair_tile=240, pairs_per_sheet=7,
)


def arg(a, k, n=1):
    if k not in a:
        return None
    i = a.index(k)
    return a[i + 1:i + 1 + n] if n > 1 else a[i + 1]


def ratio_status(r, fail, warn):
    return 'FAIL' if r < fail else 'WARN' if r < warn else 'PASS'


def judge(ref, ours, refw, oursw, refdis, ranged):
    """ref / ours: summarize() dicts. refdis: whole-reference dissolve lengths (style, used also for --range)."""
    rows = []

    def add(name, r, o, st, note=''):
        rows.append((name, r, o, st, note))

    # blended frames at cuts
    b = ours['blends']
    add('blended frame at cut', str(len(ref['blends'])), str(len(b)), 'FAIL' if b and T['blend_any_fail'] else 'PASS',
        ', '.join(f"f{x['f']} {x['t']:.2f}s ({x['alpha'][0]:.2f})" for x in b))
    # dissolves (judged against the whole reference's style)
    od = [x['frames'] for x in ours['dissolves']]
    if refdis and od:
        rm, om = float(np.median(refdis)), float(np.median(od))
        st = 'FAIL' if abs(om - rm) > T['dissolve_median_frames'] else 'PASS'
        add('dissolve median frames', f'{rm:g}', f'{om:g}', st, 'ours ' + ' '.join(map(str, od)))
        srt = sorted(refdis)
        ceil = srt[-1 - T['ref_ignore_longest']] if len(srt) > T['ref_ignore_longest'] + 1 else srt[-1]
        long_ = [x for x in ours['dissolves'] if x['frames'] > ceil + T['dissolve_over_ref_max']]
        add('dissolve too long', f'<= {ceil}+{T["dissolve_over_ref_max"]}', str(max(od)), 'WARN' if long_ else 'PASS',
            ', '.join(f"{x['t0']:.2f}s {x['frames']}f" for x in long_))
    elif od:
        add('dissolve median frames', '-', f'{np.median(od):g}', 'PASS', 'no reference dissolves to compare')
    # camera
    add('dead-still camera s', f"{ref['dead_still_s']:g}", f"{ours['dead_still_s']:g}",
        'FAIL' if ours['dead_still_s'] > T['dead_still_fail_s'] else 'PASS', ' '.join(ours['dead_still']))
    if ref['diff_median'] and ours['diff_median'] is not None:
        r = ours['diff_median'] / ref['diff_median']
        add('median frame change', f"{ref['diff_median']:g}", f"{ours['diff_median']:g}",
            ratio_status(r, T['motion_fail'], T['motion_warn']), f'x{r:.2f}')
    # per act
    for ra, oa in zip(ref['acts'], ours['acts']):
        lab = 'range' if ranged else f"act {oa['act']}"
        for k, name in (('edge', 'edge density'), ('sharp', 'sharpness')):
            if ra[k] and oa[k] is not None:
                r = oa[k] / ra[k]
                add(f'{name} {lab}', f'{ra[k]:g}', f'{oa[k]:g}', ratio_status(r, T['detail_fail'], T['detail_warn']), f'x{r:.2f}')
        r = oa['col'] / ra['col'] - 1
        add(f'colourfulness {lab}', f"{ra['col']:g}", f"{oa['col']:g}",
            'FAIL' if abs(r) > T['col_fail'] else 'WARN' if abs(r) > T['col_warn'] else 'PASS', f'{r * 100:+.0f}%')
        dsat = oa['sat'] - ra['sat']
        add(f'saturation {lab}', f"{ra['sat']:g}", f"{oa['sat']:g}", 'WARN' if dsat > T['sat_over_warn'] else 'PASS',
            f'{dsat:+.3f}' + (' (colour wash over everything)' if dsat > T['sat_over_warn'] else ''))
    if not ranged and len(ref['acts']) >= 3 and len(ours['acts']) >= 3:
        rr = ref['acts'][-1]['col'] / ref['acts'][0]['col']; orr = ours['acts'][-1]['col'] / ours['acts'][0]['col']
        add('colour last/first act', f'{rr:.2f}', f'{orr:.2f}', 'WARN' if abs(orr - rr) > T['col_ratio_warn'] else 'PASS')
    # captions
    rc, oc = ref['caption'], ours['caption']
    if rc['h'] and oc['h']:
        r = oc['h'] / rc['h'] - 1
        add('caption text height px', f"{rc['h']:g}", f"{oc['h']:g}", 'WARN' if abs(r) > T['cap_h_warn'] else 'PASS', f'{r * 100:+.0f}%')
        dy = oc['y'] - rc['y']
        add('caption centre (share of H)', f"{rc['y']:.3f}", f"{oc['y']:.3f}", 'WARN' if abs(dy) > T['cap_y_warn'] else 'PASS')
        add('caption outline px (approx.)', f"{rc['outline']}", f"{oc['outline']}", 'INFO')
    elif rc['h']:
        add('caption found', 'yes', 'no', 'WARN', 'no white outlined caption found at 60-80% of the height')
    if not ranged:
        r = ours['duration'] / ref['duration'] - 1
        add('duration s', f"{ref['duration']:.1f}", f"{ours['duration']:.1f}", 'WARN' if abs(r) > T['duration_warn'] else 'PASS', f'{r * 100:+.0f}%')
        r = ours['n_setups'] / ref['n_setups'] - 1
        add('camera setups', str(ref['n_setups']), str(ours['n_setups']), 'WARN' if abs(r) > T['setups_warn'] else 'PASS', f'{r * 100:+.0f}%')
        r = ours['setup_median'] / ref['setup_median'] - 1
        add('median setup length s', f"{ref['setup_median']:g}", f"{ours['setup_median']:g}",
            'WARN' if abs(r) > T['setups_warn'] else 'PASS', f'{r * 100:+.0f}%')
        if oursw:
            w = oursw['wps']
            add('words per second', f"{refw['wps']:g}" if refw else '-', f'{w:g}',
                'FAIL' if not T['wps_min'] <= w <= T['wps_max'] else 'PASS', f"target {T['wps_min']}-{T['wps_max']}")
        rl, ol = ref.get('loudness') or {}, ours.get('loudness') or {}
        if rl.get('I') is not None and ol.get('I') is not None:
            add('loudness LUFS', f"{rl['I']:g}", f"{ol['I']:g}", 'FAIL' if abs(ol['I'] - rl['I']) > T['lufs_fail'] else 'PASS')
            add('loudness range LU', f"{rl['LRA']:g}", f"{ol['LRA']:g}", 'WARN' if ol['LRA'] - rl['LRA'] > T['lra_over_warn'] else 'PASS')
        elif rl.get('I') is not None:
            add('loudness LUFS', f"{rl['I']:g}", 'no audio', 'FAIL')
    return rows


def table(rows):
    w = max(len(r[0]) for r in rows)
    L = [f"{'CHECK':{w}}  {'REF':>12}  {'OURS':>10}  RESULT  NOTE"]
    for n, r, o, st, note in rows:
        L.append(f'{n:{w}}  {r:>12}  {o:>10}  {st:6}  {note}')
    return '\n'.join(L)


def pairs(prof, ref_s, ours_v, ours_dur, ref_dur, out_dir, t0=None, t1=None, clip=False):
    """Reference middle frame of each setup on top, ours below at the same share of runtime (or the same time with
    --range). Returns the written paths."""
    from PIL import Image
    tw = T['pair_tile']
    src = prof.get('source')
    have_src = bool(src and os.path.exists(src))
    items = []
    for st in prof['setups']:
        a, b = st['a'] / vm.FPS, st['b'] / vm.FPS
        if t0 is not None and (b <= t0 or a >= t1):
            continue
        if t0 is not None:
            a, b = max(a, t0), min(b, t1)
        mid = (a + b) / 2
        if t0 is None:
            to = mid / ref_dur * ours_dur
        else:
            to = mid - t0 if clip else mid
        if have_src and t0 is not None:
            rim = vm.grab(src, mid, tw)
        else:
            p = os.path.join(prof['_dir'], st.get('frame') or '')
            rim = Image.open(p).convert('RGB') if st.get('frame') and os.path.exists(p) else vm.grab(src, mid, tw) if have_src else Image.new('RGB', (tw, tw * 16 // 9))
        items.append((f"REF #{st['n']} {mid:.2f}s", rim, f'OURS {to:.2f}s', vm.grab(ours_v, min(to, ours_dur - 0.05), tw)))
    paths = []
    k = T['pairs_per_sheet']
    for i in range(0, len(items), k):
        ch = items[i:i + k]
        p = os.path.join(out_dir, f'pairs_{i // k + 1}.jpg')
        vm.tile([x[1] for x in ch] + [x[3] for x in ch], [x[0] for x in ch] + [x[2] for x in ch], len(ch), p, tw, fs=13)
        paths.append(p)
    return paths


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    ov, pdir, od = a[0], a[1], a[2]
    words = arg(a, '--words')
    acts = [float(x) for x in arg(a, '--acts').split(',')] if '--acts' in a else None
    rng = [float(x) for x in arg(a, '--range', 2)] if '--range' in a else None
    os.makedirs(od, exist_ok=True)
    prof, rraw = vm.load_profile(pdir)
    ref_dur = rraw['n'] / vm.FPS
    kw = dict(still_share=T['still_share'], device_view_s=T['device_view_s'])

    raw, oprof = vm.build_profile(ov, od, acts=acts, words=words if not rng else None, frames=False, sheets=True)
    ours_dur = raw['n'] / vm.FPS
    clip = False
    if rng:
        t0, t1 = rng
        clip = ours_dur <= (t1 - t0) + 0.5
        ref_s = vm.summarize(rraw, t0=t0, t1=t1, **kw)
        ours_s = vm.summarize(raw, t0=0, t1=ours_dur, **kw) if clip else vm.summarize(raw, t0=t0, t1=t1, **kw)
    else:
        ref_s = vm.summarize(rraw, prof['acts'], **kw)
        ours_s = vm.summarize(raw, oprof['acts'], **kw)
    refdis = [x['frames'] for x in prof['summary']['dissolves']]
    rows = judge(ref_s, ours_s, prof.get('words'), oprof.get('words'), refdis, bool(rng))
    tbl = table(rows)
    pp = pairs(prof, ref_s, ov, ours_dur, ref_dur, od, *(rng or (None, None)), clip=clip)

    nf = sum(r[3] == 'FAIL' for r in rows); nw = sum(r[3] == 'WARN' for r in rows)
    head = (f"{os.path.basename(ov)} vs {prof['video']}" + (f"  range {rng[0]:g}-{rng[1]:g} s" + (' (our file is the clip)' if clip else '') if rng else '')
            + f"\n{nf} FAIL, {nw} WARN  ({oprof['seconds']} s to measure ours)")
    print(head); print(tbl)
    md = [f'# Compare: {os.path.basename(ov)} vs reference {prof["video"]}', '',
          head.splitlines()[-1] + (f", range {rng[0]:g}-{rng[1]:g} s" if rng else ''), '', '```', tbl, '```', '',
          '## Ours', '```', vm.text_summary(ours_s, oprof.get('words') if not rng else None, ours_s['setups']), '```', '',
          '## Reference' + (' (same stretch)' if rng else ''), '```', vm.text_summary(ref_s, prof.get('words') if not rng else None), '```', '',
          '## Files', '- ' + '\n- '.join(os.path.basename(p) for p in pp) + '  (reference on top, ours below)',
          '- beats.jpg, transitions/*.jpg (ours, every frame through each transition)', '']
    open(os.path.join(od, 'compare.md'), 'w', encoding='utf-8').write('\n'.join(md))
    print(f"-> {os.path.join(od, 'compare.md')}, {len(pp)} pair sheets")
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
