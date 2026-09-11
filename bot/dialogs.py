import json
import re
import base64
import traceback
from config import FORMS_CONFIG, logger
from services.glpi_service import GLPIService
from bot.state import user_profile_accessor
from bot.utils import UserNameFormatter
from bot.auth import UserAuthorization
from bot.attachments import TeamsAttachmentHandler

glpi = GLPIService()

_YES_WORDS = {"sim", "s", "quero", "yes", "claro", "ok", "quero sim"}
_NO_WORDS = {"não", "nao", "n", "não quero", "nao quero", "no", "sem anexo"}
_DONE_WORDS = {"concluir", "pronto", "finalizar", "não tenho mais", "nao tenho mais", "acabei", "é só isso", "e so isso"}
_CONFIRM_WORDS = {"sim", "s", "continuar", "ok", "pode continuar", "1"}

_ASK_ATTACHMENT_MSG = (
    "📎 **{first_name}**, antes de finalizar: deseja anexar algum **arquivo** "
    "a este chamado (print, foto, pdf, etc.)?\n\n"
    "Responda **'sim'** ou **'não'**."
)

_COLLECT_ATTACHMENT_MSG = (
    "📎 **{first_name}**, agora ficou ainda mais fácil: você pode colar o arquivo direto no chat "
    "(Ctrl+V) ou clicar no ícone de anexo (clipe) aqui embaixo para selecionar.\n\n"
    "Pode enviar quantos precisar! Quando terminar de mandar tudo, é só digitar **'concluir'**."
)

FLEXSMART_WARNING = (
    "🛑 ATENÇÃO: O atendimento para o FlexSmart mudou! Utilize o formulário "
    "\"Solicitações sistema FlexSmart\" no menu principal. Chamados de FlexSmart "
    "abertos por este formulário serão cancelados automaticamente a partir do dia 01/10."
)


class DynamicFormProcessor:
    @staticmethod
    def identify_form(text_lower: str):
        logger.info(f"Tentando identificar formulário para: '{text_lower}'")
        for key, form in FORMS_CONFIG.items():
            for kw in form.get("keywords", []):
                if kw in text_lower:
                    logger.info(f"Match encontrado: form '{key}' com keyword '{kw}'")
                    return key, form
        logger.info("Nenhum formulário identificado")
        return None, None

    @staticmethod
    def format_question_prompt(question: dict, current_selected: list = None, user_name: str = None) -> str:
        label = question.get("label", "Pergunta")
        options = question.get("options", [])
        is_multiple = question.get("multiple", False)
        first_name = UserNameFormatter.extract_first_name(user_name)
        prefix = f"{first_name}, " if first_name and first_name != "Usuário" else ""
        if not options:
            return f"📌 **{prefix}{label}**\n\n*(Responda digitando o texto diretamente)*"
        options_text = "\n".join([f"**{i+1}** - {opt}" for i, opt in enumerate(options)])
        prompt = f"📌 **{prefix}{label}**\n\n{options_text}"
        if is_multiple:
            if current_selected:
                selected_str = ", ".join([f"**{item}**" for item in current_selected])
                prompt += f"\n\n🛒 **Itens selecionados até agora:** {selected_str}"
                prompt += "\n\n*(Digite o número de mais um item para adicionar ou digite **'Continuar'** para avançar)*"
            else:
                prompt += "\n\n*(Digite o número/nome da opção ou digite **'Continuar'** para avançar)*"
        else:
            prompt += "\n\n*(Digite o número ou o nome da opção)*"
        return prompt

    @staticmethod
    def validate_email(email: str) -> bool:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email.strip()) is not None

    @staticmethod
    def validate_and_normalize_answer(user_input: str, question: dict):
        options = question.get("options", [])
        label = question.get("label", "").lower()
        if not options:
            if any(palavra in label for palavra in ["e-mail", "email", "teams"]):
                if not DynamicFormProcessor.validate_email(user_input):
                    return False, "⚠️ **Email inválido!** Por favor, digite um email válido (ex: nome.sobrenome@compasi.com.br)"
            return True, user_input.strip()
        clean_input = user_input.strip()
        if clean_input.isdigit():
            idx = int(clean_input) - 1
            if 0 <= idx < len(options):
                return True, options[idx]
        for opt in options:
            if clean_input.lower() == opt.lower():
                return True, opt
        options_list_str = ", ".join([f"'{opt}'" for opt in options])
        return False, f"⚠️ Opção inválida! Escolha o número de **1 a {len(options)}** ou digite uma das opções: {options_list_str}."

    @classmethod
    def get_next_valid_question(cls, session: dict):
        while session.get("pending_questions"):
            candidate_q = session["pending_questions"][0]
            depends_on = candidate_q.get("depends_on")
            if depends_on:
                target_field = depends_on.get("field")
                required_value = depends_on.get("value")
                form_config = FORMS_CONFIG.get(session["form_key"], {})
                questions_dict = form_config.get("questions", {})
                parent_q_config = questions_dict.get(target_field, {})
                parent_q_id = str(parent_q_config.get("id")) if parent_q_config else None
                actual_value = session["answers"].get(parent_q_id) if parent_q_id else None
                if actual_value != required_value:
                    skipped_q = session["pending_questions"].pop(0)
                    q_id = str(skipped_q["id"])
                    options = skipped_q.get("options", [])
                    default_val = options[0] if options else "N/A"
                    session["answers"][q_id] = default_val
                    continue
            return candidate_q
        return None

    @classmethod
    async def handle_special_commands(cls, turn_context, text_lower: str, user_name: str):
        first_name = UserNameFormatter.extract_first_name(user_name)
        if text_lower in ["oi", "ola", "olá", "hello", "hey", "eae", "eai", "opa", "bom dia", "boa tarde", "boa noite"]:
            return UserNameFormatter.format_greeting_with_emoji(user_name)
        if text_lower in ["ajuda", "help", "?", "comandos", "menu", "socorro"]:
            return (
                f"📋 **Olá, {first_name}!** Aqui estão os comandos disponíveis:\n\n"
                f"**📝 Para abrir um chamado:**\n"
                f"• Digite **'manutenção'** ou descreva o problema (ex: 'erro impressora')\n"
                f"• Digite **'cadastro'** ou 'novo colaborador' *(restrito)*\n"
                f"• Digite **'FlexSmart'** para problemas no sistema FlexSmart\n\n"
                f"**🛠️ Comandos:**\n"
                f"• **cancelar** - Cancela o atendimento atual\n"
                f"• **ajuda** - Mostra esta mensagem\n"
                f"• **status** - Informações sobre chamados\n"
                f"• **sobre** - Sobre o assistente\n\n"
                f"**📋 Formulários disponíveis:**\n"
                f"• Manutenção de Equipamentos *(todos)*\n"
                f"• Cadastro de Colaborador *(RH, TI, Gerência)*\n"
                f"• Sistema FlexSmart *(todos)*\n\n"
                f"---\n\n"
                f"💡 **Dica:** Descreva seu problema com palavras como:\n"
                f"• 'manutenção', 'impressora', 'computador'\n"
                f"• 'cadastro', 'novo colaborador'\n"
                f"• 'FlexSmart', 'erro flex'"
            )
        if text_lower in ["status", "status do chamado", "meus chamados", "chamados abertos"]:
            return (
                f"🔍 **{first_name}**, para verificar o status de um chamado:\n\n"
                f"• Acesse o **GLPI** diretamente\n"
                f"• Verifique seu **email** para atualizações\n"
                f"• Consulte o **portal de chamados** da empresa\n\n"
                f"Se precisar abrir um novo chamado, é só me dizer!"
            )
        if text_lower in ["obrigado", "obrigada", "valeu", "thanks", "thank you", "vlw", "brigado", "brigada"]:
            return (
                f"😊 **De nada, {first_name}!** Fico feliz em ajudar!\n\n"
                f"Se precisar de mais alguma coisa, é só chamar!"
            )
        if text_lower in ["quem é você", "quem e voce", "sobre", "about", "o que você faz", "o que voce faz", "como funciona"]:
            return (
                f"🤖 **Olá, {first_name}!** Eu sou o **Byte Bot de Chamados**.\n\n"
                f"**O que posso fazer:**\n"
                f"• 📝 Abrir chamados de manutenção\n"
                f"• 👤 Cadastrar novos colaboradores *(restrito)*\n"
                f"• 🔧 Registrar problemas do FlexSmart\n\n"
                f"**Como usar:**\n"
                f"• Descreva seu problema (ex: 'meu PC está lento', 'erro flex')\n"
                f"• Responda às perguntas do formulário\n"
                f"• Pronto! Seu chamado será criado no GLPI\n\n"
                f"É só me dizer o que você precisa!"
            )
        if text_lower in ["contato", "suporte", "falar com alguém", "falar com alguem", "humano", "pessoa"]:
            return (
                f"📞 **{first_name}**, se precisar falar com um atendente:\n\n"
                f"• **Email:** suporte@compasi.com.br\n"
                f"• **Horário:** Seg-Sex, 8h às 18h\n\n"
                f"Mas primeiro, posso tentar ajudar! O que você precisa?"
            )
        return None

    @classmethod
    def build_confirmation_message(cls, session: dict, user_name: str) -> str:
        first_name = UserNameFormatter.extract_first_name(user_name)
        current_name = session.get("form_name", "Formulário")
        current_key = session.get("form_key")

        outros = {k: v for k, v in FORMS_CONFIG.items() if k != current_key}

        msg = f"✅ Perfeito, {first_name}! Identifiquei a solicitação: **{current_name}**.\n\n"
        msg += "Isso está correto?\n\n"
        msg += "**1** - Sim, pode continuar\n"

        index = 2
        for key, form in outros.items():
            form_name = form.get("name", key)
            msg += f"**{index}** - Trocar para {form_name}\n"
            index += 1

        msg += "\n(Digite o número da opção)"
        return msg

    @classmethod
    async def start_form_questions(cls, turn_context, session: dict, user_name: str) -> str:
        form_key = session["form_key"]
        form_config = FORMS_CONFIG.get(form_key, {})
        form_id = form_config.get("id")
        form_name = form_config.get("name", f"ID {form_id}")

        initial_answers = {}
        pending_questions = []

        questions = form_config.get("questions", {})
        for field_name, rules in questions.items():
            q_id = str(rules.get("id"))
            if not q_id:
                continue
            if rules.get("use_user_name"):
                initial_answers[q_id] = user_name
            elif rules.get("required") is True or "default" not in rules:
                pending_questions.append({
                    "id": q_id,
                    "label": rules.get("label", f"Informe: {field_name}"),
                    "options": rules.get("options", []),
                    "depends_on": rules.get("depends_on"),
                    "multiple": rules.get("multiple", False),
                })
            else:
                initial_answers[q_id] = rules.get("default", "")

        session["form_id"] = form_id
        session["form_name"] = form_name
        session["answers"] = initial_answers
        session["pending_questions"] = pending_questions
        session["stage"] = "questions"
        session["pending_attachments"] = []
        await user_profile_accessor.set(turn_context, session)

        first_q = cls.get_next_valid_question(session)
        if first_q:
            first_is_mult = first_q.get("multiple", False)
            first_q_id = str(first_q["id"])
            first_selected = session["answers"].get(first_q_id, []) if first_is_mult else None
            prompt = cls.format_question_prompt(first_q, first_selected, user_name)
            return (
                f"✅ **Perfeito, {user_name}!** Identifiquei a solicitação: **{form_name}**.\n\n"
                f"{prompt}"
            )

        session["stage"] = "ask_attachment"
        await user_profile_accessor.set(turn_context, session)
        return _ASK_ATTACHMENT_MSG.format(first_name=UserNameFormatter.extract_first_name(user_name))

    @classmethod
    async def process_user_message(cls, turn_context, user_text: str, user_name: str) -> str:
        try:
            text_clean = user_text.strip()
            text_lower = text_clean.lower()
            logger.info(f"Processando mensagem: '{text_clean}'")
            logger.info(f"Usuário: {user_name}")
            first_name = UserNameFormatter.extract_first_name(user_name)

            special_response = await cls.handle_special_commands(turn_context, text_lower, user_name)
            if special_response:
                return special_response

            session = await user_profile_accessor.get(turn_context, lambda: None)

            if text_lower in ["cancelar", "sair", "parar", "abortar"]:
                if session:
                    await user_profile_accessor.delete(turn_context)
                    return f"❌ **{first_name}**, a abertura de chamado foi cancelada."
                return f"**{first_name}**, não há atendimento em andamento."

            if session:
                stage = session.get("stage", "questions")

                # Confirmação de formulário
                if stage == "confirm_form":
                    outros = {k: v for k, v in FORMS_CONFIG.items() if k != session.get("form_key")}
                    opcoes = list(outros.keys())

                    if text_lower in _CONFIRM_WORDS or text_clean == "1":
                        if session.get("form_key") == "cadastro":
                            user_email = getattr(turn_context, 'user_email', None)
                            if not user_email:
                                user_email = UserAuthorization.extract_email(turn_context.activity)
                            if not UserAuthorization.can_access_cadastro(user_email):
                                return (
                                    f"⛔ **Acesso negado.**\n\n"
                                    f"**{first_name}**, você não tem permissão para usar o formulário de **Cadastro de Colaborador**.\n\n"
                                    f"Escolha outro formulário ou contate o suporte de TI."
                                )
                        return await cls.start_form_questions(turn_context, session, user_name)

                    if text_clean.isdigit():
                        opcao = int(text_clean)
                        if 2 <= opcao <= 1 + len(opcoes):
                            novo_form_key = opcoes[opcao - 2]
                            novo_form = outros[novo_form_key]

                            if novo_form_key == "cadastro":
                                user_email = getattr(turn_context, 'user_email', None)
                                if not user_email:
                                    user_email = UserAuthorization.extract_email(turn_context.activity)
                                if not UserAuthorization.can_access_cadastro(user_email):
                                    return (
                                        f"⛔ **Acesso negado.**\n\n"
                                        f"**{first_name}**, você não tem permissão para usar o formulário de **Cadastro de Colaborador**.\n\n"
                                        f"Escolha outro formulário ou contate o suporte de TI."
                                    )

                            session["form_key"] = novo_form_key
                            await user_profile_accessor.set(turn_context, session)
                            return await cls.start_form_questions(turn_context, session, user_name)

                    confirm_msg = cls.build_confirmation_message(session, user_name)
                    return f"⚠️ Opção inválida. Escolha **1** para continuar ou digite o número do formulário desejado.\n\n{confirm_msg}"

                # Pergunta sobre anexos
                if stage == "ask_attachment":
                    if text_lower in _YES_WORDS:
                        session["stage"] = "collecting_attachments"
                        session["pending_attachments"] = []
                        await user_profile_accessor.set(turn_context, session)
                        return _COLLECT_ATTACHMENT_MSG.format(first_name=first_name)
                    elif text_lower in _NO_WORDS:
                        return await cls._finalize_session(turn_context, session, user_name)
                    else:
                        return (
                            f"⚠️ **{first_name}**, não entendi. Deseja anexar algum **arquivo** "
                            f"a este chamado? Responda **'sim'** ou **'não'**."
                        )

                # Coleta de anexos
                if stage == "collecting_attachments":
                    baixados = await TeamsAttachmentHandler.download_attachments(turn_context)
                    if baixados:
                        for filename, file_bytes in baixados:
                            session["pending_attachments"].append({
                                "filename": filename,
                                "content_b64": base64.b64encode(file_bytes).decode("ascii"),
                            })
                        await user_profile_accessor.set(turn_context, session)
                        qtd = len(session["pending_attachments"])
                        if text_lower in _DONE_WORDS:
                            return await cls._finalize_session(turn_context, session, user_name)
                        return (
                            f"✅ Arquivo recebido! ({qtd} até agora)\n\n"
                            f"Pode colar mais arquivos direto no chat (Ctrl+V) ou anexar pelo clipe📎. Se já enviou tudo, é só digitar **'concluir'**."
                        )
                    if text_lower in _DONE_WORDS:
                        return await cls._finalize_session(turn_context, session, user_name)
                    if not session.get("pending_attachments"):
                        return (
                            f"📎 **{first_name}**, ainda não recebi nenhum arquivo por aqui! "
                            f"Você pode colar a imagem direto no chat (Ctrl+V)"
                            f"ou clicar no ícone de anexo (clipe) para enviar, ou digite **'concluir'**"
                            f"para prosseguir sem anexo."
                        )
                    return (
                        f"⚠️ Ops,  **{first_name}**, isso não parece ser um arquivo válido!"
                        f"Tente colar o arquivo direto no chat (Ctrl+V) ou anexar pelo ícone de clipe 📎."
                        f"Se não tiver mais nada para enviar, é só digitar **'concluir'**."
                    )

                # Perguntas normais
                current_q = cls.get_next_valid_question(session)
                if not current_q:
                    session["stage"] = "ask_attachment"
                    await user_profile_accessor.set(turn_context, session)
                    return _ASK_ATTACHMENT_MSG.format(first_name=first_name)

                q_id = str(current_q["id"])
                is_multiple = current_q.get("multiple", False)

                # Aviso FlexSmart
                if current_q.get("id") == "104":
                    valido, resultado = cls.validate_and_normalize_answer(text_clean, current_q)
                    if not valido:
                        return resultado

                    session["answers"][q_id] = resultado
                    session["pending_questions"].pop(0)
                    await user_profile_accessor.set(turn_context, session)

                    aviso = ""
                    if resultado == "FlexSmart":
                        aviso = FLEXSMART_WARNING

                    next_q = cls.get_next_valid_question(session)

                    if next_q:
                        next_prompt = cls.format_question_prompt(next_q, None, user_name)
                        if aviso:
                            return f"{aviso}\n\n{next_prompt}"
                        else:
                            return next_prompt

                    session["stage"] = "ask_attachment"
                    await user_profile_accessor.set(turn_context, session)
                    if aviso:
                        return f"{aviso}\n\n{_ASK_ATTACHMENT_MSG.format(first_name=first_name)}"
                    else:
                        return _ASK_ATTACHMENT_MSG.format(first_name=first_name)

                # Múltipla escolha
                if is_multiple:
                    current_list = session["answers"].get(q_id, [])
                    if not isinstance(current_list, list):
                        current_list = []
                    if text_lower in ["continuar", "avançar", "avancar", "pronto", "ok", "finalizar", "concluir"]:
                        if not current_list:
                            return f"⚠️ **{first_name}**, selecione pelo menos 1 item!"
                        session["answers"][q_id] = current_list
                        session["pending_questions"].pop(0)
                        await user_profile_accessor.set(turn_context, session)
                        next_q = cls.get_next_valid_question(session)
                        if next_q:
                            next_is_mult = next_q.get("multiple", False)
                            next_q_id = str(next_q["id"])
                            next_selected = session["answers"].get(next_q_id, []) if next_is_mult else None
                            await user_profile_accessor.set(turn_context, session)
                            return cls.format_question_prompt(next_q, next_selected, user_name)
                        session["stage"] = "ask_attachment"
                        await user_profile_accessor.set(turn_context, session)
                        return _ASK_ATTACHMENT_MSG.format(first_name=first_name)
                    valido, item_selecionado = cls.validate_and_normalize_answer(text_clean, current_q)
                    if not valido:
                        return item_selecionado
                    if item_selecionado not in current_list:
                        current_list.append(item_selecionado)
                    session["answers"][q_id] = current_list
                    await user_profile_accessor.set(turn_context, session)
                    return cls.format_question_prompt(current_q, current_list, user_name)

                # Escolha única ou texto
                valido, resultado = cls.validate_and_normalize_answer(text_clean, current_q)
                if not valido:
                    return resultado
                session["answers"][q_id] = resultado
                session["pending_questions"].pop(0)
                next_q = cls.get_next_valid_question(session)
                if next_q:
                    next_is_mult = next_q.get("multiple", False)
                    next_q_id = str(next_q["id"])
                    next_selected = session["answers"].get(next_q_id, []) if next_is_mult else None
                    await user_profile_accessor.set(turn_context, session)
                    return cls.format_question_prompt(next_q, next_selected, user_name)
                session["stage"] = "ask_attachment"
                await user_profile_accessor.set(turn_context, session)
                return _ASK_ATTACHMENT_MSG.format(first_name=first_name)

            # Início de conversa
            form_key, form_config = cls.identify_form(text_lower)
            if not form_config:
                return (
                    f"❌ **{first_name}**, não consegui identificar sua solicitação.\n\n"
                    f"**Tente descrever com palavras como:**\n"
                    f"• **manutenção**, **impressora**, **computador** para problemas\n"
                    f"• **cadastro**, **admissão** para novos colaboradores\n"
                    f"• **FlexSmart**, **erro flex** para o sistema FlexSmart\n\n"
                    f"Ou digite **ajuda** para ver todos os comandos."
                )

            if form_key == "cadastro":
                user_email = getattr(turn_context, 'user_email', None)
                if not user_email:
                    user_email = UserAuthorization.extract_email(turn_context.activity)
                display_name = turn_context.activity.from_property.name if turn_context.activity else None
                if not UserAuthorization.can_access_cadastro(user_email, display_name):
                    logger.warning(f"⛔ Acesso NEGADO ao cadastro para: {user_email}")
                    return (
                        f"⛔ **Acesso negado.**\n\n"
                        f"**{first_name}**, você não tem permissão para usar o formulário de **Cadastro de Colaborador**.\n\n"
                        f"Este formulário é restrito aos seguintes grupos:\n"
                        f"• Recursos Humanos (RH)\n"
                        f"• TI\n"
                        f"• Gerência/Diretoria\n\n"
                        f"Você ainda pode abrir chamados de **manutenção** ou **FlexSmart** normalmente!"
                    )

            new_session = {
                "form_key": form_key,
                "form_id": form_config.get("id"),
                "form_name": form_config.get("name", f"ID {form_config.get('id')}"),
                "answers": {},
                "pending_questions": [],
                "stage": "confirm_form",
                "pending_attachments": [],
            }
            await user_profile_accessor.set(turn_context, new_session)

            return cls.build_confirmation_message(new_session, user_name)

        except Exception as e:
            logger.error(f"Erro em process_user_message: {e}")
            logger.error(traceback.format_exc())
            first_name = UserNameFormatter.extract_first_name(user_name)
            return (
                f"😅 **Opa, {first_name}, algo saiu diferente do esperado aqui.**\n\n"
                f"Tenta de novo, ou digite **'cancelar'** pra recomeçar do zero.\n\n"
                f"Se continuar acontecendo, chama o suporte de TI — eles resolvem rapidinho! 🙏"
            )

    @classmethod
    async def _finalize_session(cls, turn_context, session: dict, user_name: str) -> str:
        try:
            await user_profile_accessor.delete(turn_context)
            form_id = session["form_id"]
            form_name = session["form_name"]
            final_answers = session["answers"]
            first_name = UserNameFormatter.extract_first_name(user_name)
            user_email = getattr(turn_context, 'user_email', None)
            pending_attachments = session.get("pending_attachments", [])
            attachments_bytes = [
                (item["filename"], base64.b64decode(item["content_b64"]))
                for item in pending_attachments
            ]
            logger.info(f"Finalizando formulário {form_id} para {user_name}")
            logger.info(f"Email do requerente: {user_email}")
            logger.info(f"Respostas: {json.dumps(final_answers, ensure_ascii=False)}")
            logger.info(f"Anexos pendentes: {len(attachments_bytes)}")
            await turn_context.send_activity(
                f"⏳ **{first_name}**, estou processando sua solicitação..."
            )
            try:
                success, msg = glpi.create_form_answer(
                    form_id,
                    final_answers,
                    requester_email=user_email,
                    attachments=attachments_bytes,
                )
            except TimeoutError:
                return (
                    f"😅 **Calma, {first_name}, o sistema tá um pouco lento agora.**\n\n"
                    f"Fica tranquilo(a) que suas respostas não foram perdidas. Pode tentar de novo "
                    f"em alguns instantes, tá bem?\n\n"
                    f"Se continuar assim, chama o suporte de TI que eles resolvem rapidinho! 🙏"
                )
            except Exception as glpi_error:
                logger.error(f"Erro no GLPI: {glpi_error}")
                return (
                    f"😥 **Ih, {first_name}, deu um probleminha por aqui do nosso lado.**\n\n"
                    f"Já registrei o que aconteceu pra gente dar uma olhada. Você pode tentar "
                    f"novamente daqui a pouco?\n\n"
                    f"Se continuar dando erro, chama o suporte de TI — desculpa o transtorno! 🙏"
                )
            if success:
                anexo_info = f"\n\n📎 {len(attachments_bytes)} arquivo(s) anexado(s)." if attachments_bytes else ""
                return (
                    f"✅ **Sucesso, {first_name}!** Seu chamado foi gerado no GLPI "
                    f"usando o formulário **{form_name}**.{anexo_info}\n\n"
                    f"Você receberá atualizações por email."
                )
            else:
                logger.error(f"GLPI retornou falha: {msg}")
                return (
                    f"😕 **Poxa, {first_name}, não consegui registrar seu chamado agora.**\n\n"
                    f"Deve ser algo passageiro no sistema. Tenta de novo daqui a pouquinho?\n\n"
                    f"Se continuar acontecendo, é só chamar o suporte de TI. Desculpa o transtorno! 🙏"
                )
        except Exception as e:
            logger.error(f"Erro ao finalizar sessão: {e}")
            logger.error(traceback.format_exc())
            first_name = UserNameFormatter.extract_first_name(user_name)
            return (
                f"😅 **{first_name}, tive um probleminha aqui pra fechar seu atendimento.**\n\n"
                f"Pode tentar novamente? Se persistir, chama o suporte de TI que eles resolvem rápido. Desculpa! 🙏"
            )