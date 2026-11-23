#!/usr/bin/env python3
"""Word timings for a voiceover, on your own computer (NVIDIA Parakeet via sherpa-onnx, model from setup.sh).

    <kit python> words.py <voiceover.wav|mp3|m4a> [script.json | script.txt]

Writes <voiceover>.words.json next to the audio: a list of {"w": word, "s": start, "e": end} in seconds.
With a script, the words come out spelled exactly as in the script (split on whitespace) and the timings come from
the audio; words the recogniser missed get times between their neighbours.
Files over ~65 s are cut at quiet spots into pieces of up to 55 s, so a full-length voiceover works too.
"""
import difflib
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.realpath(__file__))
RATE = 16000
PIECE, SEARCH = 55.0, 10.0         # piece length, and the window (s) searched for a quiet cut; Shorts stay in one piece
MAX_WORD = 1.2                     # a word never lasts longer than this


def read_audio(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(RATE), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def model():
    import sherpa_onnx
    found = sorted(glob.glob(os.path.join(HERE, 'models', 'sherpa-onnx-nemo-parakeet*')))
    if not found:
        sys.exit(f'word-timing model not found in {HERE}/models: run  bash "{os.path.dirname(HERE)}/setup.sh"')
    m = found[0]
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=os.path.join(m, 'encoder.int8.onnx'), decoder=os.path.join(m, 'decoder.int8.onnx'),
        joiner=os.path.join(m, 'joiner.int8.onnx'), tokens=os.path.join(m, 'tokens.txt'), model_type='nemo_transducer')


def cut_points(audio):
    """piece boundaries in seconds, each placed at the quietest 50 ms before the target length"""
    total = len(audio) / RATE
    cuts, t = [0.0], 0.0
    win = int(0.05 * RATE)
    while total - t > PIECE + SEARCH:
        a, b = int((t + PIECE - SEARCH) * RATE), int((t + PIECE) * RATE)
        energy = np.convolve(audio[a:b] ** 2, np.ones(win), 'valid')
        t = (a + int(np.argmin(energy)) + win // 2) / RATE
        cuts.append(t)
    return cuts + [total]


def hear(audio):
    """[(word, start)] as recognised, across all pieces"""
    rec, out = model(), []
    cuts = cut_points(audio)
    for t0, t1 in zip(cuts, cuts[1:]):
        stream = rec.create_stream()
        stream.accept_waveform(RATE, audio[int(t0 * RATE):int(t1 * RATE)])
        rec.decode_stream(stream)
        res = stream.result
        first = True
        for tok, ts in zip(res.tokens, res.timestamps):
            text = tok.lstrip('▁ ')
            if tok.startswith(('▁', ' ')) or first:        # a new word (each piece starts with one)
                if text:
                    out.append([text, float(ts) + t0])
                    first = False
            elif out:
                out[-1][0] += text
    return [(w, s) for w, s in out]


def key(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def align(heard, script_words):
    """script spelling, heard timing; unmatched script words are spread evenly between matched neighbours"""
    times = [None] * len(script_words)
    sm = difflib.SequenceMatcher(None, [key(w) for w in script_words], [key(w) for w, _ in heard], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            times[a + k] = heard[b + k][1]
    known = [i for i, t in enumerate(times) if t is not None]
    if not known:
        sys.exit('none of the script words were heard: is this the right audio?')
    for i in range(len(times)):
        if times[i] is None:
            lo = max((j for j in known if j < i), default=None)
            hi = min((j for j in known if j > i), default=None)
            if lo is None:
                times[i] = max(0.0, times[hi] - 0.3 * (hi - i))
            elif hi is None:
                times[i] = times[lo] + 0.3 * (i - lo)
            else:
                times[i] = times[lo] + (times[hi] - times[lo]) * (i - lo) / (hi - lo)
    return list(zip(script_words, times))


def load_script(path):
    raw = open(path, encoding='utf-8').read()
    return ' '.join(json.loads(raw)) if path.endswith('.json') else raw


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    audio_path = sys.argv[1]
    audio = read_audio(audio_path)
    words = hear(audio)
    if len(sys.argv) > 2:
        words = align(words, load_script(sys.argv[2]).split())
    total = len(audio) / RATE
    out = [{'w': w, 's': round(s, 3), 'e': round(min(words[i + 1][1] if i + 1 < len(words) else total, s + MAX_WORD), 3)}
           for i, (w, s) in enumerate(words)]
    dst = os.path.splitext(audio_path)[0] + '.words.json'
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=0)
    print(f'{len(out)} words, {total:.1f} s, {len(out) / max(total, 1e-6):.2f} words/s -> {dst}')


if __name__ == '__main__':
    main()
