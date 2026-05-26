import type { SurfaceSlot } from "../api/types";
import { useLayoutDraft } from "./LayoutDraftContext";
import {
  findModuleRow,
  isRequiredModule,
  reorderInSlot,
  SURFACE_SLOTS,
  updateModuleRow,
} from "./layoutUtils";

interface ModuleLayoutControlsProps {
  moduleId: string;
}

export function ModuleLayoutControls({ moduleId }: ModuleLayoutControlsProps) {
  const { draft, setDraft, catalogById, saving, error, persist } = useLayoutDraft();
  const moduleRow = findModuleRow(draft, moduleId);
  if (!moduleRow) {
    return null;
  }

  const definition = catalogById.get(moduleId);
  const required = isRequiredModule(moduleId) || definition?.required;
  const title = definition?.title ?? moduleId;

  function toggleEnabled(enabled: boolean) {
    if (required && !enabled) {
      return;
    }
    setDraft(updateModuleRow(draft, moduleId, { enabled }));
  }

  function moveSlot(slot: SurfaceSlot) {
    setDraft(updateModuleRow(draft, moduleId, { slot }));
  }

  function toggleCollapsed() {
    const current = findModuleRow(draft, moduleId);
    if (!current) {
      return;
    }
    setDraft(updateModuleRow(draft, moduleId, { collapsed: !current.collapsed }));
  }

  return (
    <div
      className="module-layout-controls"
      aria-label={`Layout controls for ${title}`}
      onClick={(event) => event.stopPropagation()}
    >
      <label className="layout-toggle">
        <input
          type="checkbox"
          checked={moduleRow.enabled}
          disabled={required}
          onChange={(event) => toggleEnabled(event.target.checked)}
        />
        <span>On</span>
      </label>
      <label className="layout-select">
        <span className="sr-only">Slot for {title}</span>
        <select
          value={moduleRow.slot}
          onChange={(event) => moveSlot(event.target.value as SurfaceSlot)}
          aria-label={`Slot for ${title}`}
        >
          {SURFACE_SLOTS.map((slot) => (
            <option key={slot} value={slot}>
              {slot}
            </option>
          ))}
        </select>
      </label>
      <div className="layout-buttons">
        <button
          type="button"
          aria-label={`Move ${title} up`}
          onClick={() => setDraft(reorderInSlot(draft, moduleId, "up"))}
        >
          Up
        </button>
        <button
          type="button"
          aria-label={`Move ${title} down`}
          onClick={() => setDraft(reorderInSlot(draft, moduleId, "down"))}
        >
          Down
        </button>
        <button type="button" onClick={toggleCollapsed}>
          {moduleRow.collapsed ? "Expand" : "Collapse"}
        </button>
        <button type="button" disabled={saving} onClick={() => persist()}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      {required ? <span className="badge locked">required</span> : null}
      {error ? <p className="module-error module-layout-error">{error}</p> : null}
    </div>
  );
}
