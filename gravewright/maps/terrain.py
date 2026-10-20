"""Versioned, scene-owned tactical terrain and its public projection."""

from gravewright.rules.kallistis_runtime import RuleError, terrain_movement_multiplier

from .models import TacticalTerrain, TerrainCell, TerrainConnection
from .services import MapError


def cost_for(terrain_type):
    try:
        return terrain_movement_multiplier(terrain_type)
    except RuleError as error:
        if terrain_type == "INTRANSPONIVEL":
            return 0
        raise MapError(str(error)) from None


def project(scene):
    grid = TacticalTerrain.objects.filter(scene=scene).first()
    if not grid:
        return None
    cells = list(grid.cells.order_by("y", "x").values(
        "x", "y", "terrain_type", "elevation", "traversable", "movement_cost"
    ))
    connections = [
        {
            "from": [row.cell_a.x, row.cell_a.y],
            "to": [row.cell_b.x, row.cell_b.y],
            "kind": row.kind,
        }
        for row in grid.connections.select_related("cell_a", "cell_b").order_by("id")
    ]
    return {
        "schemaVersion": grid.schema_version,
        "version": grid.version,
        "width": grid.width,
        "height": grid.height,
        "cells": cells,
        "connections": connections,
    }


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _cell(grid, x, y):
    if not _integer(x, 0, grid.width - 1) or not _integer(y, 0, grid.height - 1):
        raise MapError("Terrain cell is outside the grid.")
    try:
        return grid.cells.get(x=x, y=y)
    except TerrainCell.DoesNotExist:
        raise MapError("Terrain cell is missing.", "conflict") from None


def apply(scene, action, payload):
    if action == "initialize":
        width, height = payload.get("width", 16), payload.get("height", 16)
        if not _integer(width, 1, 64) or not _integer(height, 1, 64) or width * height > 4096:
            raise MapError("Tactical terrain dimensions must be 1–64 cells per side.")
        if TacticalTerrain.objects.filter(scene=scene).exists():
            raise MapError("Tactical terrain is already initialized.", "conflict")
        grid = TacticalTerrain.objects.create(scene=scene, width=width, height=height)
        TerrainCell.objects.bulk_create([
            TerrainCell(terrain=grid, x=x, y=y)
            for y in range(height) for x in range(width)
        ])
        return {"terrain": project(scene)}

    grid = TacticalTerrain.objects.select_for_update().filter(scene=scene).first()
    if not grid:
        raise MapError("Initialize tactical terrain before editing it.", "not_found")
    expected = payload.get("expectedVersion")
    if not _integer(expected, 1, 2**31 - 1) or expected != grid.version:
        raise MapError("Tactical terrain changed. Reload it before editing.", "conflict")

    if action == "cell":
        cell = _cell(grid, payload.get("x"), payload.get("y"))
        terrain_type = payload.get("terrainType", cell.terrain_type)
        if not isinstance(terrain_type, str) or terrain_type not in {"NORMAL", "DIFICIL", "SEVERO", "INTRANSPONIVEL"}:
            raise MapError("Unknown KALLÍSTIS terrain type.")
        elevation = payload.get("elevation", cell.elevation)
        if not _integer(elevation, -20, 20):
            raise MapError("Terrain elevation must be an integer from -20 to 20.")
        cell.terrain_type = terrain_type
        cell.elevation = elevation
        cell.traversable = terrain_type != "INTRANSPONIVEL"
        cell.movement_cost = cost_for(terrain_type)
        cell.save(update_fields=["terrain_type", "elevation", "traversable", "movement_cost"])
    elif action in {"connect", "disconnect"}:
        ax, ay = payload.get("x"), payload.get("y")
        bx, by = payload.get("toX"), payload.get("toY")
        a, b = _cell(grid, ax, ay), _cell(grid, bx, by)
        if (abs(ax - bx) + abs(ay - by)) != 1:
            raise MapError("A height connection must join orthogonally adjacent cells.")
        a_id, b_id = sorted((a.pk, b.pk))
        if action == "disconnect":
            TerrainConnection.objects.filter(terrain=grid, cell_a_id=a_id, cell_b_id=b_id).delete()
        else:
            if a.elevation == b.elevation:
                raise MapError("A height connection requires different floor elevations.")
            if not a.traversable or not b.traversable:
                raise MapError("A height connection cannot touch impassable terrain.")
            kind = payload.get("kind", "STAIR")
            if not isinstance(kind, str) or kind not in {"STAIR", "RAMP"}:
                raise MapError("Connection must be STAIR or RAMP.")
            TerrainConnection.objects.update_or_create(
                terrain=grid, cell_a_id=a_id, cell_b_id=b_id, defaults={"kind": kind}
            )
    else:
        raise MapError("Unknown tactical terrain command.")
    grid.version += 1
    grid.save(update_fields=["version"])
    return {"terrain": project(scene)}
