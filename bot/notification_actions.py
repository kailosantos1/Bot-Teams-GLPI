"""Notification payloads are intercepted before forms and textual reply capture."""
import asyncio
import secrets
import time
from bot.cards import Activity, HeroCard, CardAction, _card_attachment, is_personal_conversation
from config import settings
from identity.notifications import NotificationStore
from notifications.policy import Policy


def actions(text, values):
    buttons = [CardAction(type='messageBack', title=label, text=label, display_text=label, value=value)
               for label, value in values]
    return Activity(type='message', text=text, attachments=[_card_attachment(HeroCard(text=text, buttons=buttons))])


async def handle(context, user_name):
    from bot import dialogs, ticket_consult
    from bot.ticket_detail import details
    from bot.cards import build_interrupt_activity
    payload = getattr(context.activity, 'value', None)
    if not isinstance(payload, dict) or not {'notification', 'notification_choice', 'notification_resume'} & set(payload):
        return False, None
    context.sensitive_ticket_flow = True
    unavailable = 'Esse aviso não está mais disponível. Consulte seus chamados novamente.'
    fallback = lambda: actions(unavailable, [('Meus chamados', {'action': 'consult_tickets'})])
    if not is_personal_conversation(context.activity):
        return True, unavailable
    policy = Policy.configured(settings)
    if policy is None:
        return True, fallback()
    resolver = getattr(context, 'resolve_ticket_identity', None)
    result = await resolver() if resolver else None
    if not result or result.code != 'ok' or not result.identity:
        return True, fallback()
    binding = [result.identity.tenant_id, result.identity.object_id, result.glpi_user_id,
               context.activity.conversation.id, context.activity.from_property.id]
    nav = await dialogs.nav_state_accessor.get(context, lambda: {})
    notice_state = await ticket_consult.notification_state_accessor.get(context, lambda: {})
    state = await ticket_consult.query_state_accessor.get(context, lambda: {})
    if set(payload) == {'notification_resume'}:
        saved = notice_state.get('notification_saved')
        if (not saved or payload['notification_resume'] != saved['token']
                or saved['state'].get('binding') != binding or saved['state'].get('expires', 0) <= time.time()):
            return True, fallback()
        if await dialogs.user_profile_accessor.get(context, lambda: None) or state.get('view') in {'capture', 'confirm'}:
            return True, 'Existe um preenchimento em andamento. Continue usando as opções atuais.'
        await ticket_consult.query_state_accessor.set(context, saved['state'])
        await dialogs.nav_state_accessor.set(context, {'screen': 'consult'})
        await ticket_consult.notification_state_accessor.delete(context)
        # Preserve operation and version; render through existing authorization.
        old = saved['state']
        from bot.ticket_detail import handle as detail_handle
        return True, await detail_handle(context, '/tentar-novamente', result, binding, old, None)
    token = payload.get('notification')
    if set(payload) == {'notification_choice', 'token'}:
        pending = notice_state.get('notification_pending')
        if (not pending or payload['token'] != pending['token'] or pending['expires'] <= time.time()
                or state.get('version') != pending['version'] or state.get('binding') != binding):
            return True, fallback()
        if payload['notification_choice'] == 'continue':
            notice_state.pop('notification_pending', None)
            await ticket_consult.notification_state_accessor.set(context, notice_state)
            return True, 'Seu preenchimento foi mantido. Continue usando as opções da resposta em andamento.'
        if payload['notification_choice'] != 'leave':
            return True, fallback()
        token = pending['event']
    elif set(payload) != {'notification'} or not isinstance(token, str) or not 20 <= len(token) <= 100:
        return True, fallback()
    try:
        store = NotificationStore(settings.IDENTITY_DB_PATH)
        event = await asyncio.to_thread(store.event, token, result, policy.app)
        if not event:
            return True, fallback()
        # Even the interruption prompt is preceded by current resource authorization.
        if not await asyncio.to_thread(ticket_consult.query.available, result.glpi_user_id, event['ticket']):
            return True, fallback()
        session = await dialogs.user_profile_accessor.get(context, lambda: None)
        if session:
            confirmation = secrets.token_urlsafe(24)
            await dialogs.nav_state_accessor.set(context, {'screen': 'confirm_menu_interrupt', 'confirmation': confirmation})
            return True, build_interrupt_activity(user_name, session.get('form_name', 'Formulário'), confirmation)
        drafting = state.get('view') in {'capture', 'confirm'} and state.get('binding') == binding and state.get('expires', 0) > time.time()
        if drafting and 'notification_choice' not in payload:
            confirmation = secrets.token_urlsafe(24)
            notice_state['notification_pending'] = {'token': confirmation, 'event': token, 'version': state['version'], 'expires': min(state['expires'], time.time() + 300)}
            await ticket_consult.notification_state_accessor.set(context, notice_state)
            return True, actions('Existe uma resposta em preenchimento. Deseja continuar ou guardar o rascunho e ver o aviso? O prazo do rascunho continua correndo.', [
                ('Continuar resposta', {'notification_choice': 'continue', 'token': confirmation}),
                ('Guardar e ver chamado', {'notification_choice': 'leave', 'token': confirmation})])
        if drafting and notice_state.get('notification_saved', {}).get('state', {}).get('expires', 0) > time.time():
            return True, 'Existe outra resposta guardada. Retome-a pelo botão anterior antes de guardar mais uma. O preenchimento atual foi mantido.'
        if drafting:
            notice_state['notification_saved'] = {'state': dict(state), 'token': secrets.token_urlsafe(24)}
        notice_state.pop('notification_pending', None)
        nav['screen'] = 'consult'
        await dialogs.nav_state_accessor.set(context, nav)
        await ticket_consult.notification_state_accessor.set(context, notice_state)
        clean = {'binding': binding, 'expires': time.time() + 300, 'ids': [], 'offset': 0}
        response = await details(context, result, binding, clean, tid=event['ticket'])
        saved = notice_state.get('notification_saved')
        if saved and saved['state'].get('expires', 0) > time.time():
            await context.send_activity(actions('Rascunho guardado até o prazo original.', [('Retomar resposta guardada', {'notification_resume': saved['token']})]))
        return True, response
    except Exception:
        return True, fallback()
