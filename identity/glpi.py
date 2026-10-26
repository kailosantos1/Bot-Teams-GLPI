"""Consulta exata por ID, sem cache, nomes ou alterações de dados GLPI."""
from dataclasses import dataclass
import requests
from .store import user_id


@dataclass(frozen=True)
class UserCheck:
    code: str
    glpi_user_id: int | None = None


class GLPIUserReader:
    def __init__(self, url, app_token, user_token):
        self.url = url.rstrip('/')
        self.app_token = app_token
        self.user_token = user_token

    def check(self, requested_id):
        requested_id = user_id(requested_id)
        headers = {'App-Token': self.app_token}
        session = None
        try:
            response = requests.get(self.url + '/initSession', headers={
                **headers, 'Authorization': 'user_token ' + self.user_token},
                timeout=10, allow_redirects=False)
            if response.status_code != 200:
                return UserCheck('glpi_unavailable')
            data = response.json()
            session = data.get('session_token') if isinstance(data, dict) else None
            if not isinstance(session, str) or not session:
                return UserCheck('glpi_incomplete')
            headers['Session-Token'] = session
            response = requests.get(self.url + f'/User/{requested_id}', headers=headers,
                                    timeout=10, allow_redirects=False)
            if response.status_code == 404:
                return UserCheck('glpi_missing')
            if response.status_code != 200:
                return UserCheck('glpi_unavailable')
            data = response.json()
            if not isinstance(data, dict) or user_id(data.get('id')) != requested_id:
                return UserCheck('glpi_incomplete')
            # Aceita somente as representações explícitas documentadas de flags.
            if str(data.get('is_active')) not in ('0', '1') or str(data.get('is_deleted')) not in ('0', '1'):
                return UserCheck('glpi_incomplete')
            if str(data['is_deleted']) == '1':
                return UserCheck('glpi_deleted')
            if str(data['is_active']) != '1':
                return UserCheck('glpi_inactive')
            return UserCheck('ok', requested_id)
        except (requests.RequestException, ValueError, TypeError):
            return UserCheck('glpi_unavailable')
        finally:
            if session:
                try:
                    requests.get(self.url + '/killSession', headers=headers,
                                 timeout=10, allow_redirects=False)
                except requests.RequestException:
                    pass
