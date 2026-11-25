"""Minimal TrueType table reader (no fontTools): unitsPerEm, hhea ascent/descent, and the Unicode cmap."""
import struct


def tables(d):
    n = struct.unpack(">H", d[4:6])[0]
    return {d[12 + 16 * i:16 + 16 * i].decode("latin-1"): struct.unpack(">II", d[20 + 16 * i:28 + 16 * i]) for i in range(n)}


def info(path):
    d = open(path, "rb").read(); T = tables(d)
    ho = T["head"][0]; upm = struct.unpack(">H", d[ho + 18:ho + 20])[0]
    hh = T["hhea"][0]; asc, desc = struct.unpack(">hh", d[hh + 4:hh + 8])
    co = T["cmap"][0]; n = struct.unpack(">H", d[co + 2:co + 4])[0]; subs = {}
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", d[co + 4 + 8 * i:co + 12 + 8 * i]); subs[(pid, eid)] = co + off
    codes = set()
    for key in ((3, 10), (0, 4), (3, 1), (0, 3), (0, 1), (0, 0), (3, 0), (1, 0)):
        if key not in subs:
            continue
        o = subs[key]; fmt = struct.unpack(">H", d[o:o + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", d[o + 6:o + 8])[0]; s = segx2 // 2
            ends = struct.unpack(f">{s}H", d[o + 14:o + 14 + segx2])
            starts = struct.unpack(f">{s}H", d[o + 16 + segx2:o + 16 + 2 * segx2])
            for a, b in zip(starts, ends):
                if a != 0xFFFF:
                    codes |= set(range(a, b + 1))
        elif fmt == 12:
            ng = struct.unpack(">I", d[o + 12:o + 16])[0]
            for g in range(ng):
                a, b, _ = struct.unpack(">III", d[o + 16 + 12 * g:o + 28 + 12 * g]); codes |= set(range(a, b + 1))
        elif fmt == 0:
            codes |= set(range(256))
        elif fmt == 6:
            first, cnt = struct.unpack(">HH", d[o + 6:o + 10]); codes |= set(range(first, first + cnt))
        if codes:
            sym = key == (3, 0)
            break
    return dict(upm=upm, ascent=asc, descent=-desc, codes=sorted(codes), symbol=sym if codes else False)
