# asset_manifest.json

Claude (or you) writes this list; `scripts/get_assets.py` downloads it in one go.

```json
{"episode": "ep01",
 "items": [
  {"id": "A001",
   "url": "https://d2pn8kiwq2w21t.cloudfront.net/original_images/jpegPIA17172.jpg",
   "kind": "image",
   "title": "The Day the Earth Smiled",
   "source_class": "REAL_PHOTO",
   "credit": "NASA/JPL-Caltech/SSI",
   "source_url": "https://www.jpl.nasa.gov/images/pia17172-the-day-the-earth-smiled",
   "credit_checked": true,
   "shots": ["S001", "S040"],
   "trim_start": 0, "speed": 1.0}
 ]}
```
- `url` must be the FILE itself (jpg/png/tif/mp4/mov), not the web page. A web page is rejected with a clear message.
- `kind`: image | video (guessed from the extension if missing).
- `shots`: which shots use it. Empty is fine; map later.
- `credit_checked`: true only if someone read the credit on `source_url`. Items found by `--search` are never auto-verified.
- `trim_start` / `speed`: video only, copied to the shot.

JPL pattern (most Cassini/Juno/Mars images): page `https://www.jpl.nasa.gov/images/piaNNNNN-…` →
JPG `https://d2pn8kiwq2w21t.cloudfront.net/original_images/jpegPIANNNNN.jpg`, TIFF `https://photojournal.jpl.nasa.gov/tiff/PIANNNNN.tif`.
