"""Idempotent dice submission, private audiences and committed chat delivery.

A durable claim is recorded before evaluation. Completion rechecks authorization
and persists the result; retries retrieve that result instead of drawing again."""

from datetime import timedelta
from uuid import UUID, uuid5
from django import forms
from django.db import transaction
from django.utils import timezone

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Membership
from gravewright.chat.models import Message, Recipient
from gravewright.chat.services import public_message, consume_limit
from gravewright.realtime.services import authorize
from .models import Submission
from gravewright.chat.context import scene_for, readable
from .engine import RollError
from .kallistis import evaluate as evaluate_kallistis, prepare_action


class RollForm(forms.Form):
    expression = forms.CharField(max_length=512)
    label = forms.CharField(max_length=48, required=False)
    visibility = forms.ChoiceField(choices=[('public', 'Public'), ('gm', 'GM')])
    repeat = forms.IntegerField(min_value=1, max_value=12)
    requestId = forms.UUIDField()
    system = forms.ChoiceField(choices=[('generic', 'Generic'), ('kallistis', 'KALLISTIS')])
    modifier = forms.IntegerField(min_value=-1000, max_value=1000)
    difficulty = forms.IntegerField(min_value=1, max_value=1000)


def validate(payload):
    if not isinstance(payload, dict):
        raise RollError('Invalid roll request.')
    values = {'label': '', 'visibility': 'public', 'repeat': 1, 'system': 'generic',
              'modifier': 0, 'difficulty': 15, **payload}
    mode = payload.get('mode', payload.get('kallistisMode', 'single'))
    if mode not in ('single', 'action', 'opposed'):
        raise RollError('KALLISTIS mode must be single, action or opposed.')
    raw_difficulty = values['difficulty']
    difficulty_label = None
    if isinstance(raw_difficulty, dict):
        difficulty_label = raw_difficulty.get('label')
        values['difficulty'] = raw_difficulty.get('value')
    elif isinstance(raw_difficulty, int):
        difficulty_label = payload.get('difficultyLabel')
    if any(not isinstance(values.get(key), str) for key in ['expression', 'label', 'visibility', 'requestId', 'system']) or type(values['repeat']) is not int or type(values['modifier']) is not int or type(values['difficulty']) is not int:
        raise RollError('Invalid roll request.')
    form = RollForm(values)
    if not form.is_valid():
        raise RollError(' '.join(str(e) for errors in form.errors.values() for e in errors))
    data = {**form.cleaned_data, 'mapId': payload.get('mapId'), 'block_id': payload.get('block_id'),
            'mode': mode, 'difficulty_label': difficulty_label}
    if data['system'] == 'kallistis' and data['expression'].strip().lower() != '2d10':
        raise RollError('KALLISTIS rolls use the fixed 2d10 expression.')
    if data['system'] != 'kallistis' and mode != 'single':
        raise RollError('KALLISTIS action modes require the KALLISTIS system.')
    if data['system'] == 'kallistis' and mode == 'action':
        action_payload = _action_payload(payload)
        actor_input = payload.get('action') if isinstance(payload.get('action'), dict) else {}
        actor_id_input = payload.get('actorId', payload.get('actor_id')) or actor_input.get('actorId', actor_input.get('actor_id'))
        if actor_id_input:
            # Numeric values are replaced from Actor after membership and
            # campaign authorization; keep validation structural here.
            action_payload = dict(action_payload)
            for field in ('attribute', 'skill'):
                if isinstance(action_payload.get(field), dict):
                    action_payload[field] = {**action_payload[field], 'value': 0}
            for field in ('attribute_value', 'attributeValue', 'skill_value', 'skillValue'):
                if field in action_payload:
                    action_payload[field] = 0
        data['action'] = prepare_action(action_payload)
        actor_id = actor_id_input
        if actor_id:
            try:
                data['actor_id'] = str(UUID(str(actor_id)))
            except (ValueError, TypeError, AttributeError):
                raise RollError('actor_id must be a UUID.') from None
            data['action']['actor_id'] = data['actor_id']
        data['modifier'] = data['action']['modifier_total']
    elif data['system'] == 'kallistis' and mode == 'opposed':
        opposed = payload.get('opposed')
        if not isinstance(opposed, dict):
            raise RollError('Opposed KALLISTIS rolls require two sides.')
        side_a = opposed.get('side_a', opposed.get('sideA'))
        side_b = opposed.get('side_b', opposed.get('sideB'))
        data['opposed'] = {
            'opposed_test_id': _opposed_test_id(data['requestId'], payload.get('opposed_test_id', payload.get('opposedTestId'))),
            'side_a': prepare_action(side_a),
            'side_b': prepare_action(side_b),
        }
    return data


def _action_payload(payload):
    action = payload.get('action')
    if isinstance(action, dict):
        return action
    names = ('action_label', 'actionLabel', 'attribute', 'attribute_name', 'attributeName',
             'attribute_value', 'attributeValue', 'skill', 'skill_name', 'skillName',
             'skill_value', 'skillValue', 'impulse', 'pressure', 'helpers', 'helper_count', 'helperCount',
             'corruption_applies', 'corruptionApplies')
    return {name: payload[name] for name in names if name in payload}


def bind_actor_action(data, member):
    """Replace client-supplied numeric action values with Actor values."""
    if not data.get('action') or not data.get('actor_id'):
        return data
    from gravewright.actors import runtime

    action = runtime.authoritative_action(data['actor_id'], member, data['action'])
    return {**data, 'action': action, 'modifier': action['modifier_total']}


def _opposed_test_id(request_id, requested=None):
    if requested is None:
        return str(uuid5(UUID(str(request_id)), 'kallistis-opposed'))
    try:
        return str(UUID(str(requested)))
    except (ValueError, TypeError, AttributeError):
        raise RollError('opposed_test_id must be a UUID.') from None


def _opposed_request_id(request_id, side):
    return str(uuid5(UUID(str(request_id)), f'kallistis-opposed:{side}'))


def envelope(message):
    audience = list(message.recipients.values_list('user_id', flat=True)) if message.visibility == 'gm' else None
    return public_message(message), [str(pk) for pk in audience] if audience is not None else None


def claim(member_id, data):
    """Reserve a request before random evaluation, or return its completed message."""
    with transaction.atomic():
        member = Membership.objects.select_for_update().filter(pk=member_id).first()
        if member is None or member.role=='streamer':
            raise AuthError('not_a_member')
        previous = Message.objects.filter(campaign_id=member.campaign_id, author_id=member.user_id,
                                           request_id=data['requestId']).first()
        if previous:
            if not readable(member.campaign_id, member.user_id, previous.scene_id): raise AuthError('invalid_scene')
            if previous.roll is None:
                raise RollError('This request ID was already used for a chat message.')
            return None, envelope(previous)
        reservation = Submission.objects.filter(campaign_id=member.campaign_id, author_id=member.user_id,
                                                  request_id=data['requestId']).first()
        if reservation:
            if reservation.error:
                raise RollError(reservation.error)
            if reservation.expires_at <= timezone.now():
                raise RollError('The roll was interrupted. Submit a new roll.')
            raise AuthError('roll_in_progress')
        resolved = scene_for(member, data.get('mapId'), data.get('block_id'))
        data['resolved_scene_id'] = str(resolved.pk) if resolved else None
        consume_limit(member)
        reservation = Submission.objects.create(campaign_id=member.campaign_id, author_id=member.user_id,
            request_id=data['requestId'], expires_at=timezone.now()+timedelta(seconds=15))
        return reservation.pk, None


def fail(reservation_id, error):
    Submission.objects.filter(pk=reservation_id).update(error=str(error)[:512])


def complete(reservation_id, data, result, session_key, campaign_id, user_id):
    """Reauthorize and commit a reserved result with its fixed recipient audience."""
    with transaction.atomic():
        member = authorize(session_key, campaign_id, user_id) if session_key is not None else Membership.objects.select_related('user').filter(campaign_id=campaign_id,user_id=user_id,user__is_active=True).first()
        if member is None or member.role=='streamer':
            raise AuthError('not_a_member')
        # Membership deletion and other submissions serialize against this lock.
        Membership.objects.select_for_update().get(pk=member.pk)
        claim = Submission.objects.select_for_update().get(pk=reservation_id)
        if claim.error or claim.expires_at <= timezone.now():
            raise RollError('The roll was interrupted. Submit a new roll.')
        data = bind_actor_action(data, member)
        if data.get('action'):
            from gravewright.actors import runtime
            condition_modifier, _ = runtime.action_modifier(
                data.get('actor_id'), member, data['action'], consume=True
            )
            if condition_modifier:
                result = [runtime.adjust_result(item, condition_modifier) for item in result] if isinstance(result, list) else runtime.adjust_result(result, condition_modifier)
                data = {**data, 'modifier': data['modifier'] + condition_modifier,
                        'action': {**data['action'], 'condition_modifier': condition_modifier}}
        label = data['label'] or data.get('action', {}).get('action_label', '')
        result_value = result[0] if isinstance(result, list) else result
        if data.get('action'):
            result_value = {**result_value, 'action': data['action']}
        if data.get('mode') == 'opposed':
            result_value = {**result_value, 'opposed': data['opposed']}
        roll = {'expression': data['expression'], 'label': label,
                'secret': data['visibility'] == 'gm', 'result': result_value}
        if data['system'] == 'kallistis':
            roll.update({'system': 'kallistis', 'modifier': data['modifier'],
                         'difficulty': data['difficulty']})
            if data.get('difficulty_label'):
                roll['difficulty_label'] = data['difficulty_label']
            if data.get('action'):
                roll['action'] = data['action']
            if data.get('mode') == 'action':
                roll['mode'] = 'action'
            if data.get('mode') == 'opposed':
                roll.update({'mode': 'opposed', 'opposed': data['opposed']})
        if isinstance(result, list):
            roll['batch'] = [{'label': f'Value {i+1}', 'result': value} for i, value in enumerate(result)]
        scene = scene_for(member, data['resolved_scene_id']) if data.get('resolved_scene_id') else None
        message = Message.objects.create(campaign_id=campaign_id, author_id=user_id, scene=scene,
            author_name=member.user.name, text=label, request_id=data['requestId'],
            visibility=data['visibility'], roll=roll)
        if roll['secret']:
            audience = set(Membership.objects.filter(campaign_id=campaign_id, role='gm').values_list('user_id', flat=True))
            audience.add(user_id)
            Recipient.objects.bulk_create([Recipient(message=message, user_id=pk) for pk in audience])
        from gravewright.realtime.dispatch import message as publish, changed
        publish(campaign_id,message.pk)
        changed(campaign_id,user_id,'dice','roll',data['requestId'])
    return envelope(message)


def _opposed_messages(campaign_id, test_id):
    messages = Message.objects.filter(
        campaign_id=campaign_id,
        roll__opposed__opposed_test_id=test_id,
        deleted=False,
    ).order_by('id')
    return list(messages)


def _opposed_resolution(side_a, side_b):
    if side_a['total'] > side_b['total']:
        winner = 'SIDE_A_WINS'
    elif side_b['total'] > side_a['total']:
        winner = 'SIDE_B_WINS'
    else:
        winner = 'TIE_PENDING_CONTEXT'
    return {'winner': winner, 'tie_policy': 'TIE_REQUIRES_CONTEXT'}


def opposed_roll(member_id, data, session_key, campaign_id, user_id):
    """Create or replay two real KALLISTIS submissions for one opposed test."""
    member = Membership.objects.filter(pk=member_id, campaign_id=campaign_id,
                                       user_id=user_id, user__is_active=True).first()
    if member is None or member.role == 'streamer':
        raise AuthError('not_a_member', 403)
    test_id = data['opposed']['opposed_test_id']
    existing = _opposed_messages(campaign_id, test_id)
    if len(existing) == 2:
        return [envelope(message) for message in existing]
    side_data = []
    for side in ('side_a', 'side_b'):
        side_data.append({**data, 'requestId': data['requestId'] if side == 'side_a' else _opposed_request_id(data['requestId'], side),
                          'label': f"{'Side A' if side == 'side_a' else 'Side B'} · {data['opposed'][side]['action_label']}",
                          'action': data['opposed'][side], 'modifier': data['opposed'][side]['modifier_total'],
                          'mode': 'opposed',
                          'opposed_side': side})
    reservations = []
    try:
        for entry in side_data:
            reservation, previous = claim(member_id, entry)
            if previous:
                previous_message, audience = previous
                found = _opposed_messages(campaign_id, test_id)
                if len(found) == 2:
                    return [envelope(message) for message in found]
                raise AuthError('roll_in_progress')
            reservations.append(reservation)
        results = [evaluate_kallistis(entry['modifier'], entry['difficulty'], repeat=1)
                   for entry in side_data]
        resolution = _opposed_resolution(results[0], results[1])
        envelopes = []
        for entry, result in zip(side_data, results):
            entry['opposed'] = {
                'opposed_test_id': test_id,
                'side': entry['opposed_side'],
                'resolution': resolution,
                'other_total': results[1]['total'] if entry['opposed_side'] == 'side_a' else results[0]['total'],
            }
            envelopes.append(complete(reservations.pop(0), entry, result, session_key, campaign_id, user_id))
        return envelopes
    except (AuthError, RollError):
        for reservation in reservations:
            fail(reservation, 'Opposed test was interrupted.')
        raise


def roll(campaign_id, user_id, expression, request_id, *, repeat=1, label='', visibility='public',
         map_id=None, system='generic', modifier=0, difficulty=15, mode='single', action=None,
         opposed=None, opposed_test_id=None):
    """Persist a roll from the native grammar without requiring an HTTP session."""
    payload = dict(expression=expression, requestId=str(request_id), repeat=repeat, label=label,
                   visibility=visibility, mapId=map_id, system=system, modifier=modifier,
                   difficulty=difficulty, mode=mode)
    if action is not None:
        payload['action'] = action
    if opposed is not None:
        payload['opposed'] = opposed
    if opposed_test_id is not None:
        payload['opposed_test_id'] = opposed_test_id
    data=validate(payload)
    member=Membership.objects.filter(campaign_id=campaign_id,user_id=user_id,user__is_active=True).first()
    if member is None or member.role=='streamer':raise AuthError('not_a_member',403)
    data = bind_actor_action(data, member)
    if data.get('mode') == 'opposed':
        return opposed_roll(member.pk, data, None, campaign_id, user_id)[0][0]
    reservation,previous=claim(member.pk,data)
    if previous:return previous[0]
    try:
        if data['system'] == 'kallistis':
            result=evaluate_kallistis(data['modifier'], data['difficulty'], repeat=data['repeat'])
        else:
            from .engine import evaluate
            result=evaluate(expression,repeat)
        return complete(reservation,data,result,None,campaign_id,user_id)[0]
    except (AuthError,RollError) as error:
        fail(reservation,error)
        raise


def reroll(campaign_id, user_id, request_id, message_id):
    """Spend one Determination and replace both natural dice in one action roll."""
    from gravewright.actors import runtime
    from gravewright.actors.models import Actor
    from gravewright.campaigns.models import Campaign
    from gravewright.journals.services import member as resolve_member

    try:
        request_id = UUID(str(request_id))
        message_id = int(message_id)
    except (ValueError, TypeError, AttributeError):
        raise RollError("Invalid reroll request.") from None
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = resolve_member(campaign_id, user_id)
        previous = Message.objects.filter(campaign_id=campaign_id, author_id=user_id,
                                           request_id=request_id).first()
        if previous:
            return envelope(previous)
        original = Message.objects.select_for_update().filter(
            pk=message_id, campaign_id=campaign_id, roll__system="kallistis",
            roll__mode="action", deleted=False,
        ).first()
        if original is None:
            raise RollError("Only a persisted KALLISTIS action can be rerolled.")
        roll_data = original.roll or {}
        if roll_data.get("reroll_of") or roll_data.get("rerolled_by"):
            raise RollError("This action already used Determination.")
        action = roll_data.get("action") or {}
        actor_id = action.get("actor_id")
        if not actor_id:
            raise RollError("This action has no runtime actor.")
        actor = Actor.objects.select_for_update().filter(pk=actor_id, campaign_id=campaign_id).first()
        if actor is None or not runtime.access(actor, who, True):
            raise AuthError("not_found")
        state = runtime.read(actor.data)
        determination = state["resources"]["determination"]
        if determination["current"] < 1:
            raise RollError("Insufficient determination.")
        determination["current"] -= 1
        runtime._write(actor, state)
        result = evaluate_kallistis(roll_data["modifier"], roll_data["difficulty"], repeat=1)
        new_roll = {**roll_data, "result": {**result, "action": action},
                    "reroll_of": str(original.pk), "determination_spent": 1}
        message = Message.objects.create(
            campaign_id=campaign_id, author_id=user_id, scene_id=original.scene_id,
            author_name=who.user.name, text=original.text, request_id=request_id,
            visibility=original.visibility, roll=new_roll,
        )
        if message.visibility == "gm":
            audience = set(Membership.objects.filter(campaign_id=campaign_id, role="gm").values_list("user_id", flat=True))
            audience.add(user_id)
            Recipient.objects.bulk_create([Recipient(message=message, user_id=pk) for pk in audience])
        original.roll = {**roll_data, "rerolled_by": str(message.pk)}
        original.save(update_fields=["roll"])
        from gravewright.realtime.dispatch import message as publish, changed
        publish(campaign_id, message.pk)
        changed(campaign_id, user_id, "actors", "runtime.resource", request_id, {"actorId": str(actor.pk)})
    return envelope(message)
