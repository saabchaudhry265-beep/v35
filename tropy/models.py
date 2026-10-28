"""Save-aware data classes."""
from dataclasses import dataclass, field

from .common import RARITIES, SLOTS, WEAPONS, WW, WH, number
from .content import ENEMIES, MODS, PATTERNS

KINDS = set(ENEMIES)


@dataclass
class Item:
    name: str
    slot: str
    rarity: int
    power: int = 0
    armor: int = 0
    crit: int = 0
    hp: int = 0
    weapon: str = "sword"
    unique: bool = False
    tier: int = 0
    plus: int = 0
    mods: list = field(default_factory=list)

    @property
    def color(self):
        return RARITIES[self.rarity][1]

    @property
    def price(self):
        return 8 + self.rarity * 8 + self.power + self.armor + self.hp // 3 + self.plus * 12

    @property
    def title(self):
        return self.name + (" +" + str(self.plus) if self.plus else "")

    @classmethod
    def restore(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Повреждён предмет")
        item = cls(**data)
        if not isinstance(item.name, str) or len(item.name) > 150:
            raise ValueError("Некорректное имя предмета")
        if item.slot not in SLOTS or item.weapon not in WEAPONS:
            raise ValueError("Некорректный тип предмета")
        if type(item.rarity) is not int or not 0 <= item.rarity < 5:
            raise ValueError("Некорректная редкость")
        for key in ("power", "armor", "crit", "hp"):
            number(getattr(item, key), 0, 10000)
        if type(item.unique) is not bool:
            raise ValueError("Некорректный признак предмета")
        if type(item.tier) is not int or not 0 <= item.tier <= 2:
            raise ValueError("Некорректный тир")
        if type(item.plus) is not int or not 0 <= item.plus <= 5:
            raise ValueError("Некорректное улучшение")
        if not isinstance(item.mods, list) or len(item.mods) > 3 or any(x not in MODS for x in item.mods):
            raise ValueError("Некорректные свойства")
        return item


@dataclass(eq=False)  # identity comparison: faster and avoids removing the wrong twin enemy
class Enemy:
    x: float
    y: float
    kind: str
    zone: int
    hp: float
    maxhp: float
    damage: float
    speed: float
    radius: float
    home_x: float
    home_y: float
    cd: float = 0.8
    wind: float = 0.0
    attack: str = ""
    ax: float = 0.0
    ay: float = 1.0
    dash: float = 0.0
    flash: float = 0.0
    phase: int = 1
    side: int = 1
    kx: float = 0.0
    ky: float = 0.0
    combo: int = 0
    pat: str = ""
    pt: float = 0.0
    pi: float = 0.0
    bp: int = 0
    ba: float = 0.0
    wmax: float = 0.0
    burn: float = 0.0
    slow: float = 0.0
    tag: str = ""
    awake: int = 0
    room: int = -1
    tx: float = 0.0
    ty: float = 0.0
    elite: str = ""

    @classmethod
    def restore(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Повреждён враг")
        e = cls(**data)
        if e.kind not in KINDS or type(e.zone) is not int or not 0 <= e.zone < 3:
            raise ValueError("Неизвестный враг")
        for key in ("x", "home_x"):
            number(getattr(e, key), 0, WW)
        for key in ("y", "home_y"):
            number(getattr(e, key), 0, WH)
        number(e.maxhp, 1, 100000)
        number(e.hp, 0.001, e.maxhp)
        number(e.damage, 0, 10000)
        number(e.speed, 1, 1000)
        number(e.radius, 1, 100)
        for key in ("cd", "wind", "dash", "flash"):
            number(getattr(e, key), 0, 100)
        for key in ("pt", "pi"):
            number(getattr(e, key), -200, 100)
        for key in ("ax", "ay"):
            number(getattr(e, key), -1.01, 1.01)
        for key in ("kx", "ky"):
            number(getattr(e, key), -5000, 5000)
        number(e.ba, -1000, 1000)
        for key in ("wmax", "burn", "slow"):
            number(getattr(e, key), 0, 100)
        number(e.tx, -10000, 10000)
        number(e.ty, -10000, 10000)
        if e.elite not in ("", "fast", "armored", "vampiric", "explosive"):
            raise ValueError("Повреждён элитный признак")
        if not isinstance(e.tag, str) or len(e.tag) > 40 or type(e.awake) is not int or type(e.room) is not int:
            raise ValueError("Повреждён враг")
        if e.phase not in (1, 2, 3) or e.side not in (-1, 1):
            raise ValueError("Повреждено состояние врага")
        if e.attack not in ("", "charge", "cast", "hop", "burrow", "blink", "transform", "leap") or (e.pat and e.pat not in PATTERNS):
            raise ValueError("Повреждена атака")
        if type(e.combo) is not int or type(e.bp) is not int:
            raise ValueError("Повреждён счётчик")
        # Active attacks are cancelled on load; the next one gets a fresh warning.
        e.wind = e.dash = e.flash = e.pt = e.pi = 0
        e.kx = e.ky = 0.0
        e.attack = ""
        e.pat = ""
        e.combo = 0
        e.wmax = e.burn = e.slow = 0.0
        e.awake = 0
        e.room = -1
        e.tx = e.ty = 0.0
        e.cd = max(0.8, e.cd)
        return e
