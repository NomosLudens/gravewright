"""KALLISTIS core resolution on top of the native server-side dice pipeline."""

from .engine import RollError
from .grammar.runtime import secure_sample


MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 1000
MIN_MODIFIER = -1000
MAX_MODIFIER = 1000

ACTION_VALUE_MIN = -1000
ACTION_VALUE_MAX = 1000
ACTION_LABEL_MAX = 80
SKILL_LABEL_MAX = 80
REASON_MAX = 200

ATTRIBUTES = {
    "corpo": "Corpo",
    "agilidade": "Agilidade",
    "intelecto": "Intelecto",
    "presenca": "Presença",
    "vontade": "Vontade",
    "sintonia": "Sintonia",
}

DIFFICULTY_PRESETS = {
    10: "baixa",
    12: "favorável",
    15: "incerta",
    18: "difícil",
    21: "severa",
    24: "extrema",
    27: "lendária",
    30: "épica",
}


LIGHT_PRINCIPLES = {
    1: {
        "key": "centelha",
        "label": "Centelha",
        "success": "o efeito começa, ainda que pequeno ou incompleto",
        "failure": "a tentativa revela intenção, esforço ou hesitação",
    },
    2: {
        "key": "vestigio",
        "label": "Vestígio",
        "success": "a ação deixa pista, marca ou evidência útil",
        "failure": "você deixa rastros, provas ou sinais indesejados",
    },
    3: {
        "key": "forma",
        "label": "Forma",
        "success": "algo ganha contorno, função, posição ou definição",
        "failure": "a forma criada é instável, inadequada ou limitada",
    },
    4: {
        "key": "movimento",
        "label": "Movimento",
        "success": "alguém ou algo muda de posição, ritmo ou direção",
        "failure": "o movimento cria posição desfavorável",
    },
    5: {
        "key": "exposicao",
        "label": "Exposição",
        "success": "alvo, fraqueza, mentira ou passagem fica visível",
        "failure": "você, aliado ou recurso fica exposto",
    },
    6: {
        "key": "abertura",
        "label": "Abertura",
        "success": "surge oportunidade imediata",
        "failure": "a oposição recebe abertura ou iniciativa",
    },
    7: {
        "key": "impacto",
        "label": "Impacto",
        "success": "algo é interrompido, quebrado, deslocado ou forçado",
        "failure": "há recuo, dano colateral ou reação",
    },
    8: {
        "key": "testemunho",
        "label": "Testemunho",
        "success": "a ação é reconhecida, vista ou registrada",
        "failure": "a cena atrai autoridade, testemunhas ou julgamento",
    },
    9: {
        "key": "transformacao",
        "label": "Transformação",
        "success": "ambiente ou situação sofre mudança duradoura",
        "failure": "alteração permanente ocorre de modo indesejado",
    },
    10: {
        "key": "manifestacao_plena",
        "label": "Manifestação plena",
        "success": "o efeito se torna incontestável e domina a cena",
        "failure": "a consequência aparece imediatamente e não pode ser ocultada",
    },
}

DARK_PRINCIPLES = {
    1: {
        "key": "sussurro",
        "label": "Sussurro",
        "success": "intuição ou sinal quase imperceptível aparece",
        "failure": "algo importante permanece ambíguo",
    },
    2: {
        "key": "eco",
        "label": "Eco",
        "success": "detalhe do passado ou de outra cena retorna",
        "failure": "eco falso, incompleto ou perturbador interfere",
    },
    3: {
        "key": "contexto",
        "label": "Contexto",
        "success": "surge conexão com história, lugar ou instituição",
        "failure": "falta uma peça e cresce o risco de interpretação errada",
    },
    4: {
        "key": "caminho",
        "label": "Caminho",
        "success": "aparece rota alternativa ou solução indireta",
        "failure": "a única rota exige custo, atraso ou desvio",
    },
    5: {
        "key": "vinculo",
        "label": "Vínculo",
        "success": "relação é fortalecida, compreendida ou transformada",
        "failure": "surge tensão, dívida, dependência ou distância",
    },
    6: {
        "key": "segredo",
        "label": "Segredo",
        "success": "algo oculto se torna acessível",
        "failure": "o segredo é parcial, perigoso ou também percebe você",
    },
    7: {
        "key": "memoria",
        "label": "Memória",
        "success": "o passado retorna de forma útil e atuante",
        "failure": "lembrança dolorosa, distorcida ou indesejada emerge",
    },
    8: {
        "key": "possibilidade",
        "label": "Possibilidade",
        "success": "nova opção futura se torna real",
        "failure": "oportunidade surge para a oposição ou cobra preço",
    },
    9: {
        "key": "profundidade",
        "label": "Profundidade",
        "success": "causa verdadeira, estrutura ou identidade é revelada",
        "failure": "a revelação desestabiliza crenças, vínculos ou segurança",
    },
    10: {
        "key": "origem",
        "label": "Origem",
        "success": "a ação toca a raiz de relação, fenômeno ou verdade",
        "failure": "dívida profunda, eco ou consequência duradoura desperta",
    },
}

PREDOMINANCE_INTENSITIES = {
    0: {"key": "resonance", "label": "Ressonância"},
    1: {"key": "subtle", "label": "Sutil"},
    2: {"key": "subtle", "label": "Sutil"},
    3: {"key": "clear", "label": "Clara"},
    4: {"key": "clear", "label": "Clara"},
    5: {"key": "clear", "label": "Clara"},
    6: {"key": "intense", "label": "Intensa"},
    7: {"key": "intense", "label": "Intensa"},
    8: {"key": "intense", "label": "Intensa"},
    9: {"key": "absolute", "label": "Absoluta"},
}

RESONANCES = {
    1: {"name": "Ressonância Frágil", "opening": "algo pequeno sobrevive, começa ou recusa desaparecer"},
    2: {"name": "Ressonância do Eco", "opening": "pista, som, memória ou padrão retorna"},
    3: {"name": "Ressonância da Forma", "opening": "algo recebe estrutura estável ou significado definido"},
    4: {"name": "Ressonância da Passagem", "opening": "rota, deslocamento ou transição torna-se possível"},
    5: {"name": "Ressonância do Espelho", "opening": "relação, correspondência ou identidade é revelada"},
    6: {"name": "Ressonância do Acorde", "opening": "aliados, forças ou intenções entram em coordenação"},
    7: {"name": "Ressonância da Fratura", "opening": "defesa, mentira, barreira ou padrão é rompido"},
    8: {"name": "Ressonância do Vínculo", "opening": "relação é restaurada, transformada ou posta à prova"},
    9: {"name": "Ressonância da Convergência", "opening": "várias contribuições produzem mudança coletiva"},
    10: {"name": "Ressonância Plena", "opening": "Luz e Escuridão alteram a cena em escala excepcional"},
}


def _reading(principle):
    return {
        "label": principle["label"],
        "success": principle["success"],
        "failure": principle["failure"],
    }


def _validate(modifier, difficulty):
    if type(modifier) is not int or not MIN_MODIFIER <= modifier <= MAX_MODIFIER:
        raise RollError("KALLISTIS modifier must be an integer between -1000 and 1000.")
    if type(difficulty) is not int or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        raise RollError("KALLISTIS difficulty must be an integer between 1 and 1000.")


def _text(value, field, maximum, *, required=True):
    if not isinstance(value, str):
        raise RollError(f"{field} must be text.")
    value = value.strip()
    if required and not value:
        raise RollError(f"{field} is required.")
    if len(value) > maximum:
        raise RollError(f"{field} must contain at most {maximum} characters.")
    return value


def _integer(value, field):
    if type(value) is not int or not ACTION_VALUE_MIN <= value <= ACTION_VALUE_MAX:
        raise RollError(f"{field} must be an integer between {ACTION_VALUE_MIN} and {ACTION_VALUE_MAX}.")
    return value


def prepare_action(action):
    """Validate an action input and calculate every derived modifier server-side.

    This is deliberately a value object: no character, inventory or party
    schema is implied by an action roll in this gate.
    """
    if not isinstance(action, dict):
        raise RollError("KALLISTIS action data is required.")

    def value(*names, default=None):
        for name in names:
            if name in action:
                return action[name]
        return default

    action_label = _text(value("action_label", "actionLabel", "label"), "action_label", ACTION_LABEL_MAX)

    attribute = value("attribute", default=None)
    if attribute is None:
        attribute = {"name": value("attribute_name", "attributeName"),
                     "value": value("attribute_value", "attributeValue")}
    if not isinstance(attribute, dict):
        raise RollError("attribute must be an object.")
    attribute_name = value_from(attribute, "name", "attribute_name", "attributeName")
    attribute_name = _text(attribute_name, "attribute_name", 24).lower()
    if attribute_name not in ATTRIBUTES:
        raise RollError("attribute_name must be one of Corpo, Agilidade, Intelecto, Presença, Vontade or Sintonia.")
    attribute_value = _integer(value_from(attribute, "value", "attribute_value", "attributeValue"), "attribute_value")

    skill = value("skill", default=None)
    if skill is None:
        skill = {"name": value("skill_name", "skillName"),
                 "value": value("skill_value", "skillValue")}
    if not isinstance(skill, dict):
        raise RollError("skill must be an object.")
    skill_name = _text(value_from(skill, "name", "skill_name", "skillName"), "skill_name", SKILL_LABEL_MAX)
    skill_value = _integer(value_from(skill, "value", "skill_value", "skillValue"), "skill_value")

    impulse = value("impulse", default=None)
    pressure = value("pressure", default=None)
    if impulse is None:
        impulse = {"level": value("impulse_level", "impulseLevel", default=0),
                   "reason": value("impulse_reason", "impulseReason", default="")}
    if pressure is None:
        pressure = {"level": value("pressure_level", "pressureLevel", default=0),
                    "reason": value("pressure_reason", "pressureReason", default="")}
    if not isinstance(impulse, dict) or not isinstance(pressure, dict):
        raise RollError("impulse and pressure must be objects.")
    impulse_level = _level(value_from(impulse, "level", "impulse_level", "impulseLevel", default=0), "impulse_level")
    pressure_level = _level(value_from(pressure, "level", "pressure_level", "pressureLevel", default=0), "pressure_level")
    impulse_reason = _text(value_from(impulse, "reason", "impulse_reason", "impulseReason", default=""), "impulse_reason", REASON_MAX, required=False)
    pressure_reason = _text(value_from(pressure, "reason", "pressure_reason", "pressureReason", default=""), "pressure_reason", REASON_MAX, required=False)

    helpers = value("helpers", default=None)
    helper_count = value("helper_count", "helperCount", default=None)
    if helpers is not None and not isinstance(helpers, list):
        raise RollError("helpers must be a list.")
    if helpers is not None and len(helpers) > 2:
        raise RollError("A KALLISTIS action accepts at most 2 helpers.")
    if helper_count is not None and (type(helper_count) is not int or not 0 <= helper_count <= 2):
        raise RollError("helper_count must be 0, 1 or 2.")
    if helpers is None:
        helpers = [{"label": "", "reason": ""} for _ in range(helper_count or 0)]
    elif helper_count is not None and helper_count != len(helpers):
        raise RollError("helper_count must match helpers.")
    normalized_helpers = []
    for helper in helpers:
        if not isinstance(helper, dict):
            raise RollError("Each helper must be an object.")
        normalized_helpers.append({
            "label": _text(helper.get("label", ""), "helper.label", ACTION_LABEL_MAX, required=False),
            "reason": _text(helper.get("reason", ""), "helper.reason", REASON_MAX, required=False),
        })
    helper_count = len(normalized_helpers)
    corruption_applies = value("corruption_applies", "corruptionApplies", default=False)
    if type(corruption_applies) is not bool:
        raise RollError("corruption_applies must be boolean.")

    impulse_base_bonus = impulse_level * 2
    helper_bonus = helper_count * 2
    impulse_bonus = min(4, impulse_base_bonus + helper_bonus)
    pressure_penalty = -(pressure_level * 2)
    base_modifier = attribute_value + skill_value
    circumstance_modifier = impulse_bonus + pressure_penalty
    modifier_total = base_modifier + circumstance_modifier
    if not MIN_MODIFIER <= modifier_total <= MAX_MODIFIER:
        raise RollError("The calculated KALLISTIS modifier must be between -1000 and 1000.")

    return {
        "action_label": action_label,
        "attribute": {"name": attribute_name, "label": ATTRIBUTES[attribute_name], "value": attribute_value},
        "skill": {"name": skill_name, "value": skill_value},
        "impulse": {"level": impulse_level, "base_bonus": impulse_base_bonus,
                    "bonus": impulse_bonus, "reason": impulse_reason},
        "pressure": {"level": pressure_level, "penalty": pressure_penalty,
                     "reason": pressure_reason},
        "helpers": normalized_helpers,
        "helper_count": helper_count,
        "helper_bonus": helper_bonus,
        "corruption_applies": corruption_applies,
        "base_modifier": base_modifier,
        "circumstance_modifier": circumstance_modifier,
        "modifier_total": modifier_total,
    }


def value_from(mapping, *names, default=None):
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def _level(value, field):
    if type(value) is not int or not 0 <= value <= 2:
        raise RollError(f"{field} must be 0, 1 or 2.")
    return value


def _die(random_source):
    sample = random_source()
    if type(sample) not in (int, float) or not 0 <= sample < 1:
        raise RollError("Random source must return a finite value in [0, 1).")
    return int(sample * 10) + 1


def _face(die, value):
    """Describe the visual face without changing the die's numeric value."""
    glyph = None
    if die == "light":
        glyph = "light" if value == 10 else "dark" if value == 1 else None
    else:
        glyph = "dark" if value == 10 else "light" if value == 1 else None
    return {
        "value": value,
        "kind": "glyph" if glyph else "number",
        "glyph": glyph,
    }


def _degree(margin):
    if margin <= -5:
        return "failure_severe"
    if margin < 0:
        return "failure"
    if margin <= 4:
        return "success"
    if margin <= 9:
        return "success_strong"
    return "success_extraordinary"


def _one(modifier, difficulty, random_source):
    light_die = _die(random_source)
    dark_die = _die(random_source)
    light_face = _face("light", light_die)
    dark_face = _face("dark", dark_die)
    natural_total = light_die + dark_die
    total = natural_total + modifier
    margin = total - difficulty
    resonance = light_die == dark_die
    delta = abs(light_die - dark_die)
    light = LIGHT_PRINCIPLES[light_die]
    dark = DARK_PRINCIPLES[dark_die]
    intensity = PREDOMINANCE_INTENSITIES[delta]
    resonance_data = RESONANCES[light_die] if resonance else None
    degree = _degree(margin)
    return {
        "system": "kallistis",
        "version": 2,
        "light_die": light_die,
        "light_face": light_face,
        "light_principle": light["key"],
        "light_principle_label": light["label"],
        "light_reading": _reading(light),
        "dark_die": dark_die,
        "dark_face": dark_face,
        "dark_principle": dark["key"],
        "dark_principle_label": dark["label"],
        "dark_reading": _reading(dark),
        "natural_total": natural_total,
        "modifier": modifier,
        "total": total,
        "difficulty": difficulty,
        "margin": margin,
        "success": total >= difficulty,
        "degree": degree,
        "grade": degree,
        "predominance": "resonance" if resonance else "light" if light_die > dark_die else "dark",
        "predominance_delta": delta,
        "predominance_intensity": intensity["key"],
        "predominance_intensity_label": intensity["label"],
        "resonance": resonance,
        "critical": resonance,
        "critical_type": "resonance" if resonance else None,
        "resonance_value": light_die if resonance else None,
        "resonance_name": resonance_data["name"] if resonance_data else None,
        "resonance_opening": resonance_data["opening"] if resonance_data else None,
    }


def evaluate(modifier=0, difficulty=15, *, repeat=1, random_source=None):
    """Evaluate one or more authoritative KALLISTIS 2d10 tests.

    The two natural d10 values remain separate. Equality is Ressonância; it
    does not trigger another random draw.
    """
    _validate(modifier, difficulty)
    if type(repeat) is not int or not 1 <= repeat <= 12:
        raise RollError("Choose between 1 and 12 independent rolls.")
    source = random_source if random_source is not None else secure_sample
    results = [_one(modifier, difficulty, source) for _ in range(repeat)]
    return results[0] if repeat == 1 else results
