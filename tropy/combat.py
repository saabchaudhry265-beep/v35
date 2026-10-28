"""Stats, items, hits, kills, skills and loot (mixin for Game)."""
import math
import random

from .common import *
from .content import *
from .models import Item, Enemy
from .meta import DIFFICULTY
from . import world as W

ITEM_NAMES = {
    "sword": ["Меч следопыта", "Стальной клинок", "Рунный меч"],
    "spear": ["Копьё дозорного", "Охотничья пика", "Рунное копьё"],
    "staff": ["Посох искр", "Посох хранителя", "Рунный посох"],
    "hammer": ["Молот кузнеца", "Боевой молот", "Рунный молот"],
    "bow": ["Охотничий лук", "Длинный лук", "Рунный лук"],
}
ELITE_KINDS = ("slime", "wolf", "bat", "spore", "wisp", "golem", "archer", "ghost", "scarab", "shaman", "imp", "magma", "cultist")
ELITE_NAMES = {"fast": "Стремительный", "armored": "Бронированный", "vampiric": "Кровожадный", "explosive": "Взрывной"}
ARMOR_NAMES = ["Куртка следопыта", "Доспех стража", "Пепельная броня"]
AMULET_NAMES = ["Лесной оберег", "Печать руин", "Звезда пустошей"]
BOSS_KINDS = ("boss", "finalboss", "miniboss")


class CombatMixin:
    # ------------------------------------------------------------ stats
    def rank(self, sid):
        return self.p["skills"].get(sid, 0)

    def buffed(self, name):
        return self.buffs.get(name, 0) > 0

    def mod_count(self, mod):
        n = self.relics.get(mod, 0)
        for it in self.p["equip"].values():
            if it:
                n += it.mods.count(mod)
        return n

    def meta_rank(self, name):
        return self.meta["upgrades"].get(name, 0) if self.mode == "abyss" else 0

    def char_id(self):
        return self.p.get("char", 0)

    def equipped(self, key):
        return sum(getattr(it, key) for it in self.p["equip"].values() if it)

    def max_hp(self):
        mult = 1 + 0.06 * self.rank("tough") + 0.10 * self.mod_count("vital") + 0.05 * self.meta_rank("hp")
        if self.mode == "abyss" and "frail" in self.heat:
            mult *= 0.75
        return int((80 + self.p["vit"] * 8 + self.equipped("hp")) * mult)

    def damage(self):
        base = 8 + self.p["str"] * 1.6 + self.equipped("power")
        mult = 1 + 0.06 * self.rank("might") + 0.10 * self.mod_count("might") + 0.04 * self.meta_rank("dmg")
        rage = self.mod_count("rage")
        if rage:
            mult += min(0.5, (1 - self.p["hp"] / max(1, self.max_hp())) * 0.6 * rage)
        return base * mult * (1.35 if self.buffed("cry") else 1)

    def defense(self):
        return self.equipped("armor") + 2 * self.rank("armor")

    def crit(self):
        bonus = 8 if self.char_id() == 1 else 0
        return min(70, self.p["agi"] * 1.2 + self.equipped("crit") + 4 * self.rank("crit") + 6 * self.mod_count("sharp") + bonus)

    def cdr(self):
        return max(0.4, 1 - 0.07 * self.rank("focus") - (0.15 if self.char_id() == 2 else 0))

    def move_speed(self):
        mult = (1.2 if self.buffed("cry") else 1) * (1 + 0.08 * self.mod_count("swift")) * (1.1 if self.char_id() == 1 else 1)
        return (185 + self.p["agi"] * 0.8) * mult

    def weapon(self):
        item = self.p["equip"]["weapon"]
        return item.weapon if item else "sword"

    def weapon_tier(self):
        item = self.p["equip"]["weapon"]
        return item.tier if item else 0

    def resist(self, e, dtype):
        if e.kind == "finalboss":
            table = BOSSES[3]["res"]
        elif e.kind == "boss":
            table = BOSSES[e.zone]["res"]
        else:
            table = ENEMIES[e.kind]["res"]
        return table.get(dtype, 1.0)

    # ------------------------------------------------------------ world
    def area_kind(self, key=None):
        key = key or self.area
        for prefix, kind in (("zone", "zone"), ("dg", "dungeon"), ("pass", "pass"), ("final", "final"), ("abyss", "abyss")):
            if key.startswith(prefix):
                return kind
        return "zone"

    def world(self):
        return self.worlds[self.area]

    def current(self):
        return self.areas[self.area]

    def blocked(self, x, y, radius):
        return self.worlds[self.area].blocked(x, y, radius)

    def move(self, x, y, dx, dy, radius):
        nx = clamp(x + dx, 30 + radius, WW - 30 - radius)
        if not self.blocked(nx, y, radius):
            x = nx
        ny = clamp(y + dy, 30 + radius, WH - 30 - radius)
        if not self.blocked(x, ny, radius):
            y = ny
        return x, y

    def move_enemy(self, e, dx, dy):
        oldx, oldy = e.x, e.y
        e.x, e.y = self.move(e.x, e.y, dx, dy, e.radius)
        if distance(oldx, oldy, e.x, e.y) < math.hypot(dx, dy) * 0.3:
            e.x, e.y = self.move(e.x, e.y, -dy * e.side, dx * e.side, e.radius)

    def surface(self):
        return self.area_kind() == "zone"

    def zone_index(self):
        kind = self.area_kind()
        if kind == "zone":
            return int(self.area[-1])
        if kind == "dungeon":
            return DUNGEONS[self.area]["zone"]
        if kind == "pass":
            return int(self.area[-1])
        if kind == "abyss":
            return self.run["zi"]
        return 2

    def camp(self):
        return self.worlds[self.area].camp_xy if self.area in self.worlds else None

    def near_camp(self):
        c = self.camp()
        return bool(c) and distance(self.p["x"], self.p["y"], *c) < CAMP_R - 20

    def zone_factor(self):
        return (1 + 0.35 * self.zone_index()) * self.scale_mul

    # ---------------------------------------------------------- enemies
    def make_enemy(self, kind, x, y, zi, dungeon=False, elite=None):
        info = ENEMIES[kind]
        scale = ZONES[zi]["scale"] * (1.18 if dungeon else 1) * self.scale_mul
        if kind == "finalboss":
            scale = 1
        hp_mul = dmg_mul = spd_mul = 1.0
        if self.mode == "campaign":
            diff = DIFFICULTY[self.settings["difficulty"]]
            hp_mul, dmg_mul = diff[1], diff[2]
        else:
            if "tough" in self.heat:
                hp_mul = 1.3
            if "fury" in self.heat:
                dmg_mul = 1.25
            if "swift" in self.heat:
                spd_mul = 1.15
        if elite is None:
            chance = {"zone": 0.06, "dungeon": 0.10, "pass": 0.10, "abyss": min(0.3, 0.10 + 0.01 * self.run.get("floor", 1))}.get(self.area_kind(), 0)
            elite = random.choice(list(ELITE_NAMES)) if kind in ELITE_KINDS and random.random() < chance else ""
        hp = info["hp"] * scale * hp_mul * (2.2 if elite == "armored" else 1)
        speed = info["speed"] * spd_mul * (1.4 if elite == "fast" else 1)
        e = Enemy(x, y, kind, zi, hp, hp, info["dmg"] * scale * dmg_mul, speed, info["r"], x, y, side=random.choice((-1, 1)))
        e.elite = elite
        return e

    def make_boss(self, zi, x, y, awake=0):
        e = self.make_enemy("boss", x, y, zi)
        e.awake = awake
        return e

    def ensure_area(self, key):
        if key in self.areas:
            return
        kind = self.area_kind(key)
        if kind == "final":
            self.worlds[key] = W.build_final()
            boss = self.make_enemy("finalboss", WW / 2, 850, 2)
            boss.awake = 1
            self.areas[key] = {"enemies": [boss], "drops": [], "reward": False}
        elif kind == "dungeon":
            idx = DUNGEON_IDS.index(key)
            self.worlds[key] = W.build_dungeon(key, DUNGEONS[key], cleared=self.p["dungeons"][idx])
            self.areas[key] = {"enemies": [], "drops": [], "reward": False}
        elif kind == "pass":
            i = int(key[-1])
            self.worlds[key] = W.build_pass(i, PASSES[i], cleared=self.p["passes"][i])
            self.areas[key] = {"enemies": [], "drops": [], "reward": False}
        elif kind == "zone":
            zi = int(key[-1])
            self.worlds[key] = W.build_zone(zi)
            self.areas[key] = {"enemies": [], "drops": [], "reward": False}
            for _ in range(14):
                self.spawn_regular(key)
            if not self.p["bosses"][zi]:
                ax, ay = self.worlds[key].arena_xy
                self.areas[key]["enemies"].append(self.make_boss(zi, ax, ay))

    def spawn_regular(self, key=None):
        key = key or self.area
        if not key.startswith("zone"):
            return
        zi = int(key[-1])
        world = self.worlds[key]
        table = SPAWN[zi]
        kind = random.choices(list(table), weights=list(table.values()))[0]
        pack = random.randint(1, PACKS.get(kind, 1))
        camp, arena = world.camp_xy, world.arena_xy
        for _ in range(120):
            x, y = random.randint(95, WW - 95), random.randint(95, WH - 95)
            if distance(x, y, *camp) < 300 or distance(x, y, *arena) < W.ARENA_R + 60:
                continue
            if key == self.area and abs(x - self.p["x"]) < VW / 2 + 80 and abs(y - self.p["y"]) < VH / 2 + 80:
                continue
            if world.blocked(x, y, 22):
                continue
            for k in range(pack):
                ex, ey = x + random.randint(-45, 45), y + random.randint(-45, 45)
                if world.blocked(ex, ey, 16):
                    ex, ey = x, y
                self.areas[key]["enemies"].append(self.make_enemy(kind, ex, ey, zi))
            return

    # ------------------------------------------------------------- loot
    def roll_mods(self, slot, rarity):
        n = {0: 0, 1: 0, 2: 1, 3: 1, 4: 2}[rarity]
        if rarity == 3 and random.random() < 0.4:
            n = 2
        pool = MOD_POOL[slot]
        return random.sample(pool, min(n, len(pool)))

    def make_item(self, zi, reward=False, slot=None, min_rarity=None):
        weights = [0, 0, 30, 45, 25] if reward else [48, 28, 15, 7, 2]
        if min_rarity:
            weights = [w if i >= min_rarity else 0 for i, w in enumerate(weights)]
            if not any(weights):
                weights[min_rarity] = 1
        rarity = random.choices(range(5), weights=weights)[0]
        if self.mod_count("fortune"):
            rarity = max(rarity, random.choices(range(5), weights=weights)[0])
        slot = slot or random.choice(list(SLOTS))
        weapon = random.choice(list(WEAPONS)) if slot == "weapon" else "sword"
        mult = RARITIES[rarity][2] * (1 + zi * 0.55)
        power = armor = crit = hp = 0
        if slot == "weapon":
            power = max(3, int(random.randint(4, 7) * mult))
            crit = rarity + random.randint(0, 3)
            name = ITEM_NAMES[weapon][zi]
        elif slot == "armor":
            armor = max(1, int(random.randint(2, 4) * mult))
            hp = int(random.randint(5, 10) * mult)
            name = ARMOR_NAMES[zi]
        else:
            power = int(random.randint(1, 3) * mult)
            crit = int(random.randint(2, 4) * mult)
            hp = int(random.randint(3, 7) * mult)
            name = AMULET_NAMES[zi]
        return Item(name, slot, rarity, power, armor, crit, hp, weapon, False, zi, 0, self.roll_mods(slot, rarity))

    def make_unique(self, uid):
        u = UNIQUES[uid]
        return Item(u["name"], u["slot"], 4, u.get("power", 0), u.get("armor", 0), u.get("crit", 0), u.get("hp", 0),
                    u.get("weapon", "sword"), True, u["tier"], 0, list(u["mods"]))

    def add_drop(self, x, y, item):
        ang = random.uniform(0, math.tau)
        d = random.uniform(24, 56)
        fx, fy = x + math.cos(ang) * d, y + math.sin(ang) * d
        if self.blocked(fx, fy, 6):
            fx, fy = x, y
        self.current()["drops"].append({"x": fx, "y": fy, "ox": x, "oy": y, "item": item, "age": 0.0})
        if item.rarity >= 3:
            self.shake = max(self.shake, 5)
            self.sound("level" if item.rarity == 4 else "win")

    def add_item(self, item, x=None, y=None):
        if len(self.p["inv"]) < 60:
            self.p["inv"].append(item)
            self.sound("loot")
            self.notify("Получено: " + item.title, item.color)
            return True
        if x is not None:
            self.add_drop(x, y, item)
            self.notify("Сумка полна. Предмет оставлен на земле.", RED)
        else:
            self.notify("Сумка полна: освободи место.", RED)
        return False

    # ------------------------------------------------------ fx helpers
    def floater(self, x, y, text, color=TEXT):
        self.floaters.append([x, y, str(text), color, 1.0])

    def burst(self, x, y, color, count=9):
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(25, 145)
            self.particles.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed, random.uniform(0.2, 0.6), color])

    def sparkle(self, x, y, color, count=10, spread=26):
        for _ in range(count):
            self.particles.append([x + random.uniform(-spread, spread), y + random.uniform(-6, 6),
                                   random.uniform(-14, 14), random.uniform(-90, -30), random.uniform(0.4, 0.9), color])

    def visual_ring(self, x, y, radius, color):
        self.particles.append([x, y, 0, 0, 0.35, color, radius])

    def add_fx(self, kind, x, y, size, life, color=(255, 200, 120), extra=None):
        if len(self.fx) < 80:
            self.fx.append([kind, x, y, size, life, life, color, extra])

    def level_up(self):
        while self.p["xp"] >= self.p["xpnext"]:
            self.p["xp"] -= self.p["xpnext"]
            self.p["level"] += 1
            self.p["points"] += 3
            self.p["sp"] += 2
            self.p["xpnext"] = int(self.p["xpnext"] * 1.17 + 5)
            self.p["hp"] = self.max_hp()
            self.p["potions"] = min(8, self.p["potions"] + 1)
            self.levelfx = {"t": 0.0, "level": self.p["level"]}
            self.shake = max(self.shake, 7)
            self.flash = max(self.flash, 0.35)
            self.burst(self.p["x"], self.p["y"], GOLD, 26)
            self.notify("Уровень {}! +3 очка героя (C), +2 очка навыков (K).".format(self.p["level"]), GOLD)
            self.sound("level")

    # ------------------------------------------------------ taking hits
    def take_damage(self, amount, src=None, pos=None, by=None):
        if self.state != "play" or self.p["hp"] <= 0 or self.p["invuln"] > 0:
            return
        ghosty = self.mod_count("ghosty")
        if ghosty and random.random() < min(0.4, 0.08 * ghosty):
            self.floater(self.p["x"], self.p["y"] - 30, "уклон", BLUE)
            self.p["invuln"] = 0.3
            return
        dealt = max(1, amount * 25 / (25 + self.defense()))
        if self.char_id() == 0:
            dealt *= 0.9
        guard = self.mod_count("guard")
        if guard and random.random() < min(0.45, 0.15 * guard):
            dealt *= 0.5
            self.floater(self.p["x"], self.p["y"] - 40, "блок", BLUE)
        if src:
            self.last_hit = {"src": src, "t": 2.5, "pos": pos}
        if self.shield > 0:
            absorbed = min(self.shield, dealt)
            self.shield -= absorbed
            dealt -= absorbed
            self.floater(self.p["x"], self.p["y"] - 40, "щит", BLUE)
            if self.shield <= 0:
                self.buffs["shield"] = 0
        self.p["invuln"] = 0.55
        self.hurt_t = 0.3
        self.hint("telegraph")
        thorns = self.mod_count("thorns")
        if thorns:
            self.visual_ring(self.p["x"], self.p["y"], 110, (255, 120, 80))
            for e in list(self.current()["enemies"]):
                if distance(self.p["x"], self.p["y"], e.x, e.y) < 110 + e.radius:
                    self.hit(e, 0.8 * thorns, "none")
        if dealt <= 0:
            self.burst(self.p["x"], self.p["y"], BLUE, 5)
            return
        if by is not None and by.elite == "vampiric":
            by.hp = min(by.maxhp, by.hp + dealt * 0.6)
        if self.p["hp"] - dealt <= 0 and self.mod_count("second") and not self.second_used:
            self.second_used = True
            self.p["hp"] = self.max_hp() * 0.3
            self.floater(self.p["x"], self.p["y"] - 50, "ВТОРОЕ ДЫХАНИЕ", GOLD)
            self.add_fx("shock", self.p["x"], self.p["y"], 160, 0.5, GOLD)
            self.flash = max(self.flash, 0.4)
            return
        self.p["hp"] = max(0, self.p["hp"] - dealt)
        self.shake = max(self.shake, 4)
        self.rumble(0.4, 0.7, 160)
        if self.settings["numbers"]:
            self.floater(self.p["x"], self.p["y"] - 24, "-" + str(int(dealt)), RED)
        self.burst(self.p["x"], self.p["y"], RED, 6)
        self.sound("hurt")
        if self.p["hp"] <= 0:
            self.set_state("dead")
            self.pending_save = True
            self.meta["stats"]["deaths"] += 1
            self.profile_dirty = True
            self.on_player_death()

    def hit(self, enemy, multiplier=1, dtype=None):
        if enemy not in self.current()["enemies"] or enemy.hp <= 0:
            return
        if enemy.kind in BOSS_KINDS and (not enemy.awake or (enemy.attack == "transform" and enemy.wind > 0)):
            if enemy.awake or self.time - self.last_immune > 1:
                self.last_immune = self.time
                self.floater(enemy.x, enemy.y - enemy.radius - 10, "неуязвим", MUTED)
            return
        if enemy.attack == "burrow" and enemy.dash > 0:
            return
        dtype = dtype or DTYPES[self.weapon()]
        res = 1.0 if dtype == "none" else self.resist(enemy, dtype)
        crit = random.random() * 100 < self.crit()
        damage = self.damage() * multiplier * (1.8 if crit else 1) * res
        if self.char_id() == 2 and dtype == "magic":
            damage *= 1.15
        tag = " КРИТ" if crit else ""
        if dtype != "none" and self.mod_count("heavy"):
            self.hit_counter += 1
            if self.hit_counter % 5 == 0:
                damage *= 2.5
                tag += " ТЯЖЁЛЫЙ"
        echo = self.mod_count("echo")
        if echo and random.random() < 0.15 * echo:
            damage *= 2
            tag += " ЭХО"
        enemy.hp -= damage
        enemy.flash = 0.12
        color = GOLD if crit else TEXT
        if res >= 1.25:
            tag += " ▲"
            color = (255, 170, 70)
        elif res <= 0.7:
            tag += " ▼"
            color = MUTED
        if res >= 1.25 and dtype != "none":
            self.meta["stats"]["weak_hits"] += 1
        if self.settings["numbers"] or tag:
            self.floater(enemy.x, enemy.y - enemy.radius, (str(int(damage)) if self.settings["numbers"] else "") + tag, color)
        self.burst(enemy.x, enemy.y, GOLD if crit else (255, 170, 70) if res >= 1.25 else BLUE, 4 + int(crit) * 3)
        heal = 0.02 * self.rank("vamp") + 0.03 * self.mod_count("lifesteal")
        if heal:
            self.p["hp"] = min(self.max_hp(), self.p["hp"] + damage * heal)
        if self.mod_count("burn"):
            enemy.burn = 3.0
        if self.mod_count("frost"):
            enemy.slow = 2.0
        if crit and self.mod_count("chain") and not self.chaining:
            self.chaining = True
            near = sorted((o for o in self.current()["enemies"] if o is not enemy),
                          key=lambda o: distance(o.x, o.y, enemy.x, enemy.y))[:2]
            for o in near:
                if distance(o.x, o.y, enemy.x, enemy.y) < 240:
                    self.bolts.append([(enemy.x, enemy.y), (o.x, o.y), 0.25, random.randint(0, 99)])
                    self.hit(o, 0.6 * self.mod_count("chain"), "magic")
            self.chaining = False
        kx, ky = direction(enemy.x - self.p["x"], enemy.y - self.p["y"])
        if self.weapon() == "hammer" and dtype == "blunt":
            kx, ky = kx * 1.7, ky * 1.7
        force = {"slime": 420, "slimelet": 420, "wolf": 420, "bat": 380, "spore": 380, "wisp": 300, "golem": 260,
                 "archer": 400, "ghost": 300, "scarab": 300, "shaman": 400, "imp": 380, "magma": 330,
                 "cultist": 380, "miniboss": 120, "boss": 90, "finalboss": 60}[enemy.kind]
        enemy.kx, enemy.ky = kx * force, ky * force
        if crit:
            self.hitstop = max(self.hitstop, 0.035)
        self.sound("hit")
        if enemy.hp <= 0:
            self.kill(enemy)

    def dot_damage(self, e, amount):
        e.hp -= amount
        e.flash = max(e.flash, 0.05)
        if e.hp <= 0:
            self.kill(e)

    def kill(self, e):
        enemies = self.current()["enemies"]
        if e in enemies:
            enemies.remove(e)
        self.deaths.append([e.x, e.y, e.kind, e.radius, 0.0, e.zone])
        self.burst(e.x, e.y, ZONES[e.zone]["boss_color"], 18)
        self.p["kills"] += 1
        self.run_stats["kills"] += 1
        self.meta["stats"]["kills"] += 1
        self.profile_dirty = True
        if e.elite:
            self.meta["stats"]["elites"] = self.meta["stats"].get("elites", 0) + 1
            self.floater(e.x, e.y - 40, ELITE_NAMES[e.elite].upper(), GOLD)
            if e.elite == "explosive":
                for k in range(8):
                    self.shoot(e.x, e.y, k * math.tau / 8, 170, e.damage * 0.5, 7, (255, 160, 60), 0, 3.0, "Взрыв")
                self.add_fx("shock", e.x, e.y, 100, 0.4, (255, 160, 60))
        wis = (1 + 0.08 * self.rank("wisdom") + 0.15 * self.mod_count("xp"))
        gold_mul = 1 + 0.25 * self.mod_count("gold") + 0.10 * self.meta_rank("gold")
        zf = self.zone_factor()
        if self.mod_count("killheal"):
            self.p["hp"] = min(self.max_hp(), self.p["hp"] + 4 * self.mod_count("killheal"))
        if self.mod_count("blast") and not self.blasting:
            self.blasting = True
            self.visual_ring(e.x, e.y, 90, (255, 150, 60))
            for o in list(enemies):
                if distance(o.x, o.y, e.x, e.y) < 90 + o.radius:
                    self.hit(o, 0.5 * self.mod_count("blast"), "magic")
            self.blasting = False
        if e.kind == "finalboss":
            self.p["complete"] = True
            self.p["gold"] += int(300 * gold_mul)
            self.p["xp"] += int(350 * wis)
            self.bullets.clear()
            self.hazards.clear()
            self.arena = None
            self.shake, self.flash, self.slowmo = 16, 1.0, 1.2
            self.quest_event("boss", 3)
            self.level_up()
            self.add_item(Item("Рассвет Эльдории", "amulet", 4, power=10, crit=10, hp=65, unique=True, tier=2,
                               mods=["vital", "might", "sharp"]), e.x, e.y)
            self.sound("win")
            self.pending_save = True
            self.start_cutscene(OUTRO, lambda: self.set_state("victory"))
            return
        if self.area_kind() == "zone":
            self.p["zonekills"][e.zone] += 1
        if e.kind == "boss":
            self.on_boss_killed(e, wis, gold_mul)
            self.level_up()
            return
        if e.kind == "miniboss":
            self.bullets.clear()
            self.hazards = [h for h in self.hazards if h.get("linger")]
            self.shake, self.flash = 10, 0.5
            self.p["gold"] += int(60 * zf * gold_mul)
            self.p["xp"] += int(90 * zf * wis)
            self.burst(e.x, e.y, GOLD, 30)
            self.floater(e.x, e.y - 50, "СТРАЖ ПОВЕРЖЕН", GOLD)
            self.sound("win")
            self.quest_event("miniboss", 0)
        else:
            elite_mul = 2.5 if e.elite else 1
            diff_bonus = DIFFICULTY[self.settings["difficulty"]][1] if self.mode == "campaign" else 1.0
            self.p["gold"] += int((random.randint(3, 7) + e.zone * 2) * gold_mul * self.scale_mul * elite_mul * max(1.0, diff_bonus))
            self.p["xp"] += max(1, int(ENEMIES[e.kind]["xp"] * 1.3 * (1 + 0.35 * e.zone) * self.scale_mul ** 0.5 * wis * elite_mul * max(1.0, diff_bonus)))
            chance = (0.30 if self.area_kind() != "abyss" else 0.12) * (1.5 if self.mod_count("fortune") else 1) + (0.5 if e.elite else 0)
            if e.kind != "slimelet" and random.random() < chance:
                self.add_drop(e.x, e.y, self.make_item(e.zone))
            if random.random() < 0.055:
                self.p["potions"] = min(8, self.p["potions"] + 1)
                self.floater(e.x, e.y - 35, "+1 зелье", GREEN)
            self.quest_event("kill", e.kind, e.zone)
            if e.kind in ENEMY_ORDER and e.kind not in self.p["seen"]:
                self.p["seen"].append(e.kind)
            if e.kind == "magma":
                for sx in (-1, 1):
                    m = self.make_enemy("slimelet", e.x + sx * 22, e.y, e.zone, self.area_kind() == "dungeon")
                    m.room = e.room
                    m.cd = 1.0
                    enemies.append(m)
        self.level_up()

    def on_boss_killed(self, e, wis, gold_mul):
        self.p["bosses"][e.zone] = True
        self.p["gold"] += int((80 + e.zone * 45) * gold_mul)
        self.p["xp"] += int((125 + e.zone * 65) * wis * 1.5)
        self.add_drop(e.x, e.y, self.make_unique("boss%d" % e.zone))
        for _ in range(2):
            self.add_drop(e.x, e.y, self.make_item(e.zone, True))
        self.bullets.clear()
        self.hazards = [h for h in self.hazards if h.get("linger")]
        self.arena = None
        self.shake, self.flash, self.slowmo = 14, 0.8, 1.0
        self.burst(e.x, e.y, GOLD, 40)
        self.floater(e.x, e.y - 60, "ХРАНИТЕЛЬ ПОВЕРЖЕН", GOLD)
        self.notify(ZONES[e.zone]["boss"] + " повержен! Путь вперёд открыт.")
        self.sound("win")
        self.pending_save = True
        self.quest_event("boss", e.zone)

    # -------------------------------------------------------- attacking
    def autoaim(self):
        px, py = self.p["x"], self.p["y"]
        best, best_d = None, 320
        for e in self.current()["enemies"]:
            if not e.awake and e.kind in BOSS_KINDS:
                continue
            d = distance(px, py, e.x, e.y) - e.radius
            if d < best_d:
                best, best_d = e, d
        if best:
            self.p["face_x"], self.p["face_y"] = direction(best.x - px, best.y - py)

    def in_combat(self):
        return any(distance(self.p["x"], self.p["y"], e.x, e.y) < 420 and (e.awake or e.kind not in BOSS_KINDS)
                   for e in self.current()["enemies"]) or self.arena is not None

    def attack(self, special=False, pulse=False):
        if self.state != "play" or self.p["hp"] <= 0:
            return
        px, py = self.p["x"], self.p["y"]
        fx, fy = self.p["face_x"], self.p["face_y"]
        kind = self.weapon()
        cdr = self.cdr()
        if pulse:
            if self.p["pulse_cd"] > 0:
                return
            self.p["pulse_cd"] = 6 * cdr
            self.visual_ring(px, py, 115, BLUE)
            self.add_fx("shock", px, py, 115, 0.35, BLUE)
            self.shake = max(self.shake, 3)
            for e in list(self.current()["enemies"]):
                if distance(px, py, e.x, e.y) <= 115 + e.radius:
                    self.hit(e, 1.0, "none")
            return
        cd = "skill_cd" if special else "attack_cd"
        if self.p[cd] > 0:
            return
        self.p[cd] = (8 if special else {"sword": 0.4, "spear": 0.55, "staff": 0.65, "hammer": 0.85, "bow": 0.5}[kind]) * cdr
        twin = self.mod_count("twin")
        self.swing = 0.22
        self.swing_special = special
        self.lunge = 0.12
        if kind == "staff":
            angles = [-0.30, -0.15, 0, 0.15, 0.30] if special else ([0] if not twin else [-0.12, 0.12][:1 + min(1, twin)])
            angle = math.atan2(fy, fx)
            for offset in angles:
                self.projectiles.append({"x": px + fx * 23, "y": py + fy * 23, "dx": math.cos(angle + offset),
                                         "dy": math.sin(angle + offset), "life": 0.9, "mult": 1.6 if special else 1.2,
                                         "dtype": "magic", "pierce": 0, "speed": 540, "arrow": False, "hit": []})
            return
        if kind == "bow":
            angle = math.atan2(fy, fx)
            offsets = [-0.07, 0, 0.07] if special else ([0] if not twin else [-0.1, 0.1])
            for offset in offsets:
                self.projectiles.append({"x": px + fx * 20, "y": py + fy * 20, "dx": math.cos(angle + offset),
                                         "dy": math.sin(angle + offset), "life": 0.9, "mult": 1.6 if special else 1.1,
                                         "dtype": "pierce", "pierce": 3 if special else 1, "speed": 780, "arrow": True, "hit": []})
            self.sound("swing")
            return
        if kind == "hammer" and special:
            self.visual_ring(px, py, 170, (255, 190, 100))
            self.add_fx("shock", px, py, 170, 0.5, (255, 190, 100))
            self.add_fx("crack", px, py, 170, 0.7, (80, 60, 50))
            self.shake = max(self.shake, 9)
            self.sound("boom")
            for e in list(self.current()["enemies"]):
                if distance(px, py, e.x, e.y) <= 170 + e.radius:
                    e.slow = max(e.slow, 1.5)
                    e.cd += 0.8
                    self.hit(e, 2.4)
            return
        if special and kind == "sword":
            self.visual_ring(px, py, 150, GOLD)
            self.add_fx("shock", px, py, 150, 0.4, GOLD)
            self.shake = max(self.shake, 4)
            for e in list(self.current()["enemies"]):
                if distance(px, py, e.x, e.y) <= 150 + e.radius:
                    self.hit(e, 1.6)
            return
        reach = 285 if special else (155 if kind == "spear" else 105 if kind == "hammer" else 90)
        self.slashes.append([px, py, math.atan2(fy, fx), reach, 0.18, 0.18, "thrust" if kind == "spear" else "arc", GOLD])
        targets = []
        for e in self.current()["enemies"]:
            if kind == "spear":
                valid = segment_distance(e.x, e.y, px, py, px + fx * reach, py + fy * reach) <= e.radius + 17
            else:
                dx, dy = e.x - px, e.y - py
                d = math.hypot(dx, dy)
                valid = d <= reach + e.radius and (d < 24 or (dx * fx + dy * fy) / max(d, 1) >= 0.1)
            if valid:
                targets.append(e)
        targets.sort(key=lambda e: distance(px, py, e.x, e.y))
        for e in targets[:(20 if special else (3 if kind == "spear" else 2)) + twin]:
            self.hit(e, 1.9 if special else (0.9 if kind == "spear" else 1.9 if kind == "hammer" else 1))
        if kind == "hammer":
            self.shake = max(self.shake, 3)
            self.sound("boom")

    def potion(self):
        if self.p["hp"] >= self.max_hp():
            self.notify("Здоровье уже полное.")
        elif self.p["potions"] <= 0:
            self.notify("Нет зелий. Купи их в лагере или найди у врагов.", RED)
        else:
            self.p["potions"] -= 1
            mult = 1 + 0.12 * self.rank("elixir") + 0.30 * self.mod_count("potion")
            heal = max(40, int(self.max_hp() * 0.4 * mult))
            self.p["hp"] = min(self.max_hp(), self.p["hp"] + heal)
            self.floater(self.p["x"], self.p["y"] - 30, "+" + str(heal), GREEN)
            self.sparkle(self.p["x"], self.p["y"], GREEN, 18, 18)
            self.visual_ring(self.p["x"], self.p["y"], 40, GREEN)
            self.sound("loot")

    def dash(self):
        if self.p["dash_cd"] <= 0:
            self.p["dash_cd"] = 1.4 * self.cdr()
            self.p["dash"] = 0.18
            self.p["invuln"] = max(self.p["invuln"], 0.26)
            self.sound("dash")
            n = self.mod_count("dashblast")
            if n:
                self.add_fx("shock", self.p["x"], self.p["y"], 110, 0.35, (255, 170, 80))
                for e in list(self.current()["enemies"]):
                    if distance(self.p["x"], self.p["y"], e.x, e.y) < 110 + e.radius:
                        self.hit(e, 1.2 * n, "none")

    # ----------------------------------------------------------- skills
    def use_skill(self, key):
        sid = ACTIVE_KEYS.get(key)
        if self.state != "play" or not sid:
            return
        if not self.rank(sid):
            self.notify("Навык не изучен. Открой дерево навыков: K.", MUTED)
            return
        if self.skill_cd[sid] > 0:
            return
        info = SKILLS[sid]
        self.skill_cd[sid] = info["cd"] * self.cdr()
        px, py = self.p["x"], self.p["y"]
        enemies = self.current()["enemies"]
        if sid == "cry":
            self.buffs["cry"] = 7
            self.visual_ring(px, py, 90, (255, 120, 90))
            self.floater(px, py - 44, "БОЕВОЙ КЛИЧ", (255, 150, 100))
            self.shake = max(self.shake, 4)
        elif sid == "shield":
            self.shield = 90 + self.p["level"] * 6
            self.buffs["shield"] = 8
            self.visual_ring(px, py, 70, BLUE)
            self.floater(px, py - 44, "ЩИТ СВЕТА", BLUE)
        elif sid == "chain":
            current, hit = (px, py), []
            for _ in range(5):
                options = [e for e in enemies if e not in hit and distance(current[0], current[1], e.x, e.y) < (420 if not hit else 260)
                           and (e.awake or e.kind not in BOSS_KINDS)]
                if not options:
                    break
                tgt = min(options, key=lambda e: distance(current[0], current[1], e.x, e.y))
                self.bolts.append([current, (tgt.x, tgt.y), 0.3, random.randint(0, 99)])
                hit.append(tgt)
                current = (tgt.x, tgt.y)
            for e in hit:
                self.hit(e, 2.0, "magic")
            if not hit:
                self.skill_cd[sid] = 1.0
                self.notify("Нет целей для молнии.", MUTED)
        elif sid == "meteor":
            near = [e for e in enemies if distance(px, py, e.x, e.y) < 520 and (e.awake or e.kind not in BOSS_KINDS)]
            if near:
                tgt = min(near, key=lambda e: distance(px, py, e.x, e.y))
                tx, ty = tgt.x, tgt.y
            else:
                tx, ty = px + self.p["face_x"] * 260, py + self.p["face_y"] * 260
            self.meteors.append({"x": tx, "y": ty, "t": 0.0, "delay": 0.85, "r": 125})
        self.sound("level")

    def update_skills(self, dt):
        for sid in self.skill_cd:
            self.skill_cd[sid] = max(0, self.skill_cd[sid] - dt)
        for name in list(self.buffs):
            self.buffs[name] = max(0, self.buffs[name] - dt)
        if self.mod_count("chill"):
            for e in self.current()["enemies"]:
                if distance(e.x, e.y, self.p["x"], self.p["y"]) < 130:
                    e.slow = max(e.slow, 0.3)
        if not self.buffs.get("shield"):
            self.shield = 0
        for b in list(self.bolts):
            b[2] -= dt
            if b[2] <= 0:
                self.bolts.remove(b)
        for m in list(self.meteors):
            m["t"] += dt
            if m["t"] >= m["delay"]:
                self.meteors.remove(m)
                self.shake = max(self.shake, 11)
                self.visual_ring(m["x"], m["y"], m["r"], (255, 150, 70))
                self.add_fx("shock", m["x"], m["y"], m["r"], 0.5, (255, 150, 70))
                self.burst(m["x"], m["y"], (255, 150, 70), 30)
                for e in list(self.current()["enemies"]):
                    if distance(m["x"], m["y"], e.x, e.y) <= m["r"] + e.radius:
                        self.hit(e, 3.2, "magic")
        orbs = self.mod_count("orbit")
        if orbs:
            self.orb_t += dt * 3.2
            n = min(6, orbs * 2)
            for k in range(n):
                a = self.orb_t + k * math.tau / n
                ox, oy = self.p["x"] + math.cos(a) * 62, self.p["y"] + math.sin(a) * 62
                for e in list(self.current()["enemies"]):
                    if distance(ox, oy, e.x, e.y) < e.radius + 12 and self.orb_cd.get(id(e), 0) <= 0:
                        self.orb_cd[id(e)] = 0.4
                        self.hit(e, 0.45, "magic")
            for key in list(self.orb_cd):
                self.orb_cd[key] -= dt
                if self.orb_cd[key] <= 0:
                    del self.orb_cd[key]
