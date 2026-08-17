# bot/dialogs.py
import json
import re
import traceback
from config import FORMS_CONFIG, logger
from services.glpi_service import GLPIService
from bot.state import user_profile_accessor
from bot.utils import UserNameFormatter
from bot.auth import UserAuthorization

glpi = GLPIService()


class DynamicFormProcessor:
    @staticmethod
    def identify_form(text_lower: str):
        """Identifica qual formulário usar baseado nas keywords do YAML."""
        logger.info(f"Tentando identificar formulário para: '{text_lower}'")
        
        for key, form in FORMS_CONFIG.items():
            keywords = form.get("keywords", [])
            
            for kw in keywords:
                if kw in text_lower:
                    logger.info(f"Match encontrado: form '{key}' com keyword '{kw}'")
                    return key, form
        
        logger.info("Nenhum formulário identificado")
        return None, None
    
    @staticmethod
    def format_question_prompt(question: dict, current_selected: list = None, user_name: str = None) -> str:
        """Monta o texto da pergunta."""
        label = question.get("label", "Pergunta")
        options = question.get("options", [])
        is_multiple = question.get("multiple", False)
        
        first_name = UserNameFormatter.extract_first_name(user_name)
        prefix = f"{first_name}, " if first_name and first_name != "Usuário" else ""
        
        # CAMPO DE TEXTO LIVRE
        if not options:
            return f"📌 **{prefix}{label}**\n\n*(Responda digitando o texto diretamente)*"
        
        # CAMPO DE OPÇÕES
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
        """Valida formato de email."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email.strip()) is not None
    
    @staticmethod
    def validate_and_normalize_answer(user_input: str, question: dict):
        """Valida e converte resposta do usuário."""
        options = question.get("options", [])
        label = question.get("label", "").lower()
        
        if not options:
            # Campo de texto livre
            if any(palavra in label for palavra in ["e-mail", "email", "teams"]):
                if not DynamicFormProcessor.validate_email(user_input):
                    return False, "⚠️ **Email inválido!** Por favor, digite um email válido (ex: nome.sobrenome@compasi.com.br)"
            
            return True, user_input.strip()
        
        clean_input = user_input.strip()
        
        # Seleção por NÚMERO
        if clean_input.isdigit():
            idx = int(clean_input) - 1
            if 0 <= idx < len(options):
                return True, options[idx]
        
        # Seleção por TEXTO
        for opt in options:
            if clean_input.lower() == opt.lower():
                return True, opt
        
        options_list_str = ", ".join([f"'{opt}'" for opt in options])
        return False, f"⚠️ Opção inválida! Escolha o número de **1 a {len(options)}** ou digite uma das opções: {options_list_str}."
    
    @classmethod
    def get_next_valid_question(cls, session: dict):
        """Retorna a próxima pergunta válida."""
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
        """Processa comandos especiais."""
        first_name = UserNameFormatter.extract_first_name(user_name)
        
        # COMANDOS DE SAUDAÇÃO
        if text_lower in ["oi", "ola", "olá", "hello", "hey", "eae", "eai", "opa", "bom dia", "boa tarde", "boa noite"]:
            return UserNameFormatter.format_greeting_with_emoji(user_name)
        
        # COMANDO DE AJUDA
        if text_lower in ["ajuda", "help", "?", "comandos", "menu", "socorro"]:
            return (
                f"📋 **Olá, {first_name}!** Aqui estão os comandos disponíveis:\n\n"
                f"**📝 Para abrir um chamado:**\n"
                f"• Digite **'manutenção'** ou descreva o problema (ex: 'erro impressora')\n"
                f"• Digite **'cadastro'** ou 'novo colaborador' *(restrito)*\n\n"
                f"**🛠️ Comandos:**\n"
                f"• **cancelar** - Cancela o atendimento atual\n"
                f"• **ajuda** - Mostra esta mensagem\n"
                f"• **status** - Informações sobre chamados\n"
                f"• **sobre** - Sobre o assistente\n\n"
                f"**📋 Formulários disponíveis:**\n"
                f"• Manutenção de Equipamentos *(todos)*\n"
                f"• Cadastro de Colaborador *(RH, TI, Gerência)*\n\n"
                f"---\n\n"
                f"💡 **Dica:** Descreva seu problema com palavras como:\n"
                f"• 'manutenção', 'impressora', 'computador'\n"
                f"• 'cadastro', 'novo colaborador'"
            )
        
        # COMANDO DE STATUS
        if text_lower in ["status", "status do chamado", "meus chamados", "chamados abertos"]:
            return (
                f"🔍 **{first_name}**, para verificar o status de um chamado:\n\n"
                f"• Acesse o **GLPI** diretamente\n"
                f"• Verifique seu **email** para atualizações\n"
                f"• Consulte o **portal de chamados** da empresa\n\n"
                f"Se precisar abrir um novo chamado, é só me dizer!"
            )
        
        # COMANDO DE AGRADECIMENTO
        if text_lower in ["obrigado", "obrigada", "valeu", "thanks", "thank you", "vlw", "brigado", "brigada"]:
            return (
                f"😊 **De nada, {first_name}!** Fico feliz em ajudar!\n\n"
                f"Se precisar de mais alguma coisa, é só chamar!"
            )
        
        # COMANDO SOBRE O BOT
        if text_lower in ["quem é você", "quem e voce", "sobre", "about", "o que você faz", "o que voce faz", "como funciona"]:
            return (
                f"🤖 **Olá, {first_name}!** Eu sou o **Byte Bot de Chamados**.\n\n"
                f"**O que posso fazer:**\n"
                f"• 📝 Abrir chamados de manutenção\n"
                f"• 👤 Cadastrar novos colaboradores *(restrito)*\n"
                f"• 🔧 Registrar problemas de equipamentos\n\n"
                f"**Como usar:**\n"
                f"• Descreva seu problema (ex: 'meu PC está lento')\n"
                f"• Responda às perguntas do formulário\n"
                f"• Pronto! Seu chamado será criado no GLPI\n\n"
                f"É só me dizer o que você precisa!"
            )
        
        # COMANDO DE CONTATO
        if text_lower in ["contato", "suporte", "falar com alguém", "falar com alguem", "humano", "pessoa"]:
            return (
                f"📞 **{first_name}**, se precisar falar com um atendente:\n\n"
                f"• **Email:** suporte@compasi.com.br\n"
                f"• **Horário:** Seg-Sex, 8h às 18h\n\n"
                f"Mas primeiro, posso tentar ajudar! O que você precisa?"
            )
        
        return None
    
    @classmethod
    async def process_user_message(cls, turn_context, user_text: str, user_name: str) -> str:
        try:
            text_clean = user_text.strip()
            text_lower = text_clean.lower()
            
            logger.info(f"Processando mensagem: '{text_clean}'")
            logger.info(f"Usuário: {user_name}")
            
            first_name = UserNameFormatter.extract_first_name(user_name)
            
            # Verifica comandos especiais primeiro
            special_response = await cls.handle_special_commands(turn_context, text_lower, user_name)
            if special_response:
                return special_response
            
            # Sessão do formulário
            session = await user_profile_accessor.get(turn_context, lambda: None)
            logger.info(f"Sessão existente: {session is not None}")
            
            # CANCELAMENTO
            if text_lower in ["cancelar", "sair", "parar", "abortar"]:
                if session:
                    await user_profile_accessor.delete(turn_context)
                    return f"❌ **{first_name}**, a abertura de chamado foi cancelada."
                return f"**{first_name}**, não há atendimento em andamento."
            
            # SESSÃO ATIVA
            if session:
                logger.info("Processando resposta em sessão ativa")
                current_q = cls.get_next_valid_question(session)
                
                if not current_q:
                    return await cls._finalize_session(turn_context, session, user_name)
                
                q_id = str(current_q["id"])
                is_multiple = current_q.get("multiple", False)
                
                # MÚLTIPLA ESCOLHA
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
                        
                        return await cls._finalize_session(turn_context, session, user_name)
                    
                    valido, item_selecionado = cls.validate_and_normalize_answer(text_clean, current_q)
                    if not valido:
                        return item_selecionado
                    
                    if item_selecionado not in current_list:
                        current_list.append(item_selecionado)
                    
                    session["answers"][q_id] = current_list
                    await user_profile_accessor.set(turn_context, session)
                    
                    return cls.format_question_prompt(current_q, current_list, user_name)
                
                # ESCOLHA ÚNICA OU TEXTO
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
                
                return await cls._finalize_session(turn_context, session, user_name)
            
            # INÍCIO DE CONVERSA
            logger.info("Iniciando identificação de formulário")
            form_key, form_config = cls.identify_form(text_lower)
            
            if not form_config:
                logger.warning(f"Formulário não identificado para: '{text_lower}'")
                return (
                    f"❌ **{first_name}**, não consegui identificar sua solicitação.\n\n"
                    f"**Tente descrever com palavras como:**\n"
                    f"• **manutenção**, **impressora**, **computador** para problemas\n"
                    f"• **cadastro**, **admissão** para novos colaboradores\n\n"
                    f"Ou digite **ajuda** para ver todos os comandos."
                )
            
            # ============================================================
            # VERIFICAÇÃO DE PERMISSÃO PARA CADASTRO
            # ============================================================
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
                        f"Se você acredita que isso é um erro, contate o suporte de TI.\n\n"
                        f"Você ainda pode abrir chamados de **manutenção** normalmente!"
                    )
            
            # MONTAGEM DA FILA
            logger.info(f"Formulário identificado: {form_key}")
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
                        "multiple": rules.get("multiple", False)
                    })
                else:
                    initial_answers[q_id] = rules.get("default", "")
            
            new_session = {
                "form_key": form_key,
                "form_id": form_id,
                "form_name": form_name,
                "answers": initial_answers,
                "pending_questions": pending_questions
            }
            await user_profile_accessor.set(turn_context, new_session)
            
            first_q = cls.get_next_valid_question(new_session)
            if first_q:
                first_is_mult = first_q.get("multiple", False)
                first_q_id = str(first_q["id"])
                first_selected = new_session["answers"].get(first_q_id, []) if first_is_mult else None
                await user_profile_accessor.set(turn_context, new_session)
                prompt = cls.format_question_prompt(first_q, first_selected, user_name)
                return (
                    f"✅ **Perfeito, {first_name}!** Identifiquei a solicitação: **{form_name}**.\n\n"
                    f"{prompt}"
                )
            
            return await cls._finalize_session(turn_context, new_session, user_name)
            
        except Exception as e:
            logger.error(f"Erro em process_user_message: {e}")
            logger.error(traceback.format_exc())
            
            # Retorna mensagem amigável em vez de erro técnico
            first_name = UserNameFormatter.extract_first_name(user_name)
            return (
                f"⚠️ **{first_name}, ocorreu um erro ao processar sua mensagem.**\n\n"
                f"Tente novamente ou digite **'cancelar'** para reiniciar.\n"
                f"Se o problema persistir, contate o suporte de TI."
            )
    
    @classmethod
    async def _finalize_session(cls, turn_context, session: dict, user_name: str) -> str:
        """Encerra a sessão e grava no GLPI."""
        try:
            await user_profile_accessor.delete(turn_context)
            
            form_id = session["form_id"]
            form_name = session["form_name"]
            final_answers = session["answers"]
            
            first_name = UserNameFormatter.extract_first_name(user_name)
            
            logger.info(f"Finalizando formulário {form_id} para {user_name}")
            logger.info(f"Respostas: {json.dumps(final_answers, ensure_ascii=False)}")
            
            await turn_context.send_activity(
                f"⏳ **{first_name}**, estou processando sua solicitação..."
            )
            
            # Tenta criar o chamado no GLPI
            try:
                success, msg = glpi.create_form_answer(form_id, final_answers)
            except TimeoutError:
                logger.error("Timeout ao criar chamado no GLPI")
                return (
                    f"⚠️ **{first_name}, o GLPI demorou muito para responder.**\n\n"
                    f"Sua solicitação pode não ter sido registrada.\n"
                    f"Tente novamente em alguns instantes ou contate o suporte de TI."
                )
            except Exception as glpi_error:
                logger.error(f"Erro no GLPI: {glpi_error}")
                return (
                    f"⚠️ **{first_name}, erro ao criar o chamado no GLPI.**\n\n"
                    f"Detalhes: {str(glpi_error)[:200]}\n\n"
                    f"Tente novamente ou contate o suporte de TI."
                )
            
            if success:
                return (
                    f"✅ **Sucesso, {first_name}!** Seu chamado foi gerado no GLPI "
                    f"usando o formulário **{form_name}**.\n\n"
                    f"Você receberá atualizações por email."
                )
            else:
                return (
                    f"❌ **{first_name}, ocorreu um erro ao criar o chamado no GLPI:**\n"
                    f"{msg}\n\n"
                    f"Por favor, tente novamente ou contate o suporte de TI."
                )
        except Exception as e:
            logger.error(f"Erro ao finalizar sessão: {e}")
            logger.error(traceback.format_exc())
            
            first_name = UserNameFormatter.extract_first_name(user_name)
            return (
                f"⚠️ **{first_name}, ocorreu um erro ao finalizar o atendimento.**\n\n"
                f"Tente novamente ou contate o suporte de TI."
            )