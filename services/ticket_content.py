"""Untrusted GLPI HTML -> passive Teams text; no resources are fetched."""
from html.parser import HTMLParser
import re
import unicodedata

MAX_SOURCE = 100_000
PAGE_SIZE = 1200


class ContentLimit(ValueError):
    pass


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'iframe', 'object', 'svg', 'template', 'head'}:
            self.hidden.append(tag)
        if not self.hidden and tag in {'p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'blockquote'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag in {'p', 'div', 'li', 'tr', 'blockquote'}:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def passive(text):
    """Literal preview: preserve text, neutralize markup/mentions, redact URLs."""
    if not isinstance(text, str) or len(text) > MAX_SOURCE:
        raise ContentLimit()
    text = re.sub(r'(?i)(?:[a-z][a-z0-9+.-]*://|www\.|mailto:)[^\s<>]+', '〔link removido〕', text)
    text = re.sub(r'(?i)\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>]*)?', '〔endereço removido〕', text)
    text = ''.join(c for c in text if c in '\n\t' or unicodedata.category(c)[0] != 'C')
    return text.translate(str.maketrans({'@': '＠', '<': '＜', '>': '＞', '*': '＊', '_': '＿',
                                      '[': '［', ']': '］', '`': '｀', '#': '＃', '\\': '＼', '|': '｜'}))


def html_text(source):
    # Caller requests X-GLPI-Sanitized-Content:false. HTMLParser decodes text
    # entities once; decoded text is NEVER parsed again as HTML.
    if not isinstance(source, str) or len(source) > MAX_SOURCE:
        raise ContentLimit()
    parser = _Text()
    parser.feed(source)
    parser.close()
    text = ''.join(parser.parts).replace('\r\n', '\n').replace('\r', '\n')
    text = '\n'.join(' '.join(line.split()) for line in text.split('\n'))
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return passive(text)


def pages(text):
    return [text[i:i + PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)] or ['(Sem texto.)']
