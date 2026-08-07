"""
Entrenador de Salidas — Swim start reaction trainer (español)

Three modes:
  AUTO      full sequence with randomised gaps, hands-free
  MANUAL    the coach fires each command, for training another swimmer
  REACCIÓN  full sequence, then measures how fast you tap the screen

Sequence (as called at a meet):
    "Nadadores, a órdenes del árbitro"
        -> pausa aleatoria
    pi· pi· pi· pi·  piiiiiii      (cuatro rápidos + uno largo y claro)
        -> pausa aleatoria
    "En sus marcas"
        -> pausa aleatoria (la importante)
    SEÑAL DE SALIDA
"""

import os
import random
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.animation import Animation

from config import Store, grade_for, fmt_ms, RANGE_FIELDS
import theme as T
from theme import (
    WaterBackground, Card, PillButton, Chip, Slider2, PulseRing,
    CYAN, TEXT, TEXT_MUTED, TEXT_FAINT, EMERALD, AMBER, ROSE, VIOLET,
    SLATE_DARK, hx,
)

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

MODE_AUTO = "auto"
MODE_MANUAL = "manual"
MODE_REACT = "react"

MODE_META = {
    MODE_AUTO: ("AUTO", "Secuencia completa sola"),
    MODE_MANUAL: ("MANUAL", "Tú das cada orden"),
    MODE_REACT: ("REACCIÓN", "Mide tu tiempo"),
}

# The four steps of the sequence, used by both the automatic engine and the
# manual mode buttons.
STEP_ARBITRO = 0
STEP_SILBATOS = 1
STEP_MARCAS = 2
STEP_SALIDA = 3

STEP_TEXT = {
    STEP_ARBITRO: "Nadadores,\na órdenes del árbitro",
    STEP_SILBATOS: "Pitidos del árbitro",
    STEP_MARCAS: "En sus marcas",
    STEP_SALIDA: "¡SALIDA!",
}

STEP_BUTTON = {
    STEP_ARBITRO: "1 · A órdenes del árbitro",
    STEP_SILBATOS: "2 · Cinco pitidos",
    STEP_MARCAS: "3 · En sus marcas",
    STEP_SALIDA: "4 · ¡SEÑAL DE SALIDA!",
}

# Measured lengths of the cue clips, so the randomised gap starts counting
# only after the audio has finished rather than overlapping it.
DUR_ARBITRO = 1.97
DUR_BEEPS = 2.26     # 4 fast beeps + the long clear fifth
DUR_MARCAS = 0.87


def lbl(text, size=14, color=TEXT_MUTED, bold=False, halign="left", **kw):
    w = Label(text=text, font_size=sp(size), color=color, bold=bold,
              halign=halign, valign="middle", **kw)
    w.bind(size=lambda i, v: setattr(i, "text_size", v))
    return w


class Audio:
    """Loads and plays the cue sounds, honouring per-cue volume settings."""

    FILES = {
        "arbitro": "v_arbitro.ogg",
        "marcas": "v_marcas.ogg",
        "silbatos": "referee_beeps.ogg",
        "salida": "start_beep.ogg",
    }
    VOLUME_KEY = {
        "arbitro": "vol_voice",
        "marcas": "vol_voice",
        "silbatos": "vol_whistle",
        "salida": "vol_start",
    }

    def __init__(self, store):
        self.store = store
        self.sounds = {}
        for key, name in self.FILES.items():
            path = os.path.join(ASSETS, name)
            try:
                self.sounds[key] = SoundLoader.load(path)
            except Exception:
                self.sounds[key] = None

    def play(self, key):
        snd = self.sounds.get(key)
        if not snd:
            return
        try:
            snd.stop()
            snd.volume = float(self.store.get(self.VOLUME_KEY[key]))
            snd.play()
        except Exception:
            pass

    def stop_all(self):
        for snd in self.sounds.values():
            if snd:
                try:
                    snd.stop()
                except Exception:
                    pass


# ======================================================================
#  Train screen
# ======================================================================
class TrainScreen(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", spacing=dp(12), **kw)
        self.app = app
        self.mode = MODE_AUTO
        self.running = False
        self.armed = False          # start signal fired, waiting for a tap
        self.t_signal = None
        self.manual_step = STEP_ARBITRO
        self._timers = []

        # -- mode selector ------------------------------------------------
        self.mode_row = BoxLayout(size_hint_y=None, height=dp(58),
                                  spacing=dp(8))
        self.mode_buttons = {}
        for m in (MODE_AUTO, MODE_MANUAL, MODE_REACT):
            name, _sub = MODE_META[m]
            b = PillButton(text=name, font_size=sp(13), radius=dp(14))
            b.bind(on_release=lambda _b, mm=m: self.set_mode(mm))
            self.mode_buttons[m] = b
            self.mode_row.add_widget(b)
        self.add_widget(self.mode_row)

        self.mode_hint = lbl("", size=12, color=TEXT_FAINT, halign="center",
                             size_hint_y=None, height=dp(16))
        self.add_widget(self.mode_hint)

        # -- sequence preview --------------------------------------------
        self.preview = BoxLayout(size_hint_y=None, height=dp(30),
                                 spacing=dp(6))
        self.add_widget(self.preview)

        # -- stage ---------------------------------------------------------
        self.stage = FloatLayout()
        self.ring = PulseRing(pos_hint={"center_x": .5, "center_y": .58})
        self.stage.add_widget(self.ring)

        self.stage_box = BoxLayout(orientation="vertical", spacing=dp(6),
                                   pos_hint={"center_x": .5, "center_y": .5},
                                   size_hint=(1, None), height=dp(210))
        self.badge = lbl("LISTO PARA EMPEZAR", size=11, color=CYAN,
                         bold=True, halign="center",
                         size_hint_y=None, height=dp(20))
        self.big = lbl("Entrenador\nde Salidas", size=34, color=TEXT,
                       bold=True, halign="center")
        self.sub = lbl("", size=13, color=TEXT_FAINT, halign="center",
                       size_hint_y=None, height=dp(40))
        self.stage_box.add_widget(self.badge)
        self.stage_box.add_widget(self.big)
        self.stage_box.add_widget(self.sub)
        self.stage.add_widget(self.stage_box)
        self.add_widget(self.stage)

        # -- manual step buttons -------------------------------------------
        self.manual_box = BoxLayout(orientation="vertical", spacing=dp(8),
                                    size_hint_y=None, height=dp(0),
                                    opacity=0)
        self.manual_buttons = {}
        for step in (STEP_ARBITRO, STEP_SILBATOS, STEP_MARCAS, STEP_SALIDA):
            b = PillButton(text=STEP_BUTTON[step], font_size=sp(14),
                           radius=dp(14), size_hint_y=None, height=dp(50))
            b.bind(on_release=lambda _b, s=step: self.manual_fire(s))
            self.manual_buttons[step] = b
            self.manual_box.add_widget(b)
        self.add_widget(self.manual_box)

        # -- primary action -------------------------------------------------
        self.primary = PillButton(text="INICIAR", size_hint_y=None,
                                  height=dp(64), font_size=sp(18),
                                  radius=dp(18))
        self.primary.bind(on_release=lambda *_: self.on_primary())
        self.add_widget(self.primary)

        self.set_mode(MODE_AUTO)

    # -- helpers ---------------------------------------------------------
    def s(self, k):
        return float(self.app.store.get(k))

    def rand_gap(self, base):
        lo, hi = self.s(base + "_min"), self.s(base + "_max")
        if hi < lo:
            lo, hi = hi, lo
        return random.uniform(lo, hi)

    def after(self, delay, fn):
        ev = Clock.schedule_once(lambda _dt: fn(), delay)
        self._timers.append(ev)
        return ev

    def clear_timers(self):
        for ev in self._timers:
            try:
                ev.cancel()
            except Exception:
                pass
        self._timers = []

    def refresh_preview(self):
        self.preview.clear_widgets()
        self.preview.add_widget(Widget())
        items = [
            ("Árbitro", False),
            ("%g-%gs" % (self.s("g1_min"), self.s("g1_max")), False),
            ("5 pitidos", False),
            ("%g-%gs" % (self.s("g2_min"), self.s("g2_max")), False),
            ("Marcas", False),
            ("%g-%gs" % (self.s("g3_min"), self.s("g3_max")), True),
            ("SALIDA", True),
        ]
        if self.mode == MODE_MANUAL:
            items = [("Tú controlas cada orden", True)]
        for text, accent in items:
            self.preview.add_widget(Chip(text=text, accent=accent))
        self.preview.add_widget(Widget())

    # -- mode ------------------------------------------------------------
    def set_mode(self, mode):
        if self.running:
            return
        self.mode = mode
        for m, b in self.mode_buttons.items():
            active = (m == mode)
            b.filled = active
            b.fill_color = list(CYAN)
            b.text_color = list(SLATE_DARK if active else CYAN)
            b._sync_col()
        self.mode_hint.text = MODE_META[mode][1]
        self.refresh_preview()
        self.reset(soft=True)

    # -- reset -------------------------------------------------------------
    def reset(self, soft=False):
        self.clear_timers()
        self.app.audio.stop_all()
        self.running = False
        self.armed = False
        self.t_signal = None
        self.manual_step = STEP_ARBITRO
        self.app.set_tint(T.SKY)

        if self.mode == MODE_MANUAL:
            self.manual_box.height = dp(4 * 50 + 3 * 8)
            self.manual_box.opacity = 1
            self.primary.text = "REINICIAR SECUENCIA"
            self.badge.text = "MODO MANUAL"
            self.big.text = "Dirige\nla salida"
            self.big.font_size = sp(30)
            self.sub.text = "Pulsa cada orden cuando quieras darla."
            self.refresh_manual_buttons()
        else:
            self.manual_box.height = 0
            self.manual_box.opacity = 0
            self.primary.text = "INICIAR"
            self.primary.disabled_look = False
            self.badge.text = "LISTO PARA EMPEZAR"
            self.big.text = ("Entrenador\nde Salidas" if soft
                             else "Listo para\notra salida")
            self.big.font_size = sp(34)
            self.sub.text = (
                "Toca la pantalla en cuanto suene la señal."
                if self.mode == MODE_REACT else
                "Escucha la secuencia completa y sal con la señal."
            )
        self.badge.color = CYAN

    # -- primary button ----------------------------------------------------
    def on_primary(self):
        if self.mode == MODE_MANUAL:
            self.reset()
            return
        if self.running:
            self.reset()
            return
        self.start_auto()

    # -- automatic sequence -------------------------------------------------
    def start_auto(self):
        self.clear_timers()
        self.running = True
        self.armed = False
        self.t_signal = None
        self.primary.text = "DETENER"
        self.primary.filled = False
        self.primary.fill_color = list(ROSE)
        self.primary._sync_col()
        self.badge.text = "PREPARADOS"
        self.badge.color = CYAN
        self.big.text = "Preparados…"
        self.big.font_size = sp(30)
        self.sub.text = ("No toques todavía." if self.mode == MODE_REACT
                         else "")
        self.app.set_tint(T.SKY)
        self.after(self.rand_gap("pre"), self.step_arbitro)

    def step_arbitro(self):
        if not self.running:
            return
        self.show_step(STEP_ARBITRO)
        self.app.audio.play("arbitro")
        self.after(DUR_ARBITRO + self.rand_gap("g1"), self.step_silbatos)

    def step_silbatos(self):
        if not self.running:
            return
        self.show_step(STEP_SILBATOS)
        self.app.audio.play("silbatos")
        self.after(DUR_BEEPS + self.rand_gap("g2"), self.step_marcas)

    def step_marcas(self):
        if not self.running:
            return
        self.show_step(STEP_MARCAS)
        self.app.audio.play("marcas")
        self.after(DUR_MARCAS + self.rand_gap("g3"), self.step_salida)

    def step_salida(self):
        if not self.running:
            return
        self.fire_start_signal()
        if self.mode == MODE_REACT:
            # wait for the tap; give up after a while
            self.after(6.0, self.timeout_react)
        else:
            self.after(2.0, self.finish_auto)

    def timeout_react(self):
        if self.armed:
            self.armed = False
            self.running = False
            self.badge.text = "SIN REGISTRO"
            self.badge.color = AMBER
            self.big.text = "No hubo\ntoque"
            self.big.font_size = sp(30)
            self.sub.text = "Pulsa INICIAR para intentarlo de nuevo."
            self.restore_primary()

    def finish_auto(self):
        self.running = False
        self.badge.text = "SECUENCIA COMPLETA"
        self.badge.color = CYAN
        self.big.text = "¡Buena\nsalida!"
        self.big.font_size = sp(32)
        self.sub.text = "Pulsa INICIAR para repetir."
        self.app.set_tint(T.SKY)
        self.restore_primary()

    def restore_primary(self):
        self.primary.text = "INICIAR"
        self.primary.filled = True
        self.primary.fill_color = list(CYAN)
        self.primary.text_color = list(SLATE_DARK)
        self.primary._sync_col()

    def show_step(self, step):
        self.badge.text = "EN CURSO"
        self.badge.color = CYAN
        self.big.text = STEP_TEXT[step]
        self.big.font_size = sp(30 if step != STEP_SALIDA else 46)

    def fire_start_signal(self):
        self.app.audio.play("salida")
        self.t_signal = time.perf_counter()
        self.armed = (self.mode == MODE_REACT)
        self.badge.text = "¡FUERA!"
        self.badge.color = EMERALD
        self.big.text = "¡SALIDA!"
        self.big.font_size = sp(48)
        self.sub.text = ("¡TOCA LA PANTALLA!" if self.mode == MODE_REACT
                         else "")
        self.app.set_tint(T.EMERALD, 0.22)
        self.ring.fire()

    # -- manual mode --------------------------------------------------------
    def refresh_manual_buttons(self):
        for step, b in self.manual_buttons.items():
            is_next = (step == self.manual_step)
            done = step < self.manual_step
            b.disabled_look = False
            if step == STEP_SALIDA:
                b.filled = is_next
                b.fill_color = list(EMERALD)
                b.text_color = list(SLATE_DARK)
            else:
                b.filled = is_next
                b.fill_color = list(CYAN)
                b.text_color = list(SLATE_DARK)
            if done:
                b.filled = False
                b.fill_color = list(hx(EMERALD, 1))
            b._sync_col()

    def manual_fire(self, step):
        # allow firing any step, but advance the highlight naturally
        key = {STEP_ARBITRO: "arbitro", STEP_SILBATOS: "silbatos",
               STEP_MARCAS: "marcas", STEP_SALIDA: "salida"}[step]
        self.app.audio.play(key)
        if step == STEP_SALIDA:
            self.badge.text = "¡FUERA!"
            self.badge.color = EMERALD
            self.big.text = "¡SALIDA!"
            self.big.font_size = sp(46)
            self.sub.text = "Pulsa REINICIAR para otra salida."
            self.app.set_tint(T.EMERALD, 0.22)
            self.ring.fire()
            self.manual_step = STEP_ARBITRO
        else:
            self.badge.text = "MODO MANUAL"
            self.badge.color = CYAN
            self.big.text = STEP_TEXT[step]
            self.big.font_size = sp(28)
            self.sub.text = "Pulsa la siguiente orden cuando estés listo."
            self.manual_step = step + 1
        self.refresh_manual_buttons()

    # -- taps (reaction mode) ------------------------------------------------
    def handle_tap(self):
        """Called by the app when the user taps the stage area."""
        if self.mode != MODE_REACT:
            return False
        if self.armed and self.t_signal is not None:
            ms = (time.perf_counter() - self.t_signal) * 1000.0
            self.armed = False
            self.running = False
            self.clear_timers()
            self.record(ms)
            return True
        if self.running:
            self.false_start()
            return True
        return False

    def record(self, ms):
        self.app.store.add_time(ms)
        label, color = grade_for(ms)
        self.badge.text = "TU REACCIÓN"
        self.badge.color = TEXT_FAINT
        self.big.text = fmt_ms(ms)
        self.big.font_size = sp(50)
        best = self.app.store.best()
        is_best = best is not None and abs(ms - best) < 0.51
        self.sub.text = ("%s%s" % (label, "  ·  ¡NUEVO RÉCORD!" if is_best
                                   else ""))
        self.sub.color = color
        self.app.set_tint(color, 0.18)
        self.restore_primary()
        self.app.refresh_history()

    def false_start(self):
        self.clear_timers()
        self.app.audio.stop_all()
        self.running = False
        self.armed = False
        self.badge.text = "DESCALIFICADO"
        self.badge.color = ROSE
        self.big.text = "SALIDA\nEN FALSO"
        self.big.font_size = sp(38)
        self.sub.text = "Saliste antes de la señal."
        self.sub.color = ROSE
        self.app.set_tint(T.ROSE, 0.22)
        self.restore_primary()


# ======================================================================
#  History screen
# ======================================================================
class HistoryScreen(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", spacing=dp(12), **kw)
        self.app = app

        self.stats = BoxLayout(size_hint_y=None, height=dp(84), spacing=dp(10))
        self.stat_widgets = {}
        for key, title in (("best", "MEJOR"), ("avg", "PROMEDIO"),
                           ("n", "INTENTOS")):
            card = Card(orientation="vertical", padding=dp(10))
            value = lbl("--", size=21, color=CYAN, bold=True, halign="center")
            name = lbl(title, size=10, color=TEXT_FAINT, halign="center",
                       size_hint_y=None, height=dp(14))
            card.add_widget(value)
            card.add_widget(name)
            self.stat_widgets[key] = value
            self.stats.add_widget(card)
        self.add_widget(self.stats)

        self.add_widget(lbl("HISTORIAL", size=11, color=TEXT_FAINT, bold=True,
                            size_hint_y=None, height=dp(18)))

        self.scroll = ScrollView(bar_width=dp(2))
        self.list_box = BoxLayout(orientation="vertical", spacing=dp(7),
                                  size_hint_y=None, padding=(0, 0, 0, dp(6)))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        self.add_widget(self.scroll)

        clear = PillButton(text="BORRAR HISTORIAL", filled=False,
                           fill_color=list(ROSE), size_hint_y=None,
                           height=dp(46), font_size=sp(13))
        clear.bind(on_release=lambda *_: self.clear())
        self.add_widget(clear)
        self.refresh()

    def clear(self):
        self.app.store.clear_history()
        self.refresh()

    def refresh(self):
        st = self.app.store
        self.stat_widgets["best"].text = fmt_ms(st.best())
        self.stat_widgets["avg"].text = fmt_ms(st.average())
        self.stat_widgets["n"].text = str(st.count())

        self.list_box.clear_widgets()
        if not st.history:
            empty = lbl("Aún no hay tiempos.\nUsa el modo REACCIÓN para "
                        "registrar tu primera salida.",
                        size=13, color=TEXT_FAINT, halign="center",
                        size_hint_y=None, height=dp(60))
            self.list_box.add_widget(empty)
            return

        best = st.best()
        for i, h in enumerate(st.history[:40]):
            ms = h["ms"]
            label, color = grade_for(ms)
            row = Card(orientation="horizontal", size_hint_y=None,
                       height=dp(50), padding=(dp(12), 0), spacing=dp(8))
            n = lbl("#%d" % (st.count() - i), size=12, color=TEXT_FAINT,
                    size_hint_x=None, width=dp(42))
            t = lbl(fmt_ms(ms), size=17, color=TEXT, bold=True)
            g = lbl(label, size=11, color=color, bold=True, halign="right")
            row.add_widget(n)
            row.add_widget(t)
            if best is not None and abs(ms - best) < 0.51:
                row.add_widget(lbl("RÉCORD", size=10, color=AMBER, bold=True,
                                   halign="right", size_hint_x=None,
                                   width=dp(58)))
                row.border = list(hx(AMBER, 0.45))
                row._sync_col()
            row.add_widget(g)
            self.list_box.add_widget(row)


# ======================================================================
#  Settings screen
# ======================================================================
class SettingsScreen(ScrollView):
    def __init__(self, app, **kw):
        super().__init__(bar_width=dp(2), **kw)
        self.app = app
        self.box = BoxLayout(orientation="vertical", spacing=dp(12),
                             size_hint_y=None, padding=(0, 0, dp(4), dp(10)))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.add_widget(self.box)
        self.build()

    def build(self):
        self.box.clear_widgets()
        self.box.add_widget(lbl(
            "Cada pausa se sortea al azar dentro del rango que definas. "
            "Un rango amplio hace la salida menos previsible.",
            size=12, color=TEXT_FAINT, size_hint_y=None, height=dp(46)))

        for base, title, hint in RANGE_FIELDS:
            self.box.add_widget(self.range_card(base, title, hint))

        self.box.add_widget(lbl("VOLUMEN", size=11, color=TEXT_FAINT,
                                bold=True, size_hint_y=None, height=dp(20)))
        for key, title in (("vol_voice", "Voz del árbitro"),
                           ("vol_whistle", "Pitidos del árbitro"),
                           ("vol_start", "Señal de salida")):
            self.box.add_widget(self.volume_card(key, title))

        reset = PillButton(text="RESTABLECER VALORES", filled=False,
                           fill_color=list(AMBER), size_hint_y=None,
                           height=dp(46), font_size=sp(13))
        reset.bind(on_release=lambda *_: self.reset())
        self.box.add_widget(reset)

    def reset(self):
        self.app.store.reset_settings()
        self.build()
        self.app.train.refresh_preview()

    def range_card(self, base, title, hint):
        card = Card(orientation="vertical", size_hint_y=None, height=dp(150),
                    padding=dp(14), spacing=dp(2))
        head = BoxLayout(size_hint_y=None, height=dp(22))
        head.add_widget(lbl(title, size=14, color=TEXT, bold=True))
        value = lbl("", size=13, color=CYAN, bold=True, halign="right",
                    size_hint_x=None, width=dp(110))
        head.add_widget(value)
        card.add_widget(head)
        card.add_widget(lbl(hint, size=11, color=TEXT_FAINT,
                            size_hint_y=None, height=dp(16)))

        sliders = {}

        def show():
            value.text = "%g – %g s" % (self.app.store.get(base + "_min"),
                                        self.app.store.get(base + "_max"))
            # the store clamps min<=max, so pull both knobs back in sync
            for sfx, widget in sliders.items():
                stored = float(self.app.store.get(base + sfx))
                if abs(widget.value - stored) > 1e-9:
                    widget.value = stored
        show()

        for suffix, cap in (("_min", "mín"), ("_max", "máx")):
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            row.add_widget(lbl(cap, size=11, color=TEXT_FAINT,
                               size_hint_x=None, width=dp(28)))
            sl = Slider2(min=0.5, max=15.0, step=0.5)
            sl.value = float(self.app.store.get(base + suffix))
            sliders[suffix] = sl

            def changed(v, key=base + suffix):
                self.app.store.set(key, v)
                show()
                self.app.train.refresh_preview()

            sl._on_change = changed
            row.add_widget(sl)
            card.add_widget(row)
        return card

    def volume_card(self, key, title):
        card = Card(orientation="vertical", size_hint_y=None, height=dp(84),
                    padding=dp(14), spacing=dp(2))
        head = BoxLayout(size_hint_y=None, height=dp(22))
        head.add_widget(lbl(title, size=13, color=TEXT, bold=True))
        value = lbl("", size=12, color=CYAN, bold=True, halign="right",
                    size_hint_x=None, width=dp(60))
        head.add_widget(value)
        card.add_widget(head)

        def show():
            value.text = "%d%%" % round(self.app.store.get(key) * 100)
        show()

        sl = Slider2(min=0.0, max=1.0, step=0.05)
        sl.value = float(self.app.store.get(key))

        def changed(v, k=key):
            self.app.store.set(k, v)
            show()

        sl._on_change = changed
        card.add_widget(sl)
        return card


# ======================================================================
#  Root
# ======================================================================
class Root(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.bg = WaterBackground()
        self.add_widget(self.bg)

        col = BoxLayout(orientation="vertical", padding=(dp(16), dp(18)),
                        spacing=dp(10))

        # header
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        mark = Card(size_hint=(None, None), size=(dp(42), dp(42)),
                    radius=dp(13))
        mark.bg = list(hx(CYAN, 0.14))
        mark.border = list(hx(CYAN, 0.32))
        mark._sync_col()
        mark.add_widget(lbl("~", size=24, color=CYAN, bold=True,
                            halign="center"))
        header.add_widget(mark)
        titles = BoxLayout(orientation="vertical")
        titles.add_widget(lbl("Entrenador de Salidas", size=19, color=TEXT,
                              bold=True))
        titles.add_widget(lbl("Reflejos de salida · natación", size=11,
                              color=TEXT_FAINT))
        header.add_widget(titles)
        col.add_widget(header)

        # screens
        self.body = BoxLayout()
        col.add_widget(self.body)

        # bottom tabs
        self.tabs = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        self.tab_buttons = {}
        for key, name in (("train", "ENTRENAR"), ("history", "TIEMPOS"),
                          ("settings", "AJUSTES")):
            b = PillButton(text=name, font_size=sp(12), radius=dp(15))
            b.bind(on_release=lambda _b, k=key: self.app.show(k))
            self.tab_buttons[key] = b
            self.tabs.add_widget(b)
        col.add_widget(self.tabs)

        self.add_widget(col)

    def on_touch_down(self, touch):
        # In reaction mode a tap anywhere on the stage counts, so intercept
        # before the buttons only while a run is actually in progress.
        tr = self.app.train
        if self.app.current == "train" and tr.mode == MODE_REACT:
            if tr.armed or tr.running:
                blocked = (tr.primary.collide_point(*touch.pos)
                           or self.tabs.collide_point(*touch.pos))
                if not blocked and tr.handle_tap():
                    return True
        return super().on_touch_down(touch)


class SwimStartApp(App):
    title = "Entrenador de Salidas"

    def build(self):
        Window.clearcolor = T.BG_DEEP
        self.store = Store(self.user_data_dir)
        self.audio = Audio(self.store)
        self.current = "train"

        self.root_widget = Root(self)
        self.train = TrainScreen(self)
        self.history = HistoryScreen(self)
        self.settings = SettingsScreen(self)
        self.screens = {"train": self.train, "history": self.history,
                        "settings": self.settings}
        self.show("train")
        return self.root_widget

    def show(self, key):
        if key not in self.screens:
            return
        self.current = key
        self.root_widget.body.clear_widgets()
        self.root_widget.body.add_widget(self.screens[key])
        for k, b in self.root_widget.tab_buttons.items():
            active = (k == key)
            b.filled = active
            b.fill_color = list(CYAN)
            b.text_color = list(SLATE_DARK if active else CYAN)
            b._sync_col()
        if key == "history":
            self.history.refresh()

    def refresh_history(self):
        self.history.refresh()

    def set_tint(self, rgba, alpha=0.12):
        self.root_widget.bg.set_tint(rgba, alpha)

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    SwimStartApp().run()
