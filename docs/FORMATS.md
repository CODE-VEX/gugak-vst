# Notes on the GUgAK EXS24 files

These notes come from inspecting the GUgAK DEMO libraries. They cover only what these files use
and are not a full specification. The code that reads them is `scripts/exsread.py` and
`scripts/pstread.py`.

## Why the libraries are hard to use on a current Mac

* **Absolute sample paths.** Every `.exs` stores its sample folder as an absolute path such as
  `/Library/Application Support/Logic/EXS Factory Samples/GUgAK DEMO/Winds/PiRi (Dang)-DEMO`.
  If the samples aren't installed at exactly that path, Logic reports missing samples or plays
  silence.
* **Truncated sample names.** The name in each sample block's header is cut to about 31
  characters plus a hash (`G18_R2_NongB_13_C3_f#929F23.wav`). The real filename is in a second,
  256-byte field.
* **Dead references.** The legacy JangGu map (`EXS24 JangGu-DEMO`) lists 17 sample blocks
  under old filenames that ship nowhere. No zone uses them, but strict loaders such as Apple's
  AUSampler refuse to open the instrument.
* **Packaging.** Each zip contains several releases (v1.2, v1.3, v1.3.1 and older "EXS24 …-DEMO"
  builds) as nested zips, some holding disk images, plus Logic project templates. 5.97 GB of
  extracted audio contains 1.1 GB of unique recordings.

## .exs (EXS24 instrument)

The file is a sequence of blocks. Each block has an 84-byte header followed by `size` bytes of
data. The files here are little-endian, with magic `TBOS`.

| Header offset | Field |
|---|---|
| 0 | 4-byte signature; `byte[3] & 0x0F` is the block type: 0 instrument, 1 zone, 2 group, 3 sample, 4 parameters |
| 4 | u32 data size |
| 8 | u32 index |
| 16 | magic `TBOS` |
| 20 | 64-byte name |

**Zone** (data offsets):

| Offset | Field |
|---|---|
| 0 | option bits: 1 one-shot, 2 pitch tracking off, 4 reverse, 8 velocity range on |
| 1 | root key |
| 2 | fine tune (signed, cents) |
| 3 | pan (signed) |
| 4 | volume (signed, dB) |
| 6–7 | key range low/high |
| 9–10 | velocity low/high |
| 12, 16 | sample start, sample end (u32 frames) |
| 20, 24, 28 | loop start, loop end, loop crossfade (u32) |
| 33 | loop on (bit 0) |
| 80 | coarse tune (signed, semitones) |
| 88 | group index (i32; −1 = none) |
| 92 | sample index (u32) |

**Group**:

| Offset | Field |
|---|---|
| 0, 1 | volume, pan |
| 2 | polyphony |
| 3 | options (bit 16 = mute) |
| 4 | exclusive group |
| 5–6 | velocity range |
| 73 | release trigger |
| 75 | key-switch note |
| 80 | round-robin position (i32) |
| 84 | "enable by" type (1 = note, i.e. key switch) |

**Sample**: the folder path is a 256-byte string at data offset 80; the full filename is a
256-byte string at offset 336.

**Parameters** (optional; only the three DaeGeum *simple* maps have one): u32 `n`, then `n`
parameter-id bytes, then `n` signed 16-bit values. After those come u32 `m` and `m` pairs of
(u16 id, s16 value). The ids are the same as in `.pst` files.

## .pst (Logic EXS24 plug-in setting)

The `.pst` presets hold the playing settings: volume, envelope, bend range and so on.

* `MELCPMAS1MAS` at offset 12.
* The `.exs` filename (64 bytes) at 0x18.
* From 0x58, pairs of (i32 parameter id, i32 value) until a 0,0 pair.

| Id | Parameter | Conversion |
|---|---|---|
| 0x07 | master volume | dB |
| 0x05 | polyphony | |
| 0x03 / 0x04 | bend up / down | semitones |
| 0x52 / 0x53 | attack (high / low velocity) | seconds = 10 · (raw / 127)⁴ |
| 0x54 | decay | same as attack |
| 0x51 | sustain | raw / 127 |
| 0x55 | release | same as attack |
| 0x5a | velocity sensitivity | depth = raw / −60 |
| 0x2c | filter on | |

What the GUgAK presets set:
* every preset: master −6 dB, 16 voices, attack 0, full sustain, velocity depth 1, no filter;
* release: winds 0.046 s, AJaeng 0.158 s, HaeGeum 0.109 s, GeoMunGo and the JeongAk/SanJo
  GaYaGeum 0.406 s, 18-string GaYaGeum 0.532 s, 25-string GaYaGeum 0.686 s;
* JangGu, PyeonJong, PyeonGyeong and YangGeum are one-shots.

None of the instruments use velocity layers, round robins, loops or release samples.

## DecentSampler behaviour this build relies on

Tested with DecentSampler 1.38.0 by rendering the AU offline (`tools/dshost`).

* Menu options can set group `ENABLED` flags, UI control values and MIDI note handlers. Setting
  a menu's value through a binding (here, MIDI CC 102) fires that option's bindings. Setting the
  value it already has does nothing.
* The plugin state saves the current group `enabled` flags, knob values, menu value and note
  handler state, so a selection survives saving and reopening a project.
* `TAG_ENABLED` and `<tags enabled="false">` do not stop groups from playing, so instruments are
  switched with group `ENABLED` instead.
* `pitchBendRange` only works on `<groups>`, so there is one range for the whole preset.
* Output is 5.28 dB below the sample level at velocity 127 with volume 1.0. Velocity response is
  linear in amplitude.
