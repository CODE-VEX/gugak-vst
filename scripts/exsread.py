"""Minimal EXS24 (.exs) reader; build_ds.py builds the DecentSampler mapping from its output.
See docs/FORMATS.md.

Block layout: 4B sig (endianness, version, version, type|flags), u32 size, u32 index,
u32 flags, 4B magic ('TBOS' little-endian / 'SOBT' big-endian), 64B name, size bytes data.
"""
import json, struct, sys

TYPES = {0: "instrument", 1: "zone", 2: "group", 3: "sample", 4: "params"}
PARAM_NAMES = {
    0x07: "master_volume", 0x05: "polyphony", 0x0e: "coarse_tune", 0x0f: "fine_tune",
    0x2d: "transpose", 0x03: "bend_up", 0x04: "bend_down", 0x0a: "mono_legato",
    0x2c: "filter_on", 0x1e: "cutoff", 0x1d: "reso", 0x2e: "filter_keytrack",
    0x52: "env1_attack_hi", 0x53: "env1_attack_lo", 0x58: "env1_hold", 0x54: "env1_decay",
    0x51: "env1_sustain", 0x55: "env1_release", 0x5a: "env1_vel_sens",
    0x5f: "velocity_offset", 0x61: "xfade_amount", 0x14: "glide", 0x08: "volume_keyscale",
    0x160: "master_pan",
}


def s8(b):
    return b - 256 if b > 127 else b


def read_blocks(path):
    raw = open(path, "rb").read()
    pos, out = 0, []
    while pos + 84 <= len(raw):
        big = raw[pos] == 0
        e = ">" if big else "<"
        typ = raw[pos + 3] & 0x0F
        size, index = struct.unpack_from(e + "II", raw, pos + 4)
        if raw[pos + 3] & 0x80:
            size &= 0x7FFF
        magic = raw[pos + 16:pos + 20]
        assert magic in (b"TBOS", b"SOBT", b"JBOS", b"OBSJ"), (path, pos, magic)
        name = raw[pos + 20:pos + 84].split(b"\0")[0].decode("latin-1")
        data = raw[pos + 84:pos + 84 + size]
        out.append((typ, index, name, data, e))
        pos += 84 + size
    return out


def parse(path):
    inst = {"zones": [], "groups": [], "samples": [], "params": {}, "other_blocks": {}}
    for typ, index, name, d, e in read_blocks(path):
        if typ == 1:
            opts = d[0]
            z = dict(
                name=name, oneshot=bool(opts & 1), pitch=not (opts & 2), reverse=bool(opts & 4),
                vel_range_on=bool(opts & 8), root=d[1], fine=s8(d[2]), pan=s8(d[3]),
                vol=s8(d[4]), vol_scale=d[5], lo=d[6], hi=d[7], vlo=d[9], vhi=d[10],
            )
            z["start"], z["end"], z["loop_start"], z["loop_end"], z["loop_xfade"] = \
                struct.unpack_from(e + "IIIII", d, 12)
            z["loop_on"] = bool(d[33] & 1)
            z["coarse"] = s8(d[80]) if len(d) > 80 else 0
            if len(d) >= 96:
                z["group"], z["sample"] = struct.unpack_from(e + "iI", d, 88)
            inst["zones"].append(z)
        elif typ == 2:
            g = dict(name=name, vol=s8(d[0]), pan=s8(d[1]), poly=d[2], options=d[3],
                     exclusive=d[4], vlo=d[5], vhi=d[6])
            g["release_trigger"] = bool(d[73]) if len(d) > 73 else False
            g["mute"] = bool(d[3] & 16)
            if len(d) > 84:
                g["enable_by_note_value"] = d[75]
                g["enable_by_type"] = d[84]  # 0 none, 1 note (key switch), 2 round robin, 3 CC ...
                g["rr_pos"] = struct.unpack_from(e + "i", d, 80)[0]
            inst["groups"].append(g)
        elif typ == 3:
            # 24 bytes of format info, 4 pad, 'type', size, compressed flag, 40 pad, 256B path, 256B file name
            full = d[80 + 256:80 + 512].split(b"\0")[0].decode("latin-1") if len(d) >= 80 + 512 else ""
            inst["samples"].append(full or name)
        elif typ == 4:
            n = struct.unpack_from(e + "I", d, 0)[0]
            ids = d[4:4 + n]
            for i, pid in enumerate(ids):
                if pid:
                    v = struct.unpack_from(e + "h", d, 4 + n + 2 * i)[0]
                    inst["params"][PARAM_NAMES.get(pid, hex(pid))] = v
            rest = 4 + 3 * n
            if len(d) >= rest + 4:
                m = struct.unpack_from(e + "I", d, rest)[0]
                for i in range(m):
                    off = rest + 4 + 4 * i
                    if off + 4 > len(d):
                        break
                    pid, v = struct.unpack_from(e + "Hh", d, off)
                    if pid:
                        inst["params"][PARAM_NAMES.get(pid, hex(pid))] = v
        elif typ != 0:
            inst["other_blocks"][TYPES.get(typ, str(typ))] = inst["other_blocks"].get(TYPES.get(typ, str(typ)), 0) + 1
    return inst


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(json.dumps({p: parse(p)}, indent=1))
