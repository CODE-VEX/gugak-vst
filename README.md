# Gugak for DecentSampler

This repo turns the **Gugak DEMO** Korean traditional instrument sample libraries by
CATSNU (Seoul National University) into one instrument for
[DecentSampler](https://www.decentsamples.com/product/decent-sampler-plugin/). DecentSampler is a
free AU / VST3 / standalone sampler that runs natively on Apple Silicon and loads in Logic Pro and
other DAWs.

The original libraries are Logic EXS24 instruments. They depend on samples being installed at
fixed system paths, and on current Macs they often load with missing samples or not at all. This
project reads the original `.exs` mappings and `.pst` settings, converts the audio losslessly to
FLAC, and builds a single `Gugak.dsbundle` with all 43 instruments behind one menu: GaYaGeum,
GeoMunGo, YangGeum, HaeGeum, AJaeng, DaeGeum, SoGeum, DanSo, PiRi, TaePyeongSo, Hun, JangGu,
PyeonJong and PyeonGyeong.

**No samples are included.** You supply the library zips; the scripts build the instrument from
them.

## Requirements

* macOS (Apple Silicon or Intel)
* Python 3.9 or newer
* the `flac` encoder: `brew install flac` (needs [Homebrew](https://brew.sh))
* about 4 GB of free disk space during the build. The finished instrument is 487 MB, and
  `./build.sh clean` removes the rest afterwards.

The build takes a few minutes (about 3 on an M-series MacBook).

## Build

1. Download the instruments from the CATSNU GUGAK page:
   <http://en.catsnu.com/Project/GugakVSTi.aspx>. For each wind, string and percussion
   instrument, choose the **EXS24** download; the KONTAKT, Live and Windows VST versions aren't
   used.
   Put the 23 zips into `libraries/`, keeping their original names
   (`18-string_geum exs24.zip`, `geomungo exs24.zip`, …). The full list is in
   [libraries/README.md](libraries/README.md).
2. Run:

   ```bash
   ./build.sh
   ```

   The first run creates a Python environment in `.venv`, extracts the zips (they are only
   read), encodes the audio and writes:

   ```
   dist/
     Gugak.dsbundle/                          the instrument (preset + 567 FLAC samples)
     Extras (unmapped samples, optional)/     73 recorded samples no original preset uses
     README.md                                how to install and play it
     build_info.json
   ```

   If some zips are missing, the build continues and leaves those instruments out.
3. Optional: `./build.sh clean` deletes the intermediate files in `work/`.

## Install and play

1. Install DecentSampler (free).
2. Move `dist/Gugak.dsbundle` to a permanent folder. Projects remember its location.
3. In Logic Pro: Software Instrument track → AU Instruments → Decidedly → DecentSampler, then
   load `Gugak.dsbundle/Gugak.dspreset` and pick an instrument from the menu.

Controls, key switches and MIDI CC instrument selection are described in
[docs/INSTRUMENT_README.md](docs/INSTRUMENT_README.md), which is also copied to `dist/README.md`.

## How faithful is it?

Audio is lossless: every FLAC decodes bit-identical to the original WAV. Mappings, tuning,
one-shots, key switches, exclusive groups and per-instrument release times come from the original
files.

`./verify.sh` (optional) plays every mapped key of every instrument through DecentSampler and
through Apple's AUSampler loading the original `.exs`, and compares them. For the reference build,
all 1,137 notes matched: 0 cents pitch difference, levels within 0.1 dB, and null-test residuals
between −49 and −90 dB. It needs DecentSampler and the Xcode command line tools, and takes about
40 minutes.

Known differences from Logic, such as a single global pitch-bend range of ±5 semitones, are
listed in [docs/INSTRUMENT_README.md](docs/INSTRUMENT_README.md#known-differences-from-the-logic-originals).

## How it works

| Step | Script |
|---|---|
| Extract the v1.3.1 release (plus the legacy Hun/JangGu maps) from each zip | `scripts/extract.sh` |
| Gather each library's `.exs` files and samples into one folder (hard links) | `scripts/stage.py` |
| Hash the decoded audio to find duplicates | `scripts/hash_samples.py` |
| Encode each unique sample to FLAC once and verify it | `scripts/encode_flac.py` |
| Read `.exs` + `.pst` and write the DecentSampler preset | `scripts/build_ds.py` (uses `exsread.py`, `pstread.py`) |
| Offline comparison with the originals | `verify.sh`, `scripts/compare_ref.py`, `check_env.py`, `plot_null.py`, `tools/dshost/` |

`scripts/inventory.py` and `scripts/analyze_audio.py` are analysis tools used while developing:
a per-library inventory, and checks of channels and silence.

The reverse-engineered EXS24 and `.pst` layouts, and the DecentSampler behaviour the build relies
on, are documented in [docs/FORMATS.md](docs/FORMATS.md).

## Credits and licence

Recordings: the GUgAK DEMO libraries by CATSNU, Seoul National University. The samples are not
part of this repository and remain under their original terms.

The code in this repository is released under the [MIT licence](LICENSE).
