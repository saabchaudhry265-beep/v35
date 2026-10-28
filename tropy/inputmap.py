"""Key bindings and gamepad mapping."""
import pygame

# action -> (label, default key). Arrow keys always work as an alternative for movement.
ACTIONS = [
    ("up", "Вверх", pygame.K_w), ("down", "Вниз", pygame.K_s), ("left", "Влево", pygame.K_a), ("right", "Вправо", pygame.K_d),
    ("attack", "Атака", pygame.K_SPACE), ("skill", "Навык оружия", pygame.K_r), ("pulse", "Импульс", pygame.K_q),
    ("dash", "Рывок", pygame.K_LSHIFT), ("potion", "Зелье", pygame.K_h), ("interact", "Действие", pygame.K_e),
    ("inventory", "Сумка", pygame.K_i), ("stats", "Герой", pygame.K_c), ("skills", "Навыки", pygame.K_k),
    ("journal", "Журнал", pygame.K_j), ("map", "Карта", pygame.K_m),
]
DEFAULT_KEYS = {a: k for a, _, k in ACTIONS}
LABELS = {a: label for a, label, _ in ACTIONS}


def key_label(code):
    try:
        name = pygame.key.name(code)
    except (pygame.error, TypeError, ValueError):
        name = str(code)
    return str(name).upper()


def clean_keys(raw):
    """Validate a saved binding table; unknown or duplicate entries fall back to defaults."""
    keys = dict(DEFAULT_KEYS)
    if isinstance(raw, dict):
        for action, code in raw.items():
            if action in keys and type(code) is int and 8 <= code <= 1 << 30:
                keys[action] = code
    if len(set(keys.values())) != len(keys):
        return dict(DEFAULT_KEYS)
    return keys


# Xbox-style layout as reported by SDL: A=0 B=1 X=2 Y=3 LB=4 RB=5 Back=6 Start=7
PAD_BUTTONS = {0: "interact", 1: "dash", 2: "attack", 3: "potion", 4: "pulse", 5: "skill", 6: "inventory", 7: "pause"}
PAD_DEADZONE = 0.28


def dead(value):
    return 0.0 if abs(value) < PAD_DEADZONE else value
