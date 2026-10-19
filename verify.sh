#!/bin/bash
# Optional: check dist/Gugak.dsbundle against the original EXS24 instruments, offline.
# Needs DecentSampler installed and the Xcode command line tools (for swiftc). Takes ~40 minutes.
#
#   ./verify.sh            all instruments
#   ./verify.sh 1 9 21     only these menu entries (1 = first)
#
# Every mapped key is played through the DecentSampler AU and through Apple's AUSampler loading
# the original .exs, and the two are compared (null test, pitch, level). Then envelopes and
# key-switch isolation are checked and dist/null_test.png is drawn. Report: dist/verification.txt
set -euo pipefail
cd "$(dirname "$0")"
PY="$PWD/.venv/bin/python"

[ -f dist/Gugak.dsbundle/Gugak.dspreset ] || { echo "Run ./build.sh first." >&2; exit 1; }
[ -d work/stage ] || { echo "work/ is missing (./build.sh clean was run). Run ./build.sh again." >&2; exit 1; }
if [ ! -d ~/Library/Audio/Plug-Ins/Components/DecentSampler.component ] &&
   [ ! -d /Library/Audio/Plug-Ins/Components/DecentSampler.component ]; then
  echo "DecentSampler (AU) is not installed." >&2; exit 1
fi
command -v swiftc >/dev/null || { echo "swiftc not found. Install with: xcode-select --install" >&2; exit 1; }

echo "==> Building the offline test host (tools/dshost)"
swiftc -O -o tools/dshost/dshost tools/dshost/main.swift

echo "==> Preparing reference copies of the .exs files for AUSampler"
"$PY" scripts/exs_ref.py

report=dist/verification.txt
{
  echo "Gugak.dsbundle vs. the original .exs (Apple AUSampler), every mapped key at velocity 110."
  echo "null = residual after gain matching (dB, lower is better); cents = pitch offset; lvl = level vs. reference."
  echo "The three DaeGeum *simple* .exs files embed an extra -6 dB master volume that AUSampler applies,"
  echo "so they show about +8 dB instead of +1.5 dB; Logic's .pst presets set -6 dB for every instrument."
  echo
} > "$report"

echo "==> Comparing every key with the original (the slow part)"
"$PY" scripts/compare_ref.py "$@" | tee -a "$report"

echo "==> Checking envelopes, one-shots and key-switch isolation"
{ echo; echo "Level drop 100 ms after note-off, and key-switch isolation:"; } >> "$report"
"$PY" scripts/check_env.py | tee -a "$report"

echo "==> Drawing dist/null_test.png"
"$PY" scripts/plot_null.py

echo
echo "Report: $report"
