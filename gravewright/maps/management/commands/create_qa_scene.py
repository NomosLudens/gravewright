"""Create the one explicitly scoped KALLISTIS QA map using the shared map pipeline."""

import hashlib
import math
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, UnidentifiedImageError
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import JournalError, member
from gravewright.maps import services
from gravewright.maps.models import Broadcast, Scene, Tile
from gravewright.maps.views import notify

QA_CAMPAIGN_NAME = "QA Jornada Contínua 20261007"
QA_SCENE_NAME = "Arena QA KALLISTIS"


class Command(BaseCommand):
    help = "Create or verify the KALLISTIS QA scene from an explicitly checksummed PNG."

    def add_arguments(self, parser):
        parser.add_argument("--campaign-id", required=True)
        parser.add_argument("--png-path", type=Path, required=True)
        parser.add_argument("--sha256", required=True)
        parser.add_argument("--operator-id", required=True)

    def handle(self, *args, **options):
        try:
            campaign = Campaign.objects.get(pk=options["campaign_id"])
        except (Campaign.DoesNotExist, ValueError, TypeError) as error:
            raise CommandError("Campaign was not found.") from error
        if campaign.name != QA_CAMPAIGN_NAME:
            raise CommandError("The supplied campaign is not the named QA campaign.")

        User = get_user_model()
        operator = User.objects.filter(
            pk=options["operator_id"], is_active=True
        ).first()
        if operator is None:
            raise CommandError("The indicated operator is not an active Gravewright user.")
        try:
            who = member(campaign.pk, operator.pk)
        except JournalError as error:
            raise CommandError("The indicated operator is not an active campaign member.") from error
        if who.role != "gm":
            raise CommandError("The indicated operator does not have the campaign GM role.")

        path = options["png_path"].expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".png":
            raise CommandError("--png-path must point to an existing PNG file.")
        expected = options["sha256"].strip().lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise CommandError("--sha256 must be a 64-character hexadecimal digest.")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise CommandError("The PNG SHA-256 does not match --sha256.")

        existing = Scene.objects.filter(
            campaign=campaign, name=QA_SCENE_NAME
        ).first()
        if existing is not None:
            self.report_existing(campaign, existing)
            notify(campaign.pk)
            return

        raw_settings = {"visibility": "players"}
        try:
            with path.open("rb") as source:
                row = services.create_from_upload(
                    campaign.pk,
                    operator.pk,
                    QA_SCENE_NAME,
                    raw_settings,
                    File(source, name=path.name),
                    activate=True,
                    reject_duplicate=True,
                )
        except services.MapError as error:
            if error.code == "already_exists":
                existing = Scene.objects.filter(
                    campaign=campaign, name=QA_SCENE_NAME
                ).first()
                if existing is not None:
                    self.report_existing(campaign, existing)
                    notify(campaign.pk)
                    return
            raise CommandError(str(error)) from error

        self.verify_scene(campaign, row)
        notify(campaign.pk)
        self.stdout.write(
            self.style.SUCCESS(
                f"QA_SCENE=CREATED ID={row.pk} VISIBILITY={row.visibility} "
                f"TILES={Tile.objects.filter(scene=row).count()} ACTIVE_BROADCAST=YES"
            )
        )

    def report_existing(self, campaign, row):
        try:
            self.verify_scene(campaign, row)
        except CommandError as error:
            raise CommandError(
                "A QA scene with this name already exists but is incomplete; refusing to duplicate it."
            ) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"QA_SCENE=EXISTING ID={row.pk} VISIBILITY={row.visibility} "
                f"TILES={Tile.objects.filter(scene=row).count()} ACTIVE_BROADCAST=YES"
            )
        )

    def verify_scene(self, campaign, row):
        if row.campaign_id != campaign.pk or row.visibility != "players":
            raise CommandError("The QA scene is not attached to this campaign with player visibility.")
        if not Broadcast.objects.filter(campaign=campaign, scene=row).exists():
            raise CommandError("The QA Broadcast is not active on the created scene.")
        tiles = list(Tile.objects.filter(scene=row).order_by("lod", "y", "x"))
        if not tiles:
            raise CommandError("The QA scene has no persisted map tiles.")
        expected = {
            (lod, x, y)
            for lod in range(row.max_lod + 1)
            for y in range(math.ceil(row.height / (row.tile_size * 2**lod)))
            for x in range(math.ceil(row.width / (row.tile_size * 2**lod)))
        }
        actual = {(tile.lod, tile.x, tile.y) for tile in tiles}
        if actual != expected:
            raise CommandError("The persisted QA tile pyramid is incomplete.")
        for tile in tiles:
            if not tile.file.storage.exists(tile.file.name):
                raise CommandError("A persisted QA tile file is not accessible.")
            try:
                with tile.file.open("rb") as tile_stream:
                    with Image.open(tile_stream) as image:
                        if image.format != "WEBP":
                            raise CommandError("A persisted QA tile is not WebP.")
                        image.verify()
            except (OSError, UnidentifiedImageError, ValueError) as error:
                raise CommandError("A persisted QA tile cannot be read.") from error
