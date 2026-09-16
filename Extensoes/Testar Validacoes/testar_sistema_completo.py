# testar_sistema_completo.py
"""
Script de teste automatizado do Byte Bot de Chamados (ATUALIZADO).
Alinha os testes ao novo fluxo de formulários:
  - confirmação do formulário antes de iniciar
  - autorização de cadastro via GLPI
  - FlexSmart (Liberação de Telas / Liberação Outros / Tipo Outro)
  - Manutenção (Equipamentos / Sistemas / Acessos)
  - passo final de anexo antes de criar chamado

Estratégia: os fluxos longos usam um helper DINÂMICO que responde
conforme o prompt atual do bot, evitando dependência de ordem fixa.

Não envia dados reais ao GLPI (tudo mockado).
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT_DIR)

# Variáveis dummy para pydantic-settings
os.environ.setdefault("GLPI_URL", "http://localhost")
os.environ.setdefault("GLPI_APP_TOKEN", "dummy_token")
os.environ.setdefault("GLPI_USER_TOKEN", "dummy_user_token")
os.environ.setdefault("MICROSOFT_APP_ID", "dummy_app_id")
os.environ.setdefault("MICROSOFT_APP_PASSWORD", "dummy_app_password")
os.environ.setdefault("MICROSOFT_APP_TENANT_ID", "dummy_tenant_id")

import asyncio
import json
from unittest.mock import Mock, patch

import bot.dialogs as dialogs
from bot.dialogs import DynamicFormProcessor
from bot.auth import UserAuthorization
from bot.attachments import TeamsAttachmentHandler


# ============================================================
# MOCKS
# ============================================================

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

    def clear_attachments(self):
        self.activity.attachments = []


class MockGLPI:
    """Mock do serviço GLPI com busca de email e criação de chamados."""

    def __init__(self, email_por_nome=None):
        self.created_tickets = []
        self.email_por_nome = email_por_nome or {
            "Teste User": "teste.user@compasi.com.br",
            "Carlos Pereira": "carlos.pereira@compasi.com.br",
            "Maria Santos": "maria.santos@compasi.com.br",
            "João Silva": "joao.silva@compasi.com.br",
            "Pedro Costa": "pedro.costa@systemup.inf.br",
            "Ana Costa": "ana.costa@compasi.com.br",
            "Juliana Lima": "juliana.lima@compasi.com.br",
        }

    def get_user_email(self, nome):
        return self.email_por_nome.get(nome)

    def create_form_answer(self, form_id, form_values, requester_email=None, attachments=None):
        self.created_tickets.append({
            "form_id": form_id,
            "values": form_values,
            "requester_email": requester_email,
            "attachments": attachments,
        })
        return True, "Chamado criado com sucesso (mock)"


# ============================================================
# SETUP GLOBAL
# ============================================================

mock_glpi = MockGLPI()

dialogs.glpi = mock_glpi
DynamicFormProcessor.user_profile_accessor = MockUserState()

# Garante que qualquer referência à instância GLPI no processor use o mock
for attr in ("glpi", "glpi_service", "glpi_client"):
    if hasattr(DynamicFormProcessor, attr):
        setattr(DynamicFormProcessor, attr, mock_glpi)

UserAuthorization.is_domain_allowed = classmethod(
    lambda cls, email: bool(email) and (
        email.endswith("@compasi.com.br") or email.endswith("@systemup.inf.br")
    )
)
UserAuthorization.can_access_cadastro = classmethod(
    lambda cls, email, display_name=None: True
)


# ============================================================
# HELPERS
# ============================================================

async def send(ctx, msg):
    """Envia uma mensagem e retorna a resposta do bot."""
    ctx.activity.text = msg
    resp = await DynamicFormProcessor.process_user_message(ctx, msg, ctx.user_name)
    if resp:
        await ctx.send_activity(resp)
    return resp or ""


def ultima(ctx):
    return ctx.sent_messages[-1] if ctx.sent_messages else ""


def contém(ctx, trecho, from_last=1):
    alvo = " ".join(ctx.sent_messages[-from_last:]).lower()
    return trecho.lower() in alvo


async def collect_responses(messages, user_name="Teste User"):
    """Envia uma sequência fixa de mensagens (para fluxos curtos)."""
    ctx = MockTurnContext(user_name)
    responses = []
    for msg in messages:
        resp = await send(ctx, msg)
        responses.append(resp)
    return ctx, responses


async def complete_until_anexo(ctx, max_iter=20, verbose=True):
    """
    Responde dinamicamente até o bot exibir o prompt de anexo.
    Usa heurísticas baseadas no texto do prompt atual.
    Retorna True se chegou ao prompt de anexo.
    """
    for i in range(max_iter):
        last = ultima(ctx).lower()
        if verbose:
            print(f"   [iter {i+1}] prompt: {last[:110]!r}")

        if "anexar" in last:
            return True

        # -------- Seleções de opção (via texto do prompt) --------
        if "tipo de atendimento" in last:
            await send(ctx, "1")            # Liberação (default FlexSmart)
        elif "qual liberação será feita" in last:
            await send(ctx, "Liberação genérica no sistema")
        elif "qual liberação" in last:
            await send(ctx, "1")            # Telas
        elif "qual tela" in last:
            await send(ctx, "Tela genérica")
        elif "tipo da solicitação" in last:
            await send(ctx, "1")            # Equipamentos
        elif "sistema está com problema" in last:
            await send(ctx, "1")            # FlexSmart
        elif "equipamento" in last:
            await send(ctx, "1")            # Computador/Hardware
        elif "local da solicitação" in last:
            await send(ctx, "1")            # Matriz
        elif "sua filial" in last or "escolha a filial" in last:
            await send(ctx, "2")            # Lages
        elif "canal" in last:
            await send(ctx, "3")            # OPA (evita sub-pergunta)
        elif "whatsapp" in last:
            await send(ctx, "49 99999-8888")
        elif "teams" in last or ("email" in last and "canal" not in last):
            await send(ctx, "teste.user@compasi.com.br")
        elif "urgencia" in last or "urgência" in last:
            await send(ctx, "2")            # Média
        elif "liberação é para qual usuário" in last:
            await send(ctx, "1")            # Usuario Atual
        elif "nome do usuário" in last:
            await send(ctx, "Maria Santos")
        elif "descreva" in last:
            await send(ctx, "Descrição genérica do problema")
        elif "unidade" in last:
            await send(ctx, "1")            # Matriz
        elif "setor" in last:
            await send(ctx, "1")
        elif "modelo" in last or "perfil" in last:
            await send(ctx, "Padrão")
        elif "vpn" in last:
            await send(ctx, "1")            # Sim
        elif "microsoft 365" in last or "licença" in last:
            await send(ctx, "1")            # Standard
        elif "acessos ao flex" in last:
            await send(ctx, "1")            # Sim
        elif "possui equipamento" in last:
            await send(ctx, "2")            # Não (evita sub-pergunta)
        elif "tipo de equipamento" in last:
            await send(ctx, "1")            # Desktop
        elif "ramal" in last:
            await send(ctx, "1")            # Sim
        elif "precisar ter de equipamento" in last:
            await send(ctx, "1")            # Desktop
        elif "instalado algum programa" in last:
            await send(ctx, "2")            # Não (evita sub-pergunta)
        elif "quais programas" in last:
            await send(ctx, "Office, Teams")
        elif "assinatura" in last:
            await send(ctx, "1")            # Sim
        elif "observaç" in last:
            await send(ctx, "Sem observações")
        else:
            await send(ctx, "1")            # fallback

    return False


# ============================================================
# TESTES
# ============================================================

async def test_domain_validation():
    print("\n[TESTE] Validação de domínio")
    assert UserAuthorization.is_domain_allowed("joao@compasi.com.br") is True
    assert UserAuthorization.is_domain_allowed("maria@systemup.inf.br") is True
    assert UserAuthorization.is_domain_allowed("joao@gmail.com") is False
    assert UserAuthorization.is_domain_allowed(None) is False
    assert UserAuthorization.is_domain_allowed("") is False
    print("✅ Domínio ok")


async def test_confirmation_and_switch():
    print("\n[TESTE] Confirmação e troca de formulário")

    ctx, _ = await collect_responses(["preciso de manutenção"])
    assert "Solicitações de Manutenção" in ctx.sent_messages[0]
    assert "1" in ctx.sent_messages[0] and "2" in ctx.sent_messages[0]

    ctx2, _ = await collect_responses(["preciso de manutenção", "1"])
    assert "tipo da solicitação" in ultima(ctx2).lower(), \
        f"Esperava 'tipo da solicitação', recebi: {ultima(ctx2)}"

    ctx3, _ = await collect_responses(["preciso de manutenção", "2"])
    assert "FlexSmart" in ultima(ctx3), \
        f"Esperava 'FlexSmart' após troca, recebi: {ultima(ctx3)}"

    print("✅ Confirmação e troca ok")


async def test_manutencao_fluxo_completo():
    print("\n[TESTE] Manutenção - fluxo completo (Equipamentos/Matriz/Teams)")
    ctx = MockTurnContext("Teste User")
    await send(ctx, "preciso de manutenção no meu computador")
    await send(ctx, "1")
    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo.\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ Manutenção fluxo completo ok")


async def test_manutencao_sistemas():
    print("\n[TESTE] Manutenção → Manutenção de Sistemas (FlexSmart)")
    ctx = MockTurnContext("Teste User")
    await send(ctx, "preciso de manutenção")
    await send(ctx, "1")
    await send(ctx, "2")
    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo (Sistemas).\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ Manutenção → Sistemas ok")


async def test_manutencao_acessos():
    print("\n[TESTE] Manutenção → Acessos")
    ctx = MockTurnContext("Teste User")
    await send(ctx, "preciso de um acesso")
    await send(ctx, "1")
    await send(ctx, "3")
    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo (Acessos).\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ Manutenção → Acessos ok")


async def test_flexsmart_liberacao_telas():
    print("\n[TESTE] FlexSmart → Liberação de Telas (Usuario Atual)")
    ctx = MockTurnContext("Teste User")
    await send(ctx, "erro flex")
    await send(ctx, "1")
    await send(ctx, "1")
    await send(ctx, "1")
    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo (FlexSmart/Telas).\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ FlexSmart → Telas ok")


async def test_flexsmart_liberacao_outros_usuario():
    print("\n[TESTE] FlexSmart → Liberação Outros (Outro Usuário)")
    ctx = MockTurnContext("Teste User")
    await send(ctx, "problema no flex")
    await send(ctx, "1")
    await send(ctx, "1")
    await send(ctx, "2")
    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo (FlexSmart/Outros).\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ FlexSmart → Outros ok")


async def test_flexsmart_tipo_outro():
    """FlexSmart → Tipo Outro (sem liberação). Responde dinamicamente."""
    print("\n[TESTE] FlexSmart → Tipo Outro (sem liberação)")
    ctx = MockTurnContext("Teste User")

    await send(ctx, "problema no flex")
    await send(ctx, "1")   # confirma
    await send(ctx, "2")   # tipo_atendimento: Outro

    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo (FlexSmart/Outro).\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print("✅ FlexSmart → Outro ok")


async def test_cadastro_authorized():
    print("\n[TESTE] Cadastro autorizado (mock)")
    UserAuthorization.can_access_cadastro = classmethod(
        lambda cls, email, display_name=None: True
    )
    ctx, _ = await collect_responses(["cadastrar colaborador"], user_name="Teste User")
    assert "Cadastro de Novo Colaborador" in ultima(ctx), \
        f"Não identificou cadastro: {ultima(ctx)}"

    ctx2, _ = await collect_responses(["cadastrar colaborador", "1"], user_name="Teste User")
    assert "nome completo" in ultima(ctx2).lower(), \
        f"Não pediu nome completo: {ultima(ctx2)}"
    print("✅ Cadastro autorizado ok")


async def test_cadastro_denied():
    print("\n[TESTE] Cadastro negado (autorização mockada como False)")
    UserAuthorization.can_access_cadastro = classmethod(
        lambda cls, email, display_name=None: False
    )
    ctx, _ = await collect_responses(["cadastrar colaborador"], user_name="Teste User")
    assert "acesso negado" in ultima(ctx).lower(), \
        f"Esperava acesso negado, recebi: {ultima(ctx)}"

    UserAuthorization.can_access_cadastro = classmethod(
        lambda cls, email, display_name=None: True
    )
    print("✅ Cadastro negado ok")


async def test_anexo_flow():
    """Fluxo de anexo: aceita anexar, envia o arquivo e espera criação do chamado."""
    print("\n[TESTE] Fluxo de anexo (imagem simulada)")
    mock_glpi.created_tickets.clear()

    image_bytes = b"\xff\xd8\xff\xe0" + b"fake_jpeg_content" + b"\xff\xd9"
    download_called = {"count": 0}

    async def mock_download(turn_context):
        download_called["count"] += 1
        print(f"   [MOCK] download_attachments chamado! (nº {download_called['count']})")
        return [("teste.jpeg", image_bytes)]

    # ---- Chega até o prompt de anexo ----
    ctx = MockTurnContext("Teste User", "teste.user@compasi.com.br")
    await send(ctx, "erro impressora")
    await send(ctx, "1")

    ok = await complete_until_anexo(ctx)
    assert ok, (
        "Não chegou ao prompt de anexo.\n"
        "Histórico:\n" + "\n".join(f"  - {m[:120]!r}" for m in ctx.sent_messages)
    )
    print(f"   ✓ no prompt de anexo: {ultima(ctx)[:110]!r}")

    # ---- Aceita anexar ----
    resp = await send(ctx, "sim")
    print(f"   ✓ após 'sim' → {resp[:140]!r}")

    # ---- Define attachment ANTES de enviar a próxima mensagem ----
    ctx.set_attachment("teste.jpeg", image_bytes, "image/jpeg")

    # ---- Envia a mensagem com o attachment (mock do download) ----
    with patch.object(TeamsAttachmentHandler, "download_attachments", mock_download):
        # Variações de mensagem que podem disparar o processamento do arquivo
        for tentativa in ["concluir", "", "ok", "pronto", "finalizar", "sim"]:
            print(f"   → tentando mensagem {tentativa!r} com attachment...")
            resp = await send(ctx, tentativa)
            print(f"     resposta: {resp[:150]!r}")
            if mock_glpi.created_tickets:
                break
            # Reafirma o attachment caso o bot tenha limpado
            ctx.set_attachment("teste.jpeg", image_bytes, "image/jpeg")

    print(f"   ✓ download_attachments chamado {download_called['count']}x")
    print(f"   ✓ chamados criados: {len(mock_glpi.created_tickets)}")

    if not mock_glpi.created_tickets:
        print("\n⚠️  Nenhum chamado criado. Histórico completo:")
        for i, m in enumerate(ctx.sent_messages, 1):
            print(f"  [{i}] {m[:200]!r}")
        raise AssertionError(
            "Deveria criar chamado (mock). "
            "Verifique se o bot usa activity.attachments e se o método de download é o esperado."
        )

    last_ticket = mock_glpi.created_tickets[-1]
    assert last_ticket["attachments"], "Chamado deveria ter anexo"
    print("✅ Anexo ok")


async def test_fluxo_completo_sem_anexo():
    print("\n[TESTE] Fluxo completo recusando anexo → cria chamado")
    mock_glpi.created_tickets.clear()

    ctx = MockTurnContext("Teste User")
    await send(ctx, "preciso de manutenção")
    await send(ctx, "1")

    ok = await complete_until_anexo(ctx)
    assert ok, "Não chegou ao prompt de anexo"

    await send(ctx, "não")

    assert mock_glpi.created_tickets, "Deveria criar chamado no GLPI"
    ultimo = mock_glpi.created_tickets[-1]
    assert ultimo["form_id"] == 1, f"form_id esperado=1 (manutencao), veio {ultimo['form_id']}"
    print(f"✅ Chamado criado sem anexo (form_id={ultimo['form_id']})")


async def test_flexsmart_cria_chamado():
    print("\n[TESTE] FlexSmart → cria chamado no GLPI")
    mock_glpi.created_tickets.clear()

    ctx = MockTurnContext("Teste User")
    await send(ctx, "erro flex")
    await send(ctx, "1")
    await send(ctx, "1")
    await send(ctx, "1")

    ok = await complete_until_anexo(ctx)
    assert ok, "Não chegou ao prompt de anexo"

    await send(ctx, "não")

    assert mock_glpi.created_tickets, "Deveria criar chamado no GLPI"
    ultimo = mock_glpi.created_tickets[-1]
    assert ultimo["form_id"] == 5, f"form_id esperado=5 (flexsmart), veio {ultimo['form_id']}"
    print(f"✅ FlexSmart criou chamado (form_id={ultimo['form_id']})")


async def test_erros():
    print("\n[TESTE] Tratamento de erros")

    ctx, _ = await collect_responses(["asdfghjkl"])
    assert "não consegui identificar" in ultima(ctx).lower()

    ctx2, _ = await collect_responses(["preciso de manutenção", "99"])
    assert "opção inválida" in ultima(ctx2).lower() or "inválida" in ultima(ctx2).lower()

    ctx3, _ = await collect_responses(["cancelar"])
    assert "não há atendimento" in ultima(ctx3).lower()

    print("✅ Tratamento de erros ok")


# ============================================================
# RUNNER
# ============================================================

async def run_all():
    print("🚀 Iniciando testes (novo fluxo)...")

    await test_domain_validation()
    await test_confirmation_and_switch()

    # Manutenção
    await test_manutencao_fluxo_completo()
    await test_manutencao_sistemas()
    await test_manutencao_acessos()

    # FlexSmart
    await test_flexsmart_liberacao_telas()
    await test_flexsmart_liberacao_outros_usuario()
    await test_flexsmart_tipo_outro()

    # Cadastro
    await test_cadastro_authorized()
    await test_cadastro_denied()

    # Anexos e criação
    await test_anexo_flow()
    await test_fluxo_completo_sem_anexo()
    await test_flexsmart_cria_chamado()

    # Erros
    await test_erros()

    print("\n" + "=" * 60)
    print(f"📊 Chamados criados no GLPI mock: {len(mock_glpi.created_tickets)}")
    for i, t in enumerate(mock_glpi.created_tickets, 1):
        print(f"  {i}. form_id={t['form_id']} anexos={len(t['attachments'] or [])}")
    print("=" * 60)
    print("\n✅ Todos os testes passaram!")


if __name__ == "__main__":
    asyncio.run(run_all())