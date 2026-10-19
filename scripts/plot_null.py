"""Null test / spectral comparison figure: original WAV vs (a) its FLAC copy and (b) the same
sample played through the finished DecentSampler instrument at its root key."""
import json, os, sys
import numpy as np, soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from dsrender import render
from exsread import parse
from build_ds import available, STAGE, WORK, sample_index, FLAC

ROOT = os.path.dirname(WORK)
PRESET = os.path.join(ROOT, "dist", "Gugak.dsbundle", "Gugak.dspreset")
SR = 44100
PICK = ["GaYaGeum 18-string", "HaeGeum (modal)", "DaeGeum Unified (modal)", "JangGu"]


def spec(x):
    x = x * np.hanning(len(x))
    s = np.abs(np.fft.rfft(x)) / len(x)
    return np.fft.rfftfreq(len(x), 1 / SR), 20 * np.log10(s + 1e-12)


def smooth(y, n=64):
    return np.convolve(y, np.ones(n) / n, mode="same")


def main():
    by_inode = sample_index()
    insts = available()
    pick = [i for i, x in enumerate(insts) if x[1] in PICK]
    if not pick:
        return
    fig, axes = plt.subplots(len(pick), 1, figsize=(10, 3.2 * len(pick)), squeeze=False)
    axes = axes[:, 0]
    rows = []
    for ax, ii in zip(axes, pick):
        cat, label, lib, exs = insts[ii]
        p = parse(os.path.join(STAGE, lib, exs))
        z = next(z for z in sorted(p["zones"], key=lambda z: z["root"])
                 if not z["coarse"] and not z["fine"] and z["lo"] <= z["root"] <= z["hi"] and not z["start"])
        wav = os.path.join(STAGE, lib, p["samples"][z["sample"]])
        src, _ = sf.read(wav, always_2d=True, dtype="float64")
        flac, _ = sf.read(os.path.join(FLAC, by_inode[os.stat(wav).st_ino]["path"]), always_2d=True, dtype="float64")
        flac_null = float(np.abs(src - flac).max())
        out = os.path.join(WORK, "renders", f"null_{ii + 1:02d}.wav")
        render(PRESET, [(0.05, -1, 102, ii), (0.5, 1.5, z["root"], 127)], out, settle=6.0)
        y, _ = sf.read(out, always_2d=True)
        y = y[int(0.5 * SR):, 0]
        s = src[:, 0]
        n = int(1.0 * SR)
        lag = max(range(0, 1024), key=lambda l: float(np.dot(y[l:l + n], s[:n])))
        yy = y[lag:lag + n]
        g = float(np.dot(yy, s[:n]) / np.dot(s[:n], s[:n]))
        res = yy - g * s[:n]
        null_db = 10 * np.log10(np.sum(res ** 2) / np.sum(yy ** 2))
        f, a = spec(g * s[:n]); _, b = spec(yy); _, c = spec(res)
        ax.semilogx(f[1:], smooth(a)[1:], label="original WAV (gain-matched)", lw=1.2)
        ax.semilogx(f[1:], smooth(b)[1:], label="through Gugak.dsbundle", lw=1.0, ls="--")
        ax.semilogx(f[1:], smooth(c)[1:], label=f"difference ({null_db:.0f} dB)", lw=1.0)
        ax.set_xlim(30, 20000); ax.set_ylim(-200, max(a.max(), b.max()) + 10)
        ax.set_title(f"{label}: {os.path.basename(wav)}  |  FLAC vs WAV max sample difference = {flac_null:g}")
        ax.set_ylabel("dB"); ax.legend(loc="lower left", fontsize=8); ax.grid(alpha=0.3)
        rows.append(dict(instrument=label, sample=os.path.basename(wav), flac_max_abs_diff=flac_null,
                         plugin_null_db=round(null_db, 1), plugin_gain_db=round(20 * np.log10(g), 2)))
    axes[-1].set_xlabel("Hz")
    fig.tight_layout()
    png = os.path.join(ROOT, "dist", "null_test.png")
    fig.savefig(png, dpi=110)
    json.dump(rows, open(os.path.join(WORK, "null_test.json"), "w"), indent=1)
    for r in rows:
        print(r)
    print(png)


if __name__ == "__main__":
    main()
