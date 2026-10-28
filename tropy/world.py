"""Terrain generation: biomes, rivers, bridges, props and set pieces."""
import math
import random

import pygame

from .common import *
from .content import ZONE_LAYOUT
from . import art

SOLID = (3, 4)
OX, OY = (WW - 1900) // 2, (WH - 1300) // 2
BX0, BY0, BX1, BY1 = OX + 30, OY + 30, OX + 1870, OY + 1270
ARENA_R = 430

PALETTE = {
    "forest": {0: (50, 88, 54), 1: (40, 74, 48), 2: (128, 104, 72), 3: (44, 96, 150), 4: (72, 68, 62), 5: (134, 98, 60)},
    "ruins": {0: (64, 64, 76), 1: (55, 55, 67), 2: (96, 92, 100), 3: (14, 12, 24), 4: (92, 92, 110), 5: (120, 120, 136)},
    "ash": {0: (72, 50, 44), 1: (60, 40, 36), 2: (108, 84, 72), 3: (214, 86, 30), 4: (44, 36, 40), 5: (62, 56, 60)},
}
PROP_KINDS = {
    "forest": [("tree", 0, 28), ("tree", 1, 22), ("tree", 2, 22), ("rock", 0, 12), ("bush", 0, 8)],
    "ruins": [("pillar", 0, 14), ("pillar", 1, 14), ("rubble", 0, 18), ("statue", 0, 8), ("rock", 0, 16), ("deadtree", 0, 12)],
    "ash": [("deadtree", 0, 24), ("spike", 0, 30), ("boulder", 0, 28), ("rubble", 0, 10), ("rock", 0, 8)],
}
PROP_RADIUS = {"tree": 20, "rock": 24, "bush": 14, "pillar": 16, "rubble": 22, "statue": 18,
               "deadtree": 14, "spike": 20, "boulder": 28, "hut": 46, "tent": 40, "crate": 14}


def _h(seed, ix, iy):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n ^ (n >> 16)) / 0xFFFFFFFF


def vnoise(seed, x, y):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _h(seed, ix, iy), _h(seed, ix + 1, iy)
    c, d = _h(seed, ix, iy + 1), _h(seed, ix + 1, iy + 1)
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy


def fbm(seed, x, y):
    return (vnoise(seed, x, y) + 0.5 * vnoise(seed + 7, x * 2, y * 2) + 0.25 * vnoise(seed + 13, x * 4, y * 4)) / 1.75


class World:
    def __init__(self, key, zi):
        self.key, self.zi = key, zi
        self.biome = ZONES[zi]["biome"]
        self.gw, self.gh = WW // CELL, WH // CELL
        self.grid = [bytearray(self.gw) for _ in range(self.gh)]
        self.props = []      # (x, y, r, kind, var); r == 0 -> decoration only
        self.rects = []      # blocking walls (x, y, w, h)
        self.decor = []      # baked (x, y, kind, var)
        self.pieces = []     # animated pieces (kind, x, y, seed)
        self.pois = []
        self.camp_xy = None
        self.arena_xy = None
        self.static_rects = []
        self.rooms = []
        self.doors = []
        self.traps = []
        self.biome_style = "zone"
        self._buckets = {}

    def rebuild_rects(self):
        self.rects = self.static_rects + [d["rect"] for d in self.doors if d["closed"]]

    def set_doors(self, room, closed):
        for d in self.doors:
            if room in d["rooms"]:
                d["closed"] = closed
        self.rebuild_rects()

    # ---- queries
    def code(self, x, y):
        cx, cy = int(x // CELL), int(y // CELL)
        if 0 <= cx < self.gw and 0 <= cy < self.gh:
            return self.grid[cy][cx]
        return 4

    def index_props(self):
        self._buckets = {}
        for p in self.props:
            if p[2] > 0:
                self._buckets.setdefault((int(p[0] // 128), int(p[1] // 128)), []).append(p)

    def blocked(self, x, y, radius):
        grid = self.grid
        gw, gh = self.gw, self.gh
        for px, py in ((x, y), (x - radius, y), (x + radius, y), (x, y - radius * 0.6), (x, y + radius * 0.6)):
            cx, cy = int(px // CELL), int(py // CELL)
            if not (0 <= cx < gw and 0 <= cy < gh) or grid[cy][cx] in SOLID:
                return True
        bx, by = int(x // 128), int(y // 128)
        for ix in range(bx - 1, bx + 2):
            for iy in range(by - 1, by + 2):
                for ox, oy, rr, _, _ in self._buckets.get((ix, iy), ()):
                    if (x - ox) ** 2 + (y - oy) ** 2 < (radius + rr) ** 2:
                        return True
        for rx, ry, rw, rh in self.rects:
            nx, ny = clamp(x, rx, rx + rw), clamp(y, ry, ry + rh)
            if (x - nx) ** 2 + (y - ny) ** 2 < radius * radius:
                return True
        return False

    def props_blocked(self, x, y, radius):
        bx, by = int(x // 128), int(y // 128)
        for ix in range(bx - 1, bx + 2):
            for iy in range(by - 1, by + 2):
                for ox, oy, rr, _, _ in self._buckets.get((ix, iy), ()):
                    if (x - ox) ** 2 + (y - oy) ** 2 < (radius + rr) ** 2:
                        return True
        for rx, ry, rw, rh in self.rects:
            nx, ny = clamp(x, rx, rx + rw), clamp(y, ry, ry + rh)
            if (x - nx) ** 2 + (y - ny) ** 2 < radius * radius:
                return True
        return False

    def free_spot(self, rng, margin=95, avoid=(), tries=120, radius=18):
        for _ in range(tries):
            x, y = rng.randint(margin, WW - margin), rng.randint(margin, WH - margin)
            if not self.blocked(x, y, radius) and all(distance(x, y, a, b) > r for a, b, r in avoid):
                return x, y
        return None


def _stamp(world, x, y, radius):
    cx0, cx1 = int((x - radius) // CELL), int((x + radius) // CELL)
    cy0, cy1 = int((y - radius) // CELL), int((y + radius) // CELL)
    for cy in range(max(0, cy0), min(world.gh, cy1 + 1)):
        for cx in range(max(0, cx0), min(world.gw, cx1 + 1)):
            if distance(cx * CELL + CELL / 2, cy * CELL + CELL / 2, x, y) <= radius:
                cur = world.grid[cy][cx]
                world.grid[cy][cx] = 5 if cur == 3 else 2


def _path(world, rng, a, b, width=52):
    ax, ay = a
    bx, by = b
    length = distance(ax, ay, bx, by)
    steps = max(2, int(length // 22))
    nx, ny = direction(-(by - ay), bx - ax)
    sway = rng.uniform(-90, 90)
    for i in range(steps + 1):
        f = i / steps
        off = math.sin(f * math.pi) * sway + math.sin(f * 9) * 10
        _stamp(world, ax + (bx - ax) * f + nx * off, ay + (by - ay) * f + ny * off, width)


def _clear(world, x, y, radius):
    for cy in range(max(0, int((y - radius) // CELL)), min(world.gh, int((y + radius) // CELL) + 1)):
        for cx in range(max(0, int((x - radius) // CELL)), min(world.gw, int((x + radius) // CELL) + 1)):
            if distance(cx * CELL + CELL / 2, cy * CELL + CELL / 2, x, y) <= radius:
                world.grid[cy][cx] = 0


def zone_pois(zi):
    L = ZONE_LAYOUT[zi]
    cx, cy = L["camp"]
    local = ["elder", "liara", "kael"][zi]
    field = ["hunter", "valdo", "rud"][zi]
    pois = [
        {"kind": "camp", "x": cx - 5, "y": cy + 22},
        {"kind": "npc", "npc": "merchant", "x": cx + 105, "y": cy + 22},
        {"kind": "npc", "npc": "smith", "x": cx - 118, "y": cy - 30},
        {"kind": "npc", "npc": local, "x": cx + 18, "y": cy - 108},
        {"kind": "npc", "npc": field, "x": L["field"][0], "y": L["field"][1]},
    ]
    for v, (x, y) in enumerate(L["dungeons"]):
        pois.append({"kind": "entrance", "x": x, "y": y, "dg": "dg%d_%d" % (zi, v)})
    for i, (x, y) in enumerate(L["chests"]):
        pois.append({"kind": "chest", "x": x, "y": y, "id": i})
    gx, gy = L["gate_next"]
    pois.append({"kind": "gate_next" if zi < 2 else "portal", "x": gx, "y": gy})
    if L["gate_back"]:
        pois.append({"kind": "gate_back", "x": L["gate_back"][0], "y": L["gate_back"][1]})
    return pois


def zone_camp(zi):
    return ZONE_LAYOUT[zi]["camp"]


def _blob(w, seed, bx, by, rx, ry, code):
    for cy in range(w.gh):
        for cx in range(w.gw):
            px, py = cx * CELL + 20, cy * CELL + 20
            d = ((px - bx) / rx) ** 2 + ((py - by) / ry) ** 2
            if d < 1 - 0.25 * vnoise(seed + 3, cx * 0.4, cy * 0.4):
                w.grid[cy][cx] = code


def _terrain_forest(w, rng, seed):
    for _ in range(7):
        _blob(w, seed, rng.randint(300, WW - 300), rng.randint(300, WH - 300), rng.randint(70, 150), rng.randint(60, 110), 3 if rng.random() < 0.75 else 4)
    base, phase = WH * 0.33, rng.uniform(0, 6)
    for cx in range(w.gw):
        cyc = base + 60 * math.sin(cx * 0.16 + phase) + 25 * math.sin(cx * 0.5)
        half = 1.5 + 0.7 * math.sin(cx * 0.3)
        for cy in range(w.gh):
            if abs(cy * CELL + 20 - cyc) < half * CELL:
                w.grid[cy][cx] = 3


def _terrain_ruins(w, rng, seed):
    for by in range(0, w.gh - 6, 11):
        for bx in range(0, w.gw - 8, 13):
            x0, y0, x1, y1 = bx + 2, by + 2, bx + 11, by + 9
            kind = rng.choices(["house", "rubble", "plaza"], weights=[55, 25, 20])[0]
            if kind == "house":
                gaps = rng.sample(["n", "s", "e", "w"], 2)
                for cy in range(y0, y1 + 1):
                    for cx in range(x0, x1 + 1):
                        if cx in (x0, x1) or cy in (y0, y1):
                            gap = ((cy == y0 and "n" in gaps and abs(cx - (x0 + x1) // 2) <= 1) or
                                   (cy == y1 and "s" in gaps and abs(cx - (x0 + x1) // 2) <= 1) or
                                   (cx == x0 and "w" in gaps and abs(cy - (y0 + y1) // 2) <= 1) or
                                   (cx == x1 and "e" in gaps and abs(cy - (y0 + y1) // 2) <= 1))
                            if not gap and cy < w.gh and cx < w.gw:
                                w.grid[cy][cx] = 4
            elif kind == "rubble":
                for cy in range(y0, y1 + 1):
                    for cx in range(x0, x1 + 1):
                        if rng.random() < 0.18 and cy < w.gh and cx < w.gw:
                            w.grid[cy][cx] = 4
    for cy in range(w.gh):
        for cx in range(w.gw):
            if abs(cx * w.gh / w.gw + cy - w.gh - 2 * math.sin(cx * 0.3)) < 2.2:
                w.grid[cy][cx] = 3


def _terrain_ash(w, rng, seed):
    for cy in range(w.gh):
        for cx in range(w.gw):
            if abs(fbm(seed + 21, cx * 0.08, cy * 0.08) - 0.5) < 0.028:
                w.grid[cy][cx] = 4
    for _ in range(6):
        _blob(w, seed, rng.randint(300, WW - 300), rng.randint(300, WH - 300), rng.randint(70, 140), rng.randint(60, 100), 3)
    for cy in range(w.gh):
        yy = cy * CELL + 20
        cxc = (WW * 0.40 + 130 * math.sin(yy * 0.004) + 60 * math.sin(yy * 0.011)) / CELL
        for cx in range(w.gw):
            if abs(cx - cxc) < 1.7 + 0.5 * math.sin(cy * 0.4):
                w.grid[cy][cx] = 3


def build_zone(zi):
    key = "zone" + str(zi)
    L = ZONE_LAYOUT[zi]
    w = World(key, zi)
    seed = 1000 + zi * 97
    rng = random.Random(seed)
    w.pois = zone_pois(zi)
    w.camp_xy = L["camp"]
    w.arena_xy = L["arena"]
    biome = w.biome
    for cy in range(w.gh):
        for cx in range(w.gw):
            w.grid[cy][cx] = 1 if fbm(seed, cx * 0.11, cy * 0.11) > 0.56 else 0
    {"forest": _terrain_forest, "ruins": _terrain_ruins, "ash": _terrain_ash}[biome](w, rng, seed)
    for cy in range(w.gh):
        for cx in range(w.gw):
            edge = min(cx, cy, w.gw - 1 - cx, w.gh - 1 - cy)
            if edge < 1 + int(vnoise(seed + 5, cx * 0.5, cy * 0.5) * 2.4):
                w.grid[cy][cx] = 4
    camp, arena = L["camp"], L["arena"]
    for poi in w.pois:
        _clear(w, poi["x"], poi["y"], 130)
    _clear(w, camp[0], camp[1], 250)
    _clear(w, arena[0], arena[1], ARENA_R + 40)
    for poi in w.pois:
        if poi["kind"] in ("entrance", "chest", "gate_back", "gate_next", "portal") or (poi["kind"] == "npc" and poi["npc"] in ("hunter", "valdo", "rud")):
            _path(w, rng, camp, (poi["x"], poi["y"]))
    _path(w, rng, camp, arena, 62)
    gate = L["gate_next"]
    _path(w, rng, arena, gate, 62)
    # arena pillars mark the fighting ring
    for k in range(10):
        a = math.radians(k * 36 + 18)
        px, py = arena[0] + math.cos(a) * ARENA_R, arena[1] + math.sin(a) * ARENA_R
        if distance(px, py, gate[0], gate[1]) > 150 and w.code(px, py) not in SOLID:
            w.props.append((px, py, 16, "statue" if zi == 1 else "pillar", 0))
    cx, cy = camp
    w.props += [(cx - 125, cy + 62, 30, "tent", 0), (cx + 138, cy - 62, 30, "tent", 0),
                (cx + 150, cy + 48, 14, "crate", 0), (cx + 134, cy + 62, 14, "crate", 0)]
    for k, ang in enumerate((45, 135, 225, 315)):
        a = math.radians(ang)
        w.pieces.append(("obelisk", cx + math.cos(a) * (CAMP_R + 6), cy + math.sin(a) * (CAMP_R + 6) * 0.9, k))
    for k, ang in enumerate((0, 90, 180, 270)):
        a = math.radians(ang)
        w.pieces.append(("torch", cx + math.cos(a) * (CAMP_R - 12), cy + math.sin(a) * (CAMP_R - 12) * 0.9, k))
    w.pieces += [("campfire", cx - 5, cy + 22, 0), ("banner", cx - 70, cy + 150, 0), ("banner", cx + 74, cy + 150, 1)]
    ox, oy = L["field"]
    w.props += [(ox - 80, oy - 40, 46, "hut", 0), (ox + 70, oy + 30, 14, "crate", 0)]
    w.pieces += [("campfire", ox + 10, oy + 40, 5), ("torch", ox - 40, oy + 20, 3)]
    hx, hy = L["chests"][1]
    w.static_rects += [(hx - 130, hy - 120, 260, 20), (hx - 130, hy - 120, 20, 150), (hx + 110, hy - 120, 20, 150),
                       (hx - 130, hy + 30, 90, 20), (hx + 40, hy + 30, 90, 20)]
    w.pieces += [("torch", hx - 96, hy + 20, 7), ("torch", hx + 96, hy + 20, 8)]
    w.rebuild_rects()
    avoid = [(p["x"], p["y"], 120) for p in w.pois] + [(camp[0], camp[1], 280), (arena[0], arena[1], ARENA_R + 20), (ox, oy, 140)]
    table = PROP_KINDS[biome]
    total = sum(t[2] for t in table)
    tries = count = 0
    while count < 170 and tries < 3500:
        tries += 1
        x, y = rng.randint(80, WW - 80), rng.randint(80, WH - 80)
        code = w.code(x, y)
        if code not in (0, 1):
            continue
        if biome == "forest" and code == 0 and fbm(seed + 9, x * 0.004, y * 0.004) < 0.38 and rng.random() < 0.6:
            continue
        if any(distance(x, y, a, b) < r for a, b, r in avoid):
            continue
        roll = rng.uniform(0, total)
        for kind, var, wt in table:
            roll -= wt
            if roll <= 0:
                break
        r = PROP_RADIUS[kind]
        if any(distance(x, y, p[0], p[1]) < r + p[2] + 22 for p in w.props if p[2] > 0):
            continue
        if any(w.code(x + dx, y + dy) in SOLID for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r))):
            continue
        w.props.append((x, y, r, kind, var))
        count += 1
    dk = {"forest": ["flower", "tuft", "mushroom", "pebble"], "ruins": ["crack", "pebble", "bone", "moss"],
          "ash": ["ember", "crack", "ashpile", "pebble"]}[biome]
    for _ in range(1500):
        x, y = rng.randint(50, WW - 50), rng.randint(50, WH - 50)
        if w.code(x, y) in (0, 1):
            w.decor.append((x, y, rng.choice(dk), rng.randint(0, 3)))
    w.index_props()
    return w


# ------------------------------------------------ room-based instances
SLOT_W, SLOT_H, SLOT_COLS, SLOT_ROWS = 16, 13, 5, 4


def _walk_slots(rng, n):
    for _ in range(300):
        x, y = rng.randrange(SLOT_COLS), rng.randrange(SLOT_ROWS)
        path = [(x, y)]
        while len(path) < n:
            options = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                       if 0 <= x + dx < SLOT_COLS and 0 <= y + dy < SLOT_ROWS and (x + dx, y + dy) not in path]
            if not options:
                break
            x, y = rng.choice(options)
            path.append((x, y))
        if len(path) == n:
            return path
    return [(i % SLOT_COLS, i // SLOT_COLS) for i in range(n)]


def _carve(w, cx, cy, code, half=1):
    for yy in range(cy - half, cy + half + 1):
        for xx in range(cx - half, cx + half + 1):
            if 0 <= xx < w.gw and 0 <= yy < w.gh:
                w.grid[yy][xx] = code


def build_rooms(key, zi, kinds, seed, style="cave", cleared=False, biome=None):
    """Room-based map: start room + one room per entry in kinds, joined by corridors."""
    w = World(key, zi)
    if biome:
        w.biome = biome
    w.biome_style = style
    rng = random.Random(seed)
    solid = 3 if style == "bridge" else 4
    path_code = 5 if style == "bridge" else 0
    for row in w.grid:
        for i in range(w.gw):
            row[i] = solid
    slots = _walk_slots(rng, len(kinds) + 1)
    rects = []
    for sx, sy in slots:
        rw, rh = rng.randint(9, 13), rng.randint(7, 10)
        x0 = sx * SLOT_W + (SLOT_W - rw) // 2 + rng.randint(-1, 1)
        y0 = sy * SLOT_H + 1 + (SLOT_H - rh) // 2 + rng.randint(-1, 1)
        x0, y0 = clamp(x0, 2, w.gw - rw - 2), clamp(y0, 2, w.gh - rh - 2)
        rects.append((int(x0), int(y0), rw, rh))
        for yy in range(int(y0), int(y0) + rh):
            for xx in range(int(x0), int(x0) + rw):
                w.grid[yy][xx] = 1 if rng.random() < 0.2 else 0
    centers = [(x + rw // 2, y + rh // 2) for x, y, rw, rh in rects]
    for i in range(len(rects) - 1):
        (ax, ay), (bx, by) = centers[i], centers[i + 1]
        step = 1 if bx >= ax else -1
        for xx in range(ax, bx + step, step):
            _carve(w, xx, ay, path_code)
        step = 1 if by >= ay else -1
        for yy in range(ay, by + step, step):
            _carve(w, bx, yy, path_code)
    for i, (x, y, rw, rh) in enumerate(rects):
        kind = "start" if i == 0 else kinds[i - 1]
        w.rooms.append({"kind": kind, "rect": (x * CELL, y * CELL, rw * CELL, rh * CELL),
                        "center": ((x + rw / 2) * CELL, (y + rh / 2) * CELL), "state": "cleared" if (i == 0 or cleared) else "idle",
                        "cells": (x, y, rw, rh)})
    # doors where corridors leave rooms
    for i in range(len(rects) - 1):
        (ax, ay), (bx, by) = centers[i], centers[i + 1]
        cells = []
        step = 1 if bx >= ax else -1
        cells += [(xx, ay) for xx in range(ax, bx + step, step)]
        step = 1 if by >= ay else -1
        cells += [(bx, yy) for yy in range(ay, by + step, step)]
        for room, seq in ((i, cells), (i + 1, cells[::-1])):
            x, y, rw, rh = rects[room]
            prev = seq[0]
            for cell in seq:
                if not (x <= cell[0] < x + rw and y <= cell[1] < y + rh):
                    dx, dy = cell[0] - prev[0], cell[1] - prev[1]
                    if dx:
                        rect = (cell[0] * CELL, (cell[1] - 1) * CELL, CELL, 3 * CELL)
                    else:
                        rect = ((cell[0] - 1) * CELL, cell[1] * CELL, 3 * CELL, CELL)
                    w.doors.append({"rect": rect, "closed": False, "rooms": (room,)})
                    break
                prev = cell
    # decorations / obstacles
    for i, room in enumerate(w.rooms):
        x, y, rw, rh = room["rect"]
        cx, cy = room["center"]
        for tx, ty in ((x + 30, y + 30), (x + rw - 30, y + 30)):
            w.pieces.append(("torch", tx, ty, i))
        if room["kind"] in ("combat", "trap") and i:
            for _ in range(rng.randint(2, 4)):
                px, py = rng.randint(int(x + 100), int(x + rw - 100)), rng.randint(int(y + 90), int(y + rh - 90))
                if distance(px, py, cx, cy) > 90:
                    w.props.append((px, py, 18, "pillar", rng.randint(0, 1)))
        if room["kind"] == "trap":
            for _ in range(rng.randint(6, 9)):
                tx = rng.randint(int(x + 60), int(x + rw - 140)) // CELL * CELL
                ty = rng.randint(int(y + 60), int(y + rh - 140)) // CELL * CELL
                w.traps.append([tx, ty, CELL * 2, CELL * 2, rng.random() * 3])
    w.index_props()
    w.rebuild_rects()
    for _ in range(600):
        x, y = rng.randint(50, WW - 50), rng.randint(50, WH - 50)
        if w.code(x, y) in (0, 1):
            w.decor.append((x, y, rng.choice(["crack", "pebble", "bone"]), rng.randint(0, 3)))
    return w


def build_dungeon(did, info, cleared=False):
    zi = info["zone"]
    w = build_rooms(did, zi, info["kinds"], info["seed"], "cave", cleared)
    w.pois = [{"kind": "exit", "x": w.rooms[0]["center"][0], "y": w.rooms[0]["center"][1]}]
    return w


def build_pass(index, info, cleared=False):
    zi = index  # visual biome: first pass is forest, second is ruins
    w = build_rooms("pass%d" % index, zi, info["kinds"], info["seed"], info["style"], cleared)
    a, b = w.rooms[0]["center"], w.rooms[-1]["center"]
    w.pois = [{"kind": "exit_back", "x": a[0], "y": a[1]}, {"kind": "exit_fwd", "x": b[0], "y": b[1]}]
    return w


def build_final():
    w = World("final", 2)
    w.biome = "ash"
    for cy in range(w.gh):
        for cx in range(w.gw):
            px, py = cx * CELL + 20, cy * CELL + 20
            inside = ((px - WW / 2) / 880) ** 2 + ((py - 1130) / 600) ** 2 < 1
            w.grid[cy][cx] = (1 if (cx + cy) % 7 == 0 else 0) if inside else 3
    w.pois = [{"kind": "exit", "x": WW / 2, "y": 1560}]
    for k in range(8):
        a = k * math.tau / 8
        w.pieces.append(("torch", WW / 2 + math.cos(a) * 760, 1130 + math.sin(a) * 500, k))
    rng = random.Random(99)
    for _ in range(500):
        x, y = rng.randint(50, WW - 50), rng.randint(50, WH - 50)
        if w.code(x, y) in (0, 1):
            w.decor.append((x, y, rng.choice(["crack", "ember"]), rng.randint(0, 3)))
    w.index_props()
    return w


def paint_decor(surf, kind, x, y, var):
    x, y = int(x), int(y)
    if kind == "flower":
        col = [(240, 220, 90), (240, 130, 160), (170, 160, 255), (255, 255, 255)][var]
        for dx, dy in ((0, 0), (5, 3), (-4, 4)):
            pygame.draw.circle(surf, col, (x + dx, y + dy), 2)
            pygame.draw.line(surf, (40, 90, 46), (x + dx, y + dy + 2), (x + dx, y + dy + 7), 1)
    elif kind == "tuft":
        for dx in (-4, 0, 4):
            pygame.draw.line(surf, (74, 128, 70), (x + dx, y + 6), (x + dx * 2, y - 2), 2)
    elif kind == "mushroom":
        pygame.draw.rect(surf, (230, 220, 200), (x - 1, y, 3, 5))
        pygame.draw.ellipse(surf, (200, 70, 70), (x - 5, y - 4, 10, 6))
        pygame.draw.circle(surf, (255, 240, 240), (x - 1, y - 2), 1)
    elif kind == "pebble":
        pygame.draw.ellipse(surf, (110, 110, 118), (x - 4, y - 2, 8, 5))
        pygame.draw.ellipse(surf, (150, 150, 158), (x - 2, y - 2, 4, 2))
    elif kind == "crack":
        pygame.draw.lines(surf, (30, 28, 38), False, [(x, y), (x + 8, y + 5), (x + 6, y + 12), (x + 15, y + 15)], 2)
    elif kind == "bone":
        pygame.draw.line(surf, (214, 208, 190), (x - 7, y), (x + 7, y + 3), 3)
        pygame.draw.circle(surf, (214, 208, 190), (x - 8, y), 3)
        pygame.draw.circle(surf, (214, 208, 190), (x + 8, y + 3), 3)
    elif kind == "moss":
        pygame.draw.ellipse(surf, (70, 104, 70), (x - 8, y - 4, 16, 8))
    elif kind == "ember":
        pygame.draw.circle(surf, (255, 130 + var * 20, 50), (x, y), 2)
    elif kind == "ashpile":
        pygame.draw.ellipse(surf, (110, 100, 100), (x - 9, y - 4, 18, 8))
        pygame.draw.ellipse(surf, (140, 130, 130), (x - 5, y - 4, 8, 4))


def bake(world):
    """Render the whole ground layer once."""
    surf = pygame.Surface((WW, WH))
    pal = PALETTE[world.biome]
    for cy in range(world.gh):
        row = world.grid[cy]
        for cx in range(world.gw):
            code = row[cx]
            base = pal[code]
            v = int((_h(5, cx, cy) - 0.5) * 12)
            col = tuple(int(clamp(c + v, 0, 255)) for c in base)
            pygame.draw.rect(surf, col, (cx * CELL, cy * CELL, CELL, CELL))
            if code == 5:
                for k in range(0, CELL, 10):
                    pygame.draw.line(surf, rgb(base, 0.7), (cx * CELL, cy * CELL + k), (cx * CELL + CELL, cy * CELL + k), 1)
            elif code in SOLID:
                for dx, dy, ex, ey in ((0, -1, 0, 0), (0, 1, 0, CELL - 5), (-1, 0, 0, 0), (1, 0, CELL - 5, 0)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < world.gw and 0 <= ny < world.gh and world.grid[ny][nx] not in SOLID:
                        edge = rgb(base, 1.5, 24) if code == 3 else rgb(base, 0.6)
                        if dx == 0:
                            pygame.draw.rect(surf, edge, (cx * CELL, cy * CELL + ey, CELL, 5))
                        else:
                            pygame.draw.rect(surf, edge, (cx * CELL + ex, cy * CELL, 5, CELL))
    if world.camp_xy:
        cx, cy = int(world.camp_xy[0]), int(world.camp_xy[1])
        pygame.draw.circle(surf, (86, 82, 80), (cx, cy), CAMP_R + 38)
        pygame.draw.circle(surf, (104, 100, 98), (cx, cy), CAMP_R + 28)
        rng = random.Random(11)
        for _ in range(120):
            a, d = rng.uniform(0, math.tau), rng.uniform(0, CAMP_R + 26)
            px, py = cx + math.cos(a) * d, cy + math.sin(a) * d
            pygame.draw.circle(surf, (116 + rng.randint(-10, 10),) * 3, (int(px), int(py)), rng.randint(6, 14), 1)
        pygame.draw.circle(surf, (70, 66, 66), (cx, cy), CAMP_R + 38, 4)
    for x, y, kind, var in world.decor:
        paint_decor(surf, kind, x, y, var)
    return surf.convert()
