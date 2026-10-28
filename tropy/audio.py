"""Procedural sound effects and music (mixin for Game)."""
import math
import random
from array import array

import pygame

SFX = {
    # name: (start Hz, end Hz, seconds, noise, volume)
    "hit": (220, 180, 0.055, 0.45, 1.0), "hurt": (115, 80, 0.12, 0.35, 1.0), "loot": (660, 760, 0.10, 0.0, 0.8),
    "level": (660, 1100, 0.30, 0.0, 1.0), "dash": (350, 700, 0.08, 0.5, 0.8), "win": (1046, 1318, 0.40, 0.0, 1.0),
    "ui": (900, 900, 0.03, 0.0, 0.5), "warn": (300, 520, 0.28, 0.1, 0.9), "rare": (880, 1760, 0.45, 0.0, 1.0),
    "heal": (520, 780, 0.25, 0.0, 0.8), "swing": (500, 200, 0.09, 0.7, 0.6), "boom": (90, 40, 0.30, 0.6, 1.0),
    "fire": (400, 300, 0.12, 0.6, 0.7),
}
# music: semitone offsets from A4, step length in seconds, bass pattern
TRACKS = {
    "menu": ([0, 3, 7, 12, 7, 3, 0, -2, 3, 7, 10, 7, 3, 0, -5, 0], 0.6, [-24, -24, -19, -22]),
    "zone0": ([0, 2, 4, 7, 9, 7, 4, 2, 0, 4, 7, 9, 12, 9, 7, 4], 0.5, [-24, -17, -19, -17]),
    "zone1": ([-2, 0, 3, 5, 3, 0, -2, -4, 0, 3, 5, 8, 5, 3, 0, -2], 0.55, [-26, -26, -21, -24]),
    "zone2": ([0, 3, 7, 8, 7, 3, 0, -1, 0, 4, 7, 11, 12, 11, 7, 4], 0.4, [-24, -24, -21, -20]),
    "dungeon": ([0, 0, 6, 0, 0, 7, 0, 0, 3, 0, 0, 6, 0, 0, 1, 0], 0.7, [-30, -30, -27, -30]),
    "boss": ([0, 3, 0, 7, 0, 3, 0, 8, 0, 3, 0, 7, 0, 10, 8, 7], 0.25, [-24, -24, -24, -22]),
    "abyss": ([0, 2, 4, 6, 8, 6, 4, 2, 0, 3, 6, 9, 6, 3, 0, -3], 0.5, [-28, -26, -28, -24]),
}


def synth_track(name, rate, channels):
    """Pure-Python synthesis of one music loop (safe to run in a worker thread)."""
    notes, step, bass = TRACKS[name]
    count = int(rate * step)
    samples = array("h")
    for idx, n in enumerate(notes):
        freq = 440.0 * 2 ** (n / 12)
        bfreq = 440.0 * 2 ** (bass[(idx // 4) % len(bass)] / 12)
        for i in range(count):
            t = i / rate
            env = min(1.0, i / 200) * min(1.0, (count - i) / 300) * math.exp(-1.3 * t / step)
            lead = math.sin(math.tau * freq * t) + 0.4 * math.sin(math.tau * freq * 2 * t)
            low = math.sin(math.tau * bfreq * (idx * count + i) / rate) * 0.7 if idx % 2 == 0 else 0.0
            value = int((lead * env + low * 0.5) * 2300)
            for _ in range(channels):
                samples.append(value)
    return samples.tobytes()


class AudioMixin:
    def init_audio(self):
        self.sounds = self.make_sounds()
        self.tracks = {}
        self.track_bytes = {}
        self.audio_format = None
        self.music_channel = None
        self.track_name = None
        info = pygame.mixer.get_init()
        if info and info[1] == -16:
            self.audio_format = (info[0], info[2])

    def make_sounds(self):
        result = {}
        info = pygame.mixer.get_init()
        if not info or info[1] != -16:
            return result
        rate, _, channels = info
        for name, (f0, f1, dur, noise, vol) in SFX.items():
            samples = array("h")
            count = int(rate * dur)
            phase = 0.0
            for i in range(count):
                k = i / count
                freq = f0 + (f1 - f0) * k
                phase += math.tau * freq / rate
                fade = (1 - k) ** 2
                mixed = math.sin(phase) * (1 - noise) + random.uniform(-1, 1) * noise
                sample = int(mixed * 6500 * vol * fade)
                for _ in range(channels):
                    samples.append(sample)
            try:
                result[name] = pygame.mixer.Sound(buffer=samples.tobytes())
            except pygame.error:
                pass
        return result

    def sfx_volume(self):
        return self.settings["volume"] * self.settings["sfx"]

    def sound(self, name):
        snd = self.sounds.get(name)
        if snd and self.focus:
            snd.set_volume(self.sfx_volume())
            snd.play()

    def build_track(self, name):
        data = self.track_bytes.get(name)
        if data is None and self.audio_format:
            # Synthesize on demand instead of spawning one worker per Game.
            # Tests repeatedly create/quit Pygame instances; background workers
            # surviving pygame.quit() can race with rendering and destabilize SDL.
            try:
                data = synth_track(name, *self.audio_format)
            except Exception:  # noqa: BLE001
                data = b""
            self.track_bytes[name] = data
        if not data:
            return None
        try:
            return pygame.mixer.Sound(buffer=data)
        except pygame.error:
            return None

    def desired_track(self):
        if self.state in ("menu", "creator", "sanctum", "slots", "records", "credits", "cutscene") or not self.session:
            return "menu"
        if any(e.kind in ("boss", "finalboss", "miniboss") and e.awake for e in self.current()["enemies"]):
            return "boss"
        kind = self.area_kind()
        if kind == "zone":
            return "zone%d" % self.zone_index()
        if kind in ("dungeon", "pass"):
            return "dungeon"
        return "abyss" if kind == "abyss" else "boss"

    def update_music(self):
        if not self.sounds and not self.tracks and pygame.mixer.get_init() is None:
            return
        want = self.desired_track() if (self.settings["music"] and self.focus) else None
        vol = self.settings["volume"] * self.settings["music_vol"] * 0.35
        if want != self.track_name:
            if self.music_channel:
                self.music_channel.fadeout(400) if hasattr(self.music_channel, "fadeout") else self.music_channel.stop()
            self.music_channel = None
            self.track_name = want
        if want and vol > 0:
            if self.tracks.get(want) is None:
                self.tracks[want] = self.build_track(want)
            snd = self.tracks[want]
            if snd and (self.music_channel is None or not self.music_channel.get_busy()):
                self.music_channel = snd.play(loops=-1)
            if self.music_channel:
                self.music_channel.set_volume(vol)
        elif self.music_channel:
            self.music_channel.stop()
            self.music_channel = None
