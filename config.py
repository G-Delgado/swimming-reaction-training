"""
Settings persistence and reaction-time grading.

Stored as JSON in the app's user data directory so it survives reinstalls of
the running app and app restarts.
"""

import json
import os

# Every gap in the start sequence is randomised inside a [min, max] window.
# The window after "En sus marcas" is the one that matters most for training,
# so it defaults to a wide, genuinely unpredictable range.
DEFAULTS = {
    # pause before the sequence begins at all
    "pre_min": 1.0, "pre_max": 2.5,
    # "Nadadores, a órdenes del árbitro"  ->  five beeps
    "g1_min": 1.0, "g1_max": 3.0,
    # five beeps  ->  "En sus marcas"
    "g2_min": 1.0, "g2_max": 3.0,
    # "En sus marcas"  ->  start signal   (the critical, most random window)
    "g3_min": 1.0, "g3_max": 8.0,
    # audio levels
    "vol_voice": 1.0,
    "vol_whistle": 1.0,
    "vol_start": 1.0,
}

RANGE_FIELDS = [
    ("pre", "Antes de empezar", "Pausa inicial tras pulsar Iniciar"),
    ("g1", "Tras «a órdenes del árbitro»", "Hasta los cinco pitidos"),
    ("g2", "Tras los cinco pitidos", "Hasta «En sus marcas»"),
    ("g3", "Tras «En sus marcas»", "Hasta la señal de salida"),
]

# Grades are tuned for a screen tap (pure reaction), not for feet leaving the
# block, which is roughly 250 ms slower.
GRADES = [
    (180, "RELÁMPAGO", (0.65, 0.55, 0.98, 1)),
    (230, "EXCELENTE", (0.20, 0.83, 0.60, 1)),
    (300, "MUY BUENO", (0.20, 0.83, 0.60, 1)),
    (380, "BUENO", (0.133, 0.827, 0.933, 1)),
    (480, "PROMEDIO", (0.98, 0.75, 0.29, 1)),
    (10 ** 9, "LENTO", (0.96, 0.44, 0.48, 1)),
]


def grade_for(ms):
    for limit, label, color in GRADES:
        if ms < limit:
            return label, color
    return GRADES[-1][1], GRADES[-1][2]


def fmt_ms(ms):
    if ms is None:
        return "--"
    if ms < 1000:
        return "%d ms" % round(ms)
    return "%.2f s" % (ms / 1000.0)


class Store:
    """Small JSON-backed store for settings plus reaction history."""

    def __init__(self, data_dir):
        self.dir = data_dir
        self.settings_path = os.path.join(data_dir, "settings.json")
        self.history_path = os.path.join(data_dir, "history.json")
        self.settings = dict(DEFAULTS)
        self.history = []
        self.load()

    # -- settings ------------------------------------------------------
    def load(self):
        try:
            with open(self.settings_path, "r") as fh:
                saved = json.load(fh)
            merged = dict(DEFAULTS)
            merged.update({k: v for k, v in saved.items() if k in DEFAULTS})
            self.settings = merged
        except Exception:
            self.settings = dict(DEFAULTS)
        try:
            with open(self.history_path, "r") as fh:
                hist = json.load(fh)
            if isinstance(hist, list):
                self.history = [h for h in hist if isinstance(h, dict)][:100]
        except Exception:
            self.history = []

    def save_settings(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.settings_path, "w") as fh:
                json.dump(self.settings, fh)
        except Exception:
            pass

    def set(self, key, value):
        self.settings[key] = value
        # keep each min <= its max
        base = key[:-4] if key.endswith(("_min", "_max")) else None
        if base:
            lo = self.settings.get(base + "_min", 0.0)
            hi = self.settings.get(base + "_max", 0.0)
            if lo > hi:
                if key.endswith("_min"):
                    self.settings[base + "_max"] = lo
                else:
                    self.settings[base + "_min"] = hi
        self.save_settings()

    def get(self, key):
        return self.settings.get(key, DEFAULTS.get(key))

    def reset_settings(self):
        self.settings = dict(DEFAULTS)
        self.save_settings()

    # -- history -------------------------------------------------------
    def add_time(self, ms):
        label, _ = grade_for(ms)
        self.history.insert(0, {"ms": round(ms, 1), "grade": label})
        self.history = self.history[:100]
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.history_path, "w") as fh:
                json.dump(self.history, fh)
        except Exception:
            pass

    def clear_history(self):
        self.history = []
        try:
            with open(self.history_path, "w") as fh:
                json.dump([], fh)
        except Exception:
            pass

    def best(self):
        times = [h["ms"] for h in self.history]
        return min(times) if times else None

    def average(self):
        times = [h["ms"] for h in self.history]
        return sum(times) / len(times) if times else None

    def count(self):
        return len(self.history)
