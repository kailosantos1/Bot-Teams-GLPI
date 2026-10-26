"""Bounded GLPI reads using the existing requester authorization contract."""
from datetime import datetime
import re
from identity.store import user_id
from services.ticket_conversation import TicketConversation, AccessDenied
from services.ticket_query import QueryError


class NotificationQuery(TicketConversation):
    def author_in_groups(self, author, group_ids):
        """Direct Group_User rows only, GLPI 10.0.18 REST v1; no names/tree/cache.

        Validate every page even after a match. An incomplete collection cannot
        establish either membership or confirmed nonmembership.
        """
        author = user_id(author)
        allowed = frozenset(user_id(group) for group in group_ids)
        if not allowed:
            return False
        with self.session() as get:
            offset, total, seen, groups = 0, None, set(), set()
            while True:
                response = get(f'/User/{author}/Group_User', {
                    'range': f'{offset}-{offset + 49}', 'get_hateoas': 'false',
                    'expand_dropdowns': 'false'})
                rows = response.json()
                content_range = response.headers.get('Content-Range')
                # APIRest 10.0.18 omits Content-Range when totalcount == 0.
                if (rows == [] and offset == 0 and response.status_code == 200
                        and content_range in (None, '0--1/0', '0-0/0')):
                    return False
                match = re.fullmatch(r'(\d+)-(\d+)/(\d+)', content_range or '')
                if not isinstance(rows, list) or not rows or not match:
                    raise QueryError()
                start, stop, count = map(int, match.groups())
                if (start != offset or stop - start + 1 != len(rows)
                        or count > self.MAX_ITEMS or stop >= count
                        or total is not None and total != count):
                    raise QueryError()
                total = count
                for row in rows:
                    if not isinstance(row, dict):
                        raise QueryError()
                    relation_id = user_id(row.get('id'))
                    if relation_id in seen or user_id(row.get('users_id')) != author:
                        raise QueryError()
                    seen.add(relation_id)
                    groups.add(user_id(row.get('groups_id')))
                offset += len(rows)
                if offset == total:
                    return bool(groups & allowed)

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
