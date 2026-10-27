# testar_formularios_novo.py
"""
Script de teste automatizado ATUALIZADO para os formulários do bot.
Inclui o novo formulário FlexSmart e as novas questões de Manutenção e Cadastro.

Cobre:
- Validação de domínio e autorização
- Formulário FlexSmart (Liberação de Telas / Liberação Sistema / Outro)
- Formulário Manutenção (Equipamentos / Sistemas / Acessos)
- Formulário Cadastro (fluxos com equipamento existente/novo, VPN, M365, etc.)
- Comandos e tratamento de erros
"""

import asyncio
import json
from unittest.mock import Mock
from datetime import datetime
from config import logger
from bot.dialogs import DynamicFormProcessor
from bot.utils import UserNameFormatter
from bot.auth import UserAuthorization
from services.glpi_service import FormCreationResult


# ============================================================
# MOCKS
# ============================================================

class MockState:
    """Simula o UserState de forma simples."""

    def __init__(self):
        self._session = None

    async def get(self, turn_context, default_factory):
        if self._session is None:
            self._session = default_factory() if callable(default_factory) else default_factory
        return self._session

    async def set(self, turn_context, value):
        self._session = value

    async def delete(self, turn_context):
        self._session = None


class MockGLPI:
    """Simula o serviço GLPI para testes."""

    def __init__(self):
        self.chamados_criados = []
        self.usuarios_mock = {
            "João Silva": "joao.silva@compasi.com.br",
            "Maria Santos": "maria.santos@compasi.com.br",
            "Pedro Costa": "pedro.costa@systemup.inf.br",
            "Carlos Pereira": "carlos.pereira@compasi.com.br",
            "Ana Costa": "ana.costa@compasi.com.br",
            "Juliana Lima": "juliana.lima@compasi.com.br",
            "Usuario Externo": "usuario@gmail.com",
            "Teste User": "teste.user@compasi.com.br",
        }

    def create_form_answer(self, form_id, form_values, requester_email=None, attachments=None):
        self.chamados_criados.append({
            "form_id": form_id,
            "valores": form_values,
            "requester_email": requester_email,
            "attachments": attachments,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[MOCK] Chamado criado! Form ID: {form_id}")
        return FormCreationResult(True, formanswer_id=123, ticket_id=1035)

    def get_user_email(self, nome):
        email = self.usuarios_mock.get(nome)
        if email:
            logger.info(f"[MOCK GLPI] Email encontrado para {nome}: {email}")
            return email
        logger.warning(f"[MOCK GLPI] Usuário não encontrado: {nome}")
        return None


class MockTurnContext:
    """Simula o TurnContext com turn_state."""

    def __init__(self, user_name="João Silva"):
        self.user_name = user_name
        self.sent_messages = []
        self.turn_state = {}
        self.activity = Mock()
        self.activity.from_property = Mock()
        self.activity.from_property.name = user_name
        self.activity.from_property.id = "test_user"
        self.activity.text = ""
        self.user_email = None

    async def send_activity(self, message):
        self.sent_messages.append(message)
        print(f"\n🤖 BOT: {message}\n")
        return Mock()


# ============================================================
# TESTADOR
# ============================================================

class TestadorFormularios:
    """Testa todos os fluxos dos formulários e validação."""

    def __init__(self):
        self.mock_glpi = MockGLPI()
        self.mock_state = MockState()
        self.testes_passados = 0
        self.testes_falhados = 0
        self.falhas = []

        DynamicFormProcessor.glpi = self.mock_glpi
        DynamicFormProcessor.user_profile_accessor = self.mock_state

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _checar(self, condicao, descricao):
        if condicao:
            self.testes_passados += 1
            print(f"   ✅ {descricao}")
        else:
            self.testes_falhados += 1
            self.falhas.append(descricao)
            print(f"   ❌ {descricao}")

    def _checar_contem(self, texto, trecho, descricao):
        """Verifica se um trecho aparece na resposta do bot."""
        condicao = trecho.lower() in (texto or "").lower()
        self._checar(condicao, f"{descricao} (esperado conter: '{trecho}')")

    # ------------------------------------------------------------
    # VALIDAÇÃO DE DOMÍNIO
    # ------------------------------------------------------------

    async def testar_validacao_dominio(self):
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Validação de Domínio")
        print(f"{'='*60}")

        test_cases = [
            ("joao.silva@compasi.com.br", True, "Domínio permitido"),
            ("maria.santos@compasi.com.br", True, "Domínio permitido"),
            ("pedro.costa@systemup.inf.br", True, "Domínio permitido"),
            ("ana@systemup.inf.br", True, "Domínio permitido"),
            ("usuario@gmail.com", False, "Domínio NÃO permitido"),
            ("teste@hotmail.com", False, "Domínio NÃO permitido"),
            ("carlos@yahoo.com", False, "Domínio NÃO permitido"),
            ("", False, "Email vazio"),
            ("sem_arroba", False, "Email sem @"),
            ("@compasi.com.br", False, "Email sem usuário"),
        ]

        for email, esperado, descricao in test_cases:
            resultado = UserAuthorization.is_domain_allowed(email)
            status = "✅" if resultado == esperado else "❌"
            print(f"{status} {descricao}: {email or '(vazio)'} → {'PERMITIDO' if resultado else 'NEGADO'}")
            if resultado == esperado:
                self.testes_passados += 1
            else:
                self.testes_falhados += 1
                self.falhas.append(descricao)

    async def testar_extracao_dominio(self):
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Extração de Domínio")
        print(f"{'='*60}")

        test_cases = [
            ("joao.silva@compasi.com.br", "compasi.com.br"),
            ("maria@systemup.inf.br", "systemup.inf.br"),
            ("usuario@gmail.com", "gmail.com"),
            ("sem_arroba", None),
            ("", None),
            (None, None),
        ]

        for email, esperado in test_cases:
            resultado = UserAuthorization.extract_domain(email)
            status = "✅" if resultado == esperado else "❌"
            print(f"{status} Extrair domínio de '{email}': {resultado} (esperado: {esperado})")
            if resultado == esperado:
                self.testes_passados += 1
            else:
                self.testes_falhados += 1
                self.falhas.append(f"extract_domain({email})")

    async def testar_autorizacao_usuario(self):
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Autorização de Usuários")
        print(f"{'='*60}")

        email = self.mock_glpi.get_user_email("João Silva")
        is_autorizado = UserAuthorization.is_domain_allowed(email)
        print(f"✅ João Silva: {email} → {'AUTORIZADO' if is_autorizado else 'NEGADO'}")
        self._checar(is_autorizado, "João Silva autorizado")

        email = self.mock_glpi.get_user_email("Usuario Externo")
        is_autorizado = UserAuthorization.is_domain_allowed(email)
        print(f"❌ Usuario Externo: {email} → {'AUTORIZADO' if is_autorizado else 'NEGADO'}")
        self._checar(not is_autorizado, "Usuario Externo negado")

        email = self.mock_glpi.get_user_email("Não Existe")
        print(f"❌ Não Existe: {email} → NEGADO (não encontrado)")
        self._checar(email is None, "Usuário inexistente sem email")

    async def testar_mensagem_acesso_negado(self):
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Mensagem de Acesso Negado")
        print(f"{'='*60}")

        email = "usuario@gmail.com"
        is_autorizado, _, mensagem = UserAuthorization.validate_user_with_email(email)

        print(f"Email: {email}")
        print(f"Autorizado: {is_autorizado}")
        print(f"Mensagem: {mensagem}")

        self._checar(
            not is_autorizado and "Acesso negado" in mensagem,
            "Mensagem de acesso negado correta"
        )

    # ------------------------------------------------------------
    # SIMULAÇÃO DE CONVERSA
    # ------------------------------------------------------------

    async def simular_conversa(self, mensagens, nome_usuario, nome_teste, verificacoes=None):
        """
        Simula uma conversa completa.
        verificacoes: lista de (indice_mensagem, trecho_esperado, descricao)
        """
        print(f"\n{'='*60}")
        print(f"📝 TESTE: {nome_teste}")
        print(f"{'='*60}")

        turn_context = MockTurnContext(nome_usuario)
        respostas = []

        for i, mensagem in enumerate(mensagens, 1):
            print(f"\n{'─'*40}")
            print(f"👤 USUÁRIO ({i}/{len(mensagens)}): {mensagem}")
            print(f"{'─'*40}")

            turn_context.activity.text = mensagem

            try:
                resposta = await DynamicFormProcessor.process_user_message(
                    turn_context, mensagem, nome_usuario
                )
                respostas.append(resposta)
                await turn_context.send_activity(resposta)
            except Exception as e:
                print(f"❌ ERRO: {e}")
                import traceback
                traceback.print_exc()
                self.testes_falhados += 1
                self.falhas.append(f"{nome_teste}: exceção em '{mensagem}': {e}")
                return False

        # Verificações personalizadas por índice
        if verificacoes:
            for idx, trecho, descricao in verificacoes:
                if 0 <= idx < len(respostas):
                    self._checar_contem(respostas[idx], trecho, f"{nome_teste} → {descricao}")

        self.testes_passados += 1
        print(f"\n✅ TESTE CONCLUÍDO: {nome_teste}")
        return True

    # ============================================================
    # FLEXSMART
    # ============================================================

    async def testar_flexsmart_liberacao_telas(self):
        """FlexSmart → Liberação → Telas → Usuario Atual → ..."""
        mensagens = [
            "preciso liberar uma tela no flexsmart",   # aciona flexsmart
            "1",   # tipo_atendimento: Liberação
            "1",   # qual_liberacao: Telas
            "Tela de Vendas",     # qual_tela
            "1",   # liberacao_para_usuario: Usuario Atual
            "Preciso acessar o módulo de faturamento",  # descricao
            "1",   # canal_contato: Microsoft Teams
            "joao.silva@compasi.com.br",   # email_teams
            "2",   # urgencia: Média
        ]
        await self.simular_conversa(
            mensagens, "João Silva",
            "FlexSmart → Liberação de Telas (Usuario Atual)"
        )

    async def testar_flexsmart_liberacao_outros_usuario(self):
        """FlexSmart → Liberação → Outros → Outro Usuario."""
        mensagens = [
            "liberação de sistema no flex",
            "1",   # Liberação
            "2",   # qual_liberacao: Outros
            "Liberar módulo de relatórios",   # qual_liberacao_sistema
            "2",   # liberacao_para_usuario: Outro Usuario
            "Maria Santos",   # nome_usuario
            "Liberação para novo colaborador",   # descricao
            "2",   # canal_contato: WhatsApp
            "49 99999-8888",   # whatsapp
            "3",   # urgencia: Alta
        ]
        await self.simular_conversa(
            mensagens, "João Silva",
            "FlexSmart → Liberação Outros (Outro Usuário)"
        )

    async def testar_flexsmart_tipo_outro(self):
        """FlexSmart → Outro tipo de atendimento (pula condicionais de liberação)."""
        mensagens = [
            "problema no flex",   # aciona flexsmart
            "2",   # tipo_atendimento: Outro
            "Erro ao gerar relatório",   # descricao
            "3",   # canal_contato: OPA
            "1",   # urgencia: Baixa
        ]
        await self.simular_conversa(
            mensagens, "Maria Santos",
            "FlexSmart → Tipo Outro (sem liberação)"
        )

    # ============================================================
    # MANUTENÇÃO
    # ============================================================

    async def testar_manutencao_equipamentos(self):
        """Manutenção → Manutenção de Equipamentos."""
        mensagens = [
            "preciso de manutenção no meu computador",
            "1",   # tipo_solicitacao: Manutenção de Equipamentos
            "1",   # equipamento: Computador/Hardware
            "Está muito lento e travando",   # descricao
            "2",   # local_solicitacao: Matriz
            "2",   # canal_contato: Microsoft Teams
            "joao.silva@compasi.com.br",   # email_teams
            "2",   # urgencia: Média
        ]
        await self.simular_conversa(
            mensagens, "João Silva",
            "Manutenção → Equipamentos (Matriz, Teams)"
        )

    async def testar_manutencao_filial_whatsapp(self):
        """Manutenção → Equipamentos → Filial → WhatsApp."""
        mensagens = [
            "erro no sistema",
            "1",   # Manutenção de Equipamentos
            "4",   # equipamento: Sistemas/Softwares
            "Sistema travando ao abrir tela de cadastro",   # descricao
            "1",   # local_solicitacao: Filial
            "2",   # filial: Lages
            "1",   # canal_contato: WhatsApp
            "49 98888-7777",   # whatsapp
            "3",   # urgencia: Alta
        ]
        await self.simular_conversa(
            mensagens, "Pedro Costa",
            "Manutenção → Equipamentos (Filial Lages, WhatsApp)"
        )

    async def testar_manutencao_acessos(self):
        """Manutenção → Acessos."""
        mensagens = [
            "preciso de um acesso",
            "2",   # tipo_solicitacao: Manutenção de Acessos
            "4",   # equipamento: Sistemas/Softwares
            "Preciso de acesso ao sistema ERP",   # descricao
            "2",   # local: Matriz
            "3",   # canal_contato: OPA
            "1",   # urgencia: Baixa
        ]
        await self.simular_conversa(
            mensagens, "Ana Costa",
            "Manutenção → Acessos (Matriz, OPA)"
        )

    # ============================================================
    # CADASTRO
    # ============================================================

    async def testar_cadastro_completo_matriz(self):
        """Cadastro completo → Matriz → com equipamento existente."""
        mensagens = [
            "preciso cadastrar novo colaborador",
            "Maria Oliveira",   # nome_completo
            "1",   # tipo_unidade: Matriz
            "1",   # setor: Comercial Peças
            "Padrão",   # modelo_usuario
            "1",   # acesso_vpn: Sim
            "1",   # licenca_m365: Standard
            "1",   # acesso_flex: Sim
            "1",   # possui_equipamento: Sim
            "2",   # tipo_equipamento_existente: Notebook
            "1",   # ramal_corporativo: Sim
            "1",   # equipamento_necessario (multiple): Desktop
            "1",   # precisa_programa: Sim
            "Office, Teams",   # quais_programas
            "1",   # assinatura_email: Sim
            "Cadastro urgente",   # observacoes
            "1",   # canal_contato: WhatsApp
            "49 97777-1111",   # whatsapp
        ]
        await self.simular_conversa(
            mensagens, "Carlos Pereira",
            "Cadastro → Matriz + Equipamento Existente"
        )

    async def testar_cadastro_filial_sem_equipamento(self):
        """Cadastro completo → Filial → sem equipamento."""
        mensagens = [
            "novo funcionário",
            "José Santos",   # nome
            "2",   # tipo_unidade: Filial
            "3",   # filial: Videira
            "4",   # setor: Financeiro
            "Avançado",   # modelo
            "2",   # acesso_vpn: Não
            "2",   # licenca_m365: Basic
            "2",   # acesso_flex: Não
            "2",   # possui_equipamento: Não
            "2",   # ramal_corporativo: Não
            "2",   # equipamento_necessario: Notebook
            "2",   # precisa_programa: Não
            "2",   # assinatura_email: Não
            "",    # observacoes (opcional → vazio)
            "2",   # canal_contato: Microsoft Teams
            "jose.santos@compasi.com.br",   # email_teams
        ]
        await self.simular_conversa(
            mensagens, "Juliana Lima",
            "Cadastro → Filial + Sem Equipamento"
        )

    async def testar_cadastro_multiplos_programas(self):
        """Cadastro com múltiplos programas e equipamentos (multiple)."""
        mensagens = [
            "admissão de colaborador",
            "Pedro Alves",   # nome
            "1",   # Matriz
            "12",  # setor: Desenvolvimento e Implantações
            "Dev",   # modelo
            "1",   # VPN: Sim
            "1",   # M365: Standard
            "1",   # Flex: Sim
            "2",   # possui_equipamento: Não
            "1",   # ramal: Sim
            "1,2,3",   # equipamento_necessario (multiple): Desktop, Notebook, Celular
            "1",   # precisa_programa: Sim
            "VSCode, Docker, Git, Postman",   # quais_programas
            "1",   # assinatura: Sim
            "Ambiente de desenvolvimento completo",   # observacoes
            "3",   # canal_contato: OPA
        ]
        await self.simular_conversa(
            mensagens, "Ana Costa",
            "Cadastro → Múltiplos Programas e Equipamentos"
        )

    # ============================================================
    # COMANDOS E ERROS
    # ============================================================

    async def testar_comandos(self):
        comandos = [
            ("oi", "Saudação"),
            ("ajuda", "Ajuda"),
            ("status", "Status"),
            ("quem é você", "Sobre"),
            ("obrigado", "Agradecimento"),
            ("cancelar", "Cancelamento"),
        ]
        for comando, descricao in comandos:
            await self.simular_conversa(
                [comando], "Teste User",
                f"Comando: {descricao}"
            )

    async def testar_erros(self):
        await self.simular_conversa(
            ["asdfghjkl"], "Teste User",
            "Erro: Mensagem não reconhecida"
        )
        await self.simular_conversa(
            ["preciso de manutenção", "99"], "Teste User",
            "Erro: Opção inválida"
        )
        await self.simular_conversa(
            ["cancelar"], "Teste User",
            "Erro: Cancelamento sem sessão"
        )

    # ============================================================
    # RESUMO
    # ============================================================

    def mostrar_resumo(self):
        total = self.testes_passados + self.testes_falhados
        taxa = (self.testes_passados / total * 100) if total > 0 else 0

        print(f"\n{'='*60}")
        print(f"📊 RESUMO DOS TESTES")
        print(f"{'='*60}")
        print(f"✅ Testes passaram: {self.testes_passados}")
        print(f"❌ Testes falharam: {self.testes_falhados}")
        print(f"📈 Taxa de sucesso: {taxa:.1f}%")
        print(f"{'='*60}")

        if self.falhas:
            print(f"\n⚠️  Falhas registradas:")
            for f in self.falhas:
                print(f"   - {f}")

        if self.mock_glpi.chamados_criados:
            print(f"\n📋 Chamados criados no MOCK ({len(self.mock_glpi.chamados_criados)}):")
            for i, chamado in enumerate(self.mock_glpi.chamados_criados, 1):
                print(f"\n{i}. Form ID: {chamado['form_id']}")
                print(f"   Valores: {json.dumps(chamado['valores'], indent=2, ensure_ascii=False)}")

    # ============================================================
    # EXECUÇÃO
    # ============================================================

    async def executar_todos(self):
        print("🚀 INICIANDO TESTES AUTOMATIZADOS (NOVOS FORMULÁRIOS)...")
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # Validação
        await self.testar_validacao_dominio()
        await self.testar_extracao_dominio()
        await self.testar_autorizacao_usuario()
        await self.testar_mensagem_acesso_negado()

        # Comandos
        await self.testar_comandos()

        # FlexSmart (NOVO)
        await self.testar_flexsmart_liberacao_telas()
        await self.testar_flexsmart_liberacao_outros_usuario()
        await self.testar_flexsmart_tipo_outro()

        # Manutenção (ATUALIZADO)
        await self.testar_manutencao_equipamentos()
        await self.testar_manutencao_filial_whatsapp()
        await self.testar_manutencao_acessos()

        # Cadastro (ATUALIZADO)
        await self.testar_cadastro_completo_matriz()
        await self.testar_cadastro_filial_sem_equipamento()
        await self.testar_cadastro_multiplos_programas()

        # Erros
        await self.testar_erros()

        self.mostrar_resumo()


async def main():
    testador = TestadorFormularios()
    await testador.executar_todos()


if __name__ == "__main__":
    asyncio.run(main())
