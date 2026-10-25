"""Lexical typed-plan observation. Final JSON and APP admission remain separate."""

import json


class PlanStepProgress:
    """Single pass over JSON tokens, retaining only complete direct plan steps."""

    def __init__(self, collaboration_path=("collaboration",)):
        self.collaboration_path = collaboration_path
        self.steps_path = (*collaboration_path, "steps")
        self.stack = []
        self.root_started = False
        self.root_done = False
        self.string = None
        self.string_key = False
        self.escaped = False
        self.atom = []
        self.rows = []
        self.plan = False
        self.invalid = False

    @property
    def steps(self):
        return [dict(row) for row in self.rows] if self.plan else []

    def _path(self):
        if not self.stack:
            if self.root_started:
                raise ValueError("Repeated root")
            self.root_started = True
            return ()
        top = self.stack[-1]
        if top["state"] not in {"value", "value_or_end"}:
            raise ValueError("Unexpected value")
        return (*top["path"], top["key"] if top["type"] == "{" else top["index"])

    def _value(self, path, value, *, container=False):
        if (
            len(path) == len(self.steps_path) + 1
            and path[:-1] == self.steps_path
            and not container
        ):
            raise ValueError("Plan row must be an object")
        if path == (*self.collaboration_path, "kind"):
            self.plan = value == "plan"
        if self.stack:
            parent = self.stack[-1]
            if (
                parent["type"] == "{"
                and len(parent["path"]) == len(self.steps_path) + 1
                and parent["path"][:-1] == self.steps_path
            ):
                parent["values"][parent["key"]] = value
            parent["state"] = "after"
            if parent["type"] == "[":
                parent["index"] += 1
        else:
            self.root_done = True

    def feed(self, delta):
        before = (len(self.rows) if self.plan else 0, self.invalid)
        try:
            for char in delta:
                if self.invalid:
                    break
                if self.string is not None:
                    self.string.append(char)
                    if self.escaped:
                        self.escaped = False
                    elif char == "\\":
                        self.escaped = True
                    elif char == '"':
                        value = json.loads("".join(self.string))
                        value.encode("utf-8", errors="strict")
                        self.string = None
                        if self.string_key:
                            top = self.stack[-1]
                            if value in top["keys"]:
                                raise ValueError("Duplicate field")
                            top["keys"].add(value)
                            top["key"] = value
                            top["state"] = "colon"
                        else:
                            self._value(self.string_path, value)
                    continue
                if self.atom:
                    if char not in " \t\r\n,]}":
                        self.atom.append(char)
                        continue
                    value = json.loads(
                        "".join(self.atom),
                        parse_constant=lambda _: (_ for _ in ()).throw(
                            ValueError("Nonfinite")
                        ),
                    )
                    self.atom = []
                    self._value(self.atom_path, value)
                if char.isspace():
                    continue
                if char == '"':
                    self.string_key = bool(
                        self.stack
                        and self.stack[-1]["type"] == "{"
                        and self.stack[-1]["state"] in {"key", "key_or_end"}
                    )
                    if not self.string_key:
                        self.string_path = self._path()
                    self.string = ['"']
                    self.escaped = False
                elif char in "{[":
                    path = self._path()
                    self.stack.append(
                        {
                            "type": char,
                            "path": path,
                            "state": "key_or_end" if char == "{" else "value_or_end",
                            "keys": set(),
                            "values": {},
                            "key": None,
                            "index": 0,
                        }
                    )
                elif char in "}]":
                    if not self.stack:
                        raise ValueError("Unexpected close")
                    top = self.stack.pop()
                    if (top["type"], char) not in {("{", "}"), ("[", "]")} or top[
                        "state"
                    ] not in {"after", "key_or_end", "value_or_end"}:
                        raise ValueError("Invalid close")
                    path = top["path"]
                    if (
                        len(path) == len(self.steps_path) + 1
                        and path[:-1] == self.steps_path
                    ):
                        row = top["values"]
                        if (
                            top["type"] != "{"
                            or set(row) != {"text", "kind"}
                            or not isinstance(row["text"], str)
                            or not row["text"].strip()
                            or row["kind"] not in {"discuss", "prepare_insertion"}
                        ):
                            raise ValueError("Invalid plan row")
                        if path[-1] != len(self.rows):
                            raise ValueError("Non-prefix plan row")
                        self.rows.append(row)
                    self._value(path, None, container=True)
                elif char == ":":
                    if not self.stack or self.stack[-1]["state"] != "colon":
                        raise ValueError("Unexpected colon")
                    self.stack[-1]["state"] = "value"
                elif char == ",":
                    if not self.stack or self.stack[-1]["state"] != "after":
                        raise ValueError("Unexpected comma")
                    self.stack[-1]["state"] = (
                        "key" if self.stack[-1]["type"] == "{" else "value"
                    )
                else:
                    self.atom_path = self._path()
                    self.atom = [char]
        except (ValueError, TypeError, KeyError, UnicodeError):
            self.invalid = True
        return before != (len(self.rows) if self.plan else 0, self.invalid)
