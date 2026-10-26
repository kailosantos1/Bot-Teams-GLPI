"""Bounded identity diagnostics: never format results, contexts or exceptions."""
import logging
from .service import IdentityResult

logger = logging.getLogger('bot.identity')
FAILURE_CODES = frozenset({
    'unauthenticated', 'authentication_configuration', 'authentication_disabled',
    'authentication_failed', 'sdk_unavailable', 'wrong_channel', 'personal_only',
    'tenant_denied', 'identity_missing', 'identity_mismatch', 'teams_unavailable',
    'link_missing', 'link_revoked', 'link_changed', 'identity_unavailable',
    'glpi_missing', 'glpi_inactive', 'glpi_deleted', 'glpi_incomplete', 'glpi_unavailable',
})


def log_identity_failure(result):
    if result is None:
        code = 'identity_unavailable'
    elif isinstance(result, IdentityResult) and isinstance(result.code, str) and result.code in FAILURE_CODES:
        code = result.code
    elif isinstance(result, IdentityResult) and result.code == 'ok' and result.identity is None:
        code = 'identity_missing'
    else:
        code = 'identity_unavailable'
    logger.warning('identity_failure code=%s', code)
