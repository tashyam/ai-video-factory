#!/usr/bin/env bash
# One-time setup for /3d-video-studio. Safe to run again; it skips what is already installed.
#   bash setup.sh
# Installs: three.js for the engine, Playwright + Chromium (renders the frames), a Python venv in kit/.venv
# (numpy, scipy, pillow, sherpa-onnx) and the Parakeet word-timing model (about 500 MB, downloaded once).
# Windows: run it in Git Bash.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT="$ROOT/kit"
say() { printf '\033[1m%s\033[0m\n' "$*"; }

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing. Windows: winget install Gyan.FFmpeg | Mac: brew install ffmpeg | Linux: sudo apt install ffmpeg"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ is missing: https://nodejs.org"; exit 1; }
PY=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.9+ is missing: https://python.org (on Windows tick 'Add to PATH')"; exit 1; }

say "1/4  engine: three.js"
(cd "$ROOT/engine" && npm install --silent --no-audit --no-fund)

say "2/4  kit: Playwright + Chromium"
(cd "$KIT" && npm install --silent --no-audit --no-fund && npx --yes playwright install chromium >/dev/null)

venv_py() { if [ -x "$KIT/.venv/Scripts/python.exe" ]; then echo "$KIT/.venv/Scripts/python.exe"; else echo "$KIT/.venv/bin/python"; fi; }
say "3/4  kit: Python venv"
[ -x "$(venv_py)" ] || "$PY" -m venv "$KIT/.venv"
VPY="$(venv_py)"
"$VPY" -m pip install -q --upgrade pip
"$VPY" -m pip install -q numpy scipy pillow sherpa-onnx

M="$KIT/models"; mkdir -p "$M"
if ! ls -d "$M"/sherpa-onnx-nemo-parakeet* >/dev/null 2>&1; then
  say "4/4  word-timing model (Parakeet, about 500 MB, once)"
  curl -fL -o "$M/p.tar.bz2" https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2
  (cd "$M" && tar xjf p.tar.bz2 && rm p.tar.bz2)
else
  say "4/4  word-timing model already there"
fi

say "Ready. Fully close and reopen Claude Code, then start with /3d-video-studio"
