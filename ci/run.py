#!/usr/bin/env python3
"""GitHub Actions orchestrator. Reads render_request.json and runs the requested steps, split into phases so the
slow work (3D scenes, the final picture) runs on many machines at the same time.

  --phase prepare   smoke, assets, voice_test, globes, validate (structure), tts; then plans the parallel tasks
  --phase cgi       one chunk of frames of one 3D scene        (--task '{"spec": ..., "a": 0, "b": 90, "id": ...}')
  --phase render    one chunk of frames of the final picture   (--task '{"a": 0, "b": 900, "id": ...}')
  --phase finish    joins chunks, full validation with assets, audio, meta
  --phase all       everything in one process (local runs; same result)

Every phase writes review_out/log_<tag>.txt and review_out/status_<tag>.json; finish merges them into
log.txt and status.json. Stops at the first failing step (exit 1).

render_request.json:
{"episode": "enceladus_test",
 "steps": ["smoke", "assets", "voice_test", "globes", "space3d", "validate", "tts", "render", "audio", "meta"],
 "quality": "draft" | "final",
 "search": false, "top": 2,      # assets: also search NASA for shots with only search_query
 "cgi_chunk": 90,                # frames per parallel 3D job (default: 90, more if the episode is long)
 "render_chunk": 900,            # frames per parallel picture job (default: 30 s)
 "voice_test_text": "...",       # optional
 "note": "free text"}
"""
import argparse, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "review_out"
OUT.mkdir(exist_ok=True)
req = json.loads((ROOT / "render_request.json").read_text())
ep = req["episode"]
steps = req["steps"]
ep_dir = ROOT / "episodes" / ep
ep_json = ep_dir / "episode.json"
draft = req.get("quality", "draft") == "draft"
DRAFT = ["--draft"] if draft else []
PY = sys.executable
CGI_DIR = ROOT / "cgi_parts"          # <stem>/<a>.mp4
RENDER_DIR = ROOT / "render_parts"    # <a>.mp4
PRE = ["smoke", "assets", "voice_test", "globes", "validate", "tts"]
POST = ["validate", "audio", "meta"]


class Phase:
    def __init__(self, tag):
        self.tag = tag
        self.log = OUT / f"log_{tag}.txt"
        self.status = {"phase": tag, "steps": [], "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

    def save(self):
        (OUT / f"status_{self.tag}.json").write_text(json.dumps(self.status, indent=2))

    def run(self, name, cmds):
        t0 = time.time()
        with open(self.log, "a") as log:
            log.write(f"\n===== STEP {name} ({self.tag}) =====\n")
            for cmd in cmds:
                log.write("$ " + " ".join(map(str, cmd)) + "\n"); log.flush()
                print(f"::group::{name}: {' '.join(map(str, cmd))}", flush=True)
                p = subprocess.Popen(list(map(str, cmd)), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in p.stdout:
                    sys.stdout.write(line); log.write(line)
                p.wait()
                print("::endgroup::", flush=True)
                if p.returncode != 0:
                    self.status["steps"].append({"step": name, "ok": False, "seconds": round(time.time() - t0), "exit": p.returncode})
                    self.status["result"] = f"FAILED at {name} ({self.tag})"
                    self.save()
                    sys.exit(1)
        self.status["steps"].append({"step": name, "ok": True, "seconds": round(time.time() - t0)})
        self.save()

    def done(self):
        self.status["result"] = "OK"
        self.save()


def gh_output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}={v}")
        if path:
            with open(path, "a") as f:
                f.write(f"{k}={v}\n")


def specs():
    return sorted((ep_dir / "assets" / "space3d").glob("*.json"))


def fps():
    return json.loads((ROOT / "config.json").read_text())["fps"]


def concat(parts, out):
    """Join equally encoded mp4 chunks without re-encoding."""
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    lst.unlink()
    if r.returncode:
        sys.exit(f"concat failed for {out}: {r.stderr[-500:]}")


def join_cgi():
    """cgi_parts/<stem>/<a>.mp4 -> episodes/<ep>/assets/<stem>.mp4"""
    joined = []
    if CGI_DIR.exists():
        for d in sorted(p for p in CGI_DIR.iterdir() if p.is_dir()):
            parts = sorted(d.glob("*.mp4"), key=lambda p: int(p.stem))
            if parts:
                concat(parts, ep_dir / "assets" / f"{d.name}.mp4")
                joined.append(d.name)
    if joined:
        print("joined 3D clips:", ", ".join(joined))
    return joined


def fit_specs():
    """A 3D spec with "duration": "auto" gets exactly as long as the shots that use it
    (voice-over timing from build/timeline.json, so the flight never stops before the cut)."""
    tl_path = ep_dir / "build" / "timeline.json"
    if not ep_json.exists():
        return
    ep = json.loads(ep_json.read_text())
    T = {t["id"]: t for t in json.loads(tl_path.read_text())["shots"]} if tl_path.exists() else {}
    for s in specs():
        sp = json.loads(s.read_text())
        if sp.get("duration") != "auto" and not sp.get("fit"):
            continue
        sp["fit"] = True
        used = [sh for sh in ep["shots"] if (sh["visual"].get("file") or "") == f"assets/{s.stem}.mp4"]
        secs = sum(T[sh["id"]]["dur"] - T[sh["id"]]["trans_d"] for sh in used if sh["id"] in T)
        if not secs:
            secs = sp.get("fallback", 10)
        sp["duration"] = round(secs + 1.0, 2)
        s.write_text(json.dumps(sp, indent=1))
        print(f"fit {s.stem}: {len(used)} shots -> {sp['duration']} s")


# ---------------- phases ----------------
def prepare():
    ph = Phase("prepare")
    for step in steps:
        if step not in PRE:
            continue
        if step == "smoke":
            ph.run(step, [[PY, "tests/smoke.py"]])
        elif step == "assets":
            cmds = [[PY, "scripts/get_assets.py", ep_dir, "--no-zip"] + (["--search"] if req.get("search") else [])
                    + (["--top", str(req["top"])] if req.get("top") else [])]
            if ep_json.exists():
                cmds.append([PY, "scripts/apply_bundle.py", ep_dir, ep_dir / "bundle"])
            ph.run(step, cmds)
        elif step == "voice_test":
            text = req.get("voice_test_text") or ("A spacecraft flew past a frozen moon, and found an ocean spraying into space. "
                                                  "Nobody expected it. Today, we follow the evidence.")
            ph.run(step, [[PY, "scripts/voice_test.py", text]])
        elif step == "globes":
            ph.run(step, [[PY, "scripts/globe.py", s, ep_dir / "assets" / f"{s.stem}.mp4"] for s in sorted((ep_dir / "assets" / "globes").glob("*.json"))])
        elif step == "validate":
            ph.run(step, [[PY, "scripts/validate.py", ep_json]])          # structure only; files are checked in finish
        elif step == "tts":
            ph.run(step, [[PY, "scripts/tts.py", ep_json]])
    unknown = [s for s in steps if s not in PRE + POST + ["space3d", "render"]]
    if unknown:
        ph.status["result"] = f"FAILED: unknown step {unknown}"; ph.save(); sys.exit(1)

    # plan the parallel work
    F = fps()
    cgi = []
    if "space3d" in steps:
        fit_specs()
        total = sum(int(round(json.loads(s.read_text())["duration"] * F)) for s in specs())
        chunk = int(req.get("cgi_chunk") or max(90, math.ceil(total / 200)))
        for s in specs():
            n = int(round(json.loads(s.read_text())["duration"] * F))
            for a in range(0, n, chunk):
                cgi.append({"spec": str(s.relative_to(ROOT)), "a": a, "b": min(n, a + chunk), "id": f"{s.stem}-{a:05d}"})
        # the 3D jobs only need the specs and the textures they name
        stage = ROOT / "cgi_inputs"
        shutil.rmtree(stage, ignore_errors=True)
        for s in specs():
            dst = stage / s.relative_to(ROOT); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(s, dst)
            for bd in json.loads(s.read_text()).get("bodies", []):
                for t in (bd.get("texture"), (bd.get("rings") or {}).get("texture")):
                    for c in (t if isinstance(t, list) else [t]):
                        if c and (s.parent / c).exists():
                            src = (s.parent / c).resolve()
                            d = stage / src.relative_to(ROOT); d.parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, d)
        shutil.copy(ROOT / "config.json", stage / "config.json")
    rnd = []
    if "render" in steps:
        tl = ep_dir / "build" / "timeline.json"
        if not tl.exists():
            ph.status["result"] = "FAILED: render needs build/timeline.json (add the tts step)"; ph.save(); sys.exit(1)
        n = int(round(json.loads(tl.read_text())["total"] * F))
        chunk = int(req.get("render_chunk") or max(900, math.ceil(n / 20)))
        rnd = [{"a": a, "b": min(n, a + chunk), "id": f"{a:06d}"} for a in range(0, n, chunk)]
    ph.status["plan"] = {"cgi_tasks": len(cgi), "render_tasks": len(rnd)}
    ph.done()
    gh_output(cgi_tasks=json.dumps(cgi or [{"id": "none"}]), render_tasks=json.dumps(rnd or [{"id": "none"}]),
              has_cgi=str(bool(cgi)).lower(), has_render=str(bool(rnd)).lower())
    return cgi, rnd


def cgi_task(task):
    ph = Phase(f"cgi_{task['id']}")
    spec = ROOT / task["spec"]
    out = CGI_DIR / spec.stem / f"{task['a']}.mp4"
    ph.run("space3d", [[PY, "scripts/space3d.py", spec, out, "--frames", f"{task['a']}:{task['b']}"]])
    ph.done()


def render_task(task):
    ph = Phase(f"render_{task['id']}")
    join_cgi()
    out = RENDER_DIR / f"{task['a']}.mp4"
    ph.run("render", [[PY, "scripts/render.py", ep_json, "--frames", f"{task['a']}:{task['b']}", "--out", out] + DRAFT])
    ph.done()


def finish():
    ph = Phase("finish")
    join_cgi()
    if "render" in steps:
        parts = sorted(RENDER_DIR.glob("*.mp4"), key=lambda p: int(p.stem)) if RENDER_DIR.exists() else []
        if not parts:
            ph.status["result"] = "FAILED: no rendered picture chunks"; ph.save(); sys.exit(1)
        concat(parts, ep_dir / "build" / ("video_draft.mp4" if draft else "video_silent.mp4"))
    for step in steps:
        if step == "validate":
            ph.run("validate+assets", [[PY, "scripts/validate.py", ep_json, "--assets"]])
        elif step == "audio":
            ph.run(step, [[PY, "scripts/audio.py", ep_json] + DRAFT])
        elif step == "meta":
            ph.run(step, [[PY, "scripts/meta.py", ep_json]])
    ph.done()


def merge(upstream_ok=True):
    """Fold every phase's status and log into status.json / log.txt (prepare first, finish last)."""
    order = lambda p: (0 if "prepare" in p.name else 2 if "finish" in p.name else 1, p.name)
    status = {"episode": ep, "request": req, "phases": [], "steps": []}
    failed = []
    for f in sorted(OUT.glob("status_*.json"), key=order):
        s = json.loads(f.read_text())
        status["phases"].append({"phase": s["phase"], "result": s.get("result", "incomplete"), "plan": s.get("plan")})
        for st in s["steps"]:
            status["steps"].append(dict(st, phase=s["phase"]))
        if s.get("result") != "OK":
            failed.append(f"{s['phase']}: {s.get('result', 'incomplete')}")
    if not upstream_ok and not failed:
        failed.append("a parallel job failed before it could report (see the Actions log)")
    status["result"] = "OK" if not failed else "FAILED: " + "; ".join(failed[:5])
    # parallel steps run at the same time: report wall-clock per kind, not the sum
    kinds = {}
    for st in status["steps"]:
        kinds.setdefault(st["step"], []).append(st["seconds"])
    status["seconds_by_step"] = {k: {"jobs": len(v), "longest": max(v), "sum": sum(v)} for k, v in kinds.items()}
    final = ep_dir / "build" / ("final_draft.mp4" if draft else "final.mp4")
    if not failed and final.exists():
        status["final_video"] = str(final.relative_to(ROOT))
        gh_output(final_video=status["final_video"])
    (OUT / "status.json").write_text(json.dumps(status, indent=2))
    with open(OUT / "log.txt", "w") as log:
        for f in sorted(OUT.glob("log_*.txt"), key=order):
            log.write(f.read_text())
    print(status["result"])
    return not failed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all", choices=["prepare", "cgi", "render", "finish", "merge", "all"])
    ap.add_argument("--task", default="{}")
    ap.add_argument("--upstream-ok", default="true")
    a = ap.parse_args()
    task = json.loads(a.task)
    if a.phase == "prepare":
        prepare()
    elif a.phase == "cgi":
        cgi_task(task)
    elif a.phase == "render":
        render_task(task)
    elif a.phase == "finish":
        finish()
    elif a.phase == "merge":
        sys.exit(0 if merge(a.upstream_ok == "true") else 1)
    else:
        cgi, rnd = prepare()
        for t in cgi:
            cgi_task(t)
        for t in rnd:
            render_task(t)
        finish()
        sys.exit(0 if merge() else 1)
