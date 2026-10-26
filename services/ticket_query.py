"""Shared GLPI 10.0.18 authorization and bounded session. No legacy lookup."""
from contextlib import contextmanager
from datetime import datetime
import re
import time
import requests
from identity.store import user_id

NEW, ASSIGNED, PLANNED, WAITING = 1, 2, 3, 4
REQUESTER = 1
STATUS_LABELS = {NEW: 'Novo', ASSIGNED: 'Em atendimento', PLANNED: 'Em atendimento', WAITING: 'Pendente'}
SEARCH_ID, SEARCH_REQUESTER, SEARCH_STATUS = 2, 4, 12


class QueryError(Exception):
    pass


class TicketQuery:
    MAX_ITEMS = 200
    MAX_REQUESTS = 500
    DEADLINE = 60

    def __init__(self, url, app_token, user_token):
        self.url = url.rstrip('/')
        self.app_token, self.user_token = app_token, user_token

    @contextmanager
    def session(self, *, raw_content=False):
        headers = {'App-Token': self.app_token}
        if raw_content:
            headers['X-GLPI-Sanitized-Content'] = 'false'
        end, calls = time.monotonic() + self.DEADLINE, 0

        def get(path, params=None, *, missing=False):
            nonlocal calls
            guard = getattr(self, "request_guard", None)
            if guard:
                guard()
            calls += 1
            remaining = end - time.monotonic()
            if calls > self.MAX_REQUESTS or remaining <= 0:
                raise QueryError()
            r = requests.get(self.url + path, headers=headers, params=params,
                             timeout=min(5, remaining), allow_redirects=False)
            if missing and r.status_code == 404:
                return None
            if r.status_code not in (200, 206):
                raise QueryError()
            return r

        token = None
        try:
            headers['Authorization'] = 'user_token ' + self.user_token
            data = get('/initSession').json()
            token = data.get('session_token')
            if not isinstance(token, str) or not token:
                raise QueryError()
            del headers['Authorization']
            headers['Session-Token'] = token
            def post_followup(payload, before_post):
                # No retries, redirects or user-provided endpoint. A durable fence
                # is committed immediately before the only HTTP POST.
                if time.monotonic() >= end or calls >= self.MAX_REQUESTS:
                    raise QueryError()
                before_post()
                return requests.post(self.url + '/ITILFollowup', headers=headers,
                                     json={'input': payload}, timeout=5, allow_redirects=False)
            get.post_followup = post_followup
            yield get
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise QueryError() from exc
        finally:
            if token:
                try:
                    requests.get(self.url + '/killSession', headers={'App-Token': self.app_token,
                                 'Session-Token': token}, timeout=5, allow_redirects=False)
                except requests.RequestException:
                    pass

    def relations(self, get, ticket):
        return self.collection(get, f'/Ticket/{ticket}/Ticket_User')

    def collection(self, get, path):
        rows, offset, total = [], 0, None
        seen = set()
        while True:
            r = get(path, {'range': f'{offset}-{offset + 49}', 'get_hateoas': 'false'})
            page = r.json()
            match = re.fullmatch(r'(\d+)-(\d+)/(\d+)', r.headers.get('Content-Range', ''))
            if not isinstance(page, list):
                raise QueryError()
            if not page and offset == 0 and r.status_code == 200 and r.headers.get('Content-Range') in ('0--1/0', '0-0/0'):
                return []
            if not match:
                raise QueryError()
            start, stop, count = map(int, match.groups())
            if start != offset or stop - start + 1 != len(page) or not page or count > self.MAX_ITEMS:
                raise QueryError()
            if total is not None and total != count:
                raise QueryError()
            total = count
            for relation in page:
                rid = user_id(relation.get('id'))
                if rid in seen:
                    raise QueryError()
                seen.add(rid)
            rows.extend(page)
            offset += len(page)
            if offset == total:
                return rows
            if offset > total:
                raise QueryError()

    def checked(self, get, uid, tid, *, include_content=False):
        response = get(f'/Ticket/{tid}', {'get_hateoas': 'false'}, missing=True)
        if response is None:
            return None
        row = response.json()
        if not isinstance(row, dict) or user_id(row.get('id')) != tid:
            raise QueryError()
        if 'status' not in row or str(row.get('is_deleted')) not in ('0', '1'):
            raise QueryError()
        if str(row['is_deleted']) != '0' or str(row.get('status')) not in tuple(map(str, STATUS_LABELS)):
            return None
        relations = self.relations(get, tid)
        if not all(isinstance(x, dict) and all(k in x for k in ('tickets_id', 'users_id', 'type')) for x in relations):
            raise QueryError()
        if not any(str(x['tickets_id']) == str(tid) and str(x['users_id']) == str(uid)
                   and str(x['type']) == str(REQUESTER) for x in relations):
            return None
        if not isinstance(row.get('name'), str):
            raise QueryError()
        datetime.strptime(row['date_mod'], '%Y-%m-%d %H:%M:%S')
        result = {'id': tid, 'title': row['name'], 'status': int(row['status']), 'updated': row['date_mod']}
        if include_content:
            if not isinstance(row.get('content'), str):
                raise QueryError()
            result['content'] = row['content']
        return result

    def list(self, uid):
        uid = user_id(uid)
        with self.session() as get:
            ids, offset, total = set(), 0, None
            while True:
                params = {'is_deleted': 0, 'range': f'{offset}-{offset + 49}',
                          'forcedisplay[0]': SEARCH_ID, 'sort': SEARCH_ID, 'order': 'ASC',
                          'criteria[0][field]': SEARCH_REQUESTER,
                          'criteria[0][searchtype]': 'equals', 'criteria[0][value]': uid}
                for i, status in enumerate(STATUS_LABELS):
                    base = f'criteria[1][criteria][{i}]'
                    params.update({base + '[field]': SEARCH_STATUS, base + '[searchtype]': 'equals',
                                   base + '[value]': status, base + '[link]': 'OR' if i else 'AND'})
                params['criteria[1][link]'] = 'AND'
                data = get('/search/Ticket', params).json()
                count = data['totalcount']
                page = data['data']
                if isinstance(page, dict):
                    page = list(page.values())
                if type(count) is not int or count < 0 or count > self.MAX_ITEMS or not isinstance(page, list):
                    raise QueryError()
                if total is not None and total != count:
                    raise QueryError()
                total = count
                if data['count'] != len(page) or (not page and offset < count):
                    raise QueryError()
                for row in page:
                    tid = user_id(row[str(SEARCH_ID)])
                    if tid in ids:
                        raise QueryError()
                    ids.add(tid)
                offset += len(page)
                if offset == count:
                    break
                if offset > count:
                    raise QueryError()
            result = [item for tid in ids if (item := self.checked(get, uid, tid))]
            return sorted(result, key=lambda x: (x['updated'], x['id']), reverse=True)

    def available(self, uid, tid):
        with self.session() as get:
            return self.checked(get, user_id(uid), user_id(tid)) is not None
