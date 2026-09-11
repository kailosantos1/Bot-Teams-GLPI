# testar_sistema_completo.py
"""
Script de teste automatizado do Byte Bot de Chamados.
Testa os fluxos sem enviar dados reais ao GLPI.
"""

import sys
import os

# Adiciona a raiz do projeto ao sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT_DIR)

# Define variáveis de ambiente dummy para evitar erro do pydantic-settings
os.environ.setdefault("GLPI_URL", "http://localhost")
os.environ.setdefault("GLPI_APP_TOKEN", "dummy_token")
os.environ.setdefault("GLPI_USER_TOKEN", "dummy_user_token")
os.environ.setdefault("MICROSOFT_APP_ID", "dummy_app_id")
os.environ.setdefault("MICROSOFT_APP_PASSWORD", "dummy_app_password")
os.environ.setdefault("MICROSOFT_APP_TENANT_ID", "dummy_tenant_id")

import asyncio
import json
import base64
from unittest.mock import Mock, patch

import bot.dialogs as dialogs
from bot.dialogs import DynamicFormProcessor
from bot.auth import UserAuthorization
from bot.attachments import TeamsAttachmentHandler


class MockUserState:
    def __init__(self):
        self._store = {}

    async def get(self, turn_context, default_factory):
        key = turn_context.activity.from_property.id
        if key not in self._store:
            self._store[key] = default_factory() if callable(default_factory) else default_factory
        return self._store[key]

    async def set(self, turn_context, value):
        key = turn_context.activity.from_property.id
        self._store[key] = value

    async def delete(self, turn_context):
        key = turn_context.activity.from_property.id
        self._store.pop(key, None)


class MockTurnContext:
    def __init__(self, user_name="Teste User", user_email="teste@compasi.com.br"):
        self.user_name = user_name
        self.user_email = user_email
        self.sent_messages = []
        self.activity = Mock()
        self.activity.from_property = Mock()
        self.activity.from_property.name = user_name
        self.activity.from_property.id = f"user_{user_name}"
        self.activity.text = ""
        self.activity.attachments = []
        self.turn_state = {}

    async def send_activity(self, message):
        if message:
            self.sent_messages.append(message)

    def set_attachment(self, filename, content_bytes, content_type="image/png"):
        att = Mock()
        att.name = filename
        att.content_type = content_type
        att.content_url = "https://example.com/fake_image.png"
        att.content = None
        self.activity.attachments = [att]
        self._attachment_bytes = content_bytes
        self._attachment_content_type = content_type


class MockGLPI:
    def __init__(self):
        self.created_tickets = []

    def create_form_answer(self, form_id, form_values, requester_email=None, attachments=None):
        self.created_tickets.append({
            "form_id": form_id,
            "values": form_values,
            "requester_email": requester_email,
            "attachments": attachments,
        })
        return True, "Chamado criado com sucesso (mock)"


# Substitui os serviços
mock_glpi = MockGLPI()

# Troca a variável global glpi usada dentro do dialogs
dialogs.glpi = mock_glpi

# Troca o accessor de estado
DynamicFormProcessor.user_profile_accessor = MockUserState()

# Mock dos métodos de autorização
UserAuthorization.extract_email = classmethod(lambda cls, activity: "teste@compasi.com.br")
UserAuthorization.can_access_cadastro = classmethod(lambda cls, email, display_name=None: True)
UserAuthorization.is_domain_allowed = classmethod(lambda cls, email: email.endswith("@compasi.com.br"))


async def collect_responses(messages, user_name="Teste User"):
    ctx = MockTurnContext(user_name)
    responses = []
    for msg in messages:
        ctx.activity.text = msg
        resp = await DynamicFormProcessor.process_user_message(ctx, msg, user_name)
        if resp:
            await ctx.send_activity(resp)
        responses.append(resp)
    return ctx, responses


async def test_domain_validation():
    print("\n[TESTE] Validação de domínio")
    assert UserAuthorization.is_domain_allowed("joao@compasi.com.br") is True
    assert UserAuthorization.is_domain_allowed("joao@gmail.com") is False
    print("✅ Domínio ok")


async def test_confirmation_and_switch():
    print("\n[TESTE] Confirmação e troca de formulário")
    ctx, resp = await collect_responses(["preciso de manutenção"])
    assert "Solicitações de Manutenção" in ctx.sent_messages[0]
    assert "1" in ctx.sent_messages[0] and "2" in ctx.sent_messages[0]

    # Troca para FlexSmart (opção 2)
    ctx2, resp2 = await collect_responses(["preciso de manutenção", "2"])
    assert "Nome de usuário do sistema" in ctx2.sent_messages[-1]
    print("✅ Confirmação e troca ok")


async def test_manutencao_fluxo_flexsmart():
    print("\n[TESTE] Manutenção com aviso FlexSmart")
    ctx = MockTurnContext("T", "ti.externo@compasi.com.br")

    resp = await DynamicFormProcessor.process_user_message(ctx, "erro", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "2", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)

    combined = " ".join(ctx.sent_messages)
    assert "FlexSmart" in combined and "cancelados automaticamente" in combined
    print("✅ Aviso FlexSmart ok")


async def test_flexsmart_form():
    print("\n[TESTE] Formulário FlexSmart")
    ctx, resp = await collect_responses(["erro flex"], user_name="T")
    assert "Solicitações sistema FlexSmart" in ctx.sent_messages[-1]

    ctx2 = MockTurnContext("T", "ti.externo@compasi.com.br")
    resp = await DynamicFormProcessor.process_user_message(ctx2, "erro flex", "T")
    await ctx2.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx2, "1", "T")
    await ctx2.send_activity(resp)
    assert "Nome de usuário do sistema" in ctx2.sent_messages[-1]
    print("✅ FlexSmart ok")


async def test_cadastro_authorized():
    print("\n[TESTE] Cadastro autorizado")
    ctx, resp = await collect_responses(["cadastrar colaborador"], user_name="T")
    assert "Cadastro de Novo Colaborador" in ctx.sent_messages[-1]

    ctx2 = MockTurnContext("T", "ti.externo@compasi.com.br")
    resp = await DynamicFormProcessor.process_user_message(ctx2, "cadastrar colaborador", "T")
    await ctx2.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx2, "1", "T")
    await ctx2.send_activity(resp)
    assert "nome completo" in ctx2.sent_messages[-1].lower()
    print("✅ Cadastro autorizado ok")


async def test_cadastro_denied():
    print("\n[TESTE] Cadastro negado")
    UserAuthorization.can_access_cadastro = classmethod(lambda cls, email, display_name=None: False)
    ctx, resp = await collect_responses(["cadastrar colaborador"], user_name="T")
    assert "Acesso negado" in ctx.sent_messages[-1]
    UserAuthorization.can_access_cadastro = classmethod(lambda cls, email, display_name=None: True)
    print("✅ Cadastro negado ok")


async def test_attachment_flow():
    print("\n[TESTE] Fluxo de anexo (imagem local)")
    ctx = MockTurnContext("T", "ti.externo@compasi.com.br")

    resp = await DynamicFormProcessor.process_user_message(ctx, "erro impressora", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "teste", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "1", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "ti.externo@compasi.com.br", "T")
    await ctx.send_activity(resp)
    resp = await DynamicFormProcessor.process_user_message(ctx, "2", "T")
    await ctx.send_activity(resp)

    last_msg = ctx.sent_messages[-1]
    assert "anexar" in last_msg.lower()

    resp = await DynamicFormProcessor.process_user_message(ctx, "sim", "T")
    await ctx.send_activity(resp)

    image_path = r"C:\Users\Administrator\Downloads\teste.jpeg"
    if not os.path.exists(image_path):
        print("⚠️ Arquivo de teste não encontrado, pulando simulação de upload")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ctx.set_attachment("teste.jpeg", image_bytes, "image/jpeg")

    async def mock_download(turn_context):
        return [("teste.jpeg", image_bytes)]

    with patch.object(TeamsAttachmentHandler, "download_attachments", mock_download):
        resp = await DynamicFormProcessor.process_user_message(ctx, "concluir", "T")
        await ctx.send_activity(resp)

    assert mock_glpi.created_tickets, "Deveria criar chamado (mock)"
    assert mock_glpi.created_tickets[-1]["attachments"], "Deveria ter anexo"
    print("✅ Anexo ok")


async def run_all():
    print("🚀 Iniciando testes...")
    await test_domain_validation()
    await test_confirmation_and_switch()
    await test_manutencao_fluxo_flexsmart()
    await test_flexsmart_form()
    await test_cadastro_authorized()
    await test_cadastro_denied()
    await test_attachment_flow()
    print("\n✅ Todos os testes passaram!")


if __name__ == "__main__":
    asyncio.run(run_all())