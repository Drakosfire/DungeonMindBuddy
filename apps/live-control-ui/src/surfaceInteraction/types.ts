/**
 * Surface-neutral interaction publication contract (SIH-01).
 *
 * Authority: Docs/Plans/HANDOFF-sih01-neutral-surface-interaction-contracts.md §6.1.
 * Runtime-only, non-durable, no provider lease tokens, no React/JSX payloads.
 */

export interface SurfaceInteractionIdentity {
  surfaceId: string;
  /** Opaque exact instance key — structured tuple encoding, never labels. */
  instanceKey: string;
}

export type SurfaceInteractionInstancePart = string | number | boolean | null;

export type SurfaceInteractionAvailability =
  | { status: "enabled"; disabledReason?: never }
  | { status: "disabled"; disabledReason: string };

export interface SurfaceInteractionPointer {
  kind: string;
  value: string;
}

export interface SurfaceInteractionWorkObjectIdentity {
  kind: string;
  id: string;
}

export interface SurfaceInteractionCanvasContribution {
  canvasId: string;
  workObject: SurfaceInteractionWorkObjectIdentity;
}

export interface SurfaceInteractionAgentContextContribution {
  label: string;
  campaignId: string | null;
  documentId: string | null;
  sessionNumber: number | null;
  ambientSummary: string | null;
  pointers: readonly SurfaceInteractionPointer[];
}

export interface SurfaceInteractionPlacement {
  /** Null means pinned/top-level. */
  groupId: string | null;
  /** Null iff groupId is null. */
  groupLabel: string | null;
  groupOrder: number;
  itemOrder: number;
  /**
   * Optional group fold default. Must be absent when groupId is null.
   * Same groupId contributors must agree on presence and value.
   */
  groupDefaultOpen?: boolean;
}

export type SurfaceInteractionToolActivation =
  | { kind: "projection"; projectionId: string }
  | { kind: "command"; invoke: () => void | Promise<void> };

export interface SurfaceInteractionToolContribution {
  id: string;
  label: string;
  eyebrow?: string;
  placement: SurfaceInteractionPlacement;
  availability: SurfaceInteractionAvailability;
  activation: SurfaceInteractionToolActivation;
}

export interface SurfaceInteractionCommandTarget {
  kind: string;
  id: string;
}

export interface SurfaceInteractionEditCommandContribution {
  id: string;
  label: string;
  eyebrow?: string;
  placement: SurfaceInteractionPlacement;
  availability: SurfaceInteractionAvailability;
  target: SurfaceInteractionCommandTarget;
  /** Optional toggle/pressed presentation for Edit Host buttons. */
  pressed?: boolean;
  invoke: () => void | Promise<void>;
}

export type SurfaceInteractionProjectionKind = "tool" | "content";

export type SurfaceInteractionProjectionSize = "compact" | "wide" | "fullscreen";

export interface SurfaceInteractionProjectionDescriptor {
  id: string;
  kind: SurfaceInteractionProjectionKind;
  preferredSize: SurfaceInteractionProjectionSize;
  bindingIds: readonly string[];
}

export interface SurfaceInteractionProjectionBinding {
  id: string;
  value: unknown;
}

export interface SurfaceInteractionPublication {
  surfaceId: string;
  label: string;
  identity: SurfaceInteractionIdentity;
  canvas: SurfaceInteractionCanvasContribution | null;
  agentContext: SurfaceInteractionAgentContextContribution | null;
  tools: readonly SurfaceInteractionToolContribution[];
  editCommands: readonly SurfaceInteractionEditCommandContribution[];
  projections: readonly SurfaceInteractionProjectionDescriptor[];
  projectionBindings: readonly SurfaceInteractionProjectionBinding[];
}

/**
 * Stable issue codes. The §6.3 table is the complete public vocabulary — all
 * 29 codes, in table order. Adding, renaming, or removing a code requires
 * amending the handoff; implementations must not invent extension codes.
 */
export type SurfaceInteractionValidationIssueCode =
  | "publication_shape_invalid"
  | "contribution_shape_invalid"
  | "surface_id_blank"
  | "instance_key_blank"
  | "identity_surface_mismatch"
  | "publication_label_blank"
  | "contribution_id_blank"
  | "contribution_label_blank"
  | "duplicate_tool_id"
  | "duplicate_edit_command_id"
  | "duplicate_projection_id"
  | "duplicate_projection_binding_id"
  | "placement_invalid"
  | "placement_group_conflict"
  | "disabled_reason_missing"
  | "enabled_has_disabled_reason"
  | "tool_activation_invalid"
  | "edit_command_invoke_invalid"
  | "tool_projection_missing"
  | "tool_projection_kind_mismatch"
  | "projection_kind_unknown"
  | "projection_size_unknown"
  | "projection_binding_missing"
  | "projection_binding_duplicate_reference"
  | "canvas_identity_invalid"
  | "command_target_invalid"
  | "agent_context_invalid"
  | "agent_pointer_invalid"
  | "agent_context_bounds_exceeded";

export interface SurfaceInteractionValidationIssue {
  code: SurfaceInteractionValidationIssueCode;
  /** Human-readable summary. Never carries callback source, binding values, or document bodies. */
  message: string;
  /** Exact contribution ID where applicable (may be blank when blankness is the defect). */
  contributionId?: string;
  /** Collection index of the offending contribution where applicable. */
  contributionIndex?: number;
  /** Exact referenced ID (projection target, binding ID) where applicable. */
  referencedId?: string;
}

export type SurfaceInteractionValidationResult =
  | { valid: true; publication: SurfaceInteractionPublication }
  | {
      valid: false;
      publication: unknown;
      issues: readonly SurfaceInteractionValidationIssue[];
    };
