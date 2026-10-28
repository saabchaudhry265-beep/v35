"""Procedural art: weapons, item icons, props, set pieces and effects."""
import math
import random

import pygame

from .common import *

_glows = {}
_props = {}
_fonts = {}
_lights = {}
_discs = {}
LOWFX = [False]


def reset_font_cache():
    """Discard native font handles after pygame's font subsystem restarts."""
    _fonts.clear()


def font(size, bold=True):
    # Tests and some shutdown/restart paths call pygame.quit() and then create
    # another Game in the same process. Pygame Font objects from the old font
    # subsystem must not be reused after that native subsystem is restarted.
    if not pygame.font.get_init():
        pygame.font.init()
        _fonts.clear()
    key = (size, bold)
    if key not in _fonts:
        name = "DejaVuSansCondensed-Bold.ttf" if bold else "DejaVuSansCondensed.ttf"
        try:
            _fonts[key] = pygame.font.Font(str(ASSETS / "fonts" / name), size)
        except (OSError, pygame.error):
            _fonts[key] = pygame.font.SysFont("dejavusans,arial", size, bold=bold)
    return _fonts[key]


def S(w, h):
    return pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)


def glow_surface(radius, color):
    radius = max(6, int(radius) // 6 * 6)
    key = (radius, tuple(color[:3]))
    if key not in _glows:
        if len(_glows) > 200:
            _glows.clear()
        surf = S(radius * 2, radius * 2)
        for r in range(radius, 0, -3):
            alpha = int(150 * (1 - r / radius) ** 1.7)
            pygame.draw.circle(surf, (*key[1], alpha), (radius, radius), r)
        _glows[key] = surf
    return _glows[key]


def light_surface(radius):
    radius = max(8, int(radius) // 8 * 8)
    if radius not in _lights:
        surf = S(radius * 2, radius * 2)
        for r in range(radius, 0, -4):
            a = int(255 * (1 - r / radius) ** 1.1)
            pygame.draw.circle(surf, (255, 255, 255, a), (radius, radius), r)
        _lights[radius] = surf
    return _lights[radius]


def disc_surface(radius, color, alpha):
    key = (int(radius), tuple(color[:3]), alpha // 8)
    if key not in _discs:
        if len(_discs) > 150:
            _discs.clear()
        surf = S(key[0] * 2 + 4, key[0] * 2 + 4)
        pygame.draw.circle(surf, (*key[1], key[2] * 8), (key[0] + 2, key[0] + 2), key[0])
        _discs[key] = surf
    return _discs[key]


def dashed_circle(canvas, color, x, y, r, width=3, segments=18, spin=0.0):
    for k in range(segments):
        a0 = spin + k * math.tau / segments
        a1 = a0 + math.tau / segments * 0.55
        pygame.draw.line(canvas, color, (x + math.cos(a0) * r, y + math.sin(a0) * r),
                         (x + math.cos(a1) * r, y + math.sin(a1) * r), width)


def draw_glow(canvas, x, y, radius, color, strength=1.0):
    if LOWFX[0]:
        return
    surf = glow_surface(radius, color)
    surf.set_alpha(int(255 * clamp(strength, 0, 1)))
    canvas.blit(surf, (int(x - surf.get_width() / 2), int(y - surf.get_height() / 2)))


def shadow(canvas, x, y, w, h=None):
    h = h or w * 0.4
    sh = S(w * 2 + 2, h * 2 + 2)
    pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, int(w * 2), int(h * 2)))
    canvas.blit(sh, (int(x - w), int(y - h)))


# ---------------------------------------------------------------- weapons
METALS = [((196, 202, 214), (120, 126, 140)), ((160, 205, 240), (80, 120, 170)),
          ((255, 170, 100), (150, 70, 45))]


def draw_weapon(canvas, kind, tier, accent, x, y, ang, scale=1.0, t=0.0, active=False):
    ca, sa = math.cos(ang), math.sin(ang)

    def P(d, o=0.0):
        return (x + (ca * d - sa * o) * scale, y + (sa * d + ca * o) * scale)

    tier = int(clamp(tier, 0, 2))
    light, dark = METALS[tier]
    wood = (110, 76, 48)
    if kind == "sword":
        ln = 30 + tier * 5
        blade = [P(8, -3.5), P(8 + ln, -2.5), P(13 + ln, 0), P(8 + ln, 2.5), P(8, 3.5)]
        pygame.draw.polygon(canvas, dark, blade)
        pygame.draw.line(canvas, light, P(9, -0.5), P(10 + ln, -0.5), 2)
        pygame.draw.line(canvas, accent, P(7, -8 - tier * 2), P(7, 8 + tier * 2), 4)
        pygame.draw.line(canvas, wood, P(0, 0), P(7, 0), 4)
        pygame.draw.circle(canvas, accent, P(-1, 0), max(2, int(3 * scale)))
        tip = P(13 + ln, 0)
    elif kind == "spear":
        ln = 50 + tier * 6
        pygame.draw.line(canvas, wood, P(-12, 0), P(ln, 0), max(2, int(3 * scale)))
        head = [P(ln - 2, -5 - tier), P(ln + 15, 0), P(ln - 2, 5 + tier)]
        pygame.draw.polygon(canvas, light, head)
        pygame.draw.polygon(canvas, dark, head, 1)
        pygame.draw.line(canvas, accent, P(ln - 8, -3), P(ln - 8, 3), 3)
        tip = P(ln + 15, 0)
    elif kind == "hammer":
        ln = 34 + tier * 3
        pygame.draw.line(canvas, wood, P(-8, 0), P(ln, 0), max(3, int(4 * scale)))
        head = [P(ln - 6, -10 - tier), P(ln + 12, -10 - tier), P(ln + 12, 10 + tier), P(ln - 6, 10 + tier)]
        pygame.draw.polygon(canvas, dark, head)
        pygame.draw.polygon(canvas, light, [head[0], head[1], P(ln + 12, -2), P(ln - 6, -2)])
        pygame.draw.line(canvas, accent, P(ln + 2, -10 - tier), P(ln + 2, 10 + tier), 3)
        tip = P(ln + 12, 0)
    elif kind == "bow":
        pts = [P(14 * (1 - (k / 7.0) ** 2), k * 3.2) for k in range(-7, 8)]
        pygame.draw.lines(canvas, wood, False, pts, max(3, int(4 * scale)))
        pygame.draw.line(canvas, (225, 225, 225), pts[0], pts[-1], 1)
        pygame.draw.line(canvas, accent, P(2, -3), P(2, 3), 3)
        if active:
            pygame.draw.line(canvas, (235, 225, 200), P(-4, 0), P(30, 0), 2)
            pygame.draw.polygon(canvas, light, [P(30, -3), P(38, 0), P(30, 3)])
        tip = P(14, 0)
    else:
        ln = 40 + tier * 4
        pygame.draw.line(canvas, wood, P(-8, 0), P(ln, 0), max(3, int(4 * scale)))
        for k in range(1 + tier):
            pygame.draw.line(canvas, accent, P(ln - 8 - k * 5, -4), P(ln - 8 - k * 5, 4), 2)
        orb = P(ln + 5, 0)
        if active:
            draw_glow(canvas, orb[0], orb[1], 34, accent, 0.9)
        pygame.draw.circle(canvas, dark, (int(orb[0]), int(orb[1])), max(4, int(7 * scale)))
        pygame.draw.circle(canvas, accent, (int(orb[0]), int(orb[1])), max(3, int(5 * scale)))
        pygame.draw.circle(canvas, (255, 255, 255), (int(orb[0] - 1), int(orb[1] - 1)), 2)
        tip = orb
    return tip


# ------------------------------------------------------------ item icons
def draw_item_icon(canvas, item, cx, cy, size, t=0.0):
    s = size / 48.0
    tier = item.tier
    acc = item.color
    if item.slot == "weapon":
        ang = -math.pi / 4
        c = math.cos(ang)
        offs = {"sword": 13, "spear": 20, "staff": 16, "hammer": 16, "bow": 10}[item.weapon]
        draw_weapon(canvas, item.weapon, tier, acc, cx - c * offs * s * 1.2 + 4 * s,
                    cy + offs * s * 0.9 - 2 * s, ang, s * 0.95, t, True)
    elif item.slot == "armor":
        base = [(138, 98, 60), (130, 145, 170), (120, 54, 44)][tier]
        dk = rgb(base, 0.6)

        def P(px, py):
            return (cx + px * s, cy + py * s)

        body = [P(-12, -14), P(-6, -18), P(6, -18), P(12, -14), P(18, -8), P(12, -2),
                P(11, 16), P(-11, 16), P(-12, -2), P(-18, -8)]
        pygame.draw.polygon(canvas, base, body)
        pygame.draw.polygon(canvas, dk, body, 2)
        pygame.draw.line(canvas, acc, P(-9, -13), P(9, -13), max(2, int(3 * s)))
        pygame.draw.line(canvas, acc, P(0, -12), P(0, 15), max(1, int(2 * s)))
        pygame.draw.line(canvas, acc, P(-10, 11), P(10, 11), max(2, int(3 * s)))
        if tier == 2:
            for sx in (-1, 1):
                pygame.draw.polygon(canvas, (60, 30, 30), [P(sx * 16, -10), P(sx * 24, -18), P(sx * 20, -4)])
    else:
        gem = rgb(acc)

        def P(px, py):
            return (cx + px * s, cy + py * s)

        pts = [P(-14 + k * 28 / 8, -16 + 6 * math.sin(k / 8 * math.pi) * -1 + 2) for k in range(9)]
        pygame.draw.lines(canvas, (170, 150, 90), False,
                          [P(-15, -16), P(-12, -2), P(-4, 8), P(0, 10), P(4, 8), P(12, -2), P(15, -16)], 2)
        gc = P(0, 12)
        if tier == 0:
            pygame.draw.circle(canvas, gem, (int(gc[0]), int(gc[1])), max(4, int(8 * s)))
            pygame.draw.circle(canvas, (255, 255, 255), (int(gc[0] - 2 * s), int(gc[1] - 2 * s)), max(1, int(2 * s)))
        elif tier == 1:
            pygame.draw.polygon(canvas, gem, [P(-8, 8), P(0, 3), P(8, 8), P(0, 21)])
            pygame.draw.polygon(canvas, rgb(gem, 0.55), [P(-8, 8), P(0, 3), P(8, 8), P(0, 21)], 2)
        else:
            star = []
            for k in range(10):
                rr = 11 if k % 2 == 0 else 5
                a = -math.pi / 2 + k * math.pi / 5
                star.append(P(math.cos(a) * rr, 12 + math.sin(a) * rr))
            pygame.draw.polygon(canvas, gem, star)
            pygame.draw.polygon(canvas, (255, 240, 200), star, 1)


def draw_item_frame(canvas, rect, item, t=0.0, hover=False):
    rect = pygame.Rect(rect)
    r = item.rarity
    col = item.color
    pygame.draw.rect(canvas, (24, 32, 46), rect, border_radius=6)
    if r >= 1:
        pulse = 0.5 + 0.5 * math.sin(t * 3 + rect.x)
        draw_glow(canvas, rect.centerx, rect.centery, rect.w * 0.75, col, (0.18 + 0.12 * r) * (0.7 + 0.3 * pulse))
    pygame.draw.rect(canvas, col, rect, 3 if hover or r >= 3 else 2, border_radius=6)
    draw_item_icon(canvas, item, rect.centerx, rect.centery, rect.w - 8, t)
    if r >= 3:
        for k in range(2 + (r - 3)):
            a = t * 1.6 + k * 2.1
            px = rect.centerx + math.cos(a) * rect.w * 0.45
            py = rect.centery + math.sin(a * 1.3) * rect.h * 0.45
            pygame.draw.circle(canvas, (255, 255, 255), (int(px), int(py)), 2)
    if item.plus:
        pygame.draw.rect(canvas, (20, 24, 34), (rect.right - 24, rect.bottom - 16, 22, 14), border_radius=3)
        canvas.blit(font(12).render("+" + str(item.plus), True, GOLD), (rect.right - 21, rect.bottom - 16))


# ----------------------------------------------------------------- props
def _poly(s, color, pts, outline=None):
    pygame.draw.polygon(s, color, pts)
    if outline:
        pygame.draw.polygon(s, outline, pts, 2)


def _make_prop(kind, var):
    rng = random.Random(hash((kind, var)) & 0xFFFF)
    if kind == "tree":
        s = S(110, 140)
        trunk = (92, 62, 40)
        if var == 1:  # pine
            pygame.draw.rect(s, trunk, (50, 100, 10, 30))
            for k, (w, y) in enumerate(((46, 88), (38, 62), (28, 38))):
                _poly(s, (36 + k * 8, 92 + k * 10, 60 + k * 4), [(55 - w, y + 22), (55, y - 18), (55 + w, y + 22)], (24, 60, 40))
        elif var == 2:  # oak
            pygame.draw.rect(s, trunk, (49, 70, 14, 62))
            for (ox, oy, rr, c) in ((55, 48, 34, (58, 118, 62)), (34, 62, 24, (50, 104, 56)), (78, 62, 24, (50, 104, 56)), (50, 36, 20, (84, 148, 78))):
                pygame.draw.circle(s, c, (ox, oy), rr)
        else:  # round
            pygame.draw.rect(s, trunk, (50, 84, 10, 46))
            pygame.draw.circle(s, (62, 120, 64), (55, 62), 32)
            pygame.draw.circle(s, (88, 150, 80), (44, 50), 18)
            pygame.draw.circle(s, (48, 100, 54), (70, 72), 16)
        return s, 55, 132
    if kind == "rock":
        s = S(80, 64)
        _poly(s, (116, 120, 130), [(6, 56), (14, 24), (36, 8), (62, 18), (74, 56)], (60, 62, 72))
        _poly(s, (150, 154, 164), [(16, 28), (36, 12), (50, 20), (30, 34)])
        return s, 40, 58
    if kind == "bush":
        s = S(60, 46)
        for ox, oy, rr in ((18, 28, 14), (32, 22, 16), (44, 30, 13)):
            pygame.draw.circle(s, (54, 108, 56), (ox, oy), rr)
        pygame.draw.circle(s, (92, 156, 86), (30, 18), 7)
        return s, 30, 42
    if kind == "pillar":
        s = S(70, 130)
        broken = var == 1
        top = 40 if broken else 14
        pygame.draw.rect(s, (130, 130, 148), (20, top, 30, 100))
        pygame.draw.rect(s, (96, 96, 112), (20, top, 8, 100))
        pygame.draw.rect(s, (150, 150, 168), (14, 112, 42, 12))
        if broken:
            _poly(s, (130, 130, 148), [(20, 40), (28, 30), (36, 42), (44, 28), (50, 40)])
        else:
            pygame.draw.rect(s, (150, 150, 168), (14, 6, 42, 12))
        pygame.draw.line(s, (70, 70, 84), (34, 50), (30, 80), 2)
        return s, 35, 124
    if kind == "rubble":
        s = S(80, 50)
        for ox, oy, rr in ((20, 36, 12), (42, 30, 15), (60, 38, 10), (32, 40, 9)):
            _poly(s, (112, 112, 128), [(ox - rr, oy + 8), (ox - rr * 0.5, oy - rr * 0.7), (ox + rr * 0.6, oy - rr * 0.5), (ox + rr, oy + 8)], (66, 66, 80))
        return s, 40, 46
    if kind == "statue":
        s = S(70, 140)
        pygame.draw.rect(s, (120, 120, 136), (10, 104, 50, 24))
        pygame.draw.rect(s, (140, 140, 156), (6, 120, 58, 10))
        pygame.draw.rect(s, (150, 150, 166), (24, 50, 22, 56), border_radius=6)
        pygame.draw.circle(s, (160, 160, 176), (35, 40), 12)
        pygame.draw.line(s, (150, 150, 166), (24, 56), (10, 82), 6)
        pygame.draw.line(s, (150, 150, 166), (46, 56), (62, 40), 6)
        return s, 35, 132
    if kind == "deadtree":
        s = S(100, 130)
        c = (84, 70, 62)
        pygame.draw.line(s, c, (50, 126), (50, 60), 9)
        for (x0, y0, x1, y1) in ((50, 80, 20, 40), (50, 70, 80, 30), (50, 98, 78, 70), (22, 44, 10, 24), (80, 32, 92, 14)):
            pygame.draw.line(s, c, (x0, y0), (x1, y1), 5)
        return s, 50, 124
    if kind == "spike":
        s = S(80, 110)
        for ox, h, w in ((22, 70, 12), (40, 98, 14), (58, 60, 11)):
            _poly(s, (44, 36, 48), [(ox - w, 104), (ox, 104 - h), (ox + w, 104)], (22, 18, 28))
            pygame.draw.line(s, (255, 110, 60), (ox, 104 - h + 8), (ox, 96), 2)
        return s, 40, 104
    if kind == "boulder":
        s = S(90, 70)
        _poly(s, (70, 56, 56), [(6, 64), (12, 28), (34, 8), (64, 12), (84, 40), (82, 64)], (36, 28, 30))
        pygame.draw.line(s, (255, 120, 60), (34, 18), (44, 40), 2)
        pygame.draw.line(s, (255, 120, 60), (44, 40), (40, 56), 2)
        return s, 45, 64
    if kind == "hut":
        s = S(150, 130)
        pygame.draw.rect(s, (130, 94, 60), (24, 54, 102, 62))
        pygame.draw.rect(s, (86, 58, 38), (24, 54, 102, 62), 3)
        _poly(s, (160, 76, 60), [(10, 58), (75, 8), (140, 58)], (96, 40, 36))
        pygame.draw.rect(s, (60, 40, 28), (64, 80, 24, 36))
        pygame.draw.rect(s, (240, 200, 120), (36, 70, 16, 14))
        return s, 75, 118
    if kind == "tent":
        s = S(130, 100)
        _poly(s, (198, 156, 96), [(8, 92), (65, 8), (122, 92)], (110, 80, 50))
        _poly(s, (52, 40, 36), [(48, 92), (65, 46), (82, 92)])
        pygame.draw.line(s, (110, 80, 50), (65, 8), (65, 0), 3)
        return s, 65, 92
    if kind == "crate":
        s = S(46, 46)
        pygame.draw.rect(s, (132, 92, 56), (3, 6, 40, 38))
        pygame.draw.rect(s, (84, 56, 34), (3, 6, 40, 38), 3)
        pygame.draw.line(s, (84, 56, 34), (3, 6), (43, 44), 2)
        pygame.draw.line(s, (84, 56, 34), (43, 6), (3, 44), 2)
        return s, 23, 42
    return S(10, 10), 5, 8


def prop_sprite(kind, var=0):
    key = (kind, var)
    if key not in _props:
        _props[key] = _make_prop(kind, var)
    return _props[key]


def draw_prop(canvas, kind, var, x, y):
    surf, ax, ay = prop_sprite(kind, var)
    canvas.blit(surf, (int(x - ax), int(y - ay)))


WALL_COLORS = {"forest": ((104, 96, 86), (66, 60, 54)), "ruins": ((122, 122, 140), (74, 74, 90)),
               "ash": ((84, 66, 64), (46, 36, 38))}


def draw_wall(canvas, rect, biome):
    top, side = WALL_COLORS.get(biome, WALL_COLORS["ruins"])
    r = pygame.Rect(rect)
    pygame.draw.rect(canvas, side, (r.x, r.y + 10, r.w, r.h))
    pygame.draw.rect(canvas, top, (r.x, r.y, r.w, r.h), border_radius=3)
    for k in range(0, max(r.w, r.h), 26):
        if r.w >= r.h:
            pygame.draw.line(canvas, side, (r.x + k, r.y), (r.x + k, r.y + r.h), 1)
        else:
            pygame.draw.line(canvas, side, (r.x, r.y + k), (r.x + r.w, r.y + k), 1)


# ----------------------------------------------------------- animated bits
def draw_flame(canvas, x, y, t, size=1.0, seed=0):
    for k, (col, w, h) in enumerate(((  (230, 90, 40), 13, 34), ((255, 170, 60), 9, 26), ((255, 235, 150), 5, 16))):
        flick = math.sin(t * 11 + seed + k * 1.7) * 2.2 * size
        pts = [(x - w * size, y), (x - w * 0.5 * size + flick, y - h * 0.6 * size),
               (x + flick * 1.4, y - h * size - math.sin(t * 13 + seed) * 3 * size),
               (x + w * 0.5 * size + flick, y - h * 0.6 * size), (x + w * size, y)]
        pygame.draw.polygon(canvas, col, pts)


def draw_torch(canvas, x, y, t, seed=0):
    shadow(canvas, x, y, 8, 3)
    pygame.draw.rect(canvas, (96, 66, 44), (int(x - 3), int(y - 36), 6, 36))
    pygame.draw.rect(canvas, (58, 52, 56), (int(x - 6), int(y - 40), 12, 6))
    draw_glow(canvas, x, y - 48, 70 + int(6 * math.sin(t * 9 + seed)), (255, 150, 70), 0.55)
    draw_flame(canvas, x, y - 40, t, 0.7, seed)


def draw_campfire(canvas, x, y, t):
    shadow(canvas, x, y + 6, 30, 10)
    draw_glow(canvas, x, y - 14, 150 + int(8 * math.sin(t * 8)), (255, 140, 60), 0.6)
    for ang in (0.4, 1.4, 2.4, 3.4):
        ex, ey = x + math.cos(ang) * 22, y + 4 + math.sin(ang) * 8
        pygame.draw.line(canvas, (84, 56, 36), (x, y), (ex, ey), 6)
    for k in range(8):
        a = k * math.tau / 8
        pygame.draw.circle(canvas, (110, 112, 122), (int(x + math.cos(a) * 28), int(y + 4 + math.sin(a) * 11)), 5)
    draw_flame(canvas, x, y + 2, t, 1.5)
    for k in range(5):
        ph = (t * 0.9 + k * 0.37) % 1
        pygame.draw.circle(canvas, (255, 200 - int(ph * 80), 90), (int(x + math.sin(k * 3 + t) * 14 * ph), int(y - 20 - ph * 48)), max(1, int(3 * (1 - ph))))


def draw_banner(canvas, x, y, t, color=(176, 60, 60)):
    shadow(canvas, x, y, 8, 3)
    pygame.draw.line(canvas, (96, 66, 44), (x, y), (x, y - 80), 4)
    pts = [(x, y - 78)]
    for k in range(0, 7):
        pts.append((x + 6 + k * 5, y - 78 + math.sin(t * 4 + k * 0.8) * 3 + k * 0.6))
    pts += [(x + 36, y - 52 + math.sin(t * 4 + 5) * 3)]
    pts += [(x + 6 + k * 5, y - 50 + math.sin(t * 4 + k * 0.8) * 3) for k in range(6, -1, -1)]
    pygame.draw.polygon(canvas, color, pts)


def draw_obelisk(canvas, x, y, t, seed=0):
    shadow(canvas, x, y, 16, 5)
    pygame.draw.polygon(canvas, (92, 98, 116), [(x - 14, y), (x - 9, y - 70), (x, y - 84), (x + 9, y - 70), (x + 14, y)])
    pygame.draw.polygon(canvas, (60, 64, 80), [(x, y - 84), (x + 9, y - 70), (x + 14, y), (x, y)])
    pulse = 0.55 + 0.45 * math.sin(t * 2.4 + seed)
    draw_glow(canvas, x, y - 46, 46, (110, 220, 255), 0.5 * pulse)
    pygame.draw.line(canvas, (130, 230, 255), (x - 3, y - 60), (x - 3, y - 30), 2)
    pygame.draw.circle(canvas, (170, 240, 255), (int(x), int(y - 46)), 4)


def draw_camp_ground(canvas, sx, sy, t, ripples):
    """Rune barrier ring on the ground, drawn under the entities."""
    R = CAMP_R
    dome = S(R * 2 + 8, R * 2 + 8)
    pulse = 0.5 + 0.5 * math.sin(t * 1.6)
    pygame.draw.circle(dome, (110, 200, 255, int(18 + 12 * pulse)), (R + 4, R + 4), R)
    canvas.blit(dome, (int(sx - R - 4), int(sy - R - 4)))
    pygame.draw.circle(canvas, (96, 170, 220), (int(sx), int(sy)), R, 2)
    pygame.draw.circle(canvas, (70, 120, 170), (int(sx), int(sy)), R - 14, 1)
    for k in range(24):
        a = k * math.tau / 24 + t * 0.15
        glowing = (k + int(t * 2)) % 3 == 0
        c = (150, 235, 255) if glowing else (84, 140, 184)
        p1 = (sx + math.cos(a) * (R - 12), sy + math.sin(a) * (R - 12))
        p2 = (sx + math.cos(a) * (R + 1), sy + math.sin(a) * (R + 1))
        p3 = (sx + math.cos(a + 0.05) * (R - 6), sy + math.sin(a + 0.05) * (R - 6))
        pygame.draw.lines(canvas, c, False, [p1, p3, p2], 2)
    for ang, life in ripples:
        a = ang
        pygame.draw.arc(canvas, (190, 245, 255), (int(sx - R - 6), int(sy - R - 6), (R + 6) * 2, (R + 6) * 2),
                        -a - 0.5 - (1 - life) * 0.4, -a + 0.5 + (1 - life) * 0.4, max(1, int(5 * life)))


def draw_gate(canvas, x, y, t, state, color=(190, 120, 255)):
    """state: open | sealed | locked"""
    shadow(canvas, x, y + 24, 70, 18)
    for sx in (-52, 52):
        pygame.draw.rect(canvas, (96, 98, 116), (int(x + sx - 14), int(y - 70), 28, 100))
        pygame.draw.rect(canvas, (136, 138, 156), (int(x + sx - 18), int(y - 78), 36, 12))
        pygame.draw.rect(canvas, (136, 138, 156), (int(x + sx - 18), int(y + 22), 36, 10))
    pygame.draw.arc(canvas, (136, 138, 156), (int(x - 56), int(y - 112), 112, 104), 0, math.pi, 12)
    if state == "open":
        draw_glow(canvas, x, y - 20, 110, color, 0.7)
        for k in range(5):
            ph = t * 1.4 + k * 0.7
            w = 44 * (0.55 + 0.45 * math.sin(ph))
            pygame.draw.ellipse(canvas, rgb(color, 0.5 + 0.1 * k), (int(x - w), int(y - 70 + k * 6), int(w * 2), 80 - k * 8), 3)
        for k in range(6):
            a = t * 2 + k
            pygame.draw.circle(canvas, (255, 255, 255), (int(x + math.cos(a) * 36 * math.sin(k + 1)), int(y - 30 + math.sin(a * 1.3) * 30)), 2)
    else:
        pygame.draw.rect(canvas, (36, 34, 46), (int(x - 40), int(y - 70), 80, 96))
        c = (120, 60, 60) if state == "sealed" else (90, 90, 110)
        for k in range(-1, 2):
            pygame.draw.line(canvas, c, (int(x - 40), int(y - 40 + k * 26)), (int(x + 40), int(y - 22 + k * 26)), 4)
        pygame.draw.circle(canvas, c, (int(x), int(y - 20)), 12)
        pygame.draw.circle(canvas, (26, 24, 34), (int(x), int(y - 20)), 6)


def draw_portal(canvas, x, y, t, color):
    draw_glow(canvas, x, y, 90, color, 0.6)
    for k in range(4):
        w = 40 - k * 7
        pygame.draw.ellipse(canvas, rgb(color, 0.6 + 0.12 * k), (int(x - w), int(y - w * 0.55), int(w * 2), int(w * 1.1)), 3)
    for k in range(7):
        a = t * 2.2 + k * math.tau / 7
        pygame.draw.circle(canvas, (255, 255, 255), (int(x + math.cos(a) * 34), int(y + math.sin(a) * 18)), 2)


def draw_chest(canvas, x, y, t):
    shadow(canvas, x, y + 14, 24, 8)
    pygame.draw.rect(canvas, (132, 84, 38), (int(x - 20), int(y - 8), 40, 26), border_radius=4)
    pygame.draw.rect(canvas, (104, 66, 30), (int(x - 20), int(y - 8), 40, 26), 2, border_radius=4)
    pygame.draw.rect(canvas, (154, 100, 44), (int(x - 21), int(y - 18), 42, 13), border_radius=6)
    pygame.draw.rect(canvas, GOLD, (int(x - 21), int(y - 12), 42, 4))
    pygame.draw.rect(canvas, GOLD, (int(x - 4), int(y - 6), 8, 10), border_radius=2)
    ph = (t * 0.7) % 1
    draw_glow(canvas, x, y - 8, 46, GOLD, 0.25 + 0.15 * math.sin(t * 3))
    if ph < 0.4:
        pygame.draw.line(canvas, (255, 255, 230), (int(x - 14 + ph * 60), int(y - 17)), (int(x - 8 + ph * 60), int(y - 11)), 2)


def draw_dungeon_door(canvas, x, y, t):
    shadow(canvas, x, y + 22, 52, 14)
    pygame.draw.rect(canvas, (84, 84, 100), (int(x - 44), int(y - 56), 88, 84), border_radius=10)
    pygame.draw.rect(canvas, (14, 12, 22), (int(x - 28), int(y - 40), 56, 68), border_radius=22)
    for k in range(3):
        pygame.draw.rect(canvas, (110, 110, 126), (int(x - 36 + k * 4), int(y + 22 + k * 4), 72 - k * 8, 5))
    draw_glow(canvas, x, y - 6, 60, (190, 100, 255), 0.25 + 0.1 * math.sin(t * 2))


def draw_exit(canvas, x, y, t):
    draw_portal(canvas, x, y, t, (110, 190, 255))


def marker(canvas, x, y, t, kind):
    """kind: '!' new quest, '?' ready to turn in, '.' in progress"""
    bob = math.sin(t * 4) * 3
    col = {"!": GOLD, "?": GREEN, ".": MUTED}[kind]
    img = font(26).render(kind if kind != "." else "…", True, col)
    canvas.blit(img, (int(x - img.get_width() / 2), int(y + bob - img.get_height() / 2)))


def bolt(canvas, a, b, color=(190, 230, 255), seed=0):
    pts = [a]
    n = 7
    rng = random.Random(seed)
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1
    for k in range(1, n):
        f = k / n
        off = rng.uniform(-14, 14)
        pts.append((a[0] + dx * f - dy / ln * off, a[1] + dy * f + dx / ln * off))
    pts.append(b)
    pygame.draw.lines(canvas, color, False, pts, 5)
    pygame.draw.lines(canvas, (255, 255, 255), False, pts, 2)


# ------------------------------------------------------------ hero colors
def recolor_hero(image, index):
    if index == 0:
        return image
    out = image.copy()
    w, h = out.get_size()
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = out.get_at((xx, yy))
            if a and b > r * 1.2 and b > g * 0.95:
                if index == 1:
                    new = (b, int(g * 0.55), int(r * 0.6))
                elif index == 2:
                    new = (int(r * 0.9), b, g)
                elif index == 3:
                    new = (int(b * 0.8), r, b)
                elif index == 4:
                    new = (b, int(b * 0.8), int(r * 0.7))
                else:
                    lum = (r + g + b) // 3
                    new = (int(lum * 0.45), int(lum * 0.45), int(lum * 0.55))
                out.set_at((xx, yy), tuple(min(255, int(v)) for v in new) + (a,))
    return out


_beams = {}


def beam_surface(color):
    key = tuple(color[:3])
    if key not in _beams:
        surf = S(16, 190)
        for i in range(190):
            a = int(150 * (1 - i / 190) ** 1.4)
            pygame.draw.line(surf, (*key, a), (3, i), (12, i))
            pygame.draw.line(surf, (255, 255, 255, a // 2), (7, i), (8, i))
        _beams[key] = surf
    return _beams[key]


def draw_arena_ring(canvas, x, y, R, t, color, intensity=1.0):
    n = 90
    for k in range(n):
        a0 = k * math.tau / n
        a1 = a0 + math.tau / n * 0.62
        p0 = (x + math.cos(a0) * R, y + math.sin(a0) * R)
        p1 = (x + math.cos(a1) * R, y + math.sin(a1) * R)
        if not (-60 < p0[0] < VW + 60 and -60 < p0[1] < VH + 60):
            continue
        glowing = (k + int(t * 3)) % 4 == 0
        c = rgb(color, (1.0 if glowing else 0.55) * intensity)
        pygame.draw.line(canvas, c, p0, p1, 4 if glowing else 2)
        if k % 5 == 0:
            q = (x + math.cos(a0) * (R - 14), y + math.sin(a0) * (R - 14))
            pygame.draw.line(canvas, c, p0, q, 2)


def draw_door(canvas, rect, closed, t):
    r = pygame.Rect(rect)
    if not closed:
        pygame.draw.rect(canvas, (60, 60, 72), r, 2)
        return
    pygame.draw.rect(canvas, (36, 34, 44), r)
    horizontal = r.w > r.h
    for k in range(0, (r.w if horizontal else r.h), 14):
        a, b = ((r.x + k, r.y), (r.x + k, r.bottom)) if horizontal else ((r.x, r.y + k), (r.right, r.y + k))
        pygame.draw.line(canvas, (150, 150, 168), a, b, 4)
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    draw_glow(canvas, r.centerx, r.centery, 40, (255, 60, 60), 0.3 + 0.3 * pulse)
    pygame.draw.rect(canvas, (200, 70, 70), r, 2)


def draw_trap(canvas, rect, phase):
    r = pygame.Rect(rect)
    pygame.draw.rect(canvas, (44, 40, 52), r)
    pygame.draw.rect(canvas, (84, 80, 96), r, 2)
    for ix in range(3):
        for iy in range(3):
            cx, cy = r.x + 12 + ix * 28, r.y + 12 + iy * 28
            if phase == "active":
                pygame.draw.polygon(canvas, (214, 214, 226), [(cx - 6, cy + 8), (cx, cy - 14), (cx + 6, cy + 8)])
            else:
                pygame.draw.circle(canvas, (255, 200, 80) if phase == "warn" else (30, 28, 36), (cx, cy), 4)


def draw_stairs(canvas, x, y, t, color=(150, 230, 255)):
    shadow(canvas, x, y + 20, 50, 14)
    for k in range(5):
        w = 80 - k * 10
        pygame.draw.rect(canvas, rgb((88, 90, 108), 1 - 0.12 * k), (int(x - w / 2), int(y - 16 + k * 9), w, 10))
    draw_glow(canvas, x, y + 6, 70, color, 0.35 + 0.15 * math.sin(t * 3))
    pygame.draw.polygon(canvas, color, [(x - 10, y - 30), (x + 10, y - 30), (x, y - 14)])


def draw_altar(canvas, x, y, t, color=(255, 220, 130)):
    shadow(canvas, x, y + 16, 30, 9)
    pygame.draw.rect(canvas, (110, 112, 132), (int(x - 24), int(y - 4), 48, 22), border_radius=3)
    pygame.draw.rect(canvas, (140, 142, 162), (int(x - 30), int(y - 10), 60, 10), border_radius=3)
    bob = math.sin(t * 2.5) * 4
    draw_glow(canvas, x, y - 34 + bob, 60, color, 0.6)
    pygame.draw.circle(canvas, color, (int(x), int(y - 34 + bob)), 9)
    pygame.draw.circle(canvas, (255, 255, 255), (int(x - 3), int(y - 37 + bob)), 3)


def draw_stall(canvas, x, y, t):
    shadow(canvas, x, y + 18, 40, 10)
    pygame.draw.rect(canvas, (120, 80, 48), (int(x - 38), int(y - 6), 76, 26), border_radius=4)
    pygame.draw.polygon(canvas, (180, 70, 70), [(x - 46, y - 8), (x - 34, y - 34), (x + 34, y - 34), (x + 46, y - 8)])
    for k, c in enumerate(((120, 220, 150), (255, 210, 110), (150, 190, 255))):
        pygame.draw.circle(canvas, c, (int(x - 22 + k * 22), int(y - 12)), 6)
    draw_glow(canvas, x, y - 10, 70, (255, 220, 150), 0.25)
