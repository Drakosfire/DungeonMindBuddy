import type { PlanViewRef, ProjectionSourceStatus, ProjectionTargetType } from "../api/types";

export interface PaneTargetOrigin {
  module_id: string;
  row_id?: string | null;
}

export interface PaneTarget {
  target_type: ProjectionTargetType;
  target_id: string;
  label: string;
  source_status: ProjectionSourceStatus;
  role?: string | null;
  origin?: PaneTargetOrigin;
}

export function formatTargetType(targetType: ProjectionTargetType): string {
  return targetType.replace(/_/g, " ");
}

export function paneTargetFromPlanViewRef(
  ref: PlanViewRef,
  origin?: PaneTargetOrigin,
): PaneTarget {
  return {
    target_type: ref.target_type,
    target_id: ref.target_id,
    label: ref.label,
    source_status: ref.source_status,
    role: ref.role ?? null,
    origin,
  };
}
