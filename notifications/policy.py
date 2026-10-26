from dataclasses import dataclass
from identity.store import guid, user_id


@dataclass(frozen=True)
class Policy:
    app: str
    tenant: str
    support_groups: frozenset
    integration: frozenset

    @classmethod
    def configured(cls, config):
        try:
            if config.NOTIFICATIONS_ENABLED is not True:
                return None
            support_groups = frozenset(user_id(x.strip()) for x in config.NOTIFICATIONS_SUPPORT_GROUP_IDS.split(','))
            integration = frozenset(user_id(x.strip()) for x in config.NOTIFICATIONS_INTEGRATION_IDS.split(','))
            if not support_groups or not integration:
                return None
            if not all(getattr(config, x, '').strip() for x in ('MICROSOFT_APP_PASSWORD', 'GLPI_URL', 'GLPI_APP_TOKEN', 'GLPI_USER_TOKEN')):
                return None
            guid(config.MICROSOFT_APP_TENANT_ID)
            return cls(guid(config.MICROSOFT_APP_ID), guid(config.IDENTITY_ALLOWED_TENANT_ID), support_groups, integration)
        except (ValueError, TypeError, AttributeError):
            return None

    def eligible(self, row, uid, excluded, author_in_groups):
        try:
            author = user_id(row.get('users_id'))
            candidate = (type(row.get('is_private')) in (int, str) and str(row['is_private']) == '0'
                    and ('is_deleted' not in row or type(row['is_deleted']) in (int, str) and str(row['is_deleted']) == '0')
                    and author not in self.integration
                    and author != uid and user_id(row['id']) not in excluded)
        except (ValueError, TypeError, KeyError):
            return False
        # Membership failures must propagate; False means confirmed nonmembership.
        # Integration/self/bot-receipt exclusions always precede any group lookup.
        return candidate and author_in_groups(author, self.support_groups) is True
