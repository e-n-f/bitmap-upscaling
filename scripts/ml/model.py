import torch
import torch.nn as nn
import torch.nn.functional as F


def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GELU(), nn.Conv2d(o, o, 3, padding=1), nn.GELU())


class GlyphSDF(nn.Module):
    """1-bit image (ink=1) at 1x -> signed distance (1x pixel units, + = ink) at 4x."""

    def __init__(self, c=40):
        super().__init__()
        self.e1 = block(1, c)
        self.e2 = block(c, 2 * c)
        self.e3 = block(2 * c, 4 * c)
        self.d2 = block(4 * c + 2 * c, 2 * c)
        self.d1 = block(2 * c + c, c)
        self.head = nn.Conv2d(c, 16 * 8, 3, padding=1)
        self.refine = nn.Sequential(nn.Conv2d(8, 16, 3, padding=1), nn.GELU(), nn.Conv2d(16, 1, 3, padding=1))

    def forward(self, x):
        x = x * 2 - 1
        h, w = x.shape[-2:]
        ph, pw = (-h) % 4, (-w) % 4
        x = F.pad(x, (0, pw, 0, ph), value=-1)
        a = self.e1(x)
        b = self.e2(F.avg_pool2d(a, 2))
        c = self.e3(F.avg_pool2d(b, 2))
        b = self.d2(torch.cat([F.interpolate(c, scale_factor=2, mode="bilinear"), b], 1))
        a = self.d1(torch.cat([F.interpolate(b, scale_factor=2, mode="bilinear"), a], 1))
        y = F.pixel_shuffle(self.head(a), 4)
        y = self.refine(y)
        return y[..., : 4 * h, : 4 * w]
