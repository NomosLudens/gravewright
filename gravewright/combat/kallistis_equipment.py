"""KALLISTIS v1.3 weapon damage facts used by the existing rules runtime.

Names, damage bases and tags are transcribed from KALLISTIS_REGRAS_FREEZE_V1.3,
Part IV, sections 82-83. This is a small source catalog; damage resolution stays
in gravewright.rules.kallistis_runtime.
"""

WEAPONS = {
    "Desarmado": {"base": 2, "tags": ("leve", "não letal")},
    "Arma improvisada": {"base": 3, "tags": ("precária",)},
    "Faca": {"base": 3, "tags": ("leve", "ocultável")},
    "Clava": {"base": 4, "tags": ("impacto",)},
    "Bastão": {"base": 3, "tags": ("duas mãos", "foco")},
    "Lança curta": {"base": 4, "tags": ("alcance", "arremesso")},
    "Espada": {"base": 5, "tags": ("equilibrada",)},
    "Sabre": {"base": 5, "tags": ("leve", "equilibrada")},
    "Machado": {"base": 6, "tags": ("potente",)},
    "Martelo de guerra": {"base": 6, "tags": ("impacto", "pesado")},
    "Lança longa": {"base": 5, "tags": ("alcance", "duas mãos")},
    "Lâmina grande": {"base": 7, "tags": ("potente", "pesada", "duas mãos")},
    "Arma de haste": {"base": 6, "tags": ("alcance", "pesada", "duas mãos")},
    "Funda": {"base": 3, "tags": ("leve", "munição")},
    "Arma de arremesso": {"base": 4, "tags": ("arremesso", "leve")},
    "Arco": {"base": 5, "tags": ("duas mãos", "munição")},
    "Besta": {"base": 6, "tags": ("recarga", "duas mãos")},
    "Besta pesada": {"base": 7, "tags": ("recarga", "pesada", "perfurante", "duas mãos")},
    "Arma de disparo": {"base": 6, "tags": ("ruidosa", "munição")},
    "Repetidor Nomos": {"base": 5, "tags": ("rajada", "munição", "modular")},
    "Projetor de quartzo": {"base": 6, "tags": ("mágico", "foco", "duas mãos")},
    "Bastão ritual": {"base": 3, "tags": ("foco",)},
    "Lâmina ressonante": {"base": 5, "tags": ("mágico", "equilibrada")},
    "Luva de inscrição": {"base": 4, "tags": ("mágico", "modular", "foco")},
}


def equipped_weapon(actor):
    """Resolve weapon facts only from an approved linked KALLISTIS sheet."""
    from gravewright.actors.models import KallistisCharacterLink

    if not KallistisCharacterLink.objects.filter(
        actor=actor, canonical=True, source_state="approved"
    ).exists():
        return None
    fields = actor.data.get("fields", {}) if isinstance(actor.data, dict) else {}
    snapshot = fields.get("kallistis_source_snapshot", {}) if isinstance(fields, dict) else {}
    equipment = snapshot.get("equipamento", {}) if isinstance(snapshot, dict) else {}
    name = equipment.get("arma") if isinstance(equipment, dict) else None
    item = WEAPONS.get(name)
    if not item or equipment.get("proficienciaConfirmada") is not True:
        return None
    return {"name": name, **item}
