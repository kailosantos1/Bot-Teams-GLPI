"""Módulo de cartões e ações interativas para o menu do Teams.

Gera HeroCards e Activities estruturadas compatíveis com o SDK do Microsoft Teams
e oferece fallback transparente quando o SDK não estiver instalado.
"""

from typing import Any, Dict, List, Optional

try:
    from botbuilder.core import CardFactory
    from botbuilder.schema import (
        Activity,
        ActivityTypes,
        Attachment,
        HeroCard,
        CardAction,
        ActionTypes,
    )
except ImportError:
    CardFactory = None
    class ActionTypes:
        im_back = "imBack"
        message_back = "messageBack"
        post_back = "postBack"

    class CardAction:
        def __init__(
            self,
            type: str = None,
            title: str = None,
            image: str = None,
            text: str = None,
            display_text: str = None,
            value: object = None,
            channel_data: object = None,
            **kwargs,
        ):
            self.type = type
            self.title = title
            self.image = image
            self.text = text
            self.display_text = display_text
            self.value = value
            self.channel_data = channel_data
            for k, v in kwargs.items():
                setattr(self, k, v)

    class HeroCard:
        def __init__(
            self,
            title: str = None,
            subtitle: str = None,
            text: str = None,
            images: list = None,
            buttons: list = None,
            tap: CardAction = None,
            **kwargs,
        ):
            self.title = title
            self.subtitle = subtitle
            self.text = text
            self.images = images or []
            self.buttons = buttons or []
            self.tap = tap
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Attachment:
        def __init__(
            self,
            content_type: str = None,
            content_url: str = None,
            content: object = None,
            name: str = None,
            thumbnail_url: str = None,
            **kwargs,
        ):
            self.content_type = content_type
            self.content_url = content_url
            self.content = content
            self.name = name
            self.thumbnail_url = thumbnail_url
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ActivityTypes:
        message = "message"

    class Activity:
        def __init__(
            self,
            type: str = ActivityTypes.message,
            text: str = None,
            attachments: list = None,
            channel_id: str = None,
            conversation: object = None,
            from_property: object = None,
            recipient: object = None,
            value: object = None,
            **kwargs,
        ):
            self.type = type
            self.text = text
            self.attachments = attachments or []
            self.channel_id = channel_id
            self.conversation = conversation
            self.from_property = from_property
            self.recipient = recipient
            self.value = value
            for k, v in kwargs.items():
                setattr(self, k, v)

        def __str__(self):
            return self.text or ""


VALID_ACTIONS = {
    "menu",
    "open_ticket",
    "consult_tickets",
    "continue_form",
    "cancel_form_to_menu",
}


def _btn(title: str, text: str, action: str, confirmation: str = None) -> CardAction:
    action_type = getattr(ActionTypes, "message_back", "messageBack")
    return CardAction(
        type=action_type,
        title=title,
        text=text,
        display_text=title,
        value={"action": action, **({"confirmation": confirmation} if confirmation else {})},
    )


def _card_attachment(card: HeroCard) -> Attachment:
    if CardFactory is not None:
        return CardFactory.hero_card(card)
    return Attachment(content_type="application/vnd.microsoft.card.hero", content=card)


def is_personal_conversation(activity: Any) -> bool:
    """Verifica se a atividade provém de conversa pessoal (1:1)."""
    conversation = getattr(activity, "conversation", None)
    return (
        getattr(activity, "channel_id", None) == "msteams"
        and getattr(conversation, "conversation_type", None) == "personal"
        and getattr(conversation, "is_group", False) is not True
    )


def parse_button_action(activity: Any) -> Optional[str]:
    """Extrai e valida com restrição estrita a ação de botão do payload activity.value."""
    val = getattr(activity, "value", None)
    if not isinstance(val, dict) or set(val) - {"action", "confirmation"}:
        return None
    action = val.get("action")
    if isinstance(action, str) and action in VALID_ACTIONS:
        return action
    return None


# =====================================================================
# TEXTOS E CONSTRUTORES DE ATIVIDADES / CARTÕES
# =====================================================================

CHOICE_GUIDANCE = "Toque em uma opção ou digite o número."
MENU_TEXT = "👋 {greeting} Como posso ajudar?\n\n" + CHOICE_GUIDANCE
OPEN_TICKET_TEXT = (
    "📝 Vamos abrir seu chamado! Descreva o que você precisa.\n\n"
    "Exemplos: problema na impressora, problema no FlexSmart ou cadastro de novo colaborador.\n\n"
    "Para voltar, toque no botão ou digite 0."
)
CONSULT_TEXT = "Não consegui confirmar seu acesso aos chamados. Entre em contato com o suporte de TI."
INTERRUPT_TEXT = "⚠️ você já tem um chamado em preenchimento (**{form_name}**).\n\nO que deseja fazer? Toque em uma opção ou digite o número."
UNIDENTIFIED_OPEN_TEXT = (
    "❌ não consegui identificar sua solicitação.\n\n"
    "Tente descrever com palavras como manutenção, impressora, computador, FlexSmart, cadastro ou admissão."
)
INVALID_MENU_TEXT = "⚠️ Opção inválida. Escolha uma das opções:\n\n" + CHOICE_GUIDANCE
INVALID_CONSULT_TEXT = "⚠️ Opção inválida.\n\n" + CHOICE_GUIDANCE
INTERRUPT_INVALID_TEXT = "⚠️ você tem um chamado em andamento. Toque em uma opção ou digite o número."


def build_menu_activity(first_name: str) -> Activity:
    text = MENU_TEXT.format(greeting=f"Olá, {first_name.strip()}!" if first_name and first_name.strip() and first_name != "Usuário" else "Olá!")
    card = HeroCard(
        text=text,
        buttons=[
            _btn("1 — Abrir um chamado", "1", "open_ticket"),
            _btn("2 — Consultar meus chamados", "2", "consult_tickets"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_open_ticket_activity(first_name: str = None) -> Activity:
    card = HeroCard(
        text=OPEN_TICKET_TEXT,
        buttons=[
            _btn("0 — Voltar ao menu", "0", "menu"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_consult_activity() -> Activity:
    card = HeroCard(
        text=CONSULT_TEXT,
        buttons=[
            _btn("0 — Voltar ao menu", "0", "menu"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_interrupt_activity(first_name: str, form_name: str, confirmation: str = None) -> Activity:
    text = INTERRUPT_TEXT.format(first_name=first_name, form_name=form_name)
    card = HeroCard(
        text=text,
        buttons=[
            _btn("1 — Continuar preenchimento", "1", "continue_form", confirmation),
            _btn("2 — Cancelar preenchimento e ir ao menu", "2", "cancel_form_to_menu", confirmation),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_unidentified_open_activity(first_name: str) -> Activity:
    text = UNIDENTIFIED_OPEN_TEXT.format(first_name=first_name)
    card = HeroCard(
        text=text,
        buttons=[
            _btn("0 — Voltar ao menu", "0", "menu"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_invalid_menu_activity() -> Activity:
    card = HeroCard(
        text=INVALID_MENU_TEXT,
        buttons=[
            _btn("1 — Abrir um chamado", "1", "open_ticket"),
            _btn("2 — Consultar meus chamados", "2", "consult_tickets"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_invalid_consult_activity() -> Activity:
    card = HeroCard(
        text=INVALID_CONSULT_TEXT,
        buttons=[
            _btn("0 — Voltar ao menu", "0", "menu"),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )


def build_interrupt_invalid_activity(first_name: str, confirmation: str = None) -> Activity:
    text = INTERRUPT_INVALID_TEXT.format(first_name=first_name)
    card = HeroCard(
        text=text,
        buttons=[
            _btn("1 — Continuar preenchimento", "1", "continue_form", confirmation),
            _btn("2 — Cancelar preenchimento e ir ao menu", "2", "cancel_form_to_menu", confirmation),
        ],
    )
    return Activity(
        type=ActivityTypes.message,
        attachments=[_card_attachment(card)],
    )

