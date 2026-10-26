"""Reading and reply screens. All caller selections come from current list state."""
import asyncio
import secrets
import time
from config import settings
from identity.replies import ReplyStore, MAX_REPLY, valid_reply
from services.ticket_conversation import TicketConversation, AccessDenied
from services.reply_sender import ReplySender
from services.ticket_content import passive, pages
from services.ticket_query import STATUS_LABELS

service = TicketConversation(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN)
reply_store = ReplyStore(settings.IDENTITY_DB_PATH)
UNCERTAIN = ('Não recebi a confirmação do envio. Sua mensagem pode ter sido registrada. '
             'Não vou reenviar automaticamente. Atualize a conversa para conferir.')


async def screen(context, state, text, actions, *, view=None):
    from bot.ticket_consult import card, query_state_accessor
    state = dict(state)
    if view:
        state['view'] = view
    state['version'] = secrets.token_urlsafe(16)
    # A read screen never extends a draft lifetime; SQLite checks its own deadline.
    state['expires'] = time.time() + 300
    await query_state_accessor.set(context, state)
    response = card(text, state['version'], actions)
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
    chunks = pages(row['content'])
    offset = min(max(0, offset), len(chunks) - 1)
    state['part'] = offset
    text = (f"🎫 Chamado #{tid} — {row['title'][:120]}\nSituação: {STATUS_LABELS[row['status']]}\n\n"
            f"📝 Solicitação inicial ({offset + 1}/{len(chunks)}):\n{chunks[offset]}\n\n"
            '1 — Ver conversa\n2 — Responder chamado\n3 — Voltar aos meus chamados\n0 — Menu principal')
    actions = [('1', 'Ver conversa'), ('2', 'Responder chamado'), ('3', 'Voltar aos meus chamados'), ('0', 'Menu principal')]
    if offset:
        actions.append(('7', 'Trecho anterior'))
        text += '\n7 — Trecho anterior'
    if offset + 1 < len(chunks):
        actions.append(('9', 'Ver mais'))
        text += '\n9 — Ver mais'
    return await screen(context, state, text, actions)


async def history(context, result, state, offset=0):
    messages = await asyncio.to_thread(service.history, result.glpi_user_id, state['ticket'])
    chunks = []
    for message in messages:
        parts = pages(message['content'])
        for i, part in enumerate(parts, 1):
            chunks.append(f"Autor: {message['author']}\nData: {message['date']} (horário do GLPI)\n"
                          f"Trecho {i}/{len(parts)}:\n{part}")
    offset = min(max(0, offset), max(0, len(chunks) - 1))
    text = (f"💬 Conversa pública do chamado #{state['ticket']}\nMais recentes primeiro.\n\n"
            + (f'Página {offset + 1}/{len(chunks)}\n' + chunks[offset] if chunks else 'Este chamado ainda não tem mensagens públicas.'))
    actions = [('4', 'Voltar ao chamado'), ('8', 'Atualizar conversa'), ('3', 'Meus chamados'), ('0', 'Menu principal')]
    text += '\n\n4 — Voltar ao chamado\n8 — Atualizar conversa\n3 — Meus chamados\n0 — Menu principal'
    if offset:
        text += '\n7 — Página anterior'
        actions.append(('7', 'Página anterior'))
    if offset + 1 < len(chunks):
        text += '\n9 — Mensagens anteriores / ver mais'
        actions.append(('9', 'Mensagens anteriores / ver mais'))
    return await screen(context, dict(state, part=offset), text, actions, view='history')


async def capture(context, state):
    text = (f"✍️ Digite a mensagem que deseja enviar ao chamado #{state['ticket']}.\n\n"
            f'Você poderá conferir antes de enviar. Somente texto, até {MAX_REPLY} caracteres.\n'
            'Para cancelar, use o botão ou digite /cancelar-resposta.\n'
            'Palavras e números digitados nesta tela serão parte da mensagem.')
    return await screen(context, state, text, [('cancel', 'Cancelar resposta e voltar ao chamado')], view='capture')


async def confirmation(context, state, body, prefix=''):
    text = (prefix + 'Confira sua mensagem:\n' + passive(body)
            + '\n\nA prévia oculta endereços e neutraliza formatação; o texto digitado será registrado integralmente.'
            + '\nDeseja enviar?\nDigite enviar, editar ou /cancelar-resposta.\n'
            'O autor nativo no GLPI será a conta da integração; o texto identificará a origem Teams.')
    return await screen(context, state, text,
                        [('send', 'Enviar'), ('edit', 'Editar'), ('cancel', 'Cancelar')], view='confirm')


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
        return card(UNAVAILABLE + '\n8 — Atualizar\n0 — Menu principal', '', [('8', 'Atualizar'), ('0', 'Menu principal')])
    if view in {'capture', 'confirm'}:
        if payload is None and op == '/tentar-novamente':
            op = 'retry_view'
        if getattr(context.activity, 'attachments', None):
            return await screen(context, state, 'Somente texto é aceito. Nenhum anexo foi enviado.\n'
                                'Digite /cancelar-resposta para voltar ao chamado.', [('cancel', 'Cancelar resposta')])
        draft = None
        if state.get('draft'):
            draft = await asyncio.to_thread(reply_store.get_operation, state['draft'], binding, state['ticket'])
            if not draft or draft['state'] in {'expired', 'cancelled'} or draft['expires'] <= time.time():
                return await screen(context, dict(state, draft=None), 'O rascunho expirou. Volte ao chamado para escrever novamente.\n4 — Voltar ao chamado', [('4', 'Voltar ao chamado')], view='result')
        if draft and draft['state'] != 'ready' and op not in {'send', 'enviar'}:
            if draft['state'] == 'sent':
                return await screen(context, state, f"✅ Sua mensagem foi enviada ao chamado #{state['ticket']}.\n1 — Atualizar conversa\n4 — Voltar ao chamado",
                                    [('1', 'Atualizar conversa'), ('4', 'Voltar ao chamado')], view='result')
            return await screen(context, state, UNCERTAIN + '\n1 — Atualizar conversa\n3 — Meus chamados',
                                [('1', 'Atualizar conversa'), ('3', 'Meus chamados')], view='uncertain')
        cancel = op == '/cancelar-resposta' or payload is not None and op == 'cancel'
        if cancel:
            if draft:
                await asyncio.to_thread(reply_store.cancel, state['draft'], binding, state['ticket'])
            return await details(context, result, binding, state)
        if view == 'capture':
            if payload is not None or op == 'retry_view':
                return await capture(context, state)
            raw_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
            if not valid_reply(raw_text):
                return await screen(context, state, f'Digite uma mensagem de 1 a {MAX_REPLY} caracteres. Ela não foi enviada.\n/cancelar-resposta — Cancelar', [('cancel', 'Cancelar')])
            operation = await asyncio.to_thread(reply_store.create, binding, state['ticket'], raw_text)
            return await confirmation(context, dict(state, draft=operation), raw_text)
        if not draft:
            raise ValueError('draft_missing')
        if op in {'send', 'enviar'}:
            outcome = await asyncio.to_thread(ReplySender(reply_store, service).send, state['draft'], binding, state['ticket'])
            if outcome == 'sent':
                return await screen(context, state, f"✅ Sua mensagem foi enviada ao chamado #{state['ticket']}.\n1 — Atualizar conversa\n4 — Voltar ao chamado\n0 — Menu principal",
                                    [('1', 'Atualizar conversa'), ('4', 'Voltar ao chamado'), ('0', 'Menu principal')], view='result')
            if outcome == 'retry':
                return await confirmation(context, state, draft['body'], 'Não consegui preparar o envio. Seu rascunho foi preservado.\n\n')
            if outcome == 'denied':
                await query_state_accessor.delete(context)
                from bot.ticket_consult import card
                return card(UNAVAILABLE, '', [('8', 'Atualizar lista'), ('0', 'Menu principal')])
            return await screen(context, state, UNCERTAIN + '\n1 — Atualizar conversa\n3 — Meus chamados\n0 — Menu principal',
                                [('1', 'Atualizar conversa'), ('3', 'Meus chamados'), ('0', 'Menu principal')], view='uncertain')
        if draft['state'] != 'ready':
            return await screen(context, state, UNCERTAIN + '\n1 — Atualizar conversa', [('1', 'Atualizar conversa')], view='uncertain')
        if op in {'edit', 'editar'}:
            await asyncio.to_thread(reply_store.cancel, state['draft'], binding, state['ticket'])
            return await capture(context, dict(state, draft=None))
        return await confirmation(context, state, draft['body'])
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
    return await screen(context, state, 'Opção inválida.\n4 — Voltar ao chamado\n3 — Meus chamados\n0 — Menu principal',
                        [('4', 'Voltar ao chamado'), ('3', 'Meus chamados'), ('0', 'Menu principal')])
