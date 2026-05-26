import { useLayoutDraft } from "./LayoutDraftContext";
import { isRequiredModule, sortModules } from "./layoutUtils";
import { ModuleLayoutControls } from "./ModuleLayoutControls";
import { catalogTitle } from "./moduleRegistry";

/** Disabled optional modules — layout controls only, not shown in the live surface grid. */
export function SurfaceLayoutPanel() {
  const { draft, catalogById } = useLayoutDraft();
  const disabledOptional = sortModules(
    draft.modules.filter((row) => !row.enabled && !isRequiredModule(row.module_id)),
  );

  if (disabledOptional.length === 0) {
    return null;
  }

  return (
    <aside
      className="surface-layout-panel"
      role="region"
      aria-label="Hidden modules — layout controls"
    >
      <h2 className="surface-layout-panel-title">Hidden modules</h2>
      <p className="module-muted surface-layout-panel-hint">
        Turn a module on to add it back to the live surface.
      </p>
      <ul className="surface-layout-panel-list">
        {disabledOptional.map((row) => (
          <li key={row.module_id} className="surface-layout-panel-row" data-module-id={row.module_id}>
            <div className="surface-layout-panel-row-header">
              <h3>{catalogTitle(catalogById, row.module_id)}</h3>
              <ModuleLayoutControls moduleId={row.module_id} />
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
