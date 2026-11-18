"""Usage: infer.py weights.pt out_dir image...   -> <name>_ml4x.png, <name>_ml8x.png, <name>_xbrz4x.png"""
import os, subprocess, sys
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from model import GlyphSDF

HERE = os.path.dirname(os.path.abspath(__file__))
XBRZ = os.environ.get("XBRZ", os.path.join(HERE, "..", "xbrz", "xbrz_raw"))

torch.set_num_threads(int(os.environ.get("THREADS", "4")))
sd = torch.load(sys.argv[1]); net = GlyphSDF(sd["e1.0.weight"].shape[0]); net.load_state_dict(sd); net.eval()
outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)


def save_bits(ink, path):
    Image.fromarray(np.where(ink, 0, 255).astype(np.uint8), "L").convert("1").save(path)


def xbrz(ink, k=4):
    h, w = ink.shape
    raw_in, raw_out = path_tmp + ".in", path_tmp + ".out"
    np.where(ink, 0, 0xFFFFFF).astype("<u4").tofile(raw_in)
    subprocess.run([XBRZ, str(k), str(w), str(h), raw_in, raw_out], check=True)
    o = np.fromfile(raw_out, "<u4").reshape(h * k, w * k) & 0xFF
    os.remove(raw_in); os.remove(raw_out)
    return o < 128


for p in sys.argv[3:]:
    name = os.path.splitext(os.path.basename(p))[0]
    path_tmp = os.path.join(outdir, name)
    ink = np.array(Image.open(p).convert("L")) < 128
    with torch.no_grad():
        sdf = net(torch.from_numpy(ink.astype(np.float32))[None, None])
        sig = float(os.environ.get("SMOOTH", "1.0"))   # gaussian blur of the 4x SDF, in 4x pixels
        if sig > 0:
            r = int(3 * sig); t = torch.arange(-r, r + 1, dtype=torch.float32)
            g = torch.exp(-t * t / (2 * sig * sig)); g = g / g.sum()
            sdf = F.pad(sdf, (r, r, r, r), mode="replicate")
            sdf = F.conv2d(F.conv2d(sdf, g.view(1, 1, 1, -1)), g.view(1, 1, -1, 1))
        sdf8 = F.interpolate(sdf, scale_factor=2, mode="bicubic", align_corners=False)
    save_bits(sdf[0, 0].numpy() > 0, f"{outdir}/{name}_ml4x.png")
    save_bits(sdf8[0, 0].numpy() > 0, f"{outdir}/{name}_ml8x.png")
    save_bits(np.kron(ink, np.ones((4, 4), bool)), f"{outdir}/{name}_nearest4x.png")
    save_bits(xbrz(ink), f"{outdir}/{name}_xbrz4x.png")
    print("done", name, ink.shape, flush=True)
