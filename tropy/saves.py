"""Settings and save files (mixin for Game)."""
import json
import math
import os
import shutil
from dataclasses import asdict
from pathlib import Path

from .common import *
from . import common as C
from .content import QUESTS, SKILLS, META
from .inputmap import clean_keys
from .meta import ACHIEVEMENTS, HINTS
from . import world as W
from .models import Item, Enemy, KINDS

VALID_AREAS = {"zone0", "zone1", "zone2"}


class SaveMixin:
    def default_settings(self):
        return {"resolution": 1, "fullscreen": False, "volume": 0.6, "music": True, "music_vol": 0.7, "sfx": 1.0,
                "shake": 1.0, "flash": True, "numbers": True, "colorblind": 0, "difficulty": 1, "lowfx": False,
                "fps": False, "keys": clean_keys(None)}

    def load_settings(self):
        self.settings = self.default_settings()
        try:
            data = json.loads(C.SETTINGS_FILE.read_text(encoding="utf8"))
            if not isinstance(data, dict):
                return
            idx = data.get("resolution")
            if type(idx) is int and 0 <= idx < len(RESOLUTIONS):
                self.settings["resolution"] = idx
            for key in ("fullscreen", "music", "flash", "numbers", "lowfx", "fps"):
                if type(data.get(key)) is bool:
                    self.settings[key] = data[key]
            for key in ("volume", "music_vol", "sfx", "shake"):
                v = data.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                    self.settings[key] = clamp(float(v), 0.0, 1.0)
            for key, hi in (("colorblind", 2), ("difficulty", 2)):
                if type(data.get(key)) is int and 0 <= data[key] <= hi:
                    self.settings[key] = data[key]
            self.settings["keys"] = clean_keys(data.get("keys"))
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_settings(self):
        try:
            C.DATA.mkdir(parents=True, exist_ok=True)
            tmp = C.SETTINGS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf8")
            os.replace(tmp, C.SETTINGS_FILE)
        except OSError:
            self.notify("Не удалось сохранить настройки.", RED)

    def load_profile(self):
        self.meta = {"shards": 0, "best": 0, "runs": 0, "upgrades": {}, "ach": [], "hints": [], "history": [],
                     "codex": {"mods": [], "uniques": [], "enemies": [], "bosses": []},
                     "stats": {"kills": 0, "deaths": 0, "playtime": 0, "weak_hits": 0}}
        try:
            data = json.loads(C.PROFILE_FILE.read_text(encoding="utf8"))
            for key in ("shards", "best", "runs"):
                if type(data.get(key)) is int and 0 <= data[key] <= 10 ** 9:
                    self.meta[key] = data[key]
            for key, rank in data.get("upgrades", {}).items():
                if key in META and type(rank) is int and 0 <= rank <= META[key][2]:
                    self.meta["upgrades"][key] = rank
            self.meta["ach"] = [a for a in data.get("ach", []) if a in ACHIEVEMENTS]
            self.meta["hints"] = [h for h in data.get("hints", []) if h in HINTS]
            for key in self.meta["codex"]:
                vals = data.get("codex", {}).get(key, [])
                self.meta["codex"][key] = [v for v in vals if isinstance(v, str) and len(v) < 40][:80]
            for key in self.meta["stats"]:
                v = data.get("stats", {}).get(key)
                if type(v) is int and 0 <= v <= 10 ** 10:
                    self.meta["stats"][key] = v
            hist = data.get("history", [])
            self.meta["history"] = [h for h in hist if isinstance(h, dict)][-10:]
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_profile(self):
        try:
            C.DATA.mkdir(parents=True, exist_ok=True)
            tmp = C.PROFILE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding="utf8")
            os.replace(tmp, C.PROFILE_FILE)
        except OSError:
            self.notify("Не удалось сохранить прогресс святилища.", RED)

    def archive_save(self, slot=None):
        """Keep the previous progress of a slot in a separate file before overwriting it."""
        slot = slot or self.slot
        path = C.slot_file(slot)
        if not path.exists():
            return True
        try:
            C.DATA.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, C.DATA / "eldoria_v35_slot{}.archive.json".format(slot))
            return True
        except OSError:
            self.notify("Не удалось архивировать старое сохранение. Новая игра отменена.", RED)
            return False

    def decode_save(self, data):
        if not isinstance(data, dict) or data.get("version") not in (32, 33, 34, VERSION):
            raise ValueError("Неподдерживаемая версия сохранения")
        legacy = data["version"] < 34
        raw = data.get("player")
        if not isinstance(raw, dict):
            raise ValueError("Повреждён герой")
        p = self.new_player()
        pt = raw.get("playtime", 0)
        p["playtime"] = int(pt) if type(pt) is int and 0 <= pt <= 10 ** 9 else 0
        limits = {"x": (0, WW), "y": (0, WH), "hp": (0, 1000000), "level": (1, 1000), "xp": (0, 1e100),
                  "xpnext": (1, 1e100), "str": (1, 10000), "vit": (1, 10000), "agi": (1, 10000),
                  "points": (0, 100000), "gold": (0, 1e12), "potions": (0, 8), "kills": (0, 1e12),
                  "face_x": (-1.01, 1.01), "face_y": (-1.01, 1.01), "return_x": (0, WW), "return_y": (0, WH)}
        ints = {"level", "xp", "xpnext", "str", "vit", "agi", "points", "gold", "potions", "kills"}
        for key, (lo, hi) in limits.items():
            value = raw[key]
            number(value, lo, hi)
            if key in ints and type(value) is not int:
                raise ValueError("Ожидалось целое число: " + key)
            p[key] = value
        for key, size in (("bosses", 3), ("dungeons", 3 if legacy else 6)):
            values = raw[key]
            if not isinstance(values, list) or len(values) != size or any(type(v) is not bool for v in values):
                raise ValueError("Повреждён прогресс")
            p[key] = values[:]
        if legacy:
            p["dungeons"] = [p["dungeons"][0], False, p["dungeons"][1], False, p["dungeons"][2], False]
            p["passes"] = [p["bosses"][0], p["bosses"][1]]
        else:
            passes = raw["passes"]
            if not isinstance(passes, list) or len(passes) != 2 or any(type(v) is not bool for v in passes):
                raise ValueError("Повреждены проходы")
            p["passes"] = passes[:]
        values = raw["zonekills"]
        if not isinstance(values, list) or len(values) != 3:
            raise ValueError("Повреждены счётчики")
        for value in values:
            number(value, 0, 1e12)
            if type(value) is not int:
                raise ValueError("Повреждены счётчики")
        p["zonekills"] = values[:]
        chests = raw["chests"]
        if not isinstance(chests, list) or len(chests) != 3:
            raise ValueError("Повреждены сундуки")
        for row in chests:
            if (not isinstance(row, list) or len(row) > 3 or any(type(i) is not int or i not in (0, 1, 2) for i in row)
                    or len(set(row)) != len(row)):
                raise ValueError("Повреждены сундуки")
        p["chests"] = [row[:] for row in chests]
        if type(raw["complete"]) is not bool:
            raise ValueError("Повреждён финал")
        p["complete"] = raw["complete"]
        if p["complete"] and not all(p["bosses"]):
            raise ValueError("Противоречивый прогресс")
        equip = raw["equip"]
        if not isinstance(equip, dict) or set(equip) != set(SLOTS):
            raise ValueError("Повреждена экипировка")
        for slot in SLOTS:
            item = Item.restore(equip[slot]) if equip[slot] is not None else None
            if item and item.slot != slot:
                raise ValueError("Предмет в неправильном слоте")
            p["equip"][slot] = item
        inv = raw["inv"]
        if not isinstance(inv, list) or len(inv) > 60:
            raise ValueError("Повреждён инвентарь")
        p["inv"] = [Item.restore(item) for item in inv]

        if legacy:
            p["sp"] = max(0, (p["level"] - 1) * 2 - sum(1 for _ in ()))
            if data["version"] == 33:
                p["name"] = str(raw.get("name", "Странник"))[:14] or "Странник"
                p["skills"] = {k: v for k, v in raw.get("skills", {}).items() if k in SKILLS and type(v) is int and 0 <= v <= SKILLS[k]["max"]}
                p["sp"] = raw.get("sp", 0) if type(raw.get("sp", 0)) is int else 0
                p["seen"] = [k for k in raw.get("seen", []) if k in KINDS][:12]
                p["quests"] = {k: v for k, v in raw.get("quests", {}).items() if k in QUESTS and isinstance(v, dict)
                               and type(v.get("s")) is int and type(v.get("n")) is int and 0 <= v["s"] <= 3 and 0 <= v["n"] <= 999}
        else:
            if type(raw["char"]) is not int or not 0 <= raw["char"] <= 2:
                raise ValueError("Повреждён герой")
            p["char"] = raw["char"]
            name = raw["name"]
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 14:
                raise ValueError("Повреждено имя")
            p["name"] = name
            number(raw["sp"], 0, 10000)
            if type(raw["sp"]) is not int:
                raise ValueError("Повреждены очки навыков")
            p["sp"] = raw["sp"]
            skills = raw["skills"]
            if not isinstance(skills, dict) or len(skills) > 40:
                raise ValueError("Повреждены навыки")
            for sid, rank in skills.items():
                if sid not in SKILLS or type(rank) is not int or not 0 <= rank <= SKILLS[sid]["max"]:
                    raise ValueError("Повреждены навыки")
            p["skills"] = dict(skills)
            quests = raw["quests"]
            if not isinstance(quests, dict) or len(quests) > 40:
                raise ValueError("Повреждены задания")
            for qid, st in quests.items():
                if (qid not in QUESTS or not isinstance(st, dict) or type(st.get("s")) is not int
                        or not 0 <= st["s"] <= 3 or type(st.get("n")) is not int or not 0 <= st["n"] <= 999):
                    raise ValueError("Повреждены задания")
            p["quests"] = {k: {"s": v["s"], "n": v["n"]} for k, v in quests.items()}
            seen = raw["seen"]
            if not isinstance(seen, list) or len(seen) > 20 or any(s not in KINDS for s in seen):
                raise ValueError("Повреждён бестиарий")
            p["seen"] = list(dict.fromkeys(seen))
        maxhp = int((80 + p["vit"] * 8 + sum(it.hp for it in p["equip"].values() if it)) * (1 + 0.06 * p["skills"].get("tough", 0)))
        p["hp"] = min(p["hp"], maxhp)
        fx, fy = direction(p["face_x"], p["face_y"])
        p["face_x"], p["face_y"] = fx, fy

        area = data["area"]
        if legacy:
            # The map changed in v33: keep the hero, regenerate the world.
            tail = str(area)[-1:]
            zone = 2 if area == "final" else int(tail) if tail in ("0", "1", "2") else 0
            camp = W.zone_camp(zone)
            p["x"], p["y"] = camp[0], camp[1] + 90
            p["return_x"], p["return_y"] = p["x"], p["y"]
            return p, "zone" + str(zone), {}
        raw_areas = data["areas"]
        if not isinstance(raw_areas, dict) or len(raw_areas) > 7:
            raise ValueError("Повреждён мир")
        if area not in VALID_AREAS or area not in raw_areas:
            raise ValueError("Неизвестная локация")
        areas = {}
        for key, value in raw_areas.items():
            if key not in VALID_AREAS or not isinstance(value, dict):
                raise ValueError("Повреждена локация")
            enemies, drops = value["enemies"], value["drops"]
            if not isinstance(enemies, list) or len(enemies) > 80:
                raise ValueError("Повреждены враги")
            if not isinstance(drops, list) or len(drops) > 2000:
                raise ValueError("Повреждена добыча")
            if type(value["reward"]) is not bool:
                raise ValueError("Повреждена награда")
            parsed = {"enemies": [Enemy.restore(e) for e in enemies], "drops": [], "reward": value["reward"]}
            zi = 2 if key == "final" else int(key[-1])
            for e in parsed["enemies"]:
                if e.zone != zi:
                    raise ValueError("Враг в неправильном регионе")
            for drop in drops:
                if not isinstance(drop, dict):
                    raise ValueError("Повреждена добыча")
                parsed["drops"].append({"x": number(drop["x"], 0, WW), "y": number(drop["y"], 0, WH),
                                        "item": Item.restore(drop["item"]), "age": 9.0})
            areas[key] = parsed
        return p, area, areas

    def read_save(self, path):
        if path.stat().st_size > 8_000_000:
            raise ValueError("Слишком большой файл")
        data = json.loads(path.read_text(encoding="utf8"))
        self.decode_save(data)
        return data

    def save_game(self, quiet=False):
        if self.mode == "abyss":
            if not quiet:
                self.notify("В Бездне сохранения отключены: забег идёт до смерти.", MUTED)
            return False
        if not self.session:
            return False
        p = dict(self.p)
        area = self.area
        if self.area_kind() != "zone":
            area = self.return_area
            p["x"], p["y"] = self.p["return_x"], self.p["return_y"]
        p["equip"] = {slot: asdict(item) if item else None for slot, item in self.p["equip"].items()}
        p["inv"] = [asdict(item) for item in self.p["inv"]]
        areas = {}
        for key, value in self.areas.items():
            if not key.startswith("zone"):
                continue
            areas[key] = {"enemies": [asdict(e) for e in value["enemies"] if e.hp > 0],
                          "drops": [{"x": d["x"], "y": d["y"], "item": asdict(d["item"])} for d in value["drops"]],
                          "reward": value["reward"]}
        data = {"version": VERSION, "player": p, "area": area, "areas": areas}
        main = C.slot_file(self.slot)
        tmp = Path(str(main) + ".tmp")
        backup = Path(str(main) + ".bak")
        try:
            self.decode_save(data)
            C.DATA.mkdir(parents=True, exist_ok=True)
            with tmp.open("w", encoding="utf8") as file:
                json.dump(data, file, ensure_ascii=False, indent=1, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            if main.exists() and (not quiet or self.time - self.last_backup > 120):
                try:
                    self.read_save(main)
                    backup_tmp = Path(str(backup) + ".tmp")
                    shutil.copy2(main, backup_tmp)
                    os.replace(backup_tmp, backup)
                    self.last_backup = self.time
                except (OSError, ValueError, TypeError, KeyError, OverflowError):
                    pass  # never replace a valid backup with a corrupted main save
            os.replace(tmp, main)
            if not quiet:
                self.notify("Игра сохранена.")
            return True
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as ex:
            self.notify("Ошибка сохранения: " + str(ex)[:100], RED)
            return False

    def save_candidates(self, slot):
        main = C.slot_file(slot)
        files = [main, Path(str(main) + ".bak")]
        if slot == 1:
            for legacy in C.legacy_saves():
                files += [legacy, Path(str(legacy) + ".bak")]
        return files

    def slot_info(self, slot):
        """Short summary of a save slot for the menu (None when empty or unreadable)."""
        for path in self.save_candidates(slot):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf8"))
                p = data["player"]
                return {"name": str(p.get("name", "?"))[:14], "level": int(p["level"]), "gold": int(p["gold"]),
                        "area": str(data.get("area", "zone0")), "time": int(p.get("playtime", 0) or 0),
                        "bosses": sum(1 for b in p.get("bosses", []) if b is True), "legacy": path.name.startswith("eldoria_v3") and "slot" not in path.name}
            except (OSError, ValueError, KeyError, TypeError):
                return {"name": "повреждено", "level": 0, "gold": 0, "area": "zone0", "time": 0, "bosses": 0, "legacy": False}
        return None

    def has_save(self):
        return any(self.slot_info(n) for n in range(1, C.SLOT_COUNT + 1))

    def load_game(self, slot=None):
        slot = slot or self.slot
        errors = []
        for path in self.save_candidates(slot):
            if not path.exists():
                continue
            try:
                data = self.read_save(path)
                p, area, areas = self.decode_save(data)
                self.p, self.area, self.areas = p, area, areas
                self.worlds, self.terrain_cache, self.mini_cache = {}, {}, {}
                self.mode, self.relics, self.scale_mul = "campaign", {}, 1.0
                self.return_area = self.area
                self.slot = slot
                self.build_worlds()
                self.ensure_area(self.area)
                self.reset_runtime()
                self.session = True
                self.confirm_new = False
                self.inv_page = 0
                self.autosave_time = 0
                self.pending_save = False
                self.set_state("dead" if p["hp"] <= 0 else "play")
                if p["complete"] and area == "final" and p["hp"] > 0:
                    self.set_state("victory")
                if data["version"] < 34:
                    self.notify("Старое сохранение перенесено: герой и прогресс сохранены, мир создан заново.")
                elif path.name.endswith(".bak"):
                    self.notify("Загружена резервная копия.")
                else:
                    self.notify("Сохранение загружено.")
                return True
            except (OSError, ValueError, TypeError, KeyError, OverflowError) as ex:
                errors.append(str(ex))
        self.notify("Сохранение повреждено: " + errors[-1][:90] if errors else "В этом слоте нет сохранения.", RED)
        return False
