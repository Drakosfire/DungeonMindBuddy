"""Snapshot-local Plan navigation. A selector grants no evidence or Save authority."""
from __future__ import annotations

from typing import Literal
from pydantic import Field, model_validator

from .plan_authoring import (
    Frozen, PlanAuthoringCaptureV1, PlanAuthoringBoundaryCaptureV1,
    digest, strict_json,
)


class PlanPlacementOptionV1(Frozen):
    selector: str = Field(min_length=1)
    kind: Literal["captured_target", "before_heading", "after_section", "end_page"]
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
            prefix = "before:" if self.kind == "before_heading" else "after:"
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
            if entry.kind in {"before_heading", "after_section"}:
                index = int(entry.selector.split(":", 1)[1])
                if (index >= len(content) or content[index].get("type") != "heading"
                        or entry.kind == "before_heading" and entry.root_boundary != index
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
