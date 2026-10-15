# Gravewright Tactics — Godot Transport Gate (experimental)

This directory is the **first, isolated client implementation** for the Gravewright Tactics / Knossos document. It does not change the existing PixiJS table or the Django models.

## What it actually uses

- Godot 4.6, GDScript, Compatibility renderer.
- The **existing session-authenticated** Gravewright WebSocket: `/ws/tables/<campaign-uuid>/`.
- `maps.sync` / `maps.state` to identify the authorized broadcast scene and grid dimensions.
- `tokens.sync` / `tokens.state` to show **only actual server-visible tokens**.
- `tokens.command` with `action: "move"`, token revision and unique request ID; movement is sent **only** for a selected controlled unit and one orthogonally adjacent cell.
- `tokens.ack` triggers a new authorized snapshot. `tokens.error` leaves the displayed position unchanged.
- The existing `session.ping` / `session.pong` heartbeat.

There are **no synthetic actors, hardcoded campaign IDs, client-side HP or simulated network fallbacks**. The grid is procedural visualization, **not** a reconstructed Knossos tileset. This first client does **not** add combat UI, 2.5D elevation rules, licensed sprites, scene objectives or a battle result.

## Launch and current limitations

1. Confirm that the existing Gravewright installation is healthy: log in, open a campaign and move a token in the normal table.
2. Open this project with **Godot 4.6 standard (not .NET)** and export to Web using Compatibility. Obtain the export templates if required.
3. In local development or the Gravewright Runner, the export is served at `/game/<campaign-UUID>/tactics/` from this checkout's `.godot/export` directory. The route requires a signed-in member of that campaign and redirects to the export with the campaign UUID. It is not included in the public URL configuration and is not a deployment path.
4. Open that route with the existing authenticated browser session; only a campaign you belong to will connect. Players see only the broadcast scene; GM also needs a broadcast for this first client.
5. Click a unit with `canControl=true`, then a single adjacent, empty cell. Watch the actual server acknowledgment and verify the updated position in the ordinary Gravewright table and after refresh.

The client never updates the position locally until an authorized `tokens.state` arrives. Token movement remains subject to existing service authorization, wall/collision checks, active turn and movement allowance.

## Validation record — 14 October 2026

- Godot 4.6.3 standard imported this project and ran the main scene headlessly. The Web Compatibility preset exported successfully with single-thread support.
- G0 recovery retained the Gravewright rules and brought the baseline to 398/398. The full regression after the tactical integration ran 400/400 tests.
- G1 passed on Godot 4.6.3 with the Web Compatibility export. The changed revision field was re-exported and the browser flow below ran from that export.
- G2 passed against the isolated local QA instance at `http://127.0.0.1:3001`, using separate authenticated GM and player browser contexts. The route was `/game/<authorized-campaign-id>/tactics/`; the private QA campaign identifier and request IDs are omitted here. Both sessions received `table.joined`, `maps.state`, and `tokens.state`, rendered persisted tokens, and answered the session heartbeat. Anonymous and non-member access was denied, the GM-only scene returned no player tokens, and the player’s GM-only actor command was rejected.
- G3 passed with a real Godot canvas selection and one-cell move. The request received `tokens.ack`; the player and GM received the updated state, the persisted position remained `(2,3)` after reload, and the traditional PixiJS table rendered that same state. The reverse PixiJS-to-Godot move also persisted and replicated.
- Negative movement checks rejected an uncontrolled token, an off-turn token, a stale revision, movement over the remaining allowance, and a wall-blocked move; token position, revision, and combat activation state stayed unchanged. A non-member WebSocket handshake was rejected (browser close code 1006; no `table.joined`).
- QA data used a separate SQLite file and local media root under `/tmp/gravewright-tactics-qa-20261014`; no operational campaign or account was used. QA passwords were transient and are not recorded. Evidence screenshots and WebSocket frames remain in that QA directory.
- The only browser console error was the expected 403 from the deliberate non-member WebSocket probe. No external browser requests were made. `manage.py check` and `git diff --check` passed.

The authenticated transport and one-cell movement are approved for the local QA flow; this does not authorize deployment or replace server-side rules.

## Gate to promote

- Knossos battlefield work has started in the working tree: isometric cell projection, selection, movement reach from the live combat snapshot, and token elevation from the authorized token projection. A QA-only elevation change rendered at elevation 2 and was reset to 0 through the existing token command.
- Each scene can opt into the versioned `TacticalTerrain` grid (`TerrainCell` and `TerrainConnection`); scenes without that row retain the existing movement path. The initial grid is 16×16, with only KALLÍSTIS `NORMAL`, `DIFICIL`, `SEVERO`, and `INTRANSPONIVEL` types. The terrain projection is recipient-authorized and carries its schema and revision.
- GM terrain edits use the existing idempotent `maps.command` path and increment both terrain and scene-layer versions. Players receive the public cell/connection projection. Stale revisions are rejected.
- For terrain-backed scenes, Django validates every orthogonal step, the complete token footprint, passability, KALLÍSTIS cost per destination cell, wall crossings, height transitions, and stair/ramp connections before saving. Combat movement usage consumes that same cost; a grounded token follows the destination floor, while its existing elevation offset above the floor is preserved. An explicit GM wall override is recorded in the command receipt. Non-terrain scenes retain the previous movement contract.
- QA proof on 15 October 2026: focused terrain/token/combat tests passed; Godot 4.6.3 imported and exported the updated Web Compatibility client. Two actual local authenticated WebSocket sessions received persisted tokens; a player move was acknowledged and observed by the GM, and a GM cell edit advanced the player's terrain projection from revision 7 to 8. The QA campaign ID, user IDs, cookies, and passwords are kept out of this README.
- **G4 remains PARTIAL.** This environment could not open a browser through the desktop browser bridge: browser initialization failed while loading its request-header policy, with an external Cloudflare 403. Therefore the new terrain renderer/editor, reload behavior in Godot, PixiJS visual compatibility, and browser-console smoke have not been visually verified. G4 is not approved and G5 has not started.

License: the new GDScript is contributed to the Gravewright repository under its existing GPL-3.0-only terms and any applicable contribution rules.
