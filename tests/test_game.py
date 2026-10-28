"""Run from the project folder:  python -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
import unittest
from collections import deque
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tropy import common as C  # noqa: E402
from tropy import world as W  # noqa: E402
from tropy.content import (CHARACTERS, DUNGEONS, ENEMIES, MODS, PASSES, PATTERNS, QUESTS, SKILLS,  # noqa: E402
                           SPAWN, UNIQUES, ZONE_LAYOUT, NPCS, fmt)
from tropy.models import Enemy, Item  # noqa: E402
from tropy.meta import ACHIEVEMENTS, HINTS  # noqa: E402
from tropy.inputmap import DEFAULT_KEYS  # noqa: E402
import game  # noqa: E402


class GameCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        C.DATA = Path(self.tmp.name)
        C.SETTINGS_FILE = C.DATA / "settings.json"
        C.PROFILE_FILE = C.DATA / "profile.json"
        C.LOG_FILE = C.DATA / "game.log"
        self.g = game.Game()
        self.g.slot = 1
        self.g.creator = {"char": 2, "mode": "campaign"}
        self.g.finish_creator()
        self.g.finish_cutscene()
        self.g.set_state("play")

    def tearDown(self):
        game.pygame.quit()
        self.tmp.cleanup()

    def saved(self):
        self.assertTrue(self.g.save_game(), self.g.toast)
        return json.loads(C.slot_file(1).read_text(encoding="utf8"))


class ContentTests(unittest.TestCase):
    def test_name_declension_and_gender(self):
        text = "Откликнул<ся|ась> {name}. Путь {name_g}. Ты слаб<|а>."
        self.assertEqual(fmt(text, CHARACTERS[1]), "Откликнулась Лира. Путь Лиры. Ты слаба.")
        self.assertEqual(fmt(text, CHARACTERS[0]), "Откликнулся Эйрик. Путь Эйрика. Ты слаб.")

    def test_data_is_consistent(self):
        for q in QUESTS.values():
            self.assertIn(q["giver"], NPCS)
            self.assertTrue(q.get("after", next(iter(QUESTS))) in QUESTS)
        for table in SPAWN:
            self.assertTrue(set(table) <= set(ENEMIES))
        for uid in UNIQUES:
            self.assertTrue(all(m in MODS for m in UNIQUES[uid]["mods"]))
        for did in DUNGEONS:
            self.assertIn(did, UNIQUES)
        self.assertEqual(len(PASSES), 2)


class SaveTests(GameCase):
    def test_round_trip_keeps_new_fields(self):
        self.g.p["gold"], self.g.p["skills"] = 321, {"might": 2}
        self.g.p["quests"] = {"q_slime": {"s": 1, "n": 3}}
        self.g.p["dungeons"][3] = True
        self.saved()
        other = game.Game()
        other.load_game()
        self.assertEqual((other.p["gold"], other.p["name"], other.p["char"]), (321, "Альдрик", 2))
        self.assertEqual(other.p["skills"], {"might": 2})
        self.assertTrue(other.p["dungeons"][3])

    def test_backup_used_when_main_is_corrupted(self):
        self.g.save_game()
        self.g.save_game()
        C.slot_file(1).write_text("{broken", encoding="utf8")
        other = game.Game()
        other.load_game()
        self.assertTrue(other.session)
        self.assertIn("резервная", other.toast)

    def test_rejects_bad_data(self):
        data = self.saved()
        for mutate in (lambda d: d.update(version=1), lambda d: d["player"].update(gold=True),
                       lambda d: d["player"].update(hp=float("nan")), lambda d: d["player"].update(potions=99),
                       lambda d: d["player"].update(char=9), lambda d: d["player"].update(skills={"nope": 1}),
                       lambda d: d["player"].update(dungeons=[True]), lambda d: d.update(area="dg0_0"), lambda d: d["player"].update(playtime="x") or d["player"].update(char=-1),
                       lambda d: d["player"].update(quests={"q_slime": {"s": 7, "n": 0}})):
            bad = json.loads(json.dumps(data))
            mutate(bad)
            with self.assertRaises(ValueError):
                self.g.decode_save(bad)

    def test_old_saves_are_migrated(self):
        data = self.saved()
        data["version"] = 33
        data["player"]["dungeons"] = [True, False, False]
        data["player"].pop("char")
        data["player"].pop("passes")
        data["areas"] = {}
        C.legacy_saves()[1].write_text(json.dumps(data), encoding="utf8")
        C.slot_file(1).unlink()
        other = game.Game()
        other.load_game()
        self.assertEqual(other.state, "play")
        self.assertEqual(len(other.p["dungeons"]), 6)
        self.assertTrue(other.p["dungeons"][0])

    def test_saving_inside_a_dungeon_returns_to_the_region(self):
        g = self.g
        g.p["x"], g.p["y"] = 800, 800
        g.enter("dg0_0")
        self.assertEqual(g.area, "dg0_0")
        data = self.saved()
        self.assertEqual(data["area"], "zone0")
        self.assertEqual(data["player"]["x"], 800)

    def test_state_saved_mid_boss_fight_validates(self):
        g = self.g
        boss = next(e for e in g.current()["enemies"] if e.kind == "boss")
        boss.awake, boss.pat, boss.pi, boss.slow, boss.burn = 1, "laser", -0.01, 0.0, 0.0
        self.saved()

    def test_new_game_archives_previous_save(self):
        self.g.save_game()
        self.g.creator = {"char": 0, "mode": "campaign"}
        self.g.finish_creator()
        self.assertTrue((C.DATA / "eldoria_v35_slot1.archive.json").exists())

    def test_item_and_enemy_restore(self):
        for bad in (None, [], {"name": "x", "slot": "bad", "rarity": 0}, {"name": "x", "slot": "weapon", "rarity": 9},
                    {"name": "x", "slot": "weapon", "rarity": 0, "plus": 9},
                    {"name": "x", "slot": "weapon", "rarity": 0, "mods": ["bogus"]}):
            with self.assertRaises((ValueError, TypeError)):
                Item.restore(bad)
        e = self.g.make_enemy("boss", 500, 500, 0)
        e.wind, e.attack, e.kx, e.pat, e.awake = 0.4, "charge", 300.0, "ring", 1
        restored = Enemy.restore(json.loads(json.dumps(asdict(e))))
        self.assertEqual((restored.wind, restored.attack, restored.kx, restored.pat, restored.awake), (0, "", 0.0, "", 0))


class WorldTests(GameCase):
    def test_zone_maps_are_connected_and_distinct(self):
        grids = []
        for zi in range(3):
            w = W.build_zone(zi)
            start = (int(w.camp_xy[0] // C.CELL), int(w.camp_xy[1] // C.CELL))
            seen, queue = {start}, deque([start])
            while queue:
                cx, cy = queue.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (cx + dx, cy + dy)
                    if 0 <= n[0] < w.gw and 0 <= n[1] < w.gh and n not in seen and w.grid[n[1]][n[0]] not in W.SOLID:
                        seen.add(n)
                        queue.append(n)
            for poi in w.pois:
                self.assertIn((int(poi["x"] // C.CELL), int(poi["y"] // C.CELL)), seen, (zi, poi["kind"]))
            self.assertIn((int(w.arena_xy[0] // C.CELL), int(w.arena_xy[1] // C.CELL)), seen)
            grids.append(w.grid)
        self.assertNotEqual(grids[0], grids[1])
        self.assertNotEqual([ZONE_LAYOUT[i]["camp"] for i in range(3)].count(ZONE_LAYOUT[0]["camp"]), 3)

    def test_dungeons_and_passes_are_connected(self):
        for did, info in DUNGEONS.items():
            w = W.build_dungeon(did, info)
            self.assertEqual(len(w.rooms), len(info["kinds"]) + 1)
            self.assertTrue(w.doors)
            self.assertTrue(w.pois)
        for i, info in enumerate(PASSES):
            self.assertEqual(len(W.build_pass(i, info).pois), 2)


class CombatTests(GameCase):
    def test_defense_never_zeroes_damage(self):
        self.g.p["equip"]["armor"] = Item("a", "armor", 0, armor=200)
        self.g.p["hp"], self.g.p["invuln"] = 100, 0
        self.g.take_damage(6)
        self.assertLess(self.g.p["hp"], 100)

    def test_weapon_types_use_enemy_weaknesses(self):
        golem = self.g.make_enemy("golem", 800, 800, 1)
        self.assertGreater(self.g.resist(golem, "pierce"), self.g.resist(golem, "slash"))
        shaman = self.g.make_enemy("shaman", 800, 800, 2)
        self.assertLess(self.g.resist(shaman, "magic"), self.g.resist(shaman, "slash"))

    def test_mods_are_applied(self):
        g = self.g
        base = g.damage()
        g.relics["might"] = 2
        self.assertGreater(g.damage(), base)
        e = g.make_enemy("slime", 700, 700, 0)
        g.current()["enemies"].append(e)
        g.relics["burn"] = 1
        g.relics["frost"] = 1
        g.hit(e, 1)
        self.assertGreater(e.burn, 0)
        self.assertGreater(e.slow, 0)

    def test_dormant_boss_is_invulnerable_and_arena_needs_kills(self):
        g = self.g
        boss = next(e for e in g.current()["enemies"] if e.kind == "boss")
        hp = boss.hp
        g.hit(boss, 5)
        self.assertEqual(boss.hp, hp)
        ax, ay = g.world().arena_xy
        g.p["x"], g.p["y"] = ax, ay + 300
        g.update_arena(0.016)
        self.assertEqual(boss.awake, 0)
        g.p["zonekills"][0] = 9
        g.p["x"], g.p["y"] = ax, ay + 300
        g.update_arena(0.016)
        self.assertEqual(boss.awake, 1)
        self.assertIsNotNone(g.arena)

    def test_boss_patterns_and_two_forms(self):
        g = self.g
        g.p["hp"] = 10 ** 5
        boss = g.make_enemy("boss", 1000, 800, 1)
        boss.awake = 1
        g.current()["enemies"].append(boss)
        g.p["x"], g.p["y"] = 800, 800
        for name in PATTERNS:
            g.start_pattern(boss, name)
            for _ in range(120):
                g.update_enemy(boss, 0.016)
                g.update_hazards(0.016)
                g.update_bullets(0.016)
            boss.pat, boss.wind, boss.dash, boss.attack = "", 0, 0, ""
        boss.hp = boss.maxhp * 0.4
        for _ in range(130):
            g.update_enemy(boss, 0.016)
        self.assertEqual(boss.phase, 2)

    def test_every_enemy_kind_can_attack(self):
        g = self.g
        g.p["hp"] = 10 ** 5
        for kind in list(ENEMIES):
            if kind in ("boss", "finalboss", "miniboss"):
                continue
            e = g.make_enemy(kind, 900, 900, 1)
            g.current()["enemies"].append(e)
            g.p["x"], g.p["y"] = 1000, 900
            for _ in range(240):
                g.update_enemy(e, 0.016)
                g.update_hazards(0.016)
                g.update_bullets(0.016)
            g.current()["enemies"].remove(e)

    def test_loot_drops_animate(self):
        g = self.g
        g.add_drop(900, 900, g.make_unique("dg0_0"))
        drop = g.current()["drops"][-1]
        self.assertEqual(drop["age"], 0.0)
        for _ in range(60):
            g.update(0.016)
        self.assertGreater(drop["age"], 0.9)


class ProgressTests(GameCase):
    def test_quest_flow_and_rewards(self):
        g = self.g
        self.assertEqual(g.quest_status("q_slime"), "available")
        g.accept_quest("q_slime")
        for _ in range(6):
            e = g.make_enemy("slime", 700, 700, 0)
            g.current()["enemies"].append(e)
            g.kill(e)
        self.assertEqual(g.quest_status("q_slime"), "ready")
        g.claim_quest("q_slime")
        self.assertEqual(g.quest_status("q_slime"), "done")

    def test_faster_progression(self):
        g = self.g
        g.p["xp"] = 10 ** 5
        g.level_up()
        self.assertGreaterEqual(g.p["level"], 10)
        self.assertGreaterEqual(g.p["sp"], 18)

    def test_skill_requirements_respec_and_costs(self):
        g = self.g
        g.p["sp"] = 6
        g.buy_skill("crit")
        self.assertEqual(g.rank("crit"), 0)
        g.buy_skill("might")
        g.buy_skill("might")
        g.buy_skill("cry")
        self.assertEqual(g.rank("cry"), 1)
        g.p["x"], g.p["y"] = g.world().camp_xy
        g.respec()
        self.assertEqual(g.p["sp"], 6)

    def test_passes_replace_portals(self):
        g = self.g
        gate = next(p for p in g.world().pois if p["kind"] == "gate_next")
        g.p["x"], g.p["y"] = gate["x"], gate["y"] + 60
        g.interact()
        self.assertIsNone(g.transition)
        g.p["bosses"][0], g.p["level"] = True, 5
        g.interact()
        for _ in range(100):
            g.update(0.016)
        self.assertEqual(g.area, "pass0")
        self.assertTrue(g.world().rooms)

    def test_abyss_run_awards_souls(self):
        g = self.g
        g.start_abyss(CHARACTERS[0])
        self.assertEqual(g.area, "abyss")
        g.p["hp"] = 1
        g.p["invuln"] = 0
        g.take_damage(10 ** 6, "тест")
        self.assertEqual(g.state, "dead")
        self.assertGreater(g.meta["shards"], 0)
        self.assertEqual(game.Game().meta["shards"], g.meta["shards"])


if __name__ == "__main__":
    unittest.main()


class FakeJoy:
    def __init__(self):
        self.axes = [0.0] * 6

    def get_numaxes(self):
        return 6

    def get_axis(self, i):
        return self.axes[i]

    def get_instance_id(self):
        return 7

    def rumble(self, *args):
        pass


EV = lambda t, **kw: game.pygame.event.Event(t, **kw)  # noqa: E731


class FeatureTests(GameCase):
    def test_settings_pages_and_rebinding(self):
        g = self.g
        g.open_settings()
        for tab in range(4):
            g.settings_tab = tab
            g.draw()
        g.start_rebind("attack")
        g.handle_event(EV(game.pygame.KEYDOWN, key=game.pygame.K_f, unicode="f"))
        self.assertEqual(g.keys["attack"], game.pygame.K_f)
        g.start_rebind("potion")
        g.handle_event(EV(game.pygame.KEYDOWN, key=game.pygame.K_f, unicode="f"))
        self.assertEqual(g.keys["potion"], game.pygame.K_f)
        self.assertEqual(len(set(g.keys.values())), len(g.keys))
        g.reset_keys()
        self.assertEqual(g.keys, DEFAULT_KEYS)
        g.opt_cycle("difficulty", 1, 3)
        g.opt_toggle("lowfx")
        other = game.Game()
        self.assertEqual(other.settings["difficulty"], 2)
        self.assertTrue(other.settings["lowfx"])

    def test_save_slots(self):
        g = self.g
        g.save_game()
        self.assertIsNotNone(g.slot_info(1))
        self.assertIsNone(g.slot_info(2))
        g.open_slots("new")
        g.draw()
        g.choose_slot(2)
        self.assertEqual(g.state, "creator")
        g.creator = {"char": 0, "mode": "campaign"}
        g.finish_creator()
        g.finish_cutscene()
        g.save_game()
        self.assertEqual(g.slot_info(2)["name"], "Эйрик")
        g.open_slots("load")
        g.draw()
        g.delete_slot(2)
        g.delete_slot(2)
        self.assertIsNone(g.slot_info(2))

    def test_gamepad_controls_and_menu_navigation(self):
        g = self.g
        joy = FakeJoy()
        g.joys[7] = joy
        g.p["x"], g.p["y"] = g.world().free_spot(__import__("random").Random(3), 400, avoid=((g.world().camp_xy[0], g.world().camp_xy[1], 320),), radius=40)
        x0 = g.p["x"]
        joy.axes[0] = 1.0
        for _ in range(10):
            g.update(0.016)
        self.assertGreater(g.p["x"], x0)
        joy.axes[0] = 0.0
        g.handle_event(EV(game.pygame.JOYBUTTONDOWN, button=3))
        g.handle_event(EV(game.pygame.JOYHATMOTION, value=(0, 1)))
        g.set_state("pause")
        g.draw()
        g.handle_event(EV(game.pygame.JOYHATMOTION, value=(0, -1)))
        g.draw()
        self.assertIsNotNone(g.focused_button())
        g.handle_event(EV(game.pygame.JOYBUTTONDOWN, button=1))
        self.assertEqual(g.state, "play")
        g.handle_event(EV(game.pygame.JOYDEVICEREMOVED, instance_id=7))
        self.assertEqual(g.state, "pause")

    def test_focus_loss_pauses(self):
        self.g.handle_event(EV(game.pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.g.state, "pause")
        self.assertFalse(self.g.focus)

    def test_all_weapons_attack(self):
        g = self.g
        g.p["x"], g.p["y"] = 900, 900
        for kind in C.WEAPONS:
            g.p["equip"]["weapon"] = Item("w", "weapon", 0, power=4, weapon=kind)
            e = g.make_enemy("golem", 960, 900, 1, elite="")
            g.current()["enemies"].append(e)
            for special in (False, True):
                g.p["attack_cd"] = g.p["skill_cd"] = 0
                g.p["face_x"], g.p["face_y"] = 1.0, 0.0
                g.attack(special=special)
                for _ in range(60):
                    g.update(0.016)
                    g.draw()
            g.current()["enemies"].clear()
        self.assertGreater(g.resist(g.make_enemy("golem", 0, 0, 1), "blunt"), 1.2)

    def test_elites_have_affixes_and_rewards(self):
        g = self.g
        for affix in ("fast", "armored", "vampiric", "explosive"):
            e = g.make_enemy("wolf", 800, 800, 0, elite=affix)
            g.current()["enemies"].append(e)
            self.assertEqual(e.elite, affix)
            before = g.meta["stats"].get("elites", 0)
            g.kill(e)
            self.assertEqual(g.meta["stats"]["elites"], before + 1)
        for _ in range(60):
            g.update_bullets(0.016)

    def test_new_mods(self):
        g = self.g
        g.relics.update({"rage": 2, "second": 1, "heavy": 1, "guard": 1, "chill": 1, "twin": 1, "fortune": 1, "roomheal": 1})
        base = g.damage()
        g.p["hp"] = g.max_hp() * 0.2
        self.assertGreater(g.damage(), base)
        g.p["hp"], g.p["invuln"] = 5, 0
        g.take_damage(10 ** 5, "тест")
        self.assertEqual(g.state, "play")
        self.assertTrue(g.second_used)
        e = g.make_enemy("slime", 700, 700, 0, elite="")
        g.current()["enemies"].append(e)
        for _ in range(6):
            g.hit(e, 0.01)
        g.update_skills(0.016)
        g.make_item(1)

    def test_difficulty_scales_enemies(self):
        g = self.g
        g.settings["difficulty"] = 0
        easy = g.make_enemy("wolf", 0, 0, 0, elite="")
        g.settings["difficulty"] = 2
        hard = g.make_enemy("wolf", 0, 0, 0, elite="")
        self.assertGreater(hard.maxhp, easy.maxhp)
        self.assertGreater(hard.damage, easy.damage)

    def test_abyss_heat_daily_and_history(self):
        g = self.g
        g.creator = {"char": 1, "mode": "abyss", "heat": {"tough", "fury", "dry"}, "daily": True}
        g.finish_creator()
        self.assertEqual(g.p["potions"], 0)
        self.assertEqual(g.run["seed"], __import__("tropy.meta", fromlist=["daily_seed"]).daily_seed())
        first = g.world().rooms[0]["rect"]
        g.creator = {"char": 1, "mode": "abyss", "heat": set(), "daily": True}
        g.finish_creator()
        self.assertEqual(g.world().rooms[0]["rect"], first)
        g.creator = {"char": 0, "mode": "abyss", "heat": {"tough", "fury"}}
        g.finish_creator()
        g.take_damage_force = None
        g.p["hp"], g.p["invuln"] = 1, 0
        g.take_damage(10 ** 6, "тест")
        self.assertTrue(g.meta["history"])
        self.assertEqual(g.meta["history"][-1]["heat"], 2)

    def test_achievements_hints_and_records(self):
        g = self.g
        e = g.make_enemy("slime", 700, 700, 0, elite="")
        g.current()["enemies"].append(e)
        g.kill(e)
        g.check_progress()
        self.assertIn("first_blood", g.meta["ach"])
        self.assertTrue(g.ach_toasts)
        g.hint_t = 0
        g.hint("loot")
        self.assertIn("loot", g.meta["hints"])
        g.open_records()
        for tab in range(4):
            g.records_tab = tab
            g.draw()
        g.open_credits()
        g.draw()
        self.assertEqual(len(ACHIEVEMENTS), 28)

    def test_cli_and_crash_safe_loop(self):
        self.assertEqual(game.main(["--version"]), 0)
        g = self.g
        calls = {"n": 0}

        def boom(dt):
            calls["n"] += 1
            if calls["n"] > 3:
                g.running = False
            raise RuntimeError("test crash")
        g.update = boom
        g.main_loop()
        self.assertTrue(C.LOG_FILE.exists())
        self.assertIn("test crash", C.LOG_FILE.read_text(encoding="utf8"))

    def test_remaining_screens_draw(self):
        g = self.g
        g.creator = {"char": 1, "mode": "abyss", "heat": {"tough"}}
        g.set_state("creator")
        g.draw()
        g.creator = {"char": 2, "mode": "campaign"}
        g.draw()
        for state in ("shop", "smith", "skills", "journal", "map", "stats", "inventory", "help", "sanctum", "menu"):
            g.set_state(state)
            g.journal_tab = 1
            g.draw()
        g.journal_tab = 0
        g.draw()
        g.set_state("play")

    def test_lighting_and_room_map_draw(self):
        g = self.g
        g.p["x"], g.p["y"] = 800, 800
        g.enter("dg1_1")
        g.draw()
        g.minimap((10, 10, 168, 115))
        g.settings["lowfx"] = True
        game.art.LOWFX[0] = True
        g.draw()
        game.art.LOWFX[0] = False
