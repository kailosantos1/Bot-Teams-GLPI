"""
debug_question_options.py
--------------------------
Mostra o conteúdo bruto (incluindo o campo 'values') das perguntas do
Formcreator, pra comparar com o texto configurado no forms.yaml.

Uso:
    python debug_question_options.py 106 107 109 111

Se não passar nenhum ID, usa a lista padrão abaixo (perguntas do
formulário FlexSmart que usam radios).
"""

import sys
import json
import requests
from config import settings

DEFAULT_IDS = [106, 107, 109, 111]


def get_session() -> str:
    headers = {
        "Content-Type": "application/json",
        "App-Token": settings.GLPI_APP_TOKEN,
        "Authorization": f"user_token {settings.GLPI_USER_TOKEN}",
    }
    res = requests.post(f"{settings.GLPI_URL.rstrip('/')}/initSession", headers=headers, timeout=10)
    res.raise_for_status()
    return res.json()["session_token"]


def kill_session(session_token: str) -> None:
    headers = {
        "App-Token": settings.GLPI_APP_TOKEN,
        "Session-Token": session_token,
    }
    try:
        requests.get(f"{settings.GLPI_URL.rstrip('/')}/killSession", headers=headers, timeout=5)
    except Exception:
        pass


def main():
    ids = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else DEFAULT_IDS

    session_token = get_session()
    headers = {
        "Content-Type": "application/json",
        "App-Token": settings.GLPI_APP_TOKEN,
        "Session-Token": session_token,
    }

    try:
        for q_id in ids:
            url = f"{settings.GLPI_URL.rstrip('/')}/PluginFormcreatorQuestion/{q_id}"
            res = requests.get(url, headers=headers, timeout=10)

            print("=" * 70)
            print(f"Pergunta id={q_id}  (status {res.status_code})")
            print("=" * 70)

            if res.status_code != 200:
                print(res.text)
                print()
                continue

            data = res.json()
            label = data.get("name") or data.get("label")
            values_raw = data.get("values")

            print(f"label: {label}")
            print(f"fieldtype: {data.get('fieldtype')}")
            print(f"values (bruto): {values_raw!r}")

            # 'values' costuma vir como uma string JSON dentro do JSON --
            # tenta decodificar de novo pra mostrar a lista de opções legível
            if values_raw:
                try:
                    parsed = json.loads(values_raw)
                    print(f"values (decodificado): {json.dumps(parsed, ensure_ascii=False, indent=2)}")
                except (json.JSONDecodeError, TypeError):
                    pass

            print()
    finally:
        kill_session(session_token)


if __name__ == "__main__":
    main()