# Entrenador de Salidas — Swim Start Reaction Trainer

Android app (Kivy/Python) for drilling swim race-start reflexes in Spanish.
The pauses between commands are re-randomised on every run, so the rhythm
can't be memorised.

## Sequence

```
"Nadadores, a órdenes del árbitro"
      ↓  pausa aleatoria
silbato · silbato · silbatooooo        (el tercero, largo)
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
| After the three whistles | 1 – 3 s |
| After "En sus marcas" | **1 – 8 s** |

So you can keep the early commands tight and make only the final window wildly
unpredictable, which is where the training value is. Voice, whistle, and start
signal each have their own volume.

## Audio

Voices are synthesised offline with eSpeak NG driving MBROLA `es2` diphone
voices — noticeably more natural than plain formant synthesis. The whistles are
modelled as a trilling pea-whistle (fundamental + harmonics + breath noise) and
the start signal is a hard, harmonically-stacked electronic horn with a very
fast attack, matching how real meets trigger starts.

To swap in your own recordings, drop replacements into `assets/` keeping the
same filenames:

```
v_arbitro.ogg      "Nadadores, a órdenes del árbitro"
v_marcas.ogg       "En sus marcas"
referee_beeps.ogg  the three whistles as one clip
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

## Files

```
main.py            app: modes, sequence engine, screens
theme.py           custom Kivy widgets (water background, cards, sliders)
config.py          settings + history persistence, grading
assets/            audio cues (.ogg)
buildozer.spec     Android packaging config
```
