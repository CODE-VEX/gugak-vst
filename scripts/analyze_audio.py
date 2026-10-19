"""Measure each unique sample: channel identity, peak, noise floor, silent head/tail."""
import json, os, sys
import numpy as np
import soundfile as sf

ROOT = os.path.join(os.path.dirname(__file__), "..", "work")
rows = json.load(open(os.path.join(ROOT, "hashes.json")))
EXTRA = {("hun", "EXS24 Hun-DEMO"), ("janggu", "EXS24 JangGu-DEMO")}
sel = [r for r in rows if not r["in_template"] and ("v.1.3.1" in r["ver"] or (r["lib"], r["ver"]) in EXTRA)]
uniq = {}
for r in sel:
    uniq.setdefault(r["pcm"], r)

THRESH_DB = [-96, -84, -72, -60]


def edge_lengths(env_db, thr):
    above = np.nonzero(env_db > thr)[0]
    if len(above) == 0:
        return len(env_db), len(env_db)
    return int(above[0]), int(len(env_db) - 1 - above[-1])


out = []
for h, r in uniq.items():
    p = os.path.join(ROOT, "extract", r["path"])
    x, sr = sf.read(p, dtype="float64", always_2d=True)
    xi, _ = sf.read(p, dtype="int32", always_2d=True)
    ident = x.shape[1] == 2 and np.array_equal(xi[:, 0], xi[:, 1])
    corr = None
    if x.shape[1] == 2 and not ident:
        a, b = x[:, 0], x[:, 1]
        corr = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))
        side_db = 20 * np.log10(np.max(np.abs(a - b)) + 1e-30)
    mono = np.max(np.abs(x), axis=1)
    peak_db = 20 * np.log10(mono.max() + 1e-30)
    # 1 ms max-abs envelope
    hop = sr // 1000
    n = len(mono) // hop
    env = mono[: n * hop].reshape(n, hop).max(axis=1)
    env_db = 20 * np.log10(env + 1e-30)
    edges = {t: edge_lengths(env_db, t) for t in THRESH_DB}
    # noise floor: RMS of quietest 50 ms window in the first 300 ms or last 300 ms
    out.append(dict(
        lib=r["lib"], name=r["name"], pcm=h, frames=len(x), ch=x.shape[1], subtype=r["subtype"],
        identical_channels=bool(ident), lr_corr=corr,
        side_peak_db=None if corr is None else float(side_db),
        peak_db=float(peak_db),
        head_ms={t: e[0] for t, e in edges.items()}, tail_ms={t: e[1] for t, e in edges.items()},
        first_ms_db=float(env_db[:5].max()), last_ms_db=float(env_db[-5:].max()),
        bytes=r["bytes"],
    ))
json.dump(out, open(os.path.join(ROOT, "audio_analysis.json"), "w"), indent=0)

tot = len(out)
print(f"unique samples: {tot}")
print("bit-identical L/R stereo:", sum(o["identical_channels"] for o in out))
st = [o for o in out if o["ch"] == 2 and not o["identical_channels"]]
print("stereo, not identical:", len(st), " corr>0.9999:", sum(o["lr_corr"] > 0.9999 for o in st),
      " corr>0.99:", sum(o["lr_corr"] > 0.99 for o in st))
print("min/median corr:", min(o["lr_corr"] for o in st) if st else None,
      np.median([o["lr_corr"] for o in st]) if st else None)
total_ms = sum(o["frames"] for o in out) / 44.1
for t in THRESH_DB:
    h = sum(o["head_ms"][t] for o in out); tl = sum(o["tail_ms"][t] for o in out)
    print(f"below {t} dBFS: head {h/1000:7.1f}s  tail {tl/1000:7.1f}s  of total {total_ms/1000:.1f}s "
          f"({100*(h+tl)/total_ms:.1f}%)")
print("first-ms level  (dBFS) min/median/max:",
      np.percentile([o["first_ms_db"] for o in out], [0, 50, 100]).round(1))
print("last-ms level   (dBFS) min/median/max:",
      np.percentile([o["last_ms_db"] for o in out], [0, 50, 100]).round(1))
print("peak dBFS min/median/max:", np.percentile([o["peak_db"] for o in out], [0, 50, 100]).round(1))
