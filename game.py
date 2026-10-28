"""Тропы Эльдории — action RPG. Запуск: python game.py"""
import datetime
import math
import os
import random
import shutil
import sys
import traceback

import pygame

from tropy import common as C
from tropy.common import *
from tropy.content import *
from tropy.content import legacy_char
from tropy.models import Item, Enemy
from tropy.combat import CombatMixin
from tropy.ai import AIMixin
from tropy.audio import AudioMixin
from tropy.ui2 import UI2Mixin
from tropy.inputmap import PAD_BUTTONS, dead, key_label, LABELS, ACTIONS, DEFAULT_KEYS
from tropy.meta import ACHIEVEMENTS, HINTS, DIFFICULTY, HEAT, HEAT_BONUS, daily_seed
from tropy.render import RenderMixin
from tropy.ui import UIMixin
from tropy.saves import SaveMixin
from tropy import world as W
from tropy import art

SPRITES = (
    ["enemy_slime", "enemy_wolf", "enemy_golem", "enemy_bat",
     "enemy_archer", "enemy_shaman", "enemy_finalboss", "boss_forest", "boss_ruins", "boss_ash", "enemy_spore",
     "enemy_wisp", "enemy_ghost", "enemy_scarab", "enemy_imp", "enemy_magma", "enemy_cultist"]
    + ["npc_" + n for n in NPCS] + ["char%d_%s" % (c, v) for c in range(3) for v in ("down", "up", "side")]
)


class Game(SaveMixin, CombatMixin, AIMixin, AudioMixin, RenderMixin, UI2Mixin, UIMixin):
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        # Pygame font handles become unsafe after pygame.quit(); every new Game
        # instance starts with a fresh font subsystem and must drop old handles.
        art.reset_font_cache()
        pygame.display.set_caption("Тропы Эльдории")
        try:
            pygame.display.set_icon(pygame.image.load(str(ASSETS_PATH() / "icon.png")))
        except (OSError, pygame.error):
            pass
        self.clock = pygame.time.Clock()
        self.canvas = pygame.Surface((VW, VH))
        self.fonts = self.load_fonts()
        self.load_settings()
        self.load_profile()
        self.keys = self.settings["keys"]
        self.window = None
        self.viewport = pygame.Rect(0, 0, VW, VH)
        self.apply_display()
        self.sprites = {}
        for name in SPRITES:
            try:
                self.sprites[name] = pygame.image.load(str(ASSETS_PATH() / (name + ".png"))).convert_alpha()
            except (OSError, pygame.error):
                pass
        self.sprite_cache = {}
        self.focus = True
        self.dark = None
        self._known_rects = []
        art.LOWFX[0] = self.settings["lowfx"]
        self.init_audio()
        self.slot = 1
        self.joys = {}
        self.pad_active = False
        self.focus_pos = None
        self.nav_cd = 0.0
        self.rebinding = None
        self.settings_tab = 0
        self.slots_mode = "load"
        self.slots_confirm = None
        self.records_tab = 0
        self.error_times = []
        self.hint_text, self.hint_t = "", 0.0
        self.ach_toasts = []
        self.check_t = 0.0
        self.play_accum = 0.0
        self.profile_dirty = False
        self.heat = set()
        self.seed_text = ""
        self.fps_smooth = 60.0
        self.confirm_abandon = False
        self.run_rng = random.Random()

        self.state = "menu"
        self.back_state = "menu"
        self.session = False
        self.running = True
        self.worlds, self.terrain_cache, self.mini_cache = {}, {}, {}
        self.areas = {}
        self.area = "zone0"
        self.buttons = []
        self.inv_page = 0
        self.discard_index = None
        self.confirm_new = False
        self.toast, self.toast_color, self.toast_time = "", GOLD, 0
        self.autosave_time = 0
        self.pending_save = False
        self.time = 0.0
        self.vignette = None
        self.menu_index = 0
        self.last_backup = -1e9
        self.journal_tab = 0
        self.creator = {"char": 0, "mode": "campaign"}
        self.cut = None
        self.mode = "campaign"
        self.relics, self.run, self.run_stats = {}, {"floor": 1, "zi": 0, "shards": 0}, {"kills": 0}
        self.scale_mul = 1.0
        self.return_area = "zone0"
        self.boon = None
        self.arena = None
        self.last_immune = self.last_seal_msg = -10.0
        self.p = self.new_player()
        self.reset_runtime()
        self.menu_index = self.first_menu_index()
        self.init_pads()

    def load_fonts(self):
        fonts = {}
        regular = C.ASSETS / "fonts" / "DejaVuSansCondensed.ttf"
        bold = C.ASSETS / "fonts" / "DejaVuSansCondensed-Bold.ttf"
        for size in (14, 17, 21, 32):
            try:
                fonts[size] = pygame.font.Font(str(bold if size in (21, 32) else regular), size)
            except (OSError, pygame.error):
                fonts[size] = pygame.font.SysFont("dejavusans,arial", size, bold=size in (21, 32))
        return fonts

    # ------------------------------------------------------------ setup
    def reset_runtime(self):
        self.projectiles, self.hazards, self.particles, self.floaters = [], [], [], []
        self.slashes, self.bolts, self.meteors, self.bullets = [], [], [], []
        self.ripples, self.ghosts, self.deaths = [], [], []
        self.buffs = {}
        self.skill_cd = {sid: 0.0 for sid, s in SKILLS.items() if "key" in s}
        self.shield = 0.0
        self.shake = self.flash = self.hitstop = self.slowmo = self.hurt_t = 0.0
        self.swing = self.lunge = 0.0
        self.swing_special = False
        self.moving = False
        self.ghost_timer = self.step_timer = 0.0
        self.banner = None
        self.fx = []
        self.second_used = False
        self.hit_counter = 0
        self.last_hit = None
        self.orb_t = 0.0
        self.orb_cd = {}
        self.chaining = self.blasting = False
        self.rock_t = 0.0
        self.transition = None
        self.dialog = None
        self.levelfx = None
        self.seen_bosses = set()
        self.p["invuln"] = self.p["dash"] = 0
        if self.area in self.areas:
            for e in self.areas[self.area]["enemies"]:
                e.wind = e.dash = 0
                e.cd = max(e.cd, 0.8)

    def transient_clear(self):
        self.projectiles.clear(); self.hazards.clear(); self.particles.clear(); self.floaters.clear()
        self.slashes.clear(); self.bolts.clear(); self.meteors.clear(); self.bullets.clear()
        self.ripples.clear(); self.ghosts.clear(); self.deaths.clear(); self.fx.clear()
        self.second_used = False
        self.swing = self.lunge = 0.0
        self.p["invuln"] = self.p["dash"] = 0
        if self.area in self.areas:
            for e in self.current()["enemies"]:
                e.wind = e.dash = 0
                e.kx = e.ky = 0.0
                e.cd = max(e.cd, 0.8)

    def new_player(self):
        return {
            "x": CAMP[0], "y": CAMP[1] + 90, "hp": 120, "level": 1, "xp": 0, "xpnext": 40, "char": 0,
            "str": 5, "vit": 5, "agi": 5, "points": 0, "sp": 0, "gold": 35, "potions": 3, "kills": 0,
            "zonekills": [0, 0, 0], "bosses": [False] * 3, "chests": [[], [], []], "dungeons": [False] * 6, "passes": [False] * 2,
            "complete": False, "equip": {"weapon": None, "armor": None, "amulet": None}, "inv": [],
            "face_x": 0.0, "face_y": 1.0, "attack_cd": 0.0, "skill_cd": 0.0, "pulse_cd": 0.0,
            "dash_cd": 0.0, "dash": 0.0, "invuln": 0.0, "return_x": CAMP[0], "return_y": CAMP[1],
            "name": "Странник", "skills": {}, "quests": {}, "seen": [], "playtime": 0,
        }

    def make_world(self, key):
        return W.build_zone(int(key[-1]))

    def char(self):
        ch = CHARACTERS[self.p.get("char", 0)]
        return ch if self.p["name"] == ch["name"] else legacy_char(self.p["name"], ch["gender"])

    def apply_character(self, ch):
        p = self.p
        p["char"], p["name"] = ch["id"], ch["name"]
        p["str"], p["vit"], p["agi"] = ch["stats"]
        p["skills"][ch["skill"][0]] = ch["skill"][1]
        kind = ch["weapon"]
        names = {"sword": "Походный меч", "spear": "Походное копьё", "staff": "Походный посох"}
        p["equip"]["weapon"] = Item(names[kind], "weapon", 0, power=4, weapon=kind)
        extra = ch["item"]
        p["equip"][extra["slot"]] = Item(extra["name"], extra["slot"], 1, extra.get("power", 0), extra.get("armor", 0),
                                         extra.get("crit", 0), extra.get("hp", 0))
        p["hp"] = self.max_hp()

    def build_worlds(self):
        for key in self.areas:
            self.worlds[key] = self.make_world(key)

    # ------------------------------------------------- sound and display
    def apply_display(self):
        full = self.settings["fullscreen"]
        flags = pygame.FULLSCREEN if full else pygame.RESIZABLE
        size = (0, 0) if full else RESOLUTIONS[self.settings["resolution"]]
        try:
            self.window = pygame.display.set_mode(size, flags)
        except pygame.error:
            self.settings["fullscreen"] = False
            self.settings["resolution"] = 1
            self.window = pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
        self.update_viewport()

    def update_viewport(self):
        self.window = pygame.display.get_surface() or self.window
        w, h = self.window.get_size()
        scale = min(w / VW, h / VH)
        sw, sh = max(1, int(VW * scale)), max(1, int(VH * scale))
        self.viewport = pygame.Rect((w - sw) // 2, (h - sh) // 2, sw, sh)

    def mouse(self, pos=None):
        pos = pos or pygame.mouse.get_pos()
        if not self.viewport.collidepoint(pos):
            return None
        return ((pos[0] - self.viewport.x) * VW / self.viewport.w, (pos[1] - self.viewport.y) * VH / self.viewport.h)

    def notify(self, message, color=GOLD):
        self.toast, self.toast_color, self.toast_time = message, color, 5.5

    def set_state(self, state):
        self.state = state
        self.buttons = []
        self.discard_index = None
        self.focus_pos = None
        self.confirm_abandon = False
        self.rebinding = None
        if state == "menu":
            self.menu_index = self.first_menu_index()
        elif state != "slots":
            self.confirm_new = False
            self.slots_confirm = None
        self.update_music()

    def start_new(self):
        self.open_slots("new")

    def open_slots(self, mode):
        self.slots_mode = mode
        self.slots_confirm = None
        self.back_state = "menu"
        self.set_state("slots")

    def choose_slot(self, n):
        info = self.slot_info(n)
        if self.slots_mode == "load":
            if info:
                self.load_game(n)
            return
        if info and self.slots_confirm != n:
            self.slots_confirm = n
            self.notify("Слот занят. Нажми ещё раз, чтобы начать заново (старое сохранение уйдёт в архив).", GOLD)
            return
        self.slot = n
        self.creator = {"char": 0, "mode": "campaign"}
        self.set_state("creator")

    def delete_slot(self, n):
        if self.slots_confirm != -n:
            self.slots_confirm = -n
            self.notify("Нажми «Удалить» ещё раз для подтверждения.", RED)
            return
        for path in self.save_candidates(n):
            if path.exists() and (n != 1 or path.name.startswith("eldoria_v35")):
                try:
                    path.unlink()
                except OSError:
                    pass
        self.slots_confirm = None
        self.notify("Слот очищен.")

    def start_abyss_menu(self):
        self.creator = {"char": 0, "mode": "abyss"}
        self.back_state = "menu"
        self.set_state("creator")

    def finish_creator(self):
        ch = CHARACTERS[self.creator["char"]]
        if self.creator.get("mode") == "abyss":
            self.start_abyss(ch)
            return
        if self.session and self.mode == "campaign":
            self.save_game(quiet=True)
        if not self.archive_save(self.slot):
            return
        self.mode, self.relics, self.scale_mul = "campaign", {}, 1.0
        self.p = self.new_player()
        self.apply_character(ch)
        self.areas, self.worlds, self.terrain_cache, self.mini_cache = {}, {}, {}, {}
        self.area = self.return_area = "zone0"
        camp = W.zone_camp(0)
        self.p["x"], self.p["y"] = camp[0], camp[1] + 90
        self.p["return_x"], self.p["return_y"] = self.p["x"], self.p["y"]
        self.session = True
        self.ensure_area(self.area)
        self.reset_runtime()
        self.pending_save = True

        def begin():
            self.back_state = "play"
            self.set_state("help")
            self.notify("Поговори со Старейшиной у костра (знак «!»).")
        self.start_cutscene(INTRO, begin)

    def start_cutscene(self, slides, done):
        self.cut = {"slides": slides, "i": 0, "t": 0.0, "done": done}
        self.set_state("cutscene")

    def advance_cutscene(self):
        cut = self.cut
        text = fmt(cut["slides"][cut["i"]]["text"], self.char())
        if cut["t"] * 38 < len(text):
            cut["t"] = len(text) / 38
            return
        cut["i"] += 1
        cut["t"] = 0.0
        if cut["i"] >= len(cut["slides"]):
            self.finish_cutscene()

    def finish_cutscene(self):
        cb = self.cut["done"]
        self.cut = None
        cb()

    # ----------------------------------------------------------- quests
    def quest_state(self, qid):
        return self.p["quests"].get(qid, {"s": 0, "n": 0})

    def quest_progress(self, qid):
        q = QUESTS[qid]
        if q["kind"] == "boss":
            done = self.p["complete"] if q["target"] == 3 else self.p["bosses"][q["target"]]
            return (1 if done else 0), q["n"]
        if q["kind"] == "dungeon":
            z = q["target"]
            return sum(self.p["dungeons"][z * 2:z * 2 + 2]), q["n"]
        return min(self.quest_state(qid)["n"], q["n"]), q["n"]

    def quest_status(self, qid):
        q = QUESTS[qid]
        s = self.quest_state(qid)["s"]
        if s == 3:
            return "done"
        if s == 2:
            return "ready"
        if s == 1:
            have, need = self.quest_progress(qid)
            return "ready" if have >= need else "active"
        if "after" in q and self.quest_status(q["after"]) != "done":
            return "locked"
        if q.get("boss_req") is not None and not self.p["bosses"][q["boss_req"]]:
            return "locked"
        return "available"

    def quest_event(self, kind, target, zone=None):
        for qid, q in QUESTS.items():
            st = self.quest_state(qid)
            if st["s"] != 1:
                continue
            if q["kind"] == "kill" and kind == "kill" and q["target"] == target and st["n"] < q["n"]:
                st["n"] += 1
                self.p["quests"][qid] = st
                self.floater(self.p["x"], self.p["y"] - 60, "{} {}/{}".format(q["title"], st["n"], q["n"]), GREEN)
            elif q["kind"] == "collect" and kind == "kill" and zone == q["zone"] and st["n"] < q["n"] and random.random() < q["chance"]:
                st["n"] += 1
                self.p["quests"][qid] = st
                self.floater(self.p["x"], self.p["y"] - 60, "+1 " + q["target"], GOLD)
            if self.quest_status(qid) == "ready" and not st.get("notified"):
                self.notify("Задание «{}» выполнено! Вернись к {}.".format(q["title"], NPCS[q["giver"]]["name"]), GREEN)

    def npc_marker(self, npc):
        statuses = [self.quest_status(qid) for qid, q in QUESTS.items() if q["giver"] == npc]
        if "ready" in statuses:
            return "?"
        if "available" in statuses:
            return "!"
        if "active" in statuses:
            return "."
        return None

    def open_dialog(self, npc):
        quests = [(qid, self.quest_status(qid)) for qid, q in QUESTS.items() if q["giver"] == npc]
        ready = next((qid for qid, st in quests if st == "ready"), None)
        avail = next((qid for qid, st in quests if st == "available"), None)
        active = next((qid for qid, st in quests if st == "active"), None)
        close = ("Закрыть", self.close_dialog)
        if ready:
            text, buttons = QUESTS[ready]["done"], [("Забрать награду", lambda: self.claim_quest(ready))]
        elif avail:
            q = QUESTS[avail]
            text = "{}: {}".format(q["title"], q["text"])
            buttons = [("Принять", lambda: self.accept_quest(avail)), ("Позже", self.close_dialog)]
        elif active:
            have, need = self.quest_progress(active)
            text = "Как успехи? «{}»: {}/{}. {}".format(QUESTS[active]["title"], have, need, QUESTS[active]["text"])
            buttons = [close]
        else:
            text, buttons = random.choice(NPC_IDLE[npc]), [close]
        self.dialog = {"npc": npc, "text": fmt(text, self.char()), "buttons": buttons, "t": 0.0}
        self.set_state("dialog")

    def close_dialog(self):
        self.dialog = None
        self.set_state("play")

    def accept_quest(self, qid):
        self.p["quests"][qid] = {"s": 1, "n": 0}
        self.notify("Задание принято: " + QUESTS[qid]["title"], GOLD)
        self.sound("loot")
        self.pending_save = True
        self.close_dialog()

    def claim_quest(self, qid):
        q = QUESTS[qid]
        r = q["reward"]
        self.p["quests"][qid] = {"s": 3, "n": self.quest_state(qid)["n"]}
        self.p["gold"] += r.get("gold", 0)
        self.p["xp"] += int(r.get("xp", 0) * (1 + 0.08 * self.rank("wisdom")))
        self.p["potions"] = min(8, self.p["potions"] + r.get("potions", 0))
        if r.get("sp"):
            self.p["sp"] += r["sp"]
        if r.get("item"):
            self.add_item(self.make_item(NPCS[q["giver"]]["zone"], True, min_rarity=r["item"]))
        self.notify("Награда за «{}» получена!".format(q["title"]), GREEN)
        self.sparkle(self.p["x"], self.p["y"], GOLD, 20)
        self.sound("win")
        self.level_up()
        self.pending_save = True
        self.close_dialog()

    # ---------------------------------------------------------- skills
    def req_ok(self, sid):
        req = SKILLS[sid]["req"]
        return req is None or self.rank(req[0]) >= req[1]

    def can_buy(self, sid):
        s = SKILLS[sid]
        return self.rank(sid) < s["max"] and self.req_ok(sid) and self.p["sp"] >= s.get("cost", 1)

    def buy_skill(self, sid):
        if self.can_buy(sid):
            self.p["sp"] -= SKILLS[sid].get("cost", 1)
            self.p["skills"][sid] = self.rank(sid) + 1
            self.hp_cap()
            self.sound("level")
            self.notify("Изучено: " + SKILLS[sid]["name"], GOLD)
            self.pending_save = True

    def hp_cap(self):
        self.p["hp"] = min(self.p["hp"], self.max_hp())

    # ------------------------------------------------------------ smith
    def upgrade_cost(self, item):
        return 35 * (item.plus + 1) * (1 + item.tier)

    def upgrade_item(self, slot):
        item = self.p["equip"][slot]
        if not item or item.plus >= 5:
            return
        cost = self.upgrade_cost(item)
        if self.p["gold"] < cost:
            self.notify("Не хватает золота.", RED)
            return
        self.p["gold"] -= cost
        item.plus += 1
        if slot == "weapon":
            item.power += 2 + item.tier
            item.crit += 1
        elif slot == "armor":
            item.armor += 1
            item.hp += 4
        else:
            item.power += 1
            item.crit += 1
            item.hp += 5
        self.sound("win")
        self.notify("Улучшено: " + item.title, item.color)
        self.pending_save = True

    # ----------------------------------------------------- world / POIs
    def available_pois(self):
        zi = self.zone_index()
        result = []
        for poi in self.world().pois:
            if poi["kind"] == "chest" and poi["id"] in self.p["chests"][zi]:
                continue
            if poi["kind"] == "portal" and self.p["complete"]:
                continue
            result.append(poi)
        area = self.current()
        if area["reward"]:
            rx, ry = area.get("reward_pos", (WW / 2, WH / 2))
            result.append({"kind": "reward", "x": rx, "y": ry})
        return result

    def nearest_interaction(self):
        options = []
        for poi in self.available_pois():
            d = distance(self.p["x"], self.p["y"], poi["x"], poi["y"])
            if d < (95 if poi["kind"] in ("gate_next", "gate_back", "portal") else 80):
                options.append((d, "poi", poi))
        for drop in self.current()["drops"]:
            d = distance(self.p["x"], self.p["y"], drop["x"], drop["y"])
            if d < 65 and drop.get("age", 9) > 0.5:
                options.append((d, "drop", drop))
        return min(options, key=lambda q: q[0]) if options else None

    def go(self, callback, duration=1.1):
        if not self.transition:
            self.transition = {"t": 0.0, "dur": duration, "cb": callback, "fired": False}

    def interact(self):
        result = self.nearest_interaction()
        if not result or self.transition:
            return
        _, kind, obj = result
        zi = self.zone_index()
        if kind == "drop":
            self.fly_item(obj)
            if self.add_item(obj["item"]):
                self.current()["drops"].remove(obj)
            return
        what = obj["kind"]
        if what == "camp":
            self.p["hp"] = self.max_hp()
            self.p["potions"] = max(self.p["potions"], 3)
            self.sparkle(self.p["x"], self.p["y"], (255, 190, 90), 14)
            self.notify("Отдых у костра: здоровье восстановлено, зелья пополнены до 3.")
            self.save_game()
        elif what == "npc":
            npc = obj["npc"]
            if npc == "merchant":
                self.set_state("shop")
            elif npc == "smith":
                self.set_state("smith")
            else:
                self.open_dialog(npc)
        elif what == "chest":
            self.p["chests"][zi].append(obj["id"])
            self.p["gold"] += int((12 + zi * 8) * (1 + 0.25 * self.mod_count("gold")))
            self.burst(obj["x"], obj["y"], GOLD, 24)
            self.shake = max(self.shake, 3)
            self.add_drop(obj["x"], obj["y"], self.make_item(zi))
            self.sound("loot")
            self.pending_save = True
        elif what == "entrance":
            idx = DUNGEON_IDS.index(obj["dg"])
            if self.p["dungeons"][idx]:
                self.notify("Это подземелье уже пройдено, награда получена.")
            else:
                self.go(lambda: self.enter(obj["dg"]))
        elif what in ("exit", "exit_back", "exit_fwd"):
            self.go(lambda: self.leave_through(what))
        elif what == "gate_next":
            nxt = zi + 1
            if not self.p["bosses"][zi]:
                self.notify("Путь закрыт. Победи хранителя: " + ZONES[zi]["boss"] + ".", RED)
            elif self.p["level"] < ZONES[nxt]["level"]:
                self.notify("Нужен уровень {} для региона «{}».".format(ZONES[nxt]["level"], ZONES[nxt]["name"]), RED)
            else:
                self.go(lambda: self.enter_pass(zi, True))
        elif what == "gate_back":
            self.go(lambda: self.enter_pass(zi - 1, False))
        elif what == "portal":
            if all(self.p["bosses"]):
                self.go(lambda: self.enter("final"))
            else:
                self.notify("Портал спит, пока не разрушены все три печати.", RED)
        elif what == "reward":
            self.claim_reward()
        elif what == "altar":
            self.world().pois.remove(obj)
            self.open_boon("Алтарь реликвий", self.relic_offers(3), "free")
        elif what == "stall":
            price = 40 + 12 * self.run["floor"]
            self.open_boon("Торговец Бездны", self.relic_offers(3, price), "shop")
        elif what == "stairs":
            self.go(self.next_floor)

    def claim_reward(self):
        zi = self.zone_index()
        area = self.current()
        area["reward"] = False
        if self.area_kind() == "dungeon":
            idx = DUNGEON_IDS.index(self.area)
            self.p["dungeons"][idx] = True
            item = self.make_unique(self.area)
            self.p["gold"] += int((90 + zi * 40) * (1 + 0.25 * self.mod_count("gold")))
            self.p["xp"] += int((90 + zi * 40) * (1 + 0.08 * self.rank("wisdom")))
            self.add_drop(*area.get("reward_pos", (WW / 2, WH / 2)), item)
            self.notify("Уникальная добыча подземелья: " + item.name, GOLD)
            self.p["sp"] += 1
            self.level_up()
        self.shake = max(self.shake, 5)
        self.pending_save = True

    def fly_item(self, drop):
        self.sparkle(drop["x"], drop["y"], drop["item"].color, 12, 10)

    def go_zone(self, zi, arrive_kind):
        self.transient_clear()
        self.area = self.return_area = "zone" + str(zi)
        self.ensure_area(self.area)
        poi = next(p for p in self.world().pois if p["kind"] == arrive_kind)
        camp = self.world().camp_xy
        dx, dy = direction(camp[0] - poi["x"], camp[1] - poi["y"])
        self.p["x"], self.p["y"] = poi["x"] + dx * 120, poi["y"] + dy * 120
        self.p["return_x"], self.p["return_y"] = self.p["x"], self.p["y"]
        self.pending_save = True
        self.banner = {"t": 0.0, "title": ZONES[zi]["name"], "sub": "Рекомендуемый уровень: " + str(ZONES[zi]["level"]), "color": GREEN}
        self.notify("Переход: " + ZONES[zi]["name"])

    def enter_pass(self, index, forward):
        self.return_area = self.area
        self.p["return_x"], self.p["return_y"] = self.p["x"], self.p["y"]
        self.transient_clear()
        key = "pass%d" % index
        self.areas.pop(key, None)
        self.worlds.pop(key, None)
        self.terrain_cache.pop(key, None)
        self.area = key
        self.ensure_area(key)
        room = self.world().rooms[0 if forward else -1]
        self.p["x"], self.p["y"] = room["center"][0], room["center"][1] + 40
        self.banner = {"t": 0.0, "title": PASSES[index]["name"], "sub": PASSES[index]["desc"], "color": PURPLE}
        self.pending_save = True

    def enter(self, key):
        self.return_area = self.area
        self.p["return_x"], self.p["return_y"] = self.p["x"], self.p["y"]
        self.transient_clear()
        self.areas.pop(key, None)
        self.worlds.pop(key, None)
        self.terrain_cache.pop(key, None)
        self.area = key
        self.ensure_area(key)
        if key == "final":
            self.p["x"], self.p["y"] = WW / 2, 1500
            self.notify("Сердце Пустоты ждёт. Выход находится позади.")
        else:
            c = self.world().rooms[0]["center"]
            self.p["x"], self.p["y"] = c[0], c[1] + 40
            self.banner = {"t": 0.0, "title": DUNGEONS[key]["name"], "sub": "Двери запираются, пока в комнате есть враги", "color": PURPLE}
        self.pending_save = True

    def leave_through(self, what):
        kind = self.area_kind()
        if kind == "pass":
            idx = int(self.area[-1])
            w = self.world()
            if any(r["state"] != "cleared" for r in w.rooms):
                self.notify("Сначала расправься с засадой.", RED)
                return
            self.p["passes"][idx] = True
            if what == "exit_fwd":
                self.go_zone(idx + 1, "gate_back")
            else:
                self.go_zone(idx, "gate_next")
            return
        self.leave_instance()

    def leave_instance(self):
        old = self.area
        self.transient_clear()
        self.area = self.return_area
        self.ensure_area(self.area)
        self.p["x"], self.p["y"] = self.p["return_x"], self.p["return_y"]
        for key in [k for k in self.areas if not k.startswith("zone")]:
            self.areas.pop(key, None)
            self.worlds.pop(key, None)
        self.pending_save = True
        self.notify("Ты вернулся в регион.")

    def equip(self, index):
        if not 0 <= index < len(self.p["inv"]):
            return
        item = self.p["inv"].pop(index)
        old = self.p["equip"][item.slot]
        self.p["equip"][item.slot] = item
        if old:
            self.p["inv"].append(old)
        self.hp_cap()
        self.discard_index = None
        self.notify("Экипировано: " + item.title, item.color)
        self.sparkle(self.p["x"], self.p["y"], item.color, 12)
        self.sound("loot")

    def discard(self, index):
        if not 0 <= index < len(self.p["inv"]):
            return
        item = self.p["inv"][index]
        if self.near_camp():
            if item.unique and self.discard_index != index:
                self.discard_index = index
                self.notify("Уникальный предмет! Нажми продажу ещё раз для подтверждения.")
                return
            self.p["gold"] += item.price
            self.p["inv"].pop(index)
            self.notify("Продано за " + str(item.price) + " золота.")
            self.discard_index = None
        elif self.discard_index == index:
            self.add_drop(self.p["x"], self.p["y"], self.p["inv"].pop(index))
            self.discard_index = None
            self.notify("Предмет оставлен на земле.")
        else:
            self.discard_index = index
            self.notify("Нажми «Выбросить» ещё раз для подтверждения.")

    def change_inv_page(self, step):
        self.inv_page += step
        self.discard_index = None

    def spend_point(self, key):
        if self.p["points"] > 0:
            self.p["points"] -= 1
            self.p[key] += 1

    def buy_potion(self):
        if self.p["potions"] >= 8:
            self.notify("Можно нести не больше 8 зелий.")
        elif self.p["gold"] < 20:
            self.notify("Не хватает золота.", RED)
        else:
            self.p["gold"] -= 20
            self.p["potions"] += 1
            self.notify("Зелье куплено.")
            self.sound("loot")

    def buy_weapon(self, kind):
        if self.p["gold"] < 55:
            self.notify("Не хватает золота.", RED)
            return
        zi = self.zone_index()
        names = {"sword": "Меч путешественника", "spear": "Копьё путешественника", "staff": "Посох путешественника"}
        item = Item(names[kind], "weapon", 1, power=7 + zi * 3, weapon=kind, tier=zi)
        if self.add_item(item):
            self.p["gold"] -= 55

    def respawn(self):
        self.p["gold"] = int(self.p["gold"] * 0.9)
        self.p["hp"] = self.max_hp()
        self.p["potions"] = max(2, self.p["potions"])
        self.transient_clear()
        self.area = self.return_area if self.area_kind() != "zone" else self.area
        for key in [k for k in self.areas if not k.startswith("zone")]:
            self.areas.pop(key, None)
            self.worlds.pop(key, None)
        self.ensure_area(self.area)
        zi = self.zone_index()
        self.arena = None
        for e in self.current()["enemies"]:
            e.x, e.y = e.home_x, e.home_y
            e.wind = e.dash = 0
            e.kx = e.ky = 0.0
            e.pat = ""
            e.cd = 1
            if e.kind == "boss":
                e.hp, e.phase, e.awake, e.attack = e.maxhp, 1, 0, ""
        camp = self.world().camp_xy
        self.p["x"], self.p["y"] = camp[0], camp[1] + 90
        for key in ("attack_cd", "skill_cd", "pulse_cd", "dash_cd"):
            self.p[key] = 0
        self.buffs.clear()
        self.shield = 0
        self.last_hit = None
        self.set_state("play")
        self.pending_save = True
        self.notify("Ты вернулся в лагерь. Потеряно 10% золота.")

    def continue_after_win(self):
        self.transient_clear()
        self.area = self.return_area = "zone2"
        for key in [k for k in self.areas if not k.startswith("zone")]:
            self.areas.pop(key, None)
            self.worlds.pop(key, None)
        self.ensure_area(self.area)
        camp = self.world().camp_xy
        self.p["x"], self.p["y"] = camp[0], camp[1] + 90
        self.p["hp"] = self.max_hp()
        self.set_state("play")
        self.pending_save = True
        self.notify("Эльдория спасена. Можно завершить задания или спуститься в Бездну!")

    def menu_rows(self):
        return [
            ("Продолжить сессию", self.resume, self.session),
            ("Загрузить игру", lambda: self.open_slots("load"), self.has_save()),
            ("Новая игра", self.start_new, True),
            ("Бездна (рогалик)", self.start_abyss_menu, True),
            ("Святилище душ", self.open_sanctum, True),
            ("Достижения и записи", self.open_records, True),
            ("Настройки", self.open_settings, True),
            ("Как играть", self.open_help, True),
            ("Сохранить и выйти" if self.session and self.mode == "campaign" else "Выйти", self.quit, True),
        ]

    def first_menu_index(self):
        return next((i for i, row in enumerate(self.menu_rows()) if row[2]), 0)

    def menu_move(self, step):
        rows = self.menu_rows()
        for _ in rows:
            self.menu_index = (self.menu_index + step) % len(rows)
            if rows[self.menu_index][2]:
                break

    def quit(self):
        if self.mode == "abyss" and self.session and not self.run.get("ended") and not self.confirm_abandon:
            self.confirm_abandon = True
            self.notify("Забег в Бездне будет потерян. Нажми ещё раз, чтобы выйти.", RED)
            return
        if self.mode == "abyss":
            self.end_run()
            self.running = False
        elif not self.session or self.save_game(quiet=True):
            self.running = False
        else:
            self.notify("Выход отменён: не удалось сохранить. F12 — выйти без сохранения.", RED)
        if self.running is False:
            self.save_profile()

    def to_menu(self):
        if self.mode == "abyss":
            if not self.run.get("ended") and not self.confirm_abandon:
                self.confirm_abandon = True
                self.notify("Забег в Бездне будет прерван. Нажми ещё раз для подтверждения.", RED)
                return
            self.end_run()
            self.session = False
            self.set_state("menu")
            return
        if not self.session or self.save_game():
            self.set_state("menu")

    def open_sanctum(self):
        self.set_state("sanctum")

    def buy_meta(self, key):
        name, desc, maxr, base = META[key]
        rank = self.meta["upgrades"].get(key, 0)
        cost = base * (rank + 1)
        if rank >= maxr or self.meta["shards"] < cost:
            return
        self.meta["shards"] -= cost
        self.meta["upgrades"][key] = rank + 1
        self.save_profile()
        self.sound("level")
        self.notify("Улучшено: " + name, PURPLE)

    def respec(self):
        spent = 0
        for sid, rank in self.p["skills"].items():
            spent += rank * SKILLS[sid].get("cost", 1)
        ch = CHARACTERS[self.p.get("char", 0)]
        self.p["skills"] = {ch["skill"][0]: ch["skill"][1]} if self.mode == "abyss" or self.p["name"] == ch["name"] else {}
        free = SKILLS[ch["skill"][0]].get("cost", 1) * ch["skill"][1] if self.p["skills"] else 0
        self.p["sp"] += spent - free
        self.hp_cap()
        self.notify("Навыки сброшены: очки возвращены.", GOLD)

    # ------------------------------------------------------ rooms
    def trap_phase(self, tr):
        ph = (self.time + tr[4]) % 3.0
        return "warn" if ph < 0.9 else "active" if ph < 1.6 else "off"

    def spawn_room(self, i):
        w = self.world()
        room = w.rooms[i]
        x, y, rw, rh = room["rect"]
        cx, cy = room["center"]
        zi = self.zone_index()
        kind = room["kind"]
        enemies = self.current()["enemies"]
        pool = SPAWN[min(2, zi)] if self.area_kind() != "pass" else SPAWN[min(2, zi + 1)]
        kinds, weights = list(pool), list(pool.values())
        floor = self.run["floor"] if self.mode == "abyss" else 1
        n = {"combat": 4 + zi + random.randint(0, 2) + (floor // 3 if self.mode == "abyss" else 0), "trap": 3}.get(kind, 2)
        if self.mode == "abyss" and "swarm" in self.heat and kind in ("combat", "trap"):
            n += 2

        def place(k, special=None):
            for attempt in range(90):
                ex, ey = random.randint(int(x + 70), int(x + rw - 70)), random.randint(int(y + 70), int(y + rh - 70))
                if w.blocked(ex, ey, 18) or (attempt < 60 and distance(ex, ey, self.p["x"], self.p["y"]) < 150):
                    continue
                e = special or self.make_enemy(k, ex, ey, zi, self.area_kind() != "pass")
                e.x = e.home_x = ex
                e.y = e.home_y = ey
                e.room, e.cd = i, random.uniform(0.8, 1.8)
                enemies.append(e)
                return e
        if kind in ("combat", "trap"):
            for _ in range(n):
                place(random.choices(kinds, weights=weights)[0])
        elif kind in ("miniboss", "boss"):
            if kind == "boss" and self.mode == "abyss" and self.run["floor"] % 3 == 0:
                boss = self.make_boss(min(2, (self.run["floor"] // 3 - 1) % 3), cx, cy, 1)
                boss.room = i
                enemies.append(boss)
                self.banner = {"t": 0.0, "title": BOSSES[boss.zone]["name"], "sub": BOSSES[boss.zone]["title"], "color": BOSSES[boss.zone]["color"]}
            else:
                e = self.make_enemy("miniboss", cx, cy, zi, True)
                e.awake, e.room = 1, i
                if self.area_kind() == "dungeon":
                    e.tag = DUNGEONS[self.area]["mini"]
                else:
                    e.tag = random.choice(["Страж Бездны", "Хранитель этажа", "Пожиратель душ"])
                enemies.append(e)
                self.banner = {"t": 0.0, "title": e.tag, "sub": "Страж подземелья", "color": ZONES[zi]["boss_color"]}
            for _ in range(2):
                place(random.choices(kinds, weights=weights)[0])

    def start_room(self, i):
        w = self.world()
        room = w.rooms[i]
        kind = room["kind"]
        if kind == "treasure":
            room["state"] = "cleared"
            w.pois.append({"kind": "altar", "x": room["center"][0], "y": room["center"][1]})
            return
        if kind == "shop":
            room["state"] = "cleared"
            w.pois.append({"kind": "stall", "x": room["center"][0], "y": room["center"][1]})
            return
        room["state"] = "locked"
        w.set_doors(i, True)
        self.spawn_room(i)
        self.shake = max(self.shake, 3)
        self.sound("hurt")

    def clear_room(self, i):
        w = self.world()
        room = w.rooms[i]
        room["state"] = "cleared"
        w.set_doors(i, False)
        self.sparkle(room["center"][0], room["center"][1], GOLD, 20, 60)
        self.sound("win")
        kind = room["kind"]
        self.hazards = [h for h in self.hazards if h["owner"] is not None or h.get("linger")]
        heal = self.mod_count("roomheal")
        if heal:
            self.p["hp"] = min(self.max_hp(), self.p["hp"] + self.max_hp() * 0.15 * heal)
            self.floater(room["center"][0], room["center"][1] - 30, "+{}%".format(15 * heal), GREEN)
        if self.area_kind() == "abyss":
            self.p["gold"] += int(8 * self.run["floor"] * (1 + 0.25 * self.mod_count("gold")))
        if kind in ("miniboss", "boss"):
            cx, cy = room["center"]
            if self.area_kind() == "dungeon":
                area = self.current()
                area["reward"] = True
                area["reward_pos"] = (cx, cy)
                self.notify("Подземелье зачищено! Награда появилась в центре зала.", GOLD)
            elif self.area_kind() == "abyss":
                w.pois.append({"kind": "stairs", "x": cx, "y": cy + 60})
                self.run["shards"] += 3 + self.run["floor"]
                self.open_boon("Награда за этаж", self.relic_offers(3), "free")
        elif self.area_kind() == "abyss" and random.random() < 0.4:
            self.add_drop(room["center"][0], room["center"][1], self.make_item(self.zone_index()))

    def update_rooms(self, dt):
        w = self.world()
        if not w.rooms:
            return
        px, py = self.p["x"], self.p["y"]
        enemies = self.current()["enemies"]
        for i, room in enumerate(w.rooms):
            x, y, rw, rh = room["rect"]
            if room["state"] == "idle" and x + 50 < px < x + rw - 50 and y + 50 < py < y + rh - 50:
                self.start_room(i)
            elif room["state"] == "locked" and not any(e.room == i for e in enemies):
                self.clear_room(i)
        for tr in w.traps:
            if self.trap_phase(tr) == "active" and tr[0] - 10 < px < tr[0] + tr[2] + 10 and tr[1] - 10 < py < tr[1] + tr[3] + 10:
                self.take_damage(10 * ZONES[min(2, self.zone_index())]["scale"] * self.scale_mul, "Шипы", (tr[0] + tr[2] / 2, tr[1] + tr[3] / 2))
        if w.biome_style == "bridge" and any(r["state"] == "locked" for r in w.rooms):
            self.rock_t -= dt
            if self.rock_t <= 0:
                self.rock_t = 1.1
                rx, ry = px + random.uniform(-160, 160), py + random.uniform(-160, 160)
                self.hazards.append({"x": rx, "y": ry, "radius": 58, "line": 0, "width": 0, "dx": 0, "dy": 1, "delay": 0.9, "total": 0.9,
                                     "life": 0.22, "done": False, "damage": 16 * self.scale_mul, "bdmg": 0, "burst": None,
                                     "owner": None, "src": "Камнепад", "linger": 0, "ldmg": 0, "tick": 0, "color": None})

    # ------------------------------------------------------- abyss
    def relic_offers(self, n, price=None):
        mods = self.run_rng.sample(list(MODS), n)
        return [{"mod": m, "price": price} for m in mods]

    def open_boon(self, title, offers, kind):
        self.boon = {"title": title, "offers": offers, "kind": kind}
        self.set_state("boon")

    def pick_boon(self, offer):
        if offer["price"] is not None:
            if self.p["gold"] < offer["price"] or offer.get("sold"):
                return
            self.p["gold"] -= offer["price"]
            offer["sold"] = True
        self.relics[offer["mod"]] = self.relics.get(offer["mod"], 0) + 1
        self.hp_cap()
        self.sound("win")
        self.notify("Реликвия: " + MODS[offer["mod"]][0], PURPLE)
        if self.boon["kind"] == "free":
            self.close_boon()

    def close_boon(self):
        self.boon = None
        self.set_state("play")

    def start_abyss(self, ch):
        if self.session and self.mode == "campaign":
            self.save_game(quiet=True)
        self.mode = "abyss"
        self.relics = {}
        self.heat = set(self.creator.get("heat", ()))
        seed = daily_seed() if self.creator.get("daily") else random.randint(100000, 999999)
        self.run_rng = random.Random(seed)
        self.run = {"floor": 1, "zi": 0, "shards": 0, "ended": False, "seed": seed, "char": ch["name"]}
        self.run_stats = {"kills": 0}
        self.p = self.new_player()
        self.apply_character(ch)
        self.p["potions"] = 0 if "dry" in self.heat else min(8, 3 + self.meta_rank("potion"))
        for _ in range(self.meta_rank("relic")):
            m = self.run_rng.choice(list(MODS))
            self.relics[m] = self.relics.get(m, 0) + 1
        self.areas, self.worlds, self.terrain_cache, self.mini_cache = {}, {}, {}, {}
        self.session = True
        self.build_abyss_floor(1)
        self.reset_runtime()
        self.p["hp"] = self.max_hp()
        self.set_state("play")
        self.banner = {"t": 0.0, "title": "БЕЗДНА", "sub": "Сид {} · накал {}".format(seed, len(self.heat)), "color": PURPLE}

    def build_abyss_floor(self, floor):
        zi = min(2, (floor - 1) // 3)
        self.run["floor"], self.run["zi"] = floor, zi
        self.scale_mul = 1 + 0.18 * (floor - 1)
        n_combat = 3 + min(3, floor // 2)
        kinds = ["combat"] * 2 + ["treasure" if floor % 2 else "shop"] + ["combat"] * (n_combat - 2) + ["boss"]
        seed = self.run_rng.randint(1, 10 ** 6)
        self.terrain_cache.pop("abyss", None)
        self.mini_cache = {}
        w = W.build_rooms("abyss", zi, kinds, seed, "cave", biome=ZONES[zi]["biome"])
        self.worlds["abyss"] = w
        self.areas = {"abyss": {"enemies": [], "drops": [], "reward": False}}
        self.area = self.return_area = "abyss"
        c = w.rooms[0]["center"]
        self.p["x"], self.p["y"] = c[0], c[1]
        self.p["return_x"], self.p["return_y"] = c

    def next_floor(self):
        self.transient_clear()
        self.p["hp"] = min(self.max_hp(), self.p["hp"] + self.max_hp() * 0.3)
        self.build_abyss_floor(self.run["floor"] + 1)
        self.banner = {"t": 0.0, "title": "Этаж {}".format(self.run["floor"]), "sub": ZONES[self.run["zi"]]["name"], "color": PURPLE}
        self.shake = 6

    def end_run(self):
        if self.mode != "abyss" or self.run.get("ended"):
            return
        self.run["ended"] = True
        floor = self.run["floor"]
        base = self.run["shards"] + floor * 3 + self.run_stats["kills"] // 15
        shards = int(base * (1 + HEAT_BONUS * len(self.heat)))
        self.run["shards"] = shards
        self.meta["shards"] += shards
        self.meta["best"] = max(self.meta["best"], floor)
        self.meta["runs"] += 1
        self.meta["history"].append({"char": self.run.get("char", "?"), "floor": floor, "kills": self.run_stats["kills"],
                                     "shards": shards, "heat": len(self.heat), "seed": self.run.get("seed", 0)})
        del self.meta["history"][:-10]
        self.save_profile()

    def on_player_death(self):
        self.arena = None
        if self.mode == "abyss":
            self.end_run()

    def open_settings(self):
        self.back_state = self.state
        self.set_state("settings")

    def open_help(self):
        self.back_state = self.state
        self.set_state("help")

    def resume(self):
        if self.session:
            self.dialog = None
            self.set_state("dead" if self.p["hp"] <= 0 else "play")

    def change_resolution(self, step):
        self.settings["resolution"] = (self.settings["resolution"] + step) % len(RESOLUTIONS)
        if not self.settings["fullscreen"]:
            self.apply_display()
        self.save_settings()

    def opt_float(self, key, step):
        self.settings[key] = round(clamp(self.settings[key] + step, 0, 1), 2)
        self.save_settings()
        self.update_music()
        if key in ("volume", "sfx"):
            self.sound("ui")

    def opt_toggle(self, key):
        self.settings[key] = not self.settings[key]
        art.LOWFX[0] = self.settings["lowfx"]
        self.save_settings()
        self.update_music()

    def opt_cycle(self, key, step, count):
        self.settings[key] = (self.settings[key] + step) % count
        self.save_settings()

    def start_rebind(self, action):
        self.rebinding = action

    def reset_keys(self):
        self.settings["keys"].clear()
        self.settings["keys"].update(DEFAULT_KEYS)
        self.save_settings()
        self.notify("Управление сброшено по умолчанию.")

    def apply_rebind(self, key):
        action = self.rebinding
        self.rebinding = None
        if key == pygame.K_ESCAPE or action is None:
            return
        keys = self.settings["keys"]
        for other, code in keys.items():
            if code == key and other != action:
                keys[other] = keys[action]
                break
        keys[action] = key
        self.save_settings()
        self.notify("{}: {}".format(LABELS[action], key_label(key)))

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        self.apply_display()
        self.save_settings()

    def toggle_music(self):
        self.opt_toggle("music")

    def change_volume(self, step):
        self.opt_float("volume", step)
    def cam_base(self):
        return (clamp(self.p["x"] - VW / 2, 0, WW - VW), clamp(self.p["y"] - VH / 2, 0, WH - VH))

    def aim(self, mouse):
        cx, cy = self.cam_base()
        self.p["face_x"], self.p["face_y"] = direction(mouse[0] + cx - self.p["x"], mouse[1] + cy - self.p["y"])

    def back(self):
        st = self.state
        if self.rebinding:
            self.rebinding = None
        elif st == "play":
            self.set_state("pause")
        elif st in ("pause", "inventory", "stats", "journal", "map", "shop", "smith", "skills", "dialog"):
            self.resume()
        elif st == "boon":
            self.close_boon()
        elif st in ("sanctum", "slots", "records"):
            self.set_state("menu")
        elif st in ("help", "settings", "credits"):
            self.set_state(self.back_state)
        elif st == "menu":
            self.quit()
        elif st == "creator":
            self.set_state("slots" if self.creator.get("mode") == "campaign" else "menu")
        elif st == "cutscene":
            self.finish_cutscene()

    def handle_event(self, event):
        t = event.type
        if t == pygame.QUIT:
            self.quit()
            return
        if t in (pygame.VIDEORESIZE, getattr(pygame, "WINDOWRESIZED", pygame.VIDEORESIZE)):
            self.update_viewport()
            return
        if t == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.focus = False
            if self.state == "play":
                self.set_state("pause")
            self.update_music()
            return
        if t == getattr(pygame, "WINDOWFOCUSGAINED", -1):
            self.focus = True
            return
        if t in (getattr(pygame, "JOYDEVICEADDED", -2), getattr(pygame, "JOYDEVICEREMOVED", -3),
                 getattr(pygame, "JOYBUTTONDOWN", -4), getattr(pygame, "JOYHATMOTION", -5)):
            self.handle_pad(event)
            return
        if t in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            self.pad_active = False
        if t == pygame.MOUSEBUTTONDOWN:
            mouse = self.mouse(event.pos)
            if self.state == "cutscene":
                self.advance_cutscene()
                return
            if self.state != "play" and mouse:
                for rect, action, enabled in reversed(self.buttons[:]):
                    if enabled and rect.collidepoint(mouse):
                        self.sound("ui")
                        action()
                        return
            elif self.state == "play" and mouse and not self.transition:
                self.aim(mouse)
                if event.button == 1:
                    self.attack()
                elif event.button == 3:
                    self.attack(special=True)
        if t == pygame.MOUSEWHEEL and self.state == "inventory":
            pages = max(1, math.ceil(len(self.p["inv"]) / 6))
            self.inv_page = int(clamp(self.inv_page - event.y, 0, pages - 1))
        if t == pygame.MOUSEMOTION and self.state == "play":
            mouse = self.mouse(event.pos)
            if mouse:
                self.aim(mouse)
        if t != pygame.KEYDOWN:
            return
        self.pad_active = False
        key = event.key
        b = self.keys
        if self.rebinding:
            self.apply_rebind(key)
            return
        if key == pygame.K_F12:
            self.running = False
            return
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_F3:
            self.opt_toggle("fps")
            return
        if key == pygame.K_F5 and self.session and self.state in ("play", "pause", "dead"):
            if self.save_game() and self.state == "pause":
                self.resume()
            return
        if key == pygame.K_F9 and self.state not in ("creator", "cutscene", "slots"):
            if self.mode != "abyss":
                self.load_game()
            return
        if key == pygame.K_F10:
            if self.state == "play":
                self.set_state("pause")
            elif self.state == "pause":
                self.resume()
            return
        if key == pygame.K_ESCAPE:
            self.back()
            return
        if self.state == "cutscene":
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.advance_cutscene()
            return
        if self.state == "creator":
            c = self.creator
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.finish_creator()
            elif key in (pygame.K_LEFT, pygame.K_a):
                c["char"] = (c["char"] - 1) % 3
            elif key in (pygame.K_RIGHT, pygame.K_d):
                c["char"] = (c["char"] + 1) % 3
            elif pygame.K_1 <= key <= pygame.K_3:
                c["char"] = key - pygame.K_1
            return
        if self.state == "slots":
            if pygame.K_1 <= key <= pygame.K_3:
                self.choose_slot(key - pygame.K_1 + 1)
            return
        if self.state == "records":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.records_tab = (self.records_tab + (-1 if key == pygame.K_LEFT else 1)) % 4
            return
        if self.state in ("sanctum", "credits"):
            return
        if self.state == "boon":
            offers = self.boon["offers"] if self.boon else []
            if pygame.K_1 <= key < pygame.K_1 + len(offers):
                self.pick_boon(offers[key - pygame.K_1])
            return
        if self.state == "menu":
            rows = self.menu_rows()
            if key == pygame.K_n:
                self.start_new()
            elif key in (pygame.K_UP, pygame.K_w):
                self.menu_move(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_move(1)
            elif pygame.K_1 <= key < pygame.K_1 + len(rows):
                index = key - pygame.K_1
                if rows[index][2]:
                    self.menu_index = index
                    rows[index][1]()
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if rows[self.menu_index][2]:
                    rows[self.menu_index][1]()
            return
        if self.state == "dead":
            if key == b["interact"] or (key == pygame.K_r and self.mode != "abyss"):
                if self.mode != "abyss":
                    self.respawn()
            return
        if self.state == "victory":
            if key == pygame.K_RETURN:
                self.continue_after_win()
            return
        if self.state == "help":
            if key == pygame.K_RETURN:
                self.resume() if self.session else self.set_state("menu")
            return
        if self.state == "dialog":
            buttons = self.dialog["buttons"] if self.dialog else []
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, b["interact"]) and buttons:
                buttons[0][1]()
            elif key == pygame.K_2 and len(buttons) > 1:
                buttons[1][1]()
            return
        if self.state == "pause":
            if key in (pygame.K_RETURN, pygame.K_p):
                self.resume()
            elif key == pygame.K_h:
                self.open_help()
            elif key == pygame.K_q:
                self.quit()
            elif key == pygame.K_m:
                self.to_menu()
            return
        if self.state == "settings":
            if key == pygame.K_TAB:
                self.settings_tab = (self.settings_tab + 1) % 4
            elif key == pygame.K_f:
                self.toggle_fullscreen()
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_volume(-0.1)
            elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.change_volume(0.1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.set_state(self.back_state)
            return
        panels = {b["inventory"]: "inventory", b["stats"]: "stats", b["journal"]: "journal", b["map"]: "map",
                  pygame.K_z: "map", b["skills"]: "skills"}
        if key in panels and self.state in ("play", "inventory", "stats", "journal", "map", "skills"):
            target = panels[key]
            self.set_state("play" if self.state == target else target)
            return
        if self.state == "stats" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.spend_point({pygame.K_1: "str", pygame.K_2: "vit", pygame.K_3: "agi"}[key])
            return
        if self.state != "play" or self.transition:
            return
        if key == b["attack"]:
            if self.p["attack_cd"] <= 0:
                self.autoaim()
            self.attack()
        elif key == b["skill"]:
            if self.p["skill_cd"] <= 0:
                self.autoaim()
            self.attack(special=True)
        elif key == b["pulse"]:
            self.attack(pulse=True)
        elif key == b["potion"]:
            self.potion()
        elif key == b["interact"]:
            self.interact()
        elif key in (b["dash"], pygame.K_RSHIFT):
            self.dash()
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.use_skill(key - pygame.K_1 + 1)
        elif key == pygame.K_F1:
            self.open_help()

    # ---------------------------------------------------------- gamepad
    def init_pads(self):
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                self.connect_pad(i, quiet=True)
        except (pygame.error, AttributeError):
            pass

    def connect_pad(self, index, quiet=False):
        try:
            js = pygame.joystick.Joystick(index)
            try:
                iid = js.get_instance_id()
            except AttributeError:
                iid = index
            self.joys[iid] = js
        except (pygame.error, AttributeError):
            return
        if not quiet:
            self.notify("Геймпад подключён.", GREEN)
            self.hint("gamepad")

    def disconnect_pad(self, iid):
        if self.joys.pop(iid, None) is not None:
            self.notify("Геймпад отключён.", RED)
            if self.state == "play":
                self.set_state("pause")

    def rumble(self, low, high, ms):
        for js in self.joys.values():
            try:
                js.rumble(low, high, ms)
            except (pygame.error, AttributeError, NotImplementedError):
                pass

    def pad_axes(self):
        js = next(iter(self.joys.values()), None)
        if js is None:
            return (0.0, 0.0, 0.0, 0.0, False, False)
        try:
            n = js.get_numaxes()

            def ax(i):
                return js.get_axis(i) if i < n else 0.0
            return (dead(ax(0)), dead(ax(1)), dead(ax(2)), dead(ax(3)), ax(5) > 0.3 if n > 5 else False,
                    ax(4) > 0.3 if n > 4 else False)
        except pygame.error:
            return (0.0, 0.0, 0.0, 0.0, False, False)

    def handle_pad(self, event):
        t = event.type
        if t == getattr(pygame, "JOYDEVICEADDED", -2):
            self.connect_pad(event.device_index)
            return
        if t == getattr(pygame, "JOYDEVICEREMOVED", -3):
            self.disconnect_pad(getattr(event, "instance_id", -1))
            return
        self.pad_active = True
        if t == getattr(pygame, "JOYHATMOTION", -5):
            hx, hy = event.value
            if self.state == "play":
                if not self.transition:
                    idx = {(0, 1): 1, (1, 0): 2, (0, -1): 3, (-1, 0): 4}.get((hx, hy))
                    if idx:
                        self.use_skill(idx)
            elif self.state == "creator" and hx:
                self.creator["char"] = (self.creator["char"] + hx) % 3
            elif hx or hy:
                self.nav_move(hx, -hy)
            return
        act = PAD_BUTTONS.get(event.button)
        if act is None:
            return
        if self.state == "play":
            if self.transition:
                return
            if act == "pause":
                self.set_state("pause")
            elif act == "interact":
                self.interact()
            elif act == "dash":
                self.dash()
            elif act == "attack":
                if self.p["attack_cd"] <= 0:
                    self.autoaim()
                self.attack()
            elif act == "potion":
                self.potion()
            elif act == "pulse":
                self.attack(pulse=True)
            elif act == "skill":
                if self.p["skill_cd"] <= 0:
                    self.autoaim()
                self.attack(special=True)
            elif act == "inventory":
                self.set_state("inventory")
            return
        if self.state == "cutscene":
            if act == "interact":
                self.advance_cutscene()
            elif act in ("dash", "pause"):
                self.finish_cutscene()
            return
        if self.state == "creator":
            if act in ("interact", "pause"):
                self.finish_creator()
            elif act == "dash":
                self.back()
            return
        if act == "interact":
            self.pad_activate()
        elif act == "dash":
            self.back()
        elif act == "pause" and self.state == "pause":
            self.resume()

    def nav_move(self, dx, dy):
        cands = [r for r, _, en in self.buttons if en]
        if not cands:
            return
        if self.focus_pos is None:
            self.focus_pos = cands[0].center
            return
        cur = self.focus_pos
        best, best_score = None, None
        for r in cands:
            vx, vy = r.centerx - cur[0], r.centery - cur[1]
            proj = vx * dx + vy * dy
            if proj <= 1:
                continue
            score = proj + 2.5 * abs(vx * dy - vy * dx)
            if best_score is None or score < best_score:
                best, best_score = r, score
        if best is not None:
            self.focus_pos = best.center
            self.sound("ui")

    def focused_button(self):
        cands = [(r, a) for r, a, en in self.buttons if en]
        if not cands:
            return None
        if self.focus_pos is None:
            self.focus_pos = cands[0][0].center
        fx, fy = self.focus_pos
        for r, a in cands:
            if r.collidepoint((fx, fy)):
                return r, a
        return min(cands, key=lambda c: distance(c[0].centerx, c[0].centery, fx, fy))

    def pad_activate(self):
        found = self.focused_button()
        if found:
            self.sound("ui")
            found[1]()

    # ------------------------------------------------ hints/achievements
    def log(self, message):
        try:
            C.DATA.mkdir(parents=True, exist_ok=True)
            if C.LOG_FILE.exists() and C.LOG_FILE.stat().st_size > 400_000:
                C.LOG_FILE.replace(C.LOG_FILE.with_suffix(".old"))
            with C.LOG_FILE.open("a", encoding="utf8") as f:
                f.write("[{}] v{} {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), VERSION, message))
        except OSError:
            pass

    def hint(self, hid):
        if hid in self.meta["hints"] or self.hint_t > 0:
            return
        self.meta["hints"].append(hid)
        self.profile_dirty = True
        self.hint_text, self.hint_t = HINTS[hid], 7.0

    def unlock(self, aid):
        if aid in self.meta["ach"]:
            return
        self.meta["ach"].append(aid)
        self.profile_dirty = True
        name, desc = ACHIEVEMENTS[aid]
        self.ach_toasts.append([name, desc, 5.0])
        self.sound("rare")

    def check_progress(self):
        """Polls the state for achievements, codex entries and tutorial hints."""
        st = self.meta["stats"]
        p = self.p
        if st["kills"] > 0:
            self.unlock("first_blood")
        for need, aid in ((100, "kills_100"), (1000, "kills_1000")):
            if st["kills"] >= need:
                self.unlock(aid)
        for lv in (5, 10, 15):
            if p["level"] >= lv:
                self.unlock("level_%d" % lv)
        for i in range(3):
            if p["bosses"][i] and self.mode == "campaign":
                self.unlock("boss%d" % i)
        if p["complete"]:
            self.unlock("finale")
        if sum(p["dungeons"]) >= 1:
            self.unlock("dungeon_first")
        if sum(p["dungeons"]) >= 6:
            self.unlock("dungeon_all")
        if any(p["passes"]):
            self.unlock("pass_first")
        done = sum(1 for qid in QUESTS if self.quest_status(qid) == "done")
        if done >= 5:
            self.unlock("quests_5")
        if done >= len(QUESTS):
            self.unlock("quests_all")
        if sum(p["skills"].values()) >= 10:
            self.unlock("skills_10")
        if p["gold"] >= 5000:
            self.unlock("rich")
        if st["deaths"] > 0:
            self.unlock("died")
        if st["weak_hits"] >= 50:
            self.unlock("weakness")
        if st.get("elites", 0) > 0:
            self.unlock("elite")
        codex = self.meta["codex"]
        items = list(p["equip"].values()) + list(p["inv"])
        for it in items:
            if it and it.unique:
                self.unlock("unique")
                if it.name not in codex["uniques"]:
                    codex["uniques"].append(it.name)
                    self.profile_dirty = True
            if it and it.plus >= 5:
                self.unlock("smith_max")
            for m in (it.mods if it else []):
                if m not in codex["mods"]:
                    codex["mods"].append(m)
                    self.profile_dirty = True
        for m in self.relics:
            if m not in codex["mods"]:
                codex["mods"].append(m)
                self.profile_dirty = True
        for e in self.current()["enemies"]:
            if distance(e.x, e.y, p["x"], p["y"]) < 520:
                key = "bosses" if e.kind in ("boss", "finalboss", "miniboss") else "enemies"
                tag = e.kind if key == "enemies" else self.enemy_name(e)
                if tag not in codex[key]:
                    codex[key].append(tag)
                    self.profile_dirty = True
        if all(k in codex["enemies"] for k in ENEMY_ORDER):
            self.unlock("codex_enemies")
        if self.mode == "abyss":
            for need in (5, 10, 15):
                if self.run["floor"] >= need:
                    self.unlock("abyss_%d" % need)
            if self.run["floor"] >= 5 and len(self.heat) >= 3:
                self.unlock("heat")
            if sum(self.relics.values()) >= 10:
                self.unlock("relics_10")
            if sum(self.relics.values()) >= 2:
                self.hint("relic")
        # tutorial hints
        near = [e for e in self.current()["enemies"] if distance(e.x, e.y, p["x"], p["y"]) < 360 and (e.awake or e.kind not in ("boss", "finalboss", "miniboss"))]
        if near:
            self.hint("attack")
        if any(h["delay"] > 0 and h["damage"] > 0 and distance(h["x"], h["y"], p["x"], p["y"]) < 420 for h in self.hazards):
            self.hint("telegraph")
        if any(d.get("age", 9) > 1 and distance(d["x"], d["y"], p["x"], p["y"]) < 160 for d in self.current()["drops"]):
            self.hint("loot")
        if p["hp"] < self.max_hp() * 0.5 and p["potions"] > 0:
            self.hint("potion")
        if p["level"] >= 2 and (p["sp"] or p["points"]):
            self.hint("levelup")
        if p["level"] >= 3:
            self.hint("weakness")
        poi = self.nearest_interaction()
        if poi and poi[1] == "poi" and poi[2]["kind"] == "npc" and self.npc_marker(poi[2]["npc"]) == "!":
            self.hint("quest")

    # ----------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        self.toast_time = max(0, self.toast_time - dt)
        self.fps_smooth += (1 / max(dt, 0.001) - self.fps_smooth) * 0.05
        self.nav_cd = max(0.0, self.nav_cd - dt)
        self.hint_t = max(0.0, self.hint_t - dt)
        for a in list(self.ach_toasts):
            a[2] -= dt
            if a[2] <= 0:
                self.ach_toasts.remove(a)
        if self.joys and self.state not in ("play", "cutscene", "creator") and self.nav_cd <= 0:
            mx, my, _, _, _, _ = self.pad_axes()
            if abs(mx) > 0.6 or abs(my) > 0.6:
                self.pad_active = True
                self.nav_cd = 0.22
                self.nav_move(1 if mx > 0.6 else -1 if mx < -0.6 else 0, 1 if my > 0.6 else -1 if my < -0.6 else 0)
        if self.state == "cutscene" and self.cut:
            self.cut["t"] += dt
            return
        if self.state == "dialog" and self.dialog:
            self.dialog["t"] += dt
        if not self.session:
            return
        shake_on = self.settings["shake"]
        self.shake = max(0, self.shake - 28 * dt)
        self.flash = max(0, self.flash - 2.2 * dt)
        self.hurt_t = max(0, self.hurt_t - dt)
        if self.levelfx:
            self.levelfx["t"] += dt
            if self.levelfx["t"] > 2.4:
                self.levelfx = None
        if self.banner:
            self.banner["t"] += dt
            if self.banner["t"] > 3.2:
                self.banner = None
        for r in list(self.ripples):
            r[1] -= dt * 2
            if r[1] <= 0:
                self.ripples.remove(r)
        for f in list(self.fx):
            f[4] -= dt
            if f[4] <= 0:
                self.fx.remove(f)
        if self.last_hit:
            self.last_hit["t"] -= dt
        if self.transition:
            tr = self.transition
            tr["t"] += dt
            if tr["t"] >= tr["dur"] / 2 and not tr["fired"]:
                tr["fired"] = True
                tr["cb"]()
            if tr["t"] >= tr["dur"]:
                self.transition = None
            if not tr["fired"]:
                return
        if self.state != "play":
            if self.pending_save:
                self.pending_save = False
                self.save_game(quiet=True)
            return
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        if self.slowmo > 0:
            self.slowmo -= dt
            dt *= 0.4
        p = self.p
        self.play_accum += dt
        if self.play_accum >= 1:
            whole = int(self.play_accum)
            self.play_accum -= whole
            p["playtime"] += whole
            self.meta["stats"]["playtime"] += whole
        self.check_t -= dt
        if self.check_t <= 0:
            self.check_t = 1.0
            self.check_progress()
        for key in ("attack_cd", "skill_cd", "pulse_cd", "dash_cd", "invuln", "dash"):
            p[key] = max(0, p[key] - dt)
        self.swing = max(0.0, self.swing - dt)
        self.lunge = max(0.0, self.lunge - dt)
        self.update_skills(dt)
        regen = 0.7 * self.rank("regen") + 0.8 * self.mod_count("regen")
        if regen and p["hp"] < self.max_hp():
            p["hp"] = min(self.max_hp(), p["hp"] + regen * dt)
        keys = pygame.key.get_pressed()
        b = self.keys
        dx = int(keys[b["right"]] or keys[pygame.K_RIGHT]) - int(keys[b["left"]] or keys[pygame.K_LEFT])
        dy = int(keys[b["down"]] or keys[pygame.K_DOWN]) - int(keys[b["up"]] or keys[pygame.K_UP])
        mx, my, rx, ry, rt, lt = self.pad_axes()
        if mx or my:
            dx, dy = mx, my
            self.pad_active = True
        self.moving = bool(dx or dy)
        if dx or dy:
            dx, dy = direction(dx, dy)
            p["face_x"], p["face_y"] = dx, dy
        if rx or ry:
            p["face_x"], p["face_y"] = direction(rx, ry)
        if p["dash"] > 0:
            dx, dy = p["face_x"], p["face_y"]
            speed = 650
            self.ghost_timer -= dt
            if self.ghost_timer <= 0:
                self.ghost_timer = 0.03
                fx, fy = p["face_x"], p["face_y"]
                base = "hero_side" if abs(fx) > abs(fy) else ("hero_up" if fy < 0 else "hero_down")
                self.ghosts.append([p["x"], p["y"], self.hero_sprite_name(base), 48, base == "hero_side" and fx < 0, 0.2])
            self.burst(p["x"], p["y"] + 12, (190, 180, 150), 1)
        else:
            speed = self.move_speed()
            if self.moving:
                self.step_timer -= dt
                if self.step_timer <= 0:
                    self.step_timer = 0.17
                    self.particles.append([p["x"] + random.uniform(-6, 6), p["y"] + 15, random.uniform(-10, 10), -12, 0.3, (140, 130, 110)])
        p["x"], p["y"] = self.move(p["x"], p["y"], dx * speed * dt, dy * speed * dt, 14)
        for g in list(self.ghosts):
            g[5] -= dt
            if g[5] <= 0:
                self.ghosts.remove(g)
        if keys[b["attack"]] or rt:
            if p["attack_cd"] <= 0 and not (rx or ry):
                self.autoaim()
            self.attack()
        elif lt:
            if p["skill_cd"] <= 0 and not (rx or ry):
                self.autoaim()
            self.attack(special=True)
        elif pygame.mouse.get_pressed()[0] and self.mouse():
            self.aim(self.mouse())
            self.attack()

        enemies = self.current()["enemies"]
        for e in list(enemies):
            if self.state != "play":
                break
            if e in enemies:
                self.update_enemy(e, dt)
        if self.state == "play":
            self.update_hazards(dt)
            self.update_bullets(dt)
            self.update_projectiles(dt)
        if self.state == "play":
            self.update_rooms(dt)
            self.update_pickups(dt)
            if self.surface():
                self.update_arena(dt)
                regular = sum(e.kind not in ("boss", "finalboss") for e in enemies)
                if random.random() < dt / 3 and regular < ZONE_ENEMY_CAP:
                    self.spawn_regular()
        if self.settings["lowfx"]:
            del self.particles[:max(0, len(self.particles) - 120)]
        else:
            del self.particles[:max(0, len(self.particles) - 400)]
        for part in list(self.particles):
            part[4] -= dt
            part[0] += part[2] * dt
            part[1] += part[3] * dt
            if part[4] <= 0:
                self.particles.remove(part)
        for f in list(self.floaters):
            f[1] -= 28 * dt
            f[4] -= dt
            if f[4] <= 0:
                self.floaters.remove(f)
        for s in list(self.slashes):
            s[4] -= dt
            if s[4] <= 0:
                self.slashes.remove(s)
        for d in list(self.deaths):
            d[4] += dt
            if d[4] > 0.5:
                self.deaths.remove(d)
        for drop in self.current()["drops"]:
            drop["age"] = drop.get("age", 9.0) + dt
        self.autosave_time += dt
        if self.pending_save or self.autosave_time >= 60:
            if not self.pending_save and self.in_combat():
                self.autosave_time = 50
            else:
                self.pending_save = False
                self.autosave_time = 0
                self.save_game(quiet=True)
                if self.profile_dirty:
                    self.profile_dirty = False
                    self.save_profile()

    def update_pickups(self, dt):
        if not self.mod_count("magnet"):
            return
        for drop in list(self.current()["drops"]):
            if drop.get("age", 9) > 1 and distance(drop["x"], drop["y"], self.p["x"], self.p["y"]) < 90:
                if self.add_item(drop["item"]):
                    self.current()["drops"].remove(drop)

    def main_loop(self):
        self.update_music()
        self.draw()
        crashes = []
        while self.running:
            dt = min(self.clock.tick(60 if not self.settings["lowfx"] else 45) / 1000, 0.04)
            try:
                for event in pygame.event.get():
                    self.handle_event(event)
                    if not self.running:
                        break
                if not self.running:
                    break
                self.update(dt)
                self.update_music()
                self.draw()
            except Exception:  # noqa: BLE001 - the game must never die without a log entry
                self.log("Исключение в игровом цикле:\n" + traceback.format_exc())
                crashes = [t for t in crashes if self.time - t < 3] + [self.time]
                self.notify("Произошла ошибка. Подробности записаны в game.log", RED)
                if len(crashes) >= 4:
                    if self.session and self.mode == "campaign":
                        try:
                            self.save_game(quiet=True)
                        except Exception:  # noqa: BLE001
                            pass
                    break
                self.transition = None
                if self.state not in ("menu", "play"):
                    self.set_state("play" if self.session else "menu")
        if self.profile_dirty:
            self.save_profile()
        pygame.quit()



def ASSETS_PATH():
    return C.ASSETS


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--version" in argv:
        # Windows consoles may default to cp1252/cp1251 and fail on Cyrillic.
        # Prefer UTF-8 for this short CLI response, falling back to replacement
        # characters if the output stream cannot be reconfigured.
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
        print("Тропы Эльдории v{}".format(VERSION))
        return 0
    if "--reset-settings" in argv:
        try:
            C.SETTINGS_FILE.unlink()
        except OSError:
            pass
    game = None
    try:
        game = Game()
        if "--windowed" in argv:
            game.settings["fullscreen"] = False
            game.apply_display()
        game.main_loop()
        return 0
    except Exception:  # noqa: BLE001
        text = traceback.format_exc()
        try:
            C.DATA.mkdir(parents=True, exist_ok=True)
            with C.LOG_FILE.open("a", encoding="utf8") as f:
                f.write("[fatal] v{}\n{}\n".format(VERSION, text))
        except OSError:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Игра неожиданно завершилась.\nПодробности: " + str(C.LOG_FILE), "Тропы Эльдории", 0x10)
        except Exception:  # noqa: BLE001
            print(text, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
