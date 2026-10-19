#!/bin/bash
# Build dist/Gugak.dsbundle from the GUgAK EXS24 zips in libraries/.
#
#   ./build.sh          build (re-running only redoes what changed)
#   ./build.sh clean    delete the intermediate files in work/ (keeps dist/)
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
PY="$ROOT/.venv/bin/python"

if [ "${1:-}" = clean ]; then
  rm -rf "$ROOT/work"
  echo "Removed work/. dist/ was kept."
  exit 0
fi

step() { printf '\n==> %s\n' "$*"; }
die() { printf '\nError: %s\n' "$*" >&2; exit 1; }

step "Checking requirements"
[ "$(uname -s)" = Darwin ] || die "this build needs macOS (it opens the libraries' disk images with hdiutil)."
command -v python3 >/dev/null || die "python3 not found. Install it from python.org or with: brew install python"
command -v flac >/dev/null || die "the flac encoder is not installed. Install it with: brew install flac"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "Python 3.9 or newer is required."
if [ ! -x "$PY" ]; then
  echo "   creating Python environment in .venv"
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install --quiet --upgrade pip
fi
if ! "$PY" -c 'import numpy, soundfile, scipy, matplotlib' 2>/dev/null; then
  echo "   installing Python packages (requirements.txt)"
  "$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"
fi
"$PY" scripts/check_libraries.py

step "Extracting library zips into work/extract (the zips are not modified)"
scripts/extract.sh

step "Collecting instruments and samples into work/stage"
"$PY" scripts/stage.py

# Hashing and FLAC encoding are the slow steps; skip them when the staged files are unchanged.
mkdir -p work
fingerprint="$(cd work/stage && find . -type f | LC_ALL=C sort | shasum | cut -d' ' -f1)"
if [ -f work/flac_a/manifest.json ] && [ "$(cat work/.stage_fingerprint 2>/dev/null)" = "$fingerprint" ]; then
  step "FLAC files are up to date"
else
  step "Finding duplicate samples (decoded audio hashes)"
  "$PY" scripts/hash_samples.py > work/hash_report.txt
  step "Encoding each unique sample to FLAC once and verifying it decodes bit-identically"
  rm -rf work/flac_a
  "$PY" scripts/encode_flac.py work/flac_a
  echo "$fingerprint" > work/.stage_fingerprint
fi

step "Building the DecentSampler instrument"
"$PY" scripts/build_ds.py dist

size="$(du -sh dist/Gugak.dsbundle | cut -f1)"
cat <<EOF

Done: dist/Gugak.dsbundle ($size)

Next:
  1. Install DecentSampler (free): https://www.decentsamples.com/product/decent-sampler-plugin/
  2. Move dist/Gugak.dsbundle to a permanent folder and open Gugak.dspreset in DecentSampler.
     Instructions: dist/README.md
  3. Optional: ./build.sh clean frees the disk space used by work/.
EOF
