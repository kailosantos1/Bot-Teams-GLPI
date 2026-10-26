from dataclasses import dataclass
from identity.store import guid, user_id


@dataclass(frozen=True)
class Policy:
    app: str
    tenant: str
    support: frozenset
    integration: frozenset

    @classmethod
    def configured(cls, config):
        try:
            if config.NOTIFICATIONS_ENABLED is not True:
                return None
            support = frozenset(user_id(x.strip()) for x in config.NOTIFICATIONS_SUPPORT_IDS.split(','))
            integration = frozenset(user_id(x.strip()) for x in config.NOTIFICATIONS_INTEGRATION_IDS.split(','))
            if not support or not integration or support & integration:
                return None
            if not all(getattr(config, x, '').strip() for x in ('MICROSOFT_APP_PASSWORD', 'GLPI_URL', 'GLPI_APP_TOKEN', 'GLPI_USER_TOKEN')):
                return None
            guid(config.MICROSOFT_APP_TENANT_ID)
            return cls(guid(config.MICROSOFT_APP_ID), guid(config.IDENTITY_ALLOWED_TENANT_ID), support, integration)
        except (ValueError, TypeError, AttributeError):
            return None

    def eligible(self, row, uid, excluded):
        try:
            author = user_id(row.get('users_id'))
            return (type(row.get('is_private')) in (int, str) and str(row['is_private']) == '0'
                    and ('is_deleted' not in row or type(row['is_deleted']) in (int, str) and str(row['is_deleted']) == '0')
                    and author in self.support and author not in self.integration
                    and author != uid and user_id(row['id']) not in excluded)
        except (ValueError, TypeError, KeyError):
            return False
