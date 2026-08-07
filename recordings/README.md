# Drop your recordings here

Put your audio files in this folder and tell Claude. Any format works
(`.m4a`, `.mp3`, `.wav`, `.aac`, `.ogg`, voice-memo exports, WhatsApp voice
notes — all fine). Claude converts, trims, normalises and wires them into both
the Android app and the web version.

## What to record — 4 things

| # | File name (suggested) | What it is |
|---|---|---|
| 1 | `arbitro.*` | "Nadadores, a órdenes del árbitro" |
| 2 | `marcas.*`  | "En sus marcas" |
| 3 | `pitidos.*` | The five referee beeps: 4 fast + 1 long, **as one continuous recording** |
| 4 | `salida.*`  | The start signal |

Names don't actually matter — just say which is which if they're unclear.

## Best case: record the real thing

For #3 and #4, if you can get near the actual referee's device at a meet or
training session, record *that*. A real recording of the tool beats anything
synthesised or re-created. Same for the voice lines if you can catch a real
starter — ambient pool noise in the background is fine, even good.

## If you're recording the voice yourself

- Quiet room, phone ~20 cm from your mouth, held slightly off to the side so
  you don't pop the mic on the "p" in "marcas".
- Say it the way a starter says it: firm, level, unhurried. Not shouted.
- **Do several takes in one recording**, with a couple of seconds of silence
  between them. Say the line 3-4 times, then tell Claude "use the third take"
  — or just let Claude pick the cleanest.
- Don't bother trimming, topping and tailing, or adjusting volume. That gets
  done automatically and more precisely than by hand.

## Things that don't matter

- Leading/trailing silence — trimmed automatically
- Volume differences between files — every file is peak-normalised
- File format, sample rate, mono vs stereo — all converted
- Slightly noisy background — fine, and arguably more realistic

## One thing that does matter

For the **start signal** (#4): record it with a clean, sharp onset — don't fade
in, don't start the recording mid-tone. Reaction times are measured from the
instant that sound begins, so Claude trims it to the exact onset sample. A
recording that ramps up slowly makes "when did it start" genuinely ambiguous
and will bias every time you measure.

Timing accuracy is not affected by using a recorded file instead of a
synthesised tone — the web version schedules audio on the audio clock either
way, which is sample-accurate.
