# Web version (GitHub Pages)

Same trainer as the Android app, running in any browser — including iPhone,
which can't install the `.apk`.

## Enabling GitHub Pages

Repo **Settings → Pages → Build and deployment**:

- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- Save

Live a minute or two later at:

```
https://g-delgado.github.io/swimming-reaction-training/
```

Deploying from a branch does **not** use GitHub Actions, so this publishes
even while Actions is having an outage.

## Installing it on a phone

It's a PWA, so it installs to the home screen and runs offline — no app store,
no developer account.

- **iPhone:** open in Safari → Share → *Add to Home Screen*
- **Android:** open in Chrome → menu → *Install app* / *Add to Home screen*

After the first load everything is cached, so it works poolside with no signal.

## iPhone caveats

- **The silent switch mutes it.** iOS routes web audio through the ringer
  switch. If the physical switch is on silent, you'll hear nothing. Flip it on,
  or use the Android app.
- Audio needs one tap to unlock — pressing INICIAR covers this, so it's
  invisible in practice.
- Screen sleep during a long gap is prevented via the Wake Lock API
  (iOS 16.4+). On older iOS the screen may dim mid-sequence; the audio keeps
  playing.

## Modes

| Mode | What it measures |
| --- | --- |
| **AUTO** | Nothing — just plays the sequence hands-free. |
| **MANUAL** | Nothing — you fire each command yourself. |
| **TOQUE** | How fast you tap the screen after the start signal. |
| **CÁMARA** | How fast you physically *move*, detected through the camera. |

### CÁMARA mode

Prop the phone so it sees the swimmer on the block, tap **ACTIVAR CÁMARA**,
grant permission, then run the sequence as normal.

It works by frame-differencing: every camera frame is compared with the last
one, and the moment the picture changes more than the calibrated noise floor
counts as the start. During "En sus marcas" — when the swimmer is deliberately
still — it measures the background noise (rippling water, shifting light) and
sets the trigger above it. Movement *before* the signal is flagged as a false
start, same as a real meet.

Deliberately not pose/ML detection: no model to download, runs on any phone,
and adds no inference delay, which matters when the whole event is ~200 ms.

**Accuracy is bounded by the camera frame rate — ±1 frame.** That's about
±17 ms at 60 fps, ±33 ms at 30 fps. The status line shows the actual rate and
margin once the camera is live. Compared with the touch mode (sub-millisecond),
camera timing is coarser, so treat it as "close enough to coach with", not as
an official timing system.

Things that will trip it up, and what to do:

- **Moving water, shifting sunlight, people walking behind.** Aim tighter on
  the swimmer, or lower the sensitivity in Ajustes.
- **A handheld phone.** Camera shake is motion. Prop it against something.
- **Very dark pools.** Low light means grainy frames means a high noise floor;
  it'll still work but the threshold rises and small movements may be missed.

The live meter under the video shows the current motion level, so you can wave
a hand and confirm it's actually seeing the lane before you trust a time.

## How the audio works

The two spoken lines are audio files (`.ogg` with an `.m4a` fallback, because
Safari's Ogg Vorbis support is unreliable) and are downloaded at page load, so
the very first run has sound. The five referee beeps — four fast ones then a
longer, clearer fifth — and the start horn are **synthesised live** with the
Web Audio API rather than played from files.

That's deliberate: for reaction timing we need to know exactly when the horn
begins. Scheduling it on the audio clock and reading back `outputLatency` gives
a far more honest measurement than an `<audio>` element, whose playback start
can drift by tens of milliseconds.

## Files

```
index.html            markup and screens
styles.css            pool/tech theme, lane lines, shimmer
app.js                modes, sequence engine, settings, history
manifest.webmanifest  PWA metadata
sw.js                 offline cache
audio/                the two voice cues (.ogg + .m4a)
icons/                app icons
```

## Local preview

```bash
cd docs
python3 -m http.server 8000
```

Then open `http://localhost:8000`. A plain `file://` open won't work — the
service worker and `fetch()` of the audio need a real origin.
