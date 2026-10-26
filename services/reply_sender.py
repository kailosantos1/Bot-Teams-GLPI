"""Persistent reservation and conservative classification of write outcomes."""
from services.ticket_conversation import AccessDenied
from identity.store import Conflict


class ReplySender:
    def __init__(self, store, conversation):
        self.store, self.conversation = store, conversation

    def send(self, operation, binding, ticket):
        row = self.store.reserve(operation, binding, ticket)
        if row is None:
            current = self.store.get_operation(operation, binding, ticket)
            return ('denied' if current['state'] == 'ready' else current['state']) if current else 'expired'
        token = row['reservation']
        try:
            followup = self.conversation.reply(binding[2], ticket, row['body'],
                lambda: self.store.mark_submitting(operation, token))
            self.store.finish(operation, token, followup)
            return 'sent'
        except Exception as error:
            # Never infer "not written" from a network exception. The persisted
            # fence tells whether POST could have started, including DB failures.
            try:
                current = self.store.get_operation(operation, binding, ticket)
                if current and current['state'] == 'sent':
                    return 'sent'
                if current and current['state'] == 'reserved':
                    self.store.release(operation, token)
                    return 'denied' if isinstance(error, (AccessDenied, Conflict)) else 'retry'
                if current and current['state'] == 'submitting':
                    self.store.finish(operation, token)
            except Exception:
                pass
            return 'uncertain'
