"""Serve the local Godot export inside an authenticated campaign origin."""

import base64
import hashlib
import mimetypes
from pathlib import Path
import re

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.views.decorators.http import require_GET

from gravewright.accounts.services import AuthError
from gravewright.campaigns.services import get_campaign
from gravewright.web.responses import navigate


EXPORT_ROOT = settings.BASE_DIR / "tactics" / "godot" / ".godot" / "export"


@require_GET
def export(request, campaign_id, asset="index.html"):
    if not request.user.is_authenticated:
        return navigate(request, "/login")
    try:
        get_campaign(request.user, campaign_id)
    except AuthError:
        raise Http404 from None

    if asset == "index.html" and request.GET.get("campaign") != str(campaign_id):
        return HttpResponseRedirect(f"{request.path}?campaign={campaign_id}")

    root = EXPORT_ROOT.resolve()
    target = (root / asset).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404
    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    response = FileResponse(target.open("rb"), content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    if asset == "index.html":
        html = target.read_text(encoding="utf-8")
        inline_scripts = re.findall(
            r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script\s*>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        script_hashes = " ".join(
            "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
            for script in inline_scripts
        )
        response["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self' 'unsafe-eval' " + script_hashes + "; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "font-src 'self' data:; media-src 'self' blob:; worker-src 'self' blob:; "
            "connect-src 'self' ws: wss:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
    return response
