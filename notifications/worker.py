"""Single dedicated worker. No form processors, UserState or inbound identity resolver."""
import asyncio
import json
import secrets
import time
from types import SimpleNamespace
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from identity.store import Conflict, user_id
from services.ticket_conversation import AccessDenied
from services.ticket_content import html_text
from services.ticket_query import QueryError
from .capture import valid_reference
from .lifecycle import blocking


class MembershipUnavailable(QueryError):
    """Not classified yet; never consume a watermark or discard a queued event."""
    pass


class BudgetExceeded(QueryError):
    pass


def retry_after(error):
    response = getattr(error, 'response', None)
    headers = getattr(response, 'headers', {}) or {}
    value = headers.get('Retry-After', '')
    try:
        seconds = int(value)
    except (ValueError, TypeError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 60
    return max(1, min(86400, seconds))


def notice(event, title):
    from bot.cards import Activity, HeroCard, CardAction, _card_attachment
    from bot.ticket_consult import safe_title
    text = (f"🔔 Nova resposta no chamado #{event['ticket']}\n{safe_title(html_text(title))}\n\n"
            'O suporte enviou uma mensagem.')
    button = CardAction(type='messageBack', title='Ver chamado', text='Ver chamado',
                        display_text='Ver chamado', value={'notification': event['id']})
    return Activity(type='message', attachments=[_card_attachment(HeroCard(text=text, buttons=[button]))])


class SDKTransport:
    def __init__(self, adapter, app):
        self.adapter, self.app = adapter, app

    async def send(self, reference, activity, before_send):
        from botbuilder.schema import ConversationReference
        receipt = None

        async def callback(context):
            nonlocal receipt
            # SDK continuation is outbound only. Never used as an authenticated
            # inbound activity, never passed to the activity identity resolver.
            from botbuilder.core import BotAdapter
            client = context.turn_state[BotAdapter.BOT_CONNECTOR_CLIENT_KEY]
            # msrest defaults include transport retries. Disable them explicitly:
            # only our durable queue may decide whether another attempt is safe.
            client.config.retry_policy.retries = 0
            client.config.redirect_policy.allow = False
            client.config.connection.timeout = 5
            await before_send()
            result = await context.send_activity(activity)
            receipt = result.id if result else None
        await self.adapter.continue_conversation(ConversationReference().deserialize(reference), callback, bot_id=self.app)
        return receipt


class Worker:
    MAX_RECIPIENTS = 10
    MAX_TICKETS = 50
    MAX_SENDS = 20
    MAX_CALLS = 250
    MAX_SECONDS = 120
    MAX_ATTEMPTS = 5

    def __init__(self, store, query, policy, transport):
        self.store, self.query, self.policy, self.transport = store, query, policy, transport
        self.owner = secrets.token_urlsafe(24)

    def guard(self):
        if not self.store.has_lease(self.owner):
            raise BudgetExceeded()
        self.calls += 1
        if self.calls > (150 if getattr(self, "observing", False) else self.MAX_CALLS) or time.monotonic() >= (self.deadline - 60 if getattr(self, "observing", False) else self.deadline):
            raise BudgetExceeded()

    def valid(self, ref):
        if ref['tenant'] != self.policy.tenant or ref['app'] != self.policy.app or not self.store.current(ref):
            return False
        try:
            reference = json.loads(ref['reference'])
            identity = SimpleNamespace(member_id=reference['user']['id'], object_id=ref['object_id'])
            return valid_reference(reference, identity, self.policy.app)
        except (TypeError, ValueError, KeyError):
            return False

    def exclusions(self):
        with self.store.connection() as db:
            return {r[0] for r in db.execute('SELECT followup_id FROM reply_operations WHERE followup_id IS NOT NULL')}

    def eligible(self, row, uid, excluded, membership_cache=None):
        def membership(author, groups):
            try:
                if membership_cache is not None and author in membership_cache:
                    return membership_cache[author]
                result = self.query.author_in_groups(author, groups)
                if type(result) is not bool:
                    raise QueryError()
                if membership_cache is not None:
                    membership_cache[author] = result
                return result
            except BudgetExceeded:
                raise
            except Exception:
                # Even HTTP 403/404 here is not a Teams reference failure and
                # cannot prove that the author has no group membership.
                raise MembershipUnavailable() from None
        return self.policy.eligible(row, uid, excluded, membership)

    def observe(self):
        count = 0
        excluded = self.exclusions()
        for ref in self.store.references(self.MAX_RECIPIENTS):
            self.guard()
            self.store.touch(ref)
            if not self.valid(ref):
                self.store.disable(ref['tenant'], ref['object_id'])
                continue
            try:
                tickets = self.query.list(ref['uid'])
                self.store.reconcile(ref, {t['id'] for t in tickets})
                for ticket in self.store.ordered_tickets(ref, tickets):
                    if count >= self.MAX_TICKETS:
                        return
                    count += 1
                    self.guard()
                    rows = self.query.snapshot(ref['uid'], ticket['id'])
                    ids = {user_id(row['id']) for row in rows}
                    # Reuse only within this complete ticket snapshot. Delivery
                    # always performs fresh reads, including before_send.
                    membership_cache = {}
                    eligible = {user_id(row['id']) for row in rows
                                if self.eligible(row, ref['uid'], excluded, membership_cache)}
                    self.guard()
                    self.store.observe(ref, ticket['id'], ids, eligible, self.owner)
            except AccessDenied:
                # A ticket may close or lose its requester during the scan.
                # This does not revoke unrelated tickets or the personal reference.
                continue
            except BudgetExceeded:
                return
            except (QueryError, Conflict, ValueError):
                # Complete snapshot required; leave previous baseline unchanged.
                continue

    async def cycle(self, *, simulate=False):
        await blocking(self.store.prepare)
        if not await blocking(self.store.lease, self.owner):
            return {'busy': True}
        self.calls, self.deadline = 0, time.monotonic() + self.MAX_SECONDS
        self.query.request_guard = self.guard
        sent = 0
        try:
            await blocking(self.store.cleanup)
            self.observing = True
            try:
                await blocking(self.observe)
            except BudgetExceeded:
                pass
            self.observing = False
            if not simulate:
                for _ in range(self.MAX_SENDS):
                    if time.monotonic() >= self.deadline:
                        break
                    event = await blocking(self.store.reserve)
                    if not event:
                        break
                    sent += await self.deliver(event)
            return {'busy': False, 'sent': sent, 'simulation': simulate}
        finally:
            await blocking(self.store.release, self.owner)

    async def deliver(self, event):
        submitting = False
        membership_in_progress = False
        ref = None
        async def finish(state, **kwargs):
            await blocking(self.store.transition, event, state, **kwargs)
        try:
            await blocking(self.guard)
            ref = await blocking(self.store.reference_for, event['tenant'], event['object_id'])
            if (not ref or ref['generation'] != event['generation'] or ref['revision'] != event['revision']
                    or not await blocking(self.valid, ref)):
                await finish('discarded')
                return 0
            ticket, row = await blocking(self.query.notification, ref['uid'], event['ticket'], event['followup'])
            excluded = await blocking(self.exclusions)
            if not await blocking(self.eligible, row, ref['uid'], excluded):
                await finish('discarded')
                return 0
            reference = json.loads(ref['reference'])
            async def before_send():
                nonlocal submitting, membership_in_progress
                await blocking(self.guard)
                if not await blocking(self.store.has_lease, self.owner):
                    raise Conflict('lease_lost')
                if not await blocking(self.valid, ref):
                    raise AccessDenied()
                # Recheck after connector/token preparation, immediately before send.
                _, latest = await blocking(self.query.notification, ref['uid'], event['ticket'], event['followup'])
                excluded_now = await blocking(self.exclusions)
                membership_in_progress = True
                allowed = await blocking(self.eligible, latest, ref['uid'], excluded_now)
                membership_in_progress = False
                if not allowed:
                    raise AccessDenied()
                if not await blocking(self.store.has_lease, self.owner):
                    raise Conflict('lease_lost')
                # Fence before any possible send. Crash after here is uncertain.
                await finish('submitting')
                submitting = True
            activity = await blocking(notice, event, ticket['title'])
            receipt = await asyncio.wait_for(self.transport.send(reference, activity, before_send), timeout=15)
            await finish('sent' if receipt else 'uncertain', receipt=receipt)
            return int(bool(receipt))
        except AccessDenied:
            await finish('discarded')
        except (MembershipUnavailable, BudgetExceeded):
            # A failed classification is not a send attempt. Refund only while
            # reserved, atomically with pending, so reserve's five-attempt cap
            # cannot terminate a membership outage. Never refund after the fence.
            await finish('uncertain' if submitting else 'pending',
                         classification_retry=not submitting,
                         delay=min(3600, 30 * 2 ** min(event['attempts'] - 1, 7)))
        except Exception as error:
            status = getattr(getattr(error, 'response', None), 'status_code', None)
            if isinstance(error, asyncio.TimeoutError) and membership_in_progress and not submitting:
                # wait_for may cancel before_send while its membership thread is
                # still reading. No send fence was crossed; retain classification.
                await finish('pending', classification_retry=True,
                             delay=min(3600, 30 * 2 ** min(event['attempts'] - 1, 7)))
            elif status in (400, 401, 403, 404, 410):
                await finish('rejected')
                if status in (403, 404, 410) and ref:
                    await blocking(self.store.disable, ref['tenant'], ref['object_id'])
            elif status == 429:
                await finish('pending' if event['attempts'] < self.MAX_ATTEMPTS else 'failed', delay=retry_after(error))
            elif submitting:
                await finish('uncertain')
            else:
                await finish('pending' if event['attempts'] < self.MAX_ATTEMPTS else 'failed', delay=min(3600, 30 * 2 ** (event['attempts'] - 1)))
        return 0
