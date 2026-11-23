#!/usr/bin/env python3
"""Learn from a reference Short cheaply: transcript, word times, cuts, two small strips, a draft beat sheet.

    analyze_ref.py <video> <out_dir> [--cut 0.35]

Writes into <out_dir>:
  vo.wav, vo.words.json   audio and word timings (kit/words.py, Parakeet, runs locally)
  cuts.txt                setup changes in seconds (hard cuts, dissolves, whips)
  setups.jpg              start, middle, end frame of every camera setup (look at this one first)
  overview.jpg            one frame every 3 s, 120 px tiles
  hook.jpg                first 5 s at 2 fps     end.jpg   last 9 s at 1 fps
  beats_draft.md          sentences with start time, % of runtime, words/s, shot stats.
                          Label the beats by hand using story/formula.md, then save it to story/examples/.
Runs itself under the kit's Python (needs numpy). Needs ffmpeg on PATH and the kit's voice models (bash kit/setup.sh --voice).
Only text is printed, so reading the output costs few tokens. Open the .jpg files only if needed.
"""
import json, os, re, statistics, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.environ.get('KIT') or next((d for d in (os.path.join(HERE, '..', 'kit'), os.path.expanduser('~/.claude/kit'))
                                     if os.path.isdir(os.path.join(d, '.venv'))), os.path.join(HERE, '..', 'kit'))


def kit_python():
    for p in ('.venv/Scripts/python.exe', '.venv/bin/python'):
        f = os.path.join(KIT, p)
        if os.path.exists(f):
            return f
    sys.exit(f'kit venv not found in {KIT}; run: bash "{os.path.join(HERE, "..", "setup.sh")}"  (or set KIT=...)')


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)


def duration(v):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', v],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def cuts(v, thr):
    """Setup changes, including dissolves and whips: colour-histogram distance between frames 0.3 s apart.
    0.35 found 19 setups on the dash-cam reference (20 counted by hand)."""
    import numpy as np
    W, H, F, G = 36, 64, 10, 3
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', f'fps={F},scale={W}:{H}', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3) // 32
    idx = (x[..., 0].astype(int) * 64 + x[..., 1] * 8 + x[..., 2]).reshape(len(x), -1)
    h = np.stack([np.bincount(r, minlength=512) for r in idx]) / idx.shape[1]
    d = np.zeros(len(h)); d[G:] = 0.5 * np.abs(h[G:] - h[:-G]).sum(1)
    peaks = []
    for i in range(len(d)):
        if d[i] > thr and d[i] == d[max(0, i - 5):i + 6].max() and (not peaks or i - peaks[-1] > 8):
            peaks.append(i)
    return [round((p - G / 2) / F, 1) for p in peaks]


def kinds(v, cl):
    """Hard cut vs. gradual (dissolve, whip, in-world wipe), from frame-to-frame change at full frame rate.
    A hard cut puts the whole change into 1 frame; gradual ones spread it over 4+ frames.
    On the dash-cam reference this gave 7 cuts and 11 gradual, matching the hand count."""
    import numpy as np
    W, H, F = 36, 64, 30
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', f'fps={F},scale={W}:{H}', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3) // 32
    idx = (x[..., 0].astype(int) * 64 + x[..., 1] * 8 + x[..., 2]).reshape(len(x), -1)
    h = np.stack([np.bincount(r, minlength=512) for r in idx]) / idx.shape[1]
    d = np.zeros(len(h)); d[1:] = 0.5 * np.abs(h[1:] - h[:-1]).sum(1)
    out = []
    for c in cl:
        i = int(c * F); w = d[max(0, i - 15):i + 16]; pk = w.max()
        n = int((w > 0.25 * pk).sum())
        out.append(('cut', 1) if n <= 2 else ('gradual', n))
    return out


def loudness(v):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', v, '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', r); l = re.findall(r'LRA:\s+([\d.]+) LU', r)
    return (float(i[-1]) if i else None, float(l[-1]) if l else None)


def setup_sheet(v, bounds, path):
    """Start, (middle,) end frame of every setup, 150 px, 10 per row, in time order. A red bar marks each start."""
    import tempfile, shutil
    tmp = tempfile.mkdtemp(); n = 0
    for a_, b in zip(bounds[:-1], bounds[1:]):
        ts = [a_ + 0.2] + ([(a_ + b) / 2] if b - a_ > 2.2 else []) + [b - 0.2]
        for j, t in enumerate(ts):
            vf = 'scale=150:-1' + (',drawbox=x=0:y=0:w=150:h=5:color=red@1:t=fill' if j == 0 else '')
            ff('-ss', f'{t:.2f}', '-i', v, '-frames:v', '1', '-vf', vf, '-q:v', '5', os.path.join(tmp, f'{n:03d}.jpg')); n += 1
    rows = (n + 9) // 10
    ff('-framerate', '1', '-i', os.path.join(tmp, '%03d.jpg'), '-vf', f'tile=10x{rows}', '-frames:v', '1', '-q:v', '5', path)
    shutil.rmtree(tmp, ignore_errors=True)
    return n


def sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r'[.?!]["\']?$', w['w']):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def main():
    try:
        import numpy  # noqa: F401
    except ImportError:
        os.execv(kit_python(), [kit_python(), os.path.abspath(__file__), *sys.argv[1:]])
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    v, od = a[0], a[1]
    thr = float(a[a.index('--cut') + 1]) if '--cut' in a else 0.35
    os.makedirs(od, exist_ok=True)
    D = duration(v)

    wav = os.path.join(od, 'vo.wav')
    ff('-i', v, '-vn', '-ac', '1', '-ar', '16000', wav)
    subprocess.run([kit_python(), os.path.join(KIT, 'words.py'), 'vo.wav'], cwd=od, check=True,
                   stdout=subprocess.DEVNULL)
    words = json.load(open(os.path.join(od, 'vo.words.json'), encoding='utf-8'))

    cl = cuts(v, thr)
    open(os.path.join(od, 'cuts.txt'), 'w').write('\n'.join(map(str, cl)) + '\n')

    ff('-i', v, '-vf', 'fps=1/3,scale=120:-1,tile=7x3', '-frames:v', '1', '-q:v', '5', os.path.join(od, 'overview.jpg'))
    ff('-t', '5', '-i', v, '-vf', 'fps=2,scale=120:-1,tile=10x1', '-frames:v', '1', '-q:v', '5', os.path.join(od, 'hook.jpg'))
    ff('-ss', str(max(0, D - 9)), '-i', v, '-vf', 'fps=1,scale=120:-1,tile=9x1', '-frames:v', '1', '-q:v', '5', os.path.join(od, 'end.jpg'))

    bounds = [0] + cl + [D]
    shots = [b - a_ for a_, b in zip(bounds[:-1], bounds[1:])]
    nf = setup_sheet(v, bounds, os.path.join(od, 'setups.jpg'))
    kd = kinds(v, cl); lu, lra = loudness(v)
    sents = sentences(words)
    nw = len(words)

    def word_at(t):
        nxt = [w for w in words if w['s'] >= t - 0.15]  # first word spoken in the new setup
        return nxt[0]['w'] if nxt else ''
    L = [f'# Beat sheet draft: {os.path.basename(v)}', '',
         f'- Runtime {D:.1f} s, {nw} words, {nw / D:.2f} words/s, {len(sents)} sentences',
         f'- {len(shots)} camera setups: mean {statistics.mean(shots):.1f} s, median {statistics.median(shots):.1f} s, '
         f'range {min(shots):.1f} to {max(shots):.1f} s ',
         f'- Transitions: {sum(k == "cut" for k, _ in kd)} hard cuts, {sum(k != "cut" for k, _ in kd)} gradual',
         f'- Loudness {lu} LUFS, range {lra} LU', '',
         f'`setups.jpg`: {nf} frames, start / middle / end of each setup in order (red bar = setup start).', '',
         '| setup | start | dur | in | first word | picture (fill in) |', '|---|---|---|---|---|---|']
    for i, (a_, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        tr = '—' if i == 0 else (kd[i - 1][0] if kd[i - 1][0] == 'cut' else f'gradual {kd[i - 1][1]}f')
        L.append(f'| {i + 1} | {a_:.1f} | {b - a_:.1f} | {tr} | {word_at(a_)} |  |')
    L += ['', '| # | start (✂ = new setup) | % | beat (fill in from formula.md) | sentence |', '|---|---|---|---|---|']
    for i, s in enumerate(sents, 1):
        t = s[0]['s']
        cut = '✂ ' if any(abs(c - t) < 0.4 for c in cl) else ''
        L.append(f'| {i} | {cut}{t:.1f} | {100 * t / D:.0f}% |  | {" ".join(w["w"] for w in s)} |')
    L += ['', '## Notes (fill in)', '- Hook: first frame, first words, time of first payoff:',
          '- Title promise vs. first sentence (the curiosity gap):', '- Where the "But" turns fall:',
          '- Dialogue lines:', '- Colour acts / mood shifts:', '- Reveal: how the answer is shown:',
          '- Last line / loop back to the first frame:']
    open(os.path.join(od, 'beats_draft.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L[:5]))
    print(f'{len(sents)} sentences -> {os.path.join(od, "beats_draft.md")}')


if __name__ == '__main__':
    main()
