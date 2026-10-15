"""Authenticated local-browser proof for the Gravewright Godot terrain gate.

Run with the isolated G4 QA database:
  GRAVEWRIGHT_DATABASE=/tmp/gravewright-tactics-qa-20261015/gravewright.sqlite3 \
  GRAVEWRIGHT_MEDIA_ROOT=/tmp/gravewright-tactics-qa-20261015/media \
  uv run python tests/e2e/tactics_g4_1_visual.py

The script rotates only the dedicated QA users' passwords in that database,
then authenticates through the product login form in two independent Chrome
contexts. It does not create fake network data or replace browser interactions.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from django import setup


ROOT = Path(__file__).resolve().parents[2]
QA_DB = Path(os.environ.get("GRAVEWRIGHT_DATABASE", ""))
BASE = "http://127.0.0.1:3001"
EVIDENCE = ROOT / "docs/evidence/gravewright-g4.1-2026-10-15"
CAMPAIGN_NAME = "Knossos QA - G4"
GODOT_VIEWPORT = (960, 540)
sys.path.insert(0, str(ROOT))


def provision_qa_passwords() -> tuple[str, dict[str, tuple[str, str]]]:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    setup()
    from gravewright.campaigns.models import Campaign, Membership
    from django.db import connections

    if not QA_DB.is_file() or QA_DB.resolve() == (ROOT / "data/gravewright.sqlite3").resolve():
        raise RuntimeError("Refusing to run without the isolated G4 QA database.")
    campaign = Campaign.objects.get(name=CAMPAIGN_NAME)
    if Campaign.objects.filter(name=CAMPAIGN_NAME).count() != 1:
        raise RuntimeError("Expected exactly one isolated G4 QA campaign.")
    memberships = list(
        Membership.objects.filter(campaign=campaign).select_related("user")
    )
    accounts: dict[str, tuple[str, str]] = {}
    for membership in memberships:
        if membership.role not in {"gm", "player"} or membership.role in accounts:
            raise RuntimeError("QA campaign has unexpected participant roles.")
        password = secrets.token_urlsafe(24)
        membership.user.set_password(password)
        membership.user.save(update_fields=["password"])
        accounts[membership.role] = (membership.user.email, password)
    if set(accounts) != {"gm", "player"}:
        raise RuntimeError("QA campaign must have one GM and one player.")
    connections.close_all()
    return str(campaign.pk), accounts


async def main() -> None:
    from playwright.async_api import async_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    campaign_id, accounts = await asyncio.to_thread(provision_qa_passwords)

    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", 3001)) == 0:
            raise RuntimeError("QA port 3001 is already in use; refusing to attach to an unknown server.")

    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    server = subprocess.Popen(
        [sys.executable, "-m", "daphne", "-b", "127.0.0.1", "-p", "3001", "config.asgi:application"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("Isolated Daphne QA server exited during startup.")
            try:
                with urlopen(BASE + "/login", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Isolated QA server did not become ready on localhost.")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path="/usr/bin/google-chrome",
                headless=True,
                args=[
                    "--no-sandbox", "--disable-dev-shm-usage", "--enable-webgl",
                    "--ignore-gpu-blocklist", "--use-gl=angle", "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            results: dict[str, object] = {
                "qa_origin": BASE,
                "campaign": "Knossos QA - G4 (identifiers omitted)",
                "roles": {},
                "screenshots": [],
                "websocket_types": {},
                "console_errors": [],
                "page_errors": [],
                "failed_requests": [],
                "http_errors": [],
            }
            contexts = {}
            pages = {}
            frames: dict[str, list[dict]] = {"gm": [], "player": []}
            outgoing: dict[str, list[dict]] = {"gm": [], "player": []}
            canvas_metrics: dict[str, dict] = {}
            console_errors: list[str] = []
            page_errors: list[str] = []
            failed_requests: list[str] = []
            cancelled_navigation_requests: list[str] = []
            http_errors: list[str] = []
            expected_tile_404s: list[str] = []
            tile_404_count = {"gm": 0, "player": 0}
            route = f"/game/{campaign_id}/tactics/"

            def safe_message(value: str) -> str:
                return re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<uuid>", value)

            def safe_path(value: str) -> str:
                return safe_message(urlsplit(value).path)

            def record_console(role: str, message) -> None:
                if message.type != "error":
                    return
                if message.text == "Failed to load resource: the server responded with a status of 404 (Not Found)" and tile_404_count[role]:
                    tile_404_count[role] -= 1
                    return
                console_errors.append(f"{role}: {safe_message(message.text)}")

            def record_failed_request(role: str, request) -> None:
                path = urlsplit(request.url).path
                failure = request.failure or "unknown"
                entry = f"{role}: {request.resource_type} {safe_path(request.url)} ({failure})"
                if failure == "net::ERR_ABORTED":
                    cancelled_navigation_requests.append(entry)
                    return
                if path.startswith("/api/maps/") and "/tiles/" in path:
                    expected_tile_404s.append(entry)
                    return
                failed_requests.append(entry)

            def record_response(role: str, response) -> None:
                if response.status < 400:
                    return
                path = urlsplit(response.url).path
                entry = f"{role}: {response.status} {response.request.method} {safe_path(response.url)}"
                if response.status == 404 and path.startswith("/api/maps/") and "/tiles/" in path:
                    expected_tile_404s.append(entry)
                    tile_404_count[role] += 1
                else:
                    http_errors.append(entry)

            def record_ws(role: str, ws) -> None:
                def receive(frame) -> None:
                    raw = frame if isinstance(frame, str) else frame.decode("utf-8", "replace")
                    try:
                        packet = json.loads(raw)
                    except Exception:
                        return
                    if isinstance(packet, dict):
                        frames[role].append(packet)

                def sent(frame) -> None:
                    raw = frame if isinstance(frame, str) else frame.decode("utf-8", "replace")
                    try:
                        packet = json.loads(raw)
                    except Exception:
                        return
                    if isinstance(packet, dict):
                        outgoing[role].append(packet)

                ws.on("framereceived", receive)
                ws.on("framesent", sent)
                ws.on("socketerror", lambda _error: console_errors.append(f"{role}: websocket socketerror"))
                ws.on("close", lambda _close: None)

            async def login(role: str):
                context = await browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
                page = await context.new_page()
                page.on("websocket", lambda ws: record_ws(role, ws))
                page.on("pageerror", lambda error: page_errors.append(f"{role}: {error.name}"))
                page.on("console", lambda message: record_console(role, message))
                page.on("requestfailed", lambda request: record_failed_request(role, request))
                page.on("response", lambda response: record_response(role, response))
                await page.goto(BASE + "/login", wait_until="domcontentloaded")
                email, password = accounts[role]
                await page.locator("#owner-email").fill(email)
                await page.locator("#owner-password").fill(password)
                await page.locator("form.gw-gate__form button[type=submit]").click()
                await page.wait_for_timeout(800)
                session = await context.request.get(BASE + "/api/auth/session")
                if session.status != 200 or not (await session.json()).get("authenticated"):
                    raise RuntimeError(f"Normal login form did not authenticate the {role} QA account.")
                response = await page.goto(BASE + route, wait_until="domcontentloaded")
                if response is None or response.status != 200 or "campaign=" not in page.url:
                    raise RuntimeError(f"Authorized Godot export route failed for {role}.")
                await page.locator("canvas").first.wait_for(state="visible", timeout=30000)
                await page.wait_for_function("() => [...document.querySelectorAll('canvas')].some(c => c.width > 0 && c.height > 0)", timeout=30000)
                for _ in range(100):
                    if any(packet.get("type") == "tokens.state" for packet in frames[role]):
                        break
                    await page.wait_for_timeout(100)
                await page.wait_for_timeout(1000)
                metric = await page.locator("canvas").first.evaluate("c => ({width:c.width,height:c.height,rect:c.getBoundingClientRect().toJSON(),webgl2:!!c.getContext('webgl2')})")
                canvas_metrics[role] = metric
                if not any(packet.get("type") == "tokens.state" for packet in frames[role]):
                    raise RuntimeError(f"{role} Godot client did not receive real tokens.state.")
                if not any(packet.get("type") == "maps.layers" for packet in frames[role]):
                    raise RuntimeError(f"{role} Godot client did not receive persisted terrain layers.")
                contexts[role] = context
                pages[role] = page
                return page

            gm = await login("gm")
            player = await login("player")
            results["roles"] = {"gm": "authenticated via normal login form", "player": "authenticated via normal login form"}
            for role, page in (("gm", gm), ("player", player)):
                screenshot = EVIDENCE / f"godot-{role}.png"
                await page.screenshot(path=str(screenshot), full_page=True)
                results["screenshots"].append(screenshot.name)

            def latest_terrain(role: str) -> dict:
                for packet in reversed(frames[role]):
                    payload = packet.get("payload", {})
                    terrain = payload.get("tacticalTerrain") if isinstance(payload, dict) else None
                    if isinstance(terrain, dict) and terrain.get("cells"):
                        return terrain
                raise RuntimeError(f"No terrain projection received by {role}.")

            gm_terrain = latest_terrain("gm")
            player_terrain = latest_terrain("player")
            if gm_terrain.get("canEdit") is not True or player_terrain.get("canEdit") is not False:
                raise RuntimeError("Terrain editing authorization projection is wrong.")
            if len(gm_terrain.get("cells", [])) != 256 or len(player_terrain.get("cells", [])) != 256:
                raise RuntimeError("The live terrain projection is not a persisted 16x16 grid.")

            async def click_godot(role: str, x: float, y: float, button: str = "left") -> None:
                page = pages[role]
                canvas = page.locator("canvas").first
                rect = await canvas.evaluate("c => c.getBoundingClientRect().toJSON()")
                scale = min(rect["width"] / GODOT_VIEWPORT[0], rect["height"] / GODOT_VIEWPORT[1])
                letterbox_x = (rect["width"] - GODOT_VIEWPORT[0] * scale) / 2
                letterbox_y = (rect["height"] - GODOT_VIEWPORT[1] * scale) / 2
                await page.mouse.click(
                    rect["x"] + letterbox_x + x * scale,
                    rect["y"] + letterbox_y + y * scale,
                    button=button,
                )
                await page.wait_for_timeout(250)

            async def cell_center(role: str, x: int, y: int, elevation: int) -> tuple[float, float]:
                width, _height = GODOT_VIEWPORT
                return width / 2 + (x - y) * 24, 86 + (x + y + 1) * 12 - elevation * 8

            async def wait_cell(role: str, x: int, y: int, kind: str, elevation: int) -> dict:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    terrain = latest_terrain(role)
                    for cell in terrain.get("cells", []):
                        if cell.get("x") == x and cell.get("y") == y and cell.get("terrain_type") == kind and cell.get("elevation") == elevation:
                            return terrain
                    await pages[role].wait_for_timeout(100)
                terrain = latest_terrain(role)
                actual = next((row for row in terrain.get("cells", []) if row.get("x") == x and row.get("y") == y), {})
                errors = [packet.get("payload", {}).get("message", packet.get("payload", {}).get("code", "error")) for packet in frames[role] if packet.get("type") in {"maps.error", "error"}]
                await pages[role].screenshot(path=str(EVIDENCE / f"debug-{role}-cell-{x}-{y}.png"), full_page=True)
                raise RuntimeError(f"Server did not project expected terrain for grid cell ({x},{y}); actual={actual}; version={terrain.get('version')}; errors={errors[-3:]}")

            async def edit_cell(role: str, x: int, y: int, kind: str, elevation: int) -> dict:
                terrain = latest_terrain(role)
                cell = next(row for row in terrain["cells"] if row["x"] == x and row["y"] == y)
                if cell["terrain_type"] == kind and int(cell["elevation"]) == elevation:
                    return terrain
                toolbar_x = {"NORMAL": 60, "DIFICIL": 143, "SEVERO": 225, "INTRANSPONIVEL": 307}
                await click_godot(role, toolbar_x[kind], 75)
                delta = elevation - int(cell["elevation"])
                for _ in range(abs(delta)):
                    await click_godot(role, 429 if delta > 0 else 375, 75)
                point = await cell_center(role, x, y, int(cell["elevation"]))
                await click_godot(role, *point)
                terrain = await wait_cell(role, x, y, kind, elevation)
                return terrain

            # Real toolbar and canvas clicks exercise picking at floor elevations 0, 1, and 2.
            terrain = await edit_cell("gm", 5, 5, "DIFICIL", 0)
            await wait_cell("player", 5, 5, "DIFICIL", 0)
            version0 = int(terrain["version"])

            terrain = await edit_cell("gm", 7, 2, "DIFICIL", 1)
            await wait_cell("player", 7, 2, "DIFICIL", 1)
            version1 = int(terrain["version"])

            terrain = await edit_cell("gm", 7, 3, "SEVERO", 2)
            await wait_cell("player", 7, 3, "SEVERO", 2)
            version2 = int(terrain["version"])

            has_test_stair = any(
                row.get("kind") == "STAIR" and
                {tuple(row.get("from", [])), tuple(row.get("to", []))} == {(7, 2), (7, 3)}
                for row in terrain.get("connections", [])
            )
            if not has_test_stair:
                await click_godot("gm", 500, 75)  # Stair tool
                p = await cell_center("gm", 7, 2, 1)
                await click_godot("gm", *p)
            await gm.screenshot(path=str(EVIDENCE / "godot-gm-picked-level-1.png"), full_page=True)
            results["screenshots"].append("godot-gm-picked-level-1.png")
            if not has_test_stair:
                p = await cell_center("gm", 7, 3, 2)
                await click_godot("gm", *p)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    terrain = latest_terrain("gm")
                    connection = any(
                        row.get("kind") == "STAIR" and
                        {tuple(row.get("from", [])), tuple(row.get("to", []))} == {(7, 2), (7, 3)}
                        for row in terrain.get("connections", [])
                    )
                    if connection:
                        break
                    await gm.wait_for_timeout(100)
                else:
                    raise RuntimeError("Visible stair editing was not persisted and projected.")
                await click_godot("gm", 500, 75)  # return to terrain selection mode
            await wait_cell("player", 7, 3, "SEVERO", 2)
            version3 = int(terrain["version"])

            # Prepare one elevated floor next to the real controlled player token,
            # then move and select that token through the Godot canvas.
            token_state = next(
                packet["payload"] for packet in reversed(frames["player"])
                if packet.get("type") == "tokens.state" and isinstance(packet.get("payload"), dict)
            )
            player_tokens = [row for row in token_state.get("tokens", []) if row.get("canControl")]
            if len(player_tokens) != 1:
                raise RuntimeError("Expected exactly one player-controlled QA token.")
            moving_token = player_tokens[0]
            source_x, source_y = int(moving_token["gridX"]), int(moving_token["gridY"])
            move_performed = source_x == 2 and source_y == 1
            target_x, target_y = source_x, source_y
            target_elevation = int(moving_token.get("elevation", 0))
            version4 = int(latest_terrain("gm")["version"])
            if move_performed:
                occupied = {(int(row["gridX"]), int(row["gridY"])) for row in token_state.get("tokens", [])}
                grid = latest_terrain("gm")
                cells_by_pos = {(row["x"], row["y"]): row for row in grid["cells"]}
                candidates = [(source_x + 1, source_y), (source_x, source_y + 1), (source_x - 1, source_y), (source_x, source_y - 1)]
                target_x, target_y = next(
                    (x, y) for x, y in candidates
                    if (x, y) in cells_by_pos and (x, y) not in occupied
                    and cells_by_pos[(x, y)]["traversable"]
                )
                source_floor = cells_by_pos[(source_x, source_y)]
                target_elevation = int(source_floor["elevation"]) + 1
                terrain = await edit_cell("gm", target_x, target_y, "NORMAL", target_elevation)
                await wait_cell("player", target_x, target_y, "NORMAL", target_elevation)
                await click_godot("gm", 500, 75)
                for x, y in ((source_x, source_y), (target_x, target_y)):
                    floor = next(row for row in latest_terrain("gm")["cells"] if row["x"] == x and row["y"] == y)
                    point = await cell_center("gm", x, y, int(floor["elevation"]))
                    await click_godot("gm", *point)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    terrain = latest_terrain("gm")
                    if any(
                        row.get("kind") == "STAIR" and
                        {tuple(row.get("from", [])), tuple(row.get("to", []))} == {(source_x, source_y), (target_x, target_y)}
                        for row in terrain.get("connections", [])
                    ):
                        break
                    await gm.wait_for_timeout(100)
                else:
                    raise RuntimeError("Master canvas did not persist the player movement stair.")
                await click_godot("gm", 500, 75)  # return to terrain selection mode
                version4 = int(terrain["version"])
                old_gm_count, old_player_count = len(frames["gm"]), len(frames["player"])
                source_center_x = 960 / 2 + (source_x - source_y) * 24
                source_center_y = 86 + (source_x + source_y + 1) * 12 - int(moving_token.get("elevation", 0)) * 8
                await click_godot("player", source_center_x, source_center_y - 10)
                destination = await cell_center("player", target_x, target_y, target_elevation)
                await click_godot("player", *destination)

            def token_at_target(role: str, start: int = 0) -> bool:
                for packet in reversed(frames[role][start:]):
                    if packet.get("type") != "tokens.state":
                        continue
                    for row in packet.get("payload", {}).get("tokens", []):
                        if row.get("canControl") and int(row.get("gridX", -999)) == target_x and int(row.get("gridY", -999)) == target_y and int(row.get("elevation", 0)) == target_elevation:
                            return True
                    return False
                return False

            if move_performed:
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    if token_at_target("player") and token_at_target("gm"):
                        break
                    await player.wait_for_timeout(100)
                else:
                    raise RuntimeError("Godot movement did not persist and replicate the elevated token position.")
                if not any(packet.get("type") == "tokens.ack" for packet in frames["player"][old_player_count:]):
                    raise RuntimeError("Godot movement did not receive tokens.ack.")
                if not token_at_target("gm", old_gm_count):
                    raise RuntimeError("Second authenticated session did not observe the elevated token move.")
            await player.wait_for_timeout(500)
            await gm.wait_for_timeout(500)
            await player.screenshot(path=str(EVIDENCE / "godot-player-token-on-raised-floor.png"), full_page=True)
            results["screenshots"].append("godot-player-token-on-raised-floor.png")
            raised_x = 960 / 2 + (target_x - target_y) * 24
            raised_y = 86 + (target_x + target_y + 1) * 12 - target_elevation * 8
            await click_godot("player", raised_x, raised_y - 10)
            await player.wait_for_timeout(350)
            await player.screenshot(path=str(EVIDENCE / "godot-player-selected-raised-token.png"), full_page=True)
            results["screenshots"].append("godot-player-selected-raised-token.png")
            await gm.screenshot(path=str(EVIDENCE / "godot-gm-observed-raised-token.png"), full_page=True)
            results["screenshots"].append("godot-gm-observed-raised-token.png")
            await gm.wait_for_timeout(500)
            await player.wait_for_timeout(500)
            for role in ("gm", "player"):
                screenshot = EVIDENCE / f"godot-{role}-levels-and-stair.png"
                await pages[role].screenshot(path=str(screenshot), full_page=True)
                results["screenshots"].append(screenshot.name)

            # Authenticated reload must recover the same backend-projected terrain.
            reload_projection = {}
            reload_token_state = {}
            for role in ("gm", "player"):
                before = len(frames[role])
                await pages[role].reload(wait_until="domcontentloaded")
                await pages[role].locator("canvas").first.wait_for(state="visible", timeout=30000)
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    received = frames[role][before:]
                    if any(p.get("type") == "tokens.state" for p in received) and any(p.get("type") == "maps.layers" for p in received):
                        reload_projection[role] = latest_terrain(role)
                        token_packet = next(p for p in reversed(received) if p.get("type") == "tokens.state")
                        reload_token_state[role] = token_packet.get("payload", {})
                        break
                    await pages[role].wait_for_timeout(100)
                if role not in reload_projection:
                    raise RuntimeError(f"{role} did not resync tokens and terrain after page reload.")
                await pages[role].screenshot(path=str(EVIDENCE / f"godot-{role}-reload.png"), full_page=True)
                results["screenshots"].append(f"godot-{role}-reload.png")

            for role, terrain_after_reload in reload_projection.items():
                found = {(cell["x"], cell["y"]): (cell["terrain_type"], cell["elevation"]) for cell in terrain_after_reload["cells"]}
                if found[(5, 5)] != ("DIFICIL", 0) or found[(7, 2)] != ("DIFICIL", 1) or found[(7, 3)] != ("SEVERO", 2):
                    raise RuntimeError(f"Persisted terrain projection did not survive reload for {role}.")
                persisted_player = next((row for row in reload_token_state[role].get("tokens", []) if row.get("canControl")), None)
                if not persisted_player or int(persisted_player.get("gridX", -999)) != target_x or int(persisted_player.get("gridY", -999)) != target_y or int(persisted_player.get("elevation", 0)) != target_elevation:
                    raise RuntimeError(f"Elevated token position did not survive page reload for {role}.")

            # Open the traditional PixiJS table in the same authorized player
            # context and compare its live server snapshot with the Godot move.
            pixi_before = len(frames["player"])
            pixi_response = await player.goto(BASE + f"/game/{campaign_id}", wait_until="domcontentloaded")
            if pixi_response is None or pixi_response.status != 200:
                raise RuntimeError("Traditional PixiJS table route failed after the Godot move.")
            deadline = time.monotonic() + 15
            pixi_token_state = None
            while time.monotonic() < deadline:
                for packet in reversed(frames["player"][pixi_before:]):
                    if packet.get("type") == "tokens.state":
                        pixi_token_state = packet.get("payload", {})
                        break
                if pixi_token_state:
                    break
                await player.wait_for_timeout(100)
            if not pixi_token_state:
                raise RuntimeError("PixiJS table did not receive live tokens.state after navigation.")
            pixi_player_token = next((row for row in pixi_token_state.get("tokens", []) if row.get("canControl")), None)
            if not pixi_player_token or int(pixi_player_token.get("gridX", -999)) != target_x or int(pixi_player_token.get("gridY", -999)) != target_y:
                raise RuntimeError("PixiJS table's live server state differs from the elevated Godot position.")
            await player.wait_for_timeout(1200)
            pixi_canvases = await player.locator("canvas").count()
            await player.screenshot(path=str(EVIDENCE / "pixijs-after-godot-raised-move.png"), full_page=True)
            results["screenshots"].append("pixijs-after-godot-raised-move.png")
            results["pixijs"] = {"route_status": pixi_response.status, "route": safe_path(player.url), "canvas_count": pixi_canvases, "live_token_state_matches_godot": True}

            for role in ("gm", "player"):
                messages = frames[role]
                results["websocket_types"][role] = sorted({str(p.get("type", "")) for p in messages})
                results.setdefault("outgoing_websocket_types", {})[role] = sorted({str(p.get("type", "")) for p in outgoing[role]})
                results.setdefault("canvas", {})[role] = canvas_metrics[role]
            results["terrain_versions"] = [version0, version1, version2, version3, version4]
            results["raised_token"] = {"position": [target_x, target_y], "floor_elevation": target_elevation, "acknowledged": move_performed, "observed_by_gm": move_performed, "persisted_after_reload": True, "movement_replayed": move_performed}
            results["terrain_projection"] = "256 cells; DIFICIL at level 0, SEVERO at levels 1 and 2, stair projected to both roles"
            results["reload"] = "both authenticated pages reloaded and received current tokens and terrain"
            results["authorization"] = "GM canEdit=true; player canEdit=false; player canvas has no authoring toolbar"
            results["console_errors"] = console_errors
            results["page_errors"] = page_errors
            results["failed_requests"] = failed_requests
            results["cancelled_navigation_requests"] = cancelled_navigation_requests
            results["http_errors"] = http_errors
            results["expected_qa_tile_404s"] = expected_tile_404s
            (EVIDENCE / "browser-results.json").write_text(json.dumps(results, indent=2) + "\n")
            (EVIDENCE / "browser-results.json").write_text(json.dumps(results, indent=2) + "\n")
            if console_errors or page_errors or failed_requests or http_errors:
                raise RuntimeError("Browser captured unexpected console, page, HTTP, or request errors.")

            for context in contexts.values():
                await context.close()
            await browser.close()
            print(json.dumps(results, indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
