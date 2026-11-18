"""1-bit pixel-art upscalers: Scale2x (EPX) and MMPX. Pixels are 0 (black) / 1 (white)."""
import sys
import numpy as np
from PIL import Image


def load(path):
    a = np.array(Image.open(path).convert("L")) >= 128
    return a.astype(np.uint8)


def save(a, path):
    Image.fromarray((a * 255).astype(np.uint8), "L").convert("1").save(path)


def nearest(a, k):
    return np.kron(a, np.ones((k, k), np.uint8))


def scale2x(a):
    p = np.pad(a, 1, mode="edge")
    B, D, E, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:], p[2:, 1:-1]
    ok = (B != H) & (D != F)
    e0 = np.where(ok & (D == B), D, E)
    e1 = np.where(ok & (B == F), F, E)
    e2 = np.where(ok & (D == H), D, E)
    e3 = np.where(ok & (H == F), F, E)
    h, w = a.shape
    out = np.empty((2 * h, 2 * w), np.uint8)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = e0, e1, e2, e3
    return out


def mmpx(a):
    """MMPX 2x (McGuire & Gagiu 2021). Luma = pixel value, so dark (0) strokes win ties."""
    h, w = a.shape

    def src(x, y):
        return int(a[min(max(y, 0), h - 1), min(max(x, 0), w - 1)])

    out = np.empty((2 * h, 2 * w), np.uint8)
    for y in range(h):
        for x in range(w):
            A, B, C = src(x - 1, y - 1), src(x, y - 1), src(x + 1, y - 1)
            D, E, F = src(x - 1, y), src(x, y), src(x + 1, y)
            G, H, I = src(x - 1, y + 1), src(x, y + 1), src(x + 1, y + 1)
            J = K = L = M = E
            if not (A == B == C == D == F == G == H == I == E):
                P, Q, R, S = src(x, y - 2), src(x - 2, y), src(x + 2, y), src(x, y + 2)
                Bl, Dl, El, Fl, Hl = B, D, E, F, H
                any3 = lambda v, a1, a2, a3: v in (a1, a2, a3)
                # 1:1 slopes
                if D == B and D != H and D != F and (El >= Dl or E == A) and any3(E, A, C, G) and (El < Dl or A != D or E != P or E != Q):
                    J = D
                if B == F and B != D and B != H and (El >= Bl or E == C) and any3(E, A, C, I) and (El < Bl or C != B or E != P or E != R):
                    K = B
                if H == D and H != F and H != B and (El >= Hl or E == G) and any3(E, A, G, I) and (El < Hl or G != H or E != S or E != Q):
                    L = H
                if F == H and F != B and F != D and (El >= Fl or E == I) and any3(E, C, G, I) and (El < Fl or I != H or E != R or E != S):
                    M = F
                # Intersections
                if E != F and E == C == I == D == Q and F == B == H and F != src(x + 3, y):
                    K = M = F
                if E != D and E == A == G == F == R and D == B == H and D != src(x - 3, y):
                    J = L = D
                if E != H and E == G == I == B == P and H == D == F and H != src(x, y + 3):
                    L = M = H
                if E != B and E == A == C == H == S and B == D == F and B != src(x, y - 3):
                    J = K = B
                # Triangle tips
                if Bl < El and E == G == H == I == S and E not in (A, D, C, F):
                    J = K = B
                if Hl < El and E == A == B == C == P and E not in (D, G, I, F):
                    L = M = H
                if Fl < El and E == A == D == G == Q and E not in (B, C, I, H):
                    K = M = F
                if Dl < El and E == C == F == I == R and E not in (B, A, G, H):
                    J = L = D
                # 2:1 slopes
                if H != B:
                    if H not in (A, E, C):
                        if H == G == F == R and H not in (D, src(x + 2, y - 1)):
                            L = M
                        if H == I == D == Q and H not in (F, src(x - 2, y - 1)):
                            M = L
                    if B not in (I, G, E):
                        if B == A == F == R and B not in (D, src(x + 2, y + 1)):
                            J = K
                        if B == C == D == Q and B not in (F, src(x - 2, y + 1)):
                            K = J
                if F != D:
                    if D not in (I, E, C):
                        if D == A == H == S and D not in (B, src(x + 1, y + 2)):
                            J = L
                        if D == G == B == P and D not in (H, src(x + 1, y - 2)):
                            L = J
                    if F not in (E, A, G):
                        if F == C == H == S and F not in (B, src(x - 1, y + 2)):
                            K = M
                        if F == I == B == P and F not in (H, src(x - 1, y - 2)):
                            M = K
            out[2 * y, 2 * x], out[2 * y, 2 * x + 1] = J, K
            out[2 * y + 1, 2 * x], out[2 * y + 1, 2 * x + 1] = L, M
    return out


if __name__ == "__main__":
    src_path, outdir = sys.argv[1], sys.argv[2]
    a = load(src_path)
    save(nearest(a, 4), f"{outdir}/nearest4.png")
    save(scale2x(scale2x(a)), f"{outdir}/scale4x.png")
    save(mmpx(mmpx(a)), f"{outdir}/mmpx4x.png")
    print("ok", a.shape, "black fraction", 1 - a.mean())
