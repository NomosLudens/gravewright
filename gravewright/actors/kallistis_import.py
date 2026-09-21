"""Validated, transactional import of a KALLISTIS runtime character snapshot."""

from copy import deepcopy
import json
import math
import re

from django.db import transaction

from gravewright.campaigns.models import Campaign, Membership
from gravewright.pdf_system.schema import defaults, normalize

from .models import Actor, KallistisCharacterLink


MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_DEPTH = 12
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|hash|secret|token|authorization|cookie|api[_-]?key|"
    r"service[_-]?role|hmac|jwt|access[_-]?token|refresh[_-]?token)",
    re.IGNORECASE,
)
TOP_LEVEL_KEYS = {
    "schema",
    "schema_version",
    "exported_at",
    "export_mode",
    "source_state",
    "canonical",
    "mesa",
    "player",
    "character",
}
CHARACTER_KEYS = {
    "kallistis_character_id",
    "name",
    "published_version",
    "snapshot",
}
PLAYER_KEYS = {"kallistis_user_id", "display_name", "email"}
MESA_KEYS = {"id", "name"}


class KallistisImportError(Exception):
    def __init__(self, code, message=None, status=400):
        self.code = code
        self.status = status
        super().__init__(message or code)


def _string(value, field, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KallistisImportError("invalid_export", f"Invalid {field}.")
    return value.strip()


def _optional_string(value, field, maximum):
    if value is not None and (not isinstance(value, str) or len(value) > maximum):
        raise KallistisImportError("invalid_export", f"Invalid {field}.")
    return value.strip() if isinstance(value, str) else None


def _walk(value, path="snapshot", depth=0):
    if depth > MAX_IMPORT_DEPTH:
        raise KallistisImportError("invalid_snapshot", f"Snapshot too deep at {path}.")
    if isinstance(value, dict):
        if len(value) > 128:
            raise KallistisImportError("invalid_snapshot", f"Too many fields at {path}.")
        for key, child in value.items():
            if (
                not isinstance(key, str)
                or len(key) > 120
                or key in {"__proto__", "constructor", "prototype"}
            ):
                raise KallistisImportError("invalid_snapshot", f"Invalid field at {path}.")
            if SENSITIVE_KEY.search(key):
                raise KallistisImportError("sensitive_field", f"Sensitive field at {path}.{key}.")
            _walk(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        if len(value) > 512:
            raise KallistisImportError("invalid_snapshot", f"Too many entries at {path}.")
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, str):
        if len(value) > 50_000:
            raise KallistisImportError("invalid_snapshot", f"String too long at {path}.")
    elif isinstance(value, float) and not math.isfinite(value):
        raise KallistisImportError("invalid_snapshot", f"Invalid number at {path}.")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise KallistisImportError("invalid_snapshot", f"Invalid value at {path}.")


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) - TOP_LEVEL_KEYS:
        raise KallistisImportError("invalid_schema")
    if payload.get("schema") != "kallistis.gravewright.character":
        raise KallistisImportError("invalid_schema")
    if payload.get("schema_version") != 1:
        raise KallistisImportError("unsupported_schema_version")
    if payload.get("export_mode") != "manual_runtime_snapshot":
        raise KallistisImportError("invalid_export_mode")
    if type(payload.get("canonical")) is not bool:
        raise KallistisImportError("invalid_export")
    source_state = _string(payload.get("source_state"), "source_state", 32)
    mesa = payload.get("mesa")
    if mesa is not None:
        if not isinstance(mesa, dict) or set(mesa) != MESA_KEYS:
            raise KallistisImportError("invalid_export")
        _string(mesa.get("id"), "mesa.id", 128)
        _string(mesa.get("name"), "mesa.name", 120)
    player = payload.get("player")
    if not isinstance(player, dict) or set(player) - PLAYER_KEYS:
        raise KallistisImportError("invalid_export")
    _optional_string(player.get("kallistis_user_id"), "player.kallistis_user_id", 128)
    _optional_string(player.get("display_name"), "player.display_name", 120)
    _optional_string(player.get("email"), "player.email", 320)
    character = payload.get("character")
    if not isinstance(character, dict) or set(character) - CHARACTER_KEYS:
        raise KallistisImportError("invalid_export")
    character_id = _string(
        character.get("kallistis_character_id"), "kallistis_character_id", 128
    )
    name = _string(character.get("name"), "character.name", 120)
    if "published_version" in character and character["published_version"] is not None:
        if (
            type(character["published_version"]) is not int
            or character["published_version"] < 1
        ):
            raise KallistisImportError("invalid_export")
    snapshot = character.get("snapshot")
    if not isinstance(snapshot, dict):
        raise KallistisImportError("invalid_snapshot")
    _walk(snapshot)
    if not isinstance(snapshot.get("nome"), str) or not snapshot["nome"].strip():
        raise KallistisImportError("invalid_snapshot")
    if not isinstance(snapshot.get("trilhas"), list) or not snapshot["trilhas"]:
        raise KallistisImportError("invalid_snapshot")
    if not isinstance(snapshot.get("atributosBase"), dict):
        raise KallistisImportError("invalid_snapshot")
    return {
        "source_state": source_state,
        "canonical": payload["canonical"],
        "character_id": character_id,
        "name": name,
        "snapshot": snapshot,
        "payload": payload,
    }


def parse_uploaded_json(raw):
    if len(raw) > MAX_IMPORT_BYTES:
        raise KallistisImportError("request_too_large", status=413)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise KallistisImportError("invalid_json") from None
    return validate_payload(payload)


def preview(parsed):
    snapshot = parsed["snapshot"]
    imported = ["name", "source_state", "canonical", "attributes", "runtime"]
    preserved = sorted(
        key for key in snapshot if key not in {"nome", "atributosBase", "trilhas"}
    )
    return {
        "schema": "kallistis.gravewright.character",
        "schema_version": 1,
        "export_mode": "manual_runtime_snapshot",
        "source_state": parsed["source_state"],
        "canonical": parsed["canonical"],
        "mesa": parsed["payload"].get("mesa"),
        "player": {
            "display_name": parsed["payload"].get("player", {}).get("display_name"),
            "email_present": bool(parsed["payload"].get("player", {}).get("email")),
        },
        "kallistis_character_id": parsed["character_id"],
        "character_name": parsed["name"],
        "mapping": {
            "imported": imported,
            "preserved_as_source_metadata": preserved,
            "unsupported": [],
        },
    }


def _number(value, fallback=0):
    return value if type(value) in (int, float) and math.isfinite(value) else fallback


def actor_data(parsed):
    snapshot = deepcopy(parsed["snapshot"])
    attributes = snapshot.get("atributosBase", {})
    tracks = snapshot.get("trilhas", [])
    active = snapshot.get("trilhaAtiva", 0)
    active_track = (
        tracks[active]
        if type(active) is int
        and 0 <= active < len(tracks)
        and isinstance(tracks[active], dict)
        else {}
    )
    raw = {
        "fields": {
            "kallistis_source_snapshot": snapshot,
            "kallistis_source_state": parsed["source_state"],
            "kallistis_canonical": parsed["canonical"],
        },
        "bio": snapshot.get("descricao", "")
        if isinstance(snapshot.get("descricao", ""), str)
        else "",
        "history": snapshot.get("biografia", "")
        if isinstance(snapshot.get("biografia", ""), str)
        else "",
        "notes": snapshot.get("notasNarrativasPublicas", "")
        if isinstance(snapshot.get("notasNarrativasPublicas", ""), str)
        else "",
        "token": {"name": parsed["name"]},
    }
    data = normalize(raw)
    data["runtime"] = {
        **defaults()["runtime"],
        "attributes": {
            "corpo": _number(attributes.get("Corpo")),
            "agilidade": _number(attributes.get("Agilidade")),
            "intelecto": _number(attributes.get("Intelecto")),
            "presenca": _number(attributes.get("Presença")),
            "vontade": _number(attributes.get("Vontade")),
            "sintonia": _number(attributes.get("Sintonia")),
            "marco": _number(active_track.get("marco")),
        },
    }
    return data


def options_for_user(user_id):
    campaigns = (
        Campaign.objects.filter(
            memberships__user_id=user_id, memberships__role=Membership.Role.GM
        )
        .distinct()
        .prefetch_related("memberships__user")
        .order_by("name", "id")
    )
    return [
        {
            "id": str(campaign.pk),
            "name": campaign.name,
            "memberships": [
                {
                    "id": str(member.pk),
                    "name": member.user.name,
                    "user_id": str(member.user_id),
                }
                for member in campaign.memberships.all()
                if member.role == Membership.Role.PLAYER and member.user.is_active
            ],
        }
        for campaign in campaigns
    ]


@transaction.atomic
def import_character(user_id, campaign_id, membership_id, payload):
    parsed = validate_payload(payload)
    campaign = Campaign.objects.select_for_update().filter(pk=campaign_id).first()
    if campaign is None:
        raise KallistisImportError("campaign_not_found", status=404)
    gm = Membership.objects.select_for_update().filter(
        campaign=campaign,
        user_id=user_id,
        role=Membership.Role.GM,
        user__is_active=True,
    ).first()
    if gm is None:
        raise KallistisImportError("unauthorized", status=403)
    player = (
        Membership.objects.select_for_update()
        .filter(
            pk=membership_id,
            campaign=campaign,
            role=Membership.Role.PLAYER,
            user__is_active=True,
        )
        .select_related("user")
        .first()
    )
    if player is None:
        raise KallistisImportError("player_not_in_campaign", status=403)
    existing = (
        KallistisCharacterLink.objects.select_related("actor")
        .filter(kallistis_character_id=parsed["character_id"])
        .first()
    )
    if existing is not None:
        raise KallistisImportError("already_imported", status=409)
    actor = Actor.objects.create(
        campaign=campaign,
        name=parsed["name"],
        type="character",
        data=actor_data(parsed),
        permissions={str(player.user_id): "owner"},
    )
    KallistisCharacterLink.objects.create(
        kallistis_character_id=parsed["character_id"],
        actor=actor,
        source_schema_version=1,
        source_state=parsed["source_state"],
        canonical=parsed["canonical"],
    )
    return {
        "actor_id": str(actor.pk),
        "kallistis_character_id": parsed["character_id"],
        "player_id": str(player.user_id),
        "player_name": player.user.name,
        "campaign_id": str(campaign.pk),
    }
