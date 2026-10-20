"""Hard-confined local settings for the G5.3 Knossos QA fixture instance."""

import os
from pathlib import Path

from .settings import *  # noqa: F403


QA_ROOT = Path("/tmp/gravewright-tactics-qa-20261015/g5.3").resolve()
if Path(DATABASES["default"]["NAME"]).resolve() != QA_ROOT / "gravewright.sqlite3":  # noqa: F405
    raise RuntimeError("G5.3 QA settings require the dedicated SQLite database path.")
if Path(MEDIA_ROOT).resolve() != QA_ROOT / "media":  # noqa: F405
    raise RuntimeError("G5.3 QA settings require the dedicated media path.")
if not Path(os.environ.get("GRAVEWRIGHT_DATABASE", "")).resolve() == QA_ROOT / "gravewright.sqlite3":
    raise RuntimeError("G5.3 QA requires GRAVEWRIGHT_DATABASE to be set explicitly.")

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]
GRAVEWRIGHT_PUBLIC_ORIGIN = ""
GRAVEWRIGHT_TACTICAL_QA_FIXTURES_ENABLED = True
GRAVEWRIGHT_TACTICAL_QA_FIXTURE_ROOT = str(QA_ROOT)
GRAVEWRIGHT_REDIS_URL = ""
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
GRAVEWRIGHT_MARKETPLACE_URL = ""
KALLISTIS_ORIGIN = ""
KALLISTIS_VTT_CONSUME_URL = ""
KALLISTIS_VTT_SERVICE_SECRET = ""
KALLISTIS_VTT_CHARACTER_READ_URL = ""
CSRF_TRUSTED_ORIGINS = []
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
DATABASES["default"]["TEST"]["NAME"] = str(QA_ROOT / "test-gravewright.sqlite3")  # noqa: F405
