# episode.json (schema_version 2)

Paths are relative to the episode folder (`episodes/epNN/`).

```json
{
  "schema_version": 2,
  "episode": {"id": "ep01", "title": "…", "language": "en", "central_question": "…"},
  "voice": {"engine": "kokoro", "voice": "af_heart", "speed": 1.0},
  "music": {"file": "assets/music/bed.mp3", "credit": "Artist – Title", "license": "CC0", "gain_db": -20},
  "beats": [
    {"id": "B1", "name": "Hook", "chapter": "The question"},
    {"id": "B2", "name": "Evidence", "because": "But the data did not fit.", "chapter": "The evidence"}
  ],
  "shots": [
    {
      "id": "S001", "beat": "B1",
      "voiceover": "One sentence, 5–18 words.",
      "visual": {
        "type": "still",                      // still | video
        "file": "assets/S001.jpg",            // or "search_query" until fetched
        "search_query": "Enceladus plume Cassini",
        "source_class": "REAL_PHOTO",
        "credit": "NASA/JPL-Caltech/Space Science Institute",
        "source_url": "https://images.nasa.gov/details/…",
        "credit_verified": false,
        "trim_start": 0, "speed": 1.0          // video only
      },
      "camera": {"move": "push_in", "strength": 0.06, "focus": [0.5, 0.5]},
      "transition_out": {"type": "crossfade", "duration": 0.5},
      "on_screen_text": "≤ 6 words",
      "label": true,
      "min_duration": 0,
      "claims": [{"text": "…", "source_url": "https://…", "verified": false}],
      "sfx": [{"file": "assets/sfx/x.wav", "at": 0.0, "gain_db": -8}]
    }
  ]
}
```
(Real files are plain JSON: remove the `//` comments.)

Rules: `source_class` ∈ REAL_PHOTO, REAL_VIDEO, PROCESSED_DATA, SCIENTIFIC_CGI, ARTIST_CONCEPT, OUR_CGI ·
`camera.move` ∈ push_in, pull_out, pan_left, pan_right, hold · `transition_out.type` ∈ cut, crossfade, dip_black, dip_white,
push_left, push_right, zoom_through (duration 0.2–1.5 s; the last shot's is ignored) · voice-over is optional (silent shots use `min_duration`) ·
`claims` are required when the voice-over contains a number · `beats[].because` is required for every beat after the first.
