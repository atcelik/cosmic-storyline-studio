# Working with ChatGPT (scriptwriting only)

ChatGPT writes the story; it cannot see our files or verify asset IDs. So it supplies `search_query` per shot and we fetch/pick real assets.

## Step 1 — outline (paste, fill the topic, review the answer)
```
Act as a documentary writer for a YouTube channel about space mysteries. English, calm, curious, precise.
Topic: <TOPIC>. Target: 10–12 minutes (about 1,600–1,800 words of narration).
Return ONLY:
1) One central question (≤ 15 words) and the one-sentence promise.
2) 6–8 beats. For each: name, what the viewer learns, the open question it ends on, and how it follows the previous beat with "but" or "therefore".
3) The 3 re-hook moments (about 25 %, 50 %, 75 %): a reveal, a scale comparison, or a surprising number.
4) A list of every factual claim with a source link you are confident exists. Mark anything you cannot source as UNVERIFIED. Do not invent numbers, quotes or links.
Rules: no "in this video", no filler, no hype words; explain uncertainty honestly ("we don't know yet").
```

## Step 2 — shots (after you approve the outline)
```
Now write the full episode as JSON ONLY, schema_version 2, following the format below exactly (no comments, no markdown).
- 110–140 shots; each shot has ONE voice-over sentence (5–18 words) or none; average shot ≈ 5 s, never > 8 s.
- First shot = the hook line. At least 3 shots in the first 15 seconds.
- Every shot: visual.type, visual.search_query (concrete: mission + target + instrument, e.g. "Cassini Enceladus plume backlit"),
  visual.source_class (REAL_PHOTO / REAL_VIDEO / PROCESSED_DATA / SCIENTIFIC_CGI / ARTIST_CONCEPT / OUR_CGI),
  camera.move (vary: push_in, pull_out, pan_left, pan_right; at most one hold in a row), strength 0.04–0.10,
  transition_out (mostly cut/crossfade; event transitions only at beat changes; max 3 identical in a row).
- Put claims[] on any shot whose voice-over contains a number or a scientific claim: text + source_url + "verified": false.
- Do not invent source URLs. If you cannot give one, leave source_url empty and verified false.
- beats[]: id, name, because (required from the second beat), chapter (short title).
<paste docs/EPISODE_FORMAT.md here>
```
Save the answer as `episodes/epNN/episode.json`, run `make check EP=epNN`, and paste the validator warnings back to ChatGPT to fix.

## Rules of thumb
- ChatGPT often gets numbers and dates slightly wrong. Every claim is checked by you (or the agent) against the source before `verified: true`.
- If the validator says a shot is too long, split the sentence into two shots rather than slowing the voice.
