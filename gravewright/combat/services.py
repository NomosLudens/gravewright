"""Server-authoritative minimum KALLISTIS combat runtime."""

from copy import deepcopy
from uuid import uuid4

from django.db import transaction

from gravewright.actors import runtime
from gravewright.actors import services as actors
from gravewright.actors.models import Actor
from gravewright.dice.kallistis import evaluate as evaluate_kallistis
from gravewright.maps.services import MapError, scene
from gravewright.table.domain import boolean, number, version
from gravewright.tokens import services as tokens
from gravewright.tokens.models import Token
from gravewright.rules import kallistis_runtime as rules

from .effects import advance as advance_effects
from .models import Encounter


DEFENSES = {"GUARDA", "FORTITUDE", "INTEGRIDADE"}
MOVEMENT_MODES = {"GRID", "ZONES"}
COMBAT_SIDES = {"friendly", "hostile"}
MAX_EVENTS = 256


def identity(entry):
    return entry.get("tokenId") or entry.get("actorId")


def actor_for(entry):
    if entry.get("tokenId"):
        token = Token.objects.select_related("actor").filter(pk=entry["tokenId"]).first()
        return token.actor if token else None
    return Actor.objects.filter(pk=entry.get("actorId")).first()


def _actor_entry(row, value):
    return next((entry for entry in row.combatants if identity(entry) == str(value)), None)


def _actor_runtime(actor):
    return runtime.read(actor.data)


def defenses(actor):
    state = _actor_runtime(actor)
    attrs = state["attributes"]
    protection = state.get("protection", 0)
    return {
        "GUARDA": 10 + attrs.get("agilidade", 0) + protection,
        "FORTITUDE": 10 + attrs.get("corpo", 0) + attrs.get("vontade", 0),
        "INTEGRIDADE": 10 + attrs.get("vontade", 0) + attrs.get("sintonia", 0),
        "protection": protection,
    }


def _config(row):
    value = row.config if isinstance(row.config, dict) else {}
    value.setdefault("movement_mode", "GRID")
    value.setdefault("movement_allowance", {"GRID": 6, "ZONES": 2})
    value["initiative_status"] = "SIDE_ALTERNATION"
    value.setdefault("processed_events", {})
    value.setdefault("resolutions", [])
    value.setdefault("movement_overrides", [])
    return value


def _remember(config, bucket, key, value=True):
    values = config.setdefault(bucket, {})
    if key in values:
        return False
    values[key] = value
    if len(values) > MAX_EVENTS:
        for old in list(values)[:-MAX_EVENTS]:
            values.pop(old, None)
    return True


def _safe_write(actor, state):
    actor.data = {**(actor.data if isinstance(actor.data, dict) else {}), "runtime": state}
    actor.version += 1
    actor.save(update_fields=["data", "version", "updated_at"])
    for token in actor.tokens.filter(linked=True):
        token.version += 1
        token.save(update_fields=["version"])


def _condition(state, kind):
    return next((item for item in state["conditions"] if item.get("type") == kind), None)


def _ensure_down(state):
    if not _condition(state, "CAIDO"):
        state["conditions"].append({
            "id": str(uuid4()), "type": "CAIDO", "source": "vitality_zero",
            "applied_by": "system", "applied_at": "", "duration": "PERMANENT",
            "removal_rule": "permanence", "intensity": 1, "metadata": {},
        })
    state.setdefault("combat", {}).setdefault("permanence_successes", 0)
    state.setdefault("combat", {}).setdefault("permanence_failures", 0)


def _remove_condition(state, kind):
    state["conditions"] = [item for item in state["conditions"] if item.get("type") != kind]


def _turn_key(row, entry, phase):
    return f"{phase}:{row.round}:{identity(entry)}"


def _activation_order(row, first_side=None):
    config = _config(row)
    first_side = first_side or config.get("first_side")
    if first_side not in COMBAT_SIDES:
        raise MapError("Roll side initiative and choose which side acts first.")
    queues = {side: [] for side in COMBAT_SIDES}
    for entry in row.combatants:
        side = entry.get("side")
        if side in COMBAT_SIDES and not entry.get("defeated"):
            try:
                count = int(number(entry.get("activations", 1), 1, 12))
            except (TypeError, ValueError):
                raise MapError("Activations per combatant must be between 1 and 12.") from None
            queues[side].extend([identity(entry)] * count)
    order = []
    other_side = "hostile" if first_side == "friendly" else "friendly"
    while queues["friendly"] or queues["hostile"]:
        for side in (first_side, other_side):
            if queues[side]:
                order.append(queues[side].pop(0))
    config["activation_order"] = order
    return order


def _current_entry(row):
    order = _config(row).get("activation_order") or []
    if 0 <= row.turn < len(order):
        return _actor_entry(row, order[row.turn])
    return None


def _start_turn(row, entry):
    actor = actor_for(entry)
    if actor is None:
        return {"phase": "start", "skipped": True}
    state = _actor_runtime(actor)
    state["rules"] = rules.begin_round(
        state["rules"], movement_mode=_config(row)["movement_mode"]
    )
    _safe_write(actor, state)
    result = {"phase": "start", "actorId": str(actor.pk), "condition": None}
    if not _condition(state, "CAIDO"):
        return result
    key = _turn_key(row, entry, "start")
    config = _config(row)
    if not _remember(config, "processed_events", key):
        return {**result, "replayed": True}
    attrs = state["attributes"]
    skills = state.get("skills", {})
    skill = skills.get("atletismo", skills.get("Atletismo", 0))
    roll = evaluate_kallistis(attrs.get("corpo", 0) + skill, 12)
    combat = state.setdefault("combat", {})
    combat["permanence_last"] = {
        "dc": 12, "attribute": "Corpo", "attribute_value": attrs.get("corpo", 0),
        "skill": "Atletismo", "skill_value": skill, **roll,
    }
    if roll["success"]:
        combat["permanence_successes"] = combat.get("permanence_successes", 0) + 1
    else:
        combat["permanence_failures"] = combat.get("permanence_failures", 0) + 1
    result["condition"] = deepcopy(combat["permanence_last"])
    result["permanence_successes"] = combat["permanence_successes"]
    result["permanence_failures"] = combat["permanence_failures"]
    if combat["permanence_successes"] >= 3:
        state["resources"]["vitality"]["current"] = 1
        _remove_condition(state, "CAIDO")
        combat["permanence_outcome"] = "STABILIZED"
        result["outcome"] = "STABILIZED"
    elif combat["permanence_failures"] >= 3:
        combat["permanence_outcome"] = "TERMINAL"
        result["outcome"] = "TERMINAL"
    _safe_write(actor, state)
    return result


def _end_turn(row, entry):
    actor = actor_for(entry)
    if actor is None:
        return {"phase": "end", "skipped": True}
    state = _actor_runtime(actor)
    result = {"phase": "end", "actorId": str(actor.pk), "sangrando": False}
    if not _condition(state, "SANGRANDO"):
        return result
    key = _turn_key(row, entry, "end")
    config = _config(row)
    if not _remember(config, "processed_events", key):
        return {**result, "replayed": True}
    item = state["resources"]["vitality"]
    before = item["current"]
    item["current"] = max(0, before - 2)
    result.update({"sangrando": True, "tick": -2, "vitality_before": before, "vitality_after": item["current"]})
    if item["current"] == 0:
        _ensure_down(state)
        result["caido"] = True
    _safe_write(actor, state)
    return result


def _reset_movement(entry):
    entry["movement_used"] = 0
    entry["run_used"] = False


def _serialized_combatant(row, entry, who, target):
    token = Token.objects.filter(pk=entry.get("tokenId"), scene=target).select_related("actor").first() if entry.get("tokenId") else None
    actor = token.actor if token else Actor.objects.filter(pk=entry.get("actorId"), campaign_id=who.campaign_id).first()
    if not actor:
        return None
    if who.role != "gm" and (entry.get("hidden") or (token.hidden if token else not actors.access(actor, who))):
        return None
    data = tokens.data(token) if token else {}
    index = row.combatants.index(entry)
    activation_order = _config(row).get("activation_order") or []
    current_id = activation_order[row.turn] if row.active and row.turn < len(activation_order) else None
    next_id = activation_order[row.turn + 1] if row.active and row.turn + 1 < len(activation_order) else (activation_order[0] if row.active and activation_order else None)
    controlled = tokens.control(token, who) if token else actors.access(actor, who, True)
    actor_state = _actor_runtime(actor)
    public_entry = dict(entry)
    if who.role != "gm" and not controlled:
        public_entry.pop("run_used", None)
    side_score = (_config(row).get("side_initiative") or {}).get("totals", {}).get(entry.get("side"))
    movement = None
    if who.role == "gm" or controlled:
        config = _config(row)
        mode = config["movement_mode"]
        per_move = config["movement_allowance"].get(mode, 6 if mode == "GRID" else 2)
        conditions = {item.get("type") for item in actor_state["conditions"]}
        if "LENTO" in conditions:
            per_move = max(0, per_move - (2 if mode == "GRID" else 1))
        immobile = "IMOBILIZADO" in conditions
        if immobile:
            per_move = 0
        run_used = entry.get("run_used", False) is True
        action_economy = actor_state["rules"].get("action_economy", {})
        movement = {
            "mode": mode,
            "pointsPerMove": per_move,
            "used": entry.get("movement_used", 0),
            "runUsed": run_used,
            "canRun": bool(
                row.active
                and identity(entry) == current_id
                and not run_used
                and not immobile
                and action_economy.get("action", 0) > 0
            ),
        }
    bars = data.get("bars", {}).get("bar_1", {})
    maximum, value = bars.get("max", 0), bars.get("value", 0)
    return {
        "position": index + 1, "conditions_count": len(_actor_runtime(actor)["conditions"]),
        "bar": {"value": value, "max": maximum, "percent": value / maximum * 100 if maximum else 0} if controlled else None,
        **public_entry, "id": identity(entry), "token_id": entry.get("tokenId"), "actor_id": str(actor.pk),
        "side_score": side_score,
        "name": data.get("token", {}).get("name") or actor.name, "canControl": controlled,
        "current": row.active and identity(entry) == current_id, "is_current": row.active and identity(entry) == current_id,
        "is_next": row.active and identity(entry) == next_id,
        "has_acted": row.active and identity(entry) in activation_order[:row.turn],
        "can_move_up": index > 0, "can_move_down": index < len(row.combatants) - 1,
        "defenses": defenses(actor),
        "runtime": actor_state if who.role == "gm" or controlled else None,
        "movement": movement,
    }


def state(who, scene_id=None):
    if not scene_id:
        return dict(active=False, round=0, turn=0, combatants=[], version=0)
    target = scene(scene_id, who)
    row = Encounter.objects.filter(scene=target).first()
    if not row:
        return dict(sceneId=str(target.pk), active=False, round=0, turn=0, combatants=[], version=0)
    rows = [item for entry in row.combatants if (item := _serialized_combatant(row, entry, who, target))]
    config = _config(row)
    visible_by_id = {item["id"]: item for item in rows}
    order = config.get("activation_order") or []
    turn_order = [
        {"id": actor_id, "name": visible_by_id[actor_id]["name"], "side": visible_by_id[actor_id].get("side"), "current": slot == row.turn}
        for slot, actor_id in enumerate(order) if actor_id in visible_by_id
    ]
    return {
        "sceneId": str(target.pk), "active": row.active, "round": row.round, "turn": row.turn,
        "combatants": rows,
        "current_name": next((item["name"] for item in rows if item["is_current"]), ""),
        "next_name": next((item["name"] for item in rows if item["is_next"]), ""),
        "version": row.version,
        "turn_order": turn_order,
        "config": config,
        "initiative_status": "SIDE_ALTERNATION",
    }


def _entry_for_target(row, value):
    entry = _actor_entry(row, value)
    if not entry:
        raise MapError("Combatant not found.")
    return entry


def _controlled(entry, who):
    token = tokens.get(entry["tokenId"], who) if entry.get("tokenId") else None
    return tokens.control(token, who) if token else actors.access(actors.get(entry["actorId"], who), who, True)


def _require_gm(who):
    if who.role != "gm":
        raise MapError("Only the GM can manage combat.", "forbidden")


def _spend_actor_action(actor):
    actor = Actor.objects.select_for_update().get(pk=actor.pk)
    actor_state = _actor_runtime(actor)
    try:
        spent = rules.spend_action(actor_state["rules"], "action")
    except rules.RuleError as exc:
        raise MapError(str(exc), "action_spent") from None
    actor_state["rules"] = spent["state"]
    _safe_write(actor, actor_state)
    return actor


def _resolve_action(row, who, payload):
    attacker = actors.get(payload.get("actorId"), who)
    if who.role != "gm" and not actors.access(attacker, who, True):
        raise MapError("Character not controlled.", "forbidden")
    if row.active and who.role != "gm":
        entry = next((item for item in row.combatants if (candidate := actor_for(item)) and candidate.pk == attacker.pk), None)
        if entry is None or identity(_current_entry(row) or {}) != identity(entry):
            raise MapError("It is not this character's turn.", "not_your_turn")
        if _actor_runtime(attacker)["rules"].get("action_economy", {}).get("action", 0) < 1:
            raise MapError("Action already spent.", "action_spent")
    defense_name = str(payload.get("targetDefense", payload.get("defense", "GUARDA"))).upper()
    environmental = defense_name in {"ENVIRONMENT", "DIFFICULTY"}
    if defense_name not in DEFENSES and not environmental:
        raise MapError("Invalid target defense.")
    target_entry = None if environmental else _entry_for_target(row, payload.get("targetId"))
    target_actor = attacker if environmental else actor_for(target_entry)
    if not target_actor:
        raise MapError("Target not found.")
    action = payload.get("action")
    if not isinstance(action, dict):
        raise MapError("Structured action is required.")
    prepared = runtime.authoritative_action(attacker.pk, who, action)
    attacker_state = _actor_runtime(attacker)
    target_state = _actor_runtime(target_actor)
    modifier = prepared["modifier_total"]
    condition_modifier = 0
    sources = []
    if not environmental and _condition(target_state, "EXPOSTO"):
        condition_modifier += 2
        sources.append("Exposto")
    if payload.get("grave_wound_applies") is True and attacker_state.get("combat", {}).get("grave_wound"):
        current_pressure = prepared["pressure"]["level"]
        if current_pressure < 2:
            prepared["pressure"]["level"] = min(2, current_pressure + 1)
            prepared["pressure"]["penalty"] = -(prepared["pressure"]["level"] * 2)
            modifier -= 2
            sources.append("Ferida Grave")
    target_value = number(payload.get("difficulty"), 1, 1000) if environmental else defenses(target_actor)[defense_name]
    result_defense = "DIFFICULTY" if environmental else defense_name
    roll = evaluate_kallistis(modifier + condition_modifier, target_value)
    result = {
        **roll, "attribute": prepared["attribute"], "skill": prepared["skill"],
        "light": roll["light_die"], "dark": roll["dark_die"],
        "modifier": modifier + condition_modifier, "condition_modifier": condition_modifier,
        "condition_source": sources[0] if sources else None, "target_defense": result_defense,
        "target_defense_value": target_value, "environmental": environmental,
        "grave_wound_applies": payload.get("grave_wound_applies") is True,
    }
    if row.active and who.role != "gm":
        attacker = _spend_actor_action(attacker)
    config = _config(row)
    config["resolutions"] = (config["resolutions"] + [{"id": str(uuid4()), "kind": "action", **result}])[-MAX_EVENTS:]
    return {"kind": "action", "attackerId": str(attacker.pk), "targetId": None if environmental else str(target_actor.pk), "result": result}


def _damage(row, who, payload):
    _require_gm(who)
    target_entry = _entry_for_target(row, payload.get("targetId", payload.get("actorId")))
    actor = actor_for(target_entry)
    if not actor:
        raise MapError("Target not found.")
    event_id = str(payload.get("damageEventId") or payload.get("eventId") or uuid4())
    config = _config(row)
    if event_id in config.setdefault("processed_events", {}):
        previous = next((item for item in config["resolutions"] if item.get("event_id") == event_id), None)
        return {"kind": "damage", "replayed": True, "result": previous}
    raw = number(payload.get("rawDamage"), 0, 100000)
    state = _actor_runtime(actor)
    was_down = bool(_condition(state, "CAIDO"))
    protection = payload.get("protectionValue", state.get("protection", 0))
    protection = number(protection, 0, 100000)
    post = max(0, raw - protection)
    before = state["resources"]["vitality"]["current"]
    damage_result = rules.apply_damage(
        state, raw, protection=protection,
        fortitude=defenses(actor)["FORTITUDE"], damage_event=event_id,
    )
    post = damage_result["post_protection"]
    excess = damage_result["excess"]
    state = damage_result["state"]
    if state["resources"]["vitality"]["current"] == 0:
        _ensure_down(state)
    combat = state.setdefault("combat", {})
    down = bool(_condition(state, "CAIDO"))
    if was_down and post > 0:
        combat["permanence_failures"] = min(3, combat.get("permanence_failures", 0) + 1)
        if combat["permanence_failures"] >= 3:
            combat["permanence_outcome"] = "TERMINAL"
    candidate = excess >= defenses(actor)["FORTITUDE"]
    result = {
        "event_id": event_id, "raw_damage": raw, "protection_value": protection,
        "post_protection_damage": post, "vitality_before": before,
        "vitality_after": state["resources"]["vitality"]["current"], "excess_damage": excess,
        "fortitude": defenses(actor)["FORTITUDE"], "grave_wound_candidate": candidate,
        "grave_wound_requires_gm_confirmation": candidate, "caido": down,
        "permanence_failures": combat.get("permanence_failures", 0),
    }
    _remember(config, "processed_events", event_id)
    config["resolutions"] = (config["resolutions"] + [{"kind": "damage", **result}])[-MAX_EVENTS:]
    _safe_write(actor, state)
    return {"kind": "damage", "result": result}


@transaction.atomic
def command(who, action, p):
    target = scene(p.get("sceneId"), who)
    row, created = Encounter.objects.select_for_update().get_or_create(scene=target)
    if not created:
        version(row, p)
    config = _config(row)
    if who.role != "gm" and action not in {"next", "resolve", "attack", "run"}:
        raise MapError("Only the GM can manage combat.", "forbidden")
    if action in {"resolve", "attack"}:
        result = _resolve_action(row, who, p)
        row.config = config
        row.version += 1
        row.save(update_fields=["config", "version"])
        return {**state(who, str(target.pk)), "resolution": result}
    if action == "damage":
        result = _damage(row, who, p)
        row.config = config
        row.version += 1
        row.save(update_fields=["config", "version"])
        return {**state(who, str(target.pk)), "resolution": result}
    if action == "confirm-grave-wound":
        _require_gm(who)
        target_entry = _entry_for_target(row, p.get("targetId", p.get("actorId")))
        actor = actor_for(target_entry)
        if not actor:
            raise MapError("Target not found.")
        actor_state = _actor_runtime(actor)
        actor_state.setdefault("combat", {})["grave_wound"] = True
        _safe_write(actor, actor_state)
        result = {"kind": "grave_wound", "actorId": str(actor.pk), "confirmed": True, "pressure": 1}
        config["resolutions"] = (config["resolutions"] + [result])[-MAX_EVENTS:]
        row.config = config
        row.version += 1
        row.save(update_fields=["config", "version"])
        return {**state(who, str(target.pk)), "resolution": result}
    if action == "run":
        if not row.active or not row.combatants:
            raise MapError("Correr is available only during active combat.")
        entry = _entry_for_target(row, p.get("tokenId", p.get("actorId")))
        if not _current_entry(row) or identity(_current_entry(row)) != identity(entry):
            raise MapError("Correr is available only on this character's turn.", "not_your_turn")
        if who.role != "gm" and not _controlled(entry, who):
            raise MapError("Character not controlled.", "forbidden")
        if entry.get("run_used"):
            raise MapError("Correr has already been used this turn.")
        actor = actor_for(entry)
        if actor is None:
            raise MapError("Character not found.")
        actor = Actor.objects.select_for_update().get(pk=actor.pk)
        actor_state = _actor_runtime(actor)
        if _condition(actor_state, "IMOBILIZADO"):
            raise MapError("Movement blocked by IMOBILIZADO.", "immobilized")
        actor = _spend_actor_action(actor)
        entry["run_used"] = True
    elif action == "movement-mode":
        _require_gm(who)
        mode = str(p.get("mode", "")).upper()
        if mode not in MOVEMENT_MODES:
            raise MapError("Invalid movement mode.")
        config["movement_mode"] = mode
    elif action == "add":
        _require_gm(who)
        if p.get("tokenId"):
            token = tokens.get(p["tokenId"], who)
            if token.scene_id != target.pk:
                raise MapError("Token is not in this scene.")
            entry = {"tokenId": str(token.pk)}
            if token.disposition in COMBAT_SIDES:
                entry["side"] = token.disposition
        else:
            entry = {"actorId": str(actors.get(p.get("actorId"), who).pk)}
        if not any(identity(c) == identity(entry) for c in row.combatants):
            row.combatants.append({**entry, "initiative": None, "activations": 1, "defeated": False, "hidden": False, "movement_used": 0, "run_used": False})
            config.pop("side_initiative", None)
            config.pop("first_side", None)
            config.pop("activation_order", None)
    elif action == "remove":
        _require_gm(who)
        target_id = str(p.get("tokenId", p.get("actorId")))
        removed_index = next((i for i, entry in enumerate(row.combatants) if identity(entry) == target_id), None)
        if removed_index is not None:
            current_id = identity(_current_entry(row) or {})
            row.combatants.pop(removed_index)
            if not row.combatants:
                row.active, row.round, row.turn = False, 0, 0
                config.pop("side_initiative", None)
                config.pop("first_side", None)
                config.pop("activation_order", None)
            else:
                if row.active and config.get("first_side") in COMBAT_SIDES:
                    if not any(entry.get("side") == side and not entry.get("defeated") for entry in row.combatants for side in ("friendly", "hostile")):
                        row.active, row.round, row.turn = False, 0, 0
                    else:
                        order = _activation_order(row)
                        row.turn = next((slot for slot, actor_id in enumerate(order) if actor_id == current_id), min(row.turn, len(order) - 1))
                else:
                    config.pop("side_initiative", None)
                    config.pop("first_side", None)
                    config.pop("activation_order", None)
    elif action == "side":
        _require_gm(who)
        if row.active:
            raise MapError("Combatant sides can be changed between rounds only after combat stops.")
        entry = _entry_for_target(row, p.get("tokenId", p.get("actorId")))
        side = p.get("side")
        if side in COMBAT_SIDES:
            entry["side"] = side
        elif side == "":
            entry.pop("side", None)
        else:
            raise MapError("Choose Friendly or Hostile, or leave it unassigned.")
        config.pop("side_initiative", None)
        config.pop("first_side", None)
        config.pop("activation_order", None)
    elif action == "activations":
        _require_gm(who)
        if row.active:
            raise MapError("Activation counts can be changed only between encounters.")
        entry = _entry_for_target(row, p.get("tokenId", p.get("actorId")))
        try:
            value = int(p.get("value"))
        except (TypeError, ValueError):
            raise MapError("Activations per combatant must be a whole number from 1 to 12.") from None
        if str(value) != str(p.get("value")) or not 1 <= value <= 12:
            raise MapError("Activations per combatant must be a whole number from 1 to 12.")
        entry["activations"] = value
        config.pop("side_initiative", None)
        config.pop("first_side", None)
        config.pop("activation_order", None)
    elif action == "roll-initiative":
        _require_gm(who)
        if row.active:
            raise MapError("Roll side initiative before starting combat.")
        representatives = {}
        for side, field in (("friendly", "friendlyRepresentative"), ("hostile", "hostileRepresentative")):
            rep_id = str(p.get(field, ""))
            entry = _actor_entry(row, rep_id)
            if not entry or entry.get("side") != side or entry.get("defeated"):
                raise MapError(f"Choose a living {side} representative from the assigned side.")
            actor = actor_for(entry)
            if not actor:
                raise MapError("Initiative representative has no character sheet.")
            actor_state = _actor_runtime(actor)
            modifier = actor_state["attributes"].get("agilidade", 0) + actor_state.get("skills", {}).get("percepcao", 0)
            representatives[side] = {"entry": entry, "actor": actor, "modifier": modifier}
        if not any(item.get("side") == "friendly" for item in row.combatants) or not any(item.get("side") == "hostile" for item in row.combatants):
            raise MapError("Assign at least one combatant to each side before rolling.")
        rolls = {side: [] for side in COMBAT_SIDES}
        totals = {}
        while True:
            for side in ("friendly", "hostile"):
                rep = representatives[side]
                roll = evaluate_kallistis(rep["modifier"], 1)
                rolls[side].append({
                    "representativeId": identity(rep["entry"]),
                    "representative": rep["actor"].name,
                    "modifier": rep["modifier"],
                    **roll,
                })
                totals[side] = roll["total"]
            if totals["friendly"] != totals["hostile"]:
                break
        winner = "friendly" if totals["friendly"] > totals["hostile"] else "hostile"
        config["side_initiative"] = {"rolls": rolls, "totals": totals, "winner": winner, "firstSide": None}
        config.pop("first_side", None)
        config.pop("activation_order", None)
    elif action == "choose-first-side":
        _require_gm(who)
        if row.active:
            raise MapError("Choose the first side before starting combat.")
        initiative = config.get("side_initiative") or {}
        first_side = p.get("side")
        if first_side not in COMBAT_SIDES or initiative.get("winner") not in COMBAT_SIDES:
            raise MapError("Roll side initiative first.")
        if first_side not in {initiative["winner"], "hostile" if initiative["winner"] == "friendly" else "friendly"}:
            raise MapError("The winning side chooses which side acts first.")
        config["first_side"] = first_side
        initiative["firstSide"] = first_side
        _activation_order(row, first_side)
    elif action == "initiative":
        _require_gm(who)
        raise MapError("Individual initiative is not used; roll once for each side.")
    elif action == "toggle":
        _require_gm(who)
        entry = _entry_for_target(row, p.get("tokenId", p.get("actorId")))
        for field in ("hidden", "defeated"):
            if field in p:
                entry[field] = boolean(p[field])
        if not row.active and "defeated" in p:
            config.pop("side_initiative", None)
            config.pop("first_side", None)
            config.pop("activation_order", None)
    elif action in ("order-up", "order-down", "set-turn"):
        _require_gm(who)
        if action in {"order-up", "order-down"} and row.active:
            raise MapError("Combat order can be edited only before initiative is rolled.")
        index = next((i for i, c in enumerate(row.combatants) if identity(c) == str(p.get("tokenId", p.get("actorId")))), None)
        if index is None:
            raise MapError("Combatant not found.")
        if action == "set-turn":
            identity_id = identity(row.combatants[index])
            order = config.get("activation_order") or []
            row.turn = next((slot for slot, actor_id in enumerate(order) if actor_id == identity_id), 0)
        else:
            target_index = max(0, min(len(row.combatants) - 1, index + (-1 if action == "order-up" else 1)))
            if target_index != index:
                if index == row.turn:
                    row.turn = target_index
                elif target_index == row.turn:
                    row.turn = index
                row.combatants[index], row.combatants[target_index] = row.combatants[target_index], row.combatants[index]
                config.pop("side_initiative", None)
                config.pop("first_side", None)
                config.pop("activation_order", None)
    elif action in ("next-round", "previous-round"):
        _require_gm(who)
        if not row.active:
            raise MapError("Combat has not started.")
        if row.combatants:
            ending_entry = _current_entry(row)
            _end_turn(row, ending_entry)
        row.round = max(1, row.round + (-1 if action == "previous-round" else 1))
        row.turn = 0
        for entry in row.combatants:
            _reset_movement(entry)
        order = _activation_order(row)
        if not order:
            row.active, row.round, row.turn = False, 0, 0
        while order and _current_entry(row).get("defeated"):
            row.turn += 1
            if row.turn >= len(order):
                row.turn = 0
        if row.active and row.combatants:
            advance_effects(
                who.campaign_id,
                ending_entry.get("tokenId") if ending_entry else None,
                actor_id=ending_entry.get("actorId") if ending_entry else None,
                new_round=action == "next-round",
            )
        if row.active and row.combatants:
            _start_turn(row, _current_entry(row))
    elif action == "start":
        _require_gm(who)
        if not row.combatants:
            raise MapError("Add combatants first.")
        if config.get("first_side") not in COMBAT_SIDES:
            raise MapError("Roll side initiative and let the winner choose which side acts first.")
        row.active, row.round, row.turn = True, 1, 0
        for entry in row.combatants:
            _reset_movement(entry)
        order = _activation_order(row)
        while order and _current_entry(row).get("defeated"):
            row.turn += 1
            if row.turn >= len(order):
                row.turn = 0
        _start_turn(row, _current_entry(row))
    elif action == "stop":
        _require_gm(who)
        row.active, row.round, row.turn = False, 0, 0
        config.pop("side_initiative", None)
        config.pop("first_side", None)
        config.pop("activation_order", None)
    elif action in ("next", "previous"):
        if not row.active or not row.combatants:
            raise MapError("Combat has not started.")
        order = config.get("activation_order") or []
        if not order:
            raise MapError("Combat has no side activation order.")
        current = _current_entry(row)
        if current is None:
            raise MapError("This combat has no side activation sequence. Stop it, assign sides, and roll initiative.")
        if who.role != "gm" and (action != "next" or not _controlled(current, who)):
            raise MapError("It is not your turn.", "forbidden")
        if action == "previous":
            for _ in order:
                row.turn -= 1
                if row.turn < 0:
                    row.round = max(1, row.round - 1)
                    order = _activation_order(row)
                    if not order:
                        row.active, row.round, row.turn = False, 0, 0
                        break
                    row.turn = len(order) - 1
                previous_entry = _current_entry(row)
                if previous_entry and not previous_entry.get("defeated"):
                    break
        else:
            _end_turn(row, current)
            previous_round = row.round
            if not any(not entry.get("defeated") for entry in row.combatants):
                row.active, row.round, row.turn = False, 0, 0
            else:
                for _ in range(len(order) + len(row.combatants) + 1):
                    row.turn += 1
                    if row.turn >= len(order):
                        row.round += 1
                        row.turn = 0
                        order = _activation_order(row)
                        if not order:
                            row.active, row.round, row.turn = False, 0, 0
                            break
                    next_candidate = _current_entry(row)
                    if next_candidate and not next_candidate.get("defeated"):
                        break
            advance_effects(
                who.campaign_id,
                current.get("tokenId"),
                actor_id=current.get("actorId"),
                new_round=row.round != previous_round,
            )
        next_entry = _current_entry(row) if row.active else None
        if next_entry:
            _reset_movement(next_entry)
            _start_turn(row, next_entry)
    else:
        raise MapError("Unknown combat command.")
    row.config = config
    row.version += 1
    row.save()
    return state(who, str(target.pk))


def movement_context(token, who, points, *, gm_override=False):
    """Validate an active-combat move and return its authoritative allowance."""
    row = Encounter.objects.select_for_update().filter(scene=token.scene, active=True).first()
    if not row:
        return {"distance": 0, "mode": "GRID", "allowance": None, "override": False}
    entry = _entry_for_target(row, str(token.pk))
    config = _config(row)
    mode = config["movement_mode"]
    allowance = config["movement_allowance"].get(mode, 6 if mode == "GRID" else 2)
    actor_state = _actor_runtime(token.actor)
    conditions = {item.get("type") for item in actor_state["conditions"]}
    per_move = max(0, allowance - (2 if mode == "GRID" else 1)) if "LENTO" in conditions else allowance
    allowance = per_move * (2 if entry.get("run_used") else 1)
    distance = sum(
        abs(b[0] - a[0]) + abs(b[1] - a[1]) if mode == "GRID"
        else max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        for a, b in zip(points, points[1:])
    )
    if "IMOBILIZADO" in conditions:
        raise MapError("Movement blocked by IMOBILIZADO.", "immobilized")
    override = who.role == "gm" and gm_override is True
    if not override:
        if identity(_current_entry(row) or {}) != identity(entry):
            raise MapError("It is not this token's turn; GM override is required.", "not_your_turn")
        if entry.get("movement_used", 0) + distance > allowance:
            raise MapError("Movement exceeds the current allowance.", "movement_exceeded")
        entry["movement_used"] = entry.get("movement_used", 0) + distance
    else:
        config["movement_overrides"] = (config.get("movement_overrides", []) + [{"tokenId": str(token.pk), "round": row.round, "turn": row.turn}])[-MAX_EVENTS:]
    row.config = config
    row.version += 1
    row.save(update_fields=["combatants", "config", "version"])
    return {"distance": distance, "mode": mode, "allowance": allowance, "used": entry.get("movement_used", 0), "override": override}


def public_state(campaign_id, user_id, scene_id=None):
    from gravewright.table.domain import state as read
    return read(campaign_id, user_id, "combat", scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    from gravewright.table.domain import command as execute
    return execute(campaign_id, user_id, "combat", action, data, request_id)
