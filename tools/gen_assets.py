"""Generates the pixel-art sprites for new enemies, bosses and NPCs (requires Pillow).
Run:  python tools/gen_assets.py   -> writes PNG files into assets/"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets"
OL = (22, 16, 30, 255)


def finish(img, scale=2):
    alpha = img.split()[3]
    grown = alpha.filter(ImageFilter.MaxFilter(3))
    edge = ImageChops.subtract(grown, alpha)
    outline = Image.new("RGBA", img.size, OL)
    outline.putalpha(edge)
    out = Image.alpha_composite(outline, img)
    return out.resize((img.width * scale, img.height * scale), Image.NEAREST)


def canvas(n=32):
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def bat():
    im, d = canvas()
    wing, body = (96, 62, 130, 255), (66, 44, 92, 255)
    d.polygon([(13, 15), (2, 7), (4, 15), (1, 20), (8, 18), (12, 21)], fill=wing)
    d.polygon([(19, 15), (30, 7), (28, 15), (31, 20), (24, 18), (20, 21)], fill=wing)
    d.ellipse((11, 11, 21, 23), fill=body)
    d.polygon([(11, 12), (10, 6), (14, 10)], fill=body)
    d.polygon([(21, 12), (22, 6), (18, 10)], fill=body)
    d.rectangle((13, 15, 14, 16), fill=(255, 220, 80, 255))
    d.rectangle((18, 15, 19, 16), fill=(255, 220, 80, 255))
    d.polygon([(15, 19), (16, 22), (17, 19)], fill=(240, 240, 240, 255))
    return finish(im)


def archer():
    im, d = canvas()
    bone, dark = (226, 220, 204, 255), (150, 142, 128, 255)
    d.ellipse((11, 3, 21, 13), fill=bone)
    d.rectangle((13, 7, 15, 9), fill=OL)
    d.rectangle((17, 7, 19, 9), fill=OL)
    d.rectangle((14, 11, 18, 12), fill=dark)
    d.rectangle((13, 14, 19, 24), fill=bone)
    for y in (16, 19, 22):
        d.line((13, y, 19, y), fill=dark)
    d.line((16, 14, 16, 24), fill=dark)
    d.rectangle((13, 24, 15, 29), fill=bone)
    d.rectangle((17, 24, 19, 29), fill=bone)
    d.line((12, 15, 8, 20), fill=bone, width=2)
    d.arc((19, 6, 30, 26), 270, 90, fill=(140, 96, 56, 255), width=2)
    d.line((24, 7, 24, 25), fill=(230, 230, 230, 255))
    return finish(im)


def shaman():
    im, d = canvas()
    robe, dk = (116, 56, 158, 255), (74, 36, 110, 255)
    d.polygon([(16, 8), (6, 29), (26, 29)], fill=robe)
    d.polygon([(16, 8), (16, 29), (26, 29)], fill=dk)
    d.ellipse((10, 3, 22, 15), fill=dk)
    d.ellipse((12, 6, 20, 14), fill=(30, 18, 40, 255))
    d.rectangle((13, 9, 14, 10), fill=(255, 230, 90, 255))
    d.rectangle((18, 9, 19, 10), fill=(255, 230, 90, 255))
    d.line((26, 10, 26, 29), fill=(120, 84, 50, 255), width=2)
    d.ellipse((23, 4, 29, 10), fill=(230, 110, 255, 255))
    d.ellipse((24, 5, 26, 7), fill=(255, 255, 255, 255))
    return finish(im)


def person(name, skin=(238, 196, 150, 255), robe=(120, 90, 60, 255), hair=(80, 56, 40, 255), hat=None,
           extra=None, beard=None):
    im, d = canvas()
    dk = tuple(max(0, c - 40) for c in robe[:3]) + (255,)
    d.polygon([(11, 15), (21, 15), (24, 28), (8, 28)], fill=robe)
    d.polygon([(16, 15), (21, 15), (24, 28), (16, 28)], fill=dk)
    d.rectangle((12, 27, 15, 30), fill=(60, 44, 36, 255))
    d.rectangle((17, 27, 20, 30), fill=(60, 44, 36, 255))
    d.ellipse((11, 4, 21, 15), fill=skin)
    d.rectangle((13, 9, 14, 10), fill=OL)
    d.rectangle((18, 9, 19, 10), fill=OL)
    if hair:
        d.pieslice((10, 2, 22, 14), 180, 360, fill=hair)
    if beard:
        d.polygon([(12, 12), (20, 12), (16, 19)], fill=beard)
    if hat == "pointy":
        d.polygon([(8, 7), (24, 7), (16, -3)], fill=robe)
        d.rectangle((9, 6, 23, 8), fill=dk)
    elif hat == "hood":
        d.pieslice((9, 1, 23, 16), 180, 360, fill=robe)
        d.rectangle((9, 8, 11, 14), fill=robe)
        d.rectangle((21, 8, 23, 14), fill=robe)
    elif hat == "helm":
        d.pieslice((10, 2, 22, 14), 180, 360, fill=(170, 176, 190, 255))
        d.rectangle((15, 3, 17, 10), fill=(120, 126, 140, 255))
    elif hat == "wide":
        d.ellipse((6, 5, 26, 10), fill=(150, 100, 56, 255))
        d.pieslice((10, 1, 22, 12), 180, 360, fill=(150, 100, 56, 255))
    if extra:
        extra(d)
    return finish(im)


def staff(d):
    d.line((25, 8, 25, 29), fill=(120, 84, 50, 255), width=2)


def bow(d):
    d.arc((21, 8, 31, 26), 270, 90, fill=(140, 96, 56, 255), width=2)


def hammer(d):
    d.line((24, 14, 24, 28), fill=(110, 80, 50, 255), width=2)
    d.rectangle((21, 11, 28, 15), fill=(150, 154, 166, 255))


def lantern(d):
    d.line((25, 12, 25, 18), fill=(80, 60, 40, 255))
    d.rectangle((23, 18, 27, 23), fill=(255, 210, 110, 255))


def sword(d):
    d.line((25, 6, 25, 24), fill=(210, 214, 226, 255), width=2)
    d.line((22, 20, 28, 20), fill=(200, 160, 70, 255), width=2)


def pack(d):
    d.rectangle((5, 14, 10, 24), fill=(190, 110, 50, 255))


def ember(d):
    d.ellipse((22, 16, 28, 22), fill=(255, 130, 40, 255))


def forest_boss():
    im, d = canvas(48)
    bark, dk, leaf = (104, 72, 46, 255), (66, 44, 30, 255), (84, 160, 70, 255)
    for x0, x1 in ((6, 14), (34, 42)):
        d.polygon([(x0, 18), (x1, 26), (x1 - 2, 40), (x0 + 2, 36)], fill=dk)
        d.ellipse((x0 - 3, 30, x0 + 5, 42), fill=leaf)
        d.ellipse((x1 - 3, 30, x1 + 5, 42), fill=leaf)
    d.ellipse((12, 12, 36, 42), fill=bark)
    d.pieslice((12, 12, 36, 42), 90, 270, fill=dk)
    for x in (14, 20, 28, 33):
        d.line((x, 18, x + 2, 38), fill=dk, width=1)
    for x, y in ((8, 8), (14, 3), (22, 1), (30, 3), (37, 8)):
        d.polygon([(x - 4, y + 12), (x, y), (x + 4, y + 12)], fill=leaf)
    d.polygon([(16, 22), (22, 24), (22, 28), (16, 26)], fill=(255, 230, 90, 255))
    d.polygon([(32, 22), (26, 24), (26, 28), (32, 26)], fill=(255, 230, 90, 255))
    d.polygon([(19, 33), (24, 36), (29, 33), (24, 40)], fill=(30, 18, 20, 255))
    for x in range(14, 36, 6):
        d.polygon([(x, 42), (x + 3, 47), (x + 6, 42)], fill=dk)
    return finish(im)


def ruins_boss():
    im, d = canvas(48)
    st, dk, lt = (128, 142, 168, 255), (80, 92, 116, 255), (170, 184, 208, 255)
    d.rectangle((14, 18, 34, 40), fill=st)
    d.rectangle((24, 18, 34, 40), fill=dk)
    d.ellipse((6, 14, 18, 26), fill=lt)
    d.ellipse((30, 14, 42, 26), fill=lt)
    d.rectangle((16, 40, 22, 47), fill=dk)
    d.rectangle((26, 40, 32, 47), fill=dk)
    d.rectangle((16, 4, 32, 18), fill=st)
    d.polygon([(16, 6), (10, 0), (14, 12)], fill=lt)
    d.polygon([(32, 6), (38, 0), (34, 12)], fill=lt)
    d.rectangle((19, 10, 29, 13), fill=(20, 24, 40, 255))
    d.rectangle((20, 10, 22, 12), fill=(110, 240, 255, 255))
    d.rectangle((26, 10, 28, 12), fill=(110, 240, 255, 255))
    for y in (24, 30, 36):
        d.line((19, y, 29, y), fill=(110, 240, 255, 255))
    d.line((24, 22, 24, 38), fill=(110, 240, 255, 255))
    d.line((43, 4, 43, 36), fill=(214, 220, 236, 255), width=3)
    d.line((39, 32, 47, 32), fill=(200, 160, 70, 255), width=3)
    return finish(im)


def ash_boss():
    im, d = canvas(48)
    ch, dk, lava = (60, 48, 52, 255), (34, 28, 34, 255), (255, 120, 40, 255)
    d.polygon([(4, 10), (14, 20), (12, 34), (2, 28)], fill=(150, 50, 30, 255))
    d.polygon([(44, 10), (34, 20), (36, 34), (46, 28)], fill=(150, 50, 30, 255))
    d.ellipse((10, 14, 38, 44), fill=ch)
    d.pieslice((10, 14, 38, 44), 90, 270, fill=dk)
    d.polygon([(14, 16), (8, 3), (20, 12)], fill=dk)
    d.polygon([(34, 16), (40, 3), (28, 12)], fill=dk)
    for pts in (((18, 26), (22, 32), (20, 40)), ((30, 24), (26, 30), (30, 38)), ((24, 18), (24, 24))):
        d.line(pts, fill=lava, width=2)
    d.polygon([(16, 20), (22, 22), (22, 26), (16, 24)], fill=(255, 220, 90, 255))
    d.polygon([(32, 20), (26, 22), (26, 26), (32, 24)], fill=(255, 220, 90, 255))
    d.polygon([(18, 33), (24, 31), (30, 33), (24, 38)], fill=lava)
    for x in range(12, 38, 6):
        d.polygon([(x, 44), (x + 3, 48), (x + 6, 44)], fill=dk)
    return finish(im)


def spore():
    im, d = canvas()
    d.rectangle((12, 15, 20, 27), fill=(226, 214, 190, 255))
    d.rectangle((16, 15, 20, 27), fill=(190, 178, 154, 255))
    d.ellipse((4, 3, 28, 19), fill=(190, 60, 70, 255))
    d.pieslice((4, 3, 28, 19), 90, 270, fill=(150, 44, 56, 255))
    for x, y in ((9, 8), (16, 6), (22, 10), (13, 13)):
        d.ellipse((x, y, x + 3, y + 3), fill=(250, 240, 230, 255))
    d.rectangle((13, 19, 14, 21), fill=OL)
    d.rectangle((18, 19, 19, 21), fill=OL)
    d.rectangle((10, 27, 22, 29), fill=(160, 140, 110, 255))
    return finish(im)


def wisp():
    im, d = canvas()
    d.polygon([(16, 2), (24, 14), (22, 24), (16, 29), (10, 24), (8, 14)], fill=(70, 150, 255, 255))
    d.polygon([(16, 7), (21, 15), (19, 23), (16, 26), (13, 23), (11, 15)], fill=(150, 210, 255, 255))
    d.polygon([(16, 12), (18, 18), (16, 23), (14, 18)], fill=(240, 250, 255, 255))
    d.rectangle((13, 15, 14, 16), fill=OL)
    d.rectangle((18, 15, 19, 16), fill=OL)
    return finish(im)


def ghost():
    im, d = canvas()
    body = (214, 226, 245, 255)
    d.pieslice((7, 3, 25, 21), 180, 360, fill=body)
    d.rectangle((7, 12, 25, 26), fill=body)
    for x in (7, 12, 17, 22):
        d.polygon([(x, 25), (x + 3, 30), (x + 5, 25)], fill=body)
    d.rectangle((12, 11, 14, 15), fill=OL)
    d.rectangle((18, 11, 20, 15), fill=OL)
    d.ellipse((14, 17, 18, 20), fill=(60, 60, 90, 255))
    d.line((7, 15, 3, 21), fill=body, width=3)
    d.line((25, 15, 29, 21), fill=body, width=3)
    return finish(im)


def scarab():
    im, d = canvas()
    for y in (14, 19, 24):
        d.line((4, y, 11, y + 2), fill=(40, 60, 60, 255), width=2)
        d.line((28, y, 21, y + 2), fill=(40, 60, 60, 255), width=2)
    d.ellipse((8, 9, 24, 29), fill=(40, 110, 120, 255))
    d.pieslice((8, 9, 24, 29), 270, 90, fill=(30, 84, 94, 255))
    d.line((16, 11, 16, 28), fill=(230, 190, 80, 255))
    d.ellipse((11, 3, 21, 12), fill=(30, 70, 80, 255))
    d.polygon([(11, 4), (7, 1), (12, 8)], fill=(230, 190, 80, 255))
    d.polygon([(21, 4), (25, 1), (20, 8)], fill=(230, 190, 80, 255))
    d.rectangle((13, 6, 14, 7), fill=(255, 220, 90, 255))
    d.rectangle((18, 6, 19, 7), fill=(255, 220, 90, 255))
    return finish(im)


def imp():
    im, d = canvas()
    red, dk = (210, 60, 50, 255), (150, 36, 36, 255)
    d.polygon([(11, 14), (2, 6), (6, 16), (3, 22), (11, 20)], fill=dk)
    d.polygon([(21, 14), (30, 6), (26, 16), (29, 22), (21, 20)], fill=dk)
    d.ellipse((10, 13, 22, 27), fill=red)
    d.ellipse((10, 3, 22, 15), fill=red)
    d.polygon([(11, 5), (8, -1), (14, 4)], fill=(250, 230, 200, 255))
    d.polygon([(21, 5), (24, -1), (18, 4)], fill=(250, 230, 200, 255))
    d.rectangle((12, 8, 14, 9), fill=(255, 230, 90, 255))
    d.rectangle((18, 8, 20, 9), fill=(255, 230, 90, 255))
    d.polygon([(14, 12), (16, 14), (18, 12)], fill=OL)
    d.line((22, 26, 28, 29), fill=red, width=2)
    d.polygon([(27, 27), (31, 28), (28, 31)], fill=dk)
    d.rectangle((12, 26, 14, 29), fill=dk)
    d.rectangle((18, 26, 20, 29), fill=dk)
    return finish(im)


def magma():
    im, d = canvas()
    d.ellipse((3, 9, 29, 30), fill=(70, 40, 40, 255))
    d.ellipse((5, 11, 27, 29), fill=(240, 100, 30, 255))
    d.ellipse((9, 13, 23, 25), fill=(255, 180, 60, 255))
    for pts in (((6, 14), (10, 18), (8, 24)), ((26, 13), (22, 19), (25, 25))):
        d.line(pts, fill=(60, 30, 30, 255), width=2)
    d.rectangle((12, 17, 14, 19), fill=OL)
    d.rectangle((18, 17, 20, 19), fill=OL)
    return finish(im)


def cultist():
    im, d = canvas()
    robe, dk = (52, 30, 74, 255), (32, 18, 48, 255)
    d.polygon([(16, 7), (5, 29), (27, 29)], fill=robe)
    d.polygon([(16, 7), (16, 29), (27, 29)], fill=dk)
    d.ellipse((10, 2, 22, 14), fill=dk)
    d.ellipse((12, 5, 20, 13), fill=(20, 10, 28, 255))
    d.rectangle((13, 8, 14, 9), fill=(255, 60, 70, 255))
    d.rectangle((18, 8, 19, 9), fill=(255, 60, 70, 255))
    d.line((8, 18, 4, 14), fill=robe, width=3)
    d.ellipse((1, 9, 8, 16), fill=(170, 80, 255, 255))
    d.ellipse((3, 11, 5, 13), fill=(255, 255, 255, 255))
    d.line((16, 16, 16, 28), fill=(170, 40, 60, 255))
    return finish(im)


def char(kind, view):
    im, d = canvas()
    cfg = {"knight": ((168, 174, 190, 255), (60, 100, 190, 255), None),
           "ranger": ((70, 140, 80, 255), (120, 84, 50, 255), (130, 74, 40, 255)),
           "mage": ((118, 64, 176, 255), (240, 210, 120, 255), (232, 232, 245, 255))}[kind]
    cloth, trim, hair = cfg
    dk = tuple(max(0, c - 45) for c in cloth[:3]) + (255,)
    skin = (238, 196, 150, 255)
    boots = (64, 46, 38, 255)
    if view == "side":
        d.polygon([(12, 15), (21, 15), (22, 28), (10, 28)], fill=cloth)
        d.polygon([(12, 15), (16, 15), (16, 28), (10, 28)], fill=dk)
        d.rectangle((12, 27, 20, 30), fill=boots)
        d.ellipse((11, 3, 22, 15), fill=skin)
        d.rectangle((19, 8, 20, 9), fill=OL)
    else:
        d.polygon([(10, 15), (22, 15), (24, 28), (8, 28)], fill=cloth)
        d.polygon([(16, 15), (22, 15), (24, 28), (16, 28)], fill=dk)
        d.rectangle((11, 27, 15, 30), fill=boots)
        d.rectangle((17, 27, 21, 30), fill=boots)
        if view == "down":
            d.ellipse((10, 3, 22, 15), fill=skin)
            d.rectangle((13, 9, 14, 10), fill=OL)
            d.rectangle((18, 9, 19, 10), fill=OL)
        else:
            d.ellipse((10, 3, 22, 15), fill=hair or (120, 126, 140, 255))
    d.line((12, 20, 21, 20), fill=trim, width=2)
    if kind == "knight":
        helm = (170, 176, 192, 255)
        if view == "side":
            d.pieslice((10, 1, 23, 14), 180, 360, fill=helm)
            d.rectangle((10, 7, 22, 9), fill=helm)
            d.polygon([(10, 4), (4, 6), (6, 12)], fill=(200, 50, 50, 255))
        else:
            d.pieslice((9, 1, 23, 15), 180, 360, fill=helm)
            if view == "up":
                d.ellipse((10, 3, 22, 15), fill=helm)
            d.rectangle((15, 0, 17, 5), fill=(200, 50, 50, 255))
            if view == "down":
                d.rectangle((12, 8, 20, 9), fill=OL)
        d.polygon([(8, 15), (12, 14), (12, 19)], fill=helm)
        d.polygon([(24, 15), (20, 14), (20, 19)], fill=helm)
    elif kind == "ranger":
        d.pieslice((9, 1, 23, 14), 180, 360, fill=cloth)
        if view == "down":
            d.rectangle((9, 7, 11, 13), fill=cloth)
            d.rectangle((21, 7, 23, 13), fill=cloth)
        else:
            d.ellipse((9, 3, 23, 15), fill=cloth if view == "up" else skin)
            if view == "side":
                d.pieslice((9, 1, 22, 13), 180, 360, fill=cloth)
        if view != "down":
            d.line((11, 12, 7, 24), fill=hair, width=3)
            d.rectangle((20, 14, 24, 25), fill=(110, 80, 50, 255))
            d.line((22, 12, 22, 14), fill=(220, 220, 220, 255))
    else:
        d.polygon([(7, 7), (25, 7), (16, -4)], fill=cloth)
        d.rectangle((8, 6, 24, 8), fill=trim)
        if view == "down":
            d.polygon([(12, 13), (20, 13), (16, 21)], fill=hair)
        else:
            d.rectangle((11, 9, 21, 14), fill=hair)
    return finish(im)


def main():
    OUT.mkdir(exist_ok=True)
    sprites = {
        "enemy_bat": bat(), "enemy_archer": archer(), "enemy_shaman": shaman(),
        "enemy_spore": spore(), "enemy_wisp": wisp(), "enemy_ghost": ghost(), "enemy_scarab": scarab(),
        "enemy_imp": imp(), "enemy_magma": magma(), "enemy_cultist": cultist(),
        "boss_forest": forest_boss(), "boss_ruins": ruins_boss(), "boss_ash": ash_boss(),
        "npc_elder": person("elder", robe=(150, 120, 80, 255), hair=(220, 220, 220, 255), beard=(225, 225, 225, 255), extra=staff),
        "npc_hunter": person("hunter", robe=(70, 120, 70, 255), hat="hood", extra=bow, hair=None),
        "npc_liara": person("liara", robe=(110, 70, 170, 255), hat="pointy", hair=(240, 240, 255, 255), extra=staff),
        "npc_valdo": person("valdo", robe=(170, 150, 90, 255), hat="wide", extra=lantern, hair=(90, 60, 40, 255)),
        "npc_kael": person("kael", robe=(130, 134, 150, 255), hat="helm", extra=sword, hair=None),
        "npc_rud": person("rud", robe=(190, 80, 40, 255), hat="hood", extra=ember, hair=None, beard=(200, 190, 180, 255)),
        "npc_smith": person("smith", robe=(80, 80, 96, 255), hair=None, extra=hammer, beard=(70, 50, 40, 255)),
        "npc_merchant": person("merchant", robe=(60, 120, 150, 255), hat="wide", extra=pack, hair=(60, 40, 30, 255)),
    }
    for ci, kind in enumerate(("knight", "ranger", "mage")):
        for view in ("down", "up", "side"):
            sprites["char%d_%s" % (ci, view)] = char(kind, view)
    for name, img in sprites.items():
        img.save(OUT / (name + ".png"))
    sheet = Image.new("RGBA", (96 * 10, 96 * 5), (40, 50, 60, 255))
    for i, (name, img) in enumerate(sprites.items()):
        sheet.alpha_composite(img, ((i % 10) * 96, (i // 10) * 96))
    sheet.save(OUT.parent / "tools" / "contact_sheet.png")


if __name__ == "__main__":
    main()
