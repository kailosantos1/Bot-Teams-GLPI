"""Read-only exact email association, GLPI 10.0.18 REST v1.

Search option User/5 joins all UserEmail children. Search output is only a
candidate list; never a proof. Compare every raw child email, not rendered
search columns. No GLPI user/email writes, names, UPN or legacy caches.
"""
import re
import unicodedata
from .glpi import UserCheck
from .store import user_id
from services.ticket_query import TicketQuery, QueryError


def normalize_email(value):
    if not isinstance(value, str):
        raise ValueError('email_missing')
    value = value.strip().lower()
    if (not value or len(value) > 320 or value.count('@') != 1
            or any(c.isspace() or unicodedata.category(c)[0] == 'C' for c in value)
            or not all(value.split('@'))):
        raise ValueError('email_invalid')
    return value


class GLPIEmailLookup(TicketQuery):
    def candidates(self, get, email):
        ids, offset, total = set(), 0, None
        while True:
            params = {'range': f'{offset}-{offset + 49}', 'is_deleted': 0,
                      'forcedisplay[0]': 2, 'sort': 2, 'order': 'ASC',
                      'criteria[0][field]': 5, 'criteria[0][searchtype]': 'contains',
                      'criteria[0][value]': email}
            data = get('/search/User', params).json()
            count, page = data['totalcount'], data['data']
            if isinstance(page, dict):
                page = list(page.values())
            if (type(count) is not int or count < 0 or count > self.MAX_ITEMS
                    or not isinstance(page, list) or type(data['count']) is not int
                    or data['count'] != len(page) or total is not None and total != count):
                raise QueryError()
            total = count
            if not count and offset == 0 and not page:
                return set()
            match = re.fullmatch(r'(\d+)-(\d+)/(\d+)', data.get('content-range', ''))
            if not match or not page:
                raise QueryError()
            start, stop, reported = map(int, match.groups())
            if start != offset or stop - start + 1 != len(page) or reported != count or stop >= count:
                raise QueryError()
            for row in page:
                ids.add(user_id(row['2']))
            offset += len(page)
            if offset == total:
                return ids

    def emails(self, get, uid):
        offset, total, seen, emails = 0, None, set(), []
        while True:
            response = get(f'/User/{uid}/UserEmail', {'range': f'{offset}-{offset + 49}',
                           'get_hateoas': 'false', 'expand_dropdowns': 'false'})
            rows = response.json()
            header = response.headers.get('Content-Range')
            if rows == [] and offset == 0 and response.status_code == 200 and header in (None, '0--1/0', '0-0/0'):
                return []
            match = re.fullmatch(r'(\d+)-(\d+)/(\d+)', header or '')
            if not isinstance(rows, list) or not rows or not match:
                raise QueryError()
            start, stop, count = map(int, match.groups())
            if (start != offset or stop - start + 1 != len(rows) or stop >= count
                    or count > self.MAX_ITEMS or total is not None and total != count):
                raise QueryError()
            total = count
            for row in rows:
                eid = user_id(row['id'])
                if eid in seen or user_id(row['users_id']) != uid or not isinstance(row['email'], str):
                    raise QueryError()
                seen.add(eid)
                # Empty addresses are not matches; do not rewrite stored values.
                emails.append(row['email'].strip().lower())
            offset += len(rows)
            if offset == total:
                return emails

    def find(self, email):
        try:
            email = normalize_email(email)
            with self.session(raw_content=True) as get:
                matches = set()
                for uid in sorted(self.candidates(get, email)):
                    response = get(f'/User/{uid}', {'get_hateoas': 'false', 'expand_dropdowns': 'false'})
                    row = response.json()
                    if not isinstance(row, dict) or user_id(row.get('id')) != uid:
                        raise QueryError()
                    if any(type(row.get(field)) not in (int, str) or str(row[field]) not in ('0', '1')
                           for field in ('is_active', 'is_deleted')):
                        raise QueryError()
                    if str(row['is_active']) != '1' or str(row['is_deleted']) != '0':
                        continue
                    if email in self.emails(get, uid):
                        matches.add(uid)
                if not matches:
                    return UserCheck('email_no_match')
                if len(matches) != 1:
                    return UserCheck('email_ambiguous')
                return UserCheck('ok', next(iter(matches)))
        except (QueryError, ValueError, TypeError, KeyError, AttributeError):
            return UserCheck('glpi_unavailable')
