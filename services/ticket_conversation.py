"""Authorized Ticket + ITILFollowup only, GLPI 10.0.18 REST v1."""
from datetime import datetime
from html import escape
import requests
from identity.store import user_id
from services.ticket_query import TicketQuery, QueryError
from services.ticket_content import html_text, passive, description_text


class AccessDenied(Exception):
    pass


class SendUncertain(Exception):
    pass


class TicketConversation(TicketQuery):
    def authorize(self, get, uid, tid, *, content=False):
        row = self.checked(get, user_id(uid), user_id(tid), include_content=content)
        if row is None:
            raise AccessDenied()
        return row

    def details(self, uid, tid):
        with self.session(raw_content=True) as get:
            row = self.authorize(get, uid, tid, content=True)
            row['title'] = html_text(row['title'])
            row['content'] = description_text(row['content'])
            return row

    def author(self, get, uid):
        try:
            uid = user_id(uid)
            r = get(f'/User/{uid}', {'get_hateoas': 'false'}, missing=True)
            if r is None:
                return 'Autor não identificado'
            data = r.json()
            if user_id(data['id']) != uid:
                return 'Autor não identificado'
            names = [data.get('firstname', ''), data.get('realname', '')]
            if not all(isinstance(x, str) for x in names):
                return 'Autor não identificado'
            name = ' '.join(names).strip()
            return html_text(name)[:120] or 'Autor não identificado'
        except (QueryError, ValueError, TypeError, KeyError, requests.RequestException):
            return 'Autor não identificado'

    def history(self, uid, tid, trusted_followups=None):
        trusted_followups = set(trusted_followups or ())
        with self.session(raw_content=True) as get:
            self.authorize(get, uid, tid)
            rows = self.collection(get, f'/Ticket/{tid}/ITILFollowup')
            public = []
            authors = {}
            for row in rows:
                # Validate parent even for private/unsupported entries. A mixed
                # collection is a contract failure, never a public timeline.
                if row.get('itemtype') != 'Ticket' or str(row.get('items_id')) != str(tid):
                    raise QueryError()
                privacy = row.get('is_private')
                if type(privacy) not in (int, str) or str(privacy) != '0':
                    continue
                if not isinstance(row.get('content'), str) or not isinstance(row.get('date'), str):
                    raise QueryError()
                datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S')
                followup_id = user_id(row['id'])
                trusted = followup_id in trusted_followups
                author_id = str(uid if trusted else row.get('users_id'))
                if author_id not in authors:
                    authors[author_id] = self.author(get, uid if trusted else row.get('users_id'))
                content = html_text(row['content'])
                if trusted:
                    current = f'Origem: Microsoft Teams — {authors[author_id]}'
                    legacy = current + ' (requerente com identidade validada).'
                    fallback = 'Origem: Microsoft Teams — Requerente com identidade validada'
                    legacy_fallback = fallback + ' (requerente com identidade validada).'
                    first, separator, remainder = content.partition('\n')
                    if separator and first in {current, legacy, fallback, legacy_fallback}:
                        # html_text separates adjacent paragraphs with two newlines.
                        # partition consumed the first; remove only the structural
                        # second newline, never arbitrary whitespace from the body.
                        content = remainder[1:] if remainder.startswith('\n') else remainder
                public.append({'id': user_id(row['id']), 'date': row['date'],
                               'author': authors[author_id], 'content': content})
            # Authorization again after paging, before returning content.
            self.authorize(get, uid, tid)
            return sorted(public, key=lambda x: (x['date'], x['id']), reverse=True)

    def reply(self, uid, tid, text, before_post):
        with self.session(raw_content=True) as get:
            self.authorize(get, uid, tid)
            label = self.author(get, uid)
            if label == 'Autor não identificado':
                label = 'Requerente com identidade validada'
            origin = f'Origem: Microsoft Teams — {label}'
            content = '<p>' + escape(origin) + '</p><p>' + escape(text).replace('\n', '<br>') + '</p>'
            payload = {'itemtype': 'Ticket', 'items_id': user_id(tid), 'is_private': 0, 'content': content, '_no_reopen': True}
            # Omit users_id: native author is the authenticated API account.
            self.authorize(get, uid, tid)
            try:
                r = get.post_followup(payload, before_post)
                if r.status_code != 201:
                    raise SendUncertain()
                return user_id(r.json()['id'])
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                raise SendUncertain() from exc
