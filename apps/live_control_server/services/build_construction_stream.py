"""Operation-local construction observation; never a durable page or retry owner."""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
import json
from typing import Callable
from threading import Lock

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

construction_sink: ContextVar[Callable[[dict], None] | None] = ContextVar('construction_sink', default=None)
_running: set[asyncio.Task] = set()


def observe(value: dict) -> None:
    sink = construction_sink.get()
    if sink is not None:
        try:
            sink(value)
        except Exception:
            pass  # Delivery cannot change authorization, persistence or retry policy.


class MarkdownStringProgress:
    """Single-pass lexical projection of completed lines in one root JSON string.

    This is deliberately not JSON admission. GE and the proposal owner still
    validate the complete final object, including duplicate fields and content.
    """
    def __init__(self):
        self.depth = 0
        self.expect_key = False
        self.key = None
        self.in_string = False
        self.key_string = False
        self.selected = False
        self.key_chars: list[str] = []
        self.escaped = False
        self.unicode_digits: str | None = None
        self.high: int | None = None
        self.seen = False
        self.invalid = False
        self.line: list[str] = []
        self.lines: list[str] = []
        self.revision = 0

    @property
    def markdown(self):
        return ''.join(self.lines)

    def _decoded(self, char: str):
        point = ord(char)
        if self.high is not None:
            if not 0xDC00 <= point <= 0xDFFF:
                self.invalid = True
                return
            char = chr(0x10000 + ((self.high - 0xD800) << 10) + point - 0xDC00)
            self.high = None
        elif 0xD800 <= point <= 0xDBFF:
            self.high = point
            return
        elif 0xDC00 <= point <= 0xDFFF:
            self.invalid = True
            return
        self.line.append(char)
        if char == '\n':
            self.lines.append(''.join(self.line))
            self.line.clear()
            self.revision += 1

    def feed(self, delta: str) -> bool:
        before = self.revision
        for char in delta:
            if self.invalid:
                break
            if not self.in_string:
                if char == '"':
                    self.in_string = True
                    self.key_string = self.depth == 1 and self.expect_key
                    self.selected = self.depth == 1 and not self.expect_key and self.key == 'replacement_markdown'
                    self.key_chars = []
                    if self.selected:
                        if self.seen:
                            self.invalid = True
                        self.seen = True
                elif char in '{[':
                    self.depth += 1
                    if self.depth == 1 and char == '{':
                        self.expect_key = True
                elif char in '}]':
                    self.depth -= 1
                elif char == ',' and self.depth == 1:
                    self.expect_key = True
                    self.key = None
                elif char == ':' and self.depth == 1:
                    self.expect_key = False
                continue
            if self.key_string:
                self.key_chars.append(char)
            if self.unicode_digits is not None:
                if char not in '0123456789abcdefABCDEF':
                    self.invalid = True
                    break
                self.unicode_digits += char
                if len(self.unicode_digits) == 4:
                    if self.selected:
                        self._decoded(chr(int(self.unicode_digits, 16)))
                    self.unicode_digits = None
                continue
            if self.escaped:
                self.escaped = False
                if char == 'u':
                    self.unicode_digits = ''
                elif char in '"\\/bfnrt':
                    if self.selected:
                        self._decoded({'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}.get(char, char))
                else:
                    self.invalid = True
                continue
            if char == '\\':
                self.escaped = True
            elif char == '"':
                self.in_string = False
                if self.key_string:
                    try:
                        self.key = json.loads('"' + ''.join(self.key_chars))
                    except ValueError:
                        self.invalid = True
                elif self.selected:
                    if self.high is not None:
                        self.invalid = True
                    elif self.line:
                        self.lines.append(''.join(self.line))
                        self.line.clear()
                        self.revision += 1
                    self.key = None
                self.selected = False
            elif ord(char) < 0x20:
                self.invalid = True
            elif self.selected:
                self._decoded(char)
        return self.revision != before


def turn_stream(execute: Callable[[], dict], client_turn_id: str) -> StreamingResponse:
    """One owned execution, continued after observer disconnect; no replay/cache."""
    async def events():
        loop = asyncio.get_running_loop()
        wake = asyncio.Event()
        lock = Lock()
        latest = None
        terminal = None
        retired = False
        wake_pending = False

        def publish(value, *, final=False):
            nonlocal latest, terminal, wake_pending
            # Bound pending snapshots before crossing the worker/loop boundary.
            with lock:
                if retired:
                    return
                if final:
                    terminal = value
                else:
                    latest = value
                if wake_pending:
                    return
                wake_pending = True
                loop.call_soon_threadsafe(wake.set)

        def work():
            token = construction_sink.set(publish)
            result = {'kind': 'error', 'status': 500, 'detail': {'code': 'turn_stream_failed',
                      'message': 'The saved request needs checking. No automatic retry was sent.'}}
            try:
                result = {'kind': 'result', 'response': execute()}
            except HTTPException as exc:
                result = {'kind': 'error', 'status': exc.status_code, 'detail': exc.detail}
            except Exception:
                pass  # The route/service already owns durable uncertainty and diagnostics.
            finally:
                construction_sink.reset(token)
                publish(result, final=True)

        def release(task):
            _running.discard(task)
            if not task.cancelled():
                task.exception()

        task = asyncio.create_task(asyncio.to_thread(work))
        _running.add(task)
        task.add_done_callback(release)
        try:
            while True:
                await wake.wait()
                wake.clear()
                with lock:
                    value, latest = latest, None
                    end = terminal
                    wake_pending = False
                if value is not None:
                    yield 'data: ' + json.dumps({'schema': 'dmb_build_turn_stream_v1',
                        'client_turn_id': client_turn_id, 'kind': 'construction', 'progress': value}) + '\n\n'
                if end is not None:
                    yield 'data: ' + json.dumps({'schema': 'dmb_build_turn_stream_v1',
                        'client_turn_id': client_turn_id, **end}) + '\n\n'
                    return
        finally:
            with lock:
                retired = True
                latest = terminal = None
            # Do not cancel the one durable request when only its observer retires.

    return StreamingResponse(events(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
