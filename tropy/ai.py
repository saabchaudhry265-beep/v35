"""Enemy behaviour, bosses, arenas, hazards and bullets (mixin for Game)."""
import math
import random

from .common import *
from .content import *
from . import world as W
from .combat import ELITE_NAMES

BOSS_KINDS = ("boss", "finalboss", "miniboss")
RANGED = {"archer": (250, 360), "shaman": (250, 360), "spore": (220, 330), "cultist": (260, 380), "wisp": (200, 300)}
ATTACK_RANGE = {"slime": 190, "slimelet": 150, "magma": 190, "wolf": 235, "bat": 260, "imp": 270, "golem": 150,
                "archer": 440, "shaman": 440, "spore": 360, "wisp": 340, "ghost": 320, "scarab": 300, "cultist": 450}
DASH_SPEED = {"wolf": 470, "bat": 540, "imp": 520, "slime": 320, "slimelet": 300, "magma": 300, "scarab": 210}


class AIMixin:
    def enemy_name(self, e):
        if e is None:
            return "Ловушка"
        if getattr(e, "elite", ""):
            return ELITE_NAMES[e.elite] + " " + ENEMIES[e.kind]["name"].lower()
        if e.kind == "finalboss":
            return BOSSES[3]["name"]
        if e.kind == "boss":
            return BOSSES[e.zone]["name"]
        if e.kind == "miniboss":
            return e.tag or ENEMIES["miniboss"]["name"]
        return ENEMIES[e.kind]["name"]

    def boss_key(self, e):
        if e.kind == "finalboss":
            return 3
        if e.kind == "miniboss":
            return 4 + e.zone
        return e.zone

    def boss_color(self, e):
        if e.kind == "finalboss":
            return BOSSES[3]["color"]
        if e.kind == "boss":
            return BOSSES[e.zone]["color"]
        return ZONES[e.zone]["boss_color"]

    # ----------------------------------------------------------- spawners
    def danger(self, e, delay, radius=0, x=None, y=None, line=0, width=24, damage=None, burst=None,
               linger=0.0, ldmg=0.0, color=None):
        self.hazards.append({
            "x": e.x if x is None else x, "y": e.y if y is None else y, "radius": radius, "line": line, "width": width,
            "dx": e.ax, "dy": e.ay, "delay": delay, "total": delay, "life": 0.22, "done": False,
            "damage": (e.damage * (1.35 if e.phase >= 2 else 1)) if damage is None else damage,
            "bdmg": e.damage * 0.55, "burst": burst, "owner": e, "src": self.enemy_name(e),
            "linger": linger, "ldmg": ldmg, "tick": 0.0, "color": color,
        })

    def shoot(self, x, y, angle, speed, dmg, r=7, color=(255, 110, 110), home=0.0, life=6.0, src=None):
        if len(self.bullets) > 420:
            return
        self.bullets.append({"x": x, "y": y, "ox": x, "oy": y, "dx": math.cos(angle), "dy": math.sin(angle),
                             "speed": speed, "dmg": dmg, "r": r, "color": color, "home": home, "life": life,
                             "age": 0.0, "src": src})

    def fire_burst(self, x, y, base_angle, burst, dmg, src=None):
        n = burst["n"]
        for k in range(n):
            if burst.get("ring"):
                ang = base_angle + k * math.tau / n
            else:
                spread = burst.get("spread", 0.4)
                ang = base_angle + (k - (n - 1) / 2) * (spread / max(1, n - 1)) * (1 if n > 1 else 0)
            self.shoot(x, y, ang, burst.get("speed", 160), dmg, burst.get("r", 6), burst.get("color", (255, 120, 90)),
                       burst.get("home", 0.0), 4.5, src)

    # ------------------------------------------------------- regular AI
    def prepare_enemy(self, e):
        px, py = self.p["x"], self.p["y"]
        e.ax, e.ay = direction(px - e.x, py - e.y)
        z = e.zone
        f = 1 - 0.07 * z
        k = e.kind
        if k == "wolf":
            e.wind, e.attack, e.cd = max(0.3, 0.5 * f), "charge", 2.4
            e.combo = 0 if z == 0 else (1 if z == 1 else 2)
        elif k == "bat":
            e.wind, e.attack, e.cd = 0.36 * f, "charge", 2.0
            e.combo = 0 if z == 0 else 1
        elif k == "imp":
            e.wind, e.attack, e.cd = 0.45 * f, "charge", 2.6
            e.combo = 1
        elif k in ("slime", "slimelet", "magma"):
            e.wind, e.attack = (0.4 if k == "slimelet" else 0.55) * f, "hop"
            e.cd = 1.7
            e.pi = min(0.6, max(0.15, distance(e.x, e.y, px, py) / 320))
            if k == "magma":
                self.danger(e, e.wind, 54, px, py, linger=2.5, ldmg=e.damage * 0.3, color=(255, 120, 40))
            else:
                self.danger(e, e.wind, 36 if k == "slimelet" else 52, px, py)
        elif k == "golem":
            e.wind, e.attack, e.cd = 0.85 * f, "cast", 3.0
            self.danger(e, e.wind, 105, burst={"n": 8 if z == 0 else 10, "ring": True, "speed": 150, "r": 7})
        elif k == "archer":
            e.wind, e.attack, e.cd = 0.5 * f, "cast", 2.2
            burst = {"n": 1 if z == 0 else 3, "spread": 0.4, "speed": 340, "r": 5, "color": (240, 230, 190)}
            self.danger(e, e.wind, line=470, width=5, damage=0, burst=burst)
        elif k == "shaman":
            e.wind, e.attack, e.cd = 0.7 * f, "cast", 3.2
            burst = {"n": 3 + z, "spread": 0.9, "speed": 150, "r": 9, "home": 1.1, "color": (210, 120, 255)}
            self.danger(e, e.wind, 34, damage=0, burst=burst)
        elif k == "spore":
            e.wind, e.attack, e.cd = 0.7 * f, "cast", 3.3
            self.danger(e, e.wind, 78, px, py, damage=0, linger=3.5, ldmg=e.damage * 0.45, color=(130, 210, 90))
        elif k == "wisp":
            e.wind, e.attack, e.cd = 0.6 * f, "cast", 2.8
            burst = {"n": 8, "ring": True, "speed": 115, "r": 5, "color": (130, 190, 255)}
            self.danger(e, e.wind, 28, damage=0, burst=burst)
        elif k == "ghost":
            ang = random.uniform(0, math.tau)
            sx, sy = px + math.cos(ang) * 90, py + math.sin(ang) * 90
            if self.blocked(sx, sy, 14):
                sx, sy = px, py
            e.tx, e.ty = sx, sy
            e.wind, e.attack, e.cd = 0.55 * f, "blink", 3.0
            self.danger(e, 0.9 * f, 62, sx, sy)
        elif k == "scarab":
            e.wind, e.attack, e.cd = 0.4, "burrow", 3.2
            e.tx, e.ty = px, py
        elif k == "cultist":
            e.wind, e.attack, e.cd = 1.0 * f, "cast", 3.8
            base = math.atan2(e.ay, e.ax)
            for off in (-0.5, 0.0, 0.5):
                e.ax, e.ay = math.cos(base + off), math.sin(base + off)
                self.danger(e, 1.0 * f + abs(off) * 0.4, line=480, width=18)
            e.ax, e.ay = math.cos(base), math.sin(base)
        e.wmax = e.wind

    def finish_windup(self, e):
        a = e.attack
        if a == "charge":
            e.dash = {"wolf": 0.3, "bat": 0.28, "imp": 0.32}.get(e.kind, 0.3)
        elif a == "hop":
            e.dash = e.pi
        elif a == "burrow":
            e.dash = 0.9
            e.ax, e.ay = direction(e.tx - e.x, e.ty - e.y)
            self.burst(e.x, e.y, (150, 120, 80), 10)
        elif a == "blink":
            self.burst(e.x, e.y, (200, 220, 255), 10)
            e.x, e.y = e.tx, e.ty
            self.burst(e.x, e.y, (200, 220, 255), 14)
            self.add_fx("shock", e.x, e.y, 40, 0.3, (200, 220, 255))

    def finish_dash(self, e):
        f = 1 - 0.07 * e.zone
        a = e.attack
        if a == "charge":
            self.add_fx("claws", e.x, e.y, 38, 0.3, (255, 230, 160), (e.ax, e.ay))
            if e.combo > 0:
                e.combo -= 1
                e.ax, e.ay = direction(self.p["x"] - e.x, self.p["y"] - e.y)
                e.wind = e.wmax = 0.26 * f
        elif a == "hop":
            self.burst(e.x, e.y, (120, 220, 120) if e.kind != "magma" else (255, 150, 60), 8)
            self.add_fx("shock", e.x, e.y, 46, 0.3, (160, 230, 140) if e.kind != "magma" else (255, 150, 60))
        elif a == "burrow":
            self.burst(e.x, e.y, (150, 120, 80), 14)
            self.add_fx("crack", e.x, e.y, 70, 0.5, (140, 110, 80))
            self.danger(e, 0.3, 70)

    def update_enemy(self, e, dt):
        e.cd = max(0, e.cd - dt)
        e.flash = max(0, e.flash - dt)
        if e.burn > 0:
            e.burn = max(0.0, e.burn - dt)
            e.pi_burn = getattr(e, "pi_burn", 0) + dt
            if e.pi_burn >= 0.5:
                e.pi_burn = 0
                self.dot_damage(e, self.damage() * 0.3)
                if e not in self.current()["enemies"]:
                    return
        if e.slow > 0:
            e.slow = max(0.0, e.slow - dt)
        sf = 0.6 if e.slow > 0 else 1.0
        if abs(e.kx) + abs(e.ky) > 8:
            e.x, e.y = self.move(e.x, e.y, e.kx * dt, e.ky * dt, e.radius)
            decay = math.exp(-9 * dt)
            e.kx *= decay
            e.ky *= decay
        else:
            e.kx = e.ky = 0.0
        if e.kind in BOSS_KINDS:
            return self.update_boss(e, dt)
        if e.wind > 0:
            e.wind = max(0, e.wind - dt)
            if e.wind == 0:
                self.finish_windup(e)
            return
        if e.dash > 0:
            e.dash = max(0, e.dash - dt)
            sp = DASH_SPEED.get(e.kind, 470)
            self.move_enemy(e, e.ax * sp * dt, e.ay * sp * dt)
            if e.kind == "imp" and int(e.dash * 100) % 6 == 0 and len(self.hazards) < 60:
                self.danger(e, 0.05, 26, e.x, e.y, damage=0, linger=2.2, ldmg=e.damage * 0.3, color=(255, 120, 40))
            if e.kind == "scarab" and random.random() < 0.5:
                self.particles.append([e.x, e.y + 8, random.uniform(-20, 20), -20, 0.35, (150, 120, 80)])
            if e.attack == "charge" and distance(e.x, e.y, self.p["x"], self.p["y"]) < e.radius + 18:
                self.take_damage(e.damage * 1.4, self.enemy_name(e), (e.x, e.y), e)
            if e.dash == 0:
                self.finish_dash(e)
            return
        px, py = self.p["x"], self.p["y"]
        d = distance(e.x, e.y, px, py)
        ranged = e.kind in RANGED
        camp = self.camp()
        if camp and self.near_camp():
            tx, ty, attacking = e.home_x, e.home_y, False
        elif d < (520 if ranged else 390):
            tx, ty, attacking = px, py, True
        else:
            tx, ty, attacking = e.home_x, e.home_y, False
        if self.area_kind() in ("dungeon", "pass", "abyss"):
            attacking = e.room < 0 or True
            tx, ty = px, py
        if attacking and d < ATTACK_RANGE[e.kind] and e.cd <= 0:
            self.prepare_enemy(e)
            return
        speed = e.speed * sf
        if attacking and ranged:
            lo, hi = RANGED[e.kind]
            nx, ny = direction(px - e.x, py - e.y)
            if d < lo:
                self.move_enemy(e, -nx * speed * dt, -ny * speed * dt)
            elif d > hi:
                self.move_enemy(e, nx * speed * dt, ny * speed * dt)
            else:
                self.move_enemy(e, -ny * e.side * speed * 0.6 * dt, nx * e.side * speed * 0.6 * dt)
        elif attacking and e.kind in ("bat", "wisp"):
            e.ba += dt * (1.9 if e.kind == "bat" else 1.1) * e.side
            rad = 130 if e.kind == "bat" else 170
            gx, gy = px + math.cos(e.ba) * rad, py + math.sin(e.ba) * rad
            ddx, ddy = gx - e.x, gy - e.y
            dist = math.hypot(ddx, ddy)
            if dist > 4:
                self.move_enemy(e, ddx / dist * speed * dt * 1.2, ddy / dist * speed * dt * 1.2)
        else:
            dx, dy = tx - e.x, ty - e.y
            dist = math.hypot(dx, dy)
            stop = (e.radius + 20) if attacking else 8
            if dist > stop:
                self.move_enemy(e, dx / dist * speed * dt, dy / dist * speed * dt)
        if self.surface():
            self.camp_push(e)

    def camp_push(self, e):
        c = self.camp()
        if c and distance(e.x, e.y, *c) < CAMP_R:
            fx, fy = direction(e.x - c[0], e.y - c[1])
            e.x, e.y = c[0] + fx * (CAMP_R + 1), c[1] + fy * (CAMP_R + 1)
            self.ripples.append([math.atan2(fy, fx), 1.0])

    # ------------------------------------------------------------ bosses
    def update_boss(self, e, dt):
        if not e.awake:
            return
        key = self.boss_key(e)
        px, py = self.p["x"], self.p["y"]
        if e.phase == 1 and e.hp < e.maxhp * 0.5 and e.attack != "transform":
            e.attack, e.wind, e.pat, e.dash = "transform", 1.6, "", 0
            self.bullets.clear()
            self.hazards = [h for h in self.hazards if h["owner"] is not e]
            self.banner = {"t": 0.0, "title": "ВТОРАЯ ФОРМА", "sub": self.enemy_name(e), "color": RED}
            self.sound("win")
        if e.attack == "transform" and e.wind > 0:
            e.wind = max(0, e.wind - dt)
            self.shake = max(self.shake, 6)
            if random.random() < 0.6:
                self.burst(e.x + random.uniform(-30, 30), e.y + random.uniform(-30, 30), RED, 2)
            if e.wind == 0:
                e.phase, e.attack, e.cd = 2, "", 0.8
                self.visual_ring(e.x, e.y, 220, RED)
                self.add_fx("shock", e.x, e.y, 220, 0.6, RED)
                self.shake = max(self.shake, 12)
            return
        if e.wind > 0:
            e.wind = max(0, e.wind - dt)
            if e.wind == 0:
                if e.attack == "charge":
                    e.dash = 0.5
                elif e.attack == "leap":
                    e.x, e.y = e.tx, e.ty
                    self.shake = max(self.shake, 8)
                    self.add_fx("shock", e.x, e.y, 120, 0.5, self.boss_color(e))
                    self.add_fx("crack", e.x, e.y, 120, 0.6, (60, 40, 40))
            return
        if e.dash > 0:
            e.dash = max(0, e.dash - dt)
            self.move_enemy(e, e.ax * 640 * dt, e.ay * 640 * dt)
            self.confine_boss(e)
            if distance(e.x, e.y, px, py) < e.radius + 18:
                self.take_damage(e.damage * 1.2, self.enemy_name(e), (e.x, e.y))
            return
        d = distance(e.x, e.y, px, py)
        speed = e.speed * (1.25 if e.phase == 2 else 1)
        nx, ny = direction(px - e.x, py - e.y)
        if d > 330:
            self.move_enemy(e, nx * speed * dt, ny * speed * dt)
        elif d < 210:
            self.move_enemy(e, -nx * speed * dt, -ny * speed * dt)
        else:
            self.move_enemy(e, -ny * e.side * speed * 0.7 * dt, nx * e.side * speed * 0.7 * dt)
        self.confine_boss(e)
        if self.surface():
            self.camp_push(e)
        if e.pat:
            self.tick_pattern(e, dt)
        elif e.cd <= 0:
            script = BOSS_SCRIPTS[key][e.phase]
            self.start_pattern(e, script[e.bp % len(script)])
            e.bp += 1

    def confine_boss(self, e):
        if self.arena:
            d = distance(e.x, e.y, self.arena["x"], self.arena["y"])
            if d > self.arena["r"] - 50:
                fx, fy = direction(e.x - self.arena["x"], e.y - self.arena["y"])
                e.x, e.y = self.arena["x"] + fx * (self.arena["r"] - 50), self.arena["y"] + fy * (self.arena["r"] - 50)

    def start_pattern(self, e, name):
        px, py = self.p["x"], self.p["y"]
        f = 1 + 0.12 * (e.phase - 1)
        e.ax, e.ay = direction(px - e.x, py - e.y)
        e.pat, e.pi = name, 0.0
        e.ba = random.uniform(0, math.tau)
        e.flash = 0.2
        col = self.boss_color(e)
        self.floater(e.x, e.y - e.radius - 34, PATTERN_NAMES[name], col)
        self.visual_ring(e.x, e.y, 60, col)
        if name in ("ring", "fan"):
            e.pt = 2.4
        elif name == "spiral":
            e.pt = 3.4
        elif name == "rain":
            e.pt = 3.0
        elif name == "slam":
            e.pt = 1.9
            for k in range(e.phase + 1):
                ox, oy = (0, 0) if k == 0 else (random.randint(-170, 170), random.randint(-170, 170))
                burst = {"n": 10, "ring": True, "speed": 170, "r": 7, "color": col} if e.phase >= 2 and k == 0 else None
                self.danger(e, 0.9 / f, 95, clamp(px + ox, 80, WW - 80), clamp(py + oy, 80, WH - 80), burst=burst)
            self.danger(e, 0.9 / f, 140, burst={"n": 12, "ring": True, "speed": 160, "r": 7, "color": col})
        elif name == "laser":
            e.pt = 2.8
            self.laser_set(e, 0.0)
        elif name == "summon":
            e.pt = 1.4
            self.summon_minions(e)
        elif name in ("charge", "leap"):
            e.pat, e.pt = "", 0
            e.attack, e.cd = name, 1.5
            e.wind = 0.75 / f if name == "charge" else 0.8 / f
            if name == "leap":
                e.tx, e.ty = px, py
                if self.arena:
                    d = distance(px, py, self.arena["x"], self.arena["y"])
                    if d > self.arena["r"] - 90:
                        fx, fy = direction(px - self.arena["x"], py - self.arena["y"])
                        e.tx, e.ty = self.arena["x"] + fx * (self.arena["r"] - 90), self.arena["y"] + fy * (self.arena["r"] - 90)
                self.danger(e, e.wind, 115, e.tx, e.ty, burst={"n": 8, "ring": True, "speed": 170, "r": 7, "color": col})

    def laser_set(self, e, offset):
        f = 1 + 0.12 * (e.phase - 1)
        base = math.atan2(e.ay, e.ax) + offset
        n = 3 + (e.phase - 1)
        for k in range(n):
            ang = base + (k - (n - 1) / 2) * 0.5
            old = (e.ax, e.ay)
            e.ax, e.ay = math.cos(ang), math.sin(ang)
            self.danger(e, 0.95 / f, line=480, width=28)
            e.ax, e.ay = old

    def summon_minions(self, e):
        enemies = self.current()["enemies"]
        if len(enemies) >= ZONE_ENEMY_CAP + 4:
            return
        kinds = BOSS_SUMMON[self.boss_key(e)]
        for _ in range(2 if e.phase < 2 else 3):
            kind = random.choice(kinds)
            for _try in range(20):
                ang = random.uniform(0, math.tau)
                x, y = e.x + math.cos(ang) * 120, e.y + math.sin(ang) * 120
                if not self.blocked(x, y, 16):
                    m = self.make_enemy(kind, x, y, e.zone, self.area_kind() != "zone")
                    m.cd, m.room = 1.5, e.room
                    enemies.append(m)
                    self.burst(x, y, PURPLE, 10)
                    break

    def tick_pattern(self, e, dt):
        px, py = self.p["x"], self.p["y"]
        f = 1 + 0.12 * (e.phase - 1)
        dmg = e.damage * 0.5
        col = self.boss_color(e)
        src = self.enemy_name(e)
        e.pt -= dt
        e.pi -= dt
        name = e.pat
        if name == "ring" and e.pi <= 0:
            e.pi = 0.85 / f
            n = 12 + 4 * e.phase
            for k in range(n):
                self.shoot(e.x, e.y, e.ba + k * math.tau / n, 150 * f, dmg, 7, col, 0, 3.6, src)
            e.ba += math.pi / n
        elif name == "fan" and e.pi <= 0:
            e.pi = 0.55 / f
            base = math.atan2(py - e.y, px - e.x)
            n = 3 + 2 * e.phase
            for k in range(n):
                self.shoot(e.x, e.y, base + (k - (n - 1) / 2) * 0.17, 215 * f, dmg, 6, col, 0, 3.4, src)
        elif name == "spiral" and e.pi <= 0:
            e.pi = 0.075
            arms = e.phase + 1
            for k in range(arms):
                self.shoot(e.x, e.y, e.ba + k * math.tau / arms, 160 * f, dmg * 0.9, 6, col, 0, 3.6, src)
            e.ba += 0.33
        elif name == "rain" and e.pi <= 0:
            e.pi = 0.11 / f
            x = px + random.uniform(-440, 440)
            self.shoot(x, py - 420, math.pi / 2 + random.uniform(-0.08, 0.08), 260 * f, dmg, 7, col, 0, 3.0, src)
        elif name == "laser" and e.pt <= 1.5 and e.ba >= 0:
            e.ba = -1.0
            e.ax, e.ay = direction(px - e.x, py - e.y)
            self.laser_set(e, 0.25)
        if e.pt <= 0:
            e.pat = ""
            e.cd = max(0.4, 1.0 - 0.2 * (e.phase - 1))

    # ----------------------------------------------------------- arena
    def update_arena(self, dt):
        world = self.world()
        zi = self.zone_index()
        boss = next((e for e in self.current()["enemies"] if e.kind == "boss"), None)
        if self.arena and boss is None:
            self.arena = None
        if boss is None or not world.arena_xy:
            return
        ax, ay = world.arena_xy
        d = distance(self.p["x"], self.p["y"], ax, ay)
        if not boss.awake:
            if d < W.ARENA_R - 40:
                if self.p["zonekills"][zi] >= ARENA_KILLS:
                    boss.awake = 1
                    boss.cd = 1.5
                    self.arena = {"x": ax, "y": ay, "r": W.ARENA_R}
                    info = BOSSES[boss.zone]
                    self.banner = {"t": 0.0, "title": info["name"], "sub": info["title"], "color": info["color"]}
                    self.bullets.clear()
                    self.shake = max(self.shake, 8)
                    self.sound("win")
                else:
                    fx, fy = direction(self.p["x"] - ax, self.p["y"] - ay)
                    self.p["x"], self.p["y"] = ax + fx * (W.ARENA_R - 36), ay + fy * (W.ARENA_R - 36)
                    self.ripples.append([math.atan2(fy, fx), 1.0])
                    if self.time - self.last_seal_msg > 3:
                        self.last_seal_msg = self.time
                        self.notify("Печать арены не пускает. Победи ещё {} врагов региона.".format(ARENA_KILLS - self.p["zonekills"][zi]), RED)
        elif self.arena and d > W.ARENA_R - 20:
            fx, fy = direction(self.p["x"] - ax, self.p["y"] - ay)
            self.p["x"], self.p["y"] = ax + fx * (W.ARENA_R - 22), ay + fy * (W.ARENA_R - 22)

    # --------------------------------------------------- hazards/bullets
    def update_hazards(self, dt):
        enemies = self.current()["enemies"]
        for h in list(self.hazards):
            if h["owner"] is not None and not h["linger"] and h["owner"] not in enemies:
                self.hazards.remove(h)
                continue
            if h["done"] and h["linger"] > 0:
                h["linger"] -= dt
                h["tick"] -= dt
                if h["tick"] <= 0:
                    h["tick"] = 0.5
                    if (distance(self.p["x"], self.p["y"], h["x"], h["y"]) <= h["radius"] + 8 and not self.near_camp()):
                        self.take_damage(h["ldmg"], h["src"], (h["x"], h["y"]))
                if h["linger"] <= 0:
                    self.hazards.remove(h)
                continue
            h["delay"] -= dt
            if h["delay"] > 0:
                continue
            if not h["done"]:
                h["done"] = True
                if h["damage"] > 0:
                    if h["line"]:
                        inside = segment_distance(self.p["x"], self.p["y"], h["x"], h["y"],
                                                  h["x"] + h["dx"] * h["line"], h["y"] + h["dy"] * h["line"]) <= h["width"] + 14
                    else:
                        inside = distance(self.p["x"], self.p["y"], h["x"], h["y"]) <= h["radius"] + 14
                    if inside and not self.near_camp():
                        self.take_damage(h["damage"], h["src"], (h["x"], h["y"]), h["owner"])
                if h["burst"]:
                    base = math.atan2(h["dy"], h["dx"]) if not h["burst"].get("ring") else random.uniform(0, math.tau)
                    self.fire_burst(h["x"], h["y"], base, h["burst"], h["bdmg"], h["src"])
                self.burst(h["x"], h["y"], RED, 5)
                if h["line"]:
                    self.add_fx("beam", h["x"], h["y"], h["line"], 0.25, (255, 220, 140), (h["dx"], h["dy"], h["width"]))
                elif h["damage"] > 0:
                    self.add_fx("shock", h["x"], h["y"], h["radius"], 0.4, (255, 190, 120))
                    if h["radius"] >= 90:
                        self.add_fx("crack", h["x"], h["y"], h["radius"], 0.6, (60, 40, 40))
                        self.shake = max(self.shake, 5)
                if h["linger"] > 0:
                    h["tick"] = 0.5
                    continue
            h["life"] -= dt
            if h["life"] <= 0 and h["linger"] <= 0:
                self.hazards.remove(h)

    def update_bullets(self, dt):
        world = self.world()
        px, py = self.p["x"], self.p["y"]
        camp = self.camp() if self.surface() else None
        for b in list(self.bullets):
            b["age"] += dt
            b["life"] -= dt
            if b["home"] > 0 and b["age"] < 2.6:
                cur = math.atan2(b["dy"], b["dx"])
                want = math.atan2(py - b["y"], px - b["x"])
                diff = (want - cur + math.pi) % math.tau - math.pi
                cur += clamp(diff, -b["home"] * dt, b["home"] * dt)
                b["dx"], b["dy"] = math.cos(cur), math.sin(cur)
            steps = max(1, int(b["speed"] * dt // 8) + 1)
            gone = False
            for _ in range(steps):
                b["x"] += b["dx"] * b["speed"] * dt / steps
                b["y"] += b["dy"] * b["speed"] * dt / steps
                if not 20 < b["x"] < WW - 20 or not 20 < b["y"] < WH - 20 or world.props_blocked(b["x"], b["y"], b["r"]):
                    gone = True
                    break
                if camp and distance(b["x"], b["y"], *camp) < CAMP_R:
                    self.ripples.append([math.atan2(b["y"] - camp[1], b["x"] - camp[0]), 1.0])
                    gone = True
                    break
                if self.p["invuln"] <= 0 and distance(b["x"], b["y"], px, py) < b["r"] + 11:
                    self.take_damage(b["dmg"], b["src"], (b["ox"], b["oy"]))
                    gone = True
                    break
            if gone or b["life"] <= 0:
                self.bullets.remove(b)

    def update_projectiles(self, dt):
        for shot in list(self.projectiles):
            shot["life"] -= dt
            removed = False
            speed = shot.get("speed", 540)
            steps = max(1, math.ceil(speed * dt / 9))
            for _ in range(steps):
                shot["x"] += shot["dx"] * speed * dt / steps
                shot["y"] += shot["dy"] * speed * dt / steps
                if (not 25 < shot["x"] < WW - 25 or not 25 < shot["y"] < WH - 25
                        or self.world().props_blocked(shot["x"], shot["y"], 5)):
                    removed = True
                    break
                target = next((e for e in self.current()["enemies"]
                               if id(e) not in shot.get("hit", ()) and distance(shot["x"], shot["y"], e.x, e.y) < e.radius + 7), None)
                if target:
                    self.hit(target, shot["mult"], shot.get("dtype", "magic"))
                    if shot.get("pierce", 0) > 0:
                        shot["pierce"] -= 1
                        shot["hit"].append(id(target))
                    else:
                        removed = True
                        break
            if removed or shot["life"] <= 0:
                if shot in self.projectiles:
                    self.projectiles.remove(shot)
