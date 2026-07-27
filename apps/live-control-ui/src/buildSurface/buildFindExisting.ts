export const BUILD_FIND_EXISTING_EVENT = "dmb-build-find-existing";

export interface BuildFindExistingDetail {
  query: string;
  kindHint?: string | null;
}

export function dispatchBuildFindExisting(detail: BuildFindExistingDetail): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<BuildFindExistingDetail>(BUILD_FIND_EXISTING_EVENT, { detail }),
  );
}
