"""Build one DecentSampler instrument (Gugak.dsbundle) containing every GUgAK EXS24 preset.

Mappings come straight from the .exs files (exsread) and the envelope settings from the
matching Logic .pst files (pstread). Audio is the lossless FLAC set in work/flac_a.

Instrument switching: a menu whose options set every group's ENABLED flag, the Attack and
Release knobs, and the GeoMunGo key-switch note handlers. CC 102 drives the same menu
(CC value n selects entry n + 1).
"""
import glob, json, os, shutil, sys
from xml.sax.saxutils import quoteattr

sys.path.insert(0, os.path.dirname(__file__))
from exsread import parse
from pstread import parse_pst, summarize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work")
STAGE = os.path.join(WORK, "stage")
FLAC = os.path.join(WORK, "flac_a")
SELECT_CC = 102
# DecentSampler only has one global bend range; the originals use 2 (winds) or 5 (strings).
BEND_RANGE = 5

# (category, display name, stage folder, .exs file)
INSTRUMENTS = [
    ("Strings", "GaYaGeum 18-string", "18-string_geum", "GaYaGeum (18-string) - DEMO_simple.exs"),
    ("Strings", "GaYaGeum 18-string (modal)", "18-string_geum", "GaYaGeum (18-string) - DEMO_modal.exs"),
    ("Strings", "GaYaGeum 25-string", "25-string_geum", "GaYaGeum (25-string) - DEMO_simple.exs"),
    ("Strings", "GaYaGeum 25-string (modal)", "25-string_geum", "GaYaGeum (25-string) - DEMO_modal.exs"),
    ("Strings", "GaYaGeum JeongAk", "jeongakgayageum", "GaYaGeum (JeongAk) - DEMO_simple.exs"),
    ("Strings", "GaYaGeum JeongAk (modal)", "jeongakgayageum", "GaYaGeum (JeongAk) - DEMO_modal.exs"),
    ("Strings", "GaYaGeum SanJo", "sanjogayageum", "GaYaGeum (SanJo) - DEMO_simple.exs"),
    ("Strings", "GaYaGeum SanJo (modal)", "sanjogayageum", "GaYaGeum (SanJo) - DEMO_modal.exs"),
    ("Strings", "GeoMunGo (key switch A0/A#0/B0)", "geomungo", "GeoMunGo - DEMO_simple.exs"),
    ("Strings", "GeoMunGo JeongAk (modal)", "geomungo", "GeoMunGo (JeongAk) - DEMO_modal.exs"),
    ("Strings", "GeoMunGo SanJo (modal)", "geomungo", "GeoMunGo (SanJo) - DEMO_modal.exs"),
    ("Strings", "YangGeum", "yanggeum", "YangGeum - DEMO.exs"),
    ("Bowed", "HaeGeum", "haegeum", "HaeGeum - DEMO_simple.exs"),
    ("Bowed", "HaeGeum (modal)", "haegeum", "HaeGeum - DEMO_modal.exs"),
    ("Bowed", "AJaeng forsythia bow", "daeajaeng (forsythia bow)", "AJaeng [forsythia bow] - DEMO_simple.exs"),
    ("Bowed", "AJaeng forsythia bow (modal)", "daeajaeng (forsythia bow)", "AJaeng [forsythia bow] - DEMO_modal.exs"),
    ("Bowed", "AJaeng horse hair bow", "daeajaeng (horse tail hair bow)", "AJaeng [horse tail hair] - DEMO_simple.exs"),
    ("Bowed", "AJaeng horse hair bow (modal)", "daeajaeng (horse tail hair bow)", "AJaeng [horse tail hair] - DEMO_modal.exs"),
    ("Bowed", "AJaeng SanJo", "soajaeng", "AJaeng (SanJo) - DEMO_simple.exs"),
    ("Bowed", "AJaeng SanJo (modal)", "soajaeng", "AJaeng (SanJo) - DEMO_modal.exs"),
    ("Winds", "DaeGeum Unified", "daegeum (unified)", "DaeGeum (Unified) - DEMO_simple.exs"),
    ("Winds", "DaeGeum Unified (modal)", "daegeum (unified)", "DaeGeum (Unified) - DEMO_modal.exs"),
    ("Winds", "DaeGeum JeongAk", "jeongakdaegeum", "DaeGeum (JeongAk) - DEMO_simple.exs"),
    ("Winds", "DaeGeum JeongAk (modal)", "jeongakdaegeum", "DaeGeum (JeongAk) - DEMO_modal.exs"),
    ("Winds", "DaeGeum SanJo", "sanjodaegeum", "DaeGeum (SanJo) - DEMO_simple.exs"),
    ("Winds", "DaeGeum SanJo (modal)", "sanjodaegeum", "DaeGeum (SanJo) - DEMO_modal.exs"),
    ("Winds", "SoGeum", "sogeum", "SoGeum - DEMO_simple.exs"),
    ("Winds", "SoGeum (modal)", "sogeum", "SoGeum - DEMO_modal.exs"),
    ("Winds", "DanSo", "danso", "DanSo - DEMO_simple.exs"),
    ("Winds", "DanSo (modal)", "danso", "DanSo - DEMO_modal.exs"),
    ("Winds", "PiRi Hyang", "hyangpiri", "PiRi (Hyang) - DEMO_simple.exs"),
    ("Winds", "PiRi Hyang (modal)", "hyangpiri", "PiRi (Hyang) - DEMO_modal.exs"),
    ("Winds", "PiRi Se", "sepiri", "PiRi (Se) - DEMO_simple.exs"),
    ("Winds", "PiRi Se (modal)", "sepiri", "PiRi (Se) - DEMO_modal.exs"),
    ("Winds", "PiRi Dang", "dangpiri", "PiRi (Dang) - DEMO.exs"),
    ("Winds", "TaePyeongSo", "taepyeongso", "TaePyeongSo - DEMO_simple.exs"),
    ("Winds", "TaePyeongSo (modal)", "taepyeongso", "TaePyeongSo - DEMO_modal.exs"),
    ("Winds", "Hun", "hun", "Hun - DEMO.exs"),
    ("Winds", "Hun (legacy map)", "hun_legacy", "Hun-DEMO_simple.exs"),
    ("Percussion", "JangGu", "janggu", "JangGu - DEMO.exs"),
    ("Percussion", "JangGu (legacy map)", "janggu_legacy", "JangGu-DEMO.exs"),
    ("Percussion", "PyeonJong", "pyeonjong", "PyeonJong - DEMO.exs"),
    ("Percussion", "PyeonGyeong", "pyeongyeong", "PyeonGyeong - DEMO.exs"),
]
DEFAULT = 0
EXTRAS = "Extras (unmapped samples, optional)"


def available():
    """The INSTRUMENTS whose library has been extracted and staged."""
    return [i for i in INSTRUMENTS if os.path.exists(os.path.join(STAGE, i[2], i[3]))]


def pst_settings():
    """exs file name -> summarize() dict, preferring the newest library version."""
    found = {}
    for p in glob.glob(os.path.join(WORK, "extract", "**", "*.pst"), recursive=True):
        exs, prm = parse_pst(p)
        rank = 2 if "v.1.3.1" in p else 1 if "v.1.3" in p else 0
        if exs not in found or rank > found[exs][0]:
            found[exs] = (rank, summarize(prm), p)
    return {k: v[1] for k, v in found.items()}


def sample_index():
    """inode of a work/extract file -> FLAC manifest entry."""
    man = json.load(open(os.path.join(FLAC, "manifest.json")))
    by_inode = {}
    for path, pcm in man["files"].items():
        full = os.path.join(WORK, "extract", path)
        if os.path.exists(full):
            by_inode[os.stat(full).st_ino] = man["samples"][pcm]
    return by_inode


def a(**kw):
    return " ".join(f"{k}={quoteattr(str(v))}" for k, v in kw.items())


def fmt(x):
    return f"{x:.4f}".rstrip("0").rstrip(".")


def build(out_dir):
    insts = available()
    missing = [i[1] for i in INSTRUMENTS if i not in insts]
    if not insts:
        sys.exit("no instruments found in work/stage; run scripts/stage.py first")
    psts = pst_settings()
    by_inode = sample_index()
    bundle = os.path.join(out_dir, "Gugak.dsbundle")
    for old in (bundle, os.path.join(out_dir, EXTRAS)):
        if os.path.exists(old):
            shutil.rmtree(old)
    os.makedirs(os.path.join(bundle, "Samples"))

    groups = []      # dicts: inst, name, attrs, samples(list of attr strings)
    inst_groups = []  # instrument index -> list of group indices
    ks = None         # (group indices for notes 21, 22, 23)
    used = {}
    report = []
    for ii, (cat, label, lib, exs) in enumerate(insts):
        p = parse(os.path.join(STAGE, lib, exs))
        st = psts[exs]
        egroups = p["groups"]
        zones_by_group = {}
        for z in p["zones"]:
            gi = z["group"] if 0 <= z["group"] < len(egroups) else -1
            zones_by_group.setdefault(gi, []).append(z)
        mine = []
        for gi in sorted(zones_by_group):
            eg = egroups[gi] if gi >= 0 else None
            attrs = dict(name=f"{label} / {eg['name'] if eg else 'main'}", ampVelTrack=fmt(st["vel_depth"]))
            if eg and eg["vol"]:
                attrs["volume"] = f"{eg['vol']}dB"
            if eg and eg["pan"]:
                attrs["pan"] = eg["pan"]
            if eg and eg["exclusive"]:
                tag = f"x{ii}_{eg['exclusive']}"
                attrs.update(tags=tag, silencedByTags=tag, silencingMode="fast")
            samples = []
            for z in zones_by_group[gi]:
                src = os.path.join(STAGE, lib, p["samples"][z["sample"]])
                ent = by_inode[os.stat(src).st_ino]
                used[ent["path"]] = ent
                s = dict(path="Samples/" + ent["path"], rootNote=z["root"], loNote=z["lo"], hiNote=z["hi"],
                         loVel=z["vlo"] if z["vel_range_on"] else 0, hiVel=z["vhi"] if z["vel_range_on"] else 127)
                tune = z["coarse"] + z["fine"] / 100.0
                if tune:
                    s["tuning"] = fmt(tune)
                if z["vol"]:
                    s["volume"] = f"{z['vol']}dB"
                if z["pan"]:
                    s["pan"] = z["pan"]
                if z["start"]:
                    s["start"] = z["start"]
                if z["end"] and z["end"] < ent["frames"] - 1:
                    s["end"] = z["end"]
                if not z["pitch"]:
                    s["pitchKeyTrack"] = 0
                if z["oneshot"]:
                    s["ampEnvEnabled"] = "false"
                assert not z["reverse"] and not z["loop_on"], (exs, z)
                samples.append(s)
            mine.append(len(groups))
            groups.append(dict(attrs=attrs, samples=samples, ks=eg["enable_by_note_value"] if eg and eg["enable_by_type"] == 1 else None))
        inst_groups.append(mine)
        if any(groups[g]["ks"] is not None for g in mine):
            assert ks is None
            ks = (ii, {groups[g]["ks"]: g for g in mine})
        report.append(dict(index=ii + 1, name=label, exs=exs, zones=len(p["zones"]), groups=len(mine),
                           release_s=round(st["release_s"], 3), attack_s=round(st["attack_s"], 3),
                           one_shot=sum(z["oneshot"] for z in p["zones"]), bend=(st["bend_up"], st["bend_down"]),
                           master_db=st["master_db"]))

    ks_inst, ks_map = ks if ks else (None, {})
    ks_notes = sorted(ks_map)
    ks_default = ks_map[ks_notes[0]] if ks_notes else None

    def enabled_for(ii):
        on = set(inst_groups[ii])
        if ii == ks_inst:
            on = {ks_default}
        return on

    def env(ii):
        st = psts[insts[ii][3]]
        return st["attack_s"], st["release_s"]

    # ---- XML ----
    L = []
    w = L.append
    att0, rel0 = env(DEFAULT)
    w('<?xml version="1.0" encoding="UTF-8"?>')
    w('<DecentSampler minVersion="1.11.0" title="GUgAK">')
    w('  <ui width="812" height="375" bgColor="FF1B1712">')
    w('    <tab name="main">')
    # control order matters: _index 0 = menu, 1 = attack, 2 = release, 3 volume, 4 reverb, 5 room
    w(f'      <menu {a(x=40, y=80, width=430, height=34, value=DEFAULT + 1)}>')
    for ii, (cat, label, lib, exs) in enumerate(insts):
        att, rel = env(ii)
        on = enabled_for(ii)
        w(f'        <option {a(name=f"{cat}: {label}")}>')
        w(f'          <binding {a(type="control", level="ui", position=1, parameter="VALUE", translation="fixed_value", translationValue=fmt(att))}/>')
        w(f'          <binding {a(type="control", level="ui", position=2, parameter="VALUE", translation="fixed_value", translationValue=fmt(rel))}/>')
        for g in range(len(groups)):
            w(f'          <binding {a(type="general", level="group", position=g, parameter="ENABLED", translation="fixed_value", translationValue="true" if g in on else "false")}/>')
        for k in range(len(ks_notes)):
            w(f'          <binding {a(type="note", level="midi", midiElementIndex=k, parameter="ENABLED", translation="fixed_value", translationValue="true" if ii == ks_inst else "false")}/>')
        w('        </option>')
    w('      </menu>')
    knobs = [
        ("Attack", 520, 0, 3, att0, '<binding type="amp" level="instrument" position="0" parameter="ENV_ATTACK"/>'),
        ("Release", 610, 0, 5, rel0, '<binding type="amp" level="instrument" position="0" parameter="ENV_RELEASE"/>'),
        ("Volume", 700, 0, 2, 1, '<binding type="amp" level="instrument" position="0" parameter="AMP_VOLUME" translation="linear" translationOutputMin="0" translationOutputMax="2"/>'),
        ("Reverb", 520, 0, 1, 0, '<binding type="effect" level="instrument" position="0" parameter="FX_REVERB_WET_LEVEL" translation="linear" translationOutputMin="0" translationOutputMax="1"/>'),
        ("Room", 610, 0, 1, 0.7, '<binding type="effect" level="instrument" position="0" parameter="FX_REVERB_ROOM_SIZE" translation="linear" translationOutputMin="0" translationOutputMax="1"/>'),
    ]
    for i, (lab, x, lo, hi, val, b) in enumerate(knobs):
        y = 60 if i < 3 else 190
        w(f'      <labeled-knob {a(x=x, y=y, width=80, height=100, label=lab, type="float", minValue=lo, maxValue=hi, value=fmt(val), textColor="FFE8DCC8", trackForegroundColor="FFD2A04B", trackBackgroundColor="FF3A3128", textSize=14)}>')
        w(f'        {b}')
        w('      </labeled-knob>')
    w(f'      <label {a(x=40, y=24, width=430, height=40, text="GUgAK  국악", textColor="FFE8DCC8", textSize=30, hAlign="left")}/>')
    w(f'      <label {a(x=40, y=124, width=430, height=24, text="Instrument (also MIDI CC 102: value 0 = first entry)", textColor="FF9C8F7C", textSize=13, hAlign="left")}/>')
    if ks:
        w(f'      <label {a(x=40, y=150, width=430, height=24, text="GeoMunGo key switches: A0 = yu, A#0 = dae, B0 = open strings", textColor="FF9C8F7C", textSize=13, hAlign="left")}/>')
    w(f'      <label {a(x=40, y=310, width=740, height=24, text="Samples: catsnu GUgAK DEMO libraries (EXS24), converted losslessly to FLAC", textColor="FF6F6455", textSize=12, hAlign="left")}/>')
    w('    </tab>')
    w('  </ui>')
    w(f'  <groups {a(attack=fmt(att0), decay=0, sustain=1, release=fmt(rel0), globalVolume="1", pitchBendRange=BEND_RANGE, playbackMode="disk_streaming")}>')
    on0 = enabled_for(DEFAULT)
    for g, grp in enumerate(groups):
        ga = dict(grp["attrs"], enabled="true" if g in on0 else "false")
        w(f'    <group {a(**ga)}>')
        for s in grp["samples"]:
            w(f'      <sample {a(**s)}/>')
        w('    </group>')
    w('  </groups>')
    w('  <effects>')
    w('    <effect type="reverb" roomSize="0.7" damping="0.4" wetLevel="0"/>')
    w('  </effects>')
    w('  <midi>')
    for k, note in enumerate(ks_notes):
        w(f'    <note {a(note=note, enabled="true" if DEFAULT == ks_inst else "false")}>')
        for g in inst_groups[ks_inst]:
            w(f'      <binding {a(type="general", level="group", position=g, parameter="ENABLED", translation="fixed_value", translationValue="true" if g == ks_map[note] else "false")}/>')
        w('    </note>')
    w(f'    <cc number="{SELECT_CC}">')
    w(f'      <binding {a(type="control", level="ui", position=0, parameter="VALUE", translation="linear", translationOutputMin=1, translationOutputMax=128)}/>')
    w('    </cc>')
    w('  </midi>')
    w('</DecentSampler>')
    open(os.path.join(bundle, "Gugak.dspreset"), "w").write("\n".join(L) + "\n")

    for rel, ent in used.items():
        dst = os.path.join(bundle, "Samples", rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(FLAC, rel), dst)

    # recorded samples that no original instrument maps, kept outside the instrument
    man = json.load(open(os.path.join(FLAC, "manifest.json")))
    extras = [e for e in man["samples"].values() if e["path"] not in used]
    for e in extras:
        dst = os.path.join(out_dir, EXTRAS, e["path"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(FLAC, e["path"]), dst)
    doc = os.path.join(ROOT, "docs", "INSTRUMENT_README.md")
    if os.path.exists(doc):
        shutil.copy2(doc, os.path.join(out_dir, "README.md"))

    meta = dict(instruments=report, missing=missing,
                groups=[dict(index=g, name=x["attrs"]["name"]) for g, x in enumerate(groups)],
                inst_groups=inst_groups,
                ks=dict(instrument=ks_inst + 1, notes={str(n): g for n, g in ks_map.items()}) if ks else None,
                select_cc=SELECT_CC, samples=len(used), sample_bytes=sum(e["bytes"] for e in used.values()),
                extras=len(extras), extras_bytes=sum(e["bytes"] for e in extras))
    json.dump(meta, open(os.path.join(out_dir, "build_info.json"), "w"), indent=1)
    print(f"   {len(insts)} instruments, {len(groups)} groups, {len(used)} samples "
          f"({meta['sample_bytes'] / 1e6:.1f} MB) -> {bundle}")
    print(f"   {len(extras)} unmapped samples ({meta['extras_bytes'] / 1e6:.1f} MB) -> {os.path.join(out_dir, EXTRAS)}")
    if missing:
        print(f"   WARNING: {len(missing)} instruments skipped because their library zip is missing: "
              + ", ".join(missing))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist"))
