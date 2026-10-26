"""Authoritative scene token commands and ephemeral, recipient-filtered motion."""

import itertools
import math
import uuid
from copy import deepcopy

from django.conf import settings
from django.db import transaction

from gravewright.actors import services as actors
from gravewright.campaigns.models import Campaign
from gravewright.campaigns.systems import resolve_system_id
from gravewright.journals.services import identifier, member
from gravewright.maps import services as maps
from gravewright.maps.models import Receipt
from gravewright.maps.objects import boolean, choice, number

from .models import Token


def control(row, who):
    return actors.access(row.actor, who, True)


def get(value, who):
    t = (
        Token.objects.select_related("actor", "scene")
        .filter(pk=identifier(value), scene__campaign_id=who.campaign_id)
        .first()
    )
    if not t:
        raise maps.MapError("Token not found.", "not_found")
    maps.scene(t.scene_id, who)
    if t.hidden and who.role != "gm":
        raise maps.MapError("Token not found.", "not_found")
    return t


def data(t):
    """Resolve the authoritative sheet source for a linked or snapshot token."""
    return t.actor.data if t.linked else t.snapshot


def presentation(t):
    """Read optional token hints without imposing a sheet schema on systems."""
    raw = data(t)
    config = raw.get('token') if isinstance(raw.get('token'), dict) else {}
    size = config.get('size', 1)
    if type(size) not in (int, float) or not math.isfinite(size) or not 1 <= size <= 100:
        size = 1
    display = config.get('display') if isinstance(config.get('display'), dict) else {}
    bars = raw.get('bars') if isinstance(raw.get('bars'), dict) else {}
    safe_bars = {}
    for key in ('bar_1', 'bar_2'):
        bar = bars.get(key)
        if isinstance(bar, dict) and all(type(bar.get(k)) in (int, float) and math.isfinite(bar[k]) for k in ('value', 'max')):
            safe_bars[key] = {k: bar[k] for k in ('value', 'max')}
    return {'token': {**config, 'size': size, 'display': display}, 'bars': safe_bars}


def appearance(t, config):
    """Keep scene presentation independent of the installed system's sheet schema."""
    saved = t.appearance
    return {
        "nameDisplay": saved.get("nameDisplay", "selected-or-hover"),
        "showTurnIndicator": saved.get("showTurnIndicator", True),
        "bars": {
            key: {
                "visibility": saved.get("bars", {}).get(key, {}).get("visibility",
                    "everyone" if config["display"].get(key, True) else "owner"),
                "color": saved.get("bars", {}).get(key, {}).get("color", default),
            }
            for key, default in (("bar_1", "#4caf50"), ("bar_2", "#3b82f6"))
        },
    }


def clean_appearance(raw, previous):
    if not isinstance(raw, dict) or set(raw) - {"nameDisplay", "showTurnIndicator", "bars"}:
        raise maps.MapError("Invalid token appearance.")
    result = deepcopy(previous)
    if "nameDisplay" in raw:
        result["nameDisplay"] = choice(raw["nameDisplay"], {"always", "selected", "hover", "selected-or-hover"})
    if "showTurnIndicator" in raw:
        result["showTurnIndicator"] = boolean(raw["showTurnIndicator"])
    if "bars" in raw:
        bars = raw["bars"]
        if not isinstance(bars, dict) or set(bars) - {"bar_1", "bar_2"}:
            raise maps.MapError("Invalid token appearance.")
        for key, bar in bars.items():
            if not isinstance(bar, dict) or set(bar) - {"visibility", "color"}:
                raise maps.MapError("Invalid token appearance.")
            if "visibility" in bar:
                result["bars"][key]["visibility"] = choice(bar["visibility"], {"everyone", "owner", "gm"})
            if "color" in bar:
                result["bars"][key]["color"] = maps.color(bar["color"])
    return result


def project(t, who):
    """Expose geometry and only the bars, names and conditions this member sees."""
    sheet = presentation(t)
    config = sheet["token"]
    gm = who.role == "gm"
    own = control(t, who)
    style = appearance(t, config)
    bars = {
        k: {**v, "color": style["bars"][k]["color"]}
        for k, v in sheet["bars"].items()
        if gm or style["bars"][k]["visibility"] == "everyone"
        or style["bars"][k]["visibility"] == "owner" and own
    }
    return {
        "id": str(t.pk),
        "mapId": str(t.scene_id),
        "actorId": str(t.actor_id),
        "actorType": t.actor.type,
        "systemId": resolve_system_id(who.campaign.system),
        "linkMode": "linked" if t.linked else "snapshot",
        "gridX": t.grid_x,
        "gridY": t.grid_y,
        "cells": config["size"],
        "heightCells": config["size"],
        "name": (t.actor.name if t.linked else config.get("name", t.actor.name))
        if gm or own or config["display"].get("name", True)
        else "",
        "imageUrl": actors.image_url(t.actor, "token")
        or actors.image_url(t.actor, "portrait"),
        "version": t.version,
        "hidden": t.hidden,
        "layer": "gm" if t.hidden else "game",
        "locked": t.locked,
        "rotation": t.rotation,
        "elevation": t.elevation,
        "disposition": t.disposition,
        "canControl": own,
        "canOpenSheet": actors.access(t.actor, who),
        "visionEnabled": t.vision_enabled,
        "visionRange": t.vision_range,
        "bars": bars,
        "nameDisplay": style["nameDisplay"],
        "showTurnIndicator": style["showTurnIndicator"],
        **({"appearance": style} if gm else {}),
        "conditions": [
            deepcopy(c) for c in t.conditions if gm or c["visible_to"] == "everyone"
        ],
    }


def rows(scene, who):
    return [
        project(t, who)
        for t in scene.tokens.select_related("actor").prefetch_related("actor__assets")
        if not t.hidden or who.role == "gm"
    ]


def teleport_metadata(visible, candidates):
    """Keep transport markers only for the recipient's current token revisions."""
    if not isinstance(candidates, list):
        return {}
    versions = {row["id"]: row["version"] for row in visible}
    accepted = {}
    for entry in candidates:
        if (isinstance(entry, dict) and isinstance(entry.get("id"), str)
                and type(entry.get("version")) is int
                and versions.get(entry["id"]) == entry["version"]):
            accepted[entry["id"]] = {"id": entry["id"], "version": entry["version"]}
    return {"teleports": list(accepted.values())} if accepted else {}


def state(campaign, user, map_id):
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    return {"mapId": str(scene.pk), "tokens": rows(scene, who)}


def geometry(scene):
    s = {**maps.DEFAULTS, **scene.settings}
    scale = s["imageScale"]
    return (
        s["gridSize"] * scale,
        s["gridOffsetX"] * scale,
        s["gridOffsetY"] * scale,
        scene.width,
        scene.height,
    )


def vision(scene, who):
    cell, ox, oy, _, _ = geometry(scene)
    return (
        [
            {
                "x": ox + (t.grid_x + presentation(t)["token"]["size"] / 2) * cell,
                "y": oy + (t.grid_y + presentation(t)["token"]["size"] / 2) * cell,
                "radius": t.vision_range * cell,
                "elevation": t.elevation,
            }
            for t in scene.tokens.select_related("actor")
            if t.vision_enabled and not t.hidden and control(t, who)
        ]
        if who.role != "gm"
        else []
    )


def position(t, x, y):
    x = number(x, 0)
    y = number(y, 0)
    cell, ox, oy, w, h = geometry(t.scene)
    size = presentation(t)["token"]["size"]
    if x > max(0, (w - ox) / cell - size) or y > max(0, (h - oy) / cell - size):
        raise maps.MapError("Token is outside the map.")
    return x, y


def blocked(t, a, b, walls=None, *, elevation=None):
    cell, ox, oy, _, _ = geometry(t.scene)
    size = data(t)["token"]["size"]
    ax = ox + (a[0] + size / 2) * cell
    ay = oy + (a[1] + size / 2) * cell
    rx = (b[0] - a[0]) * cell
    ry = (b[1] - a[1]) * cell
    for obj in walls if walls is not None else t.scene.elements.filter(kind="walls"):
        w = obj.data
        if (
            w.get("movement_behavior") == "pass"
            or (w["kind"] == "door" and w["door_state"] == "open")
            or (
                w.get("vertical_bottom") is not None
                and (t.elevation if elevation is None else elevation) < w["vertical_bottom"]
            )
            or (
                w.get("vertical_top") is not None
                and (t.elevation if elevation is None else elevation) > w["vertical_top"]
            )
        ):
            continue
        sx = w["x2"] - w["x1"]
        sy = w["y2"] - w["y1"]
        den = rx * sy - ry * sx
        if abs(den) < 1e-9:
            continue
        qx = w["x1"] - ax
        qy = w["y1"] - ay
        if 0 <= (qx * sy - qy * sx) / den <= 1 and 0 <= (qx * ry - qy * rx) / den <= 1:
            return True
    return False


def _tactical_path(t, points):
    """Validate a terrain-backed path and return per-cell costs and final altitude."""
    from gravewright.maps.models import TacticalTerrain
    from gravewright.rules.kallistis_runtime import RuleError, movement_cost

    grid = TacticalTerrain.objects.filter(scene=t.scene).first()
    if not grid:
        return None
    cell_map = {(cell.x, cell.y): cell for cell in grid.cells.all()}
    footprints = []
    size = int(data(t)["token"].get("size", 1))
    for x, y in points:
        if float(x).is_integer() is False or float(y).is_integer() is False:
            raise maps.MapError("Tactical movement must use whole grid cells.")
        footprint = []
        for dy in range(size):
            for dx in range(size):
                cell_x, cell_y = int(x) + dx, int(y) + dy
                if not (0 <= cell_x < grid.width and 0 <= cell_y < grid.height):
                    raise maps.MapError("Movement is outside the tactical grid.")
                cell = cell_map.get((cell_x, cell_y))
                if not cell:
                    raise maps.MapError("Tactical terrain cell is missing.", "conflict")
                if not cell.traversable:
                    raise maps.MapError("Movement enters impassable terrain.", "blocked")
                footprint.append(cell)
        footprints.append(footprint)
    if any(abs(b[0] - a[0]) + abs(b[1] - a[1]) != 1 for a, b in itertools.pairwise(points)):
        raise maps.MapError("Tactical paths must enumerate orthogonally adjacent cells.")

    connection_pairs = {
        frozenset((row.cell_a_id, row.cell_b_id))
        for row in grid.connections.select_related("cell_a", "cell_b")
    }
    costs = []
    for source, destination, source_cells, destination_cells in zip(
        points, points[1:], footprints, footprints[1:]
    ):
        edge_cost = 0
        for a, b in zip(source_cells, destination_cells):
            if a.elevation != b.elevation and frozenset((a.pk, b.pk)) not in connection_pairs:
                raise maps.MapError("A valid stair or ramp is required between these heights.", "blocked")
            try:
                edge_cost = max(
                    edge_cost,
                    movement_cost(
                        int(destination[0] - source[0]),
                        int(destination[1] - source[1]),
                        b.terrain_type,
                    ),
                )
            except RuleError as error:
                raise maps.MapError(str(error), "blocked") from None
        costs.append(edge_cost)
    start_floor, end_floor = footprints[0][0], footprints[-1][0]
    offset = t.elevation - start_floor.elevation
    return costs, end_floor.elevation + offset, [footprint[0] for footprint in footprints]


def movement(t, who, raw, start=None, limit=512, walls=None, *, enforce_combat=False):
    """Validate control, revision, bounds and path collisions without saving a move."""
    if not control(t, who) or t.locked:
        raise maps.MapError("Token is locked or not controlled.", "forbidden")
    actors.revision(t, raw.get("expectedVersion", raw.get("version")))
    end = position(t, raw.get("gridX"), raw.get("gridY"))
    path = raw.get("path", [])
    if not isinstance(path, list) or len(path) > limit:
        raise maps.MapError("Invalid movement path.")
    points = [start or (t.grid_x, t.grid_y)]
    for p in path:
        if isinstance(p, dict):
            candidate = position(t, p.get("gridX"), p.get("gridY"))
        elif isinstance(p, list) and len(p) == 2:
            candidate = position(t, *p)
        else:
            raise maps.MapError("Invalid movement path.")
        if candidate != points[-1]:
            points.append(candidate)
    if end != points[-1]:
        points.append(end)
    tactical = _tactical_path(t, points)
    gm_override = who.role == "gm" and raw.get("gmOverride") is True
    check_walls = who.role != "gm" or (tactical is not None and not gm_override)
    cached_walls = (
        list(t.scene.elements.filter(kind="walls"))
        if check_walls and walls is None
        else []
    )
    if check_walls and any(
        blocked(
            t, a, b, walls if walls is not None else cached_walls,
            elevation=(t.elevation if not tactical else tactical[2][index].elevation + (t.elevation - tactical[2][0].elevation)),
        )
        for index, (a, b) in enumerate(itertools.pairwise(points))
    ):
        raise maps.MapError("Movement blocked by a wall.", "blocked")
    if enforce_combat:
        from gravewright.combat.services import movement_context
        movement_context(
            t,
            who,
            points,
            gm_override=raw.get("gmOverride") is True,
            costs=tactical[0] if tactical else None,
        )
    if tactical:
        t._tactical_elevation_after_move = tactical[1]
    t._gm_movement_override = gm_override and tactical is not None
    return end


@transaction.atomic
def command(campaign, user, action, raw, request_id):
    """Persist changes once; receipt replays rebuild the current visible token state."""
    Campaign.objects.select_for_update().get(pk=campaign)
    who = member(campaign, user)
    from gravewright.journals.services import writable
    writable(who)
    if not isinstance(raw, dict):
        raise maps.MapError("Invalid token command.")
    scene = maps.scene(raw.get("mapId"), who)
    request_id = identifier(request_id)
    previous = Receipt.objects.filter(
        campaign_id=campaign, user_id=user, request_id=request_id
    ).first()
    if previous:
        visible = rows(scene, who)
        return {
            "tokens": visible,
            "createdIds": [
                i
                for i in previous.result.get("createdIds", [])
                if i in {t["id"] for t in visible}
            ],
            **({"movementAudit": previous.result["movementAudit"]}
               if previous.result.get("movementAudit") else {}),
            **teleport_metadata(visible, previous.result.get("teleports")),
        }
    created = []
    presence_changes = []

    def presence(token, before, after, path=()):
        presence_changes.append({"token": token, "id": str(token.pk), "before": before,
                                 "after": after, "path": path})
    movement_audit = None
    if action == "place":
        maps.manage(who)
        actor = actors.get(raw.get("actorId"), who)
        existing = list(actor.tokens.all())
        linked = not existing
        for t in existing:
            if t.linked:
                t.snapshot = deepcopy(actor.data)
                if isinstance(t.snapshot.get('token'), dict):
                    t.snapshot["token"]["name"] = actor.name
                t.linked = False
                t.version += 1
                t.save()
        snapshot = deepcopy(actor.data)
        if isinstance(snapshot.get('token'), dict):
            snapshot["token"]["name"] = actor.name
        t = Token(
            scene=scene, actor=actor, linked=linked, snapshot={} if linked else snapshot
        )
        t.grid_x, t.grid_y = position(t, raw.get("gridX"), raw.get("gridY"))
        t.save()
        created = [str(t.pk)]
        presence(t, None, (t.grid_x, t.grid_y, t.elevation))
    elif action == "move":
        from gravewright.combat.models import MissionInstance
        if MissionInstance.objects.filter(
            scene=scene,
            state__in=(MissionInstance.VICTORY, MissionInstance.DEFEAT, MissionInstance.ABORTED),
        ).exists():
            raise maps.MapError("The tactical mission has ended; movement commands are closed.", "mission_closed")
        t = get(raw.get("id"), who)
        if t.scene_id != scene.pk:
            raise maps.MapError("Token is not in this scene.")
        before=(t.grid_x,t.grid_y,t.elevation)
        t.grid_x, t.grid_y = movement(t, who, raw, enforce_combat=True)
        if hasattr(t, "_tactical_elevation_after_move"):
            t.elevation = t._tactical_elevation_after_move
        if getattr(t, "_gm_movement_override", False):
            movement_audit = {
                "kind": "gm_tactical_movement_override",
                "tokenId": str(t.pk),
                "expectedVersion": raw.get("expectedVersion", raw.get("version")),
            }
        t.version += 1
        t.save()
        from gravewright.maps.zones import movement_events
        movement_events(scene,t,before)
        presence(t, before, (t.grid_x, t.grid_y, t.elevation), raw.get("path", []))
        from gravewright.combat import missions
        missions.after_token_move(t, who, request_id)
    else:
        ids = raw.get("tokenIds")
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 100
            or len(set(map(str, ids))) != len(ids)
        ):
            raise maps.MapError("Invalid token selection.")
        if action == "duplicate" and len(ids) > settings.TOKEN_CREATE_MANY_MAX:
            raise maps.MapError("Token creation limit exceeded.")
        selected = [get(i, who) for i in ids]
        if any(t.scene_id != scene.pk for t in selected):
            raise maps.MapError("Token is not in this scene.")
        rotate = (
            action == "configure"
            and isinstance(raw.get("values"), dict)
            and set(raw["values"]) == {"rotation"}
        )
        conditions = action in {'condition-add', 'condition-remove'}
        if conditions:
            if any(not control(t, who) for t in selected):
                raise maps.MapError('Token is read only.', 'forbidden')
            if action == 'condition-add' and who.role != 'gm' and raw.get('visibility') != 'everyone':
                raise maps.MapError('Only the GM can create hidden conditions.', 'forbidden')
            if action == 'condition-remove' and who.role != 'gm' and any(
                c['condition_id'] == raw.get('conditionId') and c['visible_to'] != 'everyone'
                for t in selected for c in t.conditions
            ):
                raise maps.MapError('Condition not available.', 'forbidden')
        if not rotate and not conditions:
            maps.manage(who)
        for t in selected:
            before = (t.grid_x, t.grid_y, t.elevation)
            if action == "remove":
                presence(t, before, None)
                t.delete()
                continue
            if action == "duplicate":
                snapshot = deepcopy(data(t))
                if isinstance(snapshot.get('token'), dict):
                    snapshot["token"]["name"] = snapshot["token"].get("name", t.actor.name)
                t.pk = uuid.uuid4()
                t.linked = False
                t.snapshot = snapshot
                t.version = 1
                t.sheet_version = 1
                cell, ox, oy, w, h = geometry(scene)
                size = presentation(t)["token"]["size"]
                t.grid_x = min(t.grid_x + 1, max(0, (w - ox) / cell - size))
                t.grid_y = min(t.grid_y + 1, max(0, (h - oy) / cell - size))
                created.append(str(t.pk))
            elif action == "hidden":
                t.hidden = boolean(raw.get("hidden"))
            elif action == "vision":
                t.vision_enabled = boolean(raw.get("enabled"))
                t.vision_range = number(raw.get("range"), 0)
            elif action == "configure":
                if len(selected) != 1 or not control(t, who):
                    raise maps.MapError("Select one controlled token.")
                actors.revision(t, raw.get("expectedVersion"))
                values = raw.get("values")
                if not isinstance(values, dict) or set(values) - {
                    "rotation",
                    "elevation",
                    "locked",
                    "disposition",
                    "appearance",
                }:
                    raise maps.MapError("Invalid token configuration.")
                for k, v in values.items():
                    if k == "appearance":
                        t.appearance = clean_appearance(v, appearance(t, presentation(t)["token"]))
                        continue
                    setattr(
                        t,
                        k,
                        boolean(v)
                        if k == "locked"
                        else choice(v, {"friendly", "neutral", "hostile", "unknown"})
                        if k == "disposition"
                        else number(v) % 360
                        if k == "rotation"
                        else number(v),
                    )
            elif action == "condition-add":
                from gravewright.combat.conditions import duration
                clock = duration(raw.get('duration'))
                if len(t.conditions) >= 100:
                    raise maps.MapError("Too many conditions.")
                description = raw.get('description', '')
                if not isinstance(description, str) or len(description) > 4000:
                    raise maps.MapError('Invalid condition description.')
                t.conditions.append(
                    {
                        "condition_id": uuid.uuid4().hex,
                        "label": maps.title(raw.get("label")),
                        "description": description.strip(),
                        "kind": choice(
                            raw.get("kind"), {"neutral", "positive", "negative"}
                        ),
                        "visible_to": choice(raw.get("visibility"), {"everyone", "gm"}),
                        **({'duration': clock} if clock else {}),
                    }
                )
            elif action == "condition-remove":
                t.conditions = [
                    c
                    for c in t.conditions
                    if c["condition_id"] != raw.get("conditionId")
                ]
            else:
                raise maps.MapError("Unknown token command.")
            t.version += 1
            t.save()
            if action == "duplicate":
                presence(t, None, (t.grid_x, t.grid_y, t.elevation))
            elif action == "configure" and before[2] != t.elevation:
                presence(t, before, (t.grid_x, t.grid_y, t.elevation))
    from gravewright.maps.regions import token_events
    from gravewright.maps.blueprint_delays import automation_request
    with automation_request(request_id) as world:
        token_events(scene, who, presence_changes)
    if action == "hidden" or action == "configure" and "disposition" in raw.get("values", {}):
        # Filter metadata is configuration, so establish presence without events.
        from gravewright.maps.regions import rebaseline
        rebaseline(scene)
    visible = rows(scene, who)
    teleports = [{"id": row["id"], "version": row["version"]}
                 for row in visible if row["id"] in world.teleported]
    receipt_result = {
        "createdIds": created,
        **teleport_metadata(visible, teleports),
        **({"movementAudit": movement_audit} if movement_audit else {}),
    }
    result = {"tokens": visible, **receipt_result}
    Receipt.objects.create(
        campaign_id=campaign, user_id=user, request_id=request_id, result=receipt_result
    )
    from gravewright.realtime.dispatch import changed
    changed(campaign,user,'tokens',action,request_id,{"mapId": str(scene.pk), **result})
    return result


def preview(campaign, user, map_id, positions, previous):
    """Validate transient drag coordinates without changing persisted positions."""
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    if not isinstance(positions, list) or not 1 <= len(positions) <= 100:
        raise maps.MapError("Invalid drag preview.")
    result = []
    seen = set()
    available = {str(t.pk): t for t in scene.tokens.select_related("actor")}
    walls = list(scene.elements.filter(kind="walls")) if who.role != "gm" else []
    for p in positions:
        if not isinstance(p, dict):
            raise maps.MapError("Invalid drag preview.")
        t = available.get(str(identifier(p.get("id"))))
        if t is None or (t.hidden and who.role != "gm"):
            raise maps.MapError("Token not available.")
        t.scene = scene
        if t.scene_id != scene.pk or t.pk in seen:
            raise maps.MapError("Invalid drag scope.")
        seen.add(t.pk)
        x, y = movement(t, who, p, previous.get(str(t.pk)), 16, walls)
        result.append({"id": str(t.pk), "gridX": x, "gridY": y, "version": t.version})
    return result


def motion_for(campaign, user, map_id, positions):
    """A preview carries only coordinates, never another recipient's sheet projection."""
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    queryset = scene.tokens.filter(pk__in=[p["id"] for p in positions])
    if who.role != "gm":
        queryset = queryset.filter(hidden=False)
    versions = {
        str(pk): version for pk, version in queryset.values_list("pk", "version")
    }
    return [p for p in positions if versions.get(p["id"]) == p["version"]]
