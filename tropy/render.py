"""World rendering (mixin for Game)."""
import math
import random

import pygame

from .common import *
from .content import *
from . import art, world as W


class RenderMixin:
    # ---------------------------------------------------------- sprites
    def sprite(self, name, x, y, size, flip=False):
        if name not in self.sprites:
            return False
        w, h = size if isinstance(size, tuple) else (size, size)
        w, h = max(1, int(w)), max(1, int(h))
        key = (name, w, h, flip)
        if key not in self.sprite_cache:
            if len(self.sprite_cache) > 700:
                self.sprite_cache.clear()
            source = self.sprites[name]
            if w >= source.get_width():
                image = pygame.transform.scale(source, (w, h))
            else:
                image = pygame.transform.smoothscale(source, (w, h))
            self.sprite_cache[key] = pygame.transform.flip(image, flip, False) if flip else image
        image = self.sprite_cache[key]
        self.canvas.blit(image, image.get_rect(center=(int(x), int(y))))
        return True

    def hero_sprite_name(self, base, char=None):
        c = self.p.get("char", 0) if char is None else char
        return "char{}_{}".format(c, base.split("_")[1])

    def camera(self):
        cx = clamp(self.p["x"] - VW / 2, 0, WW - VW)
        cy = clamp(self.p["y"] - VH / 2, 0, WH - VH)
        amp = self.shake * self.settings["shake"]
        if amp > 0.3:
            cx = clamp(cx + random.uniform(-amp, amp), 0, WW - VW)
            cy = clamp(cy + random.uniform(-amp, amp), 0, WH - VH)
        return cx, cy

    def terrain_surface(self):
        key = self.area
        if key not in self.terrain_cache:
            if len(self.terrain_cache) >= 2:
                self.terrain_cache.pop(next(iter(self.terrain_cache)))
            self.terrain_cache[key] = W.bake(self.world())
        return self.terrain_cache[key]

    def mini_terrain(self, size):
        key = (self.area, size)
        if key not in self.mini_cache:
            if len(self.mini_cache) > 6:
                self.mini_cache.clear()
            self.mini_cache[key] = pygame.transform.smoothscale(self.terrain_surface(), size)
        return self.mini_cache[key]

    # ------------------------------------------------------------ world
    def poi_state(self, poi):
        zi = self.zone_index()
        kind = poi["kind"]
        if kind == "gate_next":
            return "open" if self.p["bosses"][zi] else "sealed"
        if kind == "portal":
            return "open" if all(self.p["bosses"]) else "sealed"
        return "open"

    def draw_world(self):
        t = self.time
        cx, cy = self.camera()
        icx, icy = int(cx), int(cy)
        world = self.world()
        self.canvas.blit(self.terrain_surface(), (0, 0), pygame.Rect(icx, icy, VW, VH))
        self.draw_water_shimmer(world, icx, icy, t)
        for rx, ry, rw, rh in world.static_rects:
            if rx - icx < VW and rx + rw - icx > 0 and ry - icy < VH and ry + rh - icy > -20:
                art.draw_wall(self.canvas, (rx - icx, ry - icy, rw, rh), world.biome if self.surface() else "ruins")
        for d in world.doors:
            rx, ry, rw, rh = d["rect"]
            if -80 < rx - icx < VW + 80 and -80 < ry - icy < VH + 80:
                art.draw_door(self.canvas, (rx - icx, ry - icy, rw, rh), d["closed"], t)
        for tr in world.traps:
            if -80 < tr[0] - icx < VW + 80 and -80 < tr[1] - icy < VH + 80:
                art.draw_trap(self.canvas, (tr[0] - icx, tr[1] - icy, tr[2], tr[3]), self.trap_phase(tr))
        camp = world.camp_xy
        if camp:
            art.draw_camp_ground(self.canvas, camp[0] - icx, camp[1] - icy, t, self.ripples)
        if world.arena_xy and self.surface():
            self.draw_arena(world, icx, icy, t)
        for h in self.hazards:
            self.draw_hazard(h, icx, icy)

        items = []
        margin = 120
        for p in world.props:
            if -margin < p[0] - icx < VW + margin and -margin < p[1] - icy < VH + margin:
                items.append((p[1], "prop", p))
        for piece in world.pieces:
            if -margin < piece[1] - icx < VW + margin and -margin < piece[2] - icy < VH + margin:
                items.append((piece[2], "piece", piece))
        for poi in self.available_pois():
            if poi["kind"] != "camp" and -margin < poi["x"] - icx < VW + margin and -margin < poi["y"] - icy < VH + margin:
                items.append((poi["y"], "poi", poi))
        for drop in self.current()["drops"]:
            items.append((drop["y"], "drop", drop))
        for e in self.current()["enemies"]:
            if -margin < e.x - icx < VW + margin and -margin < e.y - icy < VH + margin:
                items.append((e.y, "enemy", e))
        for d in self.deaths:
            items.append((d[1], "death", d))
        for g in self.ghosts:
            items.append((g[1] - 1, "ghost", g))
        items.append((self.p["y"], "hero", None))
        for _, kind, obj in sorted(items, key=lambda row: row[0]):
            if kind == "prop":
                art.draw_prop(self.canvas, obj[3], obj[4], obj[0] - icx, obj[1] - icy)
            elif kind == "piece":
                self.draw_piece(obj, icx, icy, t)
            elif kind == "poi":
                self.draw_poi(obj, icx, icy, t)
            elif kind == "drop":
                self.draw_drop(obj, icx, icy, t)
            elif kind == "enemy":
                self.draw_enemy(obj, icx, icy, t)
            elif kind == "death":
                self.draw_death(obj, icx, icy)
            elif kind == "ghost":
                self.sprite(obj[2], obj[0] - icx, obj[1] - icy, obj[3], obj[4])
            else:
                self.draw_hero(icx, icy)

        for b in self.bullets:
            x, y = int(b["x"] - icx), int(b["y"] - icy)
            if -20 < x < VW + 20 and -20 < y < VH + 20:
                art.draw_glow(self.canvas, x, y, int(b["r"] * 3.4), b["color"], 0.8)
                pygame.draw.circle(self.canvas, b["color"], (x, y), int(b["r"]))
                pygame.draw.circle(self.canvas, (255, 255, 255), (x, y), max(1, int(b["r"] * 0.45)))
        for shot in self.projectiles:
            x, y = int(shot["x"] - icx), int(shot["y"] - icy)
            if shot.get("arrow"):
                pygame.draw.line(self.canvas, (235, 225, 200), (x - shot["dx"] * 18, y - shot["dy"] * 18), (x, y), 3)
                pygame.draw.polygon(self.canvas, (210, 214, 226), [(x + shot["dx"] * 7, y + shot["dy"] * 7),
                                    (x - shot["dy"] * 4, y + shot["dx"] * 4), (x + shot["dy"] * 4, y - shot["dx"] * 4)])
                continue
            art.draw_glow(self.canvas, x, y, 26, BLUE, 0.8)
            pygame.draw.circle(self.canvas, BLUE, (x, y), 7)
            pygame.draw.circle(self.canvas, TEXT, (x, y), 3)
        self.draw_fx(icx, icy)
        if not self.settings["lowfx"]:
            self.draw_ambient(icx, icy, t)
        if self.area_kind() in ("dungeon", "pass", "abyss", "final"):
            self.draw_darkness(icx, icy, t)
        if camp:
            art.draw_glow(self.canvas, camp[0] - icx, camp[1] - icy, CAMP_R + 60, (110, 200, 255), 0.12)

    def draw_ambient(self, icx, icy, t):
        biome = self.world().biome
        col, speed, size = {"forest": ((170, 230, 120), (14, 9), 2), "ruins": ((190, 190, 210), (6, 3), 1),
                            "ash": ((255, 150, 70), (10, -18), 2)}[biome]
        if self.area_kind() in ("dungeon", "pass", "abyss"):
            col, speed, size = (200, 200, 230), (4, -3), 1
        for i in range(34):
            x = (i * 193.7 + t * speed[0] * (1 + i % 3) - icx * 0.35) % (VW + 40) - 20
            y = (i * 97.3 + t * speed[1] * (1 + i % 2) + math.sin(t * 0.8 + i) * 18 - icy * 0.35) % (VH + 40) - 20
            tw = 0.5 + 0.5 * math.sin(t * 2 + i)
            pygame.draw.circle(self.canvas, rgb(col, 0.5 + 0.5 * tw), (int(x), int(y)), size)

    def draw_darkness(self, icx, icy, t):
        if self.settings["lowfx"]:
            return
        if self.dark is None:
            self.dark = pygame.Surface((VW, VH), pygame.SRCALPHA)
        self.dark.fill((6, 5, 14, 120 if self.area == "final" else 172))
        px, py = self.p["x"] - icx, self.p["y"] - icy
        self.dark.blit(art.light_surface(300), (int(px - 296), int(py - 296)), special_flags=pygame.BLEND_RGBA_SUB)
        for piece in self.world().pieces:
            if piece[0] == "torch":
                x, y = piece[1] - icx, piece[2] - icy - 40
                if -200 < x < VW + 200 and -200 < y < VH + 200:
                    rad = 184 + int(8 * math.sin(t * 9 + piece[3]))
                    self.dark.blit(art.light_surface(rad), (int(x - rad), int(y - rad)), special_flags=pygame.BLEND_RGBA_SUB)
        for h in self.hazards:
            if h["done"] and h["linger"] > 0:
                x, y = h["x"] - icx, h["y"] - icy
                self.dark.blit(art.light_surface(90), (int(x - 88), int(y - 88)), special_flags=pygame.BLEND_RGBA_SUB)
        self.canvas.blit(self.dark, (0, 0))

    def draw_arena(self, world, icx, icy, t):
        ax, ay = world.arena_xy
        boss = next((e for e in self.current()["enemies"] if e.kind == "boss"), None)
        if boss is None:
            return
        if self.arena:
            color, inten = (255, 90, 90), 1.0
        elif self.p["zonekills"][self.zone_index()] >= ARENA_KILLS:
            color, inten = GOLD, 0.7 + 0.3 * math.sin(t * 3)
        else:
            color, inten = (150, 90, 90), 0.6
        art.draw_arena_ring(self.canvas, ax - icx, ay - icy, W.ARENA_R, t, color, inten)

    def draw_water_shimmer(self, world, icx, icy, t):
        col = {"forest": (150, 210, 255), "ruins": (80, 60, 130), "ash": (255, 200, 90)}[world.biome]
        if self.area == "final":
            col = (150, 80, 220)
        for gy in range(max(0, icy // CELL), min(world.gh, (icy + VH) // CELL + 1)):
            row = world.grid[gy]
            for gx in range(max(0, icx // CELL), min(world.gw, (icx + VW) // CELL + 1)):
                if row[gx] == 3:
                    ph = t * 1.5 + gx * 0.7 + gy * 1.3
                    x = gx * CELL - icx + 8 + math.sin(ph) * 6
                    y = gy * CELL - icy + 12 + (gx * 7 + gy * 3) % 16
                    pygame.draw.line(self.canvas, col, (int(x), int(y)), (int(x + 12), int(y)), 2)

    def draw_piece(self, piece, icx, icy, t):
        kind, x, y, seed = piece
        x, y = x - icx, y - icy
        if kind == "campfire":
            art.draw_campfire(self.canvas, x, y, t)
        elif kind == "torch":
            art.draw_torch(self.canvas, x, y, t, seed)
        elif kind == "banner":
            art.draw_banner(self.canvas, x, y, t, (176, 60, 60) if seed % 2 == 0 else (60, 100, 176))
        elif kind == "obelisk":
            art.draw_obelisk(self.canvas, x, y, t, seed)

    def draw_poi(self, poi, icx, icy, t):
        x, y = poi["x"] - icx, poi["y"] - icy
        kind = poi["kind"]
        label = None
        if kind == "npc":
            info = NPCS[poi["npc"]]
            art.shadow(self.canvas, x, y + 14, 16, 6)
            bob = math.sin(t * 2 + poi["x"]) * 1.2
            if not self.sprite("npc_" + poi["npc"], x, y + bob, 52):
                pygame.draw.circle(self.canvas, (200, 170, 120), (int(x), int(y)), 14)
            mark = self.npc_marker(poi["npc"])
            if mark:
                art.marker(self.canvas, x, y - 46, t, mark)
            label = info["name"]
        elif kind in ("chest", "dchest"):
            art.draw_chest(self.canvas, x, y, t)
            label = "Сундук"
        elif kind == "reward":
            art.draw_chest(self.canvas, x, y, t)
            art.draw_glow(self.canvas, x, y, 90, GOLD, 0.6)
            label = "Награда"
        elif kind in ("gate_next", "gate_back", "portal"):
            state = self.poi_state(poi)
            color = (110, 190, 255) if kind == "gate_back" else (236, 119, 251) if kind == "portal" else (190, 120, 255)
            art.draw_gate(self.canvas, x, y, t, state, color)
            label = {"gate_next": "Путь вперёд", "gate_back": "Путь назад", "portal": "Портал в Пустоту"}[kind]
            if state == "sealed":
                label += " (запечатан)"
        elif kind == "entrance":
            art.draw_dungeon_door(self.canvas, x, y, t)
            idx = DUNGEON_IDS.index(poi["dg"])
            label = DUNGEONS[poi["dg"]]["name"] + (" ✓" if self.p["dungeons"][idx] else "")
        elif kind in ("exit", "exit_back"):
            art.draw_exit(self.canvas, x, y, t)
            label = "Выход" if kind == "exit" else "Назад"
        elif kind in ("exit_fwd", "stairs"):
            art.draw_stairs(self.canvas, x, y, t)
            label = "Вперёд" if kind == "exit_fwd" else "Спуск вниз"
        elif kind == "altar":
            art.draw_altar(self.canvas, x, y, t)
            label = "Алтарь реликвий"
        elif kind == "stall":
            art.draw_stall(self.canvas, x, y, t)
            label = "Торговец Бездны"
        if label:
            self.text(label, x, y + 36, MUTED, 14, True)

    def draw_hazard(self, h, icx, icy):
        x, y = int(h["x"] - icx), int(h["y"] - icy)
        lingering = h["done"] and h["linger"] > 0
        warn = ((251, 93, 104), (255, 70, 210), (255, 140, 0))[self.settings["colorblind"]]
        color = warn if h["delay"] > 0 else GOLD
        if h.get("color") and (lingering or h["damage"] <= 0):
            color = h["color"]
        faint = h["damage"] <= 0 and not h["linger"]
        if h["line"]:
            ex = int(x + h["dx"] * h["line"])
            ey = int(y + h["dy"] * h["line"])
            if not faint:
                bx0, by0 = int(max(0, min(x, ex) - h["width"] - 2)), int(max(0, min(y, ey) - h["width"] - 2))
                bx1, by1 = int(min(VW, max(x, ex) + h["width"] + 2)), int(min(VH, max(y, ey) + h["width"] + 2))
                if bx1 > bx0 and by1 > by0:
                    overlay = pygame.Surface((bx1 - bx0, by1 - by0), pygame.SRCALPHA)
                    pygame.draw.line(overlay, (*color, 65), (x - bx0, y - by0), (ex - bx0, ey - by0), int(h["width"] * 2))
                    self.canvas.blit(overlay, (bx0, by0))
            pygame.draw.line(self.canvas, color, (x, y), (ex, ey), 2 if faint else 4 if self.settings["colorblind"] else 3)
            return
        r = int(h["radius"])
        if not -r < x < VW + r or not -r < y < VH + r:
            return
        pulse = 0.5 + 0.5 * math.sin(self.time * 14)
        if lingering:
            art.draw_glow(self.canvas, x, y, r + 14, color, 0.5 * min(1, h["linger"] / 1.2) * (0.8 + 0.2 * math.sin(self.time * 5)))
            for k in range(4):
                a = self.time * 1.3 + k * 1.57
                pygame.draw.circle(self.canvas, rgb(color, 0.8), (int(x + math.cos(a) * r * 0.55), int(y + math.sin(a) * r * 0.55)), max(3, r // 5), 1)
            pygame.draw.circle(self.canvas, rgb(color, 0.8), (x, y), r, 2)
            return
        warning = h["delay"] > 0
        alpha = (int(35 + 40 * pulse) if warning else 70) if not faint else 30
        self.canvas.blit(art.disc_surface(r, color, alpha), (x - r - 2, y - r - 2))
        pygame.draw.circle(self.canvas, color, (x, y), r, 3 + (int(pulse * 2) if warning else 0))
        if warning and self.settings["colorblind"]:
            art.dashed_circle(self.canvas, (255, 255, 255), x, y, r - 6, 3, 16, self.time * 2)
        if warning:
            progress = 1 - h["delay"] / max(0.01, h["total"])
            pygame.draw.circle(self.canvas, GOLD, (x, y), max(4, int(r * progress)), 2)

    def draw_drop(self, drop, icx, icy, t):
        item = drop["item"]
        age = drop.get("age", 9.0)
        fx, fy = drop["x"], drop["y"]
        ox, oy = drop.get("ox", fx), drop.get("oy", fy)
        lift = 0.0
        if age < 0.6:
            k = age / 0.6
            px = lerp(ox, fx, ease_out(k))
            py = lerp(oy, fy, ease_out(k))
            lift = 70 * 4 * k * (1 - k)
        else:
            px, py = fx, fy
            if age < 0.95:
                lift = 9 * math.sin(math.pi * (age - 0.6) / 0.35)
        x, y = px - icx, py - icy
        if not (-80 < x < VW + 80 and -200 < y < VH + 80):
            return
        r = item.rarity
        col = item.color
        art.shadow(self.canvas, x, y + 6, 12 - lift / 12, 4)
        bob = math.sin(t * 3 + fx) * 3 if age >= 0.95 else 0
        if r >= 3 and age > 0.3:
            beam = art.beam_surface(col)
            self.canvas.blit(beam, (int(x - 8), int(y - 190 + 6)))
        art.draw_glow(self.canvas, x, y - 14 - lift, 26 + r * 13, col, 0.35 + 0.1 * r + 0.08 * math.sin(t * 4 + fx))
        art.draw_item_icon(self.canvas, item, x, y - 16 - lift + bob, 30 + r * 2, t)
        if r >= 2:
            for k in range(2 + r):
                ph = (t * 0.8 + k * 0.31 + fx * 0.013) % 1
                sx = x + math.sin(k * 2.7 + fx) * 18
                sy = y - 10 - ph * 46
                pygame.draw.circle(self.canvas, (255, 255, 255), (int(sx), int(sy)), max(1, int(2.2 * (1 - ph))))
        if r >= 1 and age > 0.9:
            font = self.fonts[14]
            label = item.title
            img = font.render(label, True, col)
            pad = pygame.Rect(0, 0, img.get_width() + 8, img.get_height() + 2)
            pad.midbottom = (int(x), int(y - 36 - bob))
            pygame.draw.rect(self.canvas, (10, 14, 22), pad, border_radius=4)
            pygame.draw.rect(self.canvas, col, pad, 1, border_radius=4)
            self.canvas.blit(img, (pad.x + 4, pad.y + 1))

    # --------------------------------------------------------- enemies
    def enemy_sprite_info(self, e):
        boss = e.kind in ("boss", "finalboss")
        if boss:
            return BOSSES[3 if e.kind == "finalboss" else e.zone]["sprite"], e.radius * 3.5
        if e.kind == "miniboss":
            return "enemy_golem", e.radius * 2.7
        if e.kind == "slimelet":
            return "enemy_magma", e.radius * 2.6
        return "enemy_" + e.kind, e.radius * 2.6

    def draw_enemy(self, e, icx, icy, t):
        x, y = int(e.x - icx), int(e.y - icy)
        r = int(e.radius)
        boss = e.kind in ("boss", "finalboss")
        big = boss or e.kind == "miniboss"
        sname, base = self.enemy_sprite_info(e)
        prog = clamp(1 - e.wind / e.wmax, 0, 1) if e.wind > 0 and e.wmax > 0 else 0.0
        if e.attack == "burrow" and e.dash > 0:
            pygame.draw.ellipse(self.canvas, (96, 78, 60), (x - 16, y + 4, 32, 14))
            for k in range(3):
                pygame.draw.circle(self.canvas, (140, 116, 84), (x + int(math.sin(t * 20 + k) * 10), y + 2 - k * 3), 3)
            return
        art.shadow(self.canvas, x, y + r * 0.7, r * 1.1, r * 0.4)
        color = self.boss_color(e) if big else None
        if big:
            if not e.awake:
                art.draw_glow(self.canvas, x, y, r * 2.5, rgb(color, 0.5), 0.3)
            else:
                art.draw_glow(self.canvas, x, y, r * 3 + int(6 * math.sin(t * 3)), color if e.phase == 1 else RED, 0.45 + 0.1 * e.phase)
        wobble = math.sin(t * (9 if e.kind in ("wolf", "bat", "imp") else 5) + e.home_x)
        sx = 1 + 0.05 * wobble + 0.2 * min(1.0, e.flash / 0.12)
        sy = 1 - 0.05 * wobble - 0.2 * min(1.0, e.flash / 0.12)
        ox = oy = 0.0
        k = e.kind
        if k in ("slime", "slimelet", "magma"):
            if e.wind > 0:
                sy, sx = sy - 0.35 * prog, sx + 0.3 * prog
            elif e.dash > 0:
                hop = math.sin(math.pi * (1 - e.dash / max(e.pi, 0.05)))
                oy, sy, sx = -hop * 34, sy + 0.15 * hop, sx - 0.1 * hop
        elif k in ("wolf", "bat", "imp"):
            if e.wind > 0:
                ox, oy, sy = -e.ax * 8 * prog, -e.ay * 8 * prog, sy - 0.15 * prog
            elif e.dash > 0:
                for j in range(1, 4):
                    art.draw_glow(self.canvas, x - e.ax * j * 15, y - e.ay * j * 15, r + 8, (255, 220, 150) if k != "imp" else (255, 120, 50), 0.35 / j)
        elif k == "golem" or k == "miniboss":
            if e.wind > 0:
                oy, sy = -prog * 14, sy + 0.25 * prog
        elif k == "scarab" and e.wind > 0:
            oy, sy = prog * 10, sy - 0.3 * prog
        elif k == "spore" and e.wind > 0:
            sx, sy = sx + 0.3 * prog, sy + 0.3 * prog
        elif big:
            if e.attack == "leap" and e.wind > 0:
                oy, sy = -prog * 30, sy + 0.2 * prog
            elif e.attack == "charge" and e.wind > 0:
                ox, oy = -e.ax * 10 * prog, -e.ay * 10 * prog
            elif e.attack == "transform":
                ox, oy = math.sin(t * 60) * 4, math.sin(t * 47) * 3
            if e.phase == 2:
                sx, sy = sx * 1.12, sy * 1.12
        if big and e.pat:
            art.draw_glow(self.canvas, x, y, r * 2 + 10, color, 0.25 + 0.15 * math.sin(t * 10))
        w, h = int(base * sx), int(base * sy)
        yy = y + (int(base) - h) // 2 + int(oy)
        if k == "bat":
            yy -= int(8 + 4 * math.sin(t * 8 + e.home_y))
        if k == "ghost":
            yy -= int(6 + 3 * math.sin(t * 3 + e.home_x))
            if e.attack == "blink" and e.wind > 0 and int(t * 24) % 2:
                return
        flip = e.ax < 0 and k in ("wolf", "bat", "archer", "shaman", "imp", "cultist", "ghost")
        if not self.sprite(sname, x + ox, yy, (w, h), flip):
            colors = {"slime": (93, 201, 120), "wolf": (174, 177, 184), "golem": (134, 151, 170), "bat": (120, 80, 140),
                      "archer": (210, 205, 190), "shaman": (150, 90, 200), "boss": ZONES[e.zone]["boss_color"],
                      "finalboss": (161, 87, 222)}
            pygame.draw.circle(self.canvas, colors.get(k, (200, 120, 120)), (x, y), r)
            pygame.draw.circle(self.canvas, (32, 30, 40), (x - 5, y - 3), 3)
            pygame.draw.circle(self.canvas, (32, 30, 40), (x + 5, y - 3), 3)
        if e.phase == 2 and big:
            art.draw_glow(self.canvas, x, y, r * 2, RED, 0.25)
        if e.flash > 0:
            art.draw_glow(self.canvas, x, y, r * 2, (255, 255, 255), 0.6)
        if e.elite:
            ec = {"fast": (120, 220, 255), "armored": (190, 190, 210), "vampiric": (255, 80, 110), "explosive": (255, 170, 60)}[e.elite]
            art.draw_glow(self.canvas, x, y, r * 2 + 12, ec, 0.5)
            pygame.draw.polygon(self.canvas, GOLD, [(x - 8, y - r - 20), (x - 4, y - r - 28), (x, y - r - 21), (x + 4, y - r - 28), (x + 8, y - r - 20)])
        if e.burn > 0:
            for j in range(3):
                art.draw_flame(self.canvas, x + (j - 1) * 8, y - r * 0.5 - j * 2, t, 0.45, j)
        if e.slow > 0:
            pygame.draw.circle(self.canvas, (150, 210, 255), (x, y), r + 5, 2)
        self.draw_attack_fx(e, x, y, r, prog, t)
        if e.kind in ("boss", "finalboss"):
            pygame.draw.circle(self.canvas, GOLD if e.phase == 1 else RED, (x, y), r + 8, 2)
            if not e.awake:
                self.text("Z z", x + r * 0.6, y - r * 1.4 + math.sin(t * 2) * 3, MUTED, 21)
        elif e.kind != "miniboss":
            pygame.draw.rect(self.canvas, (64, 34, 43), (x - r, y - r - 14, r * 2, 5))
            pygame.draw.rect(self.canvas, GOLD if e.elite else RED, (x - r, y - r - 14, int(r * 2 * max(0, e.hp) / e.maxhp), 5))

    def draw_attack_fx(self, e, x, y, r, prog, t):
        k = e.kind
        if e.wind <= 0 or e.attack == "transform":
            return
        if k in ("wolf", "bat", "imp") or (k in ("boss", "finalboss", "miniboss") and e.attack == "charge"):
            length = 150 if k not in ("boss", "finalboss", "miniboss") else 280
            end = (int(x + e.ax * length), int(y + e.ay * length))
            pygame.draw.line(self.canvas, GOLD, (x, y), end, 4)
            pygame.draw.circle(self.canvas, RED, (x, y), r + 6 + int(2 * math.sin(t * 30)), 2)
        elif k == "archer":
            ex, ey = x + e.ax * (14 + 14 * prog), y + e.ay * (14 + 14 * prog)
            pygame.draw.line(self.canvas, (240, 230, 190), (x + e.ax * 6, y + e.ay * 6), (ex, ey), 3)
            pygame.draw.circle(self.canvas, (255, 240, 200), (int(ex), int(ey)), 4)
            art.draw_glow(self.canvas, ex, ey, 24, (255, 240, 180), 0.5 * prog)
        elif k in ("shaman", "cultist"):
            col = (200, 110, 255) if k == "shaman" else (255, 70, 90)
            rr = 26 + 14 * prog
            pts = [(x + math.cos(t * 3 + a * math.tau / 5) * rr, y + r * 0.6 + math.sin(t * 3 + a * math.tau / 5) * rr * 0.45) for a in range(5)]
            pygame.draw.polygon(self.canvas, col, pts, 2)
            pygame.draw.ellipse(self.canvas, col, (int(x - rr), int(y + r * 0.6 - rr * 0.45), int(rr * 2), int(rr * 0.9)), 1)
            art.draw_glow(self.canvas, x, y - r, 34, col, 0.6 * prog)
        elif k == "wisp":
            for j in range(6):
                a = t * 6 + j * math.tau / 6
                pygame.draw.circle(self.canvas, (160, 210, 255), (int(x + math.cos(a) * (14 + 14 * prog)), int(y + math.sin(a) * (14 + 14 * prog))), 3)
        elif k == "golem" or k == "miniboss":
            pygame.draw.circle(self.canvas, RED, (x, y), int(r + 6 + 22 * prog), 2)
        elif k == "spore":
            for j in range(5):
                a = t * 4 + j * 1.3
                pygame.draw.circle(self.canvas, (160, 230, 120), (int(x + math.cos(a) * 18 * prog + j - 2), int(y - r - 6 * prog * j % 20)), 3)
        elif k == "ghost":
            art.draw_glow(self.canvas, x, y, 40, (180, 210, 255), 0.5)
        elif k in ("slime", "slimelet", "magma"):
            pygame.draw.circle(self.canvas, RED if k != "magma" else (255, 140, 40), (x, y), r + 4, 2)
        elif k in ("boss", "finalboss") and e.attack == "leap":
            pygame.draw.circle(self.canvas, RED, (x, y), int(r + 10 + 20 * prog), 2)

    def draw_death(self, d, icx, icy):
        x, y, kind, r, t, zone = d
        k = clamp(t / 0.45, 0, 1)
        boss = kind in ("boss", "finalboss")
        if boss:
            sname, base = BOSSES[3 if kind == "finalboss" else zone]["sprite"], r * 3.5
        elif kind == "miniboss":
            sname, base = "enemy_golem", r * 2.7
        else:
            sname, base = ("enemy_magma" if kind == "slimelet" else "enemy_" + kind), r * 2.6
        size = max(2, int(base * (1 - k * 0.8)))
        sx, sy = x - icx, y - icy - k * 14
        art.draw_glow(self.canvas, sx, sy, r * 2.2, (255, 255, 255), 0.7 * (1 - k))
        if k < 0.7:
            self.sprite(sname, sx, sy, size)

    def draw_hero(self, icx, icy):
        p = self.p
        t = self.time
        x, y = p["x"] - icx, p["y"] - icy
        fx, fy = p["face_x"], p["face_y"]
        if self.lunge > 0:
            k = self.lunge / 0.12
            x += fx * 7 * k
            y += fy * 7 * k
        art.shadow(self.canvas, x, y + 15, 15, 6)
        # equipment glow
        weapon, armor, amulet = p["equip"]["weapon"], p["equip"]["armor"], p["equip"]["amulet"]
        if armor and armor.rarity >= 2:
            art.draw_glow(self.canvas, x, y + 8, 40 + armor.rarity * 6, armor.color, 0.2 + 0.05 * armor.rarity)
        if self.buffed("cry"):
            art.draw_glow(self.canvas, x, y, 60, (255, 120, 80), 0.55)
        if p["invuln"] > 0 and p["dash"] <= 0 and int(t * 18) % 2:
            return
        step = abs(math.sin(t * 13)) if self.moving else 0.0
        breathe = 0.0 if self.moving else math.sin(t * 2.2) * 0.012
        size = (int(48 * (1 - 0.04 * step - breathe)), int(48 * (1 + 0.06 * step + breathe)))
        by = y - 3 * step
        base = "hero_side" if abs(fx) > abs(fy) else ("hero_up" if fy < 0 else "hero_down")
        name = self.hero_sprite_name(base)
        behind = base == "hero_up"
        if behind:
            self.draw_hero_weapon(x, by, fx, fy, t)
        drawn = self.sprite(name, x, by, size, base == "hero_side" and fx < 0)
        if not drawn:
            pygame.draw.rect(self.canvas, (74, 145, 211), (int(x - 11), int(by - 7), 22, 25), border_radius=6)
            pygame.draw.circle(self.canvas, (233, 196, 153), (int(x), int(by - 13)), 10)
        if amulet:
            pulse = 0.7 + 0.3 * math.sin(t * 4)
            if amulet.rarity >= 1:
                art.draw_glow(self.canvas, x, by - 2, 18, amulet.color, 0.6 * pulse)
            pygame.draw.circle(self.canvas, amulet.color, (int(x), int(by - 1)), 3)
        if not behind:
            self.draw_hero_weapon(x, by, fx, fy, t)
        if self.hurt_t > 0:
            art.draw_glow(self.canvas, x, y, 42, (255, 60, 60), 0.9 * self.hurt_t / 0.3)
        if self.shield > 0:
            pygame.draw.circle(self.canvas, (150, 210, 255), (int(x), int(y)), 30 + int(2 * math.sin(t * 6)), 2)
            art.draw_glow(self.canvas, x, y, 38, (130, 190, 255), 0.3)
        if self.levelfx:
            k = self.levelfx["t"]
            for i in range(7):
                a = clamp(1 - k / 2.0, 0, 1)
                art.draw_glow(self.canvas, x, y - 20 - i * 26 * (0.6 + k * 0.4), 40, GOLD, 0.45 * a)
            pygame.draw.circle(self.canvas, GOLD, (int(x), int(y + 14)), int(30 + k * 160), 3 if k < 1.5 else 1)

    def draw_hero_weapon(self, x, y, fx, fy, t):
        item = self.p["equip"]["weapon"]
        kind = self.weapon()
        tier = self.weapon_tier()
        accent = item.color if item else GOLD
        base = math.atan2(fy, fx)
        hx = x + (-math.sin(base)) * 9 + fx * 3
        hy = y + 4 + math.cos(base) * 4
        if self.swing > 0:
            prog = 1 - self.swing / 0.22
            if kind == "sword":
                ang = base - 1.2 + 2.4 * prog
                art.draw_weapon(self.canvas, kind, tier, accent, hx, hy, ang, 1.15, t)
            elif kind == "spear":
                thrust = math.sin(prog * math.pi) * 22
                art.draw_weapon(self.canvas, kind, tier, accent, hx + fx * thrust, hy + fy * thrust, base, 1.0, t)
            elif kind == "hammer":
                ang = base - 1.9 + 2.4 * prog
                art.draw_weapon(self.canvas, kind, tier, accent, hx, hy, ang, 1.2, t)
            elif kind == "bow":
                art.draw_weapon(self.canvas, kind, tier, accent, hx + fx * 6, hy + fy * 6, base, 1.0, t, True)
            else:
                art.draw_weapon(self.canvas, kind, tier, accent, hx, hy, base - 0.5 + prog * 0.5, 1.0, t, True)
        else:
            idle = (base if kind == "bow" else base + 1.35) + math.sin(t * 2.2) * 0.04
            art.draw_weapon(self.canvas, kind, tier, accent, hx, hy, idle, 0.8, t, kind == "staff")

    # ------------------------------------------------------------- fx
    def draw_fx(self, icx, icy):
        for s in self.slashes:
            sx, sy = s[0] - icx, s[1] - icy
            angle, reach, life, total, shape, color = s[2], s[3], s[4], s[5], s[6], s[7]
            t = 1 - life / total
            width = max(1, int(7 * (1 - t)))
            if shape == "arc":
                points = []
                for i in range(9):
                    a = angle - 1.0 + 2.0 * t * i / 8
                    points.append((sx + math.cos(a) * reach * 0.9, sy + math.sin(a) * reach * 0.9))
                if t > 0.04:
                    pygame.draw.lines(self.canvas, color, False, points, width)
                    pygame.draw.lines(self.canvas, (255, 255, 255), False, points, max(1, width // 3))
            else:
                tip = reach * min(1.0, t * 2.5 + 0.2)
                pygame.draw.line(self.canvas, color, (sx + math.cos(angle) * 22, sy + math.sin(angle) * 22),
                                 (sx + math.cos(angle) * tip, sy + math.sin(angle) * tip), width)
        for a, b, life, seed in self.bolts:
            art.bolt(self.canvas, (a[0] - icx, a[1] - icy), (b[0] - icx, b[1] - icy), seed=seed + int(self.time * 30))
        for m in self.meteors:
            k = m["t"] / m["delay"]
            x, y = m["x"] - icx, m["y"] - icy
            overlay = pygame.Surface((int(m["r"] * 2 + 4), int(m["r"] * 2 + 4)), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (255, 90, 40, int(30 + 50 * k)), (int(m["r"] + 2), int(m["r"] + 2)), int(m["r"] * (0.3 + 0.7 * k)))
            self.canvas.blit(overlay, (int(x - m["r"] - 2), int(y - m["r"] - 2)))
            pygame.draw.circle(self.canvas, (255, 150, 70), (int(x), int(y)), int(m["r"]), 2)
            fy = y - (1 - k) * 520
            art.draw_glow(self.canvas, x, fy, 60, (255, 150, 60), 0.9)
            pygame.draw.circle(self.canvas, (255, 210, 120), (int(x), int(fy)), 16)
        for part in self.particles:
            x, y = int(part[0] - icx), int(part[1] - icy)
            if len(part) > 6:
                pygame.draw.circle(self.canvas, part[5], (x, y), max(2, int(part[6] * (1 - part[4] / 0.35))), 3)
            else:
                pygame.draw.circle(self.canvas, part[5], (x, y), max(1, int(part[4] * 8)))
        for f in self.floaters:
            self.text(f[2], f[0] - icx, f[1] - icy, f[3], 14, True)
        for kind, fx_, fy_, size, life, total, color, extra in self.fx:
            x, y = fx_ - icx, fy_ - icy
            k = 1 - life / total
            fade = clamp(1 - k, 0, 1)
            c = rgb(color, 0.4 + 0.6 * fade)
            if kind == "shock":
                pygame.draw.circle(self.canvas, c, (int(x), int(y)), max(2, int(size * (0.25 + 0.75 * k))), max(1, int(6 * fade)))
            elif kind == "crack":
                rng = random.Random(int(fx_ * 7 + fy_))
                for _ in range(9):
                    a = rng.uniform(0, math.tau)
                    ln = size * (0.3 + 0.7 * min(1, k * 2.5)) * rng.uniform(0.6, 1.0)
                    mid = (x + math.cos(a + 0.2) * ln * 0.5, y + math.sin(a + 0.2) * ln * 0.5)
                    pygame.draw.lines(self.canvas, rgb(color, 0.6 * fade + 0.2), False,
                                      [(x, y), mid, (x + math.cos(a) * ln, y + math.sin(a) * ln)], 3)
            elif kind == "beam":
                dx, dy, width = extra
                pygame.draw.line(self.canvas, c, (x, y), (x + dx * size, y + dy * size), max(2, int(width * 2 * fade)))
                pygame.draw.line(self.canvas, (255, 255, 255), (x, y), (x + dx * size, y + dy * size), max(1, int(width * fade * 0.6)))
            elif kind == "claws":
                dx, dy = extra
                a = math.atan2(dy, dx)
                for j in (-1, 0, 1):
                    off = j * 9
                    p0 = (x + math.cos(a + 1.57) * off - math.cos(a) * 22, y + math.sin(a + 1.57) * off - math.sin(a) * 22)
                    p1 = (p0[0] + math.cos(a) * 44 * min(1, k * 3), p0[1] + math.sin(a) * 44 * min(1, k * 3))
                    pygame.draw.line(self.canvas, c, p0, p1, 4)
        orbs = self.mod_count("orbit")
        if orbs and self.state != "creator":
            n = min(6, orbs * 2)
            for k in range(n):
                a = self.orb_t + k * math.tau / n
                ox, oy = self.p["x"] - icx + math.cos(a) * 62, self.p["y"] - icy + math.sin(a) * 62
                art.draw_glow(self.canvas, ox, oy, 24, BLUE, 0.7)
                pygame.draw.circle(self.canvas, BLUE, (int(ox), int(oy)), 7)
                pygame.draw.circle(self.canvas, (255, 255, 255), (int(ox - 2), int(oy - 2)), 2)

    def draw_room_map(self, rect, world):
        def pos(x, y):
            return (int(rect.x + 2 + x / WW * (rect.w - 4)), int(rect.y + 2 + y / WH * (rect.h - 4)))
        rooms = world.rooms
        known = {i for i, r in enumerate(rooms) if r["state"] != "idle"}
        known |= {j for i in list(known) for j in (i - 1, i + 1) if 0 <= j < len(rooms)}
        for i in sorted(known):
            r = rooms[i]
            x, y, w, h = r["rect"]
            p0, p1 = pos(x, y), pos(x + w, y + h)
            visited = r["state"] != "idle"
            col = {"cleared": (60, 110, 90), "locked": (150, 60, 60), "idle": (50, 56, 70)}[r["state"]]
            pygame.draw.rect(self.canvas, col, (p0[0], p0[1], max(3, p1[0] - p0[0]), max(3, p1[1] - p0[1])))
            if not visited:
                continue
            if r["kind"] in ("boss", "miniboss"):
                pygame.draw.circle(self.canvas, RED, pos(*r["center"]), 3)
            elif r["kind"] in ("treasure", "shop"):
                pygame.draw.circle(self.canvas, GOLD, pos(*r["center"]), 3)
        self._known_rects = [rooms[i]["rect"] for i in known if rooms[i]["state"] != "idle"]
        for i in range(len(rooms) - 1):
            if i in known and i + 1 in known and (rooms[i]["state"] != "idle" or rooms[i + 1]["state"] != "idle"):
                pygame.draw.line(self.canvas, (96, 110, 130), pos(*rooms[i]["center"]), pos(*rooms[i + 1]["center"]), 1)

    def minimap(self, rect, large=False):
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.canvas, (19, 28, 38), rect, border_radius=6)
        world = self.world()
        if world.rooms:
            self.draw_room_map(rect, world)
        else:
            self.canvas.blit(self.mini_terrain((rect.w - 4, rect.h - 4)), (rect.x + 2, rect.y + 2))
        pygame.draw.rect(self.canvas, (82, 109, 140), rect, 1, border_radius=6)

        def pos(x, y):
            return (int(rect.x + 2 + x / WW * (rect.w - 4)), int(rect.y + 2 + y / WH * (rect.h - 4)))

        for poi in self.available_pois():
            if world.rooms and not any(k[0] <= poi["x"] <= k[0] + k[2] and k[1] <= poi["y"] <= k[1] + k[3] for k in self._known_rects):
                continue
            color = {"camp": GREEN, "npc": (255, 240, 160), "chest": GOLD, "entrance": (188, 139, 242),
                     "portal": (236, 119, 251), "exit": BLUE, "reward": GOLD, "gate_next": PURPLE, "gate_back": BLUE,
                     "exit_back": BLUE, "exit_fwd": PURPLE, "stairs": PURPLE, "altar": GOLD, "stall": GOLD,
                     "dchest": GOLD}.get(poi["kind"], TEXT)
            if poi["kind"] == "npc" and self.npc_marker(poi["npc"]) == "!":
                color = GOLD
            pygame.draw.circle(self.canvas, color, pos(poi["x"], poi["y"]), 5 if large else 3)
        for e in self.current()["enemies"]:
            if world.rooms and not any(k[0] <= e.x <= k[0] + k[2] and k[1] <= e.y <= k[1] + k[3] for k in self._known_rects):
                continue
            if e.kind in ("boss", "finalboss", "miniboss") or large:
                pygame.draw.circle(self.canvas, RED, pos(e.x, e.y), 6 if e.kind in ("boss", "finalboss", "miniboss") else 2)
        pygame.draw.circle(self.canvas, TEXT, pos(self.p["x"], self.p["y"]), 5 if large else 4)
