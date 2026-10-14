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
3. Serve the exported files from **the same origin** as the existing authenticated Gravewright instance. Do not deploy them to an unrelated site, expose session credentials, or bypass authentication. **A Django route/static publishing pipeline for this export is not yet implemented.**
4. Load the export with the existing authenticated browser session and `?campaign=<UUID>`; only a campaign you belong to will connect. Players see only the broadcast scene; GM also needs a broadcast for this first client.
5. Click a unit with `canControl=true`, then a single adjacent, empty cell. Watch the actual server acknowledgment and verify the updated position in the ordinary Gravewright table and after refresh.

The client never updates the position locally until an authorized `tokens.state` arrives. Token movement remains subject to existing service authorization, wall/collision checks, active turn and movement allowance.

**No Godot runtime, browser export or deployment was available in the authoring environment. This code has NOT passed Godot parsing, browser smoke testing, authentication testing or the documented gates G0–G11. Treat it as an unverified implementation, not a working product.**

## Gate to promote

- Parse and run with installed Godot 4.6 headless and in a browser.
- Use two authenticated users and a real prepared Gravewright campaign.
- Prove move -> acknowledgment -> second-client update -> reload persistence; prove invalid moves and forbidden actor commands are rejected.
- Verify all existing PixiJS table workflows still work.
- Only then prepare the first isometric Knossos art and server-authoritative elevation.

License: the new GDScript is contributed to the Gravewright repository under its existing GPL-3.0-only terms and any applicable contribution rules.
