"""train2.py MINUTES [WIDTH] [INIT_WEIGHTS]  -- trains on train2.npz / val2.npz, writes glyphsdf2.pt"""
import sys, time
import numpy as np
import torch
from model import GlyphSDF

torch.set_num_threads(4)
torch.manual_seed(0)
minutes = float(sys.argv[1])
width = int(sys.argv[2]) if len(sys.argv) > 2 else 48
init = sys.argv[3] if len(sys.argv) > 3 else None

import os
TRAIN = os.environ.get("TRAIN", "train2.npz").split(","); VAL = os.environ.get("VAL", "val2.npz").split(",")
OUT = os.environ.get("OUT", "glyphsdf2")
ds = [np.load(f) for f in TRAIN]; vs = [np.load(f) for f in VAL]
X = torch.from_numpy(np.concatenate([d["x"] for d in ds]))            # uint8, kept compact
Y = torch.from_numpy(np.concatenate([d["y"] for d in ds]))            # int8, SDF * 80
Xv = torch.from_numpy(np.concatenate([v["x"] for v in vs])).float()[:, None]
Yv = torch.from_numpy(np.concatenate([v["y"] for v in vs])).float()[:, None] / 80

net = GlyphSDF(width)
if init:
    net.load_state_dict(torch.load(init))
print("params", sum(p.numel() for p in net.parameters()), "samples", len(X), flush=True)
LR = 2e-3 if not init else 7e-4
opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-4)


def loss_fn(p, y):
    """L1 on the SDF. Targets are clipped at +-1.5; overshooting a clipped target in the right direction is not an
    error. (Clamping p itself would zero the gradient whenever predictions start out of range.)"""
    w = 1 + 4 * (y.abs() < 0.5).float()              # emphasise the region near the edge
    ok = ((y >= 1.49) & (p > y)) | ((y <= -1.49) & (p < y))
    return (w * torch.where(ok, torch.zeros_like(p), (p - y).abs())).mean()


def evaluate():
    net.eval()
    with torch.no_grad():
        p = torch.cat([net(Xv[i:i + 256]) for i in range(0, len(Xv), 256)])
    net.train()
    edge = Yv.abs() < 0.5
    err = ((p > 0) != (Yv > 0)).float().mean().item()
    err_edge = ((p > 0) != (Yv > 0))[edge].float().mean().item()
    return loss_fn(p, Yv).item(), err, err_edge


import os
os.makedirs("ckpt", exist_ok=True)
SNAP_EVERY = 15          # minutes between kept snapshots
next_snap = SNAP_EVERY
B = 64
t0 = time.time(); step = 0
while True:
    el = (time.time() - t0) / 60
    if el > minutes:
        break
    if el >= next_snap:
        torch.save(net.state_dict(), f"ckpt/{OUT}_{next_snap:03d}min_step{step}.pt")
        next_snap += SNAP_EVERY
    for g in opt.param_groups:
        g["lr"] = LR * (0.03 + 0.97 * 0.5 * (1 + np.cos(np.pi * min(el / minutes, 1))))
    idx = torch.randint(0, len(X), (B,))
    x = X[idx].float()[:, None]; y = Y[idx].float()[:, None] / 80
    if torch.rand(1) < 0.5:
        x, y = x.flip(-1), y.flip(-1)
    loss = loss_fn(net(x), y)
    opt.zero_grad(); loss.backward(); opt.step()
    step += 1
    if step % 500 == 0:
        vl, ve, vee = evaluate()
        print(f"{el:6.1f} min  step {step}  train {loss.item():.4f}  val {vl:.4f}  "
              f"4x-pixel err {ve*100:.2f}%  near-edge err {vee*100:.2f}%", flush=True)
        torch.save(net.state_dict(), f"{OUT}.pt")
torch.save(net.state_dict(), f"{OUT}.pt")
torch.save(net.state_dict(), f"ckpt/{OUT}_final_{int(minutes):03d}min_step{step}.pt")
print("final", evaluate(), flush=True)
