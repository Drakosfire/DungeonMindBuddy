"""Snapshot-local Plan navigation. A selector grants no evidence or Save authority."""
from __future__ import annotations

import re
from typing import Annotated, Literal
from pydantic import BeforeValidator, Field, model_validator
from .authored_graph_references import AuthoredReferencesV2

from .plan_authoring import (
    Frozen, PlanAuthoringCaptureV1, PlanAuthoringBoundaryCaptureV1,
    digest, strict_json, PlanRequestedWorkInputV1,
)


class PlanPlacementOptionV1(Frozen):
    selector: str = Field(min_length=1)
    kind: Literal["captured_target", "before_heading", "after_heading", "after_section", "end_page"]
    label: str = Field(min_length=1)
    root_boundary: int | None = Field(strict=True, ge=0)
    position: int | None = Field(strict=True, ge=0)
    target_capture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_kind(self):
        if self.kind == "captured_target":
            if self.selector != "captured" or self.root_boundary is not None or self.position is not None:
                raise ValueError("Captured target cannot invent a structural boundary")
        elif self.root_boundary is None or self.position is None:
            raise ValueError("Structural placement requires its editor-compiled boundary")
        elif self.kind == "end_page":
            if self.selector != "end":
                raise ValueError("End placement differs from its offered selector")
        else:
            prefix = {"before_heading": "before:", "after_heading": "under:", "after_section": "after:"}[self.kind]
            suffix = self.selector.removeprefix(prefix)
            if (not self.selector.startswith(prefix) or not suffix.isascii()
                    or not suffix.isdecimal() or str(int(suffix)) != suffix):
                raise ValueError("Section placement requires its exact root selector")
        return self

    def derived_target(self, original: PlanAuthoringCaptureV1):
        if self.kind == "captured_target":
            return original
        if original.target_kind != "insert_at_caret":
            raise ValueError("An explicit replacement cannot be broadened to an insertion")
        payload = original.model_dump(mode="json", by_alias=True)
        payload.update(schema="dmb_plan_authoring_boundary_capture_v1",
            target_kind="insert_at_boundary", root_boundary=self.root_boundary,
            **{"from": self.position, "to": self.position})
        return PlanAuthoringBoundaryCaptureV1.model_validate(payload)


class PlanPlacementCatalogV1(Frozen):
    schema_: Literal["dmb_plan_placement_catalog_v1"] = Field(
        default="dmb_plan_placement_catalog_v1", alias="schema")
    original_capture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entries: tuple[PlanPlacementOptionV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_selectors(self):
        selectors = [entry.selector for entry in self.entries]
        if selectors[0] != "captured" or len(set(selectors)) != len(selectors):
            raise ValueError("Placement catalog requires one unique captured target first")
        return self

    @property
    def sha256(self):
        return digest(self.model_dump(mode="json", by_alias=True))

    def require_original(self, original: PlanAuthoringCaptureV1):
        if (isinstance(original, PlanAuthoringBoundaryCaptureV1)
                or self.original_capture_sha256 != original.sha256
                or self.editor_sha256 != original.editor_sha256):
            raise ValueError("Placement catalog differs from its original captured page")
        content = strict_json(original.editor_json).get("content", [])
        if original.target_kind != "insert_at_caret" and len(self.entries) != 1:
            raise ValueError("Replacement authority has only its exact captured target")
        for entry in self.entries:
            if entry.derived_target(original).sha256 != entry.target_capture_sha256:
                raise ValueError("Placement target differs from its frozen offered digest")
            if entry.kind == "end_page" and entry.root_boundary != len(content):
                raise ValueError("End placement differs from the captured page end")
            if entry.kind in {"before_heading", "after_heading", "after_section"}:
                index = int(entry.selector.split(":", 1)[1])
                if (index >= len(content) or content[index].get("type") != "heading"
                        or entry.kind == "before_heading" and entry.root_boundary != index
                        or entry.kind == "after_heading" and entry.root_boundary != index + 1
                        or entry.kind == "after_section" and entry.root_boundary <= index):
                    raise ValueError("Section placement differs from its captured root heading")
        return self

    def resolve(self, original: PlanAuthoringCaptureV1, selector: str):
        self.require_original(original)
        entry = next((row for row in self.entries if row.selector == selector), None)
        if entry is None:
            raise ValueError("Plan placement selector was not offered")
        return entry.derived_target(original)

    def model_choices(self):
        # No offsets, root indices or authority digests in model-visible state.
        return [{"selector": entry.selector, "label": entry.label} for entry in self.entries]


class PlanPlacementOptionV2(Frozen):
    """Inert paragraph-capable option; V1 wire values remain unchanged."""

    selector: str = Field(min_length=1)
    kind: Literal["captured_target", "before_heading", "after_heading", "after_section",
                  "end_page", "before_paragraph", "after_paragraph"]
    label: str = Field(min_length=1)
    source_root_index: int | None = Field(strict=True, ge=0)
    root_boundary: int | None = Field(strict=True, ge=0)
    position: int | None = Field(strict=True, ge=0)
    target_capture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_kind(self):
        if self.kind == "captured_target":
            if self.selector != "captured" or any(value is not None for value in (
                self.source_root_index, self.root_boundary, self.position
            )):
                raise ValueError("Captured target cannot invent a structural boundary")
        else:
            if not re.fullmatch(r"place[1-9][0-9]*", self.selector):
                raise ValueError("V2 placement requires an opaque local selector")
            if self.root_boundary is None or self.position is None:
                raise ValueError("Structural placement requires its editor-compiled boundary")
            if (self.source_root_index is None) != (self.kind == "end_page"):
                raise ValueError("Placement requires its exact source root")
        return self

    def derived_target(self, original: PlanAuthoringCaptureV1):
        # Reuse the original boundary format, preserving the real selection.
        return PlanPlacementOptionV1.derived_target(self, original)


def _placement_headings(content: list[dict]) -> list[dict]:
    """Mirror the frontend semantic heading/table-caption navigation rules."""
    headings, ancestors = [], []
    for index, node in enumerate(content):
        attrs, children = node.get("attrs"), node.get("content", [])
        if node.get("type") != "heading" or not isinstance(attrs, dict) or not isinstance(children, list):
            continue
        level = attrs.get("level")
        if type(level) is not int or not 1 <= level <= 6:
            continue
        plain = all(isinstance(child, dict) and child.get("type") == "text"
                    and not child.get("marks") and isinstance(child.get("text"), str)
                    for child in children)
        caption = (level == 2 and index + 1 < len(content)
                   and content[index + 1].get("type") == "table" and plain
                   and not any(key != "level" and value is not None for key, value in attrs.items()))
        text = "".join(child.get("text", "") for child in children
                       if isinstance(child, dict) and child.get("type") == "text"
                       and isinstance(child.get("text"), str)).strip()
        if not text or caption:
            continue
        while ancestors and ancestors[-1][0] >= level:
            ancestors.pop()
        ancestors.append((level, text))
        path = " / ".join(label for _, label in ancestors)
        headings.append(dict(index=index, level=level, path=path))
    totals, seen = {}, {}
    for heading in headings:
        totals[heading["path"]] = totals.get(heading["path"], 0) + 1
    for offset, heading in enumerate(headings):
        path = heading["path"]
        seen[path] = seen.get(path, 0) + 1
        heading["label"] = path + (f" · {seen[path]} of {totals[path]}" if totals[path] > 1 else "")
        heading["end"] = next((row["index"] for row in headings[offset + 1:]
                               if row["level"] <= heading["level"]), len(content))
    return headings


def paragraph_placement_label(content: list[dict], index: int, kind: str, *,
                              headings: list[dict] | None = None) -> str:
    """Semantic source context only; no host identity or root index in labels."""
    node = content[index]
    inline = node.get("content", [])
    if (node.get("type") != "paragraph" or not isinstance(inline, list)
            or any(not isinstance(child, dict) or child.get("type") not in {"text", "hardBreak"}
                   or child.get("type") == "text" and not isinstance(child.get("text"), str)
                   for child in inline)):
        raise ValueError("Paragraph placement requires plain root prose")
    passage = "".join("\n" if child["type"] == "hardBreak" else child["text"] for child in inline).strip()
    if not passage:
        raise ValueError("Paragraph placement requires nonempty prose")
    section = next((heading["path"] for heading in reversed(
        _placement_headings(content) if headings is None else headings)
                    if heading["index"] < index), "this page")
    direction = "Before" if kind == "before_paragraph" else "After"
    return f"{direction} paragraph in {section}: {passage}"


class PlanPlacementCatalogV2(PlanPlacementCatalogV1):
    """Inert until the authorized reader fence and public consumers are wired."""

    schema_: Literal["dmb_plan_placement_catalog_v2"] = Field(
        default="dmb_plan_placement_catalog_v2", alias="schema")
    entries: tuple[PlanPlacementOptionV2, ...] = Field(min_length=1)

    def require_original(self, original: PlanAuthoringCaptureV1):
        if (isinstance(original, PlanAuthoringBoundaryCaptureV1)
                or self.original_capture_sha256 != original.sha256
                or self.editor_sha256 != original.editor_sha256):
            raise ValueError("Placement catalog differs from its original captured page")
        content = strict_json(original.editor_json).get("content", [])
        if not isinstance(content, list) or any(not isinstance(node, dict) for node in content):
            raise ValueError("Invalid Plan root nodes")
        if any(node.get("type") in {"pageRow", "pageImageText", "pageSlot"} for node in content):
            raise ValueError("Paragraph placement currently requires a plain Plan")
        if original.target_kind != "insert_at_caret" and len(self.entries) != 1:
            raise ValueError("Replacement authority has only its exact captured target")
        heading_rows = _placement_headings(content)
        headings = {row["index"]: row for row in heading_rows}
        for entry in self.entries:
            if entry.derived_target(original).sha256 != entry.target_capture_sha256:
                raise ValueError("Placement target differs from its frozen offered digest")
            if entry.kind == "captured_target":
                label = {"insert_at_caret": "At the captured text caret",
                         "replace_selection": "Replace only the captured selection",
                         "replace_playable_body": "Replace only the captured playable body"}[original.target_kind]
                if entry.label != label:
                    raise ValueError("Captured placement label differs from its original selection authority")
                continue
            if entry.root_boundary > len(content):
                raise ValueError("Placement boundary exceeds its captured page")
            if entry.kind == "end_page":
                if entry.root_boundary != len(content) or entry.label != "At the end of the page":
                    raise ValueError("End placement differs from the captured page end")
                continue
            index = entry.source_root_index
            if index >= len(content):
                raise ValueError("Placement source root is unavailable")
            if entry.kind in {"before_paragraph", "after_paragraph"}:
                boundary = index + int(entry.kind == "after_paragraph")
                if entry.root_boundary != boundary:
                    raise ValueError("Paragraph placement differs from its source boundary")
                if entry.label != paragraph_placement_label(content, index, entry.kind, headings=heading_rows):
                    raise ValueError("Paragraph placement label differs from its source prose")
            else:
                heading = headings.get(index)
                if heading is None:
                    raise ValueError("Section placement requires a semantic root heading")
                boundaries = {"before_heading": index, "after_heading": index + 1,
                              "after_section": heading["end"]}
                labels = {"before_heading": f"Before {heading['label']}",
                          "after_heading": f"Directly below the heading {heading['label']}, before its existing body",
                          "after_section": f"After the entire section {heading['label']}"}
                if entry.root_boundary != boundaries[entry.kind] or entry.label != labels[entry.kind]:
                    raise ValueError("Section placement differs from its exact semantic boundary")
        return self


def decode_plan_placement_catalog(value) -> PlanPlacementCatalogV2 | PlanPlacementCatalogV1:
    """Decode retained catalog versions explicitly; preserve legacy defaults."""
    if isinstance(value, PlanPlacementCatalogV1):
        value = value.model_dump(mode="json", by_alias=True)
    if not isinstance(value, dict):
        raise ValueError("Plan placement catalog must be a versioned object")
    if value.get("schema") == "dmb_plan_placement_catalog_v2":
        return PlanPlacementCatalogV2.model_validate(value)
    # V1 historically allowed its default schema to be omitted. Unknown explicit
    # schemas still fail V1's Literal check; they never fall back to a V2 guess.
    return PlanPlacementCatalogV1.model_validate(value)


PlanPlacementCatalog = Annotated[
    PlanPlacementCatalogV2 | PlanPlacementCatalogV1,
    BeforeValidator(decode_plan_placement_catalog),
]


class PlanRequestedWorkInputV2(PlanRequestedWorkInputV1):
    schema_: Literal["dmb_plan_requested_work_input_v2"] = Field(
        default="dmb_plan_requested_work_input_v2", alias="schema")
    placement_catalog: PlanPlacementCatalog | None
    original_capture: PlanAuthoringCaptureV1 | None

    @model_validator(mode="after")
    def exact_catalog(self):
        if self.target_available != (self.original_capture is not None):
            raise ValueError("Plan decision requires its complete original capture")
        if self.original_capture is not None and self.original_capture.sha256 != self.target_capture_sha256:
            raise ValueError("Plan original capture differs from its frozen digest")
        if self.placement_catalog is not None and self.original_capture is not None:
            self.placement_catalog.require_original(self.original_capture)
        if self.target_available != (self.placement_catalog is not None):
            raise ValueError("Current Plan capture requires its frozen placement catalog")
        if (self.placement_catalog is not None
                and self.placement_catalog.original_capture_sha256 != self.target_capture_sha256):
            raise ValueError("Plan decision catalog differs from its original capture")
        return self


class PlanRequestedWorkInputV3(PlanRequestedWorkInputV2):
    """Current request precedence; same captured placement authority as V2."""
    schema_: Literal["dmb_plan_requested_work_input_v3"] = Field(
        default="dmb_plan_requested_work_input_v3", alias="schema")




class PlanRequestedWorkInputV4(PlanRequestedWorkInputV3):
    """Current Plan destination decision with its exact authored selections."""
    schema_: Literal["dmb_plan_requested_work_input_v4"] = Field(
        default="dmb_plan_requested_work_input_v4", alias="schema")
    authored_references: AuthoredReferencesV2

    @model_validator(mode="after")
    def nonempty_references(self):
        if not self.authored_references.references:
            raise ValueError('Plan reference decision requires actual author selections')
        return self


class PlanRequestedWorkInputV5(PlanRequestedWorkInputV3):
    """Exact explicit operation plus optional author-selected references."""
    schema_: Literal["dmb_plan_requested_work_input_v5"] = Field(
        default="dmb_plan_requested_work_input_v5", alias="schema")
    plan_requested_operation: Literal["discuss", "write_current_page"]
    authored_references: AuthoredReferencesV2 | None

    @model_validator(mode="after")
    def actual_references(self):
        if self.authored_references is not None and not self.authored_references.references:
            raise ValueError("Explicit Plan reference input cannot be empty")
        return self


class PlanRequestedWorkInputV6(PlanRequestedWorkInputV5):
    """Current semantic reference projection; full bindings stay in this parent."""
    schema_: Literal["dmb_plan_requested_work_input_v6"] = Field(
        default="dmb_plan_requested_work_input_v6", alias="schema")
    plan_requested_operation: Literal["discuss", "write_current_page"] | None = None


class PlanRequestedWorkInputV7(PlanRequestedWorkInputV6):
    """Intent-first classification; earlier parents retain their exact wire proof."""
    schema_: Literal["dmb_plan_requested_work_input_v7"] = Field(
        default="dmb_plan_requested_work_input_v7", alias="schema")


class PlanRequestedWorkInputV8(PlanRequestedWorkInputV7):
    """Page creation is explicit; an arbitrary other destination grants nothing."""
    schema_: Literal["dmb_plan_requested_work_input_v8"] = Field(
        default="dmb_plan_requested_work_input_v8", alias="schema")


class PlanRequestedWorkInputV9(PlanRequestedWorkInputV8):
    """Intent and the complete compatible-location set are separate judgments."""
    schema_: Literal["dmb_plan_requested_work_input_v9"] = Field(
        default="dmb_plan_requested_work_input_v9", alias="schema")


def work_choice(request: PlanRequestedWorkInputV2, selected: str, *, contextual_answers=None):
    """Decode only offered choices; the selected target digest stays host-owned."""
    if isinstance(request, PlanRequestedWorkInputV9):
        from .plan_contextual_targets import contextual_work_choice
        if contextual_answers is None:
            raise ValueError("Contextual intent requires its complete anchor and relation judgments")
        return contextual_work_choice(request, selected, contextual_answers)
    if selected == 'review_connected_page':
        if not isinstance(request, PlanRequestedWorkInputV8) or request.plan_requested_operation is not None:
            raise ValueError('Connected-page review was not offered for this operation')
        return dict(requested_work=selected, placement_selector=None, target_capture_sha256=None)
    if selected in {"discuss", "clarify", "different_destination"}:
        return dict(requested_work=selected, placement_selector=None, target_capture_sha256=None)
    if selected == "write_unavailable" and request.placement_catalog is None:
        return dict(requested_work="write_current_page", placement_selector=None, target_capture_sha256=None)
    if selected.startswith("write:") and request.placement_catalog is not None:
        selector = selected.removeprefix("write:")
        entry = next((row for row in request.placement_catalog.entries if row.selector == selector), None)
        if entry is not None:
            return dict(requested_work="write_current_page", placement_selector=selector,
                target_capture_sha256=entry.target_capture_sha256)
    raise ValueError("Plan work/placement choice was not offered")
