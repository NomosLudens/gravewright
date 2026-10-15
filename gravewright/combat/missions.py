"""Persistent scenario instances layered on the existing combat authority."""

from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from gravewright.actors import runtime as actor_runtime
from gravewright.actors.models import Actor
from gravewright.maps.models import SceneObject, TacticalTerrain
from gravewright.maps.services import MapError, scene as get_scene
from gravewright.tokens.models import Token

from .models import (
    Encounter,
    MissionDefinition,
    MissionEvent,
    MissionInstance,
    MissionParticipant,
)


TERMINAL_STATES = {
    MissionInstance.VICTORY,
    MissionInstance.DEFEAT,
    MissionInstance.ABORTED,
}


def _gm(who):
    if who.role != "gm":
        raise MapError("Only the GM can manage a tactical mission.", "forbidden")


def _instance(scene_id, who, *, lock=False):
    get_scene(scene_id, who)
    query = MissionInstance.objects.select_related("definition", "scene", "encounter").filter(
        scene_id=scene_id, campaign_id=who.campaign_id
    )
    if lock:
        query = query.select_for_update()
    return query.first()


def _record(mission, kind, payload, *, actor=None, who=None):
    sequence = (mission.events.order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1
    return MissionEvent.objects.create(
        mission=mission,
        sequence=sequence,
        kind=kind,
        payload=deepcopy(payload),
        actor=actor,
        user=getattr(who, "user", None),
    )


def _participant_data(row, who):
    result = []
    for participant in row.participants.select_related("actor", "token").order_by("created_at", "id"):
        token = participant.token
        if token.hidden and who.role != "gm":
            continue
        result.append({
            "actorId": str(participant.actor_id),
            "tokenId": str(token.pk),
            "name": participant.actor.name,
            "role": participant.role,
            "side": participant.side,
            "position": {"x": token.grid_x, "y": token.grid_y, "elevation": token.elevation},
            "tokenVersion": token.version,
        })
    return result


def state(who, scene_id):
    row = _instance(scene_id, who)
    if not row:
        return {"sceneId": str(scene_id), "mission": None}
    return {
        "sceneId": str(row.scene_id),
        "mission": {
            "id": str(row.pk),
            "definition": {"key": row.definition.key, "version": row.definition.version, "title": row.definition.title},
            "state": row.state,
            "objective": deepcopy(row.objective),
            "result": deepcopy(row.result),
            "version": row.version,
            "participants": _participant_data(row, who),
            "events": [
                {"sequence": event.sequence, "kind": event.kind, "payload": event.payload, "createdAt": event.created_at.isoformat()}
                for event in row.events.order_by("sequence")
            ],
        },
    }


def _validate_ready(mission):
    terrain = TacticalTerrain.objects.filter(scene=mission.scene).first()
    if not terrain or (terrain.width, terrain.height) != (16, 16):
        raise MapError("Knossos mission requires its persisted 16 by 16 tactical grid.", "mission_setup_incomplete")
    cells = list(terrain.cells.all())
    if len(cells) != 256 or {cell.elevation for cell in cells} != {0, 1}:
        raise MapError("Knossos mission requires 256 persisted cells on two elevations.", "mission_setup_incomplete")
    cell_ids = {(cell.x, cell.y): cell.pk for cell in cells}
    stairs = terrain.connections.filter(kind="STAIR").select_related("cell_a", "cell_b")
    if not any(row.cell_a.elevation != row.cell_b.elevation for row in stairs):
        raise MapError("Knossos mission requires a persisted stair joining its two elevations.", "mission_setup_incomplete")
    if not any(not cell.traversable for cell in cells):
        raise MapError("Knossos mission requires at least one persisted impassable obstacle.", "mission_setup_incomplete")
    walls = SceneObject.objects.filter(scene=mission.scene, kind="walls")
    if not any(
        isinstance(row.data, dict)
        and row.data.get("kind") == "wall"
        and row.data.get("x1") is not None
        and row.data.get("x2") is not None
        for row in walls
    ):
        raise MapError("Knossos mission requires at least one persisted wall.", "mission_setup_incomplete")
    extraction = mission.objective.get("extraction", [])
    if not extraction or any((item.get("x"), item.get("y")) not in cell_ids for item in extraction):
        raise MapError("Mission extraction cells must be persisted cells on the scene grid.", "mission_setup_incomplete")
    counts = {role: mission.participants.filter(role=role).count() for role, _ in MissionParticipant.ROLES}
    expected = {"ALLY": 3, "HOSTILE": 3, "EVACUEE": 1}
    if counts != expected:
        raise MapError("Add three allies, three Silmari combatants, and one Nomos evacuee.", "mission_roster_incomplete")
    for participant in mission.participants.select_related("actor", "token"):
        token = participant.token
        actor = participant.actor
        if actor.campaign_id != mission.campaign_id or token.scene_id != mission.scene_id or token.actor_id != actor.pk:
            raise MapError("Mission participants must reference actors and tokens in this campaign scene.", "mission_roster_invalid")
        runtime = actor_runtime.read(actor.data)
        if runtime.get("people") is None:
            raise MapError("Mission units must be persisted KALLÍSTIS actors with a validated people and heritage profile.", "mission_roster_invalid")
        if participant.role == MissionParticipant.EVACUEE and runtime.get("people", {}).get("id") != "nomos":
            raise MapError("The evacuee must be a persisted KALLÍSTIS Nomos actor.", "mission_roster_invalid")
        from .services import identity
        encounter = mission.encounter or Encounter.objects.filter(scene=mission.scene).first()
        if not encounter or not any(identity(entry) == str(token.pk) and entry.get("side") == participant.side for entry in encounter.combatants):
            raise MapError("Every mission unit must be assigned to its side in Gravewright combat.", "mission_roster_invalid")


def _finish(mission, outcome, *, reason, actor=None, who=None):
    if mission.state in TERMINAL_STATES:
        return False
    encounter = mission.encounter or Encounter.objects.filter(scene=mission.scene).first()
    if encounter and encounter.active:
        encounter.active = False
        encounter.round = 0
        encounter.turn = 0
        encounter.version += 1
        encounter.save(update_fields=["active", "round", "turn", "version"])
    mission.state = outcome
    mission.result = {"outcome": outcome, "reason": reason}
    mission.ended_at = timezone.now()
    mission.version += 1
    mission.save(update_fields=["state", "result", "ended_at", "version", "updated_at"])
    _record(mission, "mission.ended", mission.result, actor=actor, who=who)
    return True


def _evaluate(mission, *, actor=None, who=None):
    if mission.state != MissionInstance.ACTIVE:
        return False
    evacuee = mission.participants.select_related("actor", "token").filter(role=MissionParticipant.EVACUEE).first()
    if not evacuee:
        return False
    runtime = actor_runtime.read(evacuee.actor.data)
    if runtime.get("combat", {}).get("permanence_outcome") == "TERMINAL":
        return _finish(mission, MissionInstance.DEFEAT, reason="nomos_terminal", actor=evacuee.actor, who=who)
    zone = mission.objective.get("extraction", [])
    cell = (int(evacuee.token.grid_x), int(evacuee.token.grid_y))
    if {"x": cell[0], "y": cell[1]} in zone:
        return _finish(mission, MissionInstance.VICTORY, reason="nomos_extracted", actor=evacuee.actor, who=who)
    return False


@transaction.atomic
def command(who, action, payload):
    _gm(who)
    scene_id = payload.get("sceneId")
    scene = get_scene(scene_id, who)
    if action == "mission.create":
        definition = MissionDefinition.objects.filter(key=payload.get("definition", "knossos-evacuation"), version=1).first()
        if not definition:
            raise MapError("Mission definition is unavailable.", "not_found")
        terrain = TacticalTerrain.objects.filter(scene=scene).first()
        if not terrain or (terrain.width, terrain.height) != (16, 16):
            raise MapError("Prepare the persisted 16 by 16 tactical grid before creating this mission.", "mission_setup_incomplete")
        row, created = MissionInstance.objects.get_or_create(
            scene=scene,
            defaults={
                "definition": definition,
                "campaign_id": who.campaign_id,
                "created_by_id": who.user_id,
                "objective": deepcopy(definition.content.get("objective", {})),
            },
        )
        if not created:
            raise MapError("This scene already has a mission instance.", "conflict")
        row.encounter = Encounter.objects.filter(scene=scene).first()
        row.save(update_fields=["encounter", "updated_at"])
        _record(row, "mission.created", {"definition": definition.key}, who=who)
        return state(who, scene_id)

    mission = _instance(scene_id, who, lock=True)
    if not mission:
        raise MapError("Mission instance not found.", "not_found")
    if type(payload.get("version")) is not int or payload["version"] != mission.version:
        raise MapError("Mission changed. Refresh before editing.", "conflict")
    if mission.state in TERMINAL_STATES:
        raise MapError("Mission is already in a terminal state.", "mission_closed")

    if action == "mission.participant.add":
        if mission.state not in {MissionInstance.PREPARING, MissionInstance.READY}:
            raise MapError("Mission roster is locked after it starts.", "mission_closed")
        actor = Actor.objects.filter(pk=payload.get("actorId"), campaign_id=who.campaign_id).first()
        token = Token.objects.filter(pk=payload.get("tokenId"), scene=scene, actor=actor).first() if actor else None
        role = payload.get("role")
        if not actor or not token or role not in {MissionParticipant.ALLY, MissionParticipant.HOSTILE, MissionParticipant.EVACUEE}:
            raise MapError("Select a persisted campaign actor and its token in this scene.", "mission_roster_invalid")
        if role == MissionParticipant.EVACUEE and actor_runtime.read(actor.data).get("people", {}).get("id") != "nomos":
            raise MapError("The evacuee must be a persisted KALLÍSTIS Nomos actor.", "mission_roster_invalid")
        if actor_runtime.read(actor.data).get("people") is None:
            raise MapError("Mission units must be persisted KALLÍSTIS actors with a validated people and heritage profile.", "mission_roster_invalid")
        side = "hostile" if role == MissionParticipant.HOSTILE else "friendly"
        participant, _ = MissionParticipant.objects.update_or_create(
            mission=mission, actor=actor,
            defaults={"token": token, "role": role, "side": side},
        )
        encounter, _ = Encounter.objects.get_or_create(scene=scene)
        mission.encounter = encounter
        entry = next((item for item in encounter.combatants if item.get("tokenId") == str(token.pk)), None)
        if entry is None:
            encounter.combatants.append({"tokenId": str(token.pk), "side": side, "initiative": None, "activations": 1, "defeated": False, "hidden": False, "movement_used": 0, "run_used": False})
        else:
            entry["side"] = side
        encounter.active = False
        encounter.config = {key: value for key, value in encounter.config.items() if key not in {"side_initiative", "first_side", "activation_order"}}
        encounter.version += 1
        encounter.save(update_fields=["combatants", "active", "config", "version"])
        mission.encounter = encounter
        mission.state = MissionInstance.PREPARING
        mission.version += 1
        mission.save(update_fields=["encounter", "state", "version", "updated_at"])
        _record(mission, "participant.added", {"actorId": str(actor.pk), "tokenId": str(token.pk), "role": role}, actor=actor, who=who)
    elif action == "mission.ready":
        if mission.state not in {MissionInstance.PREPARING, MissionInstance.READY}:
            raise MapError("Mission cannot enter preparation after it starts.")
        _validate_ready(mission)
        mission.state = MissionInstance.READY
        mission.version += 1
        mission.save(update_fields=["state", "version", "updated_at"])
        _record(mission, "mission.ready", {"participantCount": mission.participants.count()}, who=who)
    elif action == "mission.start":
        if mission.state != MissionInstance.READY:
            raise MapError("Mission must be ready before it starts.", "mission_not_ready")
        _validate_ready(mission)
        encounter = Encounter.objects.select_for_update().filter(scene=scene, active=True).first()
        if not encounter:
            raise MapError("Start the existing Gravewright encounter before starting the mission.", "combat_not_active")
        mission.encounter = encounter
        mission.state = MissionInstance.ACTIVE
        mission.started_at = timezone.now()
        mission.version += 1
        mission.save(update_fields=["encounter", "state", "started_at", "version", "updated_at"])
        _record(mission, "mission.started", {"encounterVersion": encounter.version}, who=who)
    elif action == "mission.abort":
        if mission.state not in {MissionInstance.PREPARING, MissionInstance.READY, MissionInstance.ACTIVE}:
            raise MapError("Mission cannot be aborted from this state.")
        _finish(mission, MissionInstance.ABORTED, reason=str(payload.get("reason", "gm_abort"))[:160], who=who)
    elif action == "mission.evaluate":
        _evaluate(mission, who=who)
    else:
        raise MapError("Unknown mission command.")
    return state(who, scene_id)


@transaction.atomic
def after_token_move(token, who, request_id):
    mission = MissionInstance.objects.select_for_update().filter(scene=token.scene, state=MissionInstance.ACTIVE).first()
    if not mission:
        return False
    ended = _evaluate(mission, actor=token.actor, who=who)
    if ended:
        _record(mission, "objective.resolved", mission.result, actor=token.actor, who=who)
        from gravewright.realtime.dispatch import changed
        changed(who.campaign_id, who.user_id, "combat", "mission.evaluate", request_id, mission.result)
    return ended


@transaction.atomic
def after_combat_command(scene_id, who, action):
    mission = MissionInstance.objects.select_for_update().filter(scene_id=scene_id, state=MissionInstance.ACTIVE).first()
    if not mission:
        return False
    ended = _evaluate(mission, who=who)
    _record(mission, "combat.command", {"action": action, "encounterVersion": mission.encounter.version if mission.encounter_id else None}, who=who)
    return ended
