/**
 * Whole-publication structural validation (SIH-01).
 *
 * Authority: handoff §6.3–§6.10. Pure, deterministic, non-throwing for ordinary
 * invalid publications. Never invokes callbacks, never inspects binding values,
 * never clones the input, and never falls back to labels, first matches, or
 * global state. Any material contradiction invalidates the whole publication;
 * no partially accepted contribution set is ever returned.
 */

import type {
  SurfaceInteractionAvailability,
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPlacement,
  SurfaceInteractionProjectionDescriptor,
  SurfaceInteractionPublication,
  SurfaceInteractionToolContribution,
  SurfaceInteractionValidationIssue,
  SurfaceInteractionValidationResult,
} from "./types";

const PROJECTION_KINDS: ReadonlySet<string> = new Set(["tool", "content"]);
const PROJECTION_SIZES: ReadonlySet<string> = new Set(["compact", "wide", "fullscreen"]);

function isBlank(value: unknown): boolean {
  return typeof value !== "string" || value.trim().length === 0;
}

// Typed callers always pass real arrays; the Array.isArray check is the
// runtime defense for untyped input reaching validation (handoff §6.6).
function asArray<T>(value: readonly T[]): readonly T[] {
  return Array.isArray(value) ? value : [];
}

function validateAvailability(
  availability: SurfaceInteractionAvailability,
  owner: { contributionId: string; contributionIndex: number },
  issues: SurfaceInteractionValidationIssue[],
): void {
  if (availability.status === "disabled" && isBlank(availability.disabledReason)) {
    issues.push({
      code: "disabled_reason_missing",
      message: `Contribution "${owner.contributionId}" is disabled without a human-readable reason.`,
      ...owner,
    });
  }
  // != null (not a blankness check): an enabled contribution is incoherent the
  // moment a disabled reason is supplied at all, even an empty string.
  if (availability.status === "enabled" && availability.disabledReason != null) {
    issues.push({
      code: "enabled_has_disabled_reason",
      message: `Contribution "${owner.contributionId}" is enabled but carries a disabled reason.`,
      ...owner,
    });
  }
}

function validatePlacement(
  placement: SurfaceInteractionPlacement,
  owner: { contributionId: string; contributionIndex: number },
  issues: SurfaceInteractionValidationIssue[],
): void {
  const problems: string[] = [];
  if ((placement.groupId == null) !== (placement.groupLabel == null)) {
    problems.push("group ID/label nullability disagrees");
  }
  if (placement.groupId != null && isBlank(placement.groupId)) problems.push("group ID is blank");
  if (placement.groupLabel != null && isBlank(placement.groupLabel)) {
    problems.push("group label is blank");
  }
  if (!Number.isInteger(placement.groupOrder)) problems.push("group order is not a finite integer");
  if (!Number.isInteger(placement.itemOrder)) problems.push("item order is not a finite integer");
  if (problems.length > 0) {
    issues.push({
      code: "placement_invalid",
      message: `Contribution "${owner.contributionId}" placement is invalid: ${problems.join("; ")}.`,
      ...owner,
    });
  }
}

function collectDuplicateIds(
  ids: readonly string[],
  code: SurfaceInteractionValidationIssue["code"],
  label: string,
  issues: SurfaceInteractionValidationIssue[],
): void {
  // Blank IDs are already reported as contribution_id_blank; they never
  // participate in duplicate detection.
  const indicesById = new Map<string, number[]>();
  ids.forEach((id, index) => {
    if (isBlank(id)) return;
    const existing = indicesById.get(id);
    if (existing) existing.push(index);
    else indicesById.set(id, [index]);
  });
  for (const [id, indices] of indicesById) {
    if (indices.length < 2) continue;
    issues.push({
      code,
      message: `${label} "${id}" is declared more than once (indices ${indices.join(", ")}).`,
      contributionId: id,
      contributionIndex: indices[0],
    });
  }
}

function validateTool(
  tool: SurfaceInteractionToolContribution,
  index: number,
  issues: SurfaceInteractionValidationIssue[],
): void {
  const owner = { contributionId: tool.id, contributionIndex: index };
  if (isBlank(tool.id)) {
    issues.push({
      code: "contribution_id_blank",
      message: `Tool contribution at index ${index} has a blank ID.`,
      contributionId: "",
      contributionIndex: index,
    });
  }
  validatePlacement(tool.placement, owner, issues);
  validateAvailability(tool.availability, owner, issues);
  const activation = tool.activation;
  if (activation == null || (activation.kind !== "projection" && activation.kind !== "command")) {
    issues.push({
      code: "tool_activation_invalid",
      message: `Tool contribution "${tool.id}" has a missing or unknown activation discriminant.`,
      ...owner,
    });
    return;
  }
  if (activation.kind === "command" && typeof activation.invoke !== "function") {
    issues.push({
      code: "tool_activation_invalid",
      message: `Tool contribution "${tool.id}" command activation is missing its invoke callback.`,
      ...owner,
    });
  }
}

function validateEditCommand(
  command: SurfaceInteractionEditCommandContribution,
  index: number,
  issues: SurfaceInteractionValidationIssue[],
): void {
  const owner = { contributionId: command.id, contributionIndex: index };
  if (isBlank(command.id)) {
    issues.push({
      code: "contribution_id_blank",
      message: `Edit command contribution at index ${index} has a blank ID.`,
      contributionId: "",
      contributionIndex: index,
    });
  }
  validatePlacement(command.placement, owner, issues);
  validateAvailability(command.availability, owner, issues);
  if (isBlank(command.target?.kind) || isBlank(command.target?.id)) {
    issues.push({
      code: "command_target_invalid",
      message: `Edit command contribution "${command.id}" has a blank target kind or ID.`,
      ...owner,
    });
  }
  if (typeof command.invoke !== "function") {
    issues.push({
      code: "edit_command_invoke_invalid",
      message: `Edit command contribution "${command.id}" is missing its invoke callback.`,
      ...owner,
    });
  }
}

function validateProjection(
  projection: SurfaceInteractionProjectionDescriptor,
  index: number,
  issues: SurfaceInteractionValidationIssue[],
): void {
  const owner = { contributionId: projection.id, contributionIndex: index };
  if (isBlank(projection.id)) {
    issues.push({
      code: "contribution_id_blank",
      message: `Projection contribution at index ${index} has a blank ID.`,
      contributionId: "",
      contributionIndex: index,
    });
  }
  if (!PROJECTION_KINDS.has(projection.kind)) {
    issues.push({
      code: "projection_kind_unknown",
      message: `Projection "${projection.id}" has unknown kind "${String(projection.kind)}".`,
      ...owner,
    });
  }
  if (!PROJECTION_SIZES.has(projection.preferredSize)) {
    issues.push({
      code: "projection_size_unknown",
      message:
        `Projection "${projection.id}" has unknown preferred size ` +
        `"${String(projection.preferredSize)}".`,
      ...owner,
    });
  }
}

export function validateSurfaceInteractionPublication<TBinding = unknown>(
  publication: SurfaceInteractionPublication<TBinding>,
): SurfaceInteractionValidationResult<TBinding> {
  const issues: SurfaceInteractionValidationIssue[] = [];

  // 1. Publication and identity.
  if (isBlank(publication.surfaceId)) {
    issues.push({
      code: "surface_id_blank",
      message: "Publication surface ID is blank.",
    });
  }
  if (isBlank(publication.identity?.instanceKey)) {
    issues.push({
      code: "instance_key_blank",
      message: "Surface identity instance key is blank.",
    });
  }
  if (publication.surfaceId !== publication.identity?.surfaceId) {
    issues.push({
      code: "identity_surface_mismatch",
      message:
        `Publication surface ID "${String(publication.surfaceId)}" does not match identity ` +
        `surface ID "${String(publication.identity?.surfaceId)}".`,
    });
  }
  if (isBlank(publication.label)) {
    issues.push({
      code: "publication_label_blank",
      message: "Publication label is blank.",
    });
  }

  // 2. Canvas contribution.
  if (publication.canvas != null) {
    const canvas = publication.canvas;
    if (
      isBlank(canvas.canvasId) ||
      isBlank(canvas.workObject?.kind) ||
      isBlank(canvas.workObject?.id)
    ) {
      issues.push({
        code: "canvas_identity_invalid",
        message: "Canvas contribution has a blank canvas ID or work-object kind/ID.",
        contributionId: typeof canvas.canvasId === "string" ? canvas.canvasId : "",
      });
    }
  }

  // 3. Agent-context contribution.
  if (publication.agentContext != null) {
    const context = publication.agentContext;
    const problems: string[] = [];
    if (isBlank(context.label)) problems.push("label is blank");
    const stringOrNullFields = [
      ["campaignId", context.campaignId],
      ["documentId", context.documentId],
      ["ambientSummary", context.ambientSummary],
    ] as const;
    for (const [field, value] of stringOrNullFields) {
      if (value !== null && typeof value !== "string") {
        problems.push(`${field} must be a string or null`);
      }
    }
    if (
      context.sessionNumber !== null &&
      (typeof context.sessionNumber !== "number" || !Number.isFinite(context.sessionNumber))
    ) {
      problems.push("sessionNumber must be a finite number or null");
    }
    if (!Array.isArray(context.pointers)) problems.push("pointers must be an array");
    if (problems.length > 0) {
      issues.push({
        code: "agent_context_invalid",
        message: `Agent-context contribution is invalid: ${problems.join("; ")}.`,
      });
    }
    asArray(context.pointers).forEach((pointer, index) => {
      if (isBlank(pointer?.kind) || isBlank(pointer?.value)) {
        issues.push({
          code: "agent_pointer_invalid",
          message: `Agent-context pointer at index ${index} has a blank kind or value.`,
          contributionIndex: index,
        });
      }
    });
  }

  // 4. Tool collection, in collection order.
  const tools = asArray(publication.tools);
  tools.forEach((tool, index) => validateTool(tool, index, issues));
  collectDuplicateIds(
    tools.map((tool) => tool.id),
    "duplicate_tool_id",
    "Tool contribution",
    issues,
  );

  // 5. Edit command collection, in collection order.
  const editCommands = asArray(publication.editCommands);
  editCommands.forEach((command, index) => validateEditCommand(command, index, issues));
  collectDuplicateIds(
    editCommands.map((command) => command.id),
    "duplicate_edit_command_id",
    "Edit command contribution",
    issues,
  );

  // 6. Projection collection, in collection order.
  const projections = asArray(publication.projections);
  projections.forEach((projection, index) => validateProjection(projection, index, issues));
  collectDuplicateIds(
    projections.map((projection) => projection.id),
    "duplicate_projection_id",
    "Projection contribution",
    issues,
  );

  // 7. Projection binding collection, in collection order.
  const bindings = asArray(publication.projectionBindings);
  bindings.forEach((binding, index) => {
    if (isBlank(binding.id)) {
      issues.push({
        code: "contribution_id_blank",
        message: `Projection binding at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
  });
  collectDuplicateIds(
    bindings.map((binding) => binding.id),
    "duplicate_projection_binding_id",
    "Projection binding",
    issues,
  );

  // 8. Cross-reference checks. Contributions with blank IDs are already invalid
  // declarations, so they can never satisfy an exact reference.
  const declaredProjections = new Map<string, SurfaceInteractionProjectionDescriptor>();
  for (const projection of projections) {
    if (isBlank(projection.id) || declaredProjections.has(projection.id)) continue;
    declaredProjections.set(projection.id, projection);
  }
  tools.forEach((tool, index) => {
    if (tool.activation == null || tool.activation.kind !== "projection") return;
    const targetId = tool.activation.projectionId;
    const target = isBlank(targetId) ? undefined : declaredProjections.get(targetId);
    if (!target) {
      issues.push({
        code: "tool_projection_missing",
        message:
          `Tool contribution "${tool.id}" targets projection "${String(targetId)}", ` +
          "which is not declared.",
        contributionId: tool.id,
        contributionIndex: index,
        referencedId: typeof targetId === "string" ? targetId : "",
      });
      return;
    }
    if (target.kind !== "tool") {
      issues.push({
        code: "tool_projection_kind_mismatch",
        message:
          `Tool contribution "${tool.id}" targets projection "${target.id}" of kind ` +
          `"${String(target.kind)}"; only kind "tool" may be activated.`,
        contributionId: tool.id,
        contributionIndex: index,
        referencedId: target.id,
      });
    }
  });

  const declaredBindingIds = new Set<string>();
  for (const binding of bindings) {
    if (!isBlank(binding.id)) declaredBindingIds.add(binding.id);
  }
  projections.forEach((projection, projectionIndex) => {
    const seen = new Set<string>();
    asArray(projection.bindingIds).forEach((bindingId) => {
      if (seen.has(bindingId)) {
        issues.push({
          code: "projection_binding_duplicate_reference",
          message:
            `Projection "${projection.id}" repeats binding reference "${String(bindingId)}".`,
          contributionId: projection.id,
          contributionIndex: projectionIndex,
          referencedId: typeof bindingId === "string" ? bindingId : "",
        });
        return;
      }
      seen.add(bindingId);
      if (isBlank(bindingId) || !declaredBindingIds.has(bindingId)) {
        issues.push({
          code: "projection_binding_missing",
          message:
            `Projection "${projection.id}" requires binding "${String(bindingId)}", ` +
            "which is not declared.",
          contributionId: projection.id,
          contributionIndex: projectionIndex,
          referencedId: typeof bindingId === "string" ? bindingId : "",
        });
      }
    });
  });

  if (issues.length === 0) {
    return { valid: true, publication };
  }
  return { valid: false, publication, issues };
}
