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


class _Description(HTMLParser):
    """Small structural tree; never retains attributes, URLs or executable HTML."""
    BLOCKS = {'p', 'div', 'section', 'article', 'li', 'ul', 'ol', 'dl', 'dt', 'dd',
              'blockquote', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table',
              'aside', 'header', 'footer', 'main'}
    HIDDEN = {'script', 'style', 'iframe', 'object', 'svg', 'template', 'head'}
    VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'wbr', 'source', 'embed', 'area', 'col', 'param'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ['', []]
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        if len(self.stack) > 64:
            raise ContentLimit()
        node = [tag, []]
        self.stack[-1][1].append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1][1].append(data)

    @classmethod
    def marked_label(cls, node):
        if isinstance(node, str):
            return False
        return node[0] in {'th', 'strong', 'b', 'dt'} or any(cls.marked_label(x) for x in node[1])

    @classmethod
    def render(cls, node):
        if isinstance(node, str):
            return node
        tag, children = node
        if tag in cls.HIDDEN:
            return ''
        if tag in {'br', 'hr'}:
            return '\n'
        if tag == 'tr':
            cells = [child for child in children if isinstance(child, list) and child[0] in {'td', 'th'}]
            only_cells = all(child in cells or isinstance(child, str) and not child.strip() for child in children)
            if only_cells and len(cells) == 2 and cells[1][0] == 'td':
                label, value = (cls.render(cell).strip() for cell in cells)
                # Recognize label/value only from markup/explicit colon, never
                # from a known field position or a dictionary of guessed names.
                if label and (cls.marked_label(cells[0]) or label.endswith(':')):
                    separator = '\n' if '\n' in value else ' '
                    return '\n\n' + label.rstrip(':') + ':' + separator + value + '\n\n'
            # Other tables keep every cell and stray text in document order.
            parts = [cls.render(child).strip() for child in children]
            return '\n\n' + ' · '.join(part for part in parts if part) + '\n\n'
        text = ''.join(cls.render(child) for child in children)
        return '\n\n' + text + '\n\n' if tag in cls.BLOCKS else text


def description_text(source):
    """Sanitized paragraphs and marked label/value rows; no content summarizing.

    Unknown structures retain all visible text in source order. No field names,
    warnings or sections are discarded. Entities are decoded only by this parser.
    """
    if not isinstance(source, str) or len(source) > MAX_SOURCE:
        raise ContentLimit()
    parser = _Description()
    try:
        parser.feed(source)
        parser.close()
    except ContentLimit:
        # Unknown/deep nesting keeps the established sanitized fallback.
        return html_text(source)
    text = parser.render(parser.root).replace('\r\n', '\n').replace('\r', '\n')
    text = '\n'.join(' '.join(line.split()) for line in text.split('\n'))
    return passive(re.sub(r'\n{3,}', '\n\n', text).strip())
