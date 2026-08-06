"""
Visual language for the trainer: deep-water slate, cyan accents, lane lines.

Kivy ships with fairly plain widgets, so this module provides the small set of
custom-drawn pieces the app needs to feel like a piece of pool-deck equipment
rather than a default toolkit form.
"""

from kivy.graphics import (
    Color, Rectangle, RoundedRectangle, Line, Ellipse,
)
from kivy.metrics import dp, sp
from kivy.properties import (
    ListProperty, NumericProperty, StringProperty, BooleanProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock

# ---- Palette (slate / cyan, mirrors the web mock) ---------------------
BG_DEEP = (0.020, 0.031, 0.063, 1)      # slate-950
BG_PANEL = (1, 1, 1, 0.04)
BG_PANEL_SOLID = (0.058, 0.078, 0.129, 1)
BORDER = (1, 1, 1, 0.10)
BORDER_CYAN = (0.133, 0.827, 0.933, 0.35)

CYAN = (0.133, 0.827, 0.933, 1)         # #22d3ee
CYAN_DIM = (0.133, 0.827, 0.933, 0.16)
SKY = (0.22, 0.60, 0.90, 1)

TEXT = (1, 1, 1, 1)
TEXT_MUTED = (1, 1, 1, 0.55)
TEXT_FAINT = (1, 1, 1, 0.34)

EMERALD = (0.20, 0.83, 0.60, 1)
AMBER = (0.98, 0.75, 0.29, 1)
ROSE = (0.96, 0.44, 0.48, 1)
VIOLET = (0.65, 0.55, 0.98, 1)
SLATE_DARK = (0.02, 0.03, 0.06, 1)


def hx(c, a=None):
    """Return colour tuple with an overridden alpha."""
    return (c[0], c[1], c[2], a if a is not None else c[3])


class WaterBackground(FloatLayout):
    """Deep-water backdrop: gradient wash, lane lines, and a drifting shimmer."""

    tint = ListProperty(list(SKY))

    def __init__(self, **kw):
        super().__init__(**kw)
        self._shimmer_x = 0.0
        with self.canvas.before:
            self._bg_col = Color(*BG_DEEP)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            # broad colour wash top-left
            self._tint_col = Color(*hx(SKY, 0.10))
            self._tint_rect = Ellipse(pos=(0, 0), size=(10, 10))
            # secondary wash bottom-right
            self._tint2_col = Color(*hx(CYAN, 0.06))
            self._tint2_rect = Ellipse(pos=(0, 0), size=(10, 10))
            # lane lines
            self._lane_col = Color(1, 1, 1, 0.05)
            self._lanes = [Line(points=[], width=1) for _ in range(9)]
            # shimmer sweep
            self._shim_col = Color(*hx(CYAN, 0.05))
            self._shim = Rectangle(pos=(0, 0), size=(0, 0))
        self.bind(pos=self._redraw, size=self._redraw)
        Clock.schedule_interval(self._animate_shimmer, 1 / 30.0)

    def set_tint(self, rgba, alpha=0.14):
        anim = Animation(rgba=[rgba[0], rgba[1], rgba[2], alpha], d=0.35)
        anim.start(self._tint_col)

    def _animate_shimmer(self, dt):
        self._shimmer_x += dt * 0.12
        if self._shimmer_x > 1.6:
            self._shimmer_x = -0.6
        w, h = self.size
        self._shim.pos = (self.x + self._shimmer_x * w, self.y + h * 0.42)
        self._shim.size = (w * 0.5, h * 0.16)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        w, h = self.size
        d1 = max(w, h) * 1.1
        self._tint_rect.pos = (self.x - d1 * 0.45, self.y + h - d1 * 0.55)
        self._tint_rect.size = (d1, d1)
        d2 = max(w, h) * 0.95
        self._tint2_rect.pos = (self.x + w - d2 * 0.55, self.y - d2 * 0.45)
        self._tint2_rect.size = (d2, d2)
        for i, ln in enumerate(self._lanes):
            y = self.y + h * (i + 1) / 10.0
            ln.points = [self.x, y, self.x + w, y]


class Card(BoxLayout):
    """Rounded translucent panel with a hairline border."""

    radius = NumericProperty(dp(16))
    bg = ListProperty(list(BG_PANEL))
    border = ListProperty(list(BORDER))

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*self.bg)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[self.radius])
            self._bc = Color(*self.border)
            self._bl = Line(rounded_rectangle=(0, 0, 1, 1, self.radius),
                            width=1.0)
        self.bind(pos=self._sync, size=self._sync, bg=self._sync_col,
                  border=self._sync_col, radius=self._sync)

    def _sync_col(self, *a):
        self._c.rgba = self.bg
        self._bc.rgba = self.border

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [self.radius]
        self._bl.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, self.radius)


class PillButton(ButtonBehavior, BoxLayout):
    """Filled or outlined rounded button with a press response."""

    text = StringProperty("")
    filled = BooleanProperty(True)
    fill_color = ListProperty(list(CYAN))
    text_color = ListProperty(list(SLATE_DARK))
    radius = NumericProperty(dp(16))
    font_size = NumericProperty(sp(17))
    bold = BooleanProperty(True)
    disabled_look = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*self.fill_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[self.radius])
            self._bc = Color(*hx(CYAN, 0.0))
            self._bl = Line(rounded_rectangle=(0, 0, 1, 1, self.radius),
                            width=1.2)
        self._label = Label(text=self.text, bold=self.bold,
                            font_size=self.font_size, color=self.text_color,
                            halign="center", valign="middle")
        self._label.bind(size=lambda *_: setattr(
            self._label, "text_size", self._label.size))
        self.add_widget(self._label)
        self.bind(pos=self._sync, size=self._sync, text=self._sync_text,
                  fill_color=self._sync_col, text_color=self._sync_text,
                  filled=self._sync_col, disabled_look=self._sync_col,
                  font_size=self._sync_text)
        self._sync_col()

    def _sync_text(self, *a):
        self._label.text = self.text
        self._label.color = self.text_color
        self._label.font_size = self.font_size

    def _sync_col(self, *a):
        if self.disabled_look:
            self._c.rgba = (1, 1, 1, 0.05)
            self._bc.rgba = (1, 1, 1, 0.10)
            self._label.color = (1, 1, 1, 0.28)
        elif self.filled:
            self._c.rgba = self.fill_color
            self._bc.rgba = (0, 0, 0, 0)
            self._label.color = self.text_color
        else:
            self._c.rgba = (1, 1, 1, 0.05)
            self._bc.rgba = hx(self.fill_color, 0.45)
            self._label.color = self.fill_color

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [self.radius]
        self._bl.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, self.radius)

    def on_press(self):
        if not self.disabled_look:
            Animation(opacity=0.72, d=0.05).start(self)

    def on_release(self):
        Animation(opacity=1.0, d=0.12).start(self)


class Chip(BoxLayout):
    """Small rounded tag used for the sequence preview."""

    def __init__(self, text="", accent=False, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.height = dp(26)
        col = CYAN if accent else (1, 1, 1, 0.55)
        with self.canvas.before:
            self._c = Color(*(hx(CYAN, 0.14) if accent else (1, 1, 1, 0.05)))
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(13)])
            self._bc = Color(*(hx(CYAN, 0.30) if accent else (1, 1, 1, 0.10)))
            self._bl = Line(rounded_rectangle=(0, 0, 1, 1, dp(13)), width=1.0)
        self._label = Label(text=text, font_size=sp(11), color=col,
                            halign="center", valign="middle")
        self._label.bind(texture_size=self._fit)
        self.add_widget(self._label)
        self.bind(pos=self._sync, size=self._sync)

    def set_text(self, t):
        self._label.text = t

    def _fit(self, inst, ts):
        self.width = ts[0] + dp(20)
        inst.text_size = (None, None)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._bl.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, dp(13))


class Slider2(Widget):
    """
    Minimal cyan slider. Kivy's stock slider ignores styling, so this draws a
    track, a filled portion, and a glowing knob, and reports value changes.
    """

    min = NumericProperty(0.0)
    max = NumericProperty(10.0)
    value = NumericProperty(1.0)
    step = NumericProperty(0.5)

    def __init__(self, on_change=None, **kw):
        super().__init__(**kw)
        self._on_change = on_change
        self.size_hint_y = None
        self.height = dp(34)
        with self.canvas:
            self._track_c = Color(1, 1, 1, 0.10)
            self._track = RoundedRectangle(radius=[dp(3)])
            self._fill_c = Color(*hx(CYAN, 0.55))
            self._fill = RoundedRectangle(radius=[dp(3)])
            self._glow_c = Color(*hx(CYAN, 0.22))
            self._glow = Ellipse()
            self._knob_c = Color(*CYAN)
            self._knob = Ellipse()
        self.bind(pos=self._sync, size=self._sync, value=self._sync,
                  min=self._sync, max=self._sync)

    def _ratio(self):
        span = max(1e-6, self.max - self.min)
        return min(1.0, max(0.0, (self.value - self.min) / span))

    def _sync(self, *a):
        h = dp(6)
        cy = self.center_y
        self._track.pos = (self.x, cy - h / 2)
        self._track.size = (self.width, h)
        r = self._ratio()
        self._fill.pos = (self.x, cy - h / 2)
        self._fill.size = (self.width * r, h)
        k = dp(20)
        kx = self.x + self.width * r - k / 2
        self._knob.pos = (kx, cy - k / 2)
        self._knob.size = (k, k)
        g = dp(34)
        self._glow.pos = (self.x + self.width * r - g / 2, cy - g / 2)
        self._glow.size = (g, g)

    def _set_from_touch(self, x):
        r = min(1.0, max(0.0, (x - self.x) / max(1.0, self.width)))
        raw = self.min + r * (self.max - self.min)
        if self.step:
            raw = round(raw / self.step) * self.step
        raw = min(self.max, max(self.min, raw))
        if abs(raw - self.value) > 1e-9:
            self.value = raw
            if self._on_change:
                self._on_change(raw)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._set_from_touch(touch.x)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._set_from_touch(touch.x)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)


class PulseRing(Widget):
    """Expanding ring, shown the moment the start signal fires."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (dp(160), dp(160))
        self.opacity = 0
        with self.canvas:
            self._c = Color(1, 1, 1, 0.0)
            self._e = Line(circle=(0, 0, 1), width=dp(2))
        self._t = 0.0
        self._running = False
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._e.circle = (self.center_x, self.center_y,
                          max(1.0, self._t * self.width * 0.5))

    def fire(self):
        self.opacity = 1
        self._t = 0.35
        if not self._running:
            self._running = True
            Clock.schedule_interval(self._step, 1 / 45.0)

    def _step(self, dt):
        self._t += dt * 1.6
        a = max(0.0, 0.65 * (1.0 - (self._t - 0.35) / 1.5))
        self._c.rgba = (1, 1, 1, a)
        self._sync()
        if a <= 0.001:
            self._running = False
            self.opacity = 0
            return False
