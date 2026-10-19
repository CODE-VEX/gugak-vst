"""Per-library inventory of the selected source versions (from work/hashes.json)."""
import json, os
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "work")
rows = json.load(open(os.path.join(ROOT, "hashes.json")))

# Source selection: latest release, plus older builds holding audio/presets absent from it.
EXTRA = {("hun", "EXS24 Hun-DEMO"), ("janggu", "EXS24 JangGu-DEMO")}

def selected(r):
    return not r["in_template"] and ("v.1.3.1" in r["ver"] or (r["lib"], r["ver"]) in EXTRA)

sel = [r for r in rows if selected(r)]
by_lib = defaultdict(list)
for r in sel:
    by_lib[r["lib"]].append(r)

print(f"{'library':34} {'n':>4} {'MB':>8}  formats")
tot_n = tot_b = 0
for lib in sorted(by_lib):
    rs = by_lib[lib]
    uniq = {r["pcm"]: r for r in rs}.values()
    b = sum(r["bytes"] for r in uniq)
    fmts = Counter(f"{r['sr']}/{r['subtype']}/{'st' if r['ch'] == 2 else 'mono'}" for r in uniq)
    print(f"{lib:34} {len(uniq):4} {b/1e6:8.1f}  {dict(fmts)}")
    tot_n += len(uniq); tot_b += b
print(f"{'TOTAL (per-library unique)':34} {tot_n:4} {tot_b/1e6:8.1f}")

g = {}
for r in sel:
    g.setdefault(r["pcm"], r)
print(f"globally unique PCM: {len(g)}  {sum(r['bytes'] for r in g.values())/1e6:.1f} MB")

pairs = Counter()
libs_by_pcm = defaultdict(set)
for r in sel:
    libs_by_pcm[r["pcm"]].add(r["lib"])
for h, l in libs_by_pcm.items():
    if len(l) > 1:
        pairs[tuple(sorted(l))] += 1
print("shared sample groups:", dict(pairs))

all_rows = [r for r in rows]
print(f"\nall extracted audio (every version + templates): {len(all_rows)} files, "
      f"{sum(r['bytes'] for r in all_rows)/1e6:.1f} MB")
