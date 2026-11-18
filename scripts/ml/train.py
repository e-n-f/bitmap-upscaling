import sys, time
import numpy as np
import torch
from model import GlyphSDF

torch.set_num_threads(4)
torch.manual_seed(0)
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 40

d = np.load("train.npz"); v = np.load("val.npz")
X = torch.from_numpy(d["x"]).float()[:, None]
Y = torch.from_numpy(d["y"]).float()[:, None] / 80
Xv = torch.from_numpy(v["x"]).float()[:, None]
Yv = torch.from_numpy(v["y"]).float()[:, None] / 80

net = GlyphSDF()
print("params", sum(p.numel() for p in net.parameters()), flush=True)
opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)


def loss_fn(p, y):
    w = 1 + 4 * (y.abs() < 0.5).float()              # emphasise the region near the edge
    return (w * (p.clamp(-1.5, 1.5) - y).abs()).mean()


def evaluate():
    net.eval()
    with torch.no_grad():
        p = torch.cat([net(Xv[i:i + 256]) for i in range(0, len(Xv), 256)])
    net.train()
    err = ((p > 0) != (Yv > 0)).float().mean().item()    # 4x pixel disagreement
    return loss_fn(p, Yv).item(), err


B = 64
t0 = time.time(); step = 0
total_steps_est = None
while True:
    el = (time.time() - t0) / 60
    if el > minutes:
        break
    # cosine-ish decay by wall time
    for g in opt.param_groups:
        g["lr"] = 2e-3 * (0.05 + 0.95 * 0.5 * (1 + np.cos(np.pi * min(el / minutes, 1))))
    idx = torch.randint(0, len(X), (B,))
    x, y = X[idx], Y[idx]
    if torch.rand(1) < 0.5:
        x, y = x.flip(-1), y.flip(-1)
    loss = loss_fn(net(x), y)
    opt.zero_grad(); loss.backward(); opt.step()
    step += 1
    if step % 300 == 0:
        vl, ve = evaluate()
        print(f"{el:5.1f} min  step {step}  train {loss.item():.4f}  val {vl:.4f}  val 4x-pixel err {ve*100:.2f}%", flush=True)
        torch.save(net.state_dict(), "glyphsdf.pt")
torch.save(net.state_dict(), "glyphsdf.pt")
print("final", evaluate(), flush=True)
