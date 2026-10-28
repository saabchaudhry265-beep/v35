"""Chaos/soak bot: plays many frames in every kind of area and checks invariants.
Run:  python tools/soak_bot.py [frames_per_area]   (uses SDL dummy drivers, no window needed)"""
import math
import os
import random
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402
from tropy import common as C  # noqa: E402
from tropy.content import DUNGEON_IDS, ENEMY_ORDER, MODS  # noqa: E402

C.DATA = Path(tempfile.mkdtemp())
C.SETTINGS_FILE = C.DATA / "settings.json"
C.PROFILE_FILE = C.DATA / "profile.json"
C.LOG_FILE = C.DATA / "game.log"
import game  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
DT = 1 / 60
PRESSED = set()


class _Keys:
    def __getitem__(self, key):
        return key in PRESSED


pygame.key.get_pressed = lambda: _Keys()


def check(g, where):
    p = g.p
    assert math.isfinite(p["x"]) and math.isfinite(p["y"]) and math.isfinite(p["hp"]), (where, "non-finite player")
    assert 0 <= p["x"] <= C.WW and 0 <= p["y"] <= C.WH, (where, "player out of world", p["x"], p["y"])
    assert len(g.bullets) <= 420 and len(g.hazards) < 400 and len(g.fx) <= 80 and len(g.particles) <= 420, (where, "unbounded lists")
    for e in g.current()["enemies"]:
        assert math.isfinite(e.x) and math.isfinite(e.y) and math.isfinite(e.hp), (where, "bad enemy", e.kind)
        assert 0 <= e.x <= C.WW and 0 <= e.y <= C.WH, (where, "enemy out of world", e.kind, e.x, e.y)
    assert len(g.current()["enemies"]) < 120, (where, "enemy explosion")


def drive(g, frames, where, rng):
    """Random-but-purposeful play: chase enemies, attack, dash, heal, use skills."""
    for i in range(frames):
        if g.state == "boon":
            g.pick_boon(g.boon["offers"][0]) if g.boon["kind"] == "free" else g.close_boon()
        if g.state == "dead":
            return "dead"
        if g.state != "play":
            g.set_state("play")
        p = g.p
        if i % 20 == 0:
            g.p["hp"] = max(p["hp"], g.max_hp() * 0.6) if rng.random() < 0.9 else p["hp"]
        targets = [e for e in g.current()["enemies"] if e.awake or e.kind not in ("boss", "finalboss", "miniboss")]
        if targets and rng.random() < 0.9:
            e = min(targets, key=lambda t: math.hypot(t.x - p["x"], t.y - p["y"]))
            dx, dy = e.x - p["x"], e.y - p["y"]
        else:
            dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
        PRESSED.clear()
        if abs(dx) > 8:
            PRESSED.add(pygame.K_d if dx > 0 else pygame.K_a)
        if abs(dy) > 8:
            PRESSED.add(pygame.K_s if dy > 0 else pygame.K_w)
        r = rng.random()
        if r < 0.02:
            g.dash()
        elif r < 0.03:
            g.attack(special=True)
        elif r < 0.035:
            g.attack(pulse=True)
        elif r < 0.04:
            g.potion()
        elif r < 0.05:
            g.use_skill(rng.randint(1, 4))
        elif r < 0.06:
            g.interact()
        if r > 0.5:
            g.attack()
        g.update(DT)
        if i % 3 == 0:
            g.draw()
        if i % 30 == 0:
            check(g, where)
        if g.transition:
            continue
    return "ok"


def main():
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 12345)
    t0 = time.time()
    g = game.Game()
    g.settings["fullscreen"] = False
    for char in range(3):
        g.creator = {"char": char, "mode": "campaign"}
        g.slot = 1 + char
        g.finish_creator()
        g.finish_cutscene()
        g.set_state("play")
        g.p["level"], g.p["sp"], g.p["points"] = 12, 24, 9
        g.p["xp"] = 0
        for m in rng.sample(list(MODS), 8):
            g.relics[m] = rng.randint(1, 2)
        for kind in rng.sample(list(C.WEAPONS), len(C.WEAPONS)):
            g.p["equip"]["weapon"] = game.Item("w", "weapon", rng.randint(0, 4), power=rng.randint(4, 30), weapon=kind, tier=char,
                                                mods=rng.sample(list(MODS), 2))
            for zi in range(3):
                g.area = g.return_area = "zone%d" % zi
                g.ensure_area(g.area)
                g.p["zonekills"][zi] = 9
                cx, cy = g.world().camp_xy
                g.p["x"], g.p["y"] = cx + 400, cy
                res = drive(g, FRAMES // 3, "zone%d/%s" % (zi, kind), rng)
                if res == "dead":
                    g.respawn()
        for did in DUNGEON_IDS[: 2 + char]:
            g.area = g.return_area = "zone%d" % int(did[2])
            g.ensure_area(g.area)
            g.enter(did)
            w = g.world()
            for room in w.rooms:
                g.p["x"], g.p["y"] = room["center"]
                res = drive(g, FRAMES // 8, did, rng)
                if res == "dead":
                    break
            g.leave_instance()
        for i in range(2):
            g.area = g.return_area = "zone%d" % i
            g.ensure_area(g.area)
            g.enter_pass(i, True)
            for room in g.world().rooms:
                g.p["x"], g.p["y"] = room["center"]
                if drive(g, FRAMES // 8, "pass%d" % i, rng) == "dead":
                    break
            g.leave_instance()
        g.p["bosses"] = [True] * 3
        g.area = g.return_area = "zone2"
        g.ensure_area("zone2")
        g.enter("final")
        drive(g, FRAMES // 2, "final", rng)
        g.respawn() if g.state == "dead" else None
        # abyss run
        g.creator = {"char": char, "mode": "abyss", "heat": set(list(["tough", "fury", "swarm", "swift"])[: char + 1])}
        g.finish_creator()
        for floor in range(1, 7):
            g.p["level"] = 10 + floor
            for room in g.world().rooms:
                g.p["x"], g.p["y"] = room["center"]
                if drive(g, FRAMES // 10, "abyss%d" % floor, rng) == "dead":
                    break
                if g.state == "dead":
                    break
            if g.state == "dead":
                break
            stairs = next((p for p in g.world().pois if p["kind"] == "stairs"), None)
            if not stairs:
                break
            g.next_floor()
        g.mode = "campaign"
        g.session = False
    log = C.LOG_FILE.read_text(encoding="utf8") if C.LOG_FILE.exists() else ""
    print("soak ok in {:.1f}s, frames/area {}, log entries: {}".format(time.time() - t0, FRAMES, log.count("[")))


if __name__ == "__main__":
    main()
