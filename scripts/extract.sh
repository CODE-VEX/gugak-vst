#!/bin/bash
# Extract the library zips in libraries/ (never modified) into work/extract/<lib>/<version>/.
# Each zip holds several releases as nested zips (some containing DMGs). Only the ones the build
# uses are extracted: v1.3.1, plus the older "EXS24 Hun-DEMO" / "EXS24 JangGu-DEMO" releases that
# carry the legacy Hun and JangGu maps. Set EXTRACT_ALL=1 to extract every release.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/libraries"
OUT="$ROOT/work/extract"
TMP="$ROOT/work/tmp"
mkdir -p "$OUT" "$TMP"

wanted() {
  [ "${EXTRACT_ALL:-0}" = 1 ] && return 0
  case "$1" in
    *v.1.3.1*|"EXS24 Hun-DEMO"|"EXS24 JangGu-DEMO") return 0 ;;
    *) return 1 ;;
  esac
}

shopt -s nullglob
zips=("$SRC"/*.zip)
[ ${#zips[@]} -gt 0 ] || { echo "No zips in $SRC" >&2; exit 1; }

for z in "${zips[@]}"; do
  lib="$(basename "$z" .zip)"; lib="${lib% exs24}"
  [ -f "$OUT/$lib/.done" ] && continue
  echo "   extracting $lib"
  rm -rf "${TMP:?}"/*; mkdir -p "$TMP/outer" "$OUT/$lib"
  unzip -q -o "$z" -d "$TMP/outer" -x '__MACOSX/*' 2>/dev/null || true
  cp "$TMP"/outer/*.pdf "$OUT/$lib/" 2>/dev/null || true
  find "$TMP/outer" -name '*.zip' -print0 | while IFS= read -r -d '' inner; do
    ver="$(basename "$inner" .zip)"
    wanted "$ver" || continue
    dest="$OUT/$lib/$ver"; mkdir -p "$dest"
    unzip -q -o "$inner" -d "$dest" -x '__MACOSX/*' '*/.DS_Store' '.DS_Store' 2>/dev/null || true
    find "$dest" -name '*.dmg' -print0 | while IFS= read -r -d '' dmg; do
      mp="$TMP/mnt"; mkdir -p "$mp"
      hdiutil attach -quiet -readonly -nobrowse -noverify -mountpoint "$mp" "$dmg"
      ditto --norsrc "$mp/Data" "$dest/$(basename "$dmg" .dmg)" 2>/dev/null || ditto --norsrc "$mp" "$dest/$(basename "$dmg" .dmg)"
      hdiutil detach -quiet "$mp"
      rm -f "$dmg"
    done
  done
  find "$OUT/$lib" -name '.DS_Store' -delete
  rm -rf "$TMP"/outer
  touch "$OUT/$lib/.done"
done
