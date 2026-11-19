"""Combine individual specimens into family sheets at 1x and 2x (pixel-doubled).

usage: python -I build_sheets.py SPECIMEN_ROOT OUT_1X OUT_2X
SPECIMEN_ROOT holds lisa-source-fonts/, lisa-kreative/ and mac-classic/ (with INDEX.txt).
"""
import glob, os, re, sys
from PIL import Image

root, out1, out2 = sys.argv[1:4]
os.makedirs(out1, exist_ok=True); os.makedirs(out2, exist_ok=True)


def stack(paths, name):
    ims = [Image.open(p).convert("L") for p in paths]
    W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
    S = Image.new("L", (W, H), 255); y = 0
    for i in ims:
        S.paste(i, (0, y)); y += i.height + 6
    S.save(f"{out1}/{name}_1x.png")
    S.resize((W * 2, H * 2), Image.NEAREST).save(f"{out2}/{name}.png")
    print(name, len(paths), S.size)


L = lambda names: [f"{root}/lisa-source-fonts/{n}.png" for n in names]
stack([f"{root}/lisa-kreative/{n}.png" for n in ("TwiggyRaw", "SomeAcronymRaw")], "lisa_specimens_kreative")
stack(L(["TILE12RPS", "TILE12R12S", "TILE12R10S", "TILE7R15S", "TILE7R20S", "TILE12VTS", "TILE20VTS"]), "lisa_specimens_modern")
stack(L(["CENTURY12RPS", "CENTURY12R12S", "CENTURY12R10S", "CENTURY14S", "CENTURY18RPS", "CENTURY24RPS", "HELV14S"]),
      "lisa_specimens_classic_helv")
stack(L(["TILE12RPS", "TILE12RPC", "TILE12RPH", "CENTURY12RPS", "CENTURY12RPC", "CENTURY12RPH", "CENTURY18RPS",
         "CENTURY18RPH", "CENTURY18RPT"]), "lisa_devices")
stack(L(["TOOLKITS", "WMFONTS", "CALCFONTS"]), "lisa_icon_fonts")

# classic Mac: which specimens came from the Twiggy suitcase (its Helvetica uses Geneva's family number)
src = {}
for line in open(f"{root}/mac-classic/INDEX.txt"):
    if "->" in line and "duplicate" not in line:
        src[line.split("->")[1].strip()] = line[29:56].strip()


def key(f):
    b = os.path.basename(f)[:-4]; m = re.match(r"(.*?)_(\d+)(.*)", b)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (b, 0, "")


files = sorted(glob.glob(f"{root}/mac-classic/*.png"))
tw = [f for f in files if "Twiggy" in src.get(os.path.basename(f)[:-4], "")]
rest = [f for f in files if f not in tw]
for name, fams, pool in [
        ("mac_chicago_monaco_venice", ["Chicago", "Monaco", "Venice"], rest), ("mac_geneva", ["Geneva"], rest),
        ("mac_newyork", ["NewYork"], rest),
        ("mac_cities", ["London", "Athens", "SanFrancisco", "Toronto", "LosAngeles", "Cairo", "Taliesin", "Mobile", "SwanSong"], rest),
        ("mac_times_helvetica", ["Times", "Helvetica"], rest), ("mac_courier_palatino_symbol", ["Courier", "Palatino", "Symbol"], rest),
        ("mac_twiggy_suitcase", ["System", "Gacha", "Cream", "TimesRoman", "Helvetica"], tw)]:
    sel = sorted([f for f in pool if key(f)[0] in fams], key=lambda f: (fams.index(key(f)[0]), key(f)[1], key(f)[2]))
    stack(sel, name)
