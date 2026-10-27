"""Conservative classification of inbound Teams attachments.

Teams may accompany ordinary text with an HTML representation.  That technical
representation is neither trusted input nor a user file and must never be read as
the message body.  Everything else remains a real/unknown attachment and is
handled conservatively.
"""


def is_technical_html(attachment) -> bool:
    raw_type = getattr(attachment, "content_type", None)
    if not isinstance(raw_type, str):
        return False
    content_type = raw_type.split(";", 1)[0].strip().lower()
    if content_type != "text/html":
        return False
    content = getattr(attachment, "content", None)
    has_download = isinstance(content, dict) and bool(content.get("downloadUrl"))
    return not (
        getattr(attachment, "name", None)
        or getattr(attachment, "content_url", None)
        or has_download
    )


def real_attachments(activity) -> list:
    """Return files/images/unknown attachments, excluding only technical HTML."""
    return [item for item in (getattr(activity, "attachments", None) or [])
            if not is_technical_html(item)]


def has_real_attachments(activity) -> bool:
    return bool(real_attachments(activity))
