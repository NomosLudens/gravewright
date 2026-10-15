# Gravewright Tactics — Gate 4 QA

**Status: PARTIAL — G4 is not approved.** The backend terrain model and authenticated WebSocket flow passed local QA. Browser rendering and visual compatibility remain unverified because the desktop browser bridge could not initialize.

## Preserved checkout

- Checkout: `/home/tonyus-dev/Portifolio/gravewright`
- Branch: `feat/tactics-godot-transport-20261014`
- Starting HEAD: `3820dd5dfccdac4786ec32a162ba4d0a593e2fa5`
- Remote branch was still at `30617b4ceb5d7aabf1d3465973157632045710e4` when checked; local branch had the two G0/G2/G3 commits ahead of it.
- Existing Godot source WIP and `.godot/` export/cache were retained. No operational campaign data, merge, or deployment was used.
- QA SQLite and media were isolated under `/tmp/gravewright-tactics-qa-20261015/`; `data/gravewright.sqlite3` was not opened for QA or modified. QA campaign and account identifiers, passwords, and cookies are omitted.

## Implementation and automated evidence

- Added scene-owned `TacticalTerrain`, `TerrainCell`, and `TerrainConnection` models with schema and terrain revisions. Initialization creates persisted cells; the only terrain values are KALLÍSTIS `NORMAL`, `DIFICIL`, `SEVERO`, and `INTRANSPONIVEL`.
- GM edits use the existing idempotent `maps.command` path, validate expected versions, persist, and trigger the existing authorized layer refresh. The public projection includes cells, movement costs, elevation, and connections; `canEdit` is role-scoped.
- Terrain-backed movement validates every orthogonal step and occupied footprint, passability, wall crossing, destination terrain cost, and every floor-height transition. The transition needs a persisted stair or ramp connection. KALLÍSTIS movement multipliers are reused by combat allowance accounting. Scenes without tactical terrain keep the prior movement contract.
- Floor elevation and token elevation are related as `Token.elevation = floor elevation + existing offset above floor`; only moves on opted-in tactical scenes adjust token elevation. Explicit GM wall overrides are stored in the command receipt.
- Focused map/token/combat run: **14 tests passed**.
- Full Django suite: **405 tests passed**. The warning `post-session backup failed: backup_drive_upload_failed` is the expected failure-path test in `gravewright/administration/test_post_session_backup.py`; the test deliberately injects that error and asserts the response.
- `manage.py check`: passed. `makemigrations --check --dry-run`: no changes detected. Godot 4.6.3 Web Compatibility export completed after the final GDScript projection adjustment. `git diff --check`: passed.

## Authenticated QA protocol proof

- QA origin: `http://127.0.0.1:3001`.
- Authenticated route: `/game/<authorized-campaign-id>/tactics/`. Both GM and player HTTP logins returned 200 and the authorized export route returned 200; anonymous route access redirected to login (302). The traditional campaign route returned HTTP 200 for the player.
- Separate GM and player sessions connected to the running Daphne WebSocket. Both received `table.joined`, `maps.state`, and `tokens.state`; the scene projection contained 256 persisted cells.
- Player move request `d43ff476-e750-4536-9bab-63fd411216d6` received `tokens.ack`. Both live sessions observed the token at `(2,1)`. A newly authenticated WebSocket session read the same position and token revision 3 after reconnect.
- GM terrain edit request `19b4f5d8-d44f-4e49-93e0-725e3151ce7c` was acknowledged. The player received terrain version 8 with 256 cells. Database readback confirmed the token at `(2,1)`, elevation `0`, revision `3`, and the edited `DIFICIL` cell cost `2`.
- Automated negative checks cover uncontrolled movement, off-turn movement, excess movement allowance, impassable terrain, missing height connection, wall crossing without explicit GM override, stale token/terrain revisions, unauthorized scene access, player terrain edits, duplicate requests, and rollback of rejected moves.

## Blocking evidence

`cua_repl` found no available browser surface. Repeated attempts to enumerate or open the local QA page failed before navigation with `Unable to load browser request-header policy`; the bridge's policy service response was blocked by Cloudflare with HTTP 403. A final recheck again returned no browsers and the same policy error. Therefore no browser could render the Godot export or traditional PixiJS canvas during this run.

Still unverified:

- Godot's rendered Knossos terrain, elevation, wall, stair, selection, and reach visuals in an authenticated browser.
- Terrain editing through the rendered GM controls and visual update in the player browser.
- Actual browser reload in Godot, PixiJS canvas representation of the same position, and browser console cleanliness.
- Visual token movement by a second browser participant. The WebSocket transport replication itself passed over two real authenticated sessions.

Do not mark G4 PASS or start G5 until those browser-level checks complete.
