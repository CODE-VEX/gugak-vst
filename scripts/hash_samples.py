"""Hash every sample (file bytes and decoded PCM) under work/extract and report
which audio exists only in older versions, plus cross-library duplicates."""
import hashlib, json, os, sys
from collections import defaultdict
import soundfile as sf

ROOT = os.path.join(os.path.dirname(__file__), "..", "work", "extract")
LIBRARIES = os.path.join(os.path.dirname(__file__), "..", "libraries")
present = {lib for lib in os.listdir(ROOT) if os.path.exists(os.path.join(LIBRARIES, f"{lib} exs24.zip"))}
rows = []
for dp, dns, fns in os.walk(ROOT):
    if os.path.samefile(dp, ROOT):
        dns[:] = [d for d in dns if d in present]
    for fn in fns:
        if not fn.lower().endswith((".wav", ".aif", ".aiff")):
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, ROOT)
        lib, ver = rel.split(os.sep)[:2]
        data, sr = sf.read(p, dtype="int32", always_2d=True)
        info = sf.info(p)
        rows.append(dict(
            path=rel, lib=lib, ver=ver, name=fn, bytes=os.path.getsize(p),
            pcm=hashlib.sha1(data.tobytes()).hexdigest(), sr=sr,
            ch=info.channels, subtype=info.subtype, frames=info.frames,
            in_template=".logicx" in rel,
        ))
json.dump(rows, open(os.path.join(ROOT, "..", "hashes.json"), "w"), indent=0)

cur = {r["pcm"] for r in rows if "v.1.3.1" in r["ver"] and not r["in_template"]}
only_old = defaultdict(list)
for r in rows:
    if r["pcm"] not in cur:
        only_old[(r["lib"], r["ver"], r["in_template"])].append(r["name"])
print("Audio NOT present in any v1.3.1 sample folder:")
for k, v in sorted(only_old.items()):
    print(f"  {k[0]} | {k[1]} | template={k[2]} | {len(v)} files, e.g. {v[:3]}")

libs_by_pcm = defaultdict(set)
for r in rows:
    if "v.1.3.1" in r["ver"] and not r["in_template"]:
        libs_by_pcm[r["pcm"]].add(r["lib"])
shared = {h: l for h, l in libs_by_pcm.items() if len(l) > 1}
print(f"\nv1.3.1 PCM shared across libraries: {len(shared)}")
for h, l in list(shared.items())[:20]:
    print("  ", sorted(l))
