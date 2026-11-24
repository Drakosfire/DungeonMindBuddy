"""Project provisional prose from the native Build writer's JSON prefix."""
from dataclasses import dataclass, field
import json
import re

from application_state.agent_conversation.native_answer_output import MAX_NATIVE_OUTPUT_BYTES

# A token is kept in the buffer only while it may still be incomplete.
_STRING_TOKEN = re.compile(r'[^"\\\x00-\x1f]+|"|\\u[0-9a-fA-F]{4}|\\["\\/bfnrt]')
_ATOM_END = re.compile(r'[\x20\t\r\n,}\]]')
_WHITESPACE = re.compile(r'[\x20\t\r\n]*')


@dataclass
class _Container:
    path: tuple
    closing: str
    state: str = "first"
    keys: set[str] = field(default_factory=set)
    key: str = ""
    index: int = 0


class BuildReplyProjection:
    """Only root answer_segments[*].text contributes to the preview.

    The decoder has no completion authority. The writer still validates and
    saves its complete SDK-selected reply, including its evidence and citations.
    """

    def __init__(self):
        self.invalid = False
        self._size = 0
        self._buffer = ""
        self._stack: list[_Container] = []
        self._started = False
        self._string: str | None = None
        self._key: list[str] = []
        self._has_text = False
        self._new_segment = False

    def feed(self, delta: str) -> str | None:
        """Return newly decoded answer text in reading order."""
        if self.invalid:
            return None
        try:
            self._size += len(delta.encode())
            if self._size > MAX_NATIVE_OUTPUT_BYTES:
                raise ValueError("Answer preview exceeds the writer output limit")
            self._buffer += delta
            cursor = 0
            parts: list[str] = []
            while cursor < len(self._buffer):
                if self._string is not None:
                    next_cursor, added = self._read_string(cursor)
                    if added:
                        parts.append(added)
                else:
                    cursor = _WHITESPACE.match(self._buffer, cursor).end()
                    if cursor == len(self._buffer):
                        break
                    next_cursor = self._read_structure(cursor)
                if next_cursor == cursor:
                    break
                cursor = next_cursor
            self._buffer = self._buffer[cursor:]
        except ValueError:
            self.invalid = True
            self._buffer = ""
            return None
        return "".join(parts) or None

    def _read_structure(self, cursor: int) -> int:
        char = self._buffer[cursor]
        if not self._started:
            if char != "{":
                raise ValueError("Expected the answer object")
            self._started = True
            self._stack.append(_Container((), "}"))
            return cursor + 1
        if not self._stack:
            raise ValueError("Unexpected text after the answer object")
        frame = self._stack[-1]
        if char == frame.closing and frame.state in ("first", "after"):
            self._stack.pop()
            return cursor + 1
        if frame.state == "after" and char == ",":
            frame.state = "next"
            return cursor + 1
        if frame.closing == "}" and frame.state in ("first", "next"):
            if char != '"':
                raise ValueError("Expected an object key")
            self._string = "key"
            self._key.clear()
            return cursor + 1
        if frame.state == "colon" and char == ":":
            frame.state = "value"
            return cursor + 1
        if frame.state == "value" or (frame.closing == "]" and frame.state in ("first", "next")):
            key = frame.key if frame.closing == "}" else frame.index
            end = self._read_value(cursor, (*frame.path, key))
            if end != cursor:
                frame.state = "after"
                frame.index += 1
            return end
        raise ValueError("Malformed answer structure")

    def _read_value(self, cursor: int, path: tuple) -> int:
        char = self._buffer[cursor]
        if char in "{[":
            if len(self._stack) >= 32:
                raise ValueError("Answer exceeds preview nesting limit")
            self._stack.append(_Container(path, "}" if char == "{" else "]"))
        elif char == '"':
            is_answer = (len(path) == 3 and path[0] == "answer_segments"
                         and type(path[1]) is int and path[2] == "text")
            self._string = "answer" if is_answer else "ignored"
            if is_answer:
                self._new_segment = True
        elif char in "-0123456789tfn":
            end = _ATOM_END.search(self._buffer, cursor)
            if end is None:
                return cursor
            json.loads(self._buffer[cursor:end.start()])
            return end.start()
        else:
            raise ValueError("Expected an answer value")
        return cursor + 1

    def _read_string(self, cursor: int) -> tuple[int, str]:
        token = _STRING_TOKEN.match(self._buffer, cursor)
        if token is None:
            tail = self._buffer[cursor:]
            if len(tail) < 6 and re.fullmatch(r'\\(?:u[0-9a-fA-F]{0,3})?', tail):
                return cursor, ""
            raise ValueError("Invalid answer string")
        value = token.group()
        end = token.end()
        if value == '"':
            if self._string == "key":
                frame = self._stack[-1]
                frame.key = "".join(self._key)
                if frame.key in frame.keys:
                    raise ValueError("Duplicate answer object key")
                frame.keys.add(frame.key)
                frame.state = "colon"
            self._string = None
            return end, ""
        if value.startswith("\\"):
            if value.startswith("\\u") and 0xD800 <= int(value[2:], 16) <= 0xDBFF:
                if len(self._buffer) - end < 6:
                    return cursor, ""
                low = _STRING_TOKEN.match(self._buffer, end)
                if low is None or not low.group().startswith("\\u"):
                    raise ValueError("Invalid answer surrogate pair")
                value += low.group()
                end = low.end()
            value = json.loads('"' + value + '"')
            value.encode()
        if self._string == "key":
            self._key.append(value)
        if self._string == "answer":
            prefix = "\n\n" if self._new_segment and self._has_text else ""
            self._new_segment = False
            self._has_text = True
            return end, prefix + value
        return end, ""
