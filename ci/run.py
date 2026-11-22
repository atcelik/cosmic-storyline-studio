#!/usr/bin/env python3
"""GitHub Actions orchestrator. Reads render_request.json and runs the requested steps in order.
Every step's output goes to review_out/log.txt; review_out/status.json records what passed.
Stops at the first failing step (exit 1) so the review pack shows exactly where it broke.

render_request.json:
{"episode": "enceladus_test",
 "steps": ["smoke", "assets", "voice_test", "globes", "validate", "tts", "render", "audio", "meta"],
 "quality": "draft" | "final",
 "search": false,                 # assets: also search NASA for shots with only search_query
 "voice_test_text": "...",        # optional
 "note": "free text, shown in the release notes"}
"""
import json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review_out"
OUT.mkdir(exist_ok=True)
LOG = OUT / "log.txt"
req = json.loads((ROOT / "render_request.json").read_text())
ep = req["episode"]
ep_dir = ROOT / "episodes" / ep
ep_json = ep_dir / "episode.json"
draft = ["--draft"] if req.get("quality", "draft") == "draft" else []
PY = sys.executable
status = {"episode": ep, "request": req, "steps": [], "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}


def save():
    (OUT / "status.json").write_text(json.dumps(status, indent=2))


def run(name, cmds):
    t0 = time.time()
    with open(LOG, "a") as log:
        log.write(f"\n===== STEP {name} =====\n")
        for cmd in cmds:
            log.write("$ " + " ".join(map(str, cmd)) + "\n"); log.flush()
            print(f"::group::{name}: {' '.join(map(str, cmd))}", flush=True)
            p = subprocess.Popen(list(map(str, cmd)), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                sys.stdout.write(line); log.write(line)
            p.wait()
            print("::endgroup::", flush=True)
            if p.returncode != 0:
                status["steps"].append({"step": name, "ok": False, "seconds": round(time.time() - t0), "exit": p.returncode})
                status["result"] = f"FAILED at {name}"
                save()
                sys.exit(1)
    status["steps"].append({"step": name, "ok": True, "seconds": round(time.time() - t0)})
    save()


for step in req["steps"]:
    if step == "smoke":
        run(step, [[PY, "tests/smoke.py"]])
    elif step == "assets":
        cmds = [[PY, "scripts/get_assets.py", ep_dir, "--no-zip"] + (["--search"] if req.get("search") else []) + (["--top", str(req["top"])] if req.get("top") else [])]
        if ep_json.exists():
            cmds.append([PY, "scripts/apply_bundle.py", ep_dir, ep_dir / "bundle"])
        run(step, cmds)
    elif step == "voice_test":
        text = req.get("voice_test_text") or ("A spacecraft flew past a frozen moon, and found an ocean spraying into space. "
                                              "Nobody expected it. Today, we follow the evidence.")
        run(step, [[PY, "scripts/voice_test.py", text]])
    elif step == "globes":
        specs = sorted((ep_dir / "assets" / "globes").glob("*.json"))
        run(step, [[PY, "scripts/globe.py", s, ep_dir / "assets" / f"{s.stem}.mp4"] for s in specs])
    elif step == "validate":
        run(step, [[PY, "scripts/validate.py", ep_json, "--assets"]])
    elif step == "tts":
        run(step, [[PY, "scripts/tts.py", ep_json]])
    elif step == "render":
        run(step, [[PY, "scripts/render.py", ep_json] + draft])
    elif step == "audio":
        run(step, [[PY, "scripts/audio.py", ep_json] + draft])
    elif step == "meta":
        run(step, [[PY, "scripts/meta.py", ep_json]])
    else:
        status["steps"].append({"step": step, "ok": False, "error": "unknown step"})
        status["result"] = f"FAILED: unknown step {step}"
        save()
        sys.exit(1)

status["result"] = "OK"
final = ep_dir / "build" / ("final_draft.mp4" if draft else "final.mp4")
if final.exists():
    status["final_video"] = str(final.relative_to(ROOT))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"final_video={final.relative_to(ROOT)}\n")
save()
print("ALL STEPS OK")
