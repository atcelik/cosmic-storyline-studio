# Retention standard (working heuristics, not guarantees)

Goal: the viewer always knows what question is open and always has something new to look at.

## Structure
- **Hook (0–15 s):** start on the strongest real image. Say the central question or the stakes in the first sentence. No logo sting, no "welcome back", no "in this video". By 15 s the promise is clear: what will be answered, and why it matters.
- **Beats:** 6–8 beats. Every beat after the first starts from the previous one with **but / therefore** (stored in `beats[].because`). Never "and then".
- **Open loops:** end each beat with a question or a complication that the next beat begins to answer within ~20 s.
- **Re-hooks:** at ~25 %, 50 % and 75 % of runtime put a reveal, a scale comparison, or a surprising number.
- **Payoff:** answer the central question by ~90 %. Use the last 30–40 s for the answer, its meaning, and one new question.
- Keep the ending short (≤ 10 s). No long outro.

- **Earth connection (owner rule, 2026-11-22).** Every episode has one beat that ties the mystery to life on Earth
  ("why this matters to us"), shown with real imagery of the Earth side (e.g. Enceladus -> deep-sea vents where life
  runs on hydrogen chemistry). Place it after the main evidence and let the final question grow out of it.

## Pacing
- Average 4–6 s per shot, hard limit 8 s (validator warns). ~110–140 shots for 11 minutes.
- Change something visually at least every 6 s (new shot, or a clear camera move plus a text card).
- Narration: one idea per sentence, ≤ 18 words, 140–160 words/min, contractions allowed, concrete numbers with a human-scale comparison.
- Place 0.4–0.8 s of silence (no voice) before a big reveal, using `min_duration` on a shot with no voice-over.

## Camera and transitions
- Every shot moves (`push_in`, `pull_out`, `pan_*`) except at most one `hold` in a row. Alternate push and pull for rhythm. `strength` 0.04–0.10.
- ~70 % of cuts are `cut` or `crossfade` (invisible, keep momentum). Reserve **event transitions** (`zoom_through`, `push_*`, `dip_*`) for beat changes — about one per beat.
- Use `dip_black` only before the final reveal or at a chapter break. Same transition ≤ 3 times in a row.
- On-screen text: ≤ 6 words, only for names, dates, numbers, or the central question.

## Sound
- Music bed under the voice, auto-ducked; swell slightly at reveals by leaving 1–2 s of no-voice shots.
- Subtle SFX at event transitions only (`sfx` per shot), −6 dB or lower.

## Learn from data (after publishing)
Open YouTube Studio → Analytics → Engagement → retention graph. Log every drop > 10 % within 10 s and the shot IDs at that time in `docs/DECISIONS.md`, then adjust the next episode (shorter hook, earlier reveal, fewer holds). Titles/thumbnails are outside this pipeline; treat the first 30 s as the thing you can fix here.
