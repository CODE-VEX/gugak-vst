"""List which of the expected library zips are in libraries/. Exits 1 if none are."""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from build_ds import INSTRUMENTS, ROOT

LIBS = os.path.join(ROOT, "libraries")
expected = sorted({lib.removesuffix("_legacy") for _, _, lib, _ in INSTRUMENTS})
present = {f for f in os.listdir(LIBS) if f.endswith(".zip")} if os.path.isdir(LIBS) else set()

found = [l for l in expected if f"{l} exs24.zip" in present]
missing = [l for l in expected if f"{l} exs24.zip" not in present]
unknown = sorted(present - {f"{l} exs24.zip" for l in expected})

print(f"   found {len(found)} of {len(expected)} library zips in libraries/")
for l in missing:
    print(f"   missing: {l} exs24.zip")
for f in unknown:
    print(f"   not recognised (ignored): {f}")
if not found:
    sys.exit("   No library zips found. See libraries/README.md.")
