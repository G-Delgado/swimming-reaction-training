/* Entrenador de Salidas — web / PWA version
 *
 * Mirrors the Android app feature-for-feature:
 *   AUTO      full sequence, randomised gaps
 *   MANUAL    coach fires each command
 *   TOQUE     measures how fast you tap after the start signal
 *   CÁMARA    measures how fast you physically move, via the camera
 *
 * The beeps and the start horn are synthesised with the Web Audio API
 * rather than played from files. That matters for the reaction mode: we know
 * the exact audio-clock time the horn begins, so the measurement isn't
 * polluted by file decode or <audio> element latency.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------- config
  var DEFAULTS = {
    pre_min: 1.0, pre_max: 2.5,
    g1_min: 1.0, g1_max: 3.0,
    g2_min: 1.0, g2_max: 3.0,
    g3_min: 1.0, g3_max: 8.0,
    vol_voice: 1.0, vol_whistle: 1.0, vol_start: 1.0,
    cam_sens: 1.0
  };

  var RANGE_FIELDS = [
    ["pre", "Antes de empezar", "Pausa inicial tras pulsar Iniciar"],
    ["g1", "Tras «a órdenes del árbitro»", "Hasta los cinco pitidos"],
    ["g2", "Tras los cinco pitidos", "Hasta «En sus marcas»"],
    ["g3", "Tras «En sus marcas»", "Hasta la señal de salida"]
  ];

  var VOLUME_FIELDS = [
    ["vol_voice", "Voz del árbitro"],
    ["vol_whistle", "Pitidos del árbitro"],
    ["vol_start", "Señal de salida"]
  ];

  var GRADES = [
    [180, "RELÁMPAGO", "var(--violet)"],
    [230, "EXCELENTE", "var(--emerald)"],
    [300, "MUY BUENO", "var(--emerald)"],
    [380, "BUENO", "var(--cyan)"],
    [480, "PROMEDIO", "var(--amber)"],
    [Infinity, "LENTO", "var(--rose)"]
  ];

  function gradeFor(ms) {
    for (var i = 0; i < GRADES.length; i++) {
      if (ms < GRADES[i][0]) return { label: GRADES[i][1], color: GRADES[i][2] };
    }
    return { label: "LENTO", color: "var(--rose)" };
  }

  function fmtMs(ms) {
    if (ms === null || ms === undefined || isNaN(ms)) return "--";
    return ms < 1000 ? Math.round(ms) + " ms" : (ms / 1000).toFixed(2) + " s";
  }

  // ---------------------------------------------------------------- store
  var SKEY = "salidas.settings", HKEY = "salidas.history";

  var store = {
    settings: Object.assign({}, DEFAULTS),
    history: [],

    load: function () {
      try {
        var s = JSON.parse(localStorage.getItem(SKEY) || "{}");
        for (var k in DEFAULTS) {
          if (typeof s[k] === "number" && isFinite(s[k])) this.settings[k] = s[k];
        }
      } catch (e) { /* defaults */ }
      try {
        var h = JSON.parse(localStorage.getItem(HKEY) || "[]");
        if (Array.isArray(h)) this.history = h.slice(0, 100);
      } catch (e) { this.history = []; }
    },
    saveSettings: function () {
      try { localStorage.setItem(SKEY, JSON.stringify(this.settings)); } catch (e) {}
    },
    get: function (k) { return this.settings[k]; },
    set: function (k, v) {
      this.settings[k] = v;
      // keep min <= max within a pair
      var m = /^(.*)_(min|max)$/.exec(k);
      if (m) {
        var lo = this.settings[m[1] + "_min"], hi = this.settings[m[1] + "_max"];
        if (lo > hi) {
          if (m[2] === "min") this.settings[m[1] + "_max"] = lo;
          else this.settings[m[1] + "_min"] = hi;
        }
      }
      this.saveSettings();
    },
    resetSettings: function () {
      this.settings = Object.assign({}, DEFAULTS);
      this.saveSettings();
    },
    addTime: function (ms) {
      this.history.unshift({ ms: Math.round(ms * 10) / 10, grade: gradeFor(ms).label });
      this.history = this.history.slice(0, 100);
      try { localStorage.setItem(HKEY, JSON.stringify(this.history)); } catch (e) {}
    },
    clearHistory: function () {
      this.history = [];
      try { localStorage.setItem(HKEY, "[]"); } catch (e) {}
    },
    best: function () {
      return this.history.length
        ? this.history.reduce(function (a, h) { return Math.min(a, h.ms); }, Infinity)
        : null;
    },
    average: function () {
      if (!this.history.length) return null;
      var s = this.history.reduce(function (a, h) { return a + h.ms; }, 0);
      return s / this.history.length;
    }
  };

  // ---------------------------------------------------------------- audio
  var audio = {
    ctx: null,
    buffers: {},
    raw: {},          // downloaded bytes, held until a context exists to decode with

    // Download the voice files immediately on page load. Fetching needs no
    // user gesture — only playback does — so by the time anyone presses
    // INICIAR the bytes are already here and the first run has sound.
    prefetch: function () {
      var self = this;
      var canOgg = (function () {
        var a = document.createElement("audio");
        return !!(a.canPlayType && a.canPlayType('audio/ogg; codecs="vorbis"'));
      })();
      var ext = canOgg ? "ogg" : "m4a";
      ["v_arbitro", "v_marcas"].forEach(function (name) {
        fetch("audio/" + name + "." + ext)
          .then(function (r) { return r.arrayBuffer(); })
          .then(function (buf) {
            self.raw[name] = buf;
            if (self.ctx) self.decode(name);
          })
          .catch(function () { /* stay silent rather than block the sequence */ });
      });
    },

    decode: function (name) {
      var self = this;
      if (!this.ctx || !this.raw[name] || this.buffers[name]) return;
      var bytes = this.raw[name];
      this.raw[name] = null;
      try {
        var p = this.ctx.decodeAudioData(
          bytes,
          function (d) { self.buffers[name] = d; },
          function () {}
        );
        if (p && p.then) p.then(function (d) { self.buffers[name] = d; }, function () {});
      } catch (e) { /* ignore */ }
    },

    init: function () {
      if (this.ctx) return this.ctx;
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      this.ctx = new AC();
      var self = this;
      Object.keys(this.raw).forEach(function (n) { self.decode(n); });
      return this.ctx;
    },

    // iOS suspends the context unless resumed from a user gesture
    unlock: function () {
      var ctx = this.init();
      if (ctx && ctx.state === "suspended") ctx.resume();
      var self = this;
      Object.keys(this.raw).forEach(function (n) { self.decode(n); });
      return ctx;
    },

    gain: function (vol, when) {
      var g = this.ctx.createGain();
      g.gain.setValueAtTime(Math.max(0.0001, vol), when);
      g.connect(this.ctx.destination);
      return g;
    },

    playVoice: function (name) {
      var ctx = this.unlock();
      if (!ctx || !this.buffers[name]) return 0;
      var when = ctx.currentTime + 0.02;
      var src = ctx.createBufferSource();
      src.buffer = this.buffers[name];
      src.connect(this.gain(store.get("vol_voice"), when));
      src.start(when);
      return this.buffers[name].duration;
    },

    /* One beep. `clear` gives the long fifth its purer, brighter character. */
    beep: function (when, dur, vol, f, clear) {
      var ctx = this.ctx;
      var out = this.gain(vol, when);

      var env = ctx.createGain();
      env.gain.setValueAtTime(0.0001, when);
      env.gain.exponentialRampToValueAtTime(1.0, when + (clear ? 0.006 : 0.004));
      env.gain.setValueAtTime(1.0, when + dur - (clear ? 0.07 : 0.018));
      env.gain.exponentialRampToValueAtTime(0.0001, when + dur);
      env.connect(out);

      // fewer/quieter harmonics on the fifth = reads as "clearer"
      var partials = clear
        ? [[1, 1.0], [2, 0.30], [3, 0.10]]
        : [[1, 1.0], [2, 0.55], [3, 0.22]];

      partials.forEach(function (h) {
        var o = ctx.createOscillator();
        o.type = "sine";
        o.frequency.setValueAtTime(f * h[0], when);
        var g = ctx.createGain();
        g.gain.setValueAtTime(h[1] * 0.5, when);
        o.connect(g); g.connect(env);
        o.start(when); o.stop(when + dur + 0.02);
      });
    },

    /* Referee: four fast beeps then a long, clearer fifth.
       Returns the total duration so the sequence can wait it out. */
    playBeeps: function () {
      var ctx = this.unlock();
      if (!ctx) return 0;
      var vol = store.get("vol_whistle");
      var t = ctx.currentTime + 0.03;
      var SHORT = 0.10, STEP = 0.30;
      for (var i = 0; i < 4; i++) {
        this.beep(t + i * STEP, SHORT, vol * 0.62, 1620, false);
      }
      this.beep(t + 4 * STEP + 0.16, 0.90, vol, 1980, true);
      return 2.26;
    },

    /* Start signal: hard, harmonically stacked, very fast attack */
    playStart: function () {
      var ctx = this.unlock();
      if (!ctx) return { at: performance.now(), dur: 0.62 };
      var vol = store.get("vol_start");
      var when = ctx.currentTime + 0.03;
      var dur = 0.62, f = 990;

      var out = this.gain(vol, when);
      var env = ctx.createGain();
      env.gain.setValueAtTime(0.0001, when);
      env.gain.exponentialRampToValueAtTime(1.0, when + 0.003);
      env.gain.setValueAtTime(1.0, when + dur - 0.06);
      env.gain.exponentialRampToValueAtTime(0.0001, when + dur);
      env.connect(out);

      [[1, 1.0], [2, 0.70], [3, 0.45], [4, 0.28], [5, 0.16]].forEach(function (h) {
        var o = ctx.createOscillator();
        o.type = "sine";
        o.frequency.setValueAtTime(f * h[0], when);
        var g = ctx.createGain();
        g.gain.setValueAtTime(h[1] * 0.34, when);
        o.connect(g); g.connect(env);
        o.start(when); o.stop(when + dur + 0.02);
      });

      // wall-clock instant the horn actually begins, for reaction timing
      var lead = (when - ctx.currentTime) * 1000;
      var latency = (ctx.outputLatency || ctx.baseLatency || 0) * 1000;
      return { at: performance.now() + lead + latency, dur: dur };
    },

    stopAll: function () {
      // Scheduled nodes are short; recreating the context is heavy-handed on
      // iOS, so we simply let queued one-shots finish. Sequence timers are
      // cancelled separately, which is what actually matters.
    }
  };

  // ------------------------------------------------------- camera detector
  /*
   * Detects the instant the swimmer moves, by frame-differencing the camera
   * feed. Deliberately not pose/ML detection: no model to download, runs on
   * any phone, and adds no inference delay — which is the whole point when
   * you're measuring a 200 ms event.
   *
   * Precision is bounded by the camera frame rate: ±1 frame, so ~17 ms at
   * 60 fps and ~33 ms at 30 fps. requestVideoFrameCallback is used where
   * available because it reports the true frame presentation time.
   */
  var W = 96, H = 72;

  var camera = {
    stream: null, video: null, cv: null, cx: null,
    prev: null, on: false,
    level: 0, baseline: 0, peak: 0,
    calibrating: false, samples: [],
    watch: null,          // callback fired when motion crosses the threshold
    _raf: null,

    supported: function () {
      return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    },

    start: function (onStatus) {
      var self = this;
      if (!this.supported()) {
        onStatus("Este navegador no permite usar la cámara", true);
        return Promise.reject();
      }
      this.video = $("camVideo");
      this.cv = document.createElement("canvas");
      this.cv.width = W; this.cv.height = H;
      this.cx = this.cv.getContext("2d", { willReadFrequently: true });

      return navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 640 }, height: { ideal: 480 },
          frameRate: { ideal: 60 }
        },
        audio: false
      }).then(function (s) {
        self.stream = s;
        self.video.srcObject = s;
        return self.video.play().catch(function () {});
      }).then(function () {
        self.on = true;
        self.prev = null;
        var t = self.stream.getVideoTracks()[0];
        var fps = (t && t.getSettings && t.getSettings().frameRate) || 30;
        onStatus("Cámara activa · " + Math.round(fps) + " fps · ±" +
                 Math.round(1000 / fps) + " ms", false);
        self.loop();
      }).catch(function (e) {
        var msg = "No se pudo abrir la cámara";
        if (e && e.name === "NotAllowedError") msg = "Permiso de cámara denegado";
        else if (e && e.name === "NotFoundError") msg = "No se encontró cámara";
        onStatus(msg, true);
        throw e;
      });
    },

    stop: function () {
      this.on = false;
      if (this._raf) { cancelAnimationFrame(this._raf); this._raf = null; }
      if (this.stream) {
        this.stream.getTracks().forEach(function (t) { t.stop(); });
        this.stream = null;
      }
      if (this.video) this.video.srcObject = null;
      this.prev = null; this.level = 0;
    },

    /* mean absolute luma difference against the previous frame, 0..1 */
    diff: function () {
      if (!this.video || this.video.readyState < 2) return 0;
      this.cx.drawImage(this.video, 0, 0, W, H);
      var d = this.cx.getImageData(0, 0, W, H).data;
      var n = W * H, cur = new Uint8Array(n), i, j, sum = 0;
      for (i = 0, j = 0; j < n; i += 4, j++) {
        cur[j] = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
      }
      if (this.prev) {
        for (j = 0; j < n; j++) {
          var a = cur[j] - this.prev[j];
          sum += a < 0 ? -a : a;
        }
      }
      this.prev = cur;
      return this.prev ? sum / n / 255 : 0;
    },

    onFrame: function (tMs) {
      if (!this.on) return;
      var v = this.diff();
      // light smoothing kills single-frame sensor noise without adding lag
      this.level = this.level * 0.35 + v * 0.65;

      if (this.calibrating) {
        this.samples.push(this.level);
        if (this.samples.length > 90) this.samples.shift();
      }
      if (this.watch) this.watch(this.level, tMs);
      if (window.__camTick) window.__camTick(this.level);
    },

    loop: function () {
      var self = this;
      if (this.video && this.video.requestVideoFrameCallback) {
        var step = function (now, meta) {
          if (!self.on) return;
          // true presentation time of this frame, mapped to performance.now()
          var t = (meta && meta.expectedDisplayTime) || now;
          self.onFrame(t);
          self.video.requestVideoFrameCallback(step);
        };
        this.video.requestVideoFrameCallback(step);
      } else {
        var tick = function (now) {
          if (!self.on) return;
          self.onFrame(now);
          self._raf = requestAnimationFrame(tick);
        };
        this._raf = requestAnimationFrame(tick);
      }
    },

    beginCalibration: function () {
      this.calibrating = true;
      this.samples = [];
    },

    /* Turn the quiet-period samples into a trigger level. */
    finishCalibration: function () {
      this.calibrating = false;
      var s = this.samples.slice().sort(function (a, b) { return a - b; });
      if (!s.length) { this.baseline = 0.004; this.peak = 0.01; }
      else {
        this.baseline = s[Math.floor(s.length * 0.5)] || 0.002;
        this.peak = s[s.length - 1] || this.baseline * 2;
      }
      var sens = store.get("cam_sens");        // 0.5 = twitchy, 3 = forgiving
      // must clear both the typical noise and the worst observed spike
      return Math.max(this.baseline * (2.2 * sens), this.peak * (1.35 * sens), 0.0045);
    }
  };

  // ---------------------------------------------------------------- state
  var MODE = { AUTO: "auto", MANUAL: "manual", REACT: "react", CAMERA: "camera" };
  var MODE_HINT = {
    auto: "Secuencia completa sola",
    manual: "Tú das cada orden",
    react: "Mide tu tiempo al tocar",
    camera: "Mide tu tiempo por movimiento"
  };
  var STEP_TEXT = [
    "Nadadores,<br>a órdenes del árbitro",
    "Pitidos del árbitro",
    "En sus marcas",
    "¡SALIDA!"
  ];

  var state = {
    view: "train",
    mode: MODE.AUTO,
    running: false,
    armed: false,
    tSignal: null,
    manualStep: 0,
    camTrigger: 0,
    timers: [],
    wakeLock: null
  };

  var $ = function (id) { return document.getElementById(id); };
  var el = {
    badge: $("badge"), big: $("big"), sub: $("sub"), ring: $("ring"),
    chips: $("chips"), modeHint: $("modeHint"), primary: $("primary"),
    manualSteps: $("manualSteps"), historyList: $("historyList"),
    statBest: $("statBest"), statAvg: $("statAvg"), statN: $("statN"),
    rangeFields: $("rangeFields"), volumeFields: $("volumeFields"),
    camPanel: $("camPanel"), camStatus: $("camStatus"),
    camBar: $("camBar"), camToggle: $("camToggle")
  };

  function clearTimers() {
    state.timers.forEach(clearTimeout);
    state.timers = [];
  }
  function after(sec, fn) {
    state.timers.push(setTimeout(fn, sec * 1000));
  }
  function randGap(base) {
    var lo = store.get(base + "_min"), hi = store.get(base + "_max");
    if (hi < lo) { var t = lo; lo = hi; hi = t; }
    return lo + Math.random() * (hi - lo);
  }

  function setFlash(cls) {
    document.body.classList.remove("go", "foul");
    if (cls) document.body.classList.add(cls);
  }
  function fireRing() {
    el.ring.classList.remove("go");
    void el.ring.offsetWidth; // restart the animation
    el.ring.classList.add("go");
  }
  function setStage(badge, badgeColor, big, bigClass, sub, subColor) {
    el.badge.textContent = badge;
    el.badge.style.color = badgeColor || "var(--cyan)";
    el.big.innerHTML = big;
    el.big.className = "big" + (bigClass ? " " + bigClass : "");
    el.sub.innerHTML = sub || "";
    el.sub.style.color = subColor || "var(--faint)";
  }

  // keep the screen awake through the long silent gaps
  function requestWake() {
    if (!("wakeLock" in navigator) || state.wakeLock) return;
    navigator.wakeLock.request("screen").then(function (l) {
      state.wakeLock = l;
      l.addEventListener("release", function () { state.wakeLock = null; });
    }).catch(function () {});
  }
  function releaseWake() {
    if (state.wakeLock) { try { state.wakeLock.release(); } catch (e) {} state.wakeLock = null; }
  }

  // ---------------------------------------------------------------- chips
  function refreshChips() {
    var s = store.settings, items;
    if (state.mode === MODE.MANUAL) {
      items = [["Tú controlas cada orden", true]];
    } else {
      var r = function (b) {
        var lo = s[b + "_min"], hi = s[b + "_max"];
        return (+lo.toFixed(1)) + "-" + (+hi.toFixed(1)) + "s";
      };
      items = [
        ["Árbitro", false], [r("g1"), false],
        ["5 pitidos", false], [r("g2"), false],
        ["Marcas", false], [r("g3"), true],
        ["SALIDA", true]
      ];
    }
    el.chips.innerHTML = "";
    items.forEach(function (it) {
      var c = document.createElement("span");
      c.className = "chip" + (it[1] ? " accent" : "");
      c.textContent = it[0];
      el.chips.appendChild(c);
    });
  }

  // ---------------------------------------------------------------- modes
  function setMode(mode) {
    if (state.running) return;
    state.mode = mode;
    Array.prototype.forEach.call(document.querySelectorAll(".mode"), function (b) {
      b.setAttribute("aria-selected", String(b.dataset.mode === mode));
    });
    el.modeHint.textContent = MODE_HINT[mode];
    refreshChips();
    reset(true);
  }

  function reset(soft) {
    clearTimers();
    audio.stopAll();
    state.running = false;
    state.armed = false;
    state.tSignal = null;
    state.manualStep = 0;
    camera.watch = null;
    setFlash(null);
    releaseWake();
    restorePrimary();

    el.camPanel.hidden = (state.mode !== MODE.CAMERA);

    if (state.mode === MODE.MANUAL) {
      el.manualSteps.hidden = false;
      el.primary.textContent = "REINICIAR SECUENCIA";
      setStage("MODO MANUAL", null, "Dirige<br>la salida", null,
               "Pulsa cada orden cuando quieras darla.");
      refreshManualSteps();
    } else {
      el.manualSteps.hidden = true;
      el.primary.textContent = "INICIAR";
      var hint;
      if (state.mode === MODE.REACT) {
        hint = "Toca la pantalla en cuanto suene la señal.";
      } else if (state.mode === MODE.CAMERA) {
        hint = camera.on
          ? "Apunta la cámara al nadador y pulsa INICIAR."
          : "Activa la cámara para medir por movimiento.";
      } else {
        hint = "Escucha la secuencia completa y sal con la señal.";
      }
      setStage("LISTO PARA EMPEZAR", null,
               soft ? "Entrenador<br>de Salidas" : "Listo para<br>otra salida",
               null, hint);
    }
  }

  function restorePrimary() {
    el.primary.classList.remove("stop");
    if (state.mode !== MODE.MANUAL) el.primary.textContent = "INICIAR";
  }

  // ------------------------------------------------------- auto sequence
  function startAuto() {
    clearTimers();
    audio.unlock();
    requestWake();
    state.running = true;
    state.armed = false;
    state.tSignal = null;
    el.primary.textContent = "DETENER";
    el.primary.classList.add("stop");
    setFlash(null);
    setStage("PREPARADOS", null, "Preparados…", null,
             state.mode === MODE.REACT ? "No toques todavía." : "");
    after(randGap("pre"), stepArbitro);
  }

  function stepArbitro() {
    if (!state.running) return;
    setStage("EN CURSO", null, STEP_TEXT[0], null, "");
    var d = audio.playVoice("v_arbitro") || 1.97;
    after(d + randGap("g1"), stepWhistles);
  }

  function stepWhistles() {
    if (!state.running) return;
    setStage("EN CURSO", null, STEP_TEXT[1], null, "");
    var d = audio.playBeeps() || 2.26;
    after(d + randGap("g2"), stepMarcas);
  }

  function stepMarcas() {
    if (!state.running) return;
    setStage("EN CURSO", null, STEP_TEXT[2], null, "");
    var d = audio.playVoice("v_marcas") || 0.87;
    // The swimmer is now still on the block, so this quiet window is exactly
    // when to measure the camera's noise floor.
    if (state.mode === MODE.CAMERA && camera.on) {
      camera.beginCalibration();
      camera.watch = watchFalseStartCam;
    }
    after(d + randGap("g3"), stepSalida);
  }

  function stepSalida() {
    if (!state.running) return;
    var res = audio.playStart();
    state.tSignal = res.at;
    var measuring = (state.mode === MODE.REACT || state.mode === MODE.CAMERA);
    state.armed = measuring;

    if (state.mode === MODE.CAMERA && camera.on) {
      state.camTrigger = camera.finishCalibration();
      camera.watch = watchStartCam;
    }

    setStage("¡FUERA!", "var(--emerald)", "¡SALIDA!", "huge",
             state.mode === MODE.REACT ? "¡TOCA LA PANTALLA!"
             : state.mode === MODE.CAMERA ? "¡SAL YA!" : "");
    setFlash("go");
    fireRing();
    if (measuring) after(6.0, timeoutReact);
    else after(2.0, finishAuto);
  }

  /* Motion after the signal = the start. */
  function watchStartCam(level, tMs) {
    if (!state.armed || state.tSignal === null) return;
    if (level < state.camTrigger) return;
    camera.watch = null;
    var ms = tMs - state.tSignal;
    if (ms < 40) return;              // almost certainly the flash, not the swimmer
    state.armed = false;
    state.running = false;
    clearTimers();
    record(ms);
  }

  /* Motion before the signal = false start. */
  function watchFalseStartCam(level) {
    if (!state.running || state.armed) return;
    // stricter than the start threshold so ordinary fidgeting doesn't DQ
    var trig = Math.max(camera.peak * 2.2, camera.baseline * 4.0, 0.012);
    if (camera.samples.length < 12) return;   // need a noise floor first
    if (level > trig) {
      camera.watch = null;
      falseStart();
    }
  }

  function timeoutReact() {
    if (!state.armed) return;
    state.armed = false;
    state.running = false;
    setFlash(null);
    releaseWake();
    setStage("SIN REGISTRO", "var(--amber)",
             state.mode === MODE.CAMERA ? "No se detectó<br>movimiento" : "No hubo<br>toque",
             null, "Pulsa INICIAR para intentarlo de nuevo.");
    restorePrimary();
  }

  function finishAuto() {
    state.running = false;
    setFlash(null);
    releaseWake();
    setStage("SECUENCIA COMPLETA", null, "¡Buena<br>salida!", null,
             "Pulsa INICIAR para repetir.");
    restorePrimary();
  }

  // ------------------------------------------------------------- manual
  function refreshManualSteps() {
    Array.prototype.forEach.call(document.querySelectorAll(".step"), function (b) {
      var i = +b.dataset.step;
      b.dataset.next = String(i === state.manualStep);
      b.dataset.done = String(i < state.manualStep);
    });
  }

  function manualFire(step) {
    audio.unlock();
    if (step === 0) audio.playVoice("v_arbitro");
    else if (step === 1) audio.playBeeps();
    else if (step === 2) audio.playVoice("v_marcas");
    else audio.playStart();

    if (step === 3) {
      setStage("¡FUERA!", "var(--emerald)", "¡SALIDA!", "huge",
               "Pulsa REINICIAR para otra salida.");
      setFlash("go");
      fireRing();
      state.manualStep = 0;
      setTimeout(function () { setFlash(null); }, 1200);
    } else {
      setStage("MODO MANUAL", null, STEP_TEXT[step], null,
               "Pulsa la siguiente orden cuando estés listo.");
      state.manualStep = step + 1;
    }
    refreshManualSteps();
  }

  // ------------------------------------------------------------ reaction
  function handleTap() {
    if (state.mode !== MODE.REACT) return false;
    if (state.armed && state.tSignal !== null) {
      var ms = performance.now() - state.tSignal;
      state.armed = false;
      state.running = false;
      clearTimers();
      record(Math.max(0, ms));
      return true;
    }
    if (state.running) { falseStart(); return true; }
    return false;
  }

  function record(ms) {
    camera.watch = null;
    store.addTime(ms);
    var g = gradeFor(ms);
    var best = store.best();
    var isBest = best !== null && Math.abs(ms - best) < 0.51;
    setFlash(null);
    releaseWake();
    setStage("TU REACCIÓN", "var(--faint)", fmtMs(ms), "num",
             g.label + (isBest ? "  ·  ¡NUEVO RÉCORD!" : ""), g.color);
    restorePrimary();
    refreshHistory();
  }

  function falseStart() {
    camera.watch = null;
    clearTimers();
    state.running = false;
    state.armed = false;
    releaseWake();
    setFlash("foul");
    setStage("DESCALIFICADO", "var(--rose)", "SALIDA<br>EN FALSO", null,
             "Saliste antes de la señal.", "var(--rose)");
    restorePrimary();
    setTimeout(function () { setFlash(null); }, 1400);
  }

  // ------------------------------------------------------------- history
  function refreshHistory() {
    el.statBest.textContent = fmtMs(store.best());
    el.statAvg.textContent = fmtMs(store.average());
    el.statN.textContent = String(store.history.length);

    el.historyList.innerHTML = "";
    if (!store.history.length) {
      var p = document.createElement("p");
      p.className = "empty";
      p.innerHTML = "Aún no hay tiempos.<br>Usa el modo REACCIÓN para registrar tu primera salida.";
      el.historyList.appendChild(p);
      return;
    }
    var best = store.best(), n = store.history.length;
    store.history.slice(0, 40).forEach(function (h, i) {
      var g = gradeFor(h.ms);
      var isBest = Math.abs(h.ms - best) < 0.51;
      var row = document.createElement("div");
      row.className = "row" + (isBest ? " best" : "");
      row.innerHTML =
        '<span class="n">#' + (n - i) + '</span>' +
        '<span class="t">' + fmtMs(h.ms) + '</span>' +
        (isBest ? '<span class="rec">RÉCORD</span>' : '') +
        '<span class="g" style="color:' + g.color + '">' + g.label + '</span>';
      el.historyList.appendChild(row);
    });
  }

  // ------------------------------------------------------------ settings
  function buildSettings() {
    el.rangeFields.innerHTML = "";
    RANGE_FIELDS.forEach(function (f) {
      var base = f[0];
      var wrap = document.createElement("div");
      wrap.className = "field";
      wrap.innerHTML =
        '<div class="field-head"><b>' + f[1] + '</b><span data-out="' + base + '"></span></div>' +
        '<small>' + f[2] + '</small>';

      var outs = wrap.querySelector('[data-out="' + base + '"]');
      var inputs = {};

      function show() {
        var lo = store.get(base + "_min"), hi = store.get(base + "_max");
        outs.textContent = (+lo.toFixed(1)) + " – " + (+hi.toFixed(1)) + " s";
        // the store clamps min<=max, so pull both sliders back in sync
        if (inputs.min) inputs.min.value = lo;
        if (inputs.max) inputs.max.value = hi;
      }

      [["min", "mín"], ["max", "máx"]].forEach(function (p) {
        var row = document.createElement("div");
        row.className = "slider-row";
        row.innerHTML = '<label>' + p[1] + '</label>';
        var inp = document.createElement("input");
        inp.type = "range";
        inp.min = "0.5"; inp.max = "15"; inp.step = "0.5";
        inp.value = store.get(base + "_" + p[0]);
        inp.setAttribute("aria-label", f[1] + " " + p[1]);
        inp.addEventListener("input", function () {
          store.set(base + "_" + p[0], parseFloat(inp.value));
          show();
          refreshChips();
        });
        inputs[p[0]] = inp;
        row.appendChild(inp);
        wrap.appendChild(row);
      });
      show();
      el.rangeFields.appendChild(wrap);
    });

    el.volumeFields.innerHTML = "";

    // camera sensitivity lives with the other tunables
    (function () {
      var wrap = document.createElement("div");
      wrap.className = "field";
      wrap.innerHTML =
        '<div class="field-head"><b>Sensibilidad de la cámara</b><span data-out></span></div>' +
        '<small>Más alta detecta antes, pero se dispara con el oleaje o la luz</small>';
      var out = wrap.querySelector("[data-out]");
      var row = document.createElement("div");
      row.className = "slider-row";
      var inp = document.createElement("input");
      inp.type = "range";
      inp.min = "0.5"; inp.max = "3"; inp.step = "0.1";
      // slider reads high->sensitive, stored value is a threshold multiplier
      inp.value = (3.5 - store.get("cam_sens")).toFixed(1);
      inp.setAttribute("aria-label", "Sensibilidad de la cámara");
      function show() {
        var s = 3.5 - store.get("cam_sens");
        out.textContent = s >= 2.4 ? "Alta" : s >= 1.4 ? "Media" : "Baja";
      }
      inp.addEventListener("input", function () {
        store.set("cam_sens", 3.5 - parseFloat(inp.value));
        show();
      });
      show();
      row.appendChild(inp);
      wrap.appendChild(row);
      el.volumeFields.appendChild(wrap);
    })();

    VOLUME_FIELDS.forEach(function (f) {
      var key = f[0];
      var wrap = document.createElement("div");
      wrap.className = "field";
      wrap.innerHTML = '<div class="field-head"><b>' + f[1] + '</b><span data-out></span></div>';
      var out = wrap.querySelector("[data-out]");
      var row = document.createElement("div");
      row.className = "slider-row";
      var inp = document.createElement("input");
      inp.type = "range";
      inp.min = "0"; inp.max = "1"; inp.step = "0.05";
      inp.value = store.get(key);
      inp.setAttribute("aria-label", f[1]);
      function show() { out.textContent = Math.round(store.get(key) * 100) + "%"; }
      inp.addEventListener("input", function () {
        store.set(key, parseFloat(inp.value));
        show();
      });
      show();
      row.appendChild(inp);
      wrap.appendChild(row);
      el.volumeFields.appendChild(wrap);
    });
  }

  // ---------------------------------------------------------------- views
  function showView(name) {
    state.view = name;
    ["train", "history", "settings"].forEach(function (v) {
      $("view-" + v).hidden = (v !== name);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.setAttribute("aria-selected", String(b.dataset.view === name));
    });
    if (name === "history") refreshHistory();
  }

  // ---------------------------------------------------------------- wiring
  function init() {
    store.load();
    audio.prefetch();

    Array.prototype.forEach.call(document.querySelectorAll(".mode"), function (b) {
      b.addEventListener("click", function () { setMode(b.dataset.mode); });
    });
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.addEventListener("click", function () { showView(b.dataset.view); });
    });
    Array.prototype.forEach.call(document.querySelectorAll(".step"), function (b) {
      b.addEventListener("click", function (e) {
        e.stopPropagation();
        manualFire(+b.dataset.step);
      });
    });

    el.primary.addEventListener("click", function (e) {
      e.stopPropagation();
      audio.unlock();
      if (state.mode === MODE.MANUAL) { reset(false); return; }
      if (state.running) { reset(false); return; }
      startAuto();
    });

    // ---- camera controls
    function camStatus(text, isError) {
      el.camStatus.textContent = text;
      el.camStatus.className = "cam-status" + (isError ? " err" : text.indexOf("activa") >= 0 ? " live" : "");
    }
    el.camToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      if (camera.on) {
        camera.stop();
        el.camToggle.textContent = "ACTIVAR CÁMARA";
        el.camToggle.classList.remove("on");
        camStatus("Cámara apagada", false);
        el.camBar.style.width = "0%";
        reset(true);
      } else {
        camStatus("Pidiendo permiso…", false);
        camera.start(camStatus).then(function () {
          el.camToggle.textContent = "APAGAR CÁMARA";
          el.camToggle.classList.add("on");
          reset(true);
        }).catch(function () {
          el.camToggle.textContent = "ACTIVAR CÁMARA";
          el.camToggle.classList.remove("on");
        });
      }
    });
    // live motion meter, so you can see it reacting before trusting it
    window.__camTick = function (level) {
      var pct = Math.min(100, (level / 0.05) * 100);
      el.camBar.style.width = pct.toFixed(0) + "%";
      el.camBar.classList.toggle("hot", state.armed && level >= state.camTrigger);
    };

    $("clearHistory").addEventListener("click", function () {
      store.clearHistory();
      refreshHistory();
    });
    $("resetSettings").addEventListener("click", function () {
      store.resetSettings();
      buildSettings();
      refreshChips();
    });

    // Tap anywhere (outside the controls) counts in reaction mode
    document.addEventListener("pointerdown", function (e) {
      if (state.view !== "train" || state.mode !== MODE.REACT) return;
      if (!state.armed && !state.running) return;
      if (e.target.closest(".primary, .tabs, .modes, .manual-steps")) return;
      if (handleTap()) e.preventDefault();
    });
    document.addEventListener("keydown", function (e) {
      if (e.code === "Space" || e.code === "Enter") {
        if (state.view === "train" && state.mode === MODE.REACT &&
            (state.armed || state.running)) {
          e.preventDefault();
          handleTap();
        }
      }
    });

    // re-acquire the wake lock if the tab was backgrounded mid-run
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible" && state.running) requestWake();
    });

    buildSettings();
    refreshHistory();
    setMode(MODE.AUTO);
    showView("train");

    if ("serviceWorker" in navigator) {
      window.addEventListener("load", function () {
        navigator.serviceWorker.register("sw.js").catch(function () {});
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // expose a little surface for automated checks
  window.__salidas = { store: store, state: state, gradeFor: gradeFor,
                      fmtMs: fmtMs, camera: camera, audio: audio,
                      watchStartCam: watchStartCam };
})();
