"""Provision the 25 KALLISTIS player phrase credentials from a private manifest."""

import json
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.exceptions import ValidationError

from gravewright.accounts.models import KallistisPlayerAccess, User
from gravewright.accounts.services import kallistis_phrase_digest, normalize_kallistis_phrase
from gravewright.campaigns.models import Campaign, Membership


EXPECTED_CODES = tuple(f"JOGADOR-{index:02d}" for index in range(1, 26))
MANIFEST_MAX_BYTES = 64 * 1024


def read_manifest(path):
    manifest_path = Path(path).expanduser()
    try:
        raw = manifest_path.read_bytes()
    except OSError as error:
        raise CommandError(f"Could not read manifest: {error}") from error
    if len(raw) > MANIFEST_MAX_BYTES:
        raise CommandError("Manifest is too large.")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise CommandError("Manifest is not valid UTF-8 JSON.") from error
    if not isinstance(document, dict) or set(document) != {"players"}:
        raise CommandError("Manifest must contain only a players array.")
    players = document["players"]
    if not isinstance(players, list) or len(players) != len(EXPECTED_CODES):
        raise CommandError("Manifest must contain exactly 25 players.")

    parsed = []
    seen_codes = set()
    seen_digests = set()
    for item in players:
        if not isinstance(item, dict) or set(item) - {"player_code", "phrase", "display_name"}:
            raise CommandError("Each player entry has an invalid shape.")
        code = item.get("player_code")
        phrase = normalize_kallistis_phrase(item.get("phrase"))
        display_name = item.get("display_name", code)
        if code not in EXPECTED_CODES or code in seen_codes:
            raise CommandError("Player codes must be the unique JOGADOR-01..25 set.")
        if phrase is None:
            raise CommandError(f"Invalid phrase for {code}.")
        if not isinstance(display_name, str) or not 2 <= len(display_name.strip()) <= 80:
            raise CommandError(f"Invalid display name for {code}.")
        digest = kallistis_phrase_digest(phrase)
        if digest in seen_digests:
            raise CommandError("Player phrases must be unique.")
        seen_codes.add(code)
        seen_digests.add(digest)
        parsed.append({
            "player_code": code,
            "phrase": phrase,
            "digest": digest,
            "display_name": display_name.strip(),
        })
    if tuple(sorted(seen_codes)) != EXPECTED_CODES:
        raise CommandError("Manifest must cover every player code from JOGADOR-01 to JOGADOR-25.")
    return parsed


class Command(BaseCommand):
    help = "Provision KALLISTIS player phrase access from a private, non-repository manifest."

    def add_arguments(self, parser):
        parser.add_argument("manifest", type=Path)
        parser.add_argument("--campaign-id", required=False)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        players = read_manifest(options["manifest"])
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("DRY_RUN=YES PLAYERS=25"))
            return
        campaign_id = options.get("campaign_id")
        if not campaign_id:
            raise CommandError("--campaign-id is required for live provisioning.")
        try:
            campaign = Campaign.objects.get(pk=campaign_id)
        except (Campaign.DoesNotExist, ValidationError, ValueError) as error:
            raise CommandError("Campaign was not found.") from error

        for player in players:
            email = f"kallistis-{player['player_code'].lower()}@shadow.gravewright.invalid"
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User(
                    name=player["display_name"],
                    email=email,
                    role=User.Role.PARTICIPANT,
                    is_active=True,
                )
                user.set_unusable_password()
                user.save(force_insert=True)
            elif user.role != User.Role.PARTICIPANT:
                raise CommandError(f"Existing user for {player['player_code']} is not a participant.")
            elif user.name != player["display_name"] or not user.is_active:
                user.name = player["display_name"]
                user.is_active = True
                user.save(update_fields=["name", "is_active"])

            access, _ = KallistisPlayerAccess.objects.select_for_update().get_or_create(
                player_code=player["player_code"],
                defaults={
                    "user": user,
                    "phrase_lookup_digest": player["digest"],
                    "phrase_hash": make_password(player["phrase"]),
                },
            )
            if access.user_id != user.pk:
                raise CommandError(f"Player code {player['player_code']} is already bound to another user.")
            access.phrase_lookup_digest = player["digest"]
            access.phrase_hash = make_password(player["phrase"])
            access.revoked_at = None
            access.save(update_fields=["phrase_lookup_digest", "phrase_hash", "revoked_at", "updated_at"])
            Membership.objects.update_or_create(
                campaign=campaign,
                user=user,
                defaults={"role": Membership.Role.PLAYER},
            )

        self.stdout.write(self.style.SUCCESS("PROVISIONED_PLAYERS=25"))
