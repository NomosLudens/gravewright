"""Server-authoritative KALLISTIS runtime resources and conditions.

This state deliberately lives beside, rather than inside, the PDF character
sheet.  It is campaign play state: small, bounded, auditable and transported
through the existing actor command/state channel.
"""

from copy import deepcopy
from math import ceil
from uuid import UUID, uuid4
from django.utils import timezone

from .models import Actor
from .services import access
from gravewright.maps.services import MapError


RESOURCE_NAMES = ("vitality", "lucidity", "flow", "breath", "determination")
CONDITION_TYPES = (
    "ABALADO", "EXPOSTO", "IMOBILIZADO", "LENTO", "SANGRANDO",
    "SILENCIADO", "DISSONANTE", "FRATURADO", "CORROMPIDO", "CAIDO",
)
DEFAULT_DURATION = "UNTIL_END_OF_SOURCE_NEXT_TURN"


def _int(value, name, minimum=None, maximum=None):
    if type(value) is not int or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise MapError(f"Invalid {name}.")
    return value


def maxima(attributes):
    attributes = attributes if isinstance(attributes, dict) else {}
    corpo = _attribute(attributes.get("corpo", 0), "corpo")
    vontade = _attribute(attributes.get("vontade", 0), "vontade")
    sintonia = _attribute(attributes.get("sintonia", 0), "sintonia")
    marco = _attribute(attributes.get("marco", 0), "marco")
    return {
        "vitality": 10 + corpo * 3,
        "lucidity": 8 + vontade * 3,
        "flow": 3 + sintonia + ceil(marco / 2),
        "breath": 3,
        "determination": 3,
    }


def _attribute(value, name):
    return _int(value, name, -1000, 1000)


def empty():
    attributes = {"corpo": 0, "vontade": 0, "sintonia": 0, "marco": 0}
    maximum = maxima(attributes)
    return {
        "attributes": attributes,
        "resources": {
            name: {"current": maximum[name] if name != "determination" else 1, "max": maximum[name]}
            for name in RESOURCE_NAMES
        },
        "conditions": [],
        "lucidity_zero_pending_resolution": False,
    }


def read(data):
    """Return a safe projection, including legacy actors with no runtime."""
    raw = data.get("runtime") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        raw = empty()
    result = empty()
    attributes = raw.get("attributes", {})
    if isinstance(attributes, dict):
        for name in result["attributes"]:
            if type(attributes.get(name)) is int:
                result["attributes"][name] = attributes[name]
    maximum = maxima(result["attributes"])
    resources = raw.get("resources", {})
    if isinstance(resources, dict):
        for name in RESOURCE_NAMES:
            saved = resources.get(name, {})
            current = saved.get("current") if isinstance(saved, dict) else None
            if type(current) is int:
                result["resources"][name]["current"] = max(0, min(maximum[name], current))
    for name in RESOURCE_NAMES:
        result["resources"][name]["max"] = maximum[name]
    conditions = raw.get("conditions", [])
    if isinstance(conditions, list):
        result["conditions"] = [deepcopy(c) for c in conditions if isinstance(c, dict) and c.get("type") in CONDITION_TYPES]
    result["lucidity_zero_pending_resolution"] = bool(raw.get("lucidity_zero_pending_resolution"))
    return result


def _write(row, state):
    row.data = {**(row.data if isinstance(row.data, dict) else {}), "runtime": state}
    row.version += 1
    row.save(update_fields=["data", "version", "updated_at"])


def _actor(data, who, *, lock=False):
    try:
        actor_id = UUID(str(data.get("actorId", data.get("id"))))
    except (ValueError, TypeError, AttributeError):
        raise MapError("Actor not found.", "not_found") from None
    query = Actor.objects.filter(pk=actor_id, campaign_id=who.campaign_id)
    row = (query.select_for_update() if lock else query).first()
    if row is None or not access(row, who, True):
        raise MapError("Character not found or access denied.", "not_found")
    return row


def initialize(data, who):
    row = _actor(data, who, lock=True)
    state = read(row.data)
    supplied = data.get("attributes", {})
    if supplied:
        if not isinstance(supplied, dict):
            raise MapError("Invalid runtime attributes.")
        for name in state["attributes"]:
            if name in supplied:
                state["attributes"][name] = _attribute(supplied[name], name)
    maximum = maxima(state["attributes"])
    for name in RESOURCE_NAMES:
        current = data.get("resources", {}).get(name) if isinstance(data.get("resources"), dict) else None
        if isinstance(current, dict) and "current" in current:
            current = _int(current["current"], f"{name}.current", 0, maximum[name])
        elif type(current) is int:
            current = _int(current, f"{name}.current", 0, maximum[name])
        else:
            current = maximum[name] if name != "determination" else 1
        state["resources"][name] = {"current": current, "max": maximum[name]}
    _write(row, state)
    return {"actorId": str(row.pk), "runtime": state}


def resource(data, who):
    row = _actor(data, who, lock=True)
    state = read(row.data)
    name = data.get("resource")
    operation = data.get("operation", "spend")
    amount = _int(data.get("amount", 1), "amount", 1, 1000)
    if name not in RESOURCE_NAMES or operation not in {"spend", "lose", "gain", "recover"}:
        raise MapError("Invalid runtime resource.")
    item = state["resources"][name]
    before = item["current"]
    if operation == "spend" and amount > before:
        raise MapError(f"Insufficient {name}.", "insufficient_resource")
    item["current"] = max(0, min(item["max"], before + (amount if operation in {"gain", "recover"} else -amount)))
    _post_resource_rules(state, name)
    _write(row, state)
    return {"actorId": str(row.pk), "resource": name, "operation": operation, "amount": amount,
            "before": before, "after": item["current"], "runtime": state}


def _post_resource_rules(state, name):
    current = state["resources"][name]["current"]
    if name == "vitality":
        if current == 0:
            _ensure_condition(state, "CAIDO", source="vitality_zero", applied_at=timezone.now().isoformat())
        elif current > 0:
            state["conditions"] = [c for c in state["conditions"] if c.get("type") != "CAIDO"]
    if name == "lucidity":
        state["lucidity_zero_pending_resolution"] = current == 0


def _ensure_condition(state, condition_type, **values):
    existing = next((c for c in state["conditions"] if c.get("type") == condition_type), None)
    if existing:
        existing.update(values)
        return existing
    condition = {"id": str(uuid4()), "type": condition_type, "source": values.pop("source", "runtime"),
                 "applied_by": values.pop("applied_by", "system"), "applied_at": values.pop("applied_at", ""),
                 "duration": values.pop("duration", DEFAULT_DURATION), "removal_rule": values.pop("removal_rule", "explicit"),
                 "intensity": values.pop("intensity", 1), "metadata": values.pop("metadata", {})}
    condition.update(values)
    state["conditions"].append(condition)
    return condition


def condition(data, who, action):
    row = _actor(data, who, lock=True)
    state = read(row.data)
    if action == "runtime.condition.apply":
        condition_type = data.get("condition_type", data.get("conditionType"))
        if condition_type not in CONDITION_TYPES:
            raise MapError("Invalid condition type.")
        condition_data = {
            "source": data.get("source", "manual"),
            "applied_by": str(who.user_id),
            "applied_at": timezone.now().isoformat(),
            "duration": data.get("duration", DEFAULT_DURATION),
            "removal_rule": data.get("removal_rule", "explicit"),
            "intensity": _int(data.get("intensity", 1), "intensity", 1, 1000),
            "metadata": data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        }
        if condition_type == "CORROMPIDO":
            condition_data["corruption_applies"] = data.get("corruption_applies") is True
        item = _ensure_condition(state, condition_type, **condition_data)
        result = {"condition": deepcopy(item), "applied": True}
    else:
        condition_id = data.get("condition_id", data.get("conditionId"))
        condition_type = data.get("condition_type", data.get("conditionType"))
        before = len(state["conditions"])
        state["conditions"] = [c for c in state["conditions"] if not ((condition_id and c.get("id") == str(condition_id)) or (condition_type and c.get("type") == condition_type))]
        result = {"condition": condition_type or condition_id, "removed": len(state["conditions"]) != before}
    _write(row, state)
    return {"actorId": str(row.pk), **result, "runtime": state}


def rest(data, who, full=False):
    row = _actor(data, who, lock=True)
    state = read(row.data)
    if not full and any(c.get("type") == "FRATURADO" for c in state["conditions"]):
        flow = state["resources"]["flow"]
        flow["current"] = min(flow["max"], flow["current"])
        restored = 0
    else:
        restored = []
        for name in RESOURCE_NAMES:
            if name == "determination":
                continue
            if full or name in {"breath", "flow"}:
                if name == "flow" and not full:
                    sintonia = state["attributes"]["sintonia"]
                    value = 1 + ceil(sintonia / 2)
                else:
                    value = state["resources"][name]["max"]
                item = state["resources"][name]
                before = item["current"]
                item["current"] = min(item["max"], before + value) if not full and name == "flow" else item["max"]
                restored.append(name)
        if full:
            _post_resource_rules(state, "vitality")
            _post_resource_rules(state, "lucidity")
    _write(row, state)
    return {"actorId": str(row.pk), "rest": "full" if full else "safe", "restored": restored,
            "flow_blocked": not full and not restored, "runtime": state}


def command(data, who, action):
    if action == "runtime.initialize":
        return initialize(data, who)
    if action == "runtime.resource":
        return resource(data, who)
    if action in {"runtime.condition.apply", "runtime.condition.remove"}:
        return condition(data, who, action)
    if action == "runtime.safe_pause":
        return rest(data, who)
    if action == "runtime.full_rest":
        return rest(data, who, full=True)
    raise MapError("Unknown runtime command.")


def action_modifier(actor_id, who, action_data, *, consume=False):
    """Resolve explicit condition effects for an action; no fuzzy text matching."""
    if not actor_id:
        return 0, []
    row = Actor.objects.select_for_update().filter(pk=actor_id, campaign_id=who.campaign_id).first()
    if row is None or not access(row, who, True):
        raise MapError("Character not found or access denied.", "not_found")
    state = read(row.data)
    modifier = 0
    consumed = []
    names = {"velarim", "merge", "evocação"}
    attribute = (action_data.get("attribute") or {}).get("name", "").casefold()
    skill = (action_data.get("skill") or {}).get("name", "").casefold()
    for item in state["conditions"]:
        kind = item.get("type")
        if kind == "ABALADO":
            modifier -= 2
            if consume:
                consumed.append(item.get("id"))
        elif kind == "DISSONANTE" and (attribute == "sintonia" or skill in names):
            modifier -= 2
        elif kind == "CORROMPIDO" and action_data.get("corruption_applies") is True and item.get("corruption_applies") is True:
            # Pressure is a level in the 03B action contract (two points per
            # level), and level 2 remains the hard cap.
            pressure = (action_data.get("pressure") or {}).get("level", 0)
            if pressure < 2:
                modifier -= 2
    if consume and consumed:
        state["conditions"] = [c for c in state["conditions"] if c.get("id") not in consumed]
        _write(row, state)
    return modifier, consumed


def adjust_result(result, modifier):
    if not modifier or not isinstance(result, dict):
        return result
    result = deepcopy(result)
    result["condition_modifier"] = modifier
    result["modifier"] += modifier
    result["total"] += modifier
    result["margin"] = result["total"] - result["difficulty"]
    result["success"] = result["total"] >= result["difficulty"]
    if result["margin"] <= -5:
        result["degree"] = result["grade"] = "failure_severe"
    elif result["margin"] < 0:
        result["degree"] = result["grade"] = "failure"
    elif result["margin"] <= 4:
        result["degree"] = result["grade"] = "success"
    elif result["margin"] <= 9:
        result["degree"] = result["grade"] = "success_strong"
    else:
        result["degree"] = result["grade"] = "success_extraordinary"
    return result
