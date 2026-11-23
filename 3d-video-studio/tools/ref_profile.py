#!/usr/bin/env python3
"""Measure a reference Short once, so every future video can be judged against it (compare_video.py).

    ref_profile.py <video> <out_dir> [--words words.json] [--acts 0,18.5,43.6,62.2]

Writes into <out_dir>:
  profile.json   duration; camera setups (start, end, how each starts: cut / dissolve with frame count and alpha
                 curve / gradual in-world transition such as a fly-through, burst or wipe); setup length mean and
                 median; dissolve frames min / median / max; blended frames at cuts; per setup pan px/s, zoom %/s,
                 roll deg/s, still share; seconds of dead-still camera; median frame-to-frame change; per act
                 colourfulness, saturation, luma, edge density, sharpness (full-res Laplacian variance, caption band
                 left out); caption text height, centre, outline; loudness I / LRA / true peak; words/s (--words).
                 It also keeps the per-frame data, so compare_video.py --range can re-measure any stretch of it.
  beats.jpg      start / middle / end of every setup, 160 px tiles, labelled (look at this first)
  transitions/   every frame through each transition, 13 per row, frame numbers on tiles (* = mixed frame)
  frames/        one 540x960 JPEG per setup middle, named s<setup>_<start s>.jpg (e.g. s05_06.97.jpg);
                 profile.json setups[i].frame points at it; compare_video.py pairs our frames with these
--acts: colour-act boundaries in seconds (default: thirds). Takes about 1 min 15 s for a 60 s video.
Needs numpy, PIL and ffmpeg/ffprobe on PATH. Only text is printed.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vidmetrics as vm  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    v, od = a[0], a[1]
    words = a[a.index('--words') + 1] if '--words' in a else None
    acts = [float(x) for x in a[a.index('--acts') + 1].split(',')] if '--acts' in a else None
    raw, prof = vm.build_profile(v, od, acts=acts, words=words)
    print(f"{prof['video']} -> {od}  ({prof['seconds']} s)")
    print(vm.text_summary(prof['summary'], prof['words'], prof['setups']))


if __name__ == '__main__':
    main()
