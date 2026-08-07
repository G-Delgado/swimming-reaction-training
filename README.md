# Entrenador de Salidas — Swim Start Reaction Trainer

Trainer for drilling swim race-start reflexes in Spanish. The pauses between
commands are re-randomised on every run, so the rhythm can't be memorised.

Two builds, same features:

| | |
| --- | --- |
| **Android app** | Kivy/Python, packaged as an `.apk` — see [Building the APK](#building-the-apk) |
| **Web app / PWA** | Runs on any phone including iPhone, installs to the home screen, works offline — see [`docs/`](docs/README.md) |

## Sequence

```
"Nadadores, a órdenes del árbitro"
      ↓  pausa aleatoria
pi · pi · pi   ·   piiiiiiii           (tres cortos + uno largo)
      ↓  pausa aleatoria
"En sus marcas"
      ↓  pausa aleatoria  ← la más importante
SEÑAL DE SALIDA                        (bocina dura)
```

## Modes

| Mode | What it does |
| --- | --- |
| **Auto** | Plays the whole sequence hands-free with randomised gaps. |
| **Manual** | You fire each command yourself, one button per step — for standing on deck and starting another swimmer at your own pace. |
| **Reacción** | Runs the sequence, then measures how fast you tap the screen after the start signal. Logs the time with a grade. |

The web version adds a fourth mode, **Cámara**, which measures how fast you
physically move instead of how fast you tap — see [`docs/README.md`](docs/README.md).

In Reacción mode, tapping *before* the signal is caught as **SALIDA EN FALSO**
(false start) and is not recorded.

### Grades

Tuned for a screen tap (pure reaction). Feet actually leaving the block is
roughly 250 ms slower than these numbers.

| Time | Grade |
| --- | --- |
| < 180 ms | RELÁMPAGO |
| < 230 ms | EXCELENTE |
| < 300 ms | MUY BUENO |
| < 380 ms | BUENO |
| < 480 ms | PROMEDIO |
| ≥ 480 ms | LENTO |

The **Tiempos** tab keeps best / average / attempt count plus a full history,
flagging your record.

## Settings

Every pause has its own independent min–max window (**Ajustes** tab). Defaults:

| Gap | Default |
| --- | --- |
| Before the sequence starts | 1 – 2.5 s |
| After "a órdenes del árbitro" | 1 – 3 s |
| After the referee beeps | 1 – 3 s |
| After "En sus marcas" | **1 – 8 s** |

So you can keep the early commands tight and make only the final window wildly
unpredictable, which is where the training value is. Voice, whistle, and start
signal each have their own volume.

## Audio

All four cues are **real recordings**, captured by the user and processed
automatically: high-passed at 70 Hz to remove handling rumble, trimmed to the
exact onset, peak-normalised to -1 dBFS, and encoded to Ogg Vorbis (Android)
plus AAC (Safari). Source files live in `recordings/`.

Leading silence is trimmed from every clip, so nothing gives a swimmer an
early cue and reaction times aren't inflated by dead air:

| Clip | Sound starts at |
| --- | --- |
| `start_beep` | ~1 ms (faint room tone), horn proper at ~13 ms |
| `referee_beeps` | ~19 ms |
| `v_arbitro`, `v_marcas` | ~33 ms — the natural soft start of the word; trimming further would clip the consonant |

The ~13 ms before the horn's first cycle is the recording's own room tone at
1-4% of peak. It is inaudible in practice and is kept because cutting into the
attack changes how the signal sounds.

To swap in your own recordings, drop replacements into `assets/` keeping the
same filenames:

```
v_arbitro.ogg      "Nadadores, a órdenes del árbitro"
v_marcas.ogg       "En sus marcas"
referee_beeps.ogg  the referee beeps as one clip (3 short + 1 long)
start_beep.ogg     the start signal
```

## Building the APK

Pushing to `main` triggers the GitHub Actions workflow in
`.github/workflows/build.yml`; download the APK from the run's **Artifacts**.

Locally (Linux/macOS/WSL, needs a JDK and ~10 GB free):

```bash
pip install buildozer cython
buildozer android debug     # APK lands in bin/
```

`buildozer.spec` pins python-for-android to `v2024.01.21` — its current master
hardcodes on-device Python 3.14, whose bootstrap is broken upstream.

## Web version

`docs/` holds a full-parity web build, published with GitHub Pages
(Settings → Pages → Deploy from a branch → `main` / `/docs`). It installs to
the home screen as a PWA and works offline, which is the only way to run this
on an iPhone. Details and iOS caveats: [`docs/README.md`](docs/README.md).

Publishing from a branch doesn't use Actions, so the web version deploys even
when Actions is down.

## Files

```
main.py            Android app: modes, sequence engine, screens
theme.py           custom Kivy widgets (water background, cards, sliders)
config.py          settings + history persistence, grading
assets/            audio cues (.ogg)
recordings/        original source recordings + how to replace them
buildozer.spec     Android packaging config
build-local.sh     build the APK locally (WSL2/Linux), no CI needed
docs/              web / PWA version, served by GitHub Pages
```
