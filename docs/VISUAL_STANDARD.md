# Visual quality standard

## Output
1920×1080, 16:9, 30 fps, H.264 (CRF 18, `medium`), BT.709 tagged, AAC 192 kbps, MP4 with faststart.
Do not upscale 24 fps material and call it 30 fps motion.

## Source resolution (validator checks with `--assets`)
- Stills used with camera motion: ≥ 2560 px wide (warn below), ≥ 3840 px preferred. < 1280 px is an error.
- Always download the **original / largest** file, never the "large/medium" preview if an original exists.
- Videos: ≥ 1080p; 30 or 60 fps preferred; clip must be at least as long as its shot (else the last frame freezes).
- Panoramas (very wide images) are good for `pan_left/right`.

## Source classes (labels are drawn on screen automatically)
| Class | Meaning | Example |
|---|---|---|
| REAL_PHOTO | camera image from a spacecraft/telescope/astronaut | Cassini photo of Enceladus plumes |
| REAL_VIDEO | real footage | ISS video |
| PROCESSED_DATA | real measurements turned into an image (false colour, composites, maps) | Webb spectrum, mission map |
| SCIENTIFIC_CGI | agency-made visualization/simulation | NASA SVS animation |
| ARTIST_CONCEPT | agency illustration of something not observed | interior-ocean cut-away |
| OUR_CGI | graphics we make (diagrams, Blender, charts) | scale comparison |

Rules: real material first; where nothing can be photographed, use the matching labelled class. Never use generative-AI images.
Label text appears for ~3 s at the start of a shot when the class or credit changes; hide with `"label": false` only for OUR_CGI.

## Camera
- Eased (smootherstep) move over the whole shot; sub-pixel exact. No shake, no x/y sine drift, no `zoompan`.
- `focus` [x, y] in 0..1 picks the point of interest (a plume, a crater). The camera never shows outside the image.
- Typical: push_in 0.06 on faces/features, pull_out 0.06 to reveal context, pan on wide images.

## Look
- Keep the original colours; no heavy filters. Dark space images: avoid crushing blacks (encoder CRF 18 handles it).
- Use `crossfade` (0.4–0.7 s) between related images; event transitions at beat changes only.

## Credits
Each non-OUR_CGI shot needs `credit` and `source_url`. Typical required wording differs per archive (NASA/JPL-Caltech, ESA/Webb, ESO/…); copy it from the item's page, then set `credit_verified: true`. Check the page for restrictions on people, logos or third-party material.
