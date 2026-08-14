import re
from html.parser import HTMLParser


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1
        elif tag.lower() == "br" and not self._ignored_depth:
            self.parts.append("\n")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag.lower() in {"p", "div", "li"} and not self._ignored_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def plain_lines(value: str | None) -> list[str]:
    if value is None:
        return []
    parser = _PlainTextParser()
    parser.feed(value)
    parser.close()
    text = "".join(parser.parts).replace("\r\n", "\n").replace("\r", "\n")
    return [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in text.split("\n")
        if line.strip()
    ]


def parse_menu(value: str) -> list[str]:
    return plain_lines(value)


def parse_optional_text(value: str | None) -> str | None:
    lines = plain_lines(value)
    return "\n".join(lines) if lines else None


def parse_nutrition(value: str | None) -> dict[str, str] | None:
    result: dict[str, str] = {}
    unlabeled = 0
    for line in plain_lines(value):
        label, separator, item_value = line.partition(":")
        if not separator:
            label, separator, item_value = line.partition("：")
        if separator and label.strip() and item_value.strip():
            key = label.strip()
            if key not in result:
                result[key] = item_value.strip()
            continue
        unlabeled += 1
        key = "정보" if unlabeled == 1 else f"정보 {unlabeled}"
        result[key] = line
    return result or None

