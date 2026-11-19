"""Minimal Mac resource-fork parser (works on .dfont, raw .rsrc, and AppleDouble ._ files)."""
import struct

def appledouble_rsrc(data):
    """Return the resource fork bytes from an AppleDouble/AppleSingle file, or None."""
    if len(data) < 26 or data[:4] not in (b"\x00\x05\x16\x07", b"\x00\x05\x16\x00"):
        return None
    n = struct.unpack(">H", data[24:26])[0]
    for i in range(n):
        eid, off, ln = struct.unpack(">III", data[26 + 12 * i:38 + 12 * i])
        if eid == 2:
            return data[off:off + ln]
    return None

def resources(fork):
    """-> list of (type, id, name, bytes)."""
    if len(fork) < 16:
        return []
    doff, moff, dlen, mlen = struct.unpack(">IIII", fork[:16])
    m = fork[moff:moff + mlen]
    tl_off, nl_off = struct.unpack(">HH", m[24:28])
    ntypes = struct.unpack(">H", m[tl_off:tl_off + 2])[0] + 1
    out = []
    for t in range(ntypes):
        rtype, cnt, rl = struct.unpack(">4sHH", m[tl_off + 2 + 8 * t:tl_off + 10 + 8 * t])
        for r in range(cnt + 1):
            e = tl_off + rl + 12 * r
            rid, noff, attr_off = struct.unpack(">hHI", m[e:e + 8])
            dpos = doff + (attr_off & 0xFFFFFF)
            ln = struct.unpack(">I", fork[dpos:dpos + 4])[0]
            name = None
            if noff != 0xFFFF:
                p = nl_off + noff; name = m[p + 1:p + 1 + m[p]].decode("mac_roman")
            out.append((rtype.decode("mac_roman"), rid, name, fork[dpos + 4:dpos + 4 + ln]))
    return out
