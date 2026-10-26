"""Fronteira opt-in com uma única passagem pelo adapter por atividade.

Instalada em main.py. dispatch aceita o adapter compartilhado do endpoint;
process é a conveniência isolada, nunca deve ser chamada de um callback do SDK.
"""
import asyncio
from .service import IdentityResult, _AuthenticatedTurn, _PROOF
from .store import guid


def _build_adapter(config):
    from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, BotAdapter
    from botframework.connector.auth import SimpleCredentialProvider
    provider = SimpleCredentialProvider(config.MICROSOFT_APP_ID, config.MICROSOFT_APP_PASSWORD)
    adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(
        app_id=config.MICROSOFT_APP_ID, app_password=config.MICROSOFT_APP_PASSWORD,
        channel_auth_tenant=config.MICROSOFT_APP_TENANT_ID, credential_provider=provider))
    return adapter, provider, BotAdapter.BOT_IDENTITY_KEY


class IdentityIngress:
    def __init__(self, config, service, *, adapter_bundle=None):
        """adapter_bundle=(adapter, seu credential provider, BOT_IDENTITY_KEY).

        Fornecer objetos reais compostos no servidor, nunca dados da requisição.
        Sem bundle, constrói um adapter isolado de forma tardia.
        """
        self.config = config
        self.service = service
        self._adapter_bundle = adapter_bundle

    def _configuration_failure(self):
        try:
            for field in ('MICROSOFT_APP_ID', 'MICROSOFT_APP_TENANT_ID', 'IDENTITY_ALLOWED_TENANT_ID'):
                guid(getattr(self.config, field))
            if not self.config.MICROSOFT_APP_PASSWORD.strip():
                raise ValueError()
            if guid(self.service.allowed_tenant) != guid(self.config.IDENTITY_ALLOWED_TENANT_ID):
                raise ValueError()
        except (ValueError, AttributeError, TypeError):
            return IdentityResult('authentication_configuration')
        return None

    @staticmethod
    def _has_bearer(authorization):
        return (isinstance(authorization, str) and authorization.startswith('Bearer ')
                and bool(authorization[7:].strip()))

    async def dispatch(self, activity, authorization, logic):
        """Única entrada futura do endpoint; devolve a resposta original do adapter.

        logic(context, resolve_identity) decide explicitamente o fluxo. A abertura
        pode ignorar resolve_identity. Somente essa função interna pode emitir a
        capacidade; não há método público que valide um TurnContext arbitrário.
        Exceções do SDK continuam com o tratamento do endpoint/adapter existente.
        """
        if self._adapter_bundle is None:
            self._adapter_bundle = _build_adapter(self.config)
        adapter, provider, identity_key = self._adapter_bundle

        async def authenticated(context):
            active = True
            cached_result = None
            resolution_lock = asyncio.Lock()

            async def resolve_once():
                nonlocal cached_result
                if not active or context.adapter is not adapter:
                    return IdentityResult('unauthenticated')
                if cached_result is not None:
                    return cached_result
                failure = self._configuration_failure()
                if failure is not None:
                    return failure
                if not self._has_bearer(authorization):
                    return IdentityResult('unauthenticated')
                try:
                    if await provider.is_authentication_disabled():
                        return IdentityResult('authentication_disabled')
                    claims = context.turn_state.get(identity_key)
                    if (claims is None or claims.is_authenticated is not True
                            or not isinstance(claims.claims, dict)
                            or claims.claims.get('aud') != self.config.MICROSOFT_APP_ID):
                        return IdentityResult('unauthenticated')
                except (AttributeError, TypeError):
                    return IdentityResult('unauthenticated')
                turn = _AuthenticatedTurn(context, _PROOF)
                try:
                    cached_result = await self.service.resolve(turn)
                    if cached_result.code == "ok":
                        from notifications.capture import capture
                        await capture(context, cached_result, self.config)
                    return cached_result
                finally:
                    turn.live = False

            async def resolve_identity():
                # Concurrent consumers in one authenticated activity share the
                # same Teams lookup, link decision and notification capture.
                async with resolution_lock:
                    return await resolve_once()

            try:
                return await logic(context, resolve_identity)
            finally:
                active = False

        return await adapter.process_activity(activity, authorization, authenticated)

    async def process(self, activity, authorization):
        """Conveniência isolada; não usar dentro de callback nem após outro adapter."""
        failure = self._configuration_failure()
        if failure is not None:
            return failure
        if not self._has_bearer(authorization):
            return IdentityResult('unauthenticated')
        result = IdentityResult('unauthenticated')

        async def identity_only(context, resolve_identity):
            nonlocal result
            result = await resolve_identity()

        try:
            await self.dispatch(activity, authorization, identity_only)
        except ImportError:
            return IdentityResult('sdk_unavailable')
        except Exception:
            return IdentityResult('authentication_failed')
        return result
