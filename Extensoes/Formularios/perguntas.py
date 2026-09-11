"""
list_form_questions.py
------------------------
Script standalone para listar, direto da API do GLPI, todos os
formulários do Formcreator e as perguntas de cada um -- com o ID
REAL de cada pergunta, exatamente como o GLPI enxerga.

Serve pra comparar com o que está configurado no forms.yaml e achar
divergência de ID (causa mais comum de "a resposta não aparece certo
no ticket").

COMO USAR:
  1. Coloque este arquivo na MESMA pasta do seu .env (mesmas
     variáveis GLPI_URL / GLPI_APP_TOKEN / GLPI_USER_TOKEN que o bot
     já usa).
  2. Rode: python list_form_questions.py
  3. (Opcional) Se quiser ver só UM formulário específico, ajuste
     FORM_ID_FILTRO abaixo com o ID dele -- olhando a primeira parte
     da saída você já descobre o ID de cada formulário.

Requer: pip install requests python-dotenv
"""

import os
import sys
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# CONFIGURAÇÃO DO SCRIPT - ajuste aqui se quiser
# ---------------------------------------------------------------------
FORM_ID_FILTRO = None   # <-- None = lista TODOS os formulários. Ou coloque um ID, ex: 5

ENV_PATH = Path(__file__).parent / ".env"
# ---------------------------------------------------------------------

load_dotenv(dotenv_path=ENV_PATH)

GLPI_URL = os.getenv("GLPI_URL", "").rstrip("/")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
GLPI_USER_TOKEN = os.getenv("GLPI_USER_TOKEN")


def log(msg: str = ""):
    print(msg)


def get_session_token() -> str | None:
    headers = {
        "Content-Type": "application/json",
        "App-Token": GLPI_APP_TOKEN,
        "Authorization": f"user_token {GLPI_USER_TOKEN}",
    }
    res = requests.post(f"{GLPI_URL}/initSession", headers=headers, timeout=10)
    if res.status_code == 200:
        return res.json().get("session_token")
    log(f"❌ Erro ao autenticar: {res.status_code} - {res.text}")
    return None


def kill_session(session_token: str):
    headers = {"App-Token": GLPI_APP_TOKEN, "Session-Token": session_token}
    try:
        requests.get(f"{GLPI_URL}/killSession", headers=headers, timeout=5)
    except Exception:
        pass


def list_forms(headers: dict) -> list[dict]:
    """Lista todos os formulários do Formcreator."""
    res = requests.get(
        f"{GLPI_URL}/PluginFormcreatorForm",
        headers=headers,
        params={"range": "0-200"},
        timeout=15,
    )
    if res.status_code not in (200, 206):
        log(f"❌ Erro ao listar formulários: {res.status_code} - {res.text}")
        return []

    data = res.json()
    if not isinstance(data, list):
        data = [data]
    return data


def list_sections(form_id: int, headers: dict) -> list[dict]:
    res = requests.get(
        f"{GLPI_URL}/PluginFormcreatorForm/{form_id}/PluginFormcreatorSection",
        headers=headers,
        params={"range": "0-100"},
        timeout=15,
    )
    if res.status_code != 200:
        return []
    data = res.json()
    if not isinstance(data, list):
        data = [data]
    return data


def list_questions(section_id: int, headers: dict) -> list[dict]:
    res = requests.get(
        f"{GLPI_URL}/PluginFormcreatorSection/{section_id}/PluginFormcreatorQuestion",
        headers=headers,
        params={"range": "0-100"},
        timeout=15,
    )
    if res.status_code != 200:
        return []
    data = res.json()
    if not isinstance(data, list):
        data = [data]
    return data


def list_question_options(question_id: int, headers: dict) -> list[str]:
    """
    Busca as opções (itens) de uma pergunta do tipo select/radio/checkbox,
    já ordenadas -- assim dá pra conferir se a ORDEM das opções no GLPI
    bate com a ordem que está no forms.yaml (outra causa comum do bug:
    a opção certa é selecionada pelo texto, mas se o texto no YAML tiver
    um espaço/acento diferente do GLPI, a comparação falha).
    """
    res = requests.get(
        f"{GLPI_URL}/PluginFormcreatorQuestion/{question_id}/PluginFormcreatorQuestion_Item",
        headers=headers,
        params={"range": "0-100"},
        timeout=15,
    )
    if res.status_code != 200:
        return []

    data = res.json()
    if not isinstance(data, list):
        data = [data]

    # Cada item costuma ter um campo 'value' ou 'name' com o texto da opção
    opcoes = []
    for item in data:
        texto = item.get("value") or item.get("name") or "?"
        opcoes.append(texto)
    return opcoes


def main():
    log("=" * 70)
    log("Listagem de formulários e perguntas do GLPI (Formcreator)")
    log("=" * 70)

    if not GLPI_URL or not GLPI_APP_TOKEN or not GLPI_USER_TOKEN:
        log("❌ GLPI_URL / GLPI_APP_TOKEN / GLPI_USER_TOKEN não encontrados no .env")
        sys.exit(1)

    session_token = get_session_token()
    if not session_token:
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "App-Token": GLPI_APP_TOKEN,
        "Session-Token": session_token,
    }

    try:
        forms = list_forms(headers)

        if not forms:
            log("Nenhum formulário encontrado.")
            return

        log(f"\n{len(forms)} formulário(s) encontrado(s):\n")

        for form in forms:
            form_id = form.get("id")
            form_name = form.get("name", "(sem nome)")

            if FORM_ID_FILTRO is not None and form_id != FORM_ID_FILTRO:
                continue

            log("-" * 70)
            log(f"📋 FORMULÁRIO  id={form_id}   nome='{form_name}'")
            log("-" * 70)

            sections = list_sections(form_id, headers)
            if not sections:
                log("   (sem seções/perguntas)")
                continue

            for section in sections:
                section_id = section.get("id")
                section_name = section.get("name", "")
                questions = list_questions(section_id, headers)

                if not questions:
                    continue

                log(f"  Seção: '{section_name}' (id={section_id})")

                for q in questions:
                    q_id = q.get("id")
                    q_name = q.get("name", "(sem label)")
                    q_type = q.get("fieldtype", "?")

                    log(f"    • id={q_id:<5} tipo={q_type:<12} label='{q_name}'")

                    if q_type in ("select", "radios", "checkboxes", "multiselect"):
                        opcoes = list_question_options(q_id, headers)
                        if opcoes:
                            for opt in opcoes:
                                log(f"          - opção: '{opt}'")

            log("")

        log("=" * 70)
        log("Compare o 'id=' de cada pergunta acima com o 'id' configurado no")
        log("seu forms.yaml -- e o texto das opções com o que está lá também.")
        log("=" * 70)

    finally:
        kill_session(session_token)


if __name__ == "__main__":
    main()