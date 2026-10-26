"""Resolução apenas dentro da fronteira autenticada definida em ingress.py."""
import asyncio
from dataclasses import dataclass
import sqlite3
from .store import guid, Conflict
from .email_lookup import normalize_email

_PROOF = object()


@dataclass(frozen=True)
class TeamsIdentity:
    tenant_id: str
    object_id: str
    member_id: str
    email: str | None
    user_principal_name: str | None


@dataclass(frozen=True)
class IdentityResult:
    code: str
    identity: TeamsIdentity | None = None
    glpi_user_id: int | None = None
    link_revision: str | None = None


class _AuthenticatedTurn:
    def __init__(self, context, proof):
        if proof is not _PROOF:
            raise ValueError('unauthenticated')
        self.context = context
        self.live = True


async def _get_member(context, member_id):
    from botbuilder.core.teams import TeamsInfo
    return await TeamsInfo.get_member(context, member_id)


class IdentityService:
    def __init__(self, store, glpi_reader, allowed_tenant, *, auto_link_enabled=False, email_lookup=None):
        self.store = store
        self.glpi = glpi_reader
        self.allowed_tenant = allowed_tenant
        self.auto_link_enabled = auto_link_enabled is True
        self.email_lookup = email_lookup

    async def _associate(self, identity):
        if not isinstance(identity.email, str) or not identity.email.strip():
            return IdentityResult('email_missing', identity)
        try:
            email = normalize_email(identity.email)
        except ValueError:
            return IdentityResult('email_invalid', identity)
        if self.email_lookup is None:
            return IdentityResult('auto_link_unavailable', identity)
        first = await asyncio.to_thread(self.email_lookup.find, email)
        if first.code != 'ok' or first.glpi_user_id is None:
            return IdentityResult(first.code if first.code in {'email_no_match', 'email_ambiguous'} else 'auto_link_unavailable', identity)
        # Repeat the entire exact uniqueness check before creating, not just the
        # candidate's default address. New ambiguity or reassignment denies.
        latest = await asyncio.to_thread(self.email_lookup.find, email)
        if latest.code != 'ok':
            return IdentityResult(latest.code if latest.code in {'email_no_match', 'email_ambiguous'} else 'auto_link_unavailable', identity)
        if latest.glpi_user_id != first.glpi_user_id:
            return IdentityResult('email_changed', identity)
        check = await asyncio.to_thread(self.glpi.check, first.glpi_user_id)
        if check.code != 'ok' or check.glpi_user_id != first.glpi_user_id:
            return IdentityResult('email_changed' if check.code in {'glpi_missing', 'glpi_inactive', 'glpi_deleted'} else 'auto_link_unavailable', identity)
        try:
            return await asyncio.to_thread(self.store.create_automatic,
                                          identity.tenant_id, identity.object_id, first.glpi_user_id)
        except Conflict:
            current = await asyncio.to_thread(self.store.get, identity.tenant_id, identity.object_id)
            code = 'link_revoked' if current and current['status'] == 'revoked' else 'link_conflict'
            return IdentityResult(code, identity)

    async def resolve(self, turn):
        if not isinstance(turn, _AuthenticatedTurn) or not turn.live:
            return IdentityResult('unauthenticated')
        try:
            allowed = guid(self.allowed_tenant)
        except (ValueError, TypeError, AttributeError):
            return IdentityResult('authentication_configuration')
        try:
            activity = turn.context.activity
            if activity.channel_id != 'msteams':
                return IdentityResult('wrong_channel')
            conversation = activity.conversation
            if conversation.conversation_type != 'personal' or conversation.is_group is True:
                return IdentityResult('personal_only')
            if not conversation.id:
                return IdentityResult('identity_missing')
            data = activity.channel_data
            tenant = guid(data['tenant']['id'])
            if tenant != allowed:
                return IdentityResult('tenant_denied')
            if conversation.tenant_id and guid(conversation.tenant_id) != tenant:
                return IdentityResult('identity_mismatch')
            sender = activity.from_property
            object_id = guid(sender.aad_object_id)
            if not isinstance(sender.id, str) or not sender.id.strip():
                return IdentityResult('identity_missing')
        except (AttributeError, KeyError, TypeError, ValueError):
            return IdentityResult('identity_missing')
        try:
            member = await asyncio.wait_for(_get_member(turn.context, sender.id), timeout=10)
        except Exception:
            return IdentityResult('teams_unavailable')
        try:
            if (member.id != sender.id or guid(member.aad_object_id) != object_id
                    or guid(member.tenant_id) != tenant):
                return IdentityResult('identity_mismatch')
            identity = TeamsIdentity(tenant, object_id, sender.id,
                                     getattr(member, 'email', None), getattr(member, 'user_principal_name', None))
        except (AttributeError, TypeError, ValueError):
            return IdentityResult('identity_missing')
        try:
            link = await asyncio.to_thread(self.store.get, tenant, object_id)
            if not link:
                if not self.auto_link_enabled:
                    return IdentityResult('link_missing', identity)
                try:
                    link = await self._associate(identity)
                except Exception:
                    return IdentityResult('auto_link_unavailable', identity)
                if isinstance(link, IdentityResult):
                    return link
            if link['status'] != 'active':
                return IdentityResult('link_revoked', identity)
            check = await asyncio.to_thread(self.glpi.check, link['glpi_user_id'])
            if check.code != 'ok' or check.glpi_user_id != link['glpi_user_id']:
                return IdentityResult(check.code if check.code != 'ok' else 'glpi_incomplete', identity)
            # Uma revogação/substituição durante a consulta invalida este resultado.
            current = await asyncio.to_thread(self.store.get, tenant, object_id)
            if current != link:
                return IdentityResult('link_changed', identity)
            return IdentityResult('ok', identity, check.glpi_user_id, link['updated_at'])
        except (sqlite3.Error, OSError, ValueError):
            return IdentityResult('identity_unavailable', identity)
