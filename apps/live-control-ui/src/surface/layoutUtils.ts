import type { SurfaceLayout, SurfaceModuleInstance, SurfaceSlot } from "../api/types";

export const REQUIRED_MODULE_IDS = ["chat", "record"] as const;

export const SURFACE_SLOTS: SurfaceSlot[] = ["main", "sidebar", "bottom", "overlay"];

export function isRequiredModule(moduleId: string): boolean {
  return (REQUIRED_MODULE_IDS as readonly string[]).includes(moduleId);
}

export function sortModules(modules: SurfaceModuleInstance[]): SurfaceModuleInstance[] {
  const slotOrder: Record<SurfaceSlot, number> = {
    main: 0,
    sidebar: 1,
    bottom: 2,
    overlay: 3,
  };
  return [...modules].sort((a, b) => {
    const slotDiff = slotOrder[a.slot] - slotOrder[b.slot];
    if (slotDiff !== 0) {
      return slotDiff;
    }
    return a.order - b.order;
  });
}

export function enabledModules(layout: SurfaceLayout): SurfaceModuleInstance[] {
  return sortModules(layout.modules.filter((row) => row.enabled));
}

export function cloneLayout(layout: SurfaceLayout): SurfaceLayout {
  return {
    ...layout,
    modules: layout.modules.map((row) => ({
      ...row,
      config: { ...row.config },
    })),
  };
}

export function findModuleRow(
  layout: SurfaceLayout,
  moduleId: string,
): SurfaceModuleInstance | undefined {
  return layout.modules.find((row) => row.module_id === moduleId);
}

export function updateModuleRow(
  layout: SurfaceLayout,
  moduleId: string,
  patch: Partial<SurfaceModuleInstance>,
): SurfaceLayout {
  const next = cloneLayout(layout);
  const index = next.modules.findIndex((row) => row.module_id === moduleId);
  if (index < 0) {
    return next;
  }
  next.modules[index] = { ...next.modules[index], ...patch };
  return next;
}

export function reorderInSlot(
  layout: SurfaceLayout,
  moduleId: string,
  direction: "up" | "down",
): SurfaceLayout {
  const next = cloneLayout(layout);
  const row = findModuleRow(next, moduleId);
  if (!row) {
    return next;
  }
  const peers = next.modules
    .filter((m) => m.slot === row.slot)
    .sort((a, b) => a.order - b.order);
  const index = peers.findIndex((m) => m.module_id === moduleId);
  const swapIndex = direction === "up" ? index - 1 : index + 1;
  if (swapIndex < 0 || swapIndex >= peers.length) {
    return next;
  }
  const swapId = peers[swapIndex].module_id;
  const a = findModuleRow(next, moduleId);
  const b = findModuleRow(next, swapId);
  if (!a || !b) {
    return next;
  }
  const aOrder = a.order;
  a.order = b.order;
  b.order = aOrder;
  return next;
}
