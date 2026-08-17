# config.py
import os
import yaml
import logging
import traceback
from pydantic_settings import BaseSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("GLPI_Bot")


class Settings(BaseSettings):
    MICROSOFT_APP_ID: str = ""
    MICROSOFT_APP_PASSWORD: str = ""
    MICROSOFT_APP_TENANT_ID: str = ""
    GLPI_URL: str
    GLPI_APP_TOKEN: str
    GLPI_USER_TOKEN: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def _validate_forms_dependencies(forms: dict) -> None:
    """Valida dependências dos formulários."""
    for form_key, form in forms.items():
        questions = form.get("questions", {})
        field_order = list(questions.keys())

        for idx, (field_name, rules) in enumerate(questions.items()):
            depends_on = rules.get("depends_on")
            if not depends_on:
                continue

            parent_field = depends_on.get("field")

            if parent_field not in field_order:
                logger.warning(
                    f"[forms.yaml:{form_key}] Campo '{field_name}' depende de "
                    f"'{parent_field}', mas esse campo não existe."
                )
                continue

            parent_idx = field_order.index(parent_field)
            if parent_idx >= idx:
                logger.warning(
                    f"[forms.yaml:{form_key}] Campo '{field_name}' depende de "
                    f"'{parent_field}', porém este aparece depois no YAML."
                )


def load_forms_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "forms.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            forms = yaml.safe_load(f).get("forms", {})

        logger.info(f"Forms carregados: {list(forms.keys())}")
        for form_key, form_data in forms.items():
            logger.info(
                f"Form '{form_key}': ID={form_data.get('id')}, "
                f"Keywords={form_data.get('keywords', [])}"
            )

        _validate_forms_dependencies(forms)
        return forms
    except FileNotFoundError:
        logger.error(f"Arquivo forms.yaml não encontrado")
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar forms.yaml: {e}")
        return {}


FORMS_CONFIG = load_forms_config()