# GUgAK — all catsnu gugak demo libraries in one instrument

`Gugak.dsbundle` is a single DecentSampler instrument with 43 instruments in one menu
(strings, bowed, winds, percussion). It plays in DecentSampler, which is a free AU / VST3 /
standalone sampler with a native Apple Silicon (arm64) build. No Rosetta needed.

## Contents

| Item | Size | Needed? |
|---|---|---|
| `Gugak.dsbundle/` (preset + 567 FLAC samples) | 487 MB | yes |
| `Extras (unmapped samples, optional)/` | 60 MB | no: 73 recorded articulations that no original preset maps |
| `build_info.json` | | no: what was built (instrument list, sample counts) |
| `null_test.png`, `verification.txt` | | no: written by `./verify.sh` |

## Install

1. Install DecentSampler (free) from
   <https://www.decentsamples.com/product/decent-sampler-plugin/>. It was tested with version
   1.38.0. The installer adds `DecentSampler.component` (AU) and `DecentSampler.vst3`.
2. Copy `Gugak.dsbundle` to a permanent place, for example `~/Music/Gugak/Gugak.dsbundle`.
   Logic projects reference this path, so don't move the bundle afterwards.
3. Logic Pro: create a Software Instrument track, then choose Instrument slot → AU Instruments →
   Decidedly → DecentSampler. In the plugin window, use DecentSampler's load/browse button to open
   `Gugak.dsbundle/Gugak.dspreset`.
4. Pick an instrument from the menu. The selection is saved with the Logic project.

If Logic doesn't list DecentSampler, open Logic → Settings → Plug-in Manager and click *Reset &
Rescan Selection*.

## Controls

* **Instrument menu**: switches all 43 instruments. Each entry also resets Attack/Release to that
  instrument's original Logic EXS24 setting.
* **MIDI CC 102** selects an instrument from a DAW lane or controller: value 0 = first menu
  entry, 1 = second, … 42 = last (PyeonGyeong).
* **Attack / Release** (seconds), **Volume**, **Reverb** (wet level, default 0 = dry like the
  originals) and **Room** (reverb size).
* **GeoMunGo (key switch)**: A0 (MIDI 21) = yu string, A#0 (22) = dae string, B0 (23) = open
  strings, as in the original. Default is yu. The key switches only work while this instrument is
  selected.

Samples stream from disk: about 250 MB of RAM for the whole library, whichever instrument is
selected.

## Size

| Stage | Size |
|---|---|
| Original zips (23) | 5,702 MB |
| All extracted audio (every version, template and duplicate) | 5,967 MB |
| Unique audio, WAV | 1,108 MB |
| Unique audio, FLAC (lossless, bit-identical) | 547 MB |
| **Final instrument (samples the presets use)** | **487 MB** (+ 60 MB optional extras) |

## Known differences from the Logic originals

* **Pitch bend:** DecentSampler has one global bend range, set to ±5 semitones. That matches the
  plucked and bowed strings. The originals used ±2 for winds, ±12 for JangGu, and 0 for PyeonJong,
  PyeonGyeong and YangGeum. To change it, edit `BEND_RANGE` in `scripts/build_ds.py` and rebuild.
* **Velocity response:** DecentSampler's response is linear in amplitude (velocity 100 is −2.1 dB
  relative to 127). EXS24's curve at full sensitivity may differ slightly.
* **Envelope curves:** release times are the original values, but the curve shapes are
  DecentSampler's.
* **Polyphony:** the originals set 16 voices; DecentSampler doesn't enforce that limit.
* **GeoMunGo exclusive groups:** each string group cuts its own previous note, as the EXS
  "exclusive" setting does.
* **Duplicate libraries:** the 18-string and 25-string GaYaGeum use identical samples and
  mapping; they differ only in release time (0.53 s vs 0.69 s). The two legacy Hun maps were
  identical, so the menu has one entry for them.
