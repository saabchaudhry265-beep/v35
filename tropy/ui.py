"""HUD, menus, character creator, cutscenes and dialogs (mixin for Game)."""
import math
import random

import pygame

from .common import *
from .content import *
from . import art
from . import common as C
from . import world as W
from .meta import HEAT, HEAT_BONUS


class UIMixin:
    # ---------------------------------------------------------- helpers
    def text(self, text, x, y, color=TEXT, size=17, center=False):
        image = self.fonts[size].render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.midtop = (int(x), int(y))
        else:
            rect.topleft = (int(x), int(y))
        self.canvas.blit(image, rect)
        return rect.height

    def wrap(self, text, x, y, width, color=TEXT, size=17):
        words = str(text).split()
        line = ""
        for word in words:
            attempt = (line + " " + word).strip()
            if self.fonts[size].size(attempt)[0] > width and line:
                self.text(line, x, y, color, size)
                y += self.fonts[size].get_linesize() + 3
                line = word
            else:
                line = attempt
        if line:
            self.text(line, x, y, color, size)
            y += self.fonts[size].get_linesize() + 3
        return y

    def button(self, label, rect, action, enabled=True, color=None, selected=False):
        rect = pygame.Rect(rect)
        mouse = self.mouse()
        hover = enabled and mouse is not None and rect.collidepoint(mouse)
        bg = (58, 81, 112) if hover else (39, 53, 74)
        if not enabled:
            bg = (31, 38, 50)
        pygame.draw.rect(self.canvas, bg, rect, border_radius=7)
        pygame.draw.rect(self.canvas, (88, 112, 147) if enabled else (48, 58, 75), rect, 1, border_radius=7)
        if selected:
            pygame.draw.rect(self.canvas, GOLD, rect, 2, border_radius=7)
        self.text(label, rect.centerx, rect.y + (rect.h - 21) // 2,
                  (color or TEXT) if enabled else (105, 117, 136), 17, center=True)
        self.buttons.append((rect, action, enabled))

    def card(self, rect, action, enabled=True):
        """Invisible clickable area."""
        self.buttons.append((pygame.Rect(rect), action, enabled))

    def overlay(self, title):
        shade = pygame.Surface((VW, VH), pygame.SRCALPHA)
        shade.fill((4, 8, 15, 205))
        self.canvas.blit(shade, (0, 0))
        pygame.draw.rect(self.canvas, PANEL, (55, 45, 890, 610), border_radius=16)
        pygame.draw.rect(self.canvas, (83, 110, 145), (55, 45, 890, 610), 2, border_radius=16)
        self.text(title, 85, 66, GOLD, 32)

    def close_button(self):
        self.button("Назад · ESC", (770, 600, 145, 36), self.resume)

    def item_summary(self, item):
        parts = []
        if item.power:
            parts.append("урон +{}".format(item.power))
        if item.armor:
            parts.append("защита +{}".format(item.armor))
        if item.crit:
            parts.append("крит +{}%".format(item.crit))
        if item.hp:
            parts.append("HP +{}".format(item.hp))
        return " · ".join(parts)

    def weakness_text(self, e):
        if e.kind == "finalboss":
            table = BOSSES[3]["res"]
        elif e.kind == "boss":
            table = BOSSES[e.zone]["res"]
        else:
            table = ENEMIES[e.kind]["res"]
        return self.res_text(table)

    def res_text(self, table):
        best = max(table, key=table.get)
        worst = min(table, key=table.get)
        parts = []
        if table[best] >= 1.2:
            parts.append(("Слабость: " + DTYPE_NAMES[best], (255, 170, 70)))
        if table[worst] <= 0.75:
            parts.append(("Устойчив: " + DTYPE_NAMES[worst], MUTED))
        return parts

    def target_enemy(self):
        best, best_d = None, 330
        for e in self.current()["enemies"]:
            if e.kind in ("boss", "finalboss") or (e.kind == "miniboss" and not e.awake):
                continue
            d = distance(self.p["x"], self.p["y"], e.x, e.y)
            if d < best_d:
                best, best_d = e, d
        return best

    def area_title(self):
        kind = self.area_kind()
        if kind == "zone":
            return ZONES[self.zone_index()]["name"]
        if kind == "dungeon":
            return "Подземелье: " + DUNGEONS[self.area]["name"]
        if kind == "pass":
            return PASSES[int(self.area[-1])]["name"]
        if kind == "abyss":
            return "Бездна · этаж {}".format(self.run["floor"])
        return "Сердце Пустоты"

    def draw_hud(self):
        self.draw_low_hp()
        pygame.draw.rect(self.canvas, BG, (12, 12, 310, 118), border_radius=9)
        self.text(self.area_title()[:34], 24, 18, GREEN, 17)
        self.text("{} · Ур. {}  Золото: {}  Зелья: {}".format(self.p["name"][:12], self.p["level"], self.p["gold"], self.p["potions"]), 24, 44, TEXT, 14)
        pygame.draw.rect(self.canvas, (73, 39, 49), (24, 70, 280, 13), border_radius=4)
        pygame.draw.rect(self.canvas, (217, 78, 100), (24, 70, int(max(0, 280 * self.p["hp"] / self.max_hp())), 13), border_radius=4)
        if self.shield > 0:
            pygame.draw.rect(self.canvas, BLUE, (24, 70, int(min(280, self.shield * 280 / self.max_hp())), 4), border_radius=2)
        self.text("{}/{} HP".format(int(self.p["hp"]), self.max_hp()), 164, 67, TEXT, 14, True)
        pygame.draw.rect(self.canvas, (54, 52, 43), (24, 95, 280, 6))
        pygame.draw.rect(self.canvas, GOLD, (24, 95, int(280 * self.p["xp"] / self.p["xpnext"]), 6))
        extra = ""
        if self.p["sp"] > 0 and int(self.time * 2) % 2:
            extra = "   K: навыки +" + str(self.p["sp"])
        elif self.p["points"] > 0:
            extra = "   C: очки +" + str(self.p["points"])
        self.text("Опыт {}/{}{}".format(self.p["xp"], self.p["xpnext"], extra), 24, 105, MUTED, 14)
        self.minimap((820, 12, 168, 115))
        self.text("M — карта", 904, 131, MUTED, 14, True)
        if self.mode == "abyss":
            self.draw_relic_list()
        else:
            self.draw_quest_tracker()

        bosses = [e for e in self.current()["enemies"] if e.kind in ("boss", "finalboss", "miniboss") and e.awake]
        target = bosses[0] if bosses else self.target_enemy()
        if target:
            big = target.kind in ("boss", "finalboss", "miniboss")
            nm = self.enemy_name(target)
            self.text(nm + (" · форма II" if big and target.phase == 2 else ""), 560, 15, GOLD, 17, True)
            w = 390 if big else 260
            x = 560 - w // 2
            pygame.draw.rect(self.canvas, (69, 35, 48), (x, 42, w, 14 if big else 10), border_radius=5)
            pygame.draw.rect(self.canvas, RED, (x, 42, int(w * max(0, target.hp) / target.maxhp), 14 if big else 10), border_radius=5)
            parts = self.weakness_text(target)
            if big and target.pat:
                parts = [("Атака: " + PATTERN_NAMES[target.pat], (255, 120, 120))] + parts
            cx = 560 - sum(self.fonts[14].size(p[0])[0] + 14 for p in parts) // 2
            for label, col in parts:
                self.text(label, cx, 60 if big else 56, col, 14)
                cx += self.fonts[14].size(label)[0] + 14
        elif self.surface() and not self.arena:
            zi = self.zone_index()
            need = max(0, ARENA_KILLS - self.p["zonekills"][zi])
            status = "Хранитель повержен" if self.p["bosses"][zi] else ("Арена открыта — иди к хранителю" if not need else "До арены хранителя: {} побед".format(need))
            self.text(status, 560, 20, GOLD, 17, True)
        self.draw_hit_source()

        pygame.draw.rect(self.canvas, BG, (12, 632, 976, 58), border_radius=9)
        skills = [("SPACE / ЛКМ", WEAPONS[self.weapon()], self.p["attack_cd"]), ("R / ПКМ", "Навык", self.p["skill_cd"]),
                  ("Q", "Импульс", self.p["pulse_cd"]), ("SHIFT", "Рывок", self.p["dash_cd"])]
        for i, (key, label, cd) in enumerate(skills):
            x = 26 + i * 118
            self.text(key, x, 639, GOLD if cd <= 0 else MUTED, 14)
            self.text(label if cd <= 0 else "{:.1f} сек.".format(cd), x, 659, TEXT, 14)
        for key, sid in sorted((s["key"], sid) for sid, s in SKILLS.items() if "key" in s):
            x = 500 + (key - 1) * 66
            learned = self.rank(sid) > 0
            cd = self.skill_cd[sid]
            pygame.draw.rect(self.canvas, (36, 48, 66) if learned else (26, 32, 44), (x, 638, 58, 46), border_radius=6)
            if cd > 0 and learned:
                pygame.draw.rect(self.canvas, (60, 40, 40), (x, 638, 58, int(46 * min(1, cd / (SKILLS[sid]["cd"] * self.cdr()))), 46), border_radius=6)
            col = GOLD if learned and cd <= 0 else MUTED
            self.text(str(key), x + 6, 640, col, 14)
            self.text(SKILLS[sid]["name"].split(" [")[0][:7] if learned else "—", x + 6, 662, TEXT if learned else MUTED, 14)
        self.text("H: лечение  E: действие", 770, 640, GREEN, 14)
        self.text("I K C J ESC", 770, 663, MUTED, 14)
        near = self.nearest_interaction()
        if near and self.state == "play":
            self.text("E — " + self.interaction_label(near), 500, 588, GOLD, 17, True)

    def draw_hit_source(self):
        h = self.last_hit
        if not h or h["t"] <= 0:
            return
        a = clamp(h["t"] / 1.0, 0, 1)
        self.text("Вас ранит: " + h["src"], 500, 90, rgb(RED, 0.5 + 0.5 * a), 17, True)
        if h["pos"]:
            cx, cy = self.cam_base()
            hx, hy = self.p["x"] - cx, self.p["y"] - cy
            dx, dy = direction(h["pos"][0] - self.p["x"], h["pos"][1] - self.p["y"])
            tip = (hx + dx * 70, hy + dy * 70)
            left = (hx + dx * 48 - dy * 9, hy + dy * 48 + dx * 9)
            right = (hx + dx * 48 + dy * 9, hy + dy * 48 - dx * 9)
            pygame.draw.polygon(self.canvas, rgb(RED, 0.5 + 0.5 * a), [tip, left, right])

    def draw_relic_list(self):
        y = 150
        self.text("Реликвии", 988 - self.fonts[14].size("Реликвии")[0], y, GOLD, 14)
        y += 18
        for mod, n in sorted(self.relics.items(), key=lambda kv: -kv[1])[:8]:
            label = "{}{}".format(MODS[mod][0], " ×" + str(n) if n > 1 else "")
            self.text(label, 988 - self.fonts[14].size(label)[0], y, TEXT, 14)
            y += 17

    def interaction_label(self, near):
        obj = near[2]
        if near[1] == "drop":
            return obj["item"].title
        kind = obj["kind"]
        if kind == "npc":
            return ("Торговать: " if obj["npc"] == "merchant" else "Кузница: " if obj["npc"] == "smith" else "Поговорить: ") + NPCS[obj["npc"]]["name"]
        if kind == "entrance":
            return "Войти: " + DUNGEONS[obj["dg"]]["name"]
        return {"camp": "Отдохнуть у костра и сохранить", "chest": "Открыть сундук", "dchest": "Открыть сундук",
                "exit": "Покинуть локацию", "exit_back": "Вернуться назад", "exit_fwd": "Идти дальше", "portal": "Войти в портал",
                "gate_next": "Отправиться вперёд", "gate_back": "Вернуться назад", "reward": "Забрать награду",
                "altar": "Выбрать реликвию", "stall": "Торговать реликвиями", "stairs": "Спуститься на следующий этаж"}[kind]

    def draw_quest_tracker(self):
        y = 150
        shown = 0
        for qid, q in QUESTS.items():
            st = self.quest_status(qid)
            if st in ("active", "ready") and shown < 3:
                have, need = self.quest_progress(qid)
                col = GREEN if st == "ready" else TEXT
                self.text(q["title"][:22], 988 - self.fonts[14].size(q["title"][:22])[0], y, col, 14)
                prog = "сдать задание" if st == "ready" else "{}/{}".format(have, need)
                self.text(prog, 988 - self.fonts[14].size(prog)[0], y + 16, MUTED, 14)
                y += 38
                shown += 1

    def draw_low_hp(self):
        ratio = self.p["hp"] / max(1, self.max_hp())
        if not 0 < ratio < 0.3:
            return
        if self.vignette is None:
            self.vignette = pygame.Surface((VW, VH), pygame.SRCALPHA)
            for i in range(24):
                a = int(150 * (1 - i / 24) ** 2)
                pygame.draw.rect(self.vignette, (255, 40, 50, a), (i * 3, i * 3, VW - 6 * i, VH - 6 * i), 3)
        pulse = (0.55 + 0.45 * math.sin(self.time * 7)) if self.settings["flash"] else 0.7
        self.vignette.set_alpha(int(255 * pulse * (1.0 if ratio < 0.15 else 0.7)))
        self.canvas.blit(self.vignette, (0, 0))

    def draw_banners(self):
        if self.banner:
            b = self.banner
            t = b["t"]
            k = min(1, t / 0.5) * min(1, (3.2 - t) / 0.5)
            bar = int(70 * k)
            pygame.draw.rect(self.canvas, (0, 0, 0), (0, 0, VW, bar))
            pygame.draw.rect(self.canvas, (0, 0, 0), (0, VH - bar, VW, bar))
            if k > 0.3:
                art.draw_glow(self.canvas, VW / 2, VH / 2 - 40, 260, b["color"], 0.35 * k)
                self.text(b["title"], VW / 2, VH / 2 - 70, b["color"], 32, True)
                self.text(b["sub"], VW / 2, VH / 2 - 24, TEXT, 21, True)
        if self.levelfx and self.levelfx["t"] < 2.0:
            k = self.levelfx["t"]
            a = clamp(1 - abs(k - 0.6) / 1.4, 0, 1)
            art.draw_glow(self.canvas, VW / 2, 150, 200, GOLD, 0.5 * a)
            self.text("УРОВЕНЬ {}".format(self.levelfx["level"]), VW / 2, 120 - int(10 * (1 - a)), GOLD, 32, True)
            self.text("+3 очка героя · +1 очко навыков", VW / 2, 160, TEXT, 17, True)
        if self.flash > 0:
            fl = pygame.Surface((VW, VH), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(255 * clamp(self.flash, 0, 1) * (0.7 if self.settings["flash"] else 0.15))))
            self.canvas.blit(fl, (0, 0))
        if self.transition:
            tr = self.transition
            k = tr["t"] / tr["dur"]
            a = 1 - abs(k * 2 - 1)
            sh = pygame.Surface((VW, VH), pygame.SRCALPHA)
            sh.fill((14, 8, 30, int(255 * clamp(a * 1.4, 0, 1))))
            self.canvas.blit(sh, (0, 0))
            for i in range(5):
                rr = int((1 - abs(k * 2 - 1)) * (120 + i * 90))
                if rr > 4:
                    pygame.draw.circle(self.canvas, rgb(PURPLE, 0.4 + 0.12 * i), (VW // 2, VH // 2), rr, 3)

    # --------------------------------------------------------- inventory
    def draw_inventory(self):
        self.overlay("Снаряжение и сумка")
        self.text("Золото: {}   Сумка: {}/60".format(self.p["gold"], len(self.p["inv"])), 85, 112, MUTED)
        x = 85
        for slot, label in SLOTS.items():
            item = self.p["equip"][slot]
            pygame.draw.rect(self.canvas, (32, 44, 62), (x, 148, 266, 90), border_radius=8)
            self.text(label, x + 10, 152, GOLD, 14)
            if item:
                art.draw_item_frame(self.canvas, (x + 8, 170, 60, 60), item, self.time)
                self.wrap(item.title, x + 76, 166, 184, item.color, 14)
                self.text(self.item_summary(item), x + 76, 195, MUTED, 14)
                if item.mods:
                    self.text("✦ " + ", ".join(MODS[m][0] for m in item.mods), x + 76, 214, PURPLE, 14)
            else:
                self.text("Не экипировано", x + 76, 190, MUTED, 14)
            x += 280
        pages = max(1, math.ceil(len(self.p["inv"]) / 6))
        self.inv_page = int(clamp(self.inv_page, 0, pages - 1))
        for row in range(6):
            index = self.inv_page * 6 + row
            if index >= len(self.p["inv"]):
                break
            item = self.p["inv"][index]
            y = 252 + row * 53
            pygame.draw.rect(self.canvas, (31, 42, 59), (85, y, 830, 48), border_radius=5)
            art.draw_item_frame(self.canvas, (89, y + 2, 44, 44), item, self.time)
            label = ("★ " if item.unique else "") + item.title
            if item.slot == "weapon":
                label += " · " + WEAPONS[item.weapon] + " (" + DTYPE_NAMES[DTYPES[item.weapon]] + ")"
            self.text(label, 144, y + 3, item.color, 14)
            mods = "  ✦ " + ", ".join(MODS[m][0] for m in item.mods) if item.mods else ""
            self.text(self.item_summary(item) + mods, 144, y + 25, MUTED, 14)
            cur = self.p["equip"][item.slot]
            cx = 570
            for key, name in (("power", "урон"), ("armor", "защ."), ("crit", "крит"), ("hp", "HP")):
                diff = getattr(item, key) - (getattr(cur, key) if cur else 0)
                if diff:
                    self.text("{} {:+d}".format(name, diff), cx, y + 3, GREEN if diff > 0 else RED, 14)
                    cx += 12 + 8 * (len(name) + 3)
            self.button("Надеть", (656, y + 7, 110, 34), lambda i=index: self.equip(i))
            selling = self.near_camp()
            action = "Продать {}".format(item.price) if selling else "Выбросить"
            if self.discard_index == index:
                action = "Точно?"
            self.button(action, (777, y + 7, 127, 34), lambda i=index: self.discard(i))
        self.button("←", (85, 600, 45, 36), lambda: self.change_inv_page(-1), self.inv_page > 0)
        self.text("{}/{}".format(self.inv_page + 1, pages), 160, 607, MUTED, 17, True)
        self.button("→", (190, 600, 45, 36), lambda: self.change_inv_page(1), self.inv_page < pages - 1)
        self.text("В лагере предметы можно продавать.", 270, 608, MUTED, 14)
        self.close_button()

    def draw_stats(self):
        self.overlay("Герой · " + self.p["name"])
        self.text("Уровень {}   Очков героя: {}   Очков навыков: {}".format(self.p["level"], self.p["points"], self.p["sp"]), 90, 120, TEXT, 21)
        rows = [("str", "Сила", "Повышает урон всех видов оружия."),
                ("vit", "Живучесть", "Каждое очко даёт 8 максимального здоровья."),
                ("agi", "Ловкость", "Повышает шанс критического удара и скорость.")]
        for i, (key, name, desc) in enumerate(rows):
            y = 180 + i * 95
            self.text("{}: {}".format(name, self.p[key]), 100, y, GOLD, 21)
            self.text(desc, 100, y + 36, MUTED, 17)
            self.button("+", (800, y, 70, 45), lambda k=key: self.spend_point(k), self.p["points"] > 0)
        self.text("Урон: {}   Защита: {}   Крит: {}%   HP: {}".format(int(self.damage()), self.defense(), int(self.crit()), self.max_hp()), 100, 480, GREEN, 17)
        self.text("Защита снижает входящий урон на {}%. Критический удар наносит 180% урона.".format(round(100 - 2500 / (25 + self.defense()))), 100, 512, MUTED, 14)
        self.text("Оружие: {} — {} урон. Слабости врагов смотри над полосой здоровья.".format(WEAPONS[self.weapon()], DTYPE_NAMES[DTYPES[self.weapon()]]), 100, 540, MUTED, 14)
        self.button("Навыки · K", (560, 600, 190, 36), lambda: self.set_state("skills"))
        self.close_button()

    def draw_skills(self):
        self.overlay("Навыки")
        self.text("Очков навыков: {}".format(self.p["sp"]), 560, 76, GOLD if self.p["sp"] else MUTED, 21)
        for b, bname in enumerate(BRANCHES):
            x0 = 65 + b * 297
            self.text(bname, x0 + 142, 118, GOLD, 21, True)
            for sid, s in SKILLS.items():
                if s["branch"] != b:
                    continue
                y = 148 + s["row"] * 88
                rank = self.rank(sid)
                req_ok = self.req_ok(sid)
                buyable = self.can_buy(sid)
                rect = pygame.Rect(x0, y, 285, 80)
                mouse = self.mouse()
                hover = mouse is not None and rect.collidepoint(mouse)
                bg = (46, 62, 86) if hover and buyable else (33, 45, 63) if req_ok else (26, 32, 44)
                pygame.draw.rect(self.canvas, bg, rect, border_radius=8)
                border = GOLD if rank >= s["max"] else (120, 200, 150) if buyable else (70, 90, 118)
                pygame.draw.rect(self.canvas, border, rect, 2, border_radius=8)
                active = "key" in s
                self.text(s["name"], x0 + 10, y + 6, TEXT if req_ok else MUTED, 17)
                for k in range(s["max"]):
                    c = GOLD if k < rank else (60, 70, 90)
                    pygame.draw.circle(self.canvas, c, (x0 + 268 - k * 16, y + 16), 6, 0 if k < rank else 1)
                self.wrap(s["desc"], x0 + 10, y + 30, 268, MUTED if req_ok else (100, 110, 130), 14)
                if not req_ok:
                    rn = SKILLS[s["req"][0]]["name"].split(" [")[0]
                    self.text("Нужно: {} ({})".format(rn, s["req"][1]), x0 + 10, y + 61, (150, 100, 100), 14)
                elif rank < s["max"]:
                    self.text("Цена: {}".format(s.get("cost", 1)), x0 + 200, y + 61, GREEN if buyable else MUTED, 14)
                self.card(rect, lambda i=sid: self.buy_skill(i), buyable)
        self.button("Сбросить навыки (у костра)", (65, 600, 300, 36), self.respec, bool(self.p["skills"]) and (self.near_camp() or self.mode == "abyss"))
        self.close_button()

    # ----------------------------------------------------------- journal
    def main_goal(self):
        if self.p["complete"]:
            return "Эльдория спасена! Исследуй оставшиеся сундуки, подземелья и задания."
        unfinished = next((i for i, done in enumerate(self.p["bosses"]) if not done), None)
        if unfinished is None:
            return "Все печати разрушены. Найди портал на севере Пепельных пустошей."
        z = ZONES[unfinished]
        if self.p["level"] < z["level"] and unfinished > 0:
            return "Достигни уровня {} и пройди в {} через врата.".format(z["level"], z["name"])
        if self.p["zonekills"][unfinished] < ARENA_KILLS:
            return "Победи {} врагов региона «{}»: печать арены хранителя ослабнет.".format(ARENA_KILLS, z["name"])
        return "Хранитель «{}» ждёт на арене. Войди в круг рун.".format(z["boss"])

    def draw_journal(self):
        self.overlay("Журнал")
        for i, label in enumerate(("Задания", "Бестиарий")):
            self.button(label, (480 + i * 150, 62, 140, 34), lambda k=i: setattr(self, "journal_tab", k), True, GOLD if self.journal_tab == i else None, self.journal_tab == i)
        if self.journal_tab == 0:
            self.text("Главная цель", 90, 115, GOLD, 21)
            y = self.wrap(self.main_goal(), 90, 148, 800, TEXT, 17)
            y = max(y + 14, 210)
            self.text("Задания", 90, y, GOLD, 21)
            y += 36
            active = [(qid, q) for qid, q in QUESTS.items() if self.quest_status(qid) in ("active", "ready")]
            if not active:
                self.text("Нет активных заданий. Поговори с жителями лагеря (знак «!»).", 95, y, MUTED, 17)
            for qid, q in active[:6]:
                have, need = self.quest_progress(qid)
                st = self.quest_status(qid)
                self.text(q["title"] + " — " + NPCS[q["giver"]]["name"], 95, y, GREEN if st == "ready" else TEXT, 17)
                y += 22
                y = self.wrap(q["text"] if st == "active" else "Задание выполнено. Вернись к " + NPCS[q["giver"]]["name"] + ".", 110, y, 780, MUTED, 14)
                self.text("Прогресс: {}/{}".format(have, need), 110, y, GOLD, 14)
                y += 26
            done = sum(1 for qid in QUESTS if self.quest_status(qid) == "done")
            self.text("Выполнено заданий: {}/{}   Подземелий: {}/6   Проходов: {}/2".format(
                done, len(QUESTS), sum(self.p["dungeons"]), sum(self.p["passes"])), 90, 570, MUTED, 17)
        else:
            y = 112
            for kind in ENEMY_ORDER:
                info = ENEMIES[kind]
                seen = kind in self.p["seen"] or kind in self.meta["codex"]["enemies"]
                pygame.draw.rect(self.canvas, (31, 42, 59), (85, y, 830, 28), border_radius=5)
                self.sprite("enemy_" + kind, 104, y + 14, 24)
                self.text(info["name"] if seen else "???", 126, y + 5, TEXT if seen else MUTED, 14)
                if seen:
                    cx = 330
                    for k in ("slash", "pierce", "magic", "blunt"):
                        v = info["res"].get(k, 1.0)
                        col = (255, 170, 70) if v >= 1.2 else MUTED if v <= 0.75 else TEXT
                        self.text("{} ×{:.2f}".format(DTYPE_NAMES[k], v), cx, y + 5, col, 14)
                        cx += 142
                else:
                    self.text("Победи или хотя бы увидь такого врага, чтобы узнать слабости.", 330, y + 5, MUTED, 14)
                y += 31
            self.text("Меч — рубящий · Копьё и лук — колющий · Посох — магия · Молот — дробящий. ▲ слабость, ▼ сопротивление.", 90, 522, MUTED, 14)
            bosses = [(i, b) for i, b in enumerate(BOSSES) if (i < 3 and self.p["bosses"][i]) or (i == 3 and self.p["complete"])]
            if bosses:
                self.text("Побеждённые хранители:", 90, 544, GOLD, 17)
                yy = 566
                for i, b in bosses:
                    self.text("{} — {}".format(b["name"], ", ".join(p[0] for p in self.res_text(b["res"])) or "без слабостей"), 100, yy, TEXT, 14)
                    yy += 18
        self.close_button()

    def draw_map(self):
        self.overlay("Карта")
        self.minimap((90, 120, 540, 372), True)
        self.text("Белый — герой · Красный — враги · Жёлтый — NPC и сундуки", 95, 505, MUTED, 14)
        self.text("Зелёный — лагерь · Фиолетовый — врата и подземелья", 95, 529, MUTED, 14)
        self.text(ZONES[self.zone_index()]["name"] if self.area != "final" else "Сердце Пустоты", 660, 125, GOLD, 21)
        y = self.wrap("Путешествие между регионами идёт через врата: на севере после победы над хранителем и на юге обратно. Врата открываются после победы над хранителем региона.", 660, 170, 260, MUTED, 14)
        self.text("Цель:", 660, y + 20, GOLD, 17)
        self.wrap(self.main_goal(), 660, y + 46, 260, TEXT, 14)
        self.close_button()

    def draw_help(self):
        self.overlay("Как играть")
        lines = [
            ("Движение", "WASD / стрелки. Мышь задаёт направление прицеливания."),
            ("Атака", "SPACE или ЛКМ; SPACE целится в ближайшего врага. R / ПКМ — навык оружия."),
            ("Типы урона", "Меч — рубящий, копьё и лук — колющий, посох — магия, молот — дробящий. У врагов есть слабость (▲) и сопротивление (▼)."),
            ("Защита", "SHIFT — рывок с неуязвимостью (уворачивайся от снарядов). Q — круговой импульс."),
            ("Навыки", "K — дерево навыков (+2 очка за уровень). Активные навыки: клавиши 1–4."),
            ("Бездна", "Режим рогалик: этажи, реликвии с синергиями, души за смерть дают постоянные улучшения."),
            ("Лечение", "H — зелье. E у костра — бесплатный отдых и сохранение."),
            ("Мир", "E — говорить с жителями, сундуки, добыча, врата, подземелья. После босса открываются врата."),
            ("Окна", "I — сумка; C — герой; J — журнал; M / Z — карта; K — навыки."),
            ("Сохранения", "F5 — сохранить; F9 — загрузить. Автосохранение раз в минуту вне боя."),
            ("Система", "ESC или F10 — пауза. F11 — полный экран."),
        ]
        y = 112
        for title, desc in lines:
            self.text(title, 90, y, GOLD, 14)
            y = self.wrap(desc, 215, y, 680, TEXT, 14) + 4
        self.button("В игру · ENTER" if self.session else "Главное меню", (650, 600, 260, 36),
                    self.resume if self.session else lambda: self.set_state("menu"))

    def draw_shop(self):
        self.overlay("Торговец Бруно")
        self.text("Золото: " + str(self.p["gold"]), 100, 130, GOLD, 21)
        self.wrap("Запасись зельями или попробуй другой стиль боя. Чтобы продать предмет, открой сумку рядом с лагерем.", 100, 180, 760, TEXT, 17)
        self.button("Зелье — 20 золота", (100, 260, 360, 45), self.buy_potion, self.p["gold"] >= 20 and self.p["potions"] < 8)
        for i, kind in enumerate(WEAPONS):
            self.button("{} — 55 золота".format(WEAPONS[kind]), (100, 322 + i * 54, 360, 44),
                        lambda k=kind: self.buy_weapon(k), self.p["gold"] >= 55 and len(self.p["inv"]) < 60)
            self.text(DTYPE_NAMES[DTYPES[kind]] + " урон", 480, 334 + i * 54, MUTED, 14)
        self.text("Зелье восстанавливает 40% здоровья.", 560, 275, GREEN, 14)
        self.text("Максимальный запас: 8 зелий.", 560, 310, MUTED, 14)
        self.button("Открыть сумку", (560, 390, 330, 45), lambda: self.set_state("inventory"))
        self.close_button()

    def draw_smith(self):
        self.overlay("Кузнец Харальд")
        self.text("Золото: " + str(self.p["gold"]), 100, 110, GOLD, 21)
        self.wrap("Улучшу снаряжение до +5. Каждое улучшение добавляет характеристики, цена растёт.", 100, 150, 760, TEXT, 17)
        for i, (slot, label) in enumerate(SLOTS.items()):
            y = 220 + i * 110
            item = self.p["equip"][slot]
            pygame.draw.rect(self.canvas, (31, 42, 59), (100, y, 790, 96), border_radius=8)
            if not item:
                self.text(label + ": не экипировано", 130, y + 34, MUTED, 17)
                continue
            art.draw_item_frame(self.canvas, (112, y + 12, 72, 72), item, self.time)
            self.text(item.title, 204, y + 12, item.color, 17)
            self.text(self.item_summary(item), 204, y + 40, MUTED, 14)
            cost = self.upgrade_cost(item)
            if item.plus >= 5:
                self.text("Максимальное улучшение", 204, y + 66, GOLD, 14)
            else:
                self.button("Улучшить — {} зол.".format(cost), (640, y + 26, 230, 44), lambda s=slot: self.upgrade_item(s), self.p["gold"] >= cost)
        self.close_button()

    # ------------------------------------------------------------ dialog
    def draw_dialog(self):
        d = self.dialog
        if not d:
            return
        pygame.draw.rect(self.canvas, (14, 20, 32), (40, 440, 920, 240), border_radius=14)
        pygame.draw.rect(self.canvas, (96, 124, 160), (40, 440, 920, 240), 2, border_radius=14)
        pygame.draw.rect(self.canvas, (28, 38, 54), (58, 458, 150, 170), border_radius=10)
        self.sprite("npc_" + d["npc"], 133, 543, 128)
        info = NPCS[d["npc"]]
        self.text(info["name"], 230, 456, GOLD, 21)
        self.text(info["role"], 230, 484, MUTED, 14)
        shown = d["text"][:int(d["t"] * 45)]
        self.wrap(shown, 230, 512, 700, TEXT, 17)
        x = 230
        for label, action in d["buttons"]:
            self.button(label, (x, 628, 190, 38), action)
            x += 200

    # --------------------------------------------------- menu / pause
    def draw_menu(self):
        self.canvas.fill((12, 20, 32))
        for i in range(45):
            x = int((i * 191 + math.sin(self.time * 0.15 + i) * 15) % VW)
            y = (i * 97) % VH
            pygame.draw.circle(self.canvas, (35, 57, 77), (x, y), 2)
        art.draw_glow(self.canvas, VW / 2, 100, 240, (255, 190, 90), 0.25)
        self.text("ТРОПЫ ЭЛЬДОРИИ", 500, 56, GOLD, 32, True)
        self.text("Одиночная action RPG · приключение и рогалик-Бездна", 500, 106, MUTED, 17, True)
        for i, (label, action, enabled) in enumerate(self.menu_rows()):
            self.button("{}. {}".format(i + 1, label), (315, 132 + i * 47, 370, 40), action, enabled, selected=(i == self.menu_index and enabled))
        self.text("↑/↓ или 1–9 — выбор · ENTER — подтвердить · N — новая игра", 500, 590, MUTED, 14, True)
        self.text("v{} · Душ в святилище: {}".format(VERSION, self.meta["shards"]), 500, 622, MUTED, 14, True)

    def draw_pause(self):
        self.overlay("Пауза")
        rows = [("Продолжить", self.resume), ("Сохранить · F5", self.save_game), ("Загрузить · F9", self.load_game),
                ("Навыки · K", lambda: self.set_state("skills")), ("Настройки", self.open_settings),
                ("Как играть", self.open_help), ("Главное меню", self.to_menu)]
        for i, (label, action) in enumerate(rows):
            self.button(label, (320, 130 + i * 58, 360, 44), action)

    def draw_dead(self):
        if self.mode == "abyss":
            self.overlay("Забег окончен")
            r = self.run
            self.text("Достигнут этаж {}".format(r["floor"]), 500, 150, GOLD, 32, True)
            self.text("Убито врагов: {}   Реликвий: {}   Золота: {}".format(self.run_stats["kills"], sum(self.relics.values()), self.p["gold"]), 500, 215, TEXT, 17, True)
            self.text("Получено душ: {}".format(r.get("shards", 0)), 500, 255, PURPLE, 21, True)
            self.wrap("Души нельзя потерять: потрать их в Святилище, чтобы сделать следующий забег сильнее.", 240, 310, 530, MUTED, 17)
            self.button("Святилище душ", (320, 400, 360, 48), self.open_sanctum)
            self.button("Главное меню", (320, 465, 360, 48), self.to_menu)
            return
        self.overlay("Герой пал")
        self.text("Путь ещё не окончен.", 500, 205, TEXT, 21, True)
        self.wrap("Возрождение вернёт тебя в безопасный лагерь. Ты потеряешь 10% золота, но сохранишь опыт, предметы и прогресс.", 240, 260, 530, MUTED, 17)
        self.button("Возродиться · R", (320, 365, 360, 48), self.respawn)
        self.button("Загрузить сохранение · F9", (320, 430, 360, 48), self.load_game)
        self.button("Главное меню", (320, 495, 360, 48), self.to_menu)

    def draw_sanctum(self):
        self.canvas.fill((14, 12, 28))
        for i in range(40):
            pygame.draw.circle(self.canvas, (60, 40, 90), (int((i * 173 + math.sin(self.time * 0.3 + i) * 12) % VW), int((i * 71) % VH)), 2)
        art.draw_glow(self.canvas, 500, 90, 200, PURPLE, 0.3)
        self.text("Святилище душ", 500, 40, PURPLE, 32, True)
        self.text("Души: {}    Лучший этаж: {}    Забегов: {}".format(self.meta["shards"], self.meta["best"], self.meta["runs"]), 500, 92, TEXT, 21, True)
        for i, (key, (name, desc, maxr, base)) in enumerate(META.items()):
            y = 150 + i * 78
            rank = self.meta["upgrades"].get(key, 0)
            pygame.draw.rect(self.canvas, (28, 24, 48), (80, y, 840, 68), border_radius=10)
            pygame.draw.rect(self.canvas, (96, 70, 150), (80, y, 840, 68), 1, border_radius=10)
            self.text(name, 100, y + 8, TEXT, 21)
            self.text(desc, 100, y + 38, MUTED, 14)
            for k in range(maxr):
                pygame.draw.circle(self.canvas, PURPLE if k < rank else (60, 52, 90), (560 + k * 16, y + 22), 6, 0 if k < rank else 1)
            cost = base * (rank + 1)
            self.button("Улучшить — {}".format(cost) if rank < maxr else "Максимум", (730, y + 14, 170, 40),
                        lambda k=key: self.buy_meta(k), rank < maxr and self.meta["shards"] >= cost)
        self.button("Главное меню · ESC", (370, 600, 260, 40), lambda: self.set_state("menu"))

    def draw_boon(self):
        b = self.boon
        shade = pygame.Surface((VW, VH), pygame.SRCALPHA)
        shade.fill((4, 6, 14, 215))
        self.canvas.blit(shade, (0, 0))
        self.text(b["title"], 500, 70, GOLD, 32, True)
        if b["kind"] == "shop":
            self.text("Золото: {}".format(self.p["gold"]), 500, 122, TEXT, 21, True)
        else:
            self.text("Выбери одну реликвию", 500, 122, MUTED, 17, True)
        for i, offer in enumerate(b["offers"]):
            x = 60 + i * 300
            mod = offer["mod"]
            rect = pygame.Rect(x, 170, 280, 330)
            have = self.mod_count(mod)
            affordable = offer["price"] is None or self.p["gold"] >= offer["price"]
            sold = offer.get("sold")
            pygame.draw.rect(self.canvas, (36, 28, 58) if not sold else (24, 24, 30), rect, border_radius=14)
            pygame.draw.rect(self.canvas, PURPLE if not sold else (60, 60, 70), rect, 2, border_radius=14)
            art.draw_glow(self.canvas, x + 140, 250, 80, PURPLE, 0.35 if not sold else 0)
            pygame.draw.circle(self.canvas, PURPLE if not sold else (70, 70, 80), (x + 140, 250), 34)
            pygame.draw.circle(self.canvas, (255, 255, 255), (x + 128, 238), 8)
            self.text(MODS[mod][0], x + 140, 310, TEXT, 21, True)
            self.wrap(MODS[mod][1], x + 20, 350, 240, MUTED, 17)
            if have:
                self.text("Уже есть: ×{}".format(have), x + 140, 420, GOLD, 14, True)
            label = "Забрать" if offer["price"] is None else ("Продано" if sold else "Купить — {}".format(offer["price"]))
            self.button(label, (x + 40, 445, 200, 42), lambda o=offer: self.pick_boon(o), affordable and not sold)
        self.button("Закрыть" if b["kind"] == "shop" else "Пропустить", (400, 560, 200, 42), self.close_boon)

    def draw_victory(self):
        self.overlay("Эльдория спасена")
        self.text("Сердце Пустоты уничтожено", 500, 190, GOLD, 32, True)
        self.wrap("Леса снова слышат птиц, древние руины обрели покой, а над пустошами появился рассвет. Твой основной путь завершён.", 210, 260, 580, TEXT, 21)
        self.text("Уровень: {}   Победы: {}   Подземелья: {}/3".format(self.p["level"], self.p["kills"], sum(self.p["dungeons"])), 500, 405, GREEN, 17, True)
        self.button("Продолжить исследование · ENTER", (280, 465, 440, 48), self.continue_after_win)
        self.button("Главное меню", (340, 530, 320, 45), self.to_menu)

    # ----------------------------------------------------------- creator
    def draw_creator(self):
        self.canvas.fill((14, 22, 34))
        for i in range(30):
            pygame.draw.circle(self.canvas, (32, 52, 72), (int((i * 211) % VW), int((i * 83) % VH)), 2)
        abyss = self.creator.get("mode") == "abyss"
        self.text("Выбери героя" + (" для Бездны" if abyss else ""), 500, 30, GOLD, 32, True)
        sel = self.creator["char"]
        for i, ch in enumerate(CHARACTERS):
            x = 40 + i * 316
            rect = pygame.Rect(x, 90, 300, 440)
            chosen = i == sel
            pygame.draw.rect(self.canvas, (36, 50, 72) if chosen else (24, 34, 50), rect, border_radius=14)
            pygame.draw.rect(self.canvas, GOLD if chosen else (60, 76, 100), rect, 3 if chosen else 1, border_radius=14)
            if chosen:
                art.draw_glow(self.canvas, x + 150, 230, 130, GOLD, 0.2)
            art.shadow(self.canvas, x + 150, 305, 50, 15)
            bob = math.sin(self.time * 2.2 + i) * 3 if chosen else 0
            self.sprite("char{}_down".format(i), x + 150, 225 + bob, 160)
            art.draw_weapon(self.canvas, ch["weapon"], 0, GOLD, x + 196, 235 + bob, 1.3, 1.6, self.time, ch["weapon"] == "staff")
            self.text(ch["name"], x + 150, 318, TEXT, 21, True)
            self.text("{} · {}".format(ch["cls"], WEAPONS[ch["weapon"]]), x + 150, 346, MUTED, 14, True)
            self.text("Сила {} · Живучесть {} · Ловкость {}".format(*ch["stats"]), x + 150, 368, TEXT, 14, True)
            self.text("Перк: " + ch["perk"], x + 150, 392, GREEN, 17, True)
            self.wrap(ch["perk_text"], x + 18, 416, 266, MUTED, 14)
            self.wrap("Старт: {}; навык «{}»".format(ch["item"]["name"], SKILLS[ch["skill"][0]]["name"].split(" [")[0]), x + 18, 462, 266, MUTED, 14)
            self.card(rect, lambda k=i: self.creator.__setitem__("char", k))
        if abyss:
            heat = self.creator.setdefault("heat", set())
            self.text("Накал (больше душ за забег):", 40, 500, GOLD, 14)
            for i, (hid, name, desc) in enumerate(HEAT):
                col, row = divmod(i, 3)
                on = hid in heat
                self.button(("✓ " if on else "") + name, (40 + col * 232, 522 + row * 34, 224, 30),
                            lambda h=hid: (heat.discard(h) if h in heat else heat.add(h)), True, GOLD if on else None, on)
            self.text("Бонус душ: +{}%".format(round(HEAT_BONUS * 100 * len(heat))), 740, 524, PURPLE, 17)
            daily = bool(self.creator.get("daily"))
            self.button(("✓ " if daily else "") + "Ежедневный забег", (740, 552, 220, 30), lambda: self.creator.__setitem__("daily", not daily), True, GOLD if daily else None, daily)
            self.button("В Бездну · ENTER", (740, 622, 220, 44), self.finish_creator)
            self.button("Назад · ESC", (40, 630, 160, 40), lambda: self.set_state("menu"))
        else:
            self.wrap(CHARACTERS[sel]["desc"], 40, 548, 600, TEXT, 17)
            self.button("Начать путь · ENTER", (740, 590, 220, 48), self.finish_creator)
            self.button("Назад · ESC", (40, 590, 160, 48), lambda: self.set_state("slots"))

    def sky(self, top, bottom):
        for y in range(0, VH, 10):
            k = y / VH
            c = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
            pygame.draw.rect(self.canvas, c, (0, y, VW, 10))

    def draw_cut_scene(self, scene, t):
        rng = random.Random(5)
        if scene in ("stars", "blood", "hero"):
            if scene == "blood":
                self.sky((40, 8, 18), (120, 30, 30))
            else:
                self.sky((6, 10, 30), (24, 30, 64))
            for i in range(90):
                x, y = rng.randint(0, VW), rng.randint(0, 420)
                tw = 0.5 + 0.5 * math.sin(t * 2 + i)
                col = (255, 160, 150) if scene == "blood" else (255, 255, 255)
                pygame.draw.circle(self.canvas, rgb(col, 0.4 + 0.6 * tw), (x, y), 1 + (i % 3 == 0))
            moon = (230, 90, 90) if scene == "blood" else (235, 235, 215)
            art.draw_glow(self.canvas, 760, 150, 130, moon, 0.5)
            pygame.draw.circle(self.canvas, moon, (760, 150), 52)
            if scene == "blood":
                pygame.draw.lines(self.canvas, (120, 30, 40), False, [(730, 120), (755, 150), (745, 180), (775, 200)], 3)
                for i in range(40):
                    x = (rng.randint(0, VW) + t * 30 * (1 + i % 3)) % VW
                    y = (rng.randint(0, VH) + t * 45) % VH
                    pygame.draw.circle(self.canvas, (200, 90, 70), (int(x), int(y)), 2)
            pygame.draw.polygon(self.canvas, (8, 12, 22), [(0, 520), (160, 430), (340, 500), (520, 410), (720, 500), (900, 440), (1000, 500), (1000, 700), (0, 700)])
            if scene == "hero":
                art.draw_glow(self.canvas, 500, 440, 220, GOLD, 0.3)
                self.sprite(self.hero_sprite_name("hero_down"), 500, 430, 240)
        elif scene == "village":
            self.sky((30, 18, 40), (150, 80, 60))
            pygame.draw.polygon(self.canvas, (14, 14, 24), [(0, 520), (200, 450), (420, 520), (640, 470), (1000, 520), (1000, 700), (0, 700)])
            for (x, y, s) in ((200, 500, 1.0), (430, 520, 1.3), (700, 505, 1.1), (860, 530, 0.9)):
                pygame.draw.polygon(self.canvas, (24, 22, 32), [(x - 60 * s, y), (x, y - 90 * s), (x + 60 * s, y)])
            art.draw_campfire(self.canvas, 560, 560, t)
            for i in range(14):
                ph = (t * 0.4 + i * 0.17) % 1
                pygame.draw.circle(self.canvas, (255, 190, 90), (int(560 + math.sin(i * 3 + t) * 60 * ph), int(540 - ph * 260)), 2)
        elif scene == "forest":
            self.sky((10, 30, 30), (30, 70, 60))
            for i in range(9):
                x = 60 + i * 120 + (i % 2) * 30
                h = 280 + (i * 37) % 120
                pygame.draw.polygon(self.canvas, (10, 30, 24), [(x - 70, 640), (x, 640 - h), (x + 70, 640)])
            pygame.draw.rect(self.canvas, (8, 22, 18), (0, 600, VW, 100))
            for i in range(26):
                a = t * 0.6 + i * 1.3
                pygame.draw.circle(self.canvas, (200, 255, 150), (int(100 + (i * 83 + math.sin(a) * 40) % 800), int(300 + (i * 47) % 300 + math.cos(a * 1.3) * 20)), 3)
        else:  # dawn
            self.sky((250, 170, 90), (255, 230, 170))
            sun = 520 - min(1, t / 6) * 120
            art.draw_glow(self.canvas, 500, sun, 320, (255, 240, 190), 0.8)
            pygame.draw.circle(self.canvas, (255, 245, 210), (500, int(sun)), 70)
            pygame.draw.polygon(self.canvas, (60, 40, 40), [(0, 560), (200, 500), (400, 560), (700, 490), (1000, 560), (1000, 700), (0, 700)])

    def draw_cutscene(self):
        cut = self.cut
        slide = cut["slides"][cut["i"]]
        self.draw_cut_scene(slide["scene"], self.time)
        pygame.draw.rect(self.canvas, (0, 0, 0), (0, 0, VW, 70))
        pygame.draw.rect(self.canvas, (0, 0, 0), (0, VH - 190, VW, 190))
        text = fmt(slide["text"], self.char())
        shown = text[:int(cut["t"] * 38)]
        self.wrap(shown, 90, VH - 170, 820, TEXT, 21)
        self.text("ENTER — дальше · ESC — пропустить", 500, VH - 36, MUTED, 14, True)

    def draw(self):
        self.buttons = []
        if self.state in ("menu",) or (not self.session and self.state not in ("creator", "cutscene", "sanctum", "slots", "credits")):
            self.draw_menu()
        elif self.state == "slots":
            self.draw_slots()
        elif self.state == "credits":
            self.draw_credits()
        elif self.state == "creator":
            self.draw_creator()
        elif self.state == "sanctum":
            self.draw_sanctum()
        elif self.state == "cutscene":
            self.draw_cutscene()
        else:
            self.draw_world()
            self.draw_hud()
            self.draw_banners()
            if self.state == "boon":
                self.draw_boon()
        draws = {"pause": self.draw_pause, "inventory": self.draw_inventory, "stats": self.draw_stats,
                 "skills": self.draw_skills, "journal": self.draw_journal, "map": self.draw_map,
                 "settings": self.draw_settings, "records": self.draw_records, "help": self.draw_help, "shop": self.draw_shop,
                 "smith": self.draw_smith, "dialog": self.draw_dialog, "dead": self.draw_dead,
                 "victory": self.draw_victory}
        if self.state in draws:
            draws[self.state]()
        self.draw_overlays_extra()
        if self.toast_time > 0 and self.state != "cutscene":
            pygame.draw.rect(self.canvas, (13, 20, 31), (25, 4, 950, 35), border_radius=7)
            self.text(self.toast, 500, 10, self.toast_color, 14, True)
        self.window.fill((0, 0, 0))
        image = pygame.transform.smoothscale(self.canvas, self.viewport.size)
        self.window.blit(image, self.viewport)
        pygame.display.flip()
