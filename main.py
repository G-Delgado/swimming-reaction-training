"""
Swim Start Reaction Trainer
----------------------------
Plays a randomized "swimmers, take your marks / ready / set / GO" (or the
Spanish equivalent) starting sequence, with unpredictable gaps between each
cue, so a swimmer can drill reacting to the start signal instead of
memorizing a fixed rhythm.

Language toggle: EN / ES
Gaps between cues: random, uniform between MIN_GAP and MAX_GAP seconds.
"""

import random

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import sp

# ---- Config -----------------------------------------------------------
MIN_GAP = 1.0   # seconds
MAX_GAP = 8.0   # seconds

SEQUENCES = {
    "EN": [
        ("assets/en_marks.ogg", "Swimmers, take your marks"),
        ("assets/en_ready.ogg", "Ready"),
        ("assets/en_set.ogg", "Set"),
        ("assets/start_buzzer.ogg", "GO!"),
    ],
    "ES": [
        ("assets/es_marcas.ogg", "Nadadores, en sus marcas"),
        ("assets/es_listos.ogg", "Listos"),
        ("assets/start_buzzer.ogg", "¡YA!"),
    ],
}

Window.clearcolor = (0.05, 0.08, 0.15, 1)


class SwimTrainerApp(App):
    def build(self):
        self.language = "EN"
        self.running = False
        self.sounds = {}
        self._events = []

        root = BoxLayout(orientation="vertical", padding=sp(24), spacing=sp(16))

        title = Label(
            text="Swim Start Reaction Trainer",
            font_size=sp(26),
            bold=True,
            size_hint=(1, 0.15),
        )
        root.add_widget(title)

        # Language toggle row
        lang_row = BoxLayout(size_hint=(1, 0.12), spacing=sp(12))
        self.btn_en = Button(text="English", background_color=(0.2, 0.6, 0.9, 1))
        self.btn_es = Button(text="Español", background_color=(0.3, 0.3, 0.35, 1))
        self.btn_en.bind(on_release=lambda *_: self.set_language("EN"))
        self.btn_es.bind(on_release=lambda *_: self.set_language("ES"))
        lang_row.add_widget(self.btn_en)
        lang_row.add_widget(self.btn_es)
        root.add_widget(lang_row)

        # Status display
        self.status_label = Label(
            text="Press Start",
            font_size=sp(40),
            bold=True,
            size_hint=(1, 0.4),
        )
        root.add_widget(self.status_label)

        self.info_label = Label(
            text=f"Random gap between cues: {MIN_GAP:.0f}-{MAX_GAP:.0f}s",
            font_size=sp(16),
            color=(0.7, 0.75, 0.8, 1),
            size_hint=(1, 0.08),
        )
        root.add_widget(self.info_label)

        # Start / Stop button
        self.start_btn = Button(
            text="START",
            font_size=sp(28),
            bold=True,
            background_color=(0.15, 0.7, 0.35, 1),
            size_hint=(1, 0.25),
        )
        self.start_btn.bind(on_release=lambda *_: self.toggle_start())
        root.add_widget(self.start_btn)

        self._preload_sounds()
        self._refresh_lang_buttons()
        return root

    # -- sound handling --------------------------------------------------
    def _preload_sounds(self):
        paths = set()
        for seq in SEQUENCES.values():
            for path, _ in seq:
                paths.add(path)
        for path in paths:
            snd = SoundLoader.load(path)
            self.sounds[path] = snd

    def set_language(self, lang):
        if self.running:
            return
        self.language = lang
        self._refresh_lang_buttons()

    def _refresh_lang_buttons(self):
        active = (0.2, 0.6, 0.9, 1)
        inactive = (0.3, 0.3, 0.35, 1)
        self.btn_en.background_color = active if self.language == "EN" else inactive
        self.btn_es.background_color = active if self.language == "ES" else inactive

    # -- sequence control --------------------------------------------------
    def toggle_start(self):
        if self.running:
            self.stop_sequence(cancelled=True)
        else:
            self.start_sequence()

    def start_sequence(self):
        self.running = True
        self.start_btn.text = "STOP"
        self.start_btn.background_color = (0.8, 0.2, 0.2, 1)
        self.status_label.text = "Get ready..."
        # brief pause before the first cue, itself randomized a little
        delay = random.uniform(1.0, 2.5)
        ev = Clock.schedule_once(lambda dt: self._run_step(0), delay)
        self._events.append(ev)

    def _run_step(self, index):
        if not self.running:
            return
        seq = SEQUENCES[self.language]
        if index >= len(seq):
            self._finish()
            return

        path, label = seq[index]
        self.status_label.text = label
        snd = self.sounds.get(path)
        if snd:
            snd.stop()
            snd.play()

        if index == len(seq) - 1:
            # last cue played (the start signal) -> end session shortly after
            ev = Clock.schedule_once(lambda dt: self._finish(), 1.5)
            self._events.append(ev)
            return

        gap = random.uniform(MIN_GAP, MAX_GAP)
        ev = Clock.schedule_once(lambda dt: self._run_step(index + 1), gap)
        self._events.append(ev)

    def _finish(self):
        self.status_label.text = "Press Start"
        self.start_btn.text = "START"
        self.start_btn.background_color = (0.15, 0.7, 0.35, 1)
        self.running = False

    def stop_sequence(self, cancelled=False):
        for ev in self._events:
            ev.cancel()
        self._events = []
        for snd in self.sounds.values():
            if snd:
                snd.stop()
        self.status_label.text = "Stopped" if cancelled else "Press Start"
        self.start_btn.text = "START"
        self.start_btn.background_color = (0.15, 0.7, 0.35, 1)
        self.running = False


if __name__ == "__main__":
    SwimTrainerApp().run()
