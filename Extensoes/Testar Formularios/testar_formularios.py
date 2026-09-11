# testar_formularios.py
"""
Script de teste automatizado para os formulários do bot.
Testa validação de domínio, autorização e todos os fluxos.
"""

import asyncio
import json
from unittest.mock import Mock
from datetime import datetime
from config import logger
from bot.dialogs import DynamicFormProcessor
from bot.utils import UserNameFormatter
from bot.auth import UserAuthorization


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
    
    def create_form_answer(self, form_id, form_values, requester_id=None):
        """Simula a criação de chamado no GLPI."""
        self.chamados_criados.append({
            "form_id": form_id,
            "valores": form_values,
            "requester_id": requester_id,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[MOCK] Chamado criado! Form ID: {form_id}")
        return True, "Chamado registrado no GLPI com sucesso!"
    
    def get_user_email(self, nome):
        """Simula a busca de email no GLPI."""
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
        self.turn_state = {}  # ADICIONADO
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


class TestadorFormularios:
    """Testa todos os fluxos dos formulários e validação."""
    
    def __init__(self):
        self.mock_glpi = MockGLPI()
        self.mock_state = MockState()
        self.testes_passados = 0
        self.testes_falhados = 0
        
        # Substitui os serviços reais pelos mocks
        DynamicFormProcessor.glpi = self.mock_glpi
        DynamicFormProcessor.user_profile_accessor = self.mock_state
    
    # ============================================================
    # TESTES DE VALIDAÇÃO DE DOMÍNIO
    # ============================================================
    
    async def testar_validacao_dominio(self):
        """Testa a validação de domínio de email."""
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
    
    async def testar_extracao_dominio(self):
        """Testa a extração de domínio."""
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
    
    async def testar_autorizacao_usuario(self):
        """Testa a autorização completa de usuários."""
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Autorização de Usuários")
        print(f"{'='*60}")
        
        # Usuário autorizado
        email = self.mock_glpi.get_user_email("João Silva")
        is_autorizado = UserAuthorization.is_domain_allowed(email)
        
        print(f"✅ João Silva: {email} → {'AUTORIZADO' if is_autorizado else 'NEGADO'}")
        if is_autorizado:
            self.testes_passados += 1
        else:
            self.testes_falhados += 1
        
        # Usuário NÃO autorizado (gmail)
        email = self.mock_glpi.get_user_email("Usuario Externo")
        is_autorizado = UserAuthorization.is_domain_allowed(email)
        
        print(f"❌ Usuario Externo: {email} → {'AUTORIZADO' if is_autorizado else 'NEGADO'}")
        if not is_autorizado:
            self.testes_passados += 1
        else:
            self.testes_falhados += 1
        
        # Usuário não encontrado
        email = self.mock_glpi.get_user_email("Não Existe")
        print(f"❌ Não Existe: {email} → NEGADO (não encontrado)")
        if email is None:
            self.testes_passados += 1
        else:
            self.testes_falhados += 1
    
    async def testar_mensagem_acesso_negado(self):
        """Testa a mensagem de acesso negado."""
        print(f"\n{'='*60}")
        print(f"📝 TESTE: Mensagem de Acesso Negado")
        print(f"{'='*60}")
        
        email = "usuario@gmail.com"
        
        is_autorizado, _, mensagem = UserAuthorization.validate_user_with_email(email)
        
        print(f"Email: {email}")
        print(f"Autorizado: {is_autorizado}")
        print(f"Mensagem: {mensagem}")
        
        if not is_autorizado and "Acesso negado" in mensagem:
            print("✅ Mensagem correta")
            self.testes_passados += 1
        else:
            print("❌ Mensagem incorreta")
            self.testes_falhados += 1
    
    # ============================================================
    # TESTES DE FORMULÁRIOS
    # ============================================================
    
    async def simular_conversa(self, mensagens, nome_usuario, nome_teste):
        """Simula uma conversa completa."""
        print(f"\n{'='*60}")
        print(f"📝 TESTE: {nome_teste}")
        print(f"{'='*60}")
        
        turn_context = MockTurnContext(nome_usuario)
        
        for i, mensagem in enumerate(mensagens, 1):
            print(f"\n{'─'*40}")
            print(f"👤 USUÁRIO ({i}/{len(mensagens)}): {mensagem}")
            print(f"{'─'*40}")
            
            turn_context.activity.text = mensagem
            
            try:
                resposta = await DynamicFormProcessor.process_user_message(
                    turn_context, mensagem, nome_usuario
                )
                
                await turn_context.send_activity(resposta)
                
            except Exception as e:
                print(f"❌ ERRO: {e}")
                import traceback
                traceback.print_exc()
                self.testes_falhados += 1
                return False
        
        self.testes_passados += 1
        print(f"\n✅ TESTE CONCLUÍDO!")
        return True
    
    async def testar_manutencao_completo(self):
        """Testa o formulário de manutenção completo."""
        mensagens = [
            "preciso de manutenção no meu PC",
            "1",
            "1",
            "1",
            "Meu computador está muito lento",
            "1",
            "joao.silva@compasi.com.br",
            "2",
        ]
        
        await self.simular_conversa(
            mensagens,
            "João Silva",
            "Manutenção - Fluxo Completo"
        )
    
    async def testar_manutencao_condicional(self):
        """Testa manutenção com campos condicionais."""
        mensagens = [
            "erro na impressora",
            "3",
            "1",
            "Impressora não imprime",
            "2",
            "49 99999-9999",
            "3",
        ]
        
        await self.simular_conversa(
            mensagens,
            "Maria Santos",
            "Manutenção - Condicional (Acessos + WhatsApp)"
        )
    
    async def testar_manutencao_filial(self):
        """Testa manutenção com filial."""
        mensagens = [
            "problema no computador",
            "1",
            "2",
            "2",
            "3",
            "Monitor não liga",
            "3",
            "1",
        ]
        
        await self.simular_conversa(
            mensagens,
            "Pedro Costa",
            "Manutenção - Filial"
        )
    
    async def testar_cadastro_completo(self):
        """Testa cadastro completo."""
        mensagens = [
            "preciso cadastrar novo colaborador",
            "Maria Oliveira",
            "1",
            "1",
            "Padrão",
            "1",
            "1",
            "1",
            "2",
            "1",
            "1",
            "continuar",
            "2",
            "1",
            "Teste de cadastro",
            "2",
            "maria.oliveira@compasi.com.br",
        ]
        
        await self.simular_conversa(
            mensagens,
            "Carlos Pereira",
            "Cadastro - Fluxo Completo"
        )
    
    async def testar_cadastro_multipla_escolha(self):
        """Testa cadastro com múltipla escolha."""
        mensagens = [
            "novo funcionário",
            "José Santos",
            "2",
            "3",
            "8",
            "Básico",
            "2",
            "1",
            "2",
            "1",
            "1",
            "2",
            "1",
            "2",
            "3",
            "continuar",
            "1",
            "Photoshop, AutoCAD",
            "2",
            "Cadastro urgente",
            "1",
            "49 98888-7777",
        ]
        
        await self.simular_conversa(
            mensagens,
            "Ana Costa",
            "Cadastro - Múltipla Escolha"
        )
    
    async def testar_cadastro_equipamento(self):
        """Testa cadastro com equipamento existente."""
        mensagens = [
            "cadastrar colaborador",
            "Pedro Alves",
            "1",
            "4",
            "Avançado",
            "1",
            "2",
            "1",
            "1",
            "2",
            "1",
            "2",
            "continuar",
            "1",
            "SAP, Excel",
            "1",
            "Cadastro financeiro",
            "3",
        ]
        
        await self.simular_conversa(
            mensagens,
            "Juliana Lima",
            "Cadastro - Equipamento Existente"
        )
    
    async def testar_comandos(self):
        """Testa comandos especiais."""
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
                [comando],
                "Teste User",
                f"Comando: {descricao}"
            )
    
    async def testar_erros(self):
        """Testa tratamento de erros."""
        await self.simular_conversa(
            ["asdfghjkl"],
            "Teste User",
            "Erro: Mensagem não reconhecida"
        )
        
        await self.simular_conversa(
            ["preciso de manutenção", "99"],
            "Teste User",
            "Erro: Opção inválida"
        )
        
        await self.simular_conversa(
            ["cancelar"],
            "Teste User",
            "Erro: Cancelamento sem sessão"
        )
    
    def mostrar_resumo(self):
        """Mostra o resumo dos testes."""
        total = self.testes_passados + self.testes_falhados
        taxa = (self.testes_passados / total * 100) if total > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO DOS TESTES")
        print(f"{'='*60}")
        print(f"✅ Testes passaram: {self.testes_passados}")
        print(f"❌ Testes falharam: {self.testes_falhados}")
        print(f"📈 Taxa de sucesso: {taxa:.1f}%")
        print(f"{'='*60}")
        
        if self.mock_glpi.chamados_criados:
            print(f"\n📋 Chamados criados no MOCK:")
            for i, chamado in enumerate(self.mock_glpi.chamados_criados, 1):
                print(f"\n{i}. Form ID: {chamado['form_id']}")
                print(f"   Valores: {json.dumps(chamado['valores'], indent=2, ensure_ascii=False)}")
    
    async def executar_todos(self):
        """Executa todos os testes."""
        print("🚀 INICIANDO TESTES AUTOMATIZADOS...")
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Testes de validação
        await self.testar_validacao_dominio()
        await self.testar_extracao_dominio()
        await self.testar_autorizacao_usuario()
        await self.testar_mensagem_acesso_negado()
        
        # Testes de comandos
        await self.testar_comandos()
        
        # Testes de manutenção
        await self.testar_manutencao_completo()
        await self.testar_manutencao_condicional()
        await self.testar_manutencao_filial()
        
        # Testes de cadastro
        await self.testar_cadastro_completo()
        await self.testar_cadastro_multipla_escolha()
        await self.testar_cadastro_equipamento()
        
        # Testes de erro
        await self.testar_erros()
        
        self.mostrar_resumo()


async def main():
    testador = TestadorFormularios()
    await testador.executar_todos()


if __name__ == "__main__":
    asyncio.run(main())