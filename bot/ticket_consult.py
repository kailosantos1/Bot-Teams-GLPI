"""Personal ticket navigation; state is a short-lived selection, never authority."""
import asyncio
import secrets
import time
import unicodedata
from bot.cards import Activity, HeroCard, CardAction, _card_attachment, is_personal_conversation
from bot.state import user_state, nav_state_accessor
from config import settings
from services.ticket_query import TicketQuery, STATUS_LABELS

query_state_accessor = user_state.create_property('TicketQueryState')
notification_state_accessor = user_state.create_property('NotificationState')
query = TicketQuery(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN)
TTL = 300
DENIED = 'Não consegui confirmar seu acesso aos chamados. Entre em contato com o suporte de TI.'
ERROR = 'Não consegui consultar seus chamados agora. Tente novamente em instantes.'
STALE = 'A lista expirou ou mudou. Atualize a lista.'
UNAVAILABLE = 'Esse chamado não está disponível para consulta. Atualize a lista.'


def safe_title(title):
    # Only letters, numbers, spaces and ordinary punctuation; no markup, URLs or mentions.
    text = ''.join(c if (unicodedata.category(c)[0] in 'LN' or c in ' ,;!?()-') else ' ' for c in title)
    return ' '.join(text.split())[:120] or 'Sem título'


def card(text, version, actions):
    buttons = []
    for action, label in actions:
        title = f'{action} — {label}' if action.isdigit() and not label.startswith(action + ' — ') else label
        buttons.append(CardAction(type='messageBack', title=title, text=action,
                                 display_text=title, value={'query': action, 'version': version}))
    guidance = '\n\nToque em uma opção ou digite o número.' if any(action.isdigit() for action, _ in actions) else ''
    attachments = [_card_attachment(HeroCard(text=text.rstrip() + guidance if offset == 0 else 'Navegação',
                    buttons=buttons[offset:offset + 5])) for offset in range(0, len(buttons), 5)]
    return Activity(type='message', text=text if not attachments else None, attachments=attachments)


async def reset(context):
    # BotStatePropertyAccessor.delete raises KeyError for an absent property.
    # Public get initializes it first, making cleanup safe on fresh/repeated turns.
    # Storage errors still propagate normally.
    await query_state_accessor.get(context, lambda: {})
    await query_state_accessor.delete(context)


async def handle(context, text):
    raw_text, text = text, text.lower()
    activity = context.activity
    if not is_personal_conversation(activity):
        return False, None
    nav = await nav_state_accessor.get(context, lambda: {})
    payload = getattr(activity, 'value', None)
    action = payload.get('action') if isinstance(payload, dict) else None
    active = nav.get('screen') == 'consult' or isinstance(payload, dict) and bool({'query', 'detail'} & set(payload))
    entry = action == 'consult_tickets' and set(payload) == {'action'}
    entry |= not payload and nav.get('screen') != 'open_ticket' and text in {
        '2', 'consultar', 'meus chamados', 'consultar chamados', 'consultar meus chamados',
        '2 — consultar meus chamados', '2 - consultar meus chamados'} and not active
    if not active and not entry:
        await reset(context)
        return False, None
    context.sensitive_ticket_flow = True
    state = await query_state_accessor.get(context, lambda: {})
    if state.get('view') in {'capture', 'confirm'}:
        entry = False
    if active and not state.get('view') and (text in {'0', 'menu', 'voltar ao menu', 'sair', 'cancelar'} and not payload
                   or action in {'menu', 'open_ticket'} and set(payload) == {'action'}):
        await reset(context)
        return False, None
    if active and isinstance(payload, dict) and payload == {'query': '0', 'version': ''}:
        await reset(context)
        from bot.cards import build_menu_activity
        await nav_state_accessor.set(context, {'screen': 'menu'})
        return True, build_menu_activity('')
    await nav_state_accessor.set(context, {'screen': 'consult'})
    try:
        resolver = getattr(context, 'resolve_ticket_identity', None)
        result = await resolver() if resolver else None
    except Exception:
        result = None
    if result is None or result.code != 'ok' or result.identity is None:
        await reset(context)
        return True, card(DENIED, '', [('0', 'Voltar ao menu')])
    binding = [result.identity.tenant_id, result.identity.object_id, result.glpi_user_id,
               activity.conversation.id, activity.from_property.id]
    valid = state.get('binding') == binding and state.get('expires', 0) > time.time()
    if not valid:
        await reset(context)
    if state.get('view') and valid and not entry and payload != {'query': '8', 'version': ''}:
        try:
            from bot.ticket_detail import handle as handle_detail
            response = await handle_detail(context, raw_text, result, binding, state, payload)
            if response is not None:
                return True, response
            # Explicit return to list: requery current items and rotate version.
            text, payload = '8', None
        except Exception:
            # Keep draft references on recoverable read/storage failures; never log text.
            from bot.ticket_detail import screen
            actions = [('retry_view', 'Tentar novamente'), ('cancel', 'Cancelar resposta')] if state.get('view') in {'capture', 'confirm'} else [('8', 'Atualizar conversa'), ('4', 'Voltar ao chamado'), ('3', 'Meus chamados'), ('0', 'Menu principal')]
            instructions = '\nUse Tentar novamente, /tentar-novamente ou /cancelar-resposta.' if state.get('view') in {'capture', 'confirm'} else ''
            return True, await screen(context, state, ERROR + instructions, actions)
    op = 'atualizar' if entry else text
    recovery = payload == {'query': '8', 'version': ''}
    if recovery:
        op = 'atualizar'
    if payload and not entry and not recovery:
        if (not isinstance(payload, dict) or set(payload) != {'query', 'version'}
                or not valid or payload['version'] != state.get('version')
                or not isinstance(payload['query'], str)):
            return True, card(STALE, '', [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
        op = payload['query']
    op = {'8': 'atualizar', '9': 'proximos', '7': 'anteriores', '6': 'lista',
          'próximos': 'proximos'}.get(op, op)
    if op == '0':
        await reset(context)
        await nav_state_accessor.set(context, {'screen': 'menu'})
        from bot.cards import build_menu_activity
        return True, build_menu_activity('')
    if not valid and op != 'atualizar':
        await reset(context)
        return True, card(STALE, '', [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
    try:
        if op.isascii() and op.isdigit() and 1 <= int(op) <= 5:
            page = state['ids']
            index = int(op) - 1
            if index >= len(page):
                return True, card('Opção inválida.', state['version'], [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
            tid = page[index]
            from bot.ticket_detail import details
            from services.ticket_conversation import AccessDenied
            try:
                return True, await details(context, result, binding, state, tid=tid)
            except AccessDenied:
                return True, card(UNAVAILABLE, state['version'],
                                  [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
        if op not in {'atualizar', 'proximos', 'anteriores', 'lista'}:
            return True, card('Opção inválida.', state.get('version', ''), [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
        offset = state.get('offset', 0) if valid else 0
        if op == 'atualizar':
            offset = 0
        elif op == 'proximos':
            offset += 5
        elif op == 'anteriores':
            offset = max(0, offset - 5)
        items = await asyncio.to_thread(query.list, result.glpi_user_id)
        offset = min(offset, max(0, ((len(items) - 1) // 5) * 5))
        page = items[offset:offset + 5]
        version = secrets.token_urlsafe(16)
        await query_state_accessor.set(context, {'binding': binding, 'expires': time.time() + TTL,
                                                'version': version, 'offset': offset, 'ids': [x['id'] for x in page]})
        message = '📋 Seus chamados em andamento:\n\n' if items else '✅ Você não tem chamados em aberto no momento.\n\n'
        actions = []
        for i, item in enumerate(page, 1):
            actions.append((str(i), f"{i} — {safe_title(item['title'])} · Chamado #{item['id']} · {STATUS_LABELS[item['status']]}"))
        for op, label, present in [('7', 'Anteriores', offset > 0), ('9', 'Próximos', offset + 5 < len(items)),
                                   ('8', 'Atualizar', True), ('0', 'Voltar ao menu', True)]:
            if present:
                actions.append((op, label))
        return True, card(message, version, actions)
    except Exception:
        await reset(context)
        return True, card(ERROR, '', [('8', 'Atualizar'), ('0', 'Voltar ao menu')])
