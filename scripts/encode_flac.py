"""Step 3a/3b/3d: encode each unique sample once to FLAC (optionally tail-trimmed) and verify.

Usage: encode_flac.py <outdir> [--trim]
Writes <outdir>/<canonical lib>/<name>.flac and <outdir>/manifest.json mapping
PCM hash -> relative path, plus every original file path -> PCM hash.
"""
import json, os, subprocess, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import soundfile as sf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "work"))
OUT = os.path.abspath(sys.argv[1])
TRIM = "--trim" in sys.argv
TRIM_DB = -84.0       # tail is cut after the last 1 ms block that exceeds this level
TAIL_PAD_MS = 50      # kept after that point, faded out with a raised cosine

rows = json.load(open(os.path.join(ROOT, "hashes.json")))
EXTRA = {("hun", "EXS24 Hun-DEMO"), ("janggu", "EXS24 JangGu-DEMO")}
sel = [r for r in rows if not r["in_template"] and ("v.1.3.1" in r["ver"] or (r["lib"], r["ver"]) in EXTRA)]

CANON = {"25-string_geum": "gayageum-18-25-string", "18-string_geum": "gayageum-18-25-string",
         "daegeum (unified)": "daegeum-shared", "jeongakdaegeum": "daegeum-shared",
         "sanjodaegeum": "daegeum-shared"}

uniq = {}
for r in sorted(sel, key=lambda r: (r["lib"], r["name"])):
    uniq.setdefault(r["pcm"], r)

dest = {}
used = set()
for h, r in uniq.items():
    folder = CANON.get(r["lib"], r["lib"]).replace(" ", "_").replace("(", "").replace(")", "")
    base = os.path.splitext(r["name"])[0]
    rel = f"{folder}/{base}.flac"
    i = 2
    while rel in used:
        rel = f"{folder}/{base}_{i}.flac"; i += 1
    used.add(rel); dest[h] = rel


def trim_tail(x, sr):
    mono = np.max(np.abs(x), axis=1)
    hop = sr // 1000
    n = len(mono) // hop
    env = mono[: n * hop].reshape(n, hop).max(axis=1)
    loud = np.nonzero(20 * np.log10(env + 1e-30) > TRIM_DB)[0]
    last = (loud[-1] + 1) * hop if len(loud) else 0
    keep = min(len(x), last + TAIL_PAD_MS * sr // 1000)
    if keep >= len(x) - sr // 100:          # less than 10 ms to gain: leave untouched
        return x, False
    y = x[:keep].copy()
    fl = keep - last
    if fl > 0:
        fade = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fl)))
        y[last:keep] *= fade[:, None]
    return y, True


def work(item):
    h, r = item
    src = os.path.join(ROOT, "extract", r["path"])
    out = os.path.join(OUT, dest[h])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    info = sf.info(src)
    trimmed = False
    if TRIM:
        x, sr = sf.read(src, dtype="float64", always_2d=True)
        y, trimmed = trim_tail(x, sr)
        tmp = out[:-5] + ".tmp.wav"
        sf.write(tmp, y, sr, subtype=info.subtype)
        src_enc = tmp
    else:
        src_enc = src
    # flac warns about every GUgAK WAV header (24-bit "legacy" format tag, PAD chunks); harmless
    proc = subprocess.run(["flac", "-8", "-e", "-p", "-f", "-s", "--no-padding", "-o", out, src_enc],
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"flac failed on {src_enc}:\n{proc.stderr}")
    # verify: decoded FLAC PCM must equal the encoder input PCM exactly
    a, _ = sf.read(src_enc, dtype="int32", always_2d=True)
    b, _ = sf.read(out, dtype="int32", always_2d=True)
    ok = a.shape == b.shape and np.array_equal(a, b)
    if TRIM:
        os.remove(src_enc)
    return h, dict(path=dest[h], ok=bool(ok), trimmed=trimmed, frames=len(b), src_frames=info.frames,
                   bytes=os.path.getsize(out), wav_bytes=r["bytes"])


with ThreadPoolExecutor(os.cpu_count()) as ex:
    res = dict(ex.map(work, uniq.items()))

manifest = dict(samples=res, files={r["path"]: r["pcm"] for r in sel})
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
bad = [v["path"] for v in res.values() if not v["ok"]]
print(f"encoded {len(res)}  failures {len(bad)} {bad[:5]}")
print(f"WAV bytes (unique): {sum(v['wav_bytes'] for v in res.values())/1e6:.1f} MB -> "
      f"FLAC {sum(v['bytes'] for v in res.values())/1e6:.1f} MB; trimmed {sum(v['trimmed'] for v in res.values())}")
