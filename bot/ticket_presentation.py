"""Display-only helpers. No identity, ticket authorization or navigation state."""
from datetime import datetime
from services.ticket_content import passive

SUMMARY_LIMIT = 24


def display_title(title, ticket=None):
    """Remove only known redundant opening labels; keep source data untouched."""
    text = title.strip()
    prefixes = ['Solicitação de ', 'Solicitações de ', 'Solicitação: ', 'Solicitação - ', 'Chamado: ']
    if ticket is not None:
        prefixes = [f'Chamado #{ticket} — ', f'Chamado #{ticket} - '] + prefixes
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()) and text[len(prefix):].strip():
            return text[len(prefix):].strip()
    return text


def title_summary(title):
    text = display_title(title)
    if len(text) <= SUMMARY_LIMIT:
        return text
    shortened = text[:SUMMARY_LIMIT - 1]
    if ' ' in shortened:
        shortened = shortened.rsplit(' ', 1)[0]
    return shortened.rstrip() + '…'


def glpi_date(value):
    """Brazilian display only: no timezone conversion or timezone assumption."""
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y às %H:%M')
    except (ValueError, TypeError):
        return passive(value)
