import uuid

from django.conf import settings
from django.db import models

class Encounter(models.Model):
    scene = models.OneToOneField('gravewright_maps.Scene', primary_key=True, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    round = models.PositiveIntegerField(default=0)
    turn = models.PositiveIntegerField(default=0)
    combatants = models.JSONField(default=list)
    history = models.JSONField(default=list)
    config = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)


class MissionDefinition(models.Model):
    """Reusable scenario contract; narrative content is explicitly non-canonical."""

    key = models.SlugField(max_length=80)
    version = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=160)
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "version"], name="combat_mission_def_key_version")]


class MissionInstance(models.Model):
    PREPARING = "PREPARING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"
    ABORTED = "ABORTED"
    STATES = [(value, value.title()) for value in (PREPARING, READY, ACTIVE, VICTORY, DEFEAT, ABORTED)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(MissionDefinition, on_delete=models.PROTECT, related_name="instances")
    campaign = models.ForeignKey("gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="tactical_missions")
    scene = models.OneToOneField("gravewright_maps.Scene", on_delete=models.CASCADE, related_name="tactical_mission")
    encounter = models.ForeignKey(Encounter, null=True, blank=True, on_delete=models.SET_NULL, related_name="missions")
    state = models.CharField(max_length=12, choices=STATES, default=PREPARING)
    objective = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tactical_missions")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MissionParticipant(models.Model):
    ALLY = "ALLY"
    HOSTILE = "HOSTILE"
    EVACUEE = "EVACUEE"
    ROLES = [(value, value.title()) for value in (ALLY, HOSTILE, EVACUEE)]

    mission = models.ForeignKey(MissionInstance, on_delete=models.CASCADE, related_name="participants")
    actor = models.ForeignKey("gravewright_actors.Actor", on_delete=models.PROTECT, related_name="tactical_mission_participations")
    token = models.OneToOneField("gravewright_tokens.Token", on_delete=models.PROTECT, related_name="tactical_mission_participation")
    role = models.CharField(max_length=12, choices=ROLES)
    side = models.CharField(max_length=12, choices=[("friendly", "Friendly"), ("hostile", "Hostile")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mission", "actor"], name="combat_mission_actor_unique")]


class MissionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(MissionInstance, on_delete=models.CASCADE, related_name="events")
    sequence = models.PositiveIntegerField()
    kind = models.CharField(max_length=40)
    request_id = models.UUIDField(null=True, blank=True)
    actor = models.ForeignKey("gravewright_actors.Actor", null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["mission", "sequence"], name="combat_mission_event_sequence"),
            models.UniqueConstraint(fields=["mission", "request_id"], name="combat_mission_event_request"),
        ]
