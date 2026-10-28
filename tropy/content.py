"""Game data: enemies, bosses, skills, quests, NPCs, items, dungeons, story texts."""
import re

ENEMIES = {
    "slime": dict(name="Слизень", hp=34, dmg=7, speed=66, r=14, xp=11, res={"blunt": 0.8, "slash": 0.75, "pierce": 1.0, "magic": 1.4}),
    "slimelet": dict(name="Слизнёнок", hp=14, dmg=5, speed=84, r=9, xp=3, res={"blunt": 0.8, "slash": 0.9, "pierce": 1.0, "magic": 1.2}),
    "wolf": dict(name="Волк", hp=44, dmg=9, speed=112, r=14, xp=16, res={"blunt": 0.9, "slash": 1.3, "pierce": 1.0, "magic": 0.8}),
    "bat": dict(name="Тень-нетопырь", hp=24, dmg=7, speed=125, r=11, xp=13, res={"blunt": 0.9, "slash": 0.8, "pierce": 1.4, "magic": 1.0}),
    "spore": dict(name="Спороносец", hp=40, dmg=8, speed=55, r=15, xp=18, res={"blunt": 1.25, "slash": 1.3, "pierce": 1.0, "magic": 0.8}),
    "wisp": dict(name="Блуждающий огонёк", hp=28, dmg=8, speed=70, r=11, xp=17, res={"blunt": 0.3, "slash": 0.5, "pierce": 0.7, "magic": 1.5}),
    "golem": dict(name="Каменный голем", hp=105, dmg=14, speed=45, r=22, xp=25, res={"blunt": 1.5, "slash": 0.6, "pierce": 1.3, "magic": 1.0}),
    "archer": dict(name="Скелет-лучник", hp=38, dmg=9, speed=72, r=14, xp=20, res={"blunt": 1.4, "slash": 1.0, "pierce": 0.5, "magic": 1.35}),
    "ghost": dict(name="Призрак", hp=46, dmg=12, speed=65, r=14, xp=24, res={"blunt": 0.4, "slash": 0.6, "pierce": 0.6, "magic": 1.5}),
    "scarab": dict(name="Скарабей", hp=60, dmg=12, speed=80, r=15, xp=22, res={"blunt": 1.0, "slash": 0.7, "pierce": 1.4, "magic": 1.0}),
    "shaman": dict(name="Шаман Пустоты", hp=50, dmg=10, speed=60, r=14, xp=26, res={"blunt": 1.0, "slash": 1.3, "pierce": 1.2, "magic": 0.5}),
    "imp": dict(name="Огненный бес", hp=44, dmg=11, speed=118, r=13, xp=24, res={"blunt": 1.0, "slash": 1.3, "pierce": 1.0, "magic": 0.6}),
    "magma": dict(name="Магма-слизень", hp=70, dmg=11, speed=60, r=17, xp=22, res={"blunt": 1.3, "slash": 0.8, "pierce": 1.3, "magic": 0.7}),
    "cultist": dict(name="Адепт Пустоты", hp=62, dmg=14, speed=62, r=14, xp=30, res={"blunt": 1.0, "slash": 1.3, "pierce": 0.9, "magic": 0.6}),
    "miniboss": dict(name="Страж подземелья", hp=420, dmg=16, speed=75, r=30, xp=0, res={"slash": 1.0, "pierce": 1.0, "magic": 1.0}),
    "boss": dict(name="Хранитель", hp=1150, dmg=19, speed=95, r=36, xp=0, res={}),
    "finalboss": dict(name="Сердце Пустоты", hp=4000, dmg=29, speed=105, r=46, xp=0, res={}),
}
ENEMY_ORDER = ["slime", "wolf", "bat", "spore", "wisp", "golem", "archer", "ghost", "scarab", "shaman", "imp", "magma", "cultist"]
REGULAR = set(ENEMY_ORDER) | {"slimelet"}

BOSSES = [
    {"name": "Корень-исполин", "title": "Страж Изумрудного леса",
     "sprite": "boss_forest", "color": (112, 197, 85),
     "res": {"slash": 1.25, "pierce": 0.9, "magic": 0.85, "blunt": 0.9}},
    {"name": "Страж руин", "title": "Последний хранитель печати",
     "sprite": "boss_ruins", "color": (153, 180, 212),
     "res": {"slash": 0.8, "pierce": 1.3, "magic": 1.0, "blunt": 1.4}},
    {"name": "Пепельный разоритель", "title": "Пожиратель пустошей",
     "sprite": "boss_ash", "color": (247, 116, 67),
     "res": {"slash": 0.9, "pierce": 0.9, "magic": 1.3, "blunt": 1.0}},
    {"name": "Сердце Пустоты", "title": "Последняя печать",
     "sprite": "enemy_finalboss", "color": (190, 100, 255),
     "res": {"slash": 1.0, "pierce": 1.0, "magic": 1.0}},
]

SPAWN = [
    {"slime": 30, "wolf": 24, "bat": 18, "spore": 16, "wisp": 12},
    {"golem": 16, "archer": 22, "ghost": 18, "scarab": 18, "wisp": 12, "bat": 14},
    {"shaman": 16, "imp": 22, "magma": 18, "cultist": 16, "golem": 14, "archer": 14},
]
ZONE_ENEMY_CAP = 18
PACKS = {"wolf": 3, "bat": 3, "slime": 2, "wisp": 2, "imp": 2, "scarab": 2}

# boss pattern scripts: key (0-2 zone bosses, 3 final, 4-6 dungeon guardians) -> phase -> patterns
BOSS_SCRIPTS = {
    0: {1: ["fan", "ring", "leap", "summon", "slam"], 2: ["spiral", "rain", "charge", "leap", "ring", "fan"]},
    1: {1: ["laser", "fan", "slam", "charge", "ring"], 2: ["laser", "spiral", "summon", "leap", "rain", "charge"]},
    2: {1: ["slam", "fan", "spiral", "leap", "rain"], 2: ["spiral", "laser", "summon", "charge", "slam", "rain", "ring"]},
    3: {1: ["ring", "laser", "fan", "leap", "slam"], 2: ["spiral", "rain", "laser", "summon", "charge", "leap", "ring", "fan"]},
    4: {1: ["fan", "charge", "slam"], 2: ["ring", "charge", "leap", "fan"]},
    5: {1: ["laser", "fan", "slam"], 2: ["ring", "laser", "leap", "charge"]},
    6: {1: ["slam", "spiral", "fan"], 2: ["spiral", "leap", "laser", "ring"]},
}
PATTERNS = {"ring", "fan", "spiral", "rain", "slam", "laser", "summon", "charge", "leap"}
PATTERN_NAMES = {"ring": "КОЛЬЦО СНАРЯДОВ", "fan": "ВЕЕР", "spiral": "СПИРАЛЬ", "rain": "ДОЖДЬ", "slam": "УДАР ПО ЗЕМЛЕ",
                 "laser": "ЛУЧИ", "summon": "ПРИЗЫВ", "charge": "РЫВОК", "leap": "ПРЫЖОК"}
BOSS_SUMMON = {0: ["slime", "wolf", "wisp"], 1: ["archer", "ghost", "scarab"], 2: ["imp", "shaman", "cultist"],
               3: ["cultist", "shaman", "imp"], 4: ["slime", "wolf"], 5: ["archer", "ghost"], 6: ["imp", "magma"]}

BRANCHES = ["Воин", "Страж", "Чародей"]
SKILLS = {
    "might": dict(name="Мощь", desc="+6% урона за ранг", max=3, branch=0, row=0, req=None),
    "crit": dict(name="Меткость", desc="+4% шанса крита за ранг", max=3, branch=0, row=1, req=("might", 1)),
    "vamp": dict(name="Жажда крови", desc="Лечит 2% нанесённого урона за ранг", max=3, branch=0, row=2, req=("crit", 1)),
    "cry": dict(name="Боевой клич [1]", desc="7 с: урон +35%, скорость +20%. Перезарядка 20 с", max=1, branch=0, row=3, req=("might", 2), cost=2, key=1, cd=20),
    "tough": dict(name="Закалка", desc="+6% здоровья за ранг", max=3, branch=1, row=0, req=None),
    "armor": dict(name="Стойкость", desc="+2 защиты за ранг", max=3, branch=1, row=1, req=("tough", 1)),
    "regen": dict(name="Живучесть", desc="+0,7 HP/с за ранг", max=3, branch=1, row=2, req=("armor", 1)),
    "shield": dict(name="Щит света [2]", desc="Поглощает 90 урона 8 с. Перезарядка 22 с", max=1, branch=1, row=3, req=("tough", 2), cost=2, key=2, cd=22),
    "focus": dict(name="Сосредоточенность", desc="-7% перезарядок за ранг", max=3, branch=2, row=0, req=None),
    "wisdom": dict(name="Мудрость", desc="+8% опыта за ранг", max=3, branch=2, row=1, req=("focus", 1)),
    "elixir": dict(name="Эликсир", desc="+12% лечения зелий за ранг", max=3, branch=2, row=2, req=("wisdom", 1)),
    "chain": dict(name="Цепная молния [3]", desc="Бьёт до 5 врагов магией. Перезарядка 9 с", max=1, branch=2, row=3, req=("focus", 2), cost=2, key=3, cd=9),
    "meteor": dict(name="Метеор [4]", desc="Падает на ближайшего врага. Перезарядка 16 с", max=1, branch=2, row=4, req=("chain", 1), cost=2, key=4, cd=16),
}
ACTIVE_KEYS = {s["key"]: sid for sid, s in SKILLS.items() if "key" in s}

NPCS = {
    "elder": dict(name="Старейшина Орен", role="Хранитель лагеря", zone=0),
    "hunter": dict(name="Охотница Тея", role="Следопыт", zone=0),
    "liara": dict(name="Странница Лиара", role="Чародейка", zone=1),
    "valdo": dict(name="Археолог Вальдо", role="Исследователь руин", zone=1),
    "kael": dict(name="Страж Каэл", role="Последний из дозора", zone=2),
    "rud": dict(name="Отшельник Руд", role="Пепельный мудрец", zone=2),
    "smith": dict(name="Кузнец Харальд", role="Кузнец", zone=-1),
    "merchant": dict(name="Торговец Бруно", role="Торговец", zone=-1),
}
NPC_IDLE = {
    "elder": ["Печати слабеют. Береги себя, путник.", "Лагерь защищён рунами. Здесь можно отдышаться."],
    "hunter": ["В лесу стало слишком шумно. Это не к добру.", "Волки теперь охотятся стаями."],
    "liara": ["Руины помнят старую магию. Не доверяй теням.", "Посох хорош против костей, но не против шаманов."],
    "valdo": ["Здесь под каждым камнем история!", "Фрагменты рун... они ещё где-то в этих залах."],
    "kael": ["Пустоши горят уже много лет.", "Сердце Пустоты — на севере. Иди осторожно."],
    "rud": ["Пепел шепчет тому, кто слушает.", "Угли падшей звезды ещё тлеют."],
    "smith": ["Хорошая сталь не знает усталости."],
    "merchant": ["Лучшие цены на этой стороне Эльдории!"],
}

# kind: kill(target=enemy kind) | boss(target=boss index) | collect(zone)
QUESTS = {
    "q_slime": dict(giver="elder", title="Слизь у лагеря", kind="kill", target="slime", n=6,
        text="Слизни подбираются к палаткам. Одолей шестерых, и я смогу спать спокойно.",
        done="Спасибо. Возьми награду.", reward=dict(gold=40, xp=70, potions=1)),
    "q_seal0": dict(giver="elder", title="Печать леса", kind="boss", target=0, n=1, after="q_slime",
        text="Корень-исполин держит первую печать, но тьма его искажает. Победи его, и врата на север откроются.",
        done="Лес вздохнул свободнее. Ты настоящий герой.", reward=dict(gold=100, xp=150, sp=1)),
    "q_wolf": dict(giver="hunter", title="Волчьи стаи", kind="kill", target="wolf", n=5,
        text="Стаи рвут мои ловушки. Убей пятерых волков, лучше рубящим оружием: их шкура мягка.",
        done="Отличная работа! Это тебе пригодится.", reward=dict(gold=50, xp=80, item=2)),
    "q_bat": dict(giver="hunter", title="Тени в чаще", kind="kill", target="bat", n=6, after="q_wolf",
        text="Нетопыри пикируют из темноты. Копьём бить их удобнее всего. Одолей шестерых.",
        done="Теперь тропы чище. Вот зелья.", reward=dict(xp=100, potions=2, gold=40)),
    "q_golem": dict(giver="liara", title="Каменные стражи", kind="kill", target="golem", n=4, boss_req=0,
        text="Големы сторожат залы. Их камень боится колющих ударов и магии. Разбей четырёх.",
        done="Магия камня ослабла. Награда твоя.", reward=dict(gold=90, xp=140, item=2)),
    "q_seal1": dict(giver="liara", title="Печать руин", kind="boss", target=1, n=1, after="q_golem",
        text="Страж руин охраняет вторую печать. Копьё пробивает его броню лучше всего.",
        done="Печать пала. Держи.", reward=dict(gold=150, xp=220, sp=1)),
    "q_archer": dict(giver="valdo", title="Костяные стрелки", kind="kill", target="archer", n=6, boss_req=0,
        text="Скелеты-лучники простреливают все проходы. Магия разрушает их кости. Одолей шестерых.",
        done="Теперь можно работать спокойно!", reward=dict(gold=80, xp=120)),
    "q_relic": dict(giver="valdo", title="Фрагменты рун", kind="collect", target="Фрагмент руны", n=3, zone=1, chance=0.35, after="q_archer",
        text="Мне нужны три фрагмента рун. Их иногда роняют скелеты и големы.",
        done="Потрясающе! Это мощная реликвия.", reward=dict(gold=100, xp=180, sp=1, item=3)),
    "q_shaman": dict(giver="kael", title="Шаманы Пустоты", kind="kill", target="shaman", n=5, boss_req=1,
        text="Шаманы выпускают наводящиеся шары. Рубящее оружие их ранит лучше всего. Одолей пятерых.",
        done="Дозор благодарит тебя.", reward=dict(gold=120, xp=200, item=2)),
    "q_seal2": dict(giver="kael", title="Печать пустошей", kind="boss", target=2, n=1, after="q_shaman",
        text="Пепельный разоритель сжёг мой дозор. Магия бьёт его лучше всего.",
        done="Последняя печать пала. Дорога к Сердцу открыта.", reward=dict(gold=200, xp=300, sp=1)),
    "q_final": dict(giver="kael", title="Сердце Пустоты", kind="boss", target=3, n=1, after="q_seal2",
        text="Портал на севере ведёт к самому Сердцу Пустоты. Уничтожь его.",
        done="Эльдория спасена. Ты стал легендой.", reward=dict(gold=300, xp=400)),
    "q_ember": dict(giver="rud", title="Угли падшей звезды", kind="collect", target="Уголь звезды", n=4, zone=2, chance=0.3, boss_req=1,
        text="Мне нужны четыре тлеющих угля. Их находят в телах пепельных тварей.",
        done="Тепло звезды в твоих руках.", reward=dict(gold=150, xp=250, sp=1, item=3)),
}

QUESTS.update({
    "q_spore": dict(giver="hunter", title="Грибная напасть", kind="kill", target="spore", n=5, after="q_wolf",
        text="Споры спороносцев отравляют траву. Бей их рубящим оружием и не стой в облаках.",
        done="Лес дышит чище. Держи награду.", reward=dict(gold=60, xp=100, item=2)),
    "q_wisp": dict(giver="elder", title="Блуждающие огни", kind="kill", target="wisp", n=5, after="q_slime",
        text="Над поляной кружат огоньки. Физическое оружие их почти не берёт — используй магию.",
        done="Огни погасли. Спасибо!", reward=dict(gold=70, xp=110, potions=2)),
    "q_dg0": dict(giver="hunter", title="Подземелья леса", kind="dungeon", target=0, n=2, after="q_bat",
        text="Под корнями и в грибных гротах прячется добыча. Пройди оба подземелья региона.",
        done="Ты настоящий спелеолог!", reward=dict(gold=140, xp=200, sp=1, item=3)),
    "q_ghost": dict(giver="liara", title="Тени руин", kind="kill", target="ghost", n=5, boss_req=0,
        text="Призраки скользят сквозь сталь. Бей их магией и не стой там, где вспыхивает круг.",
        done="Руины стали тише.", reward=dict(gold=100, xp=160, item=2)),
    "q_scarab": dict(giver="valdo", title="Скарабеи под плитами", kind="kill", target="scarab", n=5, boss_req=0,
        text="Скарабеи подкапываются под раскопки. Копьё пробивает их панцирь лучше всего.",
        done="Раскопки спасены!", reward=dict(gold=90, xp=150, potions=2)),
    "q_dg1": dict(giver="valdo", title="Подземелья руин", kind="dungeon", target=1, n=2, after="q_archer",
        text="Катакомбы и Зал зеркал хранят древние артефакты. Принеси их.",
        done="Бесценные находки!", reward=dict(gold=200, xp=300, sp=1, item=3)),
    "q_imp": dict(giver="kael", title="Огненные бесы", kind="kill", target="imp", n=6, boss_req=1,
        text="Бесы оставляют за собой огонь. Бей их рубящим оружием и не стой в пламени.",
        done="Дозор благодарит тебя.", reward=dict(gold=140, xp=240, item=2)),
    "q_cultist": dict(giver="rud", title="Адепты Пустоты", kind="kill", target="cultist", n=4, boss_req=1, after="q_ember",
        text="Адепты призывают лучи из пустоты. Разбей четверых, пока их не стало больше.",
        done="Пустота отступила.", reward=dict(gold=160, xp=280, sp=1)),
    "q_dg2": dict(giver="kael", title="Подземелья пустошей", kind="dungeon", target=2, n=2, after="q_shaman",
        text="Шахты пепла и вулканическое святилище кишат тварями. Очисти оба.",
        done="Ты — легенда пустошей.", reward=dict(gold=300, xp=450, sp=2, item=4)),
})

INTRO = [
    dict(scene="stars", text="Эльдория жила в мире, пока три хранителя удерживали печати, запиравшие Пустоту."),
    dict(scene="blood", text="Но в ночь, когда небо стало багровым, печати начали гаснуть. Леса умолкли, руины ожили, а пустоши загорелись."),
    dict(scene="village", text="Старейшина Орен созвал последних смельчаков. Откликнул<ся|ась> только {name}."),
    dict(scene="hero", text="«Ты слаб<|а>, но упрям<|а>, и это больше, чем у многих, — сказал он. — Найди хранителей, сломай печати и уничтожь Сердце Пустоты»."),
    dict(scene="forest", text="Путь {name_g} начинается у лагеря на краю Изумрудного леса."),
]
OUTRO = [
    dict(scene="dawn", text="Сердце Пустоты рассыпалось пеплом, и над пустошами впервые за долгие годы взошло солнце."),
    dict(scene="village", text="В лагере зажглись огни. Люди пели о том, кто вернул рассвет: {name}."),
    dict(scene="hero", text="Но Эльдория велика, и в её уголках ещё много тайн. Путь {name_g} не окончен — впереди Бездна."),
]
TIPS = [
    "Рывок (SHIFT) даёт неуязвимость. Используйте его против снарядов.",
    "У каждого врага есть слабость к типу оружия. Смотрите подсказку над врагом.",
    "Очки навыков тратятся на клавише K.",
    "Редкие предметы светятся и обозначаются лучом света.",
]


# ------------------------------------------------------------ characters
CHARACTERS = [
    dict(id=0, name="Эйрик", cls="Рыцарь", gender="m", weapon="sword", stats=(6, 7, 4),
         forms=("Эйрик", "Эйрика", "Эйрику", "Эйрика", "Эйриком", "Эйрике"),
         perk="Несгибаемый", perk_text="-10% получаемого урона", skill=("tough", 1),
         item=dict(name="Кольчуга новичка", slot="armor", armor=3, hp=12),
         desc="Крепкий воин. Меч бьёт быстро и по площади."),
    dict(id=1, name="Лира", cls="Следопыт", gender="f", weapon="spear", stats=(5, 4, 8),
         forms=("Лира", "Лиры", "Лире", "Лиру", "Лирой", "Лире"),
         perk="Меткий глаз", perk_text="+8% шанса крита и +10% скорости", skill=("crit", 1),
         item=dict(name="Талисман охотницы", slot="amulet", crit=4, power=1),
         desc="Быстрая и точная. Копьё достаёт издалека."),
    dict(id=2, name="Альдрик", cls="Чародей", gender="m", weapon="staff", stats=(4, 4, 6),
         forms=("Альдрик", "Альдрика", "Альдрику", "Альдрика", "Альдриком", "Альдрике"),
         perk="Поток силы", perk_text="-15% перезарядок, снаряды +15% урона", skill=("focus", 1),
         item=dict(name="Кристалл мага", slot="amulet", power=2, hp=8),
         desc="Хрупкий, но смертоносный. Посох бьёт издалека магией."),
]


def legacy_char(name, gender="m"):
    base = dict(CHARACTERS[0])
    base["name"], base["gender"] = name, gender
    base["forms"] = (name,) * 6
    return base


def fmt(text, ch):
    f = ch["forms"]
    keys = {"name": f[0], "name_g": f[1], "name_d": f[2], "name_a": f[3], "name_i": f[4], "name_p": f[5]}
    g = 1 if ch["gender"] == "m" else 2
    text = re.sub(r"\{(name(?:_[gdaip])?)\}", lambda m: keys[m.group(1)], text)
    return re.sub(r"<([^|<>]*)\|([^|<>]*)>", lambda m: m.group(g), text)


# ------------------------------------------------------------------ mods
MODS = {
    "burn": ("Поджог", "Удары поджигают врага"),
    "frost": ("Холод", "Удары замедляют врага"),
    "chain": ("Искра", "Крит бьёт молнией по врагам рядом"),
    "lifesteal": ("Вампиризм", "3% урона лечит вас"),
    "dashblast": ("Рывок-взрыв", "Рывок создаёт ударную волну"),
    "killheal": ("Жатва", "+4 здоровья за убийство"),
    "gold": ("Золотая жила", "+25% золота"),
    "xp": ("Мудрость веков", "+15% опыта"),
    "thorns": ("Шипы", "Удар по вам ранит врагов рядом"),
    "echo": ("Эхо", "15% шанс удвоить удар"),
    "swift": ("Лёгкие ноги", "+8% скорости"),
    "sharp": ("Острота", "+6% шанса крита"),
    "might": ("Сила", "+10% урона"),
    "vital": ("Жизнь", "+10% здоровья"),
    "blast": ("Взрывная смерть", "Убитые враги взрываются"),
    "ghosty": ("Призрачность", "8% шанс избежать урона"),
    "orbit": ("Орбиты", "Вас защищают вращающиеся сферы"),
    "potion": ("Эликсиры", "+30% лечения зелий"),
    "magnet": ("Магнит", "Добыча сама летит к вам"),
    "fortune": ("Удача", "Лучшая добыча и больше предметов"),
    "heavy": ("Тяжёлый удар", "Каждый 5-й удар наносит 2,5× урона"),
    "rage": ("Ярость", "Чем меньше здоровья, тем больше урон"),
    "regen": ("Регенерация", "+0,8 здоровья в секунду"),
    "guard": ("Блок", "15% шанс уменьшить урон вдвое"),
    "chill": ("Аура холода", "Враги рядом с вами замедлены"),
    "twin": ("Близнецы", "Удары достают на одну цель больше"),
    "roomheal": ("Исцеление комнат", "Зачистка комнаты лечит 15%"),
    "second": ("Второе дыхание", "Раз за область переживает смертельный удар"),
}
MOD_POOL = {
    "weapon": ["burn", "frost", "chain", "lifesteal", "echo", "might", "sharp", "blast", "orbit", "heavy", "twin", "rage"],
    "armor": ["thorns", "ghosty", "vital", "killheal", "potion", "swift", "dashblast", "frost", "guard", "second", "regen", "chill", "roomheal"],
    "amulet": list(MODS),
}
UNIQUES = {
    "dg0_0": dict(name="Клык корневого зверя", slot="weapon", weapon="spear", power=14, crit=6, mods=["burn", "lifesteal"], tier=0),
    "dg0_1": dict(name="Грибная корона", slot="amulet", power=3, crit=4, hp=40, mods=["potion", "orbit"], tier=0),
    "dg1_0": dict(name="Саван катакомб", slot="armor", armor=12, hp=40, mods=["ghosty", "thorns"], tier=1),
    "dg1_1": dict(name="Зеркальный клинок", slot="weapon", weapon="sword", power=22, crit=9, mods=["chain", "echo"], tier=1),
    "dg2_0": dict(name="Шахтёрский жезл", slot="weapon", weapon="staff", power=24, crit=8, mods=["burn", "blast"], tier=2),
    "dg2_1": dict(name="Сердце вулкана", slot="amulet", power=8, crit=6, hp=70, mods=["dashblast", "might"], tier=2),
    "boss0": dict(name="Сердце древнего леса", slot="amulet", power=5, crit=5, hp=50, mods=["vital", "killheal"], tier=0),
    "boss1": dict(name="Печать последнего стража", slot="armor", armor=14, hp=45, mods=["thorns", "vital"], tier=1),
    "boss2": dict(name="Осколок пепельной звезды", slot="weapon", weapon="sword", power=26, crit=10, mods=["burn", "might", "sharp"], tier=2),
}
DUNGEONS = {
    "dg0_0": dict(zone=0, name="Корневая пещера", seed=11, kinds=["combat", "combat", "trap", "combat", "miniboss"], mini="Хозяин корней"),
    "dg0_1": dict(zone=0, name="Грибной грот", seed=12, kinds=["combat", "trap", "combat", "combat", "combat", "miniboss"], mini="Королева спор"),
    "dg1_0": dict(zone=1, name="Катакомбы", seed=21, kinds=["combat", "combat", "trap", "combat", "combat", "miniboss"], mini="Костяной король"),
    "dg1_1": dict(zone=1, name="Зал зеркал", seed=22, kinds=["combat", "trap", "combat", "trap", "combat", "miniboss"], mini="Хранитель отражений"),
    "dg2_0": dict(zone=2, name="Шахты пепла", seed=31, kinds=["combat", "combat", "trap", "combat", "combat", "combat", "miniboss"], mini="Горный пожиратель"),
    "dg2_1": dict(zone=2, name="Вулканическое святилище", seed=32, kinds=["combat", "trap", "combat", "combat", "trap", "combat", "miniboss"], mini="Жрец магмы"),
}
DUNGEON_IDS = list(DUNGEONS)
PASSES = [
    dict(name="Корневой спуск", seed=41, style="cave", kinds=["combat", "combat", "combat"],
         desc="Тропа уходит под корни древнего леса."),
    dict(name="Обрушенный мост", seed=42, style="bridge", kinds=["combat", "combat", "combat"],
         desc="Старый мост рушится под ногами. Спеши!"),
]

# per-zone layouts (world is 3200 x 2200)
ZONE_LAYOUT = [
    dict(camp=(1600, 1100), arena=(1600, 390), gate_next=(1600, 170), gate_back=None, field=(770, 1400),
         dungeons=[(420, 1840), (2800, 1250)], chests=[(420, 380), (2760, 420), (1500, 1950)]),
    dict(camp=(950, 1150), arena=(2450, 780), gate_next=(2850, 1900), gate_back=(330, 330), field=(1750, 1700),
         dungeons=[(480, 1850), (1650, 430)], chests=[(2800, 300), (2050, 1150), (400, 1050)]),
    dict(camp=(2200, 1500), arena=(1500, 540), gate_next=(1500, 170), gate_back=(380, 1900), field=(800, 920),
         dungeons=[(2850, 400), (400, 1350)], chests=[(1100, 1750), (2800, 1000), (700, 360)]),
]

# ---------------------------------------------------------------- abyss
ABYSS_BOONS_PER_FLOOR = 1
META = {
    "hp": ("Крепость духа", "+5% здоровья за ранг", 10, 12),
    "dmg": ("Клинок Бездны", "+4% урона за ранг", 10, 14),
    "gold": ("Жила душ", "+10% золота за ранг", 8, 10),
    "relic": ("Дар предков", "Старт с реликвиями (по рангу)", 3, 40),
    "potion": ("Запас зелий", "+1 зелье на старте за ранг", 4, 20),
}

ARENA_KILLS = 8
