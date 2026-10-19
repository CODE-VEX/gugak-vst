"""Compare every key of every instrument in dist/Gugak.dsbundle with the original .exs.

DecentSampler side: the instrument is selected with MIDI CC 102 (exercising the menu bindings).
Reference side: Apple's AUSampler loads the original .exs (path-patched copy in work/exs_ref).
Both get the same notes; per note we measure the null-test residual after alignment and gain
fit, the pitch offset (log-frequency spectrum cross-correlation, cents) and the level.
The envelopes differ by design (AUSampler does not read the .pst), so only the sustained part of
each note is compared.

usage: compare_ref.py [instrument numbers...]
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from dsrender import render, HOST
from exsread import parse
from build_ds import available, STAGE, WORK

ROOT = os.path.dirname(WORK)
PRESET = os.path.join(ROOT, "dist", "Gugak.dsbundle", "Gugak.dspreset")
OUT = os.path.join(WORK, "renders", "compare")
STEP, DUR, VEL, T0 = 1.5, 0.6, 110, 0.5
SR = 44100


def render_ref(exs, notes, out):
    with tempfile.TemporaryDirectory() as td:
        st = os.path.join(td, "s.xml"); sc = os.path.join(td, "score.txt")
        open(st, "w").write("<x/>")
        open(sc, "w").write("\n".join(f"{a} {b} {n} {v}" for a, b, n, v in notes))
        r = subprocess.run([HOST, "render", st, sc, out, "1"], capture_output=True, text=True,
                           env=dict(os.environ, DSHOST_EXS=exs))
        if r.returncode:
            raise RuntimeError(r.stderr + r.stdout)


def logspec(x):
    x = x.mean(axis=1) * np.hanning(len(x))
    n = 1 << 17
    sp = np.abs(np.fft.rfft(x, n)) + 1e-9
    fr = np.fft.rfftfreq(n, 1 / SR)
    grid = 40 * 2 ** (np.arange(0, 1200 * np.log2(8000 / 40), 5) / 1200)  # 5-cent bins
    return np.log(np.interp(grid, fr, sp))


def pitch_offset(a, b):
    la, lb = logspec(a), logspec(b)
    la -= la.mean(); lb -= lb.mean()
    best = max(range(-60, 61), key=lambda s: np.dot(la[100 + s:len(la) - 100 + s], lb[100:len(lb) - 100]))
    return best * 5


def null(a, b):
    """residual (dB) of a against gain-scaled, time-aligned b."""
    n = len(a)
    ref = a
    mid = (len(b) - n) // 2
    best = None
    for lag in range(max(0, mid - 64), min(len(b) - n, mid + 64) + 1):
        seg = b[lag:lag + n]
        c = float(np.dot(seg, ref) / (np.linalg.norm(seg) + 1e-20))
        if best is None or c > best[0]:
            best = (c, lag)
    seg = b[best[1]:best[1] + n]
    g = np.sum(seg * ref) / max(np.sum(seg * seg), 1e-20)
    return 10 * np.log10(np.sum((ref - g * seg) ** 2) / max(np.sum(ref ** 2), 1e-20))


def rms_db(x):
    return 10 * np.log10(np.mean(x ** 2) + 1e-20)


def passes(p):
    """[(keyswitch note or None, zones)]"""
    g = p["groups"]
    ks = [(i, x["enable_by_note_value"]) for i, x in enumerate(g) if x["enable_by_type"] == 1]
    if not ks:
        return [(None, p["zones"])]
    return [(note, [z for z in p["zones"] if z["group"] == gi]) for gi, note in ks]


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    summary = []
    for ii, (cat, label, lib, exs) in enumerate(available()):
        if only and ii + 1 not in only:
            continue
        p = parse(os.path.join(STAGE, lib, exs))
        oneshot = any(z["oneshot"] for z in p["zones"])
        for pi, (ks, zones) in enumerate(passes(p)):
            keys = sorted({k for z in zones for k in range(z["lo"], z["hi"] + 1)})
            body = []
            if ks is not None:
                body.append((0.2, 0.1, ks, 100))
            for k, key in enumerate(keys):
                body.append((T0 + k * STEP, DUR, key, VEL))
            tag = f"{ii + 1:02d}" + (f"_ks{ks}" if ks is not None else "")
            ds_wav, ref_wav = os.path.join(OUT, tag + "_ds.wav"), os.path.join(OUT, tag + "_ref.wav")
            render(PRESET, [(0.05, -1, 102, ii)] + body, ds_wav, settle=6.0)
            render_ref(os.path.join(WORK, "exs_ref", lib, exs), body, ref_wav)
            d, _ = sf.read(ds_wav, always_2d=True)
            r, _ = sf.read(ref_wav, always_2d=True)
            rows = []
            for k, key in enumerate(keys):
                a0 = int((T0 + k * STEP + 0.03) * SR)
                a1 = int((T0 + k * STEP + (0.5 if oneshot else DUR - 0.05)) * SR)
                da, ra = d[a0:a1], r[a0 - 600:a1 + 600]
                dl, rl = rms_db(da), rms_db(ra[600:-600])
                if dl < -90 and rl < -90:
                    rows.append(dict(key=key, silent=True)); continue
                rows.append(dict(key=key, ds_db=round(dl, 1), ref_db=round(rl, 1),
                                 null_db=round(null(da.mean(axis=1), ra.mean(axis=1)), 1),
                                 cents=pitch_offset(da, ra[600:-600])))
            live = [x for x in rows if not x.get("silent")]
            diffs = np.array([x["ds_db"] - x["ref_db"] for x in live]) if live else np.array([0.0])
            med = float(np.median(diffs))
            for x in live:
                x["level_dev"] = round(x["ds_db"] - x["ref_db"] - med, 2)
            bad = [x for x in live if abs(x["level_dev"]) > 1.0 or abs(x["cents"]) > 5 or x["null_db"] > -20]
            silent = [x["key"] for x in rows if x.get("silent")]
            onesided = [x["key"] for x in live if x["ds_db"] < -90 or x["ref_db"] < -90]
            s = dict(index=ii + 1, name=label, ks=ks, keys=len(keys), median_level_diff_db=round(med, 2),
                     worst_null_db=max((x["null_db"] for x in live), default=None),
                     max_abs_cents=max((abs(x["cents"]) for x in live), default=None),
                     ds_peak=round(float(np.abs(d).max()), 3), flagged=bad, silent_both=silent, one_sided=onesided)
            summary.append(s)
            print(f"{ii + 1:2d} {label[:30]:30s}{'' if ks is None else f' ks{ks}':6s} keys {len(keys):3d}  "
                  f"lvl {med:+5.1f} dB  worst null {s['worst_null_db']}  max |cents| {s['max_abs_cents']}  "
                  f"peak {s['ds_peak']}  flagged {len(bad)}  silent {len(silent)}  one-sided {onesided}", flush=True)
    json.dump(summary, open(os.path.join(OUT, "summary.json" if not only else "summary_partial.json"), "w"), indent=1)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or None)
