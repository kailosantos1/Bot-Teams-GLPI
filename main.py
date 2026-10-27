# main.py
import uvicorn
import traceback
from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from config import settings, logger
from bot.dialogs import DynamicFormProcessor
from bot.state import conversation_state, user_state
from bot.utils import UserNameFormatter
from bot.auth import UserAuthorization
from identity.ingress import IdentityIngress, _build_adapter
from identity.service import IdentityService
from identity.store import LinkStore
from identity.glpi import GLPIUserReader
from identity.email_lookup import GLPIEmailLookup
from notifications.manager import manager as notification_manager

app = FastAPI(title="Otto — Assistente GLPI API")

adapter, credential_provider, identity_key = _build_adapter(settings)
identity_service = IdentityService(LinkStore(settings.IDENTITY_DB_PATH),
    GLPIUserReader(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN),
    settings.IDENTITY_ALLOWED_TENANT_ID, auto_link_enabled=settings.IDENTITY_AUTO_LINK_ENABLED,
    email_lookup=GLPIEmailLookup(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN))
identity_ingress = IdentityIngress(settings, identity_service,
    adapter_bundle=(adapter, credential_provider, identity_key))

async def authenticated_message(context, resolve_identity):
    context.resolve_ticket_identity = resolve_identity
    try:
        await logic_process_message(context)
    finally:
        del context.resolve_ticket_identity


async def send_error_message(context: TurnContext, message: str):
    """Envia mensagem de erro para o usuário."""
    first_name = UserNameFormatter.extract_first_name(
        context.activity.from_property.name if context.activity else None
    )

    try:
        await context.send_activity(
            f"⚠️ **{first_name}, ocorreu um erro!**\n\n"
            f"{message}\n\n"
            f"Tente novamente ou digite **'cancelar'** para reiniciar.\n"
            f"Se o problema persistir, contate o suporte de TI."
        )
    except Exception as e:
        logger.error(f"Falha ao enviar mensagem de erro: {e}")


async def on_error(context: TurnContext, error: Exception):
    """
    Handler global de erro do adapter.
    Captura QUALQUER erro e sempre responde ao usuário.
    """
    if getattr(context, 'sensitive_ticket_flow', False):
        # Never log draft text, API content or raw exceptions from this path.
        logger.error("Falha no fluxo de consulta/resposta: %s", type(error).__name__)
        await context.send_activity(
            "Não consegui concluir essa operação agora. Use as opções atuais para tentar novamente."
        )
        try:
            await conversation_state.save_changes(context)
            await user_state.save_changes(context)
        except Exception:
            logger.error("Erro ao salvar estado da consulta/resposta")
        return

    # Log detalhado
    logger.error("="*80)
    logger.error("❌ ERRO NO BOT")
    logger.error("="*80)
    logger.error(f"Tipo: {type(error).__name__}")
    logger.error(f"Mensagem: {str(error)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    try:
        if context and context.activity:
            logger.error(f"Usuário: {context.activity.from_property.name}")
    except Exception as log_error:
        logger.error(f"Erro ao logar contexto: {log_error}")

    # Mensagens de erro específicas
    error_message = "Ocorreu um erro inesperado ao processar sua mensagem."

    if isinstance(error, TimeoutError):
        error_message = "O servidor demorou muito para responder. Tente novamente em instantes."
    elif "connection" in str(error).lower():
        error_message = "Não foi possível conectar ao GLPI. Verifique se o serviço está disponível."
    elif "timeout" in str(error).lower():
        error_message = "O GLPI demorou muito para responder. Tente novamente."
    elif "authentication" in str(error).lower() or "auth" in str(error).lower():
        error_message = "Erro de autenticação com o GLPI. Contate o suporte de TI."

    await send_error_message(context, error_message)

    # Tenta salvar o estado mesmo com erro
    try:
        await conversation_state.save_changes(context)
        await user_state.save_changes(context)
    except Exception:
        logger.error("Erro ao salvar estado após erro")


adapter.on_turn_error = on_error


@app.on_event("startup")
async def on_startup():
    try:
        await notification_manager.start()
    except Exception:
        logger.error("Falha ao iniciar worker de notificações no startup")


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await notification_manager.stop()
    except Exception:
        logger.error("Falha ao encerrar worker de notificações no shutdown")


async def logic_process_message(turn_context: TurnContext):
    try:
        if turn_context.activity.type != ActivityTypes.message:
            return

        # ============================================================
        # VALIDAÇÃO DE AUTORIZAÇÃO DO USUÁRIO
        # ============================================================
        logger.info("="*60)
        logger.info("🔐 INICIANDO VALIDAÇÃO DE AUTORIZAÇÃO")
        logger.info("="*60)

        user_email = None
        if await DynamicFormProcessor.needs_legacy_authorization(turn_context):
            is_authorized, user_email, auth_message = UserAuthorization.validate_user(
                turn_context.activity
            )
            if not is_authorized:
                await turn_context.send_activity(auth_message)
                await conversation_state.save_changes(turn_context)
                await user_state.save_changes(turn_context)
                return

        user_text = (turn_context.activity.text or "").strip()
        user_name = turn_context.activity.from_property.name or "Usuário Teams"

        # NOVO: quando o usuário só cola uma imagem (Ctrl+V) sem digitar
        # nada junto, o texto vem vazio -- mas a mensagem é válida (tem
        # anexo). O mesmo vale para cliques em botões (activity.value).
        # Só bloqueia se realmente não tiver NEM texto NEM anexo NEM valor.
        tem_anexo = bool(getattr(turn_context.activity, "attachments", None))
        tem_valor = bool(getattr(turn_context.activity, "value", None))

        if not user_text and not tem_anexo and not tem_valor:
            first_name = UserNameFormatter.extract_first_name(user_name)
            await turn_context.send_activity(
                f"**{first_name}**, não consegui entender sua mensagem. "
                "Digite **ajuda** para ver os comandos disponíveis."
            )
            await conversation_state.save_changes(turn_context)
            await user_state.save_changes(turn_context)
            return

        turn_context.user_email = user_email

        response_text = await DynamicFormProcessor.process_user_message(
            turn_context, user_text, user_name
        )

        # Só envia se houver texto de resposta.
        # O processador pode ter enviado mensagens manualmente (aviso),
        # e nesse caso retorna None.
        if response_text:
            await turn_context.send_activity(response_text)

        await conversation_state.save_changes(turn_context)
        await user_state.save_changes(turn_context)

    except Exception as e:
        if getattr(turn_context, 'sensitive_ticket_flow', False):
            logger.error("Falha no fluxo de consulta/resposta")
        else:
            logger.error(f"Erro detalhado: {traceback.format_exc()}")
        raise


@app.post("/api/messages")
async def messages(req: Request):
    """
    Endpoint principal que recebe mensagens do Teams.
    SEMPRE retorna 200 para o Teams não ficar reenviando.
    """
    try:
        if "application/json" not in req.headers.get("content-type", ""):
            return Response(status_code=415)

        auth_header = req.headers.get("Authorization", "")
        body = await req.json()
        activity = Activity().deserialize(body)

        response = await identity_ingress.dispatch(activity, auth_header, authenticated_message)

        if response:
            return Response(status_code=response.status, content=response.body)
        return Response(status_code=200)

    except Exception as e:
        logger.exception(f"Erro ao processar atividade: {e}")
        return Response(status_code=200)


@app.get("/health")
async def health_check():
    """Endpoint para verificar se o bot está funcionando."""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "bot": "Otto — Assistente GLPI"
    }


@app.get("/api/status")
async def status_check():
    """Endpoint para verificar status detalhado."""
    from datetime import datetime
    from config import FORMS_CONFIG

    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "bot": "Otto — Assistente GLPI",
        "forms_loaded": len(FORMS_CONFIG),
        "forms_available": list(FORMS_CONFIG.keys()),
        "glpi_configured": bool(settings.GLPI_URL and settings.GLPI_APP_TOKEN),
        "microsoft_configured": bool(settings.MICROSOFT_APP_ID and settings.MICROSOFT_APP_PASSWORD),
        "allowed_domains": UserAuthorization.ALLOWED_DOMAINS,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_config=None,
        access_log=False
    )
