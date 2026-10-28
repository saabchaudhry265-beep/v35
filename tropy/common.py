"""Constants, paths and small helpers shared by every module."""
import math
import os
import sys
from pathlib import Path

VERSION = 35
VW, VH = 1000, 700
WW, WH = 3200, 2200
CAMP = (WW / 2, WH / 2)
CELL = 40
CAMP_R = 175
RESOLUTIONS = [(800, 600), (1000, 700), (1280, 800), (1600, 900)]
BASE = Path(__file__).resolve().parent.parent
ASSETS = Path(getattr(sys, "_MEIPASS", BASE)) / "assets"

if os.name == "nt":
    DATA = Path(os.getenv("APPDATA") or Path.home()) / "TropyEldorii"
else:
    DATA = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local/share")
    DATA /= "TropyEldorii"
SLOT_COUNT = 3
SETTINGS_FILE = DATA / "settings_v35.json"
PROFILE_FILE = DATA / "profile_v35.json"
LOG_FILE = DATA / "game.log"


def slot_file(n):
    return DATA / "eldoria_v35_slot{}.json".format(n)


def legacy_saves():
    return [DATA / "eldoria_v34.json", DATA / "eldoria_v33.json", DATA / "eldoria_v32.json"]

BG = (17, 23, 34)
PANEL = (25, 34, 49)
TEXT = (230, 236, 246)
MUTED = (155, 174, 199)
GOLD = (255, 211, 114)
GREEN = (113, 225, 155)
RED = (255, 123, 126)
BLUE = (126, 192, 255)
PURPLE = (203, 133, 255)

ZONES = [
    {"name": "Изумрудный лес", "level": 1, "biome": "forest", "scale": 1.0,
     "floor": (32, 53, 44), "tile": (37, 59, 48), "prop": (76, 126, 64),
     "boss": "Корень-исполин", "boss_color": (112, 197, 85),
     "relic": "Сердце древнего леса"},
    {"name": "Забытые руины", "level": 3, "biome": "ruins", "scale": 1.45,
     "floor": (44, 44, 52), "tile": (51, 51, 60), "prop": (119, 119, 137),
     "boss": "Страж руин", "boss_color": (153, 180, 212),
     "relic": "Печать последнего стража"},
    {"name": "Пепельные пустоши", "level": 5, "biome": "ash", "scale": 1.95,
     "floor": (59, 37, 34), "tile": (69, 43, 36), "prop": (143, 77, 57),
     "boss": "Пепельный разоритель", "boss_color": (247, 116, 67),
     "relic": "Осколок пепельной звезды"},
]
RARITIES = [
    ("Обычный", (194, 199, 207), 1.0),
    ("Необычный", (103, 215, 140), 1.2),
    ("Редкий", (102, 171, 255), 1.5),
    ("Эпический", (204, 123, 255), 1.85),
    ("Легендарный", (255, 199, 83), 2.25),
]
SLOTS = {"weapon": "Оружие", "armor": "Броня", "amulet": "Амулет"}
WEAPONS = {"sword": "Меч", "spear": "Копьё", "staff": "Посох", "hammer": "Молот", "bow": "Лук"}
DTYPES = {"sword": "slash", "spear": "pierce", "staff": "magic", "hammer": "blunt", "bow": "pierce"}
DTYPE_NAMES = {"slash": "рубящий", "pierce": "колющий", "magic": "магия", "blunt": "дробящий"}
DTYPE_SHORT = {"slash": "Руб.", "pierce": "Кол.", "magic": "Маг."}
STATES = {
    "menu", "creator", "sanctum", "boon", "cutscene", "slots", "records", "credits", "play", "pause", "inventory", "stats",
    "journal", "map", "settings", "help", "shop", "smith", "dialog",
    "skills", "dead", "victory",
}


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t, 0, 1)
    return 1 - (1 - t) ** 3


def distance(x, y, xx, yy):
    return math.hypot(x - xx, y - yy)


def direction(dx, dy):
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length else (0.0, 1.0)


def segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = clamp(((px - ax) * dx + (py - ay) * dy) / length, 0, 1) if length else 0
    return distance(px, py, ax + t * dx, ay + t * dy)


def number(value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Ожидалось число")
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError("Число вне допустимого диапазона")
    return value


def rgb(color, factor=1.0, add=0):
    return tuple(int(clamp(c * factor + add, 0, 255)) for c in color[:3])
