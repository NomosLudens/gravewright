"""Server-authoritative KALLISTIS runtime resources and conditions.

This state deliberately lives beside, rather than inside, the PDF character
sheet.  It is campaign play state: small, bounded, auditable and transported
through the existing actor command/state channel.
"""

from copy import deepcopy
from math import ceil
import unicodedata
from uuid import UUID, uuid4
from django.utils import timezone

from .models import Actor
from .services import access
from gravewright.maps.services import MapError
from gravewright.rules import kallistis_runtime as rules


ATTRIBUTE_NAMES = (
    "corpo", "agilidade", "intelecto", "presenca", "vontade", "sintonia",
)
ATTRIBUTE_INITIALS = {
    "corpo": 3, "agilidade": 2, "intelecto": 2,
    "presenca": 1, "vontade": 1, "sintonia": 0,
}
SKILL_NAMES = (
    "atletismo", "combate", "pontaria", "furtividade", "percepcao",
    "sobrevivencia", "investigacao", "conhecimento", "oficio", "influencia",
    "empatia", "cuidado", "magia", "evocacao", "velarim",
)
SKILL_MAX = 5
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
    # Marco remains a separate legacy/progression input used by the documented
    # Fluxo formula; it is not one of the six character attributes.
    attributes = {name: 0 for name in ATTRIBUTE_NAMES}
    attributes["marco"] = 0
    maximum = maxima(attributes)
    return {
        "attributes": attributes,
        "people": None,
        "resources": {
            name: {"current": maximum[name] if name != "determination" else 1, "max": maximum[name]}
            for name in RESOURCE_NAMES
        },
        "conditions": [],
        "skills": {name: 0 for name in SKILL_NAMES},
        "protection": 0,
        "combat": {
            "permanence_successes": 0,
            "permanence_failures": 0,
            "permanence_outcome": None,
            "grave_wound": False,
        },
        "lucidity_zero_pending_resolution": False,
        "rules": rules.new_session_state(attributes=attributes, skills={name: 0 for name in SKILL_NAMES}),
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
                result["attributes"][name] = _attribute(attributes[name], name)
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
    protection = raw.get("protection", 0)
    result["protection"] = protection if type(protection) is int and protection >= 0 else 0
    skills = raw.get("skills", {})
    if isinstance(skills, dict):
        for name in SKILL_NAMES:
            value = skills.get(name)
            if type(value) is int and 0 <= value <= SKILL_MAX:
                result["skills"][name] = value
    people = raw.get("people")
    if isinstance(people, dict):
        try:
            result.update(_people_projection({**people, "heritage": raw.get("heritage", people.get("heritage"))}))
        except MapError:
            pass
    combat = raw.get("combat", {})
    if isinstance(combat, dict):
        for key in ("permanence_successes", "permanence_failures"):
            if type(combat.get(key)) is int and combat[key] >= 0:
                result["combat"][key] = combat[key]
        if combat.get("permanence_outcome") in {None, "STABILIZED", "TERMINAL"}:
            result["combat"]["permanence_outcome"] = combat.get("permanence_outcome")
        result["combat"]["grave_wound"] = combat.get("grave_wound") is True
        if isinstance(combat.get("permanence_last"), dict):
            result["combat"]["permanence_last"] = deepcopy(combat["permanence_last"])
    conditions = raw.get("conditions", [])
    if isinstance(conditions, list):
        result["conditions"] = [deepcopy(c) for c in conditions if isinstance(c, dict) and c.get("type") in CONDITION_TYPES]
    result["lucidity_zero_pending_resolution"] = bool(raw.get("lucidity_zero_pending_resolution"))
    rules_state = raw.get("rules")
    if isinstance(rules_state, dict):
        result["rules"] = rules.normalize_state(rules_state)
    else:
        result["rules"] = rules.new_session_state(
            attributes=result["attributes"], skills=result["skills"], protection=result["protection"]
        )
    result["rules"]["attributes"] = deepcopy(result["attributes"])
    result["rules"]["skills"] = deepcopy(result["skills"])
    result["rules"]["protection"] = result["protection"]
    result["rules"]["resources"] = deepcopy(result["resources"])
    result["rules"]["conditions"] = deepcopy(result["conditions"])
    return result
def _write(row, state):
    state["rules"] = _rules_for(state)
    row.data = {**(row.data if isinstance(row.data, dict) else {}), "runtime": state}
    row.version += 1
    row.save(update_fields=["data", "version", "updated_at"])


def _rules_for(state):
    """Keep the generic legacy projection and the canonical rule state aligned."""
    current = state.get("rules") if isinstance(state, dict) else None
    if not isinstance(current, dict):
        current = rules.new_session_state(
            attributes=state.get("attributes", {}),
            skills=state.get("skills", {}),
            protection=state.get("protection", 0),
        )
    current = rules.normalize_state(current)
    current["attributes"] = deepcopy(state.get("attributes", current.get("attributes", {})))
    current["skills"] = deepcopy(state.get("skills", current.get("skills", {})))
    current["protection"] = state.get("protection", current.get("protection", 0))
    current["resources"] = deepcopy(state.get("resources", current.get("resources", {})))
    current["conditions"] = deepcopy(state.get("conditions", current.get("conditions", [])))
    return current


def _sync_from_rules(state, rules_state):
    state["rules"] = rules_state
    state["resources"] = deepcopy(rules_state.get("resources", state["resources"]))
    state["conditions"] = deepcopy(rules_state.get("conditions", state["conditions"]))
    state["combat"] = deepcopy(rules_state.get("combat", state["combat"]))
    state["fulgor"] = rules_state.get("fulgor", state.get("fulgor", 0))
    state["sombra"] = rules_state.get("sombra", state.get("sombra", 0))
    state["coro"] = deepcopy(rules_state.get("coro", state.get("coro", {})))


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
    raw_runtime = row.data.get("runtime") if isinstance(row.data, dict) else None
    raw_resources = raw_runtime.get("resources") if isinstance(raw_runtime, dict) else None
    preserve_current = isinstance(raw_resources, dict) and all(name in raw_resources for name in RESOURCE_NAMES)
    supplied = data.get("attributes", {})
    if supplied:
        if not isinstance(supplied, dict):
            raise MapError("Invalid runtime attributes.")
        unknown = set(supplied) - set(ATTRIBUTE_NAMES) - {"marco"}
        if unknown:
            raise MapError("Invalid runtime attribute.")
        for name in state["attributes"]:
            if name in supplied:
                state["attributes"][name] = _attribute(supplied[name], name)
    maximum = maxima(state["attributes"])
    if "protection" in data:
        state["protection"] = _int(data["protection"], "protection", 0, 1000)
    if "skills" in data:
        if not isinstance(data["skills"], dict):
            raise MapError("Invalid runtime skills.")
        unknown = set(data["skills"]) - set(SKILL_NAMES)
        if unknown:
            raise MapError("Invalid runtime skill.")
        for name, value in data["skills"].items():
            state["skills"][name] = _int(value, f"skills.{name}", 0, SKILL_MAX)
    if "people" in data:
        state.update(_people_projection(data["people"]))
    for name in RESOURCE_NAMES:
        current = data.get("resources", {}).get(name) if isinstance(data.get("resources"), dict) else None
        if isinstance(current, dict) and "current" in current:
            current = _int(current["current"], f"{name}.current", 0, maximum[name])
        elif type(current) is int:
            current = _int(current, f"{name}.current", 0, maximum[name])
        else:
            default = maximum[name] if name != "determination" else 1
            current = min(state["resources"][name]["current"], maximum[name]) if preserve_current else default
        state["resources"][name] = {"current": current, "max": maximum[name]}
    _write(row, state)
    return {"actorId": str(row.pk), "runtime": state}


def _canonical_name(value, names, field):
    if not isinstance(value, str):
        raise MapError(f"Invalid {field}.")
    normalized = _fold_name(value)
    for name in names:
        if normalized == _fold_name(name):
            return name
    raise MapError(f"Invalid {field}.")


def _fold_name(value):
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(char)
    )


def authoritative_action(actor_id, who, action_data):
    """Prepare an action using the linked Actor as numeric authority."""
    row = _actor({"actorId": actor_id}, who, lock=False)
    state = read(row.data)
    if not isinstance(action_data, dict):
        raise MapError("Structured action is required.")
    attribute = action_data.get("attribute")
    attribute_name = attribute.get("name") if isinstance(attribute, dict) else action_data.get("attribute_name", action_data.get("attributeName"))
    skill = action_data.get("skill")
    skill_name = skill.get("name") if isinstance(skill, dict) else action_data.get("skill_name", action_data.get("skillName"))
    attribute_name = _canonical_name(attribute_name, ATTRIBUTE_NAMES, "attribute")
    skill_name = _canonical_name(skill_name, SKILL_NAMES, "skill")
    bound = deepcopy(action_data)
    bound["attribute"] = {"name": attribute_name, "value": state["attributes"][attribute_name]}
    bound["skill"] = {"name": skill_name, "value": state["skills"].get(skill_name, 0)}
    from gravewright.dice.kallistis import prepare_action
    prepared = prepare_action(bound)
    if state["people"] is not None:
        for key in ("people", "trait", "gift", "heritage", "dissonance"):
            prepared[key] = deepcopy(state[key])
    prepared["actor_id"] = str(row.pk)
    prepared["actor_version"] = row.version
    return prepared


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


def rules_command(data, who):
    """Execute a canonical session rule through the actor command channel."""
    row = _actor(data, who, lock=True)
    state = read(row.data)
    operation = data.get("operation")
    rules_state = _rules_for(state)
    result = None
    if operation == "test":
        attribute = data.get("attribute", {})
        skill = data.get("skill", {})
        attribute_name = attribute.get("name") if isinstance(attribute, dict) else attribute
        skill_name = skill.get("name") if isinstance(skill, dict) else skill
        if attribute_name not in ATTRIBUTE_NAMES or skill_name not in SKILL_NAMES:
            raise MapError("Invalid runtime test attribute or skill.")
        result = rules.roll_test(
            attribute=state["attributes"][attribute_name],
            skill=state["skills"][skill_name],
            difficulty=data.get("difficulty", 15),
            impulse_sources=data.get("impulseSources", ()),
            pressure_sources=data.get("pressureSources", ()),
            helpers=data.get("helpers", ()),
            fixed_modifier=data.get("fixedModifier", 0),
        )
    elif operation == "damage":
        result = rules.apply_damage(
            rules_state, data.get("amount", 0), protection=data.get("protection"),
            fortitude=10 + state["attributes"].get("corpo", 0) + state["attributes"].get("vontade", 0),
            damage_event=data.get("eventId", "runtime"), true_damage=data.get("trueDamage") is True,
        )
        _sync_from_rules(state, result["state"])
    elif operation == "permanence":
        result = rules.permanence(rules_state)
        _sync_from_rules(state, result["state"])
    elif operation == "lucidity_zero":
        result = rules.lucidity_zero(rules_state, data.get("choice"))
        _sync_from_rules(state, result["state"])
    elif operation == "round.begin":
        result = {"state": rules.begin_round(rules_state, movement_mode=data.get("movementMode", "GRID"))}
        _sync_from_rules(state, result["state"])
    elif operation == "action.spend":
        result = {"state": rules.spend_action(rules_state, data.get("kind", "action"))}
        _sync_from_rules(state, result["state"])
    elif operation == "movement":
        result = rules.run_movement(rules_state, data.get("points", ()), terrain=data.get("terrain", "NORMAL"), forced=data.get("forced") is True, teleport=data.get("teleport") is True)
        _sync_from_rules(state, result["state"])
    elif operation == "technique":
        result = rules.technique(marco=state["attributes"].get("marco", 0), minimum_marco=data.get("minimumMarco", 1), action=data.get("action", "action"), cost=data.get("cost"), scene_key=data.get("sceneKey"), used_keys=state.get("scene_uses", {}).keys())
    elif operation == "magic":
        result = rules.magic(grade=data.get("grade"), marco=state["attributes"].get("marco", 0), action=data.get("action", "action"), cost=data.get("cost"), concentration=data.get("concentration") is True, current_concentration=rules_state.get("concentration"))
        if result.get("cost", 0):
            spent = rules.change_resource(rules_state, "flow", result["cost"], operation="spend")
            _sync_from_rules(state, spent["state"])
    elif operation == "concentration":
        result = rules.concentration_check(rules_state, data.get("damage", 0))
        _sync_from_rules(state, result["state"])
    elif operation == "evocation":
        result = rules.evocation(kind=data.get("kind", "minor"), tuning=state["attributes"].get("sintonia", 0), evocation_skill=state["skills"].get("evocacao", 0), unstable=data.get("unstable") is True, source=data.get("source"), flow_available=state["resources"]["flow"]["current"])
        spent = rules.change_resource(rules_state, "flow", result["profile"]["cost"], operation="spend")
        _sync_from_rules(state, spent["state"])
    elif operation == "merge":
        result = rules.merge(mode=data.get("mode", "voluntary_union"), consent=data.get("consent") is True, tuning=state["attributes"].get("sintonia", 0), skill=state["skills"].get(data.get("skill", "empatia"), 0), flow_available=state["resources"]["flow"]["current"], active=rules_state.get("merge"), benefits=data.get("benefits", ()))
        spent = rules.change_resource(rules_state, "flow", result["cost_each"], operation="spend")
        rules_state = spent["state"]; rules_state["merge"] = result; _sync_from_rules(state, rules_state)
    elif operation == "coro.add":
        result = rules.add_coro_pulse(rules_state, eligible=data.get("eligible", True) is True)
        _sync_from_rules(state, result["state"])
    elif operation == "coro.spend":
        result = rules.spend_coro(rules_state, data.get("role", "vanguarda"), data.get("level", 1))
        _sync_from_rules(state, result["state"])
    elif operation == "shadow":
        result = rules.change_shadow(rules_state, data.get("delta", 0), reason=data.get("reason", "runtime"))
        _sync_from_rules(state, result["state"])
    elif operation == "fulgor":
        result = rules.fulgor_gain(rules_state, data.get("amount", 1))
        _sync_from_rules(state, result["state"])
    elif operation == "artifact":
        result = rules.artifact_use(rules_state, data.get("artifact"), frequency=data.get("frequency", "scene"), use_key=data.get("useKey"))
        _sync_from_rules(state, result["state"])
    elif operation == "safe_pause":
        result = rules.safe_pause(rules_state)
        _sync_from_rules(state, result["state"])
    elif operation == "full_rest":
        result = rules.full_rest(rules_state)
        _sync_from_rules(state, result["state"])
    elif operation == "fissure":
        result = rules.fissure_traversal(state_name=data.get("stateName", "RESSONANTE"), contributions=data.get("contributions", []), has_destination=data.get("hasDestination", True) is True, has_anchor=data.get("hasAnchor", True) is True, cost_accepted=data.get("costAccepted", True) is True)
    else:
        raise MapError("Unknown KALLISTIS runtime operation.")
    _write(row, state)
    return {"actorId": str(row.pk), "operation": operation, "result": result, "runtime": state}


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
    if action == "runtime.rules":
        return rules_command(data, who)
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
PEOPLE_RULES = {
    "aelvari": {
        "label": "Aelvari",
        "trait": {"id": "memoria_estratificada", "label": "Memória Estratificada"},
        "gift": {"id": "eco_paralelo", "label": "Eco Paralelo"},
        "heritages": {"cronista": {"label": "Cronista"}, "vidente_cauteloso": {"label": "Vidente Cauteloso"}},
        "dissonance": {"id": "sobrecarga_temporal", "label": "Sobrecarga Temporal"},
    },
    "kragor": {
        "label": "Kragor",
        "trait": {"id": "forca_de_comunidade", "label": "Força de Comunidade"},
        "gift": {"id": "juramento_operante", "label": "Juramento Operante"},
        "heritages": {"escudo_do_cla": {"label": "Escudo do Clã"}, "voz_da_assembleia": {"label": "Voz da Assembleia"}},
        "dissonance": {"id": "honra_fechada", "label": "Honra Fechada"},
    },
    "draken": {
        "label": "Draken",
        "trait": {"id": "corpo_elemental", "label": "Corpo Elemental"},
        "gift": {"id": "manifestacao_elemental", "label": "Manifestação Elemental"},
        "heritages": {"soberania": {"label": "Soberania"}, "condutor": {"label": "Condutor"}},
        "dissonance": {"id": "hybris", "label": "Hýbris"},
    },
    "nomos": {
        "label": "Nomos",
        "trait": {"id": "chassi_modular", "label": "Chassi Modular"},
        "gift": {"id": "lei_interior", "label": "Lei Interior"},
        "heritages": {"reparador": {"label": "Reparador"}, "processador": {"label": "Processador"}},
        "dissonance": {"id": "otimizacao_absoluta", "label": "Otimização Absoluta"},
    },
    "livres": {
        "label": "Livres",
        "trait": {"id": "aprendizagem_cruzada", "label": "Aprendizagem Cruzada"},
        "gift": {"id": "solucao_improvisada", "label": "Solução Improvisada"},
        "heritages": {"comunidade_escolhida": {"label": "Comunidade Escolhida"}, "multiplos_caminhos": {"label": "Múltiplos Caminhos"}},
        "dissonance": {"id": "identidade_oferecida", "label": "Identidade Oferecida"},
    },
    "doreos": {
        "label": "Dóreos",
        "trait": {"id": "memoria_da_materia", "label": "Memória da Matéria"},
        "gift": {"id": "inscricao_de_promessa", "label": "Inscrição de Promessa"},
        "heritages": {"forjador": {"label": "Forjador"}, "guardiao_de_obra": {"label": "Guardião de Obra"}},
        "dissonance": {"id": "permanencia_rigida", "label": "Permanência Rígida"},
    },
    "teriantes": {
        "label": "Teriantes",
        "trait": {"id": "aspecto_faunistico", "label": "Aspecto Faunístico"},
        "gift": {"id": "instinto_inteiro", "label": "Instinto Inteiro"},
        "heritages": {"cacador": {"label": "Caçador"}, "protetor_de_bando": {"label": "Protetor de Bando"}},
        "dissonance": {"id": "reducao_ao_impulso", "label": "Redução ao Impulso"},
    },
    "nimari": {
        "label": "Nimari",
        "trait": {"id": "passo_liminal", "label": "Passo Liminal"},
        "gift": {"id": "dado_da_fortuna", "label": "Dado da Fortuna"},
        "heritages": {"cartografo_de_frestas": {"label": "Cartógrafo de Frestas"}, "negociador_de_risco": {"label": "Negociador de Risco"}},
        "dissonance": {"id": "caminho_sem_compromisso", "label": "Caminho Sem Compromisso"},
    },
    "vitralios": {
        "label": "Vitrálios",
        "trait": {"id": "corpo_harmonico", "label": "Corpo Harmônico"},
        "gift": {"id": "ressonancia_prismatica", "label": "Ressonância Prismática"},
        "heritages": {"lapidador_de_si": {"label": "Lapidador de Si"}, "coro_vitralio": {"label": "Coro Vitrálio"}},
        "dissonance": {"id": "quebra_frequencial", "label": "Quebra Frequencial"},
    },
}

def _people_projection(value):
    if not isinstance(value, dict):
        raise MapError("Invalid people data.")
    people_value = value.get("id", value.get("name"))
    people_id = _canonical_name(people_value, PEOPLE_RULES, "people")
    rule = PEOPLE_RULES[people_id]
    heritage = value.get("heritage")
    if isinstance(heritage, dict):
        heritage = heritage.get("id", heritage.get("name"))
    heritage_id = _canonical_name(heritage, rule["heritages"], "heritage")
    selected = rule["heritages"][heritage_id]
    return {
        "people": {"id": people_id, "label": rule["label"]},
        "trait": deepcopy(rule["trait"]),
        "gift": deepcopy(rule["gift"]),
        "heritage": {"id": heritage_id, "label": selected["label"]},
        "dissonance": deepcopy(rule["dissonance"]),
    }
