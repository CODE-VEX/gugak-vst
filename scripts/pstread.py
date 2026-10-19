"""Reader for Logic EXS24 plug-in settings (.pst), reverse engineered from the GUgAK files.

Layout (little-endian): u32 1000 (file size), u16 2, u16 1, u32 0x58 (offset of the
parameter list), 'MELCPMAS1MAS', 64-byte .exs instrument name at 0x18, then from 0x58
pairs of (i32 parameter id, i32 value) until an all-zero pair. Parameter ids are the same
as in the .exs PARAMS block (see exsread.PARAM_NAMES).
"""
import struct, sys
from exsread import PARAM_NAMES


def env_seconds(v):
    return 10.0 * (v / 127.0) ** 4


def parse_pst(path):
    d = open(path, "rb").read()
    assert d[12:24] == b"MELCPMAS1MAS", path
    exs = d[0x18:0x58].split(b"\0")[0].decode("latin-1")
    start = struct.unpack_from("<I", d, 8)[0]
    params = {}
    for off in range(start, len(d) - 7, 8):
        pid, val = struct.unpack_from("<ii", d, off)
        if pid == 0 and val == 0:
            break
        params[pid] = val
    return exs, params


def summarize(params):
    g = lambda k, dflt=None: params.get(k, dflt)
    return dict(
        master_db=g(0x07, 0), polyphony=g(0x05), vel_depth=max(0.0, min(1.0, g(0x5a, -60) / -60.0)),
        attack_s=env_seconds(g(0x52, 0)), attack_lovel_s=env_seconds(g(0x53, 0)),
        hold_s=env_seconds(g(0x58, 0)), decay_s=env_seconds(g(0x54, 0)),
        sustain=g(0x51, 127) / 127.0, release_s=env_seconds(g(0x55, 0)),
        filter_on=bool(g(0x2c, 0)), transpose=g(0x2d, 0), coarse=g(0x0e, 0), fine=g(0x0f, 0),
        glide=g(0x14, 0), mono_legato=g(0x0a, 0), bend_up=g(0x03), bend_down=g(0x04),
        random_vel=g(0xa4, 0), random_sample=g(0xa3, 0), random_pitch=g(0x62, 0),
        raw_release=g(0x55), raw_attack=g(0x52),
    )


if __name__ == "__main__":
    for p in sys.argv[1:]:
        exs, prm = parse_pst(p)
        print(exs, summarize(prm))
