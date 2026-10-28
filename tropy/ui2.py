"""Settings pages, save slots, records, credits and screen overlays (mixin for Game)."""
import math

import pygame

from .common import *
from .content import *
from .meta import ACHIEVEMENTS, CREDITS, DIFFICULTY, HEAT, HEAT_BONUS
from .inputmap import ACTIONS, LABELS, key_label
from . import art
from . import common as C

CB_NAMES = ["Выкл", "Красно-зелёный", "Сине-жёлтый"]
SHAKE_NAMES = {0.0: "Выкл", 0.25: "Слабая", 0.5: "Средняя", 0.75: "Сильная", 1.0: "Полная"}


def fmt_time(seconds):
    h, rest = divmod(int(seconds), 3600)
    return "{}ч {:02d}м".format(h, rest // 60)


class UI2Mixin:
    # ------------------------------------------------------------ settings
    def open_records(self):
        self.back_state = "menu"
        self.set_state("records")

    def opt_row(self, y, label, value, dec=None, inc=None, toggle=None):
        self.text(label, 110, y + 6, TEXT, 17)
        if toggle:
            self.button(value, (560, y - 2, 280, 36), toggle)
            return
        self.button("◄", (560, y - 2, 48, 36), dec or (lambda: None), dec is not None)
        self.text(value, 700, y + 6, TEXT, 17, True)
        self.button("►", (792, y - 2, 48, 36), inc or (lambda: None), inc is not None)

    def draw_settings(self):
        self.overlay("Настройки")
        for i, label in enumerate(("Экран", "Звук", "Игра", "Управление")):
            self.button(label, (110 + i * 150, 110, 142, 34), lambda k=i: setattr(self, "settings_tab", k), True,
                        GOLD if self.settings_tab == i else None, self.settings_tab == i)
        s = self.settings
        y = 180
        if self.settings_tab == 0:
            res = RESOLUTIONS[s["resolution"]]
            self.opt_row(y, "Размер окна", "{} × {}".format(*res), (lambda: self.change_resolution(-1)) if not s["fullscreen"] else None,
                         (lambda: self.change_resolution(1)) if not s["fullscreen"] else None)
            self.opt_row(y + 56, "Полный экран", "ВКЛ" if s["fullscreen"] else "ВЫКЛ", toggle=self.toggle_fullscreen)
            self.opt_row(y + 112, "Упрощённая графика", "ВКЛ" if s["lowfx"] else "ВЫКЛ", toggle=lambda: self.opt_toggle("lowfx"))
            self.opt_row(y + 168, "Счётчик FPS (F3)", "ВКЛ" if s["fps"] else "ВЫКЛ", toggle=lambda: self.opt_toggle("fps"))
            self.wrap("Окно можно растягивать мышью. «Упрощённая графика» убирает свечения и часть частиц для слабых компьютеров.", 110, y + 240, 740, MUTED, 14)
        elif self.settings_tab == 1:
            self.opt_row(y, "Общая громкость", "{}%".format(round(s["volume"] * 100)), lambda: self.opt_float("volume", -0.1), lambda: self.opt_float("volume", 0.1))
            self.opt_row(y + 56, "Музыка", "ВКЛ" if s["music"] else "ВЫКЛ", toggle=lambda: self.opt_toggle("music"))
            self.opt_row(y + 112, "Громкость музыки", "{}%".format(round(s["music_vol"] * 100)), lambda: self.opt_float("music_vol", -0.1), lambda: self.opt_float("music_vol", 0.1))
            self.opt_row(y + 168, "Громкость эффектов", "{}%".format(round(s["sfx"] * 100)), lambda: self.opt_float("sfx", -0.1), lambda: self.opt_float("sfx", 0.1))
            self.wrap("Звуки и музыка создаются программно. При потере фокуса окна звук и игра ставятся на паузу.", 110, y + 240, 740, MUTED, 14)
        elif self.settings_tab == 2:
            name, hp, dmg, desc = DIFFICULTY[s["difficulty"]][0], DIFFICULTY[s["difficulty"]][1], DIFFICULTY[s["difficulty"]][2], DIFFICULTY[s["difficulty"]][3]
            self.opt_row(y, "Сложность кампании", name, lambda: self.opt_cycle("difficulty", -1, 3), lambda: self.opt_cycle("difficulty", 1, 3))
            self.text(desc, 110, y + 40, MUTED, 14)
            shake = SHAKE_NAMES.get(round(s["shake"] * 4) / 4, "Полная")
            self.opt_row(y + 76, "Тряска экрана", shake, lambda: self.opt_float("shake", -0.25), lambda: self.opt_float("shake", 0.25))
            self.opt_row(y + 132, "Яркие вспышки", "ВКЛ" if s["flash"] else "ВЫКЛ (щадящий режим)", toggle=lambda: self.opt_toggle("flash"))
            self.opt_row(y + 188, "Числа урона", "ВКЛ" if s["numbers"] else "ВЫКЛ", toggle=lambda: self.opt_toggle("numbers"))
            self.opt_row(y + 244, "Режим для дальтоников", CB_NAMES[s["colorblind"]], lambda: self.opt_cycle("colorblind", -1, 3), lambda: self.opt_cycle("colorblind", 1, 3))
        else:
            self.text("Нажми кнопку и затем новую клавишу. Стрелки всегда дублируют движение.", 110, 156, MUTED, 14)
            for i, (action, label, _) in enumerate(ACTIONS):
                col, row = divmod(i, 8)
                x = 110 + col * 400
                yy = 184 + row * 46
                self.text(label, x, yy + 8, TEXT, 17)
                waiting = self.rebinding == action
                self.button("нажми клавишу…" if waiting else key_label(self.keys[action]), (x + 190, yy, 170, 36),
                            lambda a=action: self.start_rebind(a), True, GOLD if waiting else None, waiting)
            self.button("По умолчанию", (110, 560, 200, 34), self.reset_keys)
            self.text("Геймпад: стик — движение, правый стик — прицел, X атака, B рывок, A действие, RB навык, LB импульс.", 330, 568, MUTED, 14)
        self.button("Титры", (110, 600, 120, 36), lambda: self.open_credits())
        self.button("Назад", (760, 600, 145, 36), lambda: self.set_state(self.back_state))

    def open_credits(self):
        self.set_state("credits")

    def draw_credits(self):
        self.canvas.fill((10, 14, 26))
        art.draw_glow(self.canvas, VW / 2, 120, 240, GOLD, 0.2)
        y = 80 - int((self.time * 8) % 1)
        for head, body in CREDITS:
            if not body:
                self.text(head, 500, y, GOLD, 32, True)
                y += 70
                continue
            self.text(head, 500, y, GOLD, 17, True)
            y += 26
            y = self.wrap(body, 150, y, 700, TEXT, 17) + 22
        self.text("v{}".format(VERSION), 500, 640, MUTED, 14, True)
        self.button("Назад", (430, 650, 140, 36), lambda: self.set_state(self.back_state))

    # --------------------------------------------------------------- slots
    def draw_slots(self):
        self.canvas.fill((12, 20, 32))
        title = "Загрузить игру" if self.slots_mode == "load" else "Новая игра: выбери слот"
        self.text(title, 500, 50, GOLD, 32, True)
        for n in range(1, C.SLOT_COUNT + 1):
            x = 50 + (n - 1) * 310
            rect = pygame.Rect(x, 130, 290, 340)
            info = self.slot_info(n)
            confirm = self.slots_confirm == n
            pygame.draw.rect(self.canvas, (36, 50, 72) if info else (22, 30, 44), rect, border_radius=14)
            pygame.draw.rect(self.canvas, GOLD if confirm else (80, 104, 140), rect, 3 if confirm else 1, border_radius=14)
            self.text("Слот {}".format(n), x + 145, 148, GOLD, 21, True)
            if info:
                zone = ZONES[int(info["area"][-1])]["name"] if info["area"][-1:] in "012" else "?"
                self.text(info["name"], x + 145, 196, TEXT, 21, True)
                self.text("Уровень {}".format(info["level"]), x + 145, 232, TEXT, 17, True)
                self.text(zone, x + 145, 258, MUTED, 14, True)
                self.text("Золото: {} · Хранителей: {}/3".format(info["gold"], info["bosses"]), x + 145, 284, MUTED, 14, True)
                self.text("Время игры: " + fmt_time(info["time"]), x + 145, 310, MUTED, 14, True)
                if info["legacy"]:
                    self.text("перенос из старой версии", x + 145, 336, GREEN, 14, True)
            else:
                self.text("Пусто", x + 145, 260, MUTED, 21, True)
            self.card(rect, lambda k=n: self.choose_slot(k), bool(info) or self.slots_mode == "new")
            if info and self.slots_mode == "load":
                self.button("Удалить" if self.slots_confirm != -n else "Точно?", (x + 70, 400, 150, 36), lambda k=n: self.delete_slot(k), True, RED)
        if self.slots_mode == "new":
            self.text("Если слот занят, старое сохранение будет перенесено в архив.", 500, 500, MUTED, 14, True)
        self.button("Назад · ESC", (400, 600, 200, 40), lambda: self.set_state("menu"))

    # ------------------------------------------------------------- records
    def draw_records(self):
        self.overlay("Достижения и записи")
        for i, label in enumerate(("Достижения", "Кодекс", "Рекорды", "Забеги")):
            self.button(label, (420 + i * 125, 62, 118, 34), lambda k=i: setattr(self, "records_tab", k), True,
                        GOLD if self.records_tab == i else None, self.records_tab == i)
        m = self.meta
        if self.records_tab == 0:
            self.text("Открыто: {}/{}".format(len(m["ach"]), len(ACHIEVEMENTS)), 90, 112, GOLD, 17)
            for i, (aid, (name, desc)) in enumerate(ACHIEVEMENTS.items()):
                col, row = divmod(i, 14)
                x, y = 90 + col * 420, 142 + row * 31
                got = aid in m["ach"]
                self.text(("★ " if got else "· ") + (name if got else "???"), x, y, GOLD if got else MUTED, 14)
                self.text(desc if got else "скрыто", x + 170, y, TEXT if got else (100, 110, 130), 14)
        elif self.records_tab == 1:
            cx = m["codex"]
            self.text("Враги", 90, 112, GOLD, 17)
            for i, kind in enumerate(ENEMY_ORDER):
                known = kind in cx["enemies"]
                self.text(ENEMIES[kind]["name"] if known else "???", 90, 140 + i * 24, TEXT if known else MUTED, 14)
            self.text("Хранители", 310, 112, GOLD, 17)
            names = [b["name"] for b in BOSSES]
            for i, nm in enumerate(names):
                self.text(nm if nm in cx["bosses"] else "???", 310, 140 + i * 24, TEXT if nm in cx["bosses"] else MUTED, 14)
            self.text("Уникальные предметы", 310, 250, GOLD, 17)
            for i, uid in enumerate(UNIQUES):
                nm = UNIQUES[uid]["name"]
                self.text(nm if nm in cx["uniques"] else "???", 310, 278 + i * 24, PURPLE if nm in cx["uniques"] else MUTED, 14)
            self.text("Реликвии и свойства ({}/{})".format(len(cx["mods"]), len(MODS)), 560, 112, GOLD, 17)
            for i, (mid, (nm, desc)) in enumerate(MODS.items()):
                col, row = divmod(i, 15)
                known = mid in cx["mods"]
                self.text(nm if known else "???", 560 + col * 190, 140 + row * 24, TEXT if known else MUTED, 14)
        elif self.records_tab == 2:
            st = m["stats"]
            lines = [("Время игры", fmt_time(st["playtime"])), ("Побеждено врагов", st["kills"]), ("Смертей", st["deaths"]),
                     ("Ударов по слабости", st["weak_hits"]), ("Элитных врагов", st.get("elites", 0)),
                     ("Лучший этаж Бездны", m["best"]), ("Забегов в Бездне", m["runs"]), ("Душ в святилище", m["shards"]),
                     ("Достижений", "{}/{}".format(len(m["ach"]), len(ACHIEVEMENTS))),
                     ("Кодекс", "{}/{}".format(len(m["codex"]["enemies"]) + len(m["codex"]["mods"]) + len(m["codex"]["uniques"]) + len(m["codex"]["bosses"]),
                                               len(ENEMY_ORDER) + len(MODS) + len(UNIQUES) + len(BOSSES)))]
            for i, (k, v) in enumerate(lines):
                self.text(k, 120, 140 + i * 40, MUTED, 21)
                self.text(str(v), 520, 140 + i * 40, TEXT, 21)
        else:
            if not m["history"]:
                self.text("Забегов в Бездне ещё не было.", 120, 150, MUTED, 21)
            for i, h in enumerate(reversed(m["history"])):
                y = 140 + i * 40
                self.text("{}. {} — этаж {}, врагов {}, душ +{}".format(i + 1, h.get("char", "?"), h.get("floor", 0), h.get("kills", 0), h.get("shards", 0)), 110, y, TEXT, 17)
                self.text("накал {} · сид {}".format(h.get("heat", 0), h.get("seed", "-")), 640, y, MUTED, 14)
        self.close_button_to_menu()

    def close_button_to_menu(self):
        self.button("Назад · ESC", (770, 600, 145, 36), lambda: self.set_state("menu"))

    # ----------------------------------------------------------- overlays
    def draw_overlays_extra(self):
        if self.hint_t > 0 and self.state == "play":
            a = clamp(min(self.hint_t, 0.5) * 2, 0, 1)
            box = pygame.Rect(150, 536, 700, 54)
            pygame.draw.rect(self.canvas, (14, 20, 32), box, border_radius=10)
            pygame.draw.rect(self.canvas, rgb(GOLD, a), box, 2, border_radius=10)
            self.wrap(self.hint_text, 168, 546, 664, rgb(TEXT, a), 14)
        y = 50
        for name, desc, t in self.ach_toasts[:3]:
            x = VW - 330 + int(max(0, 0.4 - (5.0 - t)) * 800)
            pygame.draw.rect(self.canvas, (22, 30, 46), (x, y, 316, 58), border_radius=8)
            pygame.draw.rect(self.canvas, GOLD, (x, y, 316, 58), 2, border_radius=8)
            self.text("★ " + name, x + 12, y + 8, GOLD, 17)
            self.text(desc[:42], x + 12, y + 32, MUTED, 14)
            y += 66
        if self.settings["fps"]:
            self.text("FPS {:.0f} · частиц {} · пуль {}".format(self.fps_smooth, len(self.particles), len(self.bullets)), 330, 134, GREEN, 14)
        if self.pad_active and self.state not in ("play", "cutscene"):
            found = self.focused_button()
            if found:
                r = found[0]
                pygame.draw.rect(self.canvas, GOLD, r.inflate(8, 8), 3, border_radius=9)
            self.text("A — выбрать   B — назад   D-pad / стик — перемещение", 500, 672, MUTED, 14, True)
