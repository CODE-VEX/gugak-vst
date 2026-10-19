"""Write copies of the staged .exs files with every sample path pointed at the stage folder,
so Apple's AUSampler can load them as an independent reference renderer."""
import glob, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from exsread import read_blocks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def patch(src, dst):
    raw = bytearray(open(src, "rb").read())
    folder = os.path.dirname(os.path.abspath(src)).encode()
    assert len(folder) < 256
    pos = 0
    while pos < len(raw):
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        if raw[pos + 3] & 0x0F == 3:
            d = pos + 84
            raw[d + 80:d + 336] = folder.ljust(256, b"\0")
            full = bytes(raw[d + 336:d + 592]).split(b"\0")[0]
            if not os.path.exists(os.path.join(folder, full)):
                # blocks no zone uses (old names in the legacy JangGu map); AUSampler insists on loading them
                full = sorted(f for f in os.listdir(folder) if f.endswith(b".wav"))[0]
                raw[d + 336:d + 592] = full.ljust(256, b"\0")
            assert len(full) < 64
            raw[pos + 20:pos + 84] = full.ljust(64, b"\0")
        pos += 84 + size
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(raw)

for f in glob.glob(os.path.join(ROOT, "work/stage/*/*.exs")):
    lib = os.path.basename(os.path.dirname(f))
    patch(f, os.path.join(ROOT, "work/exs_ref", lib, os.path.basename(f)))
print("ok")
