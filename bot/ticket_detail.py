"""Reading and reply screens. All caller selections come from current list state."""
import asyncio
import secrets
import time
from config import settings
from identity.replies import ReplyStore, MAX_REPLY, valid_reply
from services.ticket_conversation import TicketConversation, AccessDenied
from services.reply_sender import ReplySender
from services.ticket_content import pages, PAGE_SIZE
from bot.ticket_presentation import display_title
from bot.activity_attachments import has_real_attachments
from services.ticket_query import STATUS_LABELS

service = TicketConversation(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN)
reply_store = ReplyStore(settings.IDENTITY_DB_PATH)
UNCERTAIN = ('Não recebi a confirmação do envio. Sua mensagem pode ter sido registrada. '
             'Não vou reenviar automaticamente. Atualize a conversa para conferir.')


async def screen(context, state, text, actions, *, view=None, paragraphs=False):
    from bot.ticket_consult import card, query_state_accessor
    state = dict(state)
    if view:
        state['view'] = view
    state['version'] = secrets.token_urlsafe(16)
    # A read screen never extends a draft lifetime; SQLite checks its own deadline.
    state['expires'] = time.time() + 300
    await query_state_accessor.set(context, state)
    response = card(text, state['version'], actions, paragraphs=paragraphs, guidance=not paragraphs)
    for attachment in response.attachments:
        for button in attachment.content.buttons:
            button.value = {'detail': button.value['query'], 'version': state['version']}
            if state.get('draft'):
                button.value['draft'] = state['draft']
    return response


async def details(context, result, binding, state, tid=None, offset=0):
    state = dict(state)
    tid = tid if tid is not None else state['ticket']
    row = await asyncio.to_thread(service.details, result.glpi_user_id, tid)
    state.update(ticket=tid, view='details', part=offset)
    state.pop('draft', None)
    title = display_title(row['title'], tid)
    description = pages(row['content'])
    title_parts = pages(title) if len(title) > PAGE_SIZE else []
    chunks = title_parts + description
    offset = min(max(0, offset), len(chunks) - 1)
    state['part'] = offset
    position = f' ({offset + 1}/{len(chunks)})' if title_parts else ''
    if title_parts and offset < len(title_parts):
        title, body = chunks[offset], ''
        heading = f'Título ({offset + 1}/{len(title_parts)})'
    else:
        body = chunks[offset]
        if title_parts:
            title = '(Título nas páginas anteriores)'
        heading = '📝 Solicitação' + (f' ({offset + 1}/{len(chunks)})' if len(chunks) > 1 and not title_parts else '')
    text = (f"🎫 Chamado #{tid}{position}\n{title}\nSituação: {STATUS_LABELS[row['status']]}\n\n"
            f"{heading}\n{body}")
    actions = [('1', 'Conversa'), ('2', 'Responder'), ('3', 'Meus chamados'), ('0', 'Menu')]
    if offset:
        actions.append(('7', 'Trecho anterior'))

    if offset + 1 < len(chunks):
        actions.append(('9', 'Ver mais'))

    return await screen(context, state, text, actions, paragraphs=True)


async def history(context, result, state, offset=0):
    binding = state['binding']
    trusted = await asyncio.to_thread(reply_store.sent_followups, binding, state['ticket'])
    messages = await asyncio.to_thread(service.history, result.glpi_user_id, state['ticket'], trusted)
    chunks = []
    for message_index, message in enumerate(messages):
        parts = pages(message['content'])
        for i, part in enumerate(parts, 1):
            part_label = f'Parte {i} de {len(parts)}\n' if len(parts) > 1 else ''
            chunks.append(dict(message=message_index, part=i, parts=len(parts), text=
                f"{message['author']}:\n{part_label}{part}"))
    offset = min(max(0, offset), max(0, len(chunks) - 1))
    heading = '💬 Mensagem mais recente' if chunks and offset == 0 else '💬 Mensagem'
    text = (heading + '\n\n'
            + (chunks[offset]['text'] if chunks else 'Este chamado ainda não tem mensagens públicas.'))
    actions = [('4', 'Voltar ao chamado'), ('8', 'Atualizar')]
    if offset:
        same = chunks[offset - 1]['message'] == chunks[offset]['message']
        actions.append(('7', 'Parte anterior' if same else 'Mensagens mais recentes'))
    if offset + 1 < len(chunks):
        same = chunks[offset + 1]['message'] == chunks[offset]['message']
        actions.append(('9', 'Continuar mensagem' if same else 'Mensagens mais antigas'))
    return await screen(context, dict(state, part=offset), text, actions, view='history', paragraphs=True)


async def capture(context, state):
    text = (f"✍️ Digite sua resposta para o chamado #{state['ticket']}.\n"
            'Ao enviar a mensagem, ela será registrada no chamado.')
    return await screen(context, state, text, [('cancel', 'Cancelar resposta')], view='capture')


async def handle(context, raw_text, result, binding, state, payload):
    """Return a response, or None for an explicit transition back to the list."""
    from bot.ticket_consult import query_state_accessor, UNAVAILABLE
    view, op = state.get('view'), raw_text.strip().lower()
    if payload is not None:
        expected = {'detail', 'version'} | ({'draft'} if state.get('draft') else set())
        if (not isinstance(payload, dict) or set(payload) != expected
                or payload.get('version') != state.get('version')
                or not isinstance(payload.get('detail'), str)
                or state.get('draft') and payload.get('draft') != state['draft']):
            # No untrusted payload text can become a draft or send command.
            from bot.ticket_consult import card
            return card('Esse botão não é mais válido. Use as opções atuais ou atualize a lista.', '', [('8', 'Atualizar lista'), ('0', 'Menu principal')])
        op = payload['detail']
    # Every read/edit/send screen validates the ticket again, independently of list.
    try:
        await asyncio.to_thread(service.details, result.glpi_user_id, state['ticket'])
    except AccessDenied:
        await query_state_accessor.delete(context)
        from bot.ticket_consult import card
        return card(UNAVAILABLE, '', [('8', 'Atualizar'), ('0', 'Menu principal')])
    # Confirmation cards from the previous flow are deliberately inert. Their
    # payload can never trigger ReplySender after direct-send deployment.
    if view == 'confirm':
        return await screen(context, dict(state, draft=None),
            'Esse botão pertence ao fluxo antigo e não pode enviar uma resposta. Volte ao chamado e responda novamente.',
            [('4', 'Voltar ao chamado')], view='result')
    if view in {'capture', 'confirm'}:
        if payload is None and op == '/tentar-novamente':
            op = 'retry_view'
        if has_real_attachments(context.activity):
            return await screen(context, state,
                'Somente texto é aceito nesta resposta. A mensagem e o arquivo não foram enviados nem salvos.\n'
                'Remova o arquivo e envie o texto novamente, ou use /cancelar-resposta.',
                [('cancel', 'Cancelar resposta')])
        draft = None
        if state.get('draft'):
            draft = await asyncio.to_thread(reply_store.get_operation, state['draft'], binding, state['ticket'])
            if not draft or draft['state'] in {'expired', 'cancelled'} or draft['expires'] <= time.time():
                return await screen(context, dict(state, draft=None), 'O rascunho expirou. Volte ao chamado para escrever novamente.', [('4', 'Voltar ao chamado')], view='result')
        if draft and draft['state'] != 'ready':
            if draft['state'] == 'sent':
                return await screen(context, state, '✅ Resposta enviada!',
                                    [('1', 'Ver conversa'), ('4', 'Voltar ao chamado')], view='result')
            return await screen(context, state, UNCERTAIN,
                                [('1', 'Atualizar conversa'), ('3', 'Meus chamados')], view='uncertain')
        cancel = op == '/cancelar-resposta' or payload is not None and op == 'cancel'
        if cancel:
            if draft:
                await asyncio.to_thread(reply_store.cancel, state['draft'], binding, state['ticket'])
            return await details(context, result, binding, state)
        if view == 'capture':
            if op == 'retry_view':
                return await capture(context, state)
            if payload is not None and op != 'retry_send':
                return await capture(context, state)
            created_now = False
            if not draft:
                raw_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
                if not valid_reply(raw_text):
                    return await screen(context, state, f'Digite uma mensagem de 1 a {MAX_REPLY} caracteres. Ela não foi enviada.', [('cancel', 'Cancelar resposta')])
                activity_id = getattr(context.activity, 'id', None)
                if not isinstance(activity_id, str) or not activity_id.strip():
                    return await screen(context, state,
                        'Não consegui identificar esta mensagem com segurança. Ela não foi enviada. Tente novamente.',
                        [('cancel', 'Cancelar resposta')])
                operation, _ = await asyncio.to_thread(
                    reply_store.create_for_activity, binding, state['ticket'], raw_text, activity_id)
                state = dict(state, draft=operation)
                await query_state_accessor.set(context, state)
                created_now = True
            if not created_now and op != 'retry_send':
                return await screen(context, state,
                    'Sua resposta anterior foi preservada e ainda não foi enviada. Use Tentar novamente ou cancele a resposta.',
                    [('retry_send', 'Tentar novamente'), ('cancel', 'Cancelar resposta')], view='capture')
            outcome = await asyncio.to_thread(ReplySender(reply_store, service).send,
                                              state['draft'], binding, state['ticket'])
            if outcome == 'sent':
                return await screen(context, state, '✅ Resposta enviada!',
                                    [('1', 'Ver conversa'), ('4', 'Voltar ao chamado')], view='result')
            if outcome == 'retry':
                return await screen(context, state,
                    'Não consegui preparar o envio. Sua resposta foi preservada e não foi enviada.',
                    [('retry_send', 'Tentar novamente'), ('cancel', 'Cancelar resposta')], view='capture')
            if outcome == 'denied':
                await query_state_accessor.delete(context)
                from bot.ticket_consult import card
                return card(UNAVAILABLE, '', [('8', 'Atualizar lista'), ('0', 'Menu principal')])
            return await screen(context, state, UNCERTAIN,
                                [('1', 'Ver conversa'), ('4', 'Voltar ao chamado')], view='uncertain')
    if op in {'0', 'menu'}:
        from bot.cards import build_menu_activity
        from bot.ticket_consult import nav_state_accessor
        await query_state_accessor.delete(context)
        await nav_state_accessor.set(context, {'screen': 'menu'})
        return build_menu_activity('')
    if op == '3':
        for key in ('view', 'draft', 'ticket', 'part'):
            state.pop(key, None)
        await query_state_accessor.set(context, state)
        return None
    if op in {'1', '8'} and view != 'details':
        return await history(context, result, state)
    if op == '4':
        return await details(context, result, binding, state)
    if view == 'details':
        if op == '1':
            return await history(context, result, state)
        if op == '2':
            return await capture(context, state)
        if op in {'7', '9'}:
            return await details(context, result, binding, state, offset=state.get('part', 0) + (-1 if op == '7' else 1))
    if view == 'history' and op in {'7', '9'}:
        return await history(context, result, state, state.get('part', 0) + (-1 if op == '7' else 1))
    return await screen(context, state, 'Opção inválida.',
                        [('4', 'Voltar ao chamado'), ('3', 'Meus chamados'), ('0', 'Menu principal')])
