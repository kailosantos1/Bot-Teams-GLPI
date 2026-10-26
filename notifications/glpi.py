"""Bounded GLPI reads using the existing requester authorization contract."""
from datetime import datetime
from identity.store import user_id
from services.ticket_conversation import TicketConversation, AccessDenied
from services.ticket_query import QueryError


class NotificationQuery(TicketConversation):
    def active_user(self, get, uid):
        r = get(f'/User/{user_id(uid)}', {'get_hateoas': 'false'}, missing=True)
        if r is None:
            raise AccessDenied()
        row = r.json()
        if not isinstance(row, dict) or user_id(row.get('id')) != uid:
            raise QueryError()
        if str(row.get('is_active')) == '0' or str(row.get('is_deleted')) == '1':
            raise AccessDenied()
        if str(row.get('is_active')) != '1' or str(row.get('is_deleted')) != '0':
            raise QueryError()

    @staticmethod
    def validate(row, tid):
        if not isinstance(row, dict) or row.get('itemtype') != 'Ticket' or user_id(row.get('items_id')) != tid:
            raise QueryError()
        user_id(row.get('id'))
        if not isinstance(row.get('date_creation'), str):
            raise QueryError()
        datetime.strptime(row['date_creation'], '%Y-%m-%d %H:%M:%S')
        return row

    def snapshot(self, uid, tid):
        with self.session() as get:
            self.active_user(get, uid)
            self.authorize(get, uid, tid)
            rows = self.collection(get, f'/Ticket/{tid}/ITILFollowup')
            rows = [self.validate(row, tid) for row in rows]
            self.authorize(get, uid, tid)
            return sorted(rows, key=lambda row: user_id(row['id']))

    def notification(self, uid, tid, fid):
        with self.session() as get:
            self.active_user(get, uid)
            ticket = self.authorize(get, uid, tid)
            response = get(f'/ITILFollowup/{user_id(fid)}', {'get_hateoas': 'false'}, missing=True)
            if response is None:
                raise AccessDenied()
            row = self.validate(response.json(), tid)
            if user_id(row['id']) != fid:
                raise QueryError()
            self.authorize(get, uid, tid)
            return ticket, row
