"""Envelope / switching checks on dist/Gugak.dsbundle through the DecentSampler AU.

For selected instruments (chosen via CC 102): play one note for 0.5 s and measure how long the
output takes to fall 40 dB after note-off, compared with the .pst release time. One-shot
instruments must keep sounding after note-off. Also checks that the GeoMunGo key switches are
inactive when another instrument is selected.
"""
import os, sys
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from dsrender import render
from build_ds import available, pst_settings
from exsread import parse
from build_ds import STAGE, WORK

ROOT = os.path.dirname(WORK)
PRESET = os.path.join(ROOT, "dist", "Gugak.dsbundle", "Gugak.dspreset")
OUT = os.path.join(WORK, "renders", "env")
SR = 44100


def env_db(x, win=441):
    m = np.sqrt(np.convolve(x.mean(axis=1) ** 2, np.ones(win) / win, mode="same"))
    return 20 * np.log10(m + 1e-12)


def main():
    os.makedirs(OUT, exist_ok=True)
    psts = pst_settings()
    print("instrument                          pst release  level drop 100 ms after note-off")
    insts = available()
    gmg = next((i for i, x in enumerate(insts) if x[3] == "GeoMunGo - DEMO_simple.exs"), None)
    for ii, (cat, label, lib, exs) in enumerate(insts):
        p = parse(os.path.join(STAGE, lib, exs))
        z = sorted(p["zones"], key=lambda z: z["root"])[len(p["zones"]) // 2]
        notes = [(0.05, -1, 102, ii)]
        if ii == gmg:
            notes.append((0.2, 0.1, 21, 100))
        notes.append((0.5, 0.5, z["root"], 110))
        wav = os.path.join(OUT, f"{ii + 1:02d}.wav")
        render(PRESET, notes, wav, settle=6.0)
        x, _ = sf.read(wav, always_2d=True)
        e = env_db(x)
        off = int(1.0 * SR)
        before = e[off - 2205]
        after = e[off + int(0.1 * SR)]
        one = any(zz["oneshot"] for zz in p["zones"])
        rel = psts[exs]["release_s"]
        print(f"{ii + 1:2d} {label[:32]:32s} {rel:6.3f} s {'(one-shot)' if one else '          '}  "
              f"{before - after:5.1f} dB", flush=True)

    # key switch must not affect other instruments: select another instrument after GeoMunGo,
    # press A0 (GeoMunGo yu key switch) then play; output must equal that instrument alone.
    if gmg is None or len(insts) < 2:
        return
    other = 0 if gmg != 0 else 1
    base = render(PRESET, [(0.05, -1, 102, other), (0.5, 0.6, 60, 110)], os.path.join(OUT, "ks_base.wav"), settle=6.0)
    test = render(PRESET, [(0.05, -1, 102, gmg), (0.15, -1, 102, other), (0.25, 0.1, 21, 100), (0.5, 0.6, 60, 110)],
                  os.path.join(OUT, "ks_test.wav"), settle=6.0)
    a, _ = sf.read(base, always_2d=True); b, _ = sf.read(test, always_2d=True)
    n = min(len(a), len(b))
    r = 10 * np.log10(np.sum((a[:n] - b[:n]) ** 2) / np.sum(a[:n] ** 2) + 1e-30)
    print(f"GeoMunGo key switch while {insts[other][1]} selected: difference vs. {insts[other][1]} alone {r:.1f} dB")


if __name__ == "__main__":
    main()
