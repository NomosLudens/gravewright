import json
import hashlib
import hmac
import time
from pathlib import Path

from datastar_py.django import DatastarResponse, ServerSentEventGenerator as SSE
from django.conf import settings
from django.contrib.auth import logout
from django.http import Http404, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from gravewright.web.responses import navigate

from . import services
from .kallistis import (
    KallistisCharacterReadError,
    KallistisHandoffError,
    consume_handoff,
    read_kallistis_character,
)
from .provisioning import (
    KallistisProvisionError,
    list_linkable_campaigns,
    link_existing_campaign,
    parse_campaign_list_payload,
    provision,
)
from .forms import (
    AccountUpdateForm,
    KallistisPlayerPhraseForm,
    LoginForm,
    RegistrationForm,
)


MESSAGES = json.loads(Path(__file__).with_name('messages.json').read_text())


def is_datastar(request):
    return request.headers.get('Datastar-Request') == 'true'


def gate_response(request, *, mode=None, form=None, error=None):
    if request.user.is_authenticated:
        return navigate(request, '/inside')
    if mode is None:
        mode = ('authenticated' if request.user.is_authenticated else
                'login' if services.configured() else 'setup')
    from gravewright.administration.preferences import public_privacy
    context = {
        'privacy_policy': public_privacy(),
        'mode': mode,
        'text': MESSAGES,
        'account': request.user if request.user.is_authenticated else None,
        'name': form.data.get('name', '') if form else '',
        'email': form.data.get('email', '') if form else '',
        'error': MESSAGES['errors'].get(error.code, MESSAGES['errors']['request_failed']) if error else '',
    }
    from gravewright.web.localization import template_context
    context.update(template_context(request))
    context["error"] = context.get("language", {}).get("messages", {}).get(context["error"], context["error"])
    if is_datastar(request):
        html = render_to_string('gravewright_accounts/partials/gate.html', context,
                                request=request, using='jinja2')
        response = DatastarResponse(SSE.patch_elements(html))
        # A handled validation error is a successful UI patch, not a failed fetch.
        if error:
            response['X-Auth-Status'] = str(error.status)
    else:
        response = render(request, 'gravewright_accounts/gate.html', context,
                          status=error.status if error else 200, using='jinja2')
    if error and error.retry_after:
        response['Retry-After'] = str(error.retry_after)
    return response


def api_error(error):
    response = JsonResponse({'error': error.code}, status=error.status)
    if error.retry_after:
        response['Retry-After'] = str(error.retry_after)
    return response


def validated_form(mode, data):
    if not isinstance(data, dict):
        raise services.AuthError('invalid_input')
    fields = {
        'login': ('email', 'password'),
        'player': ('phrase',),
        'register': ('name', 'email', 'password'),
        'setup': ('name', 'email', 'password'),
    }[mode]
    # Django CharField coerces other types to strings; the HTTP contract does not.
    for field in fields:
        if not isinstance(data.get(field), str):
            raise services.AuthError(
                'invalid_credentials' if mode in ('login', 'player') else f'invalid_{field}',
                401 if mode in ('login', 'player') else 400,
            )
    form_class = {
        'login': LoginForm,
        'player': KallistisPlayerPhraseForm,
        'register': RegistrationForm,
        'setup': RegistrationForm,
    }[mode]
    form = form_class(data)
    if not form.is_valid():
        field = next(iter(form.errors))
        raise services.AuthError(
            'invalid_credentials' if mode in ('login', 'player') else f'invalid_{field}',
            401 if mode in ('login', 'player') else 400,
        )
    return form


def authenticate_submission(request, mode, data):
    services.reserve_attempt(request)
    form = validated_form(mode, data)
    if mode == 'login':
        return services.sign_in(request, form.cleaned_data)
    if mode == 'player':
        return services.sign_in_kallistis_phrase(request, form.cleaned_data['phrase'])
    return services.register(request, form.cleaned_data, owner=mode == 'setup')


@ensure_csrf_cookie
@require_GET
def kallistis_handoff(request):
    code = request.GET.get("code", "")
    try:
        campaign_id = consume_handoff(request, code)
    except KallistisHandoffError:
        return HttpResponse("KALLISTIS handoff inválido ou expirado.", status=401)
    request.session.modified = False
    response = navigate(request, "/game/" + str(campaign_id))
    if request.headers.get("Datastar-Request") != "true":
        response.set_cookie(
            settings.SESSION_COOKIE_NAME,
            request.session.session_key,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite="Lax",
            path=settings.SESSION_COOKIE_PATH,
        )
    return response


@require_GET
def kallistis_character_read(request, character_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "authentication_required"}, status=401)
    try:
        projection = read_kallistis_character(request.user, character_id)
    except KallistisCharacterReadError as error:
        status = {
            "kallistis_identity_required": 403,
            "character_not_found": 404,
            "character_read_not_configured": 503,
            "character_read_unavailable": 503,
            "character_read_failure": 502,
        }.get(error.code, 502)
        return JsonResponse({"error": error.code}, status=status)
    return JsonResponse(projection, status=200)


PROVISION_SIGNATURE_MAX_AGE_SECONDS = 60


def verify_kallistis_provision_signature(request):
    secret = settings.KALLISTIS_VTT_SERVICE_SECRET
    if not secret:
        return JsonResponse({"valid": False, "error": "service_not_configured"}, status=503)
    timestamp = request.headers.get("X-Kallistis-Timestamp", "")
    signature = request.headers.get("X-Kallistis-Signature", "")
    if not timestamp or not signature:
        return JsonResponse({"valid": False, "error": "signature_required"}, status=401)
    try:
        issued_at = int(timestamp)
    except ValueError:
        return JsonResponse({"valid": False, "error": "signature_invalid"}, status=401)
    if abs(time.time() - issued_at) > PROVISION_SIGNATURE_MAX_AGE_SECONDS:
        return JsonResponse({"valid": False, "error": "signature_expired"}, status=401)
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), timestamp.encode("ascii") + b"." + request.body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return JsonResponse({"valid": False, "error": "signature_invalid"}, status=401)
    return None


@csrf_exempt
@require_POST
def kallistis_provision(request):
    signature_error = verify_kallistis_provision_signature(request)
    if signature_error is not None:
        return signature_error
    if len(request.body) > 64 * 1024:
        return JsonResponse({"valid": False, "error": "request_too_large"}, status=413)
    try:
        payload = json.loads(request.body)
        result = provision(payload)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"valid": False, "error": "invalid_json"}, status=400)
    except KallistisProvisionError as error:
        return JsonResponse({"valid": False, "error": error.code}, status=error.status)
    return JsonResponse(result, status=200)


def _kallistis_internal_payload(request):
    signature_error = verify_kallistis_provision_signature(request)
    if signature_error is not None:
        return None, signature_error
    if len(request.body) > 16 * 1024:
        return None, JsonResponse({"valid": False, "error": "request_too_large"}, status=413)
    try:
        return json.loads(request.body), None
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"valid": False, "error": "invalid_json"}, status=400)


@csrf_exempt
@require_POST
def kallistis_campaign_list(request):
    payload, error = _kallistis_internal_payload(request)
    if error is not None:
        return error
    try:
        parse_campaign_list_payload(payload)
        campaigns = list_linkable_campaigns()
    except KallistisProvisionError as exception:
        return JsonResponse({"valid": False, "error": exception.code}, status=exception.status)
    return JsonResponse({
        "valid": True,
        "campaigns": [{"id": str(row["id"]), "name": row["name"]} for row in campaigns],
    }, status=200)


@csrf_exempt
@require_POST
def kallistis_campaign_link(request):
    payload, error = _kallistis_internal_payload(request)
    if error is not None:
        return error
    try:
        result = link_existing_campaign(payload)
    except KallistisProvisionError as exception:
        return JsonResponse({"valid": False, "error": exception.code}, status=exception.status)
    return JsonResponse(result, status=200)

@require_GET
def gate(request):
    return gate_response(request)


@sensitive_post_parameters('password')
@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def access(request, mode):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return navigate(request, '/inside')
        if not services.configured():
            mode = 'setup'
        elif mode == 'setup':
            mode = 'login'
        return gate_response(request, mode=mode)
    data = request.POST.dict()
    try:
        authenticate_submission(request, mode, data)
    except services.AuthError as error:
        if error.code == 'owner_already_configured':
            mode = 'login'
        elif error.code == 'setup_required':
            mode = 'setup'
        error_form = {
            'login': LoginForm,
            'player': KallistisPlayerPhraseForm,
            'register': RegistrationForm,
            'setup': RegistrationForm,
        }[mode](data)
        return gate_response(request, mode=mode, form=error_form, error=error)
    return navigate(request, '/inside')


@require_POST
def browser_logout(request):
    logout(request)
    return navigate(request, '/login')


@ensure_csrf_cookie
@require_GET
def csrf(request):
    return JsonResponse({'ready': True, 'token': get_token(request), 'header': 'x-csrf-token'})


@require_GET
def status(request):
    return JsonResponse({'configured': services.configured()})


@require_GET
def session(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'account': services.public_account(request.user)})


def read_json(request):
    if request.content_type != 'application/json':
        raise services.AuthError('unsupported_media_type', 415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise services.AuthError('invalid_input') from None
    if not isinstance(data, dict):
        raise services.AuthError('invalid_input')
    return data


@sensitive_post_parameters('password', 'phrase', 'currentPassword', 'newPassword')
@require_POST
def api_access(request, mode):
    try:
        user = authenticate_submission(request, mode, read_json(request))
    except services.AuthError as error:
        return api_error(error)
    return JsonResponse(
        {'account': services.public_account(user)},
        status=200 if mode in ('login', 'player') else 201,
    )


@require_POST
def api_logout(request):
    logout(request)
    return HttpResponse(status=204)


@require_GET
def home(request, kind):
    if kind not in ('gm', 'player'):
        raise Http404
    if not request.user.is_authenticated:
        return api_error(services.AuthError('session_expired', 401))
    expected = 'owner' if kind == 'gm' else 'participant'
    if request.user.role != expected:
        return api_error(services.AuthError('forbidden', 403))
    return JsonResponse({'kind': kind, 'account': services.public_account(request.user)})


@sensitive_post_parameters('currentPassword', 'newPassword')
@require_POST
def account(request):
    if not request.user.is_authenticated:
        return api_error(services.AuthError('session_expired', 401))
    try:
        services.reserve_attempt(request)
        data = read_json(request)
        if set(data) - {'name', 'email', 'currentPassword', 'newPassword'}:
            raise services.AuthError('invalid_input')
        data.setdefault('name', request.user.name)
        if any(not isinstance(value, str) for value in data.values()):
            raise services.AuthError('invalid_input')
        if 'email' in data and not data['email'].strip():
            raise services.AuthError('invalid_email')
        change_password = 'newPassword' in data
        if change_password and not data['newPassword']:
            raise services.AuthError('invalid_password')
        form = AccountUpdateForm(data)
        if not form.is_valid():
            raise services.AuthError('invalid_name' if 'name' in form.errors else 'invalid_email' if 'email' in form.errors else 'invalid_password')
        user = services.update_account(request, form.cleaned_data, change_password=change_password)
    except services.AuthError as error:
        return api_error(error)
    return JsonResponse({'account': services.public_account(user)})


def csrf_failure(request, reason=''):
    error = services.AuthError('invalid_csrf_token', 403)
    if request.path.startswith('/api/'):
        return api_error(error)
    mode = 'player' if request.path.strip('/') == 'login/player' else request.path.strip('/')
    return gate_response(request, mode=mode if mode in ('login', 'player', 'register', 'setup') else None, error=error)
