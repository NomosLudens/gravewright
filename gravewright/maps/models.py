"""Scene rasters, object layers, broadcasts and shared resource command receipts."""

import uuid
from django.conf import settings
from django.db import models


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    label = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#c9a44c")
    tone = models.CharField(max_length=10, default="accent")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label", "id"]


class Scene(models.Model):
    """Raster scene metadata; block_id is the stable chat/scene context identifier."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    soundscape = models.ForeignKey('gravewright_audio.Playlist', null=True, blank=True, on_delete=models.SET_NULL)
    sound_version = models.PositiveIntegerField(default=1)
    block_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    visibility = models.CharField(
        max_length=8, default="players", choices=[("players", "Players"), ("gm", "GM")]
    )
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    tile_size = models.PositiveIntegerField(default=512)
    max_lod = models.PositiveSmallIntegerField(default=0)
    settings = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]


class Tile(models.Model):
    """One authenticated raster tile at a level of detail and grid coordinate."""
    byte_size = models.PositiveIntegerField(default=0)
    scene = models.ForeignKey(Scene, related_name="tiles", on_delete=models.CASCADE)
    lod = models.PositiveSmallIntegerField()
    x = models.PositiveIntegerField()
    y = models.PositiveIntegerField()
    file = models.FileField(upload_to="maps/tiles/%Y/%m/")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scene", "lod", "x", "y"], name="map_unique_tile"
            )
        ]


class Broadcast(models.Model):
    """The single scene selected for a campaign's player and streamer audience."""
    campaign = models.OneToOneField(
        "gravewright_campaigns.Campaign", primary_key=True, on_delete=models.CASCADE
    )
    scene = models.ForeignKey(Scene, null=True, on_delete=models.SET_NULL)


class Receipt(models.Model):
    """Retry result shared by maps, actors, tokens and table.domain resources."""
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    request_id = models.UUIDField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user", "request_id"], name="map_unique_command"
            )
        ]


class SceneState(models.Model):
    """Versioned scene-wide environment state, separate from individual objects."""
    scene = models.OneToOneField(
        Scene, related_name="environment", primary_key=True, on_delete=models.CASCADE
    )
    lighting = models.JSONField(default=dict)
    fog = models.JSONField(default=dict)
    drawings = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)


class SceneObject(models.Model):
    """A typed object such as a wall, light, marker, zone or spatial sound."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(Scene, related_name="elements", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["scene", "kind"], name="map_objects_kind")]


class TacticalTerrain(models.Model):
    """Opt-in, versioned tactical grid; legacy scenes have no terrain row."""
    scene = models.OneToOneField(
        Scene, related_name="tactical_terrain", primary_key=True, on_delete=models.CASCADE
    )
    width = models.PositiveSmallIntegerField(default=16)
    height = models.PositiveSmallIntegerField(default=16)
    version = models.PositiveIntegerField(default=1)
    schema_version = models.PositiveSmallIntegerField(default=1)


class TerrainCell(models.Model):
    NORMAL = "NORMAL"
    DIFICIL = "DIFICIL"
    SEVERO = "SEVERO"
    INTRANSPONIVEL = "INTRANSPONIVEL"
    TERRAIN_TYPES = [
        (NORMAL, "Normal"),
        (DIFICIL, "Difficult"),
        (SEVERO, "Severe"),
        (INTRANSPONIVEL, "Impassable"),
    ]
    terrain = models.ForeignKey(TacticalTerrain, related_name="cells", on_delete=models.CASCADE)
    x = models.PositiveSmallIntegerField()
    y = models.PositiveSmallIntegerField()
    terrain_type = models.CharField(max_length=16, choices=TERRAIN_TYPES, default=NORMAL)
    elevation = models.SmallIntegerField(default=0)
    traversable = models.BooleanField(default=True)
    movement_cost = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["terrain", "x", "y"], name="tactical_cell_unique")]


class TerrainConnection(models.Model):
    STAIR = "STAIR"
    RAMP = "RAMP"
    CONNECTION_TYPES = [(STAIR, "Stair"), (RAMP, "Ramp")]
    terrain = models.ForeignKey(TacticalTerrain, related_name="connections", on_delete=models.CASCADE)
    cell_a = models.ForeignKey(TerrainCell, related_name="connections_a", on_delete=models.CASCADE)
    cell_b = models.ForeignKey(TerrainCell, related_name="connections_b", on_delete=models.CASCADE)
    kind = models.CharField(max_length=8, choices=CONNECTION_TYPES)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["terrain", "cell_a", "cell_b"], name="tactical_connection_unique")]


class MapAsset(models.Model):
    folder = models.ForeignKey(
        "AssetFolder", null=True, blank=True, on_delete=models.SET_NULL
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=240)
    file = models.FileField(upload_to="maps/assets/%Y/%m/")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class AssetFolder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=80)
