"""Called only with the result of the existing live authenticated resolver."""
import asyncio
import json
from types import SimpleNamespace
from urllib.parse import urlsplit
from identity.notifications import NotificationStore
from .policy import Policy


def valid_reference(ref, identity, app):
    try:
        url = urlsplit(ref['serviceUrl'])
        conversation, user, bot = ref['conversation'], ref['user'], ref['bot']
        return bool(url.scheme == 'https' and url.hostname and not url.username and not url.password
                    and not url.query and not url.fragment
                    and ref['channelId'] == 'msteams' and conversation['conversationType'] == 'personal'
                    and conversation.get('isGroup') is not True and conversation['id']
                    and user['id'] == identity.member_id and user['aadObjectId'] == identity.object_id
                    and bot['id'] and app)
    except (ValueError, TypeError, KeyError):
        return False


async def capture(context, result, config):
    policy = Policy.configured(config)
    if policy is None or result.code != 'ok' or not result.link_revision:
        return
    store = NotificationStore(config.IDENTITY_DB_PATH)
    try:
        from botbuilder.core import TurnContext
        ref = TurnContext.get_conversation_reference(context.activity).serialize()
        # Do not retain names, activity IDs or unrelated channel data.
        ref.pop('activityId', None)
        for key in ('user', 'bot'):
            ref[key] = {k: v for k, v in ref[key].items() if k in ('id', 'aadObjectId')}
        if result.identity.tenant_id != policy.tenant or not valid_reference(ref, result.identity, policy.app):
            raise ValueError('invalid_reference')
        await asyncio.to_thread(store.capture, result, ref, policy.app)
    except Exception:
        # Fail closed for this recipient; never make legacy opening depend on IO.
        try:
            await asyncio.to_thread(store.disable, result.identity.tenant_id, result.identity.object_id)
        except Exception:
            pass


def enabled_for_context(context, config):
    """Fail-closed presentation check; never creates a link or a reference."""
    policy = Policy.configured(config)
    if policy is None:
        return False
    try:
        from botbuilder.core import TurnContext
        ref = TurnContext.get_conversation_reference(context.activity).serialize()
        ref.pop('activityId', None)
        for key in ('user', 'bot'):
            ref[key] = {k: v for k, v in ref[key].items() if k in ('id', 'aadObjectId')}
        tenant = ref['conversation']['tenantID']
        object_id = ref['user']['aadObjectId']
        identity = SimpleNamespace(member_id=ref['user']['id'], object_id=object_id)
        if tenant != policy.tenant or not valid_reference(ref, identity, policy.app):
            return False
        store = NotificationStore(config.IDENTITY_DB_PATH)
        stored = store.reference_for(tenant, object_id)
        return bool(stored and stored['app'] == policy.app
                    and json.loads(stored['reference']) == ref and store.current(stored))
    except Exception:
        return False
