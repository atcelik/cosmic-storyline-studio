# Space Mysteries pipeline

English, 10–12 minute space-mystery documentaries: approved script (`episode.json`) → real NASA/ESA footage with
smooth camera moves and transitions → synthetic narration + ducked music → 1080p/30 MP4, captions, description with credits.
All tools are free/open source.

Quick start (Ubuntu): `bash scripts/setup_server.sh` → `make smoke` → write/receive `episodes/ep01/episode.json` →
follow the gates in `AGENTS.md`. Give `AGENTS.md` to your coding agent as the project instruction file.
Status of what is and isn't tested: `docs/DECISIONS.md` (bottom section).
