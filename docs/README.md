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

## How the audio works

The two spoken lines are audio files (`.ogg` with an `.m4a` fallback, because
Safari's Ogg Vorbis support is unreliable). The three whistles and the start
horn are **synthesised live** with the Web Audio API rather than played from
files.

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
