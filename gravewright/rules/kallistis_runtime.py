"""Server-side execution primitives for the KALLISTIS mesa rules.

KALLISTIS owns character creation, permanent progression and canonical sheet
data.  Gravewright owns the transient execution of those facts during a
session.  This module is deliberately framework-free so the same rules can be
used by actor commands, combat, realtime payloads and deterministic tests.

The random core remains ``gravewright.dice.kallistis.evaluate``.  This module
does not introduce another 2d10 formula.
"""

from copy import deepcopy
from math import ceil, floor

from gravewright.dice.kallistis import evaluate as evaluate_kallistis


class RuleError(ValueError):
    """A canonical runtime rule was violated."""


ATTRIBUTES = ("corpo", "agilidade", "intelecto", "presenca", "vontade", "sintonia")
SKILLS = (
    "atletismo", "combate", "pontaria", "furtividade", "percepcao",
    "sobrevivencia", "investigacao", "conhecimento", "oficio", "influencia",
    "empatia", "cuidado", "magia", "evocacao", "velarim",
)
RESOURCES = ("vitality", "lucidity", "flow", "breath", "determination")
CONDITIONS = {
    "ABALADO": {"effect": "next_test_minus_2", "default_duration": "source_next_turn"},
    "EXPOSTO": {"effect": "attacks_against_plus_2", "default_duration": "source_next_turn"},
    "IMOBILIZADO": {"effect": "movement_zero", "default_duration": "source_next_turn"},
    "LENTO": {"effect": "movement_minus_2_grid_minus_1_zone", "default_duration": "source_next_turn"},
    "SANGRANDO": {"effect": "end_turn_vitality_minus_2", "default_duration": "until_care"},
    "SILENCIADO": {"effect": "voice_only_block", "default_duration": "source_next_turn"},
    "DISSONANTE": {"effect": "sintonia_velarim_merge_evocation_minus_2", "default_duration": "source_next_turn"},
    "FRATURADO": {"effect": "flow_recovery_block_fissure_lucidity_plus_1", "default_duration": "until_treatment"},
    "CORROMPIDO": {"effect": "direct_corruption_pressure_1", "default_duration": "until_repair"},
    "CAIDO": {"effect": "no_common_actions_concentration_lost", "default_duration": "until_stabilized"},
}
DIFFICULTIES = {
    10: "baixa", 12: "favoravel", 15: "incerta", 18: "dificil",
    21: "severa", 24: "extrema", 27: "legendaria", 30: "epica",
}
GRADE_BY_MARGIN = (
    (-5, "failure_severe"), (-1, "failure"), (0, "success"),
    (5, "success_strong"), (10, "success_extraordinary"),
)
POWER_MULTIPLIERS = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}
MAGIC_GRADE_MULTIPLIERS = {0: 1, 1: 2, 2: 3, 3: 4, 4: 4, 5: 4, 6: 4}
MAGIC_GRADE_COSTS = {0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 3, 6: 3}
EPIC_GRADE_MARKS = {4: 11, 5: 13, 6: 15}
FISSURE_DIFFICULTIES = {"LATENTE": 21, "RESSONANTE": 15, "ABERTA": 12, "FRATURADA": 18, "CORROMPIDA": 21}
SHADOW_STATES = {0: "integro", 1: "influencia", 2: "influencia", 3: "cicatriz_ativa", 4: "cicatriz_ativa", 5: "limiar_assimilacao", 6: "crise_identidade"}
PROGRESSION = {
    1: {"gain": "creation", "max_attribute": 4},
    2: {"gain": "technique_or_magic", "max_attribute": 4},
    3: {"gain": "occupation_specialization", "max_attribute": 4},
    4: {"gain": "skill_and_technique", "max_attribute": 4},
    5: {"gain": "attribute", "max_attribute": 4},
    6: {"gain": "advanced_technique_or_major_evocation", "max_attribute": 4},
    7: {"gain": "attribute", "max_attribute": 5},
    8: {"gain": "skill_and_bond", "max_attribute": 5},
    9: {"gain": "second_specialization_or_other_occupation", "max_attribute": 5},
    10: {"gain": "legacy", "max_attribute": 5},
    11: {"gain": "attribute", "max_attribute": 6, "horizon": "scene", "epic_magic": 4},
    12: {"gain": "attribute", "max_attribute": 7, "horizon": "neighborhood"},
    13: {"gain": "attribute", "max_attribute": 8, "horizon": "city", "epic_magic": 5},
    14: {"gain": "attribute", "max_attribute": 9, "horizon": "people"},
    15: {"gain": "attribute", "max_attribute": 10, "horizon": "world", "epic_magic": 6},
}

WEAPONS = {
    "desarmado": {"damage": 2, "range": "melee", "tags": ("leve", "nao_letal")},
    "improvisada": {"damage": 3, "range": "melee", "tags": ("precaria",)},
    "faca": {"damage": 3, "range": "melee", "tags": ("leve", "ocultavel")},
    "clava": {"damage": 4, "range": "melee", "tags": ("impacto",)},
    "bastao": {"damage": 3, "range": "melee", "tags": ("duas_maos", "foco")},
    "lanca_curta": {"damage": 4, "range": "melee_or_6", "tags": ("alcance", "arremesso")},
    "espada": {"damage": 5, "range": "melee", "tags": ("equilibrada",)},
    "sabre": {"damage": 5, "range": "melee", "tags": ("leve", "equilibrada")},
    "machado": {"damage": 6, "range": "melee", "tags": ("potente",)},
    "martelo_de_guerra": {"damage": 6, "range": "melee", "tags": ("impacto", "pesada")},
    "lanca_longa": {"damage": 5, "range": "2_cells", "tags": ("alcance", "duas_maos")},
    "lamina_grande": {"damage": 7, "range": "melee", "tags": ("potente", "pesada", "duas_maos")},
    "arma_de_haste": {"damage": 6, "range": "2_cells", "tags": ("alcance", "pesada", "duas_maos")},
    "funda": {"damage": 3, "range": 10, "tags": ("leve", "municao")},
    "arremesso": {"damage": 4, "range": 6, "tags": ("arremesso", "leve")},
    "arco": {"damage": 5, "range": 18, "tags": ("duas_maos", "municao")},
    "besta": {"damage": 6, "range": 18, "tags": ("recarga", "duas_maos")},
    "besta_pesada": {"damage": 7, "range": 24, "tags": ("recarga", "pesada", "perfurante", "duas_maos")},
    "arma_de_disparo": {"damage": 6, "range": 18, "tags": ("ruidosa", "municao")},
    "repetidor_nomos": {"damage": 5, "range": 12, "tags": ("rajada", "municao", "modular")},
    "projetor_de_quartzo": {"damage": 6, "range": 12, "tags": ("magico", "foco", "duas_maos")},
    "bastao_ritual": {"damage": 3, "range": "melee", "tags": ("foco",)},
    "lamina_ressonante": {"damage": 5, "range": "melee", "tags": ("magico", "equilibrada")},
    "luva_de_inscricao": {"damage": 4, "range": 6, "tags": ("magico", "modular", "foco")},
}
ARMOR = {
    "roupas_reforcadas": {"protection": 1, "guard": 0, "spaces": 1},
    "leve": {"protection": 2, "guard": 0, "spaces": 1},
    "media": {"protection": 3, "guard": 0, "spaces": 2, "penalty": {"furtividade": -1}},
    "pesada": {"protection": 4, "guard": 0, "spaces": 3, "penalty": {"agilidade": -1}},
    "escudo": {"protection": 0, "guard": 1, "spaces": 1},
}
CONSUMABLES = {
    "tonico_de_vitalidade": {"effect": "vitality", "amount": 5, "frequency": "scene"},
    "estabilizador_de_fluxo": {"effect": "flow", "amount": 2, "pressure": 2},
    "sal_de_memoria": {"effect": "integrity_defense", "amount": 2, "frequency": "scene"},
    "selo_de_contencao": {"effect": "magic_activity", "area": "3x3"},
    "municao_de_quartzo": {"effect": "damage_vs_barrier", "amount": 2},
    "fio_de_retorno": {"effect": "recover_thrown_or_key", "range": 6},
    "carga_de_reparo": {"effect": "structural_integrity", "amount": 6},
    "ampola_de_repouso": {"effect": "lucidity", "amount": 3, "condition": "LENTO"},
}


def _int(value, name, minimum=None, maximum=None):
    if type(value) is not int or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise RuleError(f"Invalid {name}.")
    return value


def _margin_grade(margin):
    if margin <= -5:
        return "failure_severe"
    if margin < 0:
        return "failure"
    if margin <= 4:
        return "success"
    if margin <= 9:
        return "success_strong"
    return "success_extraordinary"


def _sources_total(sources, *, positive):
    """Sum distinct circumstance sources, rejecting duplicate fiction."""
    if sources is None:
        return 0
    if not isinstance(sources, (list, tuple)):
        raise RuleError("Circumstance sources must be a list.")
    seen = set()
    total = 0
    for source in sources:
        if isinstance(source, str):
            source_id, points = source, 1
        elif isinstance(source, dict):
            source_id = source.get("id", source.get("source"))
            points = source.get("points", source.get("steps", 1))
        else:
            raise RuleError("Invalid circumstance source.")
        if not isinstance(source_id, str) or not source_id.strip():
            raise RuleError("Circumstance source requires an id.")
        if source_id in seen:
            raise RuleError("The same fictional circumstance cannot be stacked.")
        seen.add(source_id)
        _int(points, "circumstance points", 1, 100)
        total += points
    return total


def circumstance_modifier(*, impulse_sources=(), pressure_sources=(), helpers=()):
    helpers = list(helpers or ())
    if len(helpers) > 2:
        raise RuleError("At most two competent helpers may assist a test.")
    impulse_points = _sources_total(impulse_sources, positive=True) + len(helpers)
    pressure_points = _sources_total(pressure_sources, positive=False)
    return {
        "impulse_steps": impulse_points,
        "pressure_steps": pressure_points,
        "impulse_bonus": min(4, impulse_points * 2),
        "pressure_penalty": -min(4, pressure_points * 2),
        "helper_count": len(helpers),
        "helper_bonus": min(4, len(helpers) * 2),
    }


def resolve_test(*, light, dark, attribute=0, skill=0, difficulty=15,
                 impulse_sources=(), pressure_sources=(), helpers=(), fixed_modifier=0):
    """Resolve a deterministic KALLISTIS test while preserving both dice."""
    _int(light, "light", 1, 10); _int(dark, "dark", 1, 10)
    _int(attribute, "attribute"); _int(skill, "skill"); _int(difficulty, "difficulty", 1, 1000)
    _int(fixed_modifier, "fixed_modifier")
    circumstances = circumstance_modifier(
        impulse_sources=impulse_sources, pressure_sources=pressure_sources, helpers=helpers,
    )
    modifier = attribute + skill + fixed_modifier + circumstances["impulse_bonus"] + circumstances["pressure_penalty"]
    source = iter(((light - 1) / 10, (dark - 1) / 10)).__next__
    result = evaluate_kallistis(modifier, difficulty, random_source=source)
    return {
        **result, "version": 3, "critical": False, "critical_type": None,
        "impulse_bonus": circumstances["impulse_bonus"],
        "pressure_penalty": circumstances["pressure_penalty"], "helper_count": circumstances["helper_count"],
        "circumstances": circumstances,
    }


def roll_test(*, attribute=0, skill=0, difficulty=15, impulse_sources=(), pressure_sources=(), helpers=(), fixed_modifier=0, random_source=None):
    """Use the single dice authority and enrich its result with runtime metadata."""
    circumstances = circumstance_modifier(impulse_sources=impulse_sources, pressure_sources=pressure_sources, helpers=helpers)
    result = evaluate_kallistis(
        attribute + skill + fixed_modifier + circumstances["impulse_bonus"] + circumstances["pressure_penalty"],
        difficulty, random_source=random_source,
    )
    return {**result, "version": 3, "circumstances": circumstances,
            "impulse_bonus": circumstances["impulse_bonus"], "pressure_penalty": circumstances["pressure_penalty"]}


def opposed_test(agent, defender, *, tie="defender", random_source=None):
    """Resolve two universal tests; defender wins an established-position tie."""
    if not isinstance(agent, dict) or not isinstance(defender, dict):
        raise RuleError("Both opposed sides are required.")
    left = roll_test(attribute=agent.get("attribute", 0), skill=agent.get("skill", 0), difficulty=1, random_source=random_source)
    right = roll_test(attribute=defender.get("attribute", 0), skill=defender.get("skill", 0), difficulty=1, random_source=random_source)
    if left["total"] > right["total"]:
        winner = "agent"
    elif right["total"] > left["total"]:
        winner = "defender"
    elif tie == "agent":
        winner = "agent"
    elif tie == "impasse":
        winner = "impasse"
    else:
        winner = "defender"
    return {"agent": left, "defender": right, "winner": winner, "tie": left["total"] == right["total"]}


def scale_multiplier(attribute):
    attribute = _int(attribute, "attribute", 0)
    return 1 if attribute <= 4 else 2 ** (attribute - 4)


def derived(attributes, protection=0):
    raw = attributes if isinstance(attributes, dict) else {}
    attributes = {name: _int(raw.get(name, 0), name) for name in ATTRIBUTES}
    marco = _int(raw.get("marco", 0), "marco", 0)
    return {
        "vitality": 10 + attributes["corpo"] * 3,
        "lucidity": 8 + attributes["vontade"] * 3,
        "flow": 3 + attributes["sintonia"] + ceil(marco / 2),
        "guard": 10 + attributes["agilidade"] + _int(protection, "protection", 0),
        "fortitude": 10 + attributes["corpo"] + attributes["vontade"],
        "integrity": 10 + attributes["vontade"] + attributes["sintonia"],
        "movement_grid": 6, "movement_zones": 2, "breath": 3, "determination": 3,
    }


def new_session_state(attributes=None, skills=None, protection=0):
    attributes = {name: 0 for name in ATTRIBUTES} | (attributes or {})
    attributes["marco"] = (attributes or {}).get("marco", 0)
    maximum = derived(attributes, protection)
    return {
        "attributes": deepcopy(attributes), "skills": {name: 0 for name in SKILLS} | (skills or {}),
        "protection": protection,
        "resources": {name: {"current": maximum[name] if name not in {"determination"} else 1, "max": maximum[name]} for name in RESOURCES},
        "conditions": [],
        "action_economy": {"action": 1, "movement": maximum["movement_grid"], "reaction": 1, "round": 0},
        "combat": {"permanence_successes": 0, "permanence_failures": 0, "outcome": None, "grave_wounds": []},
        "fulgor": 0, "sombra": 0, "coro": {"pulses": 0, "bars": 0, "maximum_bars": 1},
        "concentration": None, "merge": None, "evocations": [], "effects": [],
        "inventory": [], "scene_uses": {}, "operation_uses": {}, "session_uses": {},
    }


def normalize_state(state):
    if not isinstance(state, dict):
        raise RuleError("Runtime state is required.")
    result = state
    result.setdefault("conditions", [])
    result.setdefault("combat", {"permanence_successes": 0, "permanence_failures": 0, "outcome": None, "grave_wounds": []})
    result.setdefault("action_economy", {"action": 1, "movement": 6, "reaction": 1, "round": 0})
    result.setdefault("fulgor", 0); result.setdefault("sombra", 0)
    result.setdefault("coro", {"pulses": 0, "bars": 0, "maximum_bars": 1})
    return result


def change_resource(state, name, amount, *, operation="spend"):
    state = normalize_state(state)
    if name not in RESOURCES or type(amount) is not int or amount < 1:
        raise RuleError("Invalid resource operation.")
    item = state["resources"].get(name)
    if not isinstance(item, dict):
        raise RuleError("Resource is not present in runtime state.")
    before = item["current"]
    if operation in {"spend", "lose"}:
        if operation == "spend" and amount > before:
            raise RuleError(f"Insufficient {name}.")
        after = max(0, before - amount)
    elif operation in {"gain", "recover"}:
        after = min(item["max"], before + amount)
    else:
        raise RuleError("Invalid resource operation.")
    item["current"] = after
    if name == "vitality" and after == 0:
        add_condition(state, "CAIDO", source="vitality_zero")
    return {"resource": name, "operation": operation, "amount": amount, "before": before, "after": after, "state": state}


def add_condition(state, condition, *, source="runtime", duration=None, intensity=1, metadata=None):
    state = normalize_state(state)
    if condition not in CONDITIONS:
        raise RuleError("Unknown KALLISTIS condition.")
    item = next((row for row in state["conditions"] if row.get("type") == condition), None)
    if item is None:
        item = {"id": f"condition:{condition}:{len(state['conditions']) + 1}", "type": condition,
                "source": source, "duration": duration or CONDITIONS[condition]["default_duration"],
                "intensity": intensity, "metadata": metadata or {}}
        state["conditions"].append(item)
    else:
        item.update({"source": source, "duration": duration or item.get("duration"), "intensity": intensity, "metadata": metadata or item.get("metadata", {})})
    return item


def remove_condition(state, condition=None, condition_id=None):
    state = normalize_state(state)
    before = len(state["conditions"])
    state["conditions"] = [item for item in state["conditions"] if not ((condition and item.get("type") == condition) or (condition_id and item.get("id") == str(condition_id)))]
    return {"removed": before - len(state["conditions"]), "state": state}


def safe_pause(state):
    state = normalize_state(state)
    if any(item.get("type") == "FRATURADO" for item in state["conditions"]):
        return {"restored": [], "flow_blocked": True, "state": state}
    state["resources"]["breath"]["current"] = state["resources"]["breath"]["max"]
    sintonia = state["attributes"].get("sintonia", 0)
    flow = state["resources"]["flow"]
    flow["current"] = min(flow["max"], flow["current"] + 1 + ceil(sintonia / 2))
    return {"restored": ["breath", "flow"], "flow_blocked": False, "state": state}


def full_rest(state):
    state = normalize_state(state)
    for name in ("vitality", "lucidity", "flow", "breath"):
        state["resources"][name]["current"] = state["resources"][name]["max"]
    remove_condition(state, "CAIDO")
    return {"restored": ["vitality", "lucidity", "flow", "breath"], "determination_preserved": True, "state": state}


def begin_round(state, *, movement_mode="GRID"):
    state = normalize_state(state)
    if movement_mode not in {"GRID", "ZONES"}:
        raise RuleError("Unknown movement scale.")
    economy = state["action_economy"]
    economy.update({"action": 1, "movement": 6 if movement_mode == "GRID" else 2, "reaction": 1, "movement_mode": movement_mode})
    economy["round"] = economy.get("round", 0) + 1
    return state


def spend_action(state, kind):
    state = normalize_state(state)
    economy = state["action_economy"]
    if kind == "action":
        if economy["action"] < 1: raise RuleError("Action already spent.")
        economy["action"] -= 1
    elif kind == "reaction":
        if economy["reaction"] < 1: raise RuleError("Reaction already spent.")
        economy["reaction"] -= 1
    elif kind == "movement":
        if economy["movement"] < 1: raise RuleError("Movement exhausted.")
    else:
        raise RuleError("Unknown action-economy unit.")
    return state


def movement_cost(dx, dy, terrain="NORMAL"):
    _int(dx, "dx"); _int(dy, "dy")
    if abs(dx) > 1 or abs(dy) > 1:
        raise RuleError("Movement path must enumerate adjacent cells.")
    if terrain not in {"NORMAL", "DIFICIL", "SEVERO", "INTRANSPONIVEL"}:
        raise RuleError("Unknown terrain.")
    if terrain == "INTRANSPONIVEL":
        raise RuleError("Impassable terrain.")
    base = 2 if abs(dx) and abs(dy) else 1
    return base * {"NORMAL": 1, "DIFICIL": 2, "SEVERO": 3}[terrain]


def run_movement(state, points, *, terrain="NORMAL", forced=False, teleport=False):
    state = normalize_state(state)
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise RuleError("A movement path requires at least two cells.")
    if not forced and not teleport and any(item.get("type") == "IMOBILIZADO" for item in state["conditions"]):
        raise RuleError("Movement blocked by IMOBILIZADO.")
    cost = sum(movement_cost(b[0] - a[0], b[1] - a[1], terrain) for a, b in zip(points, points[1:]))
    if teleport:
        cost = 0
    if not forced and not teleport:
        slow = any(item.get("type") == "LENTO" for item in state["conditions"])
        allowance = state["action_economy"].get("movement", 6) - (2 if slow else 0)
        if cost > allowance:
            raise RuleError("Movement exceeds the current allowance.")
        state["action_economy"]["movement"] = allowance - cost
    return {"cost": cost, "forced": forced, "teleport": teleport, "state": state}


def damage(*, base, power=0, margin_grade="success", fixed=0, body=0, protection=0, potent=False, true_damage=False, scale=1, minimum=1):
    _int(base, "base", 0); _int(power, "power", 0, 4); _int(fixed, "fixed"); _int(body, "body"); _int(protection, "protection", 0); _int(scale, "scale", 1)
    margin_bonus = {"success": 0, "success_strong": 2, "success_extraordinary": 4}.get(margin_grade, 0)
    raw = base * scale * POWER_MULTIPLIERS[power] + margin_bonus + fixed + (body if potent else 0)
    after = raw if true_damage else raw - protection
    return {"base": base, "power": power, "multiplier": POWER_MULTIPLIERS[power], "raw": raw, "protection": 0 if true_damage else protection, "final": max(minimum, after) if after > 0 else 0, "true_damage": true_damage}


def apply_damage(state, amount, *, protection=None, fortitude=None, damage_event="runtime", true_damage=False):
    state = normalize_state(state)
    _int(amount, "damage", 0); before = state["resources"]["vitality"]["current"]
    protection = state.get("protection", 0) if protection is None else _int(protection, "protection", 0)
    post = amount if true_damage else max(0, amount - protection)
    after = max(0, before - post)
    state["resources"]["vitality"]["current"] = after
    if after == 0: add_condition(state, "CAIDO", source=damage_event)
    excess = max(0, post - before)
    grave = fortitude is not None and excess >= fortitude
    return {"event_id": damage_event, "before": before, "after": after, "raw": amount, "post_protection": post, "excess": excess, "grave_wound_candidate": grave, "state": state}


def permanence(state, *, light=None, dark=None, random_source=None):
    state = normalize_state(state)
    attrs = state["attributes"]; skills = state.get("skills", {})
    roll = resolve_test(light=light, dark=dark, attribute=attrs.get("corpo", 0), skill=skills.get("atletismo", 0), difficulty=12) if light is not None else roll_test(attribute=attrs.get("corpo", 0), skill=skills.get("atletismo", 0), difficulty=12, random_source=random_source)
    combat = state["combat"]
    if roll["success"]: combat["permanence_successes"] = min(3, combat.get("permanence_successes", 0) + 1)
    else: combat["permanence_failures"] = min(3, combat.get("permanence_failures", 0) + 1)
    outcome = None
    if combat["permanence_successes"] >= 3:
        state["resources"]["vitality"]["current"] = 1; remove_condition(state, "CAIDO"); outcome = "STABILIZED"
    elif combat["permanence_failures"] >= 3:
        outcome = "TERMINAL"
    combat["outcome"] = outcome
    return {"roll": roll, "outcome": outcome, "state": state}


def lucidity_zero(state, choice):
    state = normalize_state(state)
    if state["resources"]["lucidity"]["current"] != 0:
        raise RuleError("Lucidity is not zero.")
    if choice not in {"fuga", "congelamento", "confissao", "isolamento", "pedido_de_ajuda", "cicatriz", "return_one"}:
        raise RuleError("Invalid Ruptura response.")
    if choice == "return_one": state["resources"]["lucidity"]["current"] = 1
    return {"choice": choice, "state": state}


def technique(*, marco, minimum_marco=1, action="action", cost=None, scene_key=None, used_keys=()):
    _int(marco, "marco", 0); _int(minimum_marco, "minimum_marco", 1, 15)
    if marco < minimum_marco: raise RuleError("Marco mínimo da Técnica não alcançado.")
    if action not in {"action", "reaction", "passive", "prepare", "scene"}: raise RuleError("Invalid technique action.")
    if scene_key and scene_key in set(used_keys): raise RuleError("Technique already used in this scene.")
    return {"legal": True, "action": action, "cost": cost, "scene_key": scene_key}


def magic(*, grade, marco, action="action", cost=None, concentration=False, current_concentration=None):
    _int(grade, "grade", 0, 7); _int(marco, "marco", 0, 15)
    if grade == 7: raise RuleError("G7 is cosmological and not playable.")
    minimum = {0: 1, 1: 1, 2: 3, 3: 5, 4: 11, 5: 13, 6: 15}[grade]
    if marco < minimum: raise RuleError("Marco does not grant this magic grade.")
    if concentration and current_concentration: raise RuleError("Only one persistent magic may be concentrated.")
    expected_cost = MAGIC_GRADE_COSTS[grade] if cost is None else _int(cost, "cost", 0)
    return {"grade": grade, "multiplier": MAGIC_GRADE_MULTIPLIERS[grade], "cost": expected_cost, "concentration": concentration}


def concentration_check(state, damage_taken, *, light=None, dark=None, random_source=None):
    if damage_taken < 5: return {"required": False, "maintained": True, "state": state}
    attrs = state["attributes"]; skills = state.get("skills", {})
    roll = resolve_test(light=light, dark=dark, attribute=attrs.get("vontade", 0), skill=skills.get("magia", 0), difficulty=15) if light is not None else roll_test(attribute=attrs.get("vontade", 0), skill=skills.get("magia", 0), difficulty=15, random_source=random_source)
    if not roll["success"]: state["concentration"] = None
    return {"required": True, "maintained": roll["success"], "roll": roll, "state": state}


def evocation(*, kind, tuning, evocation_skill, unstable=False, source=None, flow_available=0):
    profiles = {"minor": {"difficulty": 12, "cost": 1, "guard": 12, "vitality": 6, "damage": 3, "movement": 6}, "standard": {"difficulty": 15, "cost": 2, "guard": 14, "vitality": 14, "damage": 4, "movement": 6}, "major": {"difficulty": 18, "cost": 3, "guard": 16, "vitality": 24, "damage": 6, "movement": 8}}
    if kind not in profiles: raise RuleError("Unknown evocation size.")
    profile = deepcopy(profiles[kind]); profile["difficulty"] += 3 if unstable else 0; profile["cost"] += 1 if unstable else 0
    if flow_available < profile["cost"]: raise RuleError("Insufficient Flow for evocation.")
    roll = roll_test(attribute=tuning, skill=evocation_skill, difficulty=profile["difficulty"])
    return {"kind": kind, "profile": profile, "roll": roll, "source": source, "duration": "scene"}


def merge(*, mode, consent, tuning, skill, flow_each=1, flow_available=0, active=None, benefits=()):
    if mode not in {"shared_resonance", "voluntary_union", "forced", "corrupted"}: raise RuleError("Unknown Merge form.")
    if mode in {"shared_resonance", "voluntary_union"} and not consent: raise RuleError("Legitimate Merge requires consent.")
    if mode in {"forced", "corrupted"} and consent: raise RuleError("Forced or corrupted Merge cannot be marked consensual.")
    if active: raise RuleError("Merge is already active.")
    _int(flow_each, "flow_each", 1); _int(flow_available, "flow_available", 0)
    if flow_available < flow_each: raise RuleError("Insufficient Flow for Merge.")
    if not isinstance(benefits, (list, tuple)) or len(benefits) > 2: raise RuleError("Merge permits at most two benefits.")
    roll = roll_test(attribute=tuning, skill=skill, difficulty=15)
    return {"mode": mode, "consent": consent, "cost_each": flow_each, "benefits": list(benefits), "roll": roll, "active": True}


def coro_state(character_count, pulses=0, bars=0):
    maximum_bars = 1 if character_count <= 2 else 2 if character_count <= 4 else 3
    _int(pulses, "pulses", 0); _int(bars, "bars", 0, maximum_bars)
    if pulses > maximum_bars * 4: raise RuleError("Coro exceeds its maximum.")
    return {"pulses": pulses, "bars": pulses // 4, "maximum_bars": maximum_bars, "filled": pulses % 4}


def add_coro_pulse(state, *, eligible=True):
    state = normalize_state(state); coro = state["coro"]
    if not eligible: return {"added": False, "reason": "not_eligible", "state": state}
    max_pulses = coro.get("maximum_bars", 1) * 4
    if coro.get("pulses", 0) >= max_pulses: return {"added": False, "reason": "full", "state": state}
    coro["pulses"] = coro.get("pulses", 0) + 1; coro["bars"] = coro["pulses"] // 4
    return {"added": True, "state": state}


def spend_coro(state, role, level=1):
    state = normalize_state(state); _int(level, "level", 1, 3)
    if role not in {"vanguarda", "artilharia", "amparo", "bastiao"}: raise RuleError("Unknown Coro role.")
    if state["coro"].get("pulses", 0) < 4: raise RuleError("Coro requires a full bar.")
    if level > 3: raise RuleError("Coro level is I, II or III.")
    state["coro"]["pulses"] -= 4; state["coro"]["bars"] = state["coro"]["pulses"] // 4
    return {"role": role, "level": level, "state": state}


def change_shadow(state, delta, *, reason):
    state = normalize_state(state); before = state.get("sombra", 0)
    after = max(0, min(6, before + _int(delta, "shadow delta")))
    state["sombra"] = after
    return {"before": before, "after": after, "state": state, "reason": reason, "state_name": SHADOW_STATES[after]}


def fissure_traversal(*, state_name, contributions, has_destination=True, has_anchor=True, cost_accepted=True):
    if state_name not in FISSURE_DIFFICULTIES: raise RuleError("Unknown fissure state.")
    if not has_destination or not has_anchor: raise RuleError("Fissure requires a matching destination and valid anchor.")
    if not cost_accepted: raise RuleError("Fissure cost must be accepted before the first roll.")
    if not isinstance(contributions, list) or not contributions: raise RuleError("At least one fissure contribution is required.")
    successes = failures = 0; rolls = []
    for contribution in contributions:
        if successes >= 3 or failures >= 2: break
        roll = contribution if "success" in contribution else roll_test(attribute=contribution.get("attribute", 0), skill=contribution.get("skill", 0), difficulty=FISSURE_DIFFICULTIES[state_name])
        rolls.append(roll)
        if roll["success"]: successes += 1
        else: failures += 1
    return {"difficulty": FISSURE_DIFFICULTIES[state_name], "successes": successes, "failures": failures, "stable": successes >= 3 and failures < 2, "rolls": rolls}


def equipment_load(body, items):
    capacity = 6 + _int(body, "body")
    total = 0
    for item in items:
        total += 1 if item.get("light") else item.get("spaces", 1)
    return {"capacity": capacity, "used": total, "pressure": total > capacity}


def artifact_use(state, artifact_id, *, frequency="scene", use_key=None):
    state = normalize_state(state); uses = state.setdefault(f"{frequency}_uses", {})
    key = use_key or artifact_id
    if uses.get(key): raise RuleError("Artifact frequency already used.")
    uses[key] = True
    return {"artifact": artifact_id, "frequency": frequency, "state": state}


def fulgor_gain(state, amount=1):
    state = normalize_state(state); before = _int(state.get("fulgor", 0), "fulgor", 0, 5)
    after = before + _int(amount, "fulgor amount", 0)
    full = after >= 5
    state["fulgor"] = 0 if full else after
    return {"before": before, "after": state["fulgor"], "fulgor_pleno": full, "state": state}


def progression_contract(marco):
    _int(marco, "marco", 1, 16)
    if marco == 16: return {"marco": 16, "playable": False, "history_only": True}
    return {"marco": marco, "playable": True, **deepcopy(PROGRESSION[marco])}
