#!/usr/bin/env python3
"""Capture the unchanged delivered browser app through its actual UI.

From the repository root:
  python docs/demo-professore/capture_demo.py --environment-tls

Optional development dependencies: Playwright and a Chromium executable.
Uses an ephemeral loopback server only for internal capture and shuts it down.
No DOM replacements, mocked worker, edited pixels, or hidden-hand access.
"""
import argparse
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
from threading import Thread

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
APPROVED = "53b349bc82db48d44deeeed7df5d2c760755b787"
SEED = 43
LEVEL = 3
VIEWPORT = {"width": 1440, "height": 1100}


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sources():
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", APPROVED], cwd=ROOT, text=True
    ).splitlines()
    hashes = {}
    for relative in paths:
        expected = subprocess.check_output(["git", "show", f"{APPROVED}:{relative}"], cwd=ROOT)
        actual = (ROOT / relative).read_bytes()
        require(actual == expected, f"Delivered file changed: {relative}")
        hashes[relative] = hashlib.sha256(actual).hexdigest()
    return hashes


def check_view(data):
    view = data["view"]
    require(not any(k in view for k in ("hands", "excluded", "seed")), "Private referee data exposed")
    known = [tuple(sorted(t)) for t in view["hand"] + view["chain"]]
    require(len(known) == len(set(known)), "Duplicate known tile")
    require(all(a[1] == b[0] for a, b in zip(view["chain"], view["chain"][1:])), "Broken chain")
    require(len(view["hand"]) + view["opponent_count"] + len(view["chain"]) == 14,
            "Incorrect public tile accounting")
    require(data["event_count"] == len(view["history"]), "History count differs")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/demo-professore")
    parser.add_argument("--environment-tls", action="store_true")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    require(not any(output.glob("*.png")) and not (output / "PROVENIENZA.json").exists(),
            "Choose an output directory without previous captures; do not overwrite evidence")
    original_hashes = sources()
    build = load_script("delivered_build", "scripts/build_web.py")
    helpers = load_script("delivered_browser_helpers", "scripts/test_web_browser.py")
    generated = ROOT / "local_runs/demo-professore/site"
    manifest = build.build(generated)
    capture_started = now()
    errors, console_errors, screenshots, actions = [], [], [], []
    handler = partial(QuietHandler, directory=str(generated))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    browser_version = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chromium, headless=True,
                                        args=["--no-sandbox"])
            browser_version = browser.version
            context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1,
                                          locale="it-IT", timezone_id="Europe/Madrid",
                                          service_workers="block")
            if args.environment_tls:
                context.route("https://**/*", helpers.tls_transport(
                    ROOT / "local_runs/demo-professore/https-cache"))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text)
                    if message.type == "error" else None)
            page.goto(f"http://127.0.0.1:{server.server_port}/?seed={SEED}&level={LEVEL}",
                      wait_until="domcontentloaded")
            page.wait_for_selector('body[data-engine-ready="true"]', timeout=90000)
            data = helpers.stable(page)
            require(data["event_count"] == 0 and data["view"]["turn"] == "ASSISTED",
                    "Expected the assisted player to start with seed 43")

            def capture(filename, description):
                current = helpers.stable(page)
                check_view(current)
                require(page.locator("#hand button").count() == len(current["view"]["hand"]),
                        "Rendered hand does not match the public view")
                require(page.locator("#cpu-hand .tile-back").count() == current["view"]["opponent_count"],
                        "Rendered CPU count differs")
                page.mouse.move(3, 3)
                page.evaluate("async () => { await document.fonts.ready; "
                              "await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }")
                page.screenshot(path=str(output / filename), full_page=True)
                snapshot_name = Path(filename).with_suffix(".json").name
                write_json(output / snapshot_name, {
                    "context": description, "seed": SEED, "captured_at_utc": now(),
                    "state": current, "selected_level": page.locator("#level").input_value(),
                    "advice_visible": page.locator("#advice").is_visible(),
                    "result_text": page.locator("#result").inner_text()
                        if current["view"]["terminal"] else None,
                })
                screenshots.append({
                    "file": filename, "context": description, "public_snapshot": snapshot_name,
                    "sha256": hashlib.sha256((output / filename).read_bytes()).hexdigest(),
                    "snapshot_sha256": hashlib.sha256((output / snapshot_name).read_bytes()).hexdigest(),
                    "seed": SEED, "level": current["level"],
                    "confirmed_events": current["event_count"],
                    "own_tiles": len(current["view"]["hand"]),
                    "opponent_tiles": current["view"]["opponent_count"],
                    "chain_tiles": len(current["view"]["chain"]),
                    "pending_proposal": current["pending"],
                    "ranking_rows": len(current["ranking"]),
                    "terminal": current["view"]["terminal"],
                })
                print("Captured:", filename, "confirmed events:", current["event_count"], flush=True)

            capture("01-mano-iniziale.png", "Inizio reale: sette tessere proprie, sette CPU coperte, tavolo vuoto; consigli nascosti.")
            options = page.locator("#level option").evaluate_all(
                "nodes => nodes.map(n => ({value:n.value, text:n.textContent}))")
            require([x["value"] for x in options] == ["1", "2", "3", "4", "5"], "Unexpected level options")
            for level in range(1, 6):
                page.locator("#level").select_option(str(level))
                page.wait_for_function("level => !busy && state.level === level", arg=level)
                actions.append({"action": "select_level", "level": level, "confirmed_events": 0})
                capture(f"04-livello-{level}.png", f"Selettore originale della CPU impostato sul livello {level}; stessa mano e zero eventi.")
            page.locator("#level").select_option(str(LEVEL))
            page.wait_for_function("level => !busy && state.level === level", arg=LEVEL)

            progress_captured = advice_captured = False
            cpu_decisions = []
            for _ in range(90):
                data = helpers.stable(page)
                check_view(data)
                if data["view"]["terminal"]:
                    require(progress_captured and advice_captured, "Missing intermediate captures")
                    capture("05-fine-partita.png", "Esito effettivo della stessa partita, raggiunto confermando le mosse nell'interfaccia; nessun risultato imposto.")
                    final = data
                    break
                if (not data["pending"] and data["view"]["turn"] == "ASSISTED"
                        and data["event_count"] >= 2 and len(data["legal_moves"]) >= 2
                        and not advice_captured):
                    capture("02-partita-in-corso.png", "Partita in corso: catena confermata, estremi, nostra mano e avversario con tessere coperte.")
                    progress_captured = True
                    page.locator("#show-advice").check()
                    page.wait_for_function("!busy && state.ranking.length > 0")
                    ranked = helpers.stable(page)
                    require(len(ranked["ranking"]) == len(ranked["legal_moves"]), "Incomplete ranking")
                    require(page.locator("#ranking .rank-row").count() == len(ranked["ranking"]),
                            "Ranking rows are not rendered")
                    capture("03-classifica-consiglio-ai.png", "Consigli attivati con il checkbox originale: tutte le mosse legali ordinate, utilità e spiegazioni; prima riga raccomandata.")
                    advice_captured = True
                    page.locator("#show-advice").uncheck()
                    data = helpers.stable(page)
                if data["pending"]:
                    require(data["pending"]["legal"], "Illegal proposal")
                    if data["pending"]["player"] == "OPPONENT":
                        require(data["cpu_diagnostics"]["requested_depth"] == LEVEL,
                                "CPU is not using the requested engine level")
                        cpu_decisions.append(data["cpu_diagnostics"])
                    # Choose a real, available vertical presentation when possible.
                    # These buttons change presentation only, through the shipped UI.
                    if not data["pending"]["move"].get("pass"):
                        for direction in ["Posa verso il basso", "Posa verso l’alto"]:
                            button = page.get_by_role("button", name=direction, exact=True)
                            if button.is_enabled():
                                button.click()
                                actions.append({"action": "select_pose_direction", "button": direction,
                                                "before_event": data["event_count"]})
                                break
                    actions.append({"action": "confirm", "proposal": data["pending"],
                                    "before_event": data["event_count"]})
                    before = data["event_count"]
                    page.locator("#confirm").click()
                    page.wait_for_function("count => !busy && state.event_count === count + 1", arg=before)
                elif data["view"]["turn"] == "OPPONENT":
                    page.locator("#cpu-play").click()
                else:
                    # Existing test helper: largest-pip legal tile, no AI advice or hidden hand.
                    helpers.propose(page, data)
            else:
                raise RuntimeError("The actual game did not finish")
            require(not errors and not console_errors, f"Browser errors: {errors}; {console_errors}")
            require(sources() == original_hashes, "Delivered sources changed during capture")
            report = {
                "status": "PASS", "capture_started_at_utc": capture_started,
                "capture_finished_at_utc": now(), "display_timezone": "Europe/Madrid",
                "approved_tag": "consegna-v1.0", "approved_source_commit": APPROVED,
                "build_source_commit": manifest["source_commit"],
                "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "approved_files_byte_identical_before_and_after": len(original_hashes),
                "approved_file_sha256": original_hashes,
                "source": "Local build of the delivered browser simulator; not the public deployed site",
                "runtime": manifest["runtime"], "engine_manifest": manifest,
                "browser": "Chromium", "browser_version": browser_version, "headless": True,
                "playwright_version": importlib.metadata.version("playwright"),
                "python": platform.python_version(), "platform": platform.platform(),
                "viewport": VIEWPORT, "device_scale_factor": 1,
                "tls_transport": "verified urllib trust store" if args.environment_tls else "browser",
                "tls_verification_disabled": False,
                "screenshots_modified_after_capture": False,
                "mocked_engine_or_state": False, "dom_modified_for_capture": False,
                "seed": SEED, "played_level": LEVEL,
                "human_input": "Automated real UI clicks: largest-pip visible legal move, not a human strength evaluation",
                "cpu": "Unchanged delivered StrategyEngine in Pyodide Web Worker",
                "level_options": options, "screenshots": screenshots,
                "confirmed_actions": actions, "final_public_view": final,
                "cpu_decisions": cpu_decisions, "page_errors": errors, "console_errors": console_errors,
                "physical_camera_integration": "NOT_RUN; not implemented in this cloud handoff",
                "new_strategy_tournament": "NOT_RUN",
            }
            write_json(output / "PROVENIENZA.json", report)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(json.dumps({"status": "PASS", "screenshots": len(screenshots),
                      "confirmed_events": final["event_count"], "winner": final["view"]["winner"],
                      "reason": final["view"]["reason"], "browser_errors": len(errors) + len(console_errors)},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
