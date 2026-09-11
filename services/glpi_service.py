# services/glpi_service.py
import requests
import json
from config import settings, logger


class GLPIService:
    # Campos do tipo 'urgency' do Formcreator não aceitam texto -- só
    # aceitam o número da escala padrão do GLPI (1 a 5). Esse mapa
    # converte o texto que vem do form.yaml pro número certo.
    _URGENCY_MAP = {
        "muito baixa": 1,
        "baixa": 2,
        "media": 3,
        "média": 3,
        "alta": 4,
        "muito alta": 5,
    }

    def __init__(self):
        self.url = settings.GLPI_URL.rstrip('/')
        self.app_token = settings.GLPI_APP_TOKEN
        self.user_token = settings.GLPI_USER_TOKEN
        self._bot_user_id_cache = None

    def _get_session(self):
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Authorization": f"user_token {self.user_token}"
        }
        try:
            res = requests.post(f"{self.url}/initSession", headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json().get("session_token")
            logger.error(f"Erro ao iniciar sessão GLPI: Status {res.status_code} - {res.text}")
            return None
        except Exception as e:
            logger.exception(f"Exceção na autenticação com GLPI: {e}")
            return None

    def _kill_session(self, session_token):
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": session_token
        }
        try:
            requests.get(f"{self.url}/killSession", headers=headers, timeout=5)
        except Exception as e:
            logger.warning(f"Erro ao fechar sessão GLPI: {e}")

    def find_user_id_by_email(self, email: str, headers: dict) -> int | None:
        """Busca o ID do usuário no GLPI pelo email."""
        if not email:
            return None

        try:
            # Método 1
            search_url = f"{self.url}/search/UserEmail"
            params = {
                "criteria[0][field]": "email",
                "criteria[0][searchtype]": "equals",
                "criteria[0][value]": email,
                "range": "0-1"
            }

            res = requests.get(search_url, headers=headers, params=params, timeout=10)

            if res.status_code == 200:
                emails_data = res.json()

                if isinstance(emails_data, list) and emails_data:
                    user_id = emails_data[0].get('users_id')
                    if user_id:
                        logger.info(f"✅ Usuário encontrado: ID={user_id}")
                        return user_id

            # Método 2
            search_url2 = f"{self.url}/UserEmail"
            params2 = {
                "searchText[email]": email,
                "range": "0-1"
            }

            res2 = requests.get(search_url2, headers=headers, params=params2, timeout=10)

            if res2.status_code in [200, 206]:
                emails_data2 = res2.json()

                if isinstance(emails_data2, list) and emails_data2:
                    user_id = emails_data2[0].get('users_id')
                    if user_id:
                        logger.info(f"✅ Usuário encontrado (método 2): ID={user_id}")
                        return user_id

            logger.warning(f"Usuário não encontrado pelo email: {email}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar usuário pelo email: {e}")
            return None

    def _get_bot_user_id(self, headers: dict) -> int:
        """
        Busca o ID do Bot Teams pelo nome/login.
        Usa cache para não buscar toda vez.
        """
        if self._bot_user_id_cache:
            return self._bot_user_id_cache

        try:
            users_url = f"{self.url}/User"
            params = {"range": "0-200"}

            res = requests.get(users_url, headers=headers, params=params, timeout=10)

            if res.status_code in [200, 206]:
                users = res.json()

                if isinstance(users, list):
                    for user in users:
                        name = str(user.get('name', '')).lower()
                        firstname = str(user.get('firstname', '')).lower()
                        realname = str(user.get('realname', '')).lower()

                        if ('bot' in name and 'teams' in name) or ('bot' in firstname and 'teams' in realname):
                            user_id = user.get('id')
                            logger.info(f"✅ Bot Teams encontrado: ID={user_id}, Name={user.get('name')}")
                            self._bot_user_id_cache = user_id
                            return user_id

            logger.warning("Bot Teams não encontrado pelo nome, usando ID 282")
            self._bot_user_id_cache = 282
            return 282

        except Exception as e:
            logger.error(f"Erro ao buscar bot: {e}")
            return 282

    def _get_form_questions(self, form_id: int, headers: dict) -> list[dict]:
        """Navega pelas seções do formulário para buscar perguntas."""
        questions = []
        try:
            res_sections = requests.get(
                f"{self.url}/PluginFormcreatorForm/{form_id}/PluginFormcreatorSection",
                headers=headers,
                params={"range": "0-100"},
                timeout=10
            )
            if res_sections.status_code != 200:
                return questions

            sections = res_sections.json()
            if not isinstance(sections, list):
                sections = [sections]

            for sec in sections:
                sec_id = sec.get("id")
                if not sec_id:
                    continue

                res_questions = requests.get(
                    f"{self.url}/PluginFormcreatorSection/{sec_id}/PluginFormcreatorQuestion",
                    headers=headers,
                    params={"range": "0-100"},
                    timeout=10
                )
                if res_questions.status_code == 200:
                    q_data = res_questions.json()
                    if not isinstance(q_data, list):
                        q_data = [q_data]
                    questions.extend(q_data)

        except Exception as e:
            logger.exception(f"Erro ao consultar perguntas do formulário {form_id}: {e}")

        return questions

    def _format_field_value(self, q_id: str, val):
        """Normaliza o valor antes de enviar."""
        if isinstance(val, list):
            return list(dict.fromkeys(val))
        return val

    def _format_urgency_value(self, val):
        """
        Converte o texto da opção (ex: 'Alta') pro número que o campo
        tipo 'urgency' do Formcreator realmente aceita (1 a 5), mas
        como STRING -- o Formcreator rejeita (ERROR_GLPI_ADD) se
        mandarmos int puro no JSON. Se já vier número/numérico,
        mantém como string também.
        """
        if val is None or val == "":
            return val

        val_str = str(val).strip()
        if val_str.isdigit():
            return val_str

        chave = val_str.lower()
        numero = self._URGENCY_MAP.get(chave)

        if numero is None:
            logger.warning(f"⚠️ Valor de urgência não reconhecido: '{val}', mantendo texto original")
            return val

        logger.info(f"🔁 Urgência convertida: '{val}' -> '{numero}'")
        return str(numero)

    def _get_real_ticket_id(self, formanswer_id: int, headers: dict) -> int | None:
        """
        Busca o ID do Ticket REAL vinculado ao FormAnswer.
        Usa o endpoint Item_Ticket.
        """
        try:
            item_ticket_url = f"{self.url}/PluginFormcreatorFormAnswer/{formanswer_id}/Item_Ticket"

            logger.info(f"🔍 Buscando Ticket real do FormAnswer {formanswer_id}...")

            res = requests.get(item_ticket_url, headers=headers, timeout=10)

            logger.info(f"Status: {res.status_code}")

            if res.status_code in [200, 206]:
                items = res.json()

                if isinstance(items, list) and items:
                    tickets_id = items[0].get('tickets_id')

                    if tickets_id:
                        logger.info(f"✅ Ticket REAL encontrado: ID={tickets_id}")
                        return tickets_id

                elif isinstance(items, dict):
                    tickets_id = items.get('tickets_id')

                    if tickets_id:
                        logger.info(f"✅ Ticket REAL encontrado: ID={tickets_id}")
                        return tickets_id

            logger.warning(f"Ticket real não encontrado para FormAnswer {formanswer_id}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar ticket real: {e}")
            return None

    def _add_requester_to_ticket(self, ticket_id: int, requester_id: int, headers: dict) -> bool:
        """Adiciona o requerente correto ao ticket."""
        try:
            ticket_user_url = f"{self.url}/Ticket/{ticket_id}/Ticket_User"

            payload = {
                "input": {
                    "tickets_id": int(ticket_id),
                    "users_id": int(requester_id),
                    "type": 1
                }
            }

            logger.info(f"➕ Adicionando requerente (ID={requester_id}) ao ticket {ticket_id}")

            res = requests.post(ticket_user_url, headers=headers, json=payload, timeout=10)

            logger.info(f"Status: {res.status_code}")

            if res.status_code in [200, 201]:
                logger.info(f"✅ Requerente adicionado!")
                return True
            else:
                logger.warning(f"⚠️ Erro ao adicionar: {res.status_code}")
                return False

        except Exception as e:
            logger.error(f"Erro ao adicionar requerente: {e}")
            return False

    def _remove_bot_actors(self, ticket_id: int, headers: dict) -> bool:
        """
        Remove APENAS os atores do Bot Teams.
        Mantém outros atores.
        """
        try:
            bot_user_id = self._get_bot_user_id(headers)

            list_url = f"{self.url}/Ticket/{ticket_id}/Ticket_User"

            logger.info(f"📋 Listando atores do ticket {ticket_id}...")

            res = requests.get(list_url, headers=headers, timeout=10)

            if res.status_code not in [200, 206]:
                logger.warning(f"Erro ao listar: {res.status_code}")
                return False

            actors = res.json()
            logger.info(f"Atores: {json.dumps(actors, ensure_ascii=False, default=str)}")

            bot_actor_ids = []

            if isinstance(actors, list):
                for actor in actors:
                    if isinstance(actor, dict):
                        actor_id = actor.get('id')
                        actor_user_id = actor.get('users_id')
                        actor_type = actor.get('type')

                        if actor_user_id == bot_user_id:
                            bot_actor_ids.append(actor_id)
                            logger.info(f"🔍 Bot Teams: Actor ID={actor_id}, Type={actor_type}")

            for actor_id in bot_actor_ids:
                delete_url = f"{self.url}/Ticket/{ticket_id}/Ticket_User/{actor_id}"

                logger.info(f"🗑️ Removendo Bot Teams (Actor ID={actor_id})...")

                del_res = requests.delete(delete_url, headers=headers, timeout=10)

                logger.info(f"Status: {del_res.status_code}")

                if del_res.status_code in [200, 201]:
                    logger.info(f"✅ Bot Teams removido!")

            return len(bot_actor_ids) > 0

        except Exception as e:
            logger.error(f"Erro ao remover Bot Teams: {e}")
            return False

    def _add_teams_note(self, ticket_id: int, headers: dict) -> bool:
        """
        Adiciona uma nota simples no ticket informando que foi aberto pelo Teams.
        """
        try:
            followup_url = f"{self.url}/ITILFollowup"

            content = "🤖 Chamado aberto pelo Teams - Otto Bot de Chamados"

            payload = {
                "input": {
                    "itemtype": "Ticket",
                    "items_id": int(ticket_id),
                    "content": content,
                    "is_private": 0
                }
            }

            logger.info(f"📝 Adicionando nota ao ticket {ticket_id}...")

            res = requests.post(followup_url, headers=headers, json=payload, timeout=10)

            logger.info(f"Status: {res.status_code}")
            logger.info(f"Resposta: {res.text[:200]}")

            if res.status_code in [200, 201]:
                logger.info(f"✅ Nota adicionada!")
                return True
            else:
                logger.warning(f"⚠️ Erro ao adicionar nota: {res.status_code}")
                return False

        except Exception as e:
            logger.error(f"Erro ao adicionar nota: {e}")
            return False

    # -----------------------------------------------------------------
    # Anexos - subir documento solto e vincular a um ticket
    # -----------------------------------------------------------------
    def upload_document(self, filename: str, file_bytes: bytes, headers: dict) -> int | None:
        """
        Sobe um arquivo pro GLPI como Document solto (ainda sem vínculo).
        Retorna o ID do Document criado, ou None se falhar.
        """
        upload_manifest = {
            "input": {
                "name": filename,
                "_filename": [filename],
            }
        }

        # Para multipart, o Content-Type precisa sair do header -- o requests
        # define o multipart/form-data + boundary sozinho quando usamos files=
        upload_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}

        files = {
            "uploadManifest": (None, json.dumps(upload_manifest), "application/json"),
            "filename[0]": (filename, file_bytes),
        }

        try:
            res = requests.post(f"{self.url}/Document", headers=upload_headers, files=files, timeout=30)

            if res.status_code in (200, 201):
                doc_id = res.json().get("id")
                logger.info(f"✅ Documento enviado ao GLPI: '{filename}' (ID={doc_id})")
                return doc_id

            logger.error(f"Erro ao enviar documento '{filename}': {res.status_code} - {res.text}")
            return None

        except Exception as e:
            logger.exception(f"Exceção ao enviar documento '{filename}': {e}")
            return None

    def link_document_to_ticket(self, doc_id: int, ticket_id: int, headers: dict) -> bool:
        """Vincula um Document já existente a um Ticket."""
        try:
            payload = {
                "input": {
                    "documents_id": int(doc_id),
                    "itemtype": "Ticket",
                    "items_id": int(ticket_id),
                }
            }
            res = requests.post(f"{self.url}/Document_Item", headers=headers, json=payload, timeout=10)

            if res.status_code in (200, 201):
                logger.info(f"✅ Documento {doc_id} vinculado ao ticket {ticket_id}")
                return True

            logger.warning(f"Erro ao vincular documento {doc_id} ao ticket {ticket_id}: {res.status_code} - {res.text}")
            return False

        except Exception as e:
            logger.error(f"Erro ao vincular documento {doc_id}: {e}")
            return False

    def create_form_answer(
        self,
        form_id: int,
        form_values: dict,
        requester_email: str = None,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> tuple[bool, str]:
        """
        Cria o chamado, adiciona o requerente correto, remove o Bot Teams e,
        se houver anexos, sobe cada um e vincula ao ticket DEPOIS que ele
        já existe de verdade (evita o campo nativo 'file' do Formcreator,
        que costuma dar ERROR_GLPI_ADD).
        """
        session_token = self._get_session()
        if not session_token:
            return False, "Falha na autenticação com a API do GLPI."

        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": session_token
        }

        try:
            # 1. Busca o ID do requerente
            requester_id = None
            if requester_email:
                requester_id = self.find_user_id_by_email(requester_email, headers)
                if requester_id:
                    logger.info(f"✅ Requerente: ID={requester_id} ({requester_email})")

            # 2. Busca perguntas do formulário
            all_questions = self._get_form_questions(form_id, headers)
            normalized_values = {str(k): v for k, v in form_values.items()}

            # Mapa id -> fieldtype, usado para tratar campos especiais
            # (ex: 'urgency' precisa de número, não texto)
            q_type_by_id = {str(q.get("id")): q.get("fieldtype", "") for q in all_questions}

            for q in all_questions:
                q_id = str(q.get("id"))
                q_type = q.get("fieldtype", "")
                if q_type in ["text", "email", "textarea"] and q_id not in normalized_values:
                    normalized_values[q_id] = ""

            # 3. Monta payload (SEM anexo -- o campo nativo 'file' do
            # Formcreator não é usado; anexo é feito à parte, depois)
            fields_payload = {}
            for q_id, val in normalized_values.items():
                if q_type_by_id.get(q_id) == "urgency":
                    val = self._format_urgency_value(val)
                formatted_val = self._format_field_value(q_id, val)
                fields_payload[f"formcreator_field_{q_id}"] = formatted_val

            input_data = {
                "plugin_formcreator_forms_id": int(form_id),
                **fields_payload
            }

            payload = {"input": input_data}

            logger.info(f"Enviando Formanswer GLPI - Form ID {form_id}")

            # 4. Cria o FormAnswer
            res = requests.post(f"{self.url}/PluginFormcreatorFormanswer", headers=headers, json=payload, timeout=12)

            if res.status_code not in [200, 201]:
                logger.error(f"Erro GLPI Status {res.status_code}: {res.text}")
                return False, f"Erro ao criar no GLPI: {res.text}"

            logger.info(f"✅ FormAnswer criado!")

            # 5. Extrai o ID do FormAnswer
            formanswer_id = None

            try:
                if 'Location' in res.headers:
                    formanswer_id = res.headers['Location'].rstrip('/').split('/')[-1]
                else:
                    response_data = res.json()
                    if isinstance(response_data, dict):
                        formanswer_id = response_data.get('id')
                    elif isinstance(response_data, list) and response_data:
                        formanswer_id = response_data[0].get('id')

                logger.info(f"ID do FormAnswer: {formanswer_id}")
            except Exception as e:
                logger.warning(f"Não foi possível extrair ID: {e}")

            # 6. Busca o Ticket REAL
            created_ticket_id = None

            if formanswer_id:
                created_ticket_id = self._get_real_ticket_id(int(formanswer_id), headers)

            logger.info(f"Ticket REAL: {created_ticket_id}")

            # 7. Configura o requerente e remove o bot (não geram entrada na
            # timeline, então a ordem entre eles e o resto não importa)
            if created_ticket_id and requester_id:
                ticket_id_int = int(created_ticket_id)

                added = self._add_requester_to_ticket(ticket_id_int, requester_id, headers)
                if added:
                    logger.info(f"✅ Requerente adicionado: {requester_email}")

                removed = self._remove_bot_actors(ticket_id_int, headers)
                if removed:
                    logger.info(f"✅ Bot Teams removido")

            # 8. Sobe e vincula os anexos ANTES da nota -- assim o anexo fica
            # no topo da timeline e a nota "Chamado aberto pelo Teams" aparece
            # depois dele
            if created_ticket_id and attachments:
                ticket_id_int = int(created_ticket_id)
                logger.info(f"📎 Enviando {len(attachments)} anexo(s) ao ticket {ticket_id_int}...")

                for filename, file_bytes in attachments:
                    doc_id = self.upload_document(filename, file_bytes, headers)
                    if doc_id:
                        linked = self.link_document_to_ticket(doc_id, ticket_id_int, headers)
                        if linked:
                            logger.info(f"✅ Anexo '{filename}' vinculado ao ticket {ticket_id_int}")
                        else:
                            logger.warning(f"⚠️ Anexo '{filename}' subiu mas não vinculou ao ticket")
                    else:
                        logger.warning(f"⚠️ Falha ao subir anexo '{filename}' -- ticket já foi criado normalmente")

            # 9. Nota do Teams -- criada por último para aparecer depois do
            # anexo na timeline do ticket
            if created_ticket_id:
                ticket_id_int = int(created_ticket_id)
                noted = self._add_teams_note(ticket_id_int, headers)
                if noted:
                    logger.info(f"✅ Nota do Teams adicionada")

            return True, "Chamado registrado no GLPI com sucesso!"

        except Exception as e:
            logger.exception(f"Falha na comunicação: {e}")
            return False, f"Erro: {str(e)}"
        finally:
            self._kill_session(session_token)