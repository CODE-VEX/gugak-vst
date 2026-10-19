"""Render a .dspreset through the real DecentSampler AU via tools/dshost.

render(preset_path, notes, out_wav, menu_value=None, extra_attrs=None)
notes: list of (on_sec, dur_sec, midi_note, velocity)
"""
import os, re, subprocess, tempfile

HOST = os.path.join(os.path.dirname(__file__), "..", "tools", "dshost", "dshost")


def state_xml(preset_path, menu_value=None, playback_mode=None):
    xml = open(preset_path, encoding="utf-8").read()
    xml = re.sub(r"^<\?xml[^>]*\?>\s*", "", xml)
    base = os.path.dirname(os.path.abspath(preset_path)) + "/"
    attrs = f' _samplePath="{base}" _presetName="{os.path.basename(preset_path)}"'
    xml = re.sub(r"<DecentSampler\b", "<DecentSampler" + attrs, xml, count=1)
    if menu_value is not None:
        xml = re.sub(r'(<menu\b[^>]*?\bvalue=")\d+(")', rf"\g<1>{menu_value}\2", xml, count=1)
    if playback_mode:
        xml = re.sub(r'(<groups\b[^>]*?\bplaybackMode=")[a-z_]+(")', rf"\g<1>{playback_mode}\2", xml, count=1)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml


def render(preset_path, notes, out_wav, menu_value=None, settle=4.0, playback_mode=None):
    with tempfile.TemporaryDirectory() as td:
        st = os.path.join(td, "state.xml"); sc = os.path.join(td, "score.txt")
        open(st, "w").write(state_xml(preset_path, menu_value, playback_mode))
        open(sc, "w").write("\n".join(f"{a} {b} {n} {v}" for a, b, n, v in notes))
        # the plugin occasionally crashes the offline host; a second attempt has always worked
        for attempt in range(3):
            r = subprocess.run([HOST, "render", st, sc, out_wav, str(settle)], capture_output=True, text=True)
            if r.returncode == 0:
                break
        else:
            raise RuntimeError(f"dshost exit {r.returncode}: {r.stderr}{r.stdout}")
    return out_wav
