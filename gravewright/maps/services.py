"""Campaign-scoped scenes and publication commands, independent of HTTP/Channels."""

from io import BytesIO
import math
import re
import uuid
from django.conf import settings as django_settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import member, identifier
from .models import Scene, Tile, Folder, Broadcast, Receipt

DEFAULTS = {
    "gridSize": 70,
    "gridOffsetX": 0,
    "gridOffsetY": 0,
    "imageScale": 1,
    "measureValue": 1,
    "measureUnit": "",
    "gridVisible": True,
    "gridColor": "#79d9c0",
    "gridOpacity": 0.4,
}


class MapError(Exception):
    def __init__(self, message, code="invalid_input"):
        super().__init__(message)
        self.code = code


def title(value, limit=120):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MapError(f"Use a name with 1 to {limit} characters.")
    return value.strip()


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise MapError("Invalid color.")
    return value


def settings(raw, previous=None):
    if not isinstance(raw, dict):
        raise MapError("Invalid scene settings.")
    result = {**DEFAULTS, **(previous or {})}
    for key, low, high in [
        ("gridSize", 1, 10000),
        ("gridOffsetX", -1000000, 1000000),
        ("gridOffsetY", -1000000, 1000000),
        ("imageScale", 0.01, 100),
        ("measureValue", 0.0001, 1000000),
        ("gridOpacity", 0, 1),
    ]:
        if key not in raw:
            continue
        value = raw[key]
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not low <= value <= high
        ):
            raise MapError(f"Invalid {key}.")
        result[key] = value
    if "measureUnit" in raw:
        if not isinstance(raw["measureUnit"], str) or len(raw["measureUnit"]) > 24:
            raise MapError("Invalid measurement unit.")
        result["measureUnit"] = raw["measureUnit"].strip()
    if "gridColor" in raw:
        result["gridColor"] = color(raw["gridColor"])
    if "gridVisible" in raw:
        if type(raw["gridVisible"]) is not bool:
            raise MapError("Invalid grid visibility.")
        result["gridVisible"] = raw["gridVisible"]
    if "initialView" in raw:
        value = raw["initialView"]
        if value is None:
            result.pop("initialView", None)
        elif (
            not isinstance(value, dict)
            or any(
                type(value.get(k)) not in (int, float) or not math.isfinite(value[k])
                for k in ("x", "y", "scale")
            )
            or not 0.00001 <= value["scale"] <= 1000
            or max(abs(value["x"]), abs(value["y"])) > 1e9
        ):
            raise MapError("Invalid initial view.")
        else:
            result["initialView"] = {k: value[k] for k in ("x", "y", "scale")}
    return result


def manage(who):
    if who.role != "gm":
        raise MapError("Only the GM can manage scenes.", "forbidden")


def create_from_upload(
    campaign_id, user_id, raw_name, raw_settings, incoming, *, activate=False,
    reject_duplicate=False,
):
    """Validate a raster, persist its tile pyramid and optionally publish it."""
    stored = []
    try:
        who = member(campaign_id, user_id)
        manage(who)
        name = title(raw_name)
        options = settings(raw_settings)
        visibility = raw_settings.get("visibility", "players")
        if visibility not in ("players", "gm"):
            raise MapError("Invalid visibility.")
        target = folder(raw_settings.get("groupId"), who)
        if incoming is None or incoming.size > django_settings.MAP_UPLOAD_MAX_BYTES:
            raise MapError("Choose a map image within the configured upload limit.")
        try:
            with Image.open(incoming) as source:
                if source.format not in ("PNG", "JPEG", "WEBP", "TIFF"):
                    raise ValueError("format")
                if source.width * source.height > getattr(
                    django_settings, "GRAVEWRIGHT_MAP_MAX_PIXELS", 64_000_000
                ):
                    raise MapError("This map exceeds the server image pixel limit.")
                if (
                    source.width > django_settings.MAP_IMAGE_MAX_WIDTH
                    or source.height > django_settings.MAP_IMAGE_MAX_HEIGHT
                ):
                    raise MapError("Map dimensions exceed the configured limit.")
                levels = max(0, math.ceil(math.log2(max(source.size) / 512)))
                if sum(
                    math.ceil(source.width / (512 * 2**lod))
                    * math.ceil(source.height / (512 * 2**lod))
                    for lod in range(levels + 1)
                ) > django_settings.MAP_MAX_TILE_COUNT:
                    raise MapError("Map tile count exceeds the configured limit.")
                source.load()
                raster = ImageOps.exif_transpose(source).convert("RGBA")
        except (
            UnidentifiedImageError,
            ValueError,
            OSError,
            Image.DecompressionBombError,
        ):
            raise MapError("Choose a valid PNG, JPEG, WebP or TIFF image.") from None

        width, height = raster.size
        max_lod = max(0, math.ceil(math.log2(max(width, height) / 512)))
        tiles = []
        try:
            for lod in range(max_lod + 1):
                if lod:
                    level = raster.resize(
                        (math.ceil(width / 2**lod), math.ceil(height / 2**lod)),
                        Image.Resampling.LANCZOS,
                    )
                else:
                    level = raster
                try:
                    for y in range(math.ceil(level.height / 512)):
                        for x in range(math.ceil(level.width / 512)):
                            with level.crop(
                                (
                                    x * 512,
                                    y * 512,
                                    min((x + 1) * 512, level.width),
                                    min((y + 1) * 512, level.height),
                                )
                            ) as chunk:
                                content = BytesIO()
                                chunk.save(content, format="WEBP", lossless=True)
                            path = default_storage.save(
                                "maps/tiles/" + uuid.uuid4().hex + ".webp",
                                ContentFile(content.getvalue()),
                            )
                            stored.append(path)
                            tiles.append(
                                Tile(
                                    lod=lod,
                                    x=x,
                                    y=y,
                                    file=path,
                                    byte_size=len(content.getvalue()),
                                )
                            )
                finally:
                    if lod:
                        level.close()
        finally:
            raster.close()

        with transaction.atomic():
            Campaign.objects.select_for_update().get(pk=campaign_id)
            who = member(campaign_id, user_id)
            manage(who)
            if reject_duplicate and Scene.objects.filter(
                campaign_id=campaign_id, name=name
            ).exists():
                raise MapError("A scene with this name already exists.", "already_exists")
            target = folder(raw_settings.get("groupId"), who)
            row = Scene.objects.create(
                campaign_id=campaign_id,
                name=name,
                folder=target,
                visibility=visibility,
                width=width,
                height=height,
                max_lod=max_lod,
                settings=options,
            )
            for tile in tiles:
                tile.scene = row
            Tile.objects.bulk_create(tiles)
            if activate:
                Broadcast.objects.update_or_create(
                    campaign_id=campaign_id, defaults={"scene": row}
                )
        stored.clear()
        return row
    finally:
        for path in stored:
            default_storage.delete(path)


def scene(scene_id, who, write=False):
    """Resolve a campaign scene; non-GMs can read only the current player broadcast."""
    row = Scene.objects.filter(
        pk=identifier(scene_id), campaign_id=who.campaign_id
    ).first()
    if write:
        manage(who)
    if row is None or (
        who.role != "gm"
        and (
            row.visibility != "players"
            or not Broadcast.objects.filter(
                campaign_id=who.campaign_id, scene=row
            ).exists()
        )
    ):
        raise MapError("Scene not found or access denied.", "not_found")
    return row


def folder(folder_id, who):
    if not folder_id:
        return None
    row = Folder.objects.filter(
        pk=identifier(folder_id), campaign_id=who.campaign_id
    ).first()
    if row is None:
        raise MapError("Folder not found.")
    return row


def validate_nesting(who, target, moving=None):
    """Original scene tree: root depth zero, at most two nested levels."""
    parents = dict(
        Folder.objects.filter(campaign_id=who.campaign_id).values_list(
            "id", "parent_id"
        )
    )
    chain = set()
    cursor = target.pk if target else None
    while cursor:
        if cursor in chain or (moving and cursor == moving.pk):
            raise MapError("A folder cannot contain itself.")
        chain.add(cursor)
        cursor = parents.get(cursor)

    def height(pk):
        children = [child for child, parent in parents.items() if parent == pk]
        return 1 + max(map(height, children)) if children else 0

    if len(chain) + (height(moving.pk) if moving else 0) > 2:
        raise MapError("Scene folders support at most two nested levels.")


def view(row):
    return {
        "id": str(row.pk),
        "containerId": str(row.campaign_id),
        "blockId": str(row.block_id),
        "name": row.name,
        "status": "ready",
        "width": row.width,
        "height": row.height,
        "tileSize": row.tile_size,
        "maxLod": row.max_lod,
        "viewportLimits": {"width":django_settings.SCENE_VIEWPORT_MAX_WIDTH_CHUNKS,"height":django_settings.SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS,"area":django_settings.SCENE_VIEWPORT_MAX_AREA_CHUNKS},
        "groupId": str(row.folder_id) if row.folder_id else None,
        "visibility": row.visibility,
        **row.settings,
        "version": row.version,
        "createdAt": int(row.created_at.timestamp() * 1000),
        "updatedAt": int(row.updated_at.timestamp() * 1000),
    }


def state(campaign_id, user_id):
    who = member(campaign_id, user_id)
    active = (
        Broadcast.objects.filter(campaign_id=campaign_id)
        .select_related("scene")
        .first()
    )
    broadcast = active.scene if active else None
    if broadcast and broadcast.visibility == "gm" and who.role != "gm":
        broadcast = None
    maps = (
        Scene.objects.filter(campaign_id=campaign_id)
        if who.role == "gm"
        else ([broadcast] if broadcast else [])
    )
    folders = Folder.objects.filter(campaign_id=campaign_id) if who.role == "gm" else []
    return {
        "is_gm": who.role == "gm",
        "maps": [view(row) for row in maps],
        "activeMapId": str(broadcast.pk) if broadcast else None,
        "folders": [
            {
                "id": str(row.pk),
                "containerId": str(row.campaign_id),
                "parentId": str(row.parent_id) if row.parent_id else None,
                "label": row.label,
                "color": row.color,
                "tone": row.tone,
            }
            for row in folders
        ],
    }


def manifest(row):
    width = row.width
    height = row.height
    return {
        "mapId": str(row.pk),
        "blockId": str(row.block_id),
        "width": width,
        "height": height,
        "tileSize": row.tile_size,
        "maxLod": row.max_lod,
        "levels": [
            {
                "lod": lod,
                "width": math.ceil(width / 2**lod),
                "height": math.ceil(height / 2**lod),
                "columns": math.ceil(row.width / (row.tile_size * 2**lod)),
                "rows": math.ceil(row.height / (row.tile_size * 2**lod)),
            }
            for lod in range(row.max_lod + 1)
        ],
        "tileUrlTemplate": f"/api/maps/{row.pk}/tiles/{{lod}}/{{x}}/{{y}}.webp",
    }


def command(campaign_id, user_id, action, payload, request_id):
    """Apply an authorized scene mutation once and enqueue committed invalidations."""
    if not isinstance(action, str) or not isinstance(payload, dict):
        raise MapError("Invalid command.")
    rid = identifier(request_id)
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = member(campaign_id, user_id)
        from gravewright.journals.services import writable
        writable(who)
        if not (
            action == "objects"
            and (payload.get("area") == "markers" or payload.get("area") == "walls" and payload.get("action") == "door")
        ):
            manage(who)
        receipt = Receipt.objects.filter(
            campaign_id=campaign_id, user_id=user_id, request_id=rid
        ).first()
        if receipt:
            return receipt.result
        result = apply(who, action, payload)
        Receipt.objects.create(
            campaign_id=campaign_id, user_id=user_id, request_id=rid, result=result
        )
        from gravewright.realtime.dispatch import changed
        changed(campaign_id,user_id,'maps',action,rid,result)
    return result


def apply(who, action, p):
    if action == "objects":
        from .objects import apply as object_command

        row = scene(p.get("mapId"), who)
        return object_command(
            row, who, p.get("area"), p.get("action"), p.get("data", {})
        )
    if action.startswith("folder-"):
        if action == "folder-create":
            target = folder(p.get("parentId"), who)
            validate_nesting(who, target)
            row = Folder.objects.create(
                campaign_id=who.campaign_id,
                parent=target,
                label=title(p.get("label"), 60),
                color=color(p.get("color", "#c9a44c")),
            )
        else:
            row = folder(p.get("folderId"), who)
            if row is None:
                raise MapError("Folder not found.")
            if action == "folder-update":
                if "label" in p:
                    row.label = title(p["label"], 60)
                if "color" in p:
                    row.color = color(p["color"])
                if "parentId" in p:
                    target = folder(p["parentId"], who)
                    ancestor = target
                    while ancestor:
                        if ancestor.pk == row.pk:
                            raise MapError("A folder cannot contain itself.")
                        ancestor = ancestor.parent
                    validate_nesting(who, target, row)
                    row.parent = target
                row.save()
            elif action == "folder-delete":
                if p.get("recursive") is True:
                    ids = {row.pk}
                    while True:
                        children = set(
                            Folder.objects.filter(parent_id__in=ids).values_list(
                                "pk", flat=True
                            )
                        )
                        if children <= ids:
                            break
                        ids |= children
                    Scene.objects.filter(folder_id__in=ids).delete()
                    Folder.objects.filter(pk__in=ids).delete()
                else:
                    Folder.objects.filter(parent=row).update(parent=row.parent)
                    Scene.objects.filter(folder=row).update(folder=row.parent)
                    row.delete()
                return {}
            else:
                raise MapError("Unknown folder command.")
        return {"folderId": str(row.pk)}
    row = scene(p.get("mapId"), who, write=True)
    if action == "activate":
        Broadcast.objects.update_or_create(
            campaign_id=who.campaign_id, defaults={"scene": row}
        )
    elif action == "update":
        if type(p.get("version")) is not int or p["version"] != row.version:
            raise MapError(
                "The scene changed. Reopen its settings and try again.", "conflict"
            )
        raw = p.get("settings")
        if not isinstance(raw, dict):
            raise MapError("Invalid scene settings.")
        if "name" in raw:
            row.name = title(raw["name"])
        if "visibility" in raw:
            if raw["visibility"] not in ["players", "gm"]:
                raise MapError("Invalid visibility.")
            row.visibility = raw["visibility"]
        if "groupId" in raw:
            row.folder = folder(raw["groupId"], who)
        row.settings = settings(raw, row.settings)
        row.version += 1
        row.save()
    elif action == "move":
        row.folder = folder(p.get("groupId"), who)
        row.version += 1
        row.save()
    elif action == "delete":
        row.delete()
        return {}
    else:
        raise MapError("Unknown scene command.")
    return {"map": view(row)}


def ping(campaign_id, user_id, payload):
    who = member(campaign_id, user_id)
    if not isinstance(payload, dict):
        raise MapError("Invalid ping.")
    row = scene(payload.get("mapId"), who)
    for key, maximum in [("x", row.width), ("y", row.height)]:
        value = payload.get(key)
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= value <= maximum
        ):
            raise MapError("Ping outside the map.")
    return {
        "mapId": str(row.pk),
        "x": payload["x"],
        "y": payload["y"],
        "focus": payload.get("focus") is True and who.role == "gm",
        "color": "#f2c679",
    }


def layer_state(campaign_id, user_id, scene_id):
    """Recipient-filtered scene layers; no raw model escapes the public API."""
    from .objects import layer_state as project
    who = member(campaign_id, user_id)
    target = scene(scene_id, who)
    return project(target, who)
