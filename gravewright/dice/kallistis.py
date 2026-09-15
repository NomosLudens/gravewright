"""KALLISTIS core resolution on top of the native server-side dice pipeline."""

from .engine import RollError
from .grammar.runtime import secure_sample


MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 1000
MIN_MODIFIER = -1000
MAX_MODIFIER = 1000


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


def _die(random_source):
    sample = random_source()
    if type(sample) not in (int, float) or not 0 <= sample < 1:
        raise RollError("Random source must return a finite value in [0, 1).")
    return int(sample * 10) + 1


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
        "light_principle": light["key"],
        "light_principle_label": light["label"],
        "light_reading": _reading(light),
        "dark_die": dark_die,
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
