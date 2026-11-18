"""lisa_aspect.py weights in.png out_prefix [yscale]  -- model 4x with optional vertical stretch for non-square pixels"""
import os, sys, numpy as np, torch, torch.nn.functional as F
from PIL import Image
from model import GlyphSDF
torch.set_num_threads(int(os.environ.get("THREADS", "1")))
sd = torch.load(sys.argv[1]); net = GlyphSDF(sd["e1.0.weight"].shape[0]); net.load_state_dict(sd); net.eval()
ys = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
ink = np.array(Image.open(sys.argv[2]).convert("L")) < 128
def save(b, p): Image.fromarray(np.where(b, 0, 255).astype(np.uint8)).convert("1").save(p)
with torch.no_grad():
    sdf = net(torch.from_numpy(ink.astype(np.float32))[None, None])
    sig = 1.0; r = 3; t = torch.arange(-r, r + 1, dtype=torch.float32); g = torch.exp(-t * t / 2); g /= g.sum()
    sdf = F.conv2d(F.conv2d(F.pad(sdf, (r, r, r, r), mode="replicate"), g.view(1, 1, 1, -1)), g.view(1, 1, -1, 1))
    h, w = sdf.shape[-2:]
    tall = F.interpolate(sdf, size=(int(round(h * ys)), w), mode="bicubic", align_corners=False)
save(sdf[0, 0].numpy() > 0, sys.argv[3] + "_ml4x.png")
save(tall[0, 0].numpy() > 0, sys.argv[3] + "_ml4x_aspect.png")
# comparisons with the same stretch: nearest-neighbour rows, and xBRZ stretched by nearest
save(np.kron(ink, np.ones((4, 4), bool)), sys.argv[3] + "_nearest4x.png")
idx = np.minimum((np.arange(int(round(h * ys))) / ys).astype(int), h - 1)
save(np.kron(ink, np.ones((4, 4), bool))[idx], sys.argv[3] + "_nearest4x_aspect.png")
x4 = np.array(Image.open(sys.argv[3] + "_xbrz4x.png").convert("L")) < 128 if os.path.exists(sys.argv[3] + "_xbrz4x.png") else None
if x4 is not None: save(x4[idx], sys.argv[3] + "_xbrz4x_aspect.png")
print("ok", ink.shape)
