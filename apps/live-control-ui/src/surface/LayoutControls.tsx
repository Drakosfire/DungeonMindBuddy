import { useState } from "react";

import { putSurfaceLayout } from "../api/liveApi";
import type { SurfaceLayout, SurfaceModuleDefinition, SurfaceSlot } from "../api/types";
import {
  cloneLayout,
  isRequiredModule,
  reorderInSlot,
  SURFACE_SLOTS,
  updateModuleRow,
} from "./layoutUtils";

interface LayoutControlsProps {
  layout: SurfaceLayout;
  catalog: SurfaceModuleDefinition[];
  onLayoutSaved: (layout: SurfaceLayout) => void | Promise<void>;
}

export function LayoutControls({ layout, catalog, onLayoutSaved }: LayoutControlsProps) {
  const [draft, setDraft] = useState(() => cloneLayout(layout));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const catalogById = new Map(catalog.map((row) => [row.module_id, row]));

  async function persist(next: SurfaceLayout) {
    setSaving(true);
    setError(null);
    try {
      const saved = await putSurfaceLayout(next);
      setDraft(cloneLayout(saved.layout));
      await onLayoutSaved(saved.layout);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Layout save failed");
    } finally {
      setSaving(false);
    }
  }

  function toggleEnabled(moduleId: string, enabled: boolean) {
    if (isRequiredModule(moduleId) && !enabled) {
      return;
    }
    const next = updateModuleRow(draft, moduleId, { enabled });
    setDraft(next);
  }

  function moveSlot(moduleId: string, slot: SurfaceSlot) {
    setDraft(updateModuleRow(draft, moduleId, { slot }));
  }

  function toggleCollapsed(moduleId: string) {
    const row = draft.modules.find((m) => m.module_id === moduleId);
    if (!row) {
      return;
    }
    setDraft(updateModuleRow(draft, moduleId, { collapsed: !row.collapsed }));
  }

  return (
    <section className="layout-controls" aria-label="Layout controls">
      <h2 className="layout-controls-title">Layout</h2>
      <ul className="layout-controls-list">
        {draft.modules.map((row) => {
          const definition = catalogById.get(row.module_id);
          const required = isRequiredModule(row.module_id) || definition?.required;
          return (
            <li key={row.module_id} className="layout-control-row">
              <div className="layout-control-header">
                <strong>{definition?.title ?? row.module_id}</strong>
                {required ? <span className="badge locked">required</span> : null}
              </div>
              <label className="layout-toggle">
                <input
                  type="checkbox"
                  checked={row.enabled}
                  disabled={required}
                  onChange={(event) => toggleEnabled(row.module_id, event.target.checked)}
                />
                Enabled
              </label>
              <label className="layout-select">
                Slot
                <select
                  value={row.slot}
                  onChange={(event) =>
                    moveSlot(row.module_id, event.target.value as SurfaceSlot)
                  }
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
                  onClick={() => setDraft(reorderInSlot(draft, row.module_id, "up"))}
                >
                  Up
                </button>
                <button
                  type="button"
                  onClick={() => setDraft(reorderInSlot(draft, row.module_id, "down"))}
                >
                  Down
                </button>
                <button type="button" onClick={() => toggleCollapsed(row.module_id)}>
                  {row.collapsed ? "Expand" : "Collapse"}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <div className="layout-actions">
        <button type="button" disabled={saving} onClick={() => persist(draft)}>
          {saving ? "Saving…" : "Save layout"}
        </button>
      </div>
      {error ? <p className="module-error">{error}</p> : null}
    </section>
  );
}
