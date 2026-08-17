import requests
from config import settings, logger
 
 
class GLPIService:
    def __init__(self):
        self.url = settings.GLPI_URL.rstrip('/')
        self.app_token = settings.GLPI_APP_TOKEN
        self.user_token = settings.GLPI_USER_TOKEN
 
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
 
    def _get_form_questions(self, form_id: int, headers: dict) -> list[dict]:
        """
        Navega pelas seções do formulário para buscar todas as perguntas cadastradas.
        Estrutura GLPI: Form -> Section -> Question
        """
        questions = []
        try:
            # 1. Busca as seções do formulário
            res_sections = requests.get(
                f"{self.url}/PluginFormcreatorForm/{form_id}/PluginFormcreatorSection",
                headers=headers,
                params={"range": "0-100"},
                timeout=10
            )
            if res_sections.status_code != 200:
                logger.warning(f"Não foi possível listar seções do form {form_id}: Status {res_sections.status_code}")
                return questions
 
            sections = res_sections.json()
            if not isinstance(sections, list):
                sections = [sections]
 
            # 2. Varre cada seção buscando suas perguntas
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
        """
        Normaliza o valor antes de enviar ao Formcreator.
 
        Os valores já chegam normalizados pelo DynamicFormProcessor (texto exato da
        opção do GLPI, ou lista de textos exatos para campos de múltipla escolha) -
        então aqui só garantimos que listas não tenham duplicatas (mantendo a ordem),
        sem depender de um mapa fixo por ID de campo, que ficaria desatualizado assim
        que as opções do formulário mudarem no GLPI.
        """
        if isinstance(val, list):
            return list(dict.fromkeys(val))
        return val
 
    def create_form_answer(self, form_id: int, form_values: dict, requester_id: int = None) -> tuple[bool, str]:
        session_token = self._get_session()
        if not session_token:
            return False, "Falha na autenticação com a API do GLPI."
 
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": session_token
        }
 
        try:
            # 1. Preenchimento defensivo automático para evitar erro no PHP (parseAnswerValues)
            all_questions = self._get_form_questions(form_id, headers)
 
            # Garante que as chaves em form_values sejam tratadas como string
            normalized_values = {str(k): v for k, v in form_values.items()}
 
            for q in all_questions:
                q_id = str(q.get("id"))
                q_type = q.get("fieldtype", "")
 
                # Se for campo de texto ou e-mail e NÃO foi enviado no dicionário, injeta string vazia
                if q_type in ["text", "email", "textarea"] and q_id not in normalized_values:
                    normalized_values[q_id] = ""
 
            # 2. Monta o payload FLAT esperado pelo Formcreator API
            fields_payload = {}
            for q_id, val in normalized_values.items():
                formatted_val = self._format_field_value(q_id, val)
                fields_payload[f"formcreator_field_{q_id}"] = formatted_val
 
            input_data = {
                "plugin_formcreator_forms_id": int(form_id),
                **fields_payload
            }
 
            if requester_id:
                input_data["_users_id_requester"] = int(requester_id)
 
            payload = {
                "input": input_data
            }
 
            logger.info(f"Enviando Formanswer GLPI - Form ID {form_id}")
            logger.debug(f"Payload final: {payload}")
 
            # 3. Dispara a criação
            res = requests.post(f"{self.url}/PluginFormcreatorFormanswer", headers=headers, json=payload, timeout=12)
 
            if res.status_code in [200, 201]:
                logger.info(f"Chamado GLPI criado com sucesso via Formcreator (Form ID: {form_id})")
                return True, "Chamado registrado no GLPI com sucesso!"
            else:
                logger.error(f"Erro GLPI Status {res.status_code}: {res.text}")
                return False, f"Erro ao criar no GLPI: {res.text}"
 
        except Exception as e:
            logger.exception(f"Falha na comunicação com o GLPI: {e}")
            return False, f"Erro de comunicação com o GLPI: {str(e)}"
        finally:
            self._kill_session(session_token)