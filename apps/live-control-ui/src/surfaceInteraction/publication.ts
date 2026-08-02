/**
 * Whole-publication structural validation (SIH-01).
 *
 * Authority: handoff §6.3–§6.10. Pure, deterministic, non-throwing for any
 * malformed input. Never invokes callbacks, never inspects binding values,
 * never clones the input, never coerces malformed collections, and never
 * converts untrusted values (no String()/toString/Symbol.toPrimitive paths —
 * diagnostics name malformed types instead). Nullability means exactly null,
 * required arrays must be dense (indexed iteration with Object.hasOwn), and
 * discriminant set checks require primitive strings via typeof. Any material
 * contradiction invalidates the whole publication; no partially accepted
 * contribution set is ever returned.
 */

import type {
  SurfaceInteractionAvailability,
  SurfaceInteractionPublication,
  SurfaceInteractionValidationIssue,
  SurfaceInteractionValidationResult,
} from "./types";

export const SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS = {
  ambientSummaryMaxChars: 500,
  pointersMaxEntries: 16,
  pointerKindMaxChars: 64,
  pointerValueMaxChars: 256,
} as const;

const PROJECTION_KINDS: ReadonlySet<string> = new Set(["tool", "content"]);
const PROJECTION_SIZES: ReadonlySet<string> = new Set(["compact", "wide", "fullscreen"]);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value != null && typeof value === "object" && !Array.isArray(value);
}

function isBlank(value: unknown): boolean {
  return typeof value !== "string" || value.trim().length === 0;
}

/** Type name for diagnostics — never invokes conversions on untrusted values. */
function describeType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

/** Safe diagnostic rendering: strings are quoted verbatim; anything else is named by type. */
function preview(value: unknown): string {
  return typeof value === "string" ? JSON.stringify(value) : describeType(value);
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
  if (availability.status === "enabled" && availability.disabledReason != null) {
    issues.push({
      code: "enabled_has_disabled_reason",
      message: `Contribution "${owner.contributionId}" is enabled but carries a disabled reason.`,
      ...owner,
    });
  }
}

function validatePlacementFields(
  placement: Record<string, unknown>,
  owner: { contributionId: string; contributionIndex: number },
  issues: SurfaceInteractionValidationIssue[],
): void {
  const groupId = placement.groupId;
  const groupLabel = placement.groupLabel;
  const groupOrder = placement.groupOrder;
  const itemOrder = placement.itemOrder;
  const problems: string[] = [];
  if ((groupId === null) !== (groupLabel === null)) {
    problems.push("group ID/label nullability disagrees (both exactly null, or both nonblank strings)");
  }
  if (groupId !== null && isBlank(groupId)) problems.push("group ID is blank or not a string");
  if (groupLabel !== null && isBlank(groupLabel)) problems.push("group label is blank or not a string");
  if (!Number.isInteger(groupOrder)) problems.push("group order is not a finite integer");
  if (!Number.isInteger(itemOrder)) problems.push("item order is not a finite integer");
  if (problems.length > 0) {
    issues.push({
      code: "placement_invalid",
      message: `Contribution "${owner.contributionId}" placement is invalid: ${problems.join("; ")}.`,
      ...owner,
    });
  }
}

function hasValidPlacementForGroupConflict(placement: Record<string, unknown>): boolean {
  const groupId = placement.groupId;
  if (groupId === null || isBlank(groupId)) return false;
  const groupLabel = placement.groupLabel;
  const groupOrder = placement.groupOrder;
  const itemOrder = placement.itemOrder;
  if ((groupId === null) !== (groupLabel === null)) return false;
  if (groupLabel !== null && isBlank(groupLabel)) return false;
  if (!Number.isInteger(groupOrder) || !Number.isInteger(itemOrder)) return false;
  return true;
}

/** Primitive-string IDs only, indexed so sparse arrays cannot skip entries. */
function collectIds(entries: readonly unknown[]): string[] {
  const ids: string[] = [];
  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    ids.push(isPlainObject(entry) && typeof entry.id === "string" ? entry.id : "");
  }
  return ids;
}

function collectDuplicateIds(
  ids: readonly string[],
  code: SurfaceInteractionValidationIssue["code"],
  label: string,
  issues: SurfaceInteractionValidationIssue[],
): void {
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

export function validateSurfaceInteractionPublication(
  publication: unknown,
): SurfaceInteractionValidationResult {
  const issues: SurfaceInteractionValidationIssue[] = [];

  // 1. Publication shape.
  if (!isPlainObject(publication)) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication must be a non-null object, got ${describeType(publication)}.`,
    });
    return { valid: false, publication, issues };
  }

  const pub = publication;
  const collectionFields = ["tools", "editCommands", "projections", "projectionBindings"] as const;
  for (const field of collectionFields) {
    if (!Array.isArray(pub[field])) {
      issues.push({
        code: "publication_shape_invalid",
        message: `Publication "${field}" must be an array, got ${describeType(pub[field])}.`,
      });
    }
  }
  if (pub.canvas !== null && !isPlainObject(pub.canvas)) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication canvas must be exactly null or an object, got ${describeType(pub.canvas)}.`,
    });
  }
  if (pub.agentContext !== null && !isPlainObject(pub.agentContext)) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication agentContext must be exactly null or an object, got ${describeType(pub.agentContext)}.`,
    });
  }

  const rawTools: unknown[] = Array.isArray(pub.tools) ? pub.tools : [];
  const rawEditCommands: unknown[] = Array.isArray(pub.editCommands) ? pub.editCommands : [];
  const rawProjections: unknown[] = Array.isArray(pub.projections) ? pub.projections : [];
  const rawBindings: unknown[] = Array.isArray(pub.projectionBindings) ? pub.projectionBindings : [];
  const toolShapeValid: boolean[] = [];
  const editShapeValid: boolean[] = [];
  const projectionShapeValid: boolean[] = [];
  const bindingShapeValid: boolean[] = [];

  // 2. Per-collection entry shape (Tool, Edit, Projection, binding order),
  //    indexed so sparse arrays cannot skip entries.
  for (let index = 0; index < rawTools.length; index += 1) {
    if (!Object.hasOwn(rawTools, index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Tool contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      toolShapeValid[index] = false;
      continue;
    }
    const entry = rawTools[index];
    if (!isPlainObject(entry)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Tool contribution at index ${index} must be a non-null object, got ${describeType(entry)}.`,
        contributionIndex: index,
      });
      toolShapeValid[index] = false;
      continue;
    }
    const nestedProblems: string[] = [];
    if (!isPlainObject(entry.placement)) nestedProblems.push("placement");
    if (!isPlainObject(entry.availability)) {
      nestedProblems.push("availability");
    } else {
      const status = (entry.availability as Record<string, unknown>).status;
      if (status !== "enabled" && status !== "disabled") {
        nestedProblems.push(`availability status discriminant is neither "enabled" nor "disabled" (got ${preview(status)})`);
      }
    }
    if (!isPlainObject(entry.activation)) nestedProblems.push("activation");
    if (entry.eyebrow !== undefined && typeof entry.eyebrow !== "string") {
      nestedProblems.push(`supplied eyebrow is not a string (got ${describeType(entry.eyebrow)})`);
    }
    if (nestedProblems.length > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Tool contribution at index ${index} has malformed structure: ` +
          `${nestedProblems.join("; ")}.`,
        contributionId: typeof entry.id === "string" ? entry.id : "",
        contributionIndex: index,
      });
      toolShapeValid[index] = false;
      continue;
    }
    toolShapeValid[index] = true;
  }

  for (let index = 0; index < rawEditCommands.length; index += 1) {
    if (!Object.hasOwn(rawEditCommands, index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Edit command contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      editShapeValid[index] = false;
      continue;
    }
    const entry = rawEditCommands[index];
    if (!isPlainObject(entry)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Edit command contribution at index ${index} must be a non-null object, got ${describeType(entry)}.`,
        contributionIndex: index,
      });
      editShapeValid[index] = false;
      continue;
    }
    const nestedProblems: string[] = [];
    if (!isPlainObject(entry.placement)) nestedProblems.push("placement");
    if (!isPlainObject(entry.availability)) {
      nestedProblems.push("availability");
    } else {
      const status = (entry.availability as Record<string, unknown>).status;
      if (status !== "enabled" && status !== "disabled") {
        nestedProblems.push(`availability status discriminant is neither "enabled" nor "disabled" (got ${preview(status)})`);
      }
    }
    if (!isPlainObject(entry.target)) nestedProblems.push("target");
    if (entry.eyebrow !== undefined && typeof entry.eyebrow !== "string") {
      nestedProblems.push(`supplied eyebrow is not a string (got ${describeType(entry.eyebrow)})`);
    }
    if (nestedProblems.length > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Edit command contribution at index ${index} has malformed structure: ` +
          `${nestedProblems.join("; ")}.`,
        contributionId: typeof entry.id === "string" ? entry.id : "",
        contributionIndex: index,
      });
      editShapeValid[index] = false;
      continue;
    }
    editShapeValid[index] = true;
  }

  for (let index = 0; index < rawProjections.length; index += 1) {
    if (!Object.hasOwn(rawProjections, index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      projectionShapeValid[index] = false;
      continue;
    }
    const entry = rawProjections[index];
    if (!isPlainObject(entry)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} must be a non-null object, got ${describeType(entry)}.`,
        contributionIndex: index,
      });
      projectionShapeValid[index] = false;
      continue;
    }
    const projectionId = typeof entry.id === "string" ? entry.id : "";
    if (!Array.isArray(entry.bindingIds)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} bindingIds must be an array, got ${describeType(entry.bindingIds)}.`,
        contributionId: projectionId,
        contributionIndex: index,
      });
      projectionShapeValid[index] = false;
      continue;
    }
    const bindingIds = entry.bindingIds as unknown[];
    let bindingIdsValid = true;
    for (let elementIndex = 0; elementIndex < bindingIds.length; elementIndex += 1) {
      if (!Object.hasOwn(bindingIds, elementIndex)) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Projection "${projectionId}" bindingIds index ${elementIndex} is missing (sparse array).`,
          contributionId: projectionId,
          contributionIndex: index,
        });
        bindingIdsValid = false;
        continue;
      }
      if (typeof bindingIds[elementIndex] !== "string") {
        issues.push({
          code: "contribution_shape_invalid",
          message:
            `Projection "${projectionId}" bindingIds index ${elementIndex} must be a string, ` +
            `got ${describeType(bindingIds[elementIndex])}.`,
          contributionId: projectionId,
          contributionIndex: index,
        });
        bindingIdsValid = false;
      }
    }
    projectionShapeValid[index] = bindingIdsValid;
  }

  for (let index = 0; index < rawBindings.length; index += 1) {
    if (!Object.hasOwn(rawBindings, index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      bindingShapeValid[index] = false;
      continue;
    }
    const entry = rawBindings[index];
    if (!isPlainObject(entry)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} must be a non-null object, got ${describeType(entry)}.`,
        contributionIndex: index,
      });
      bindingShapeValid[index] = false;
      continue;
    }
    bindingShapeValid[index] = true;
  }

  let identityShapeValid = false;
  if (!isPlainObject(pub.identity)) {
    issues.push({
      code: "contribution_shape_invalid",
      message: `Publication identity must be a non-null object, got ${describeType(pub.identity)}.`,
    });
  } else {
    identityShapeValid = true;
  }

  let canvasShapeValid = false;
  if (pub.canvas !== null && isPlainObject(pub.canvas)) {
    if (!isPlainObject(pub.canvas.workObject)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Canvas workObject must be a non-null object, got ${describeType(pub.canvas.workObject)}.`,
        contributionId: typeof pub.canvas.canvasId === "string" ? pub.canvas.canvasId : "",
      });
    } else {
      canvasShapeValid = true;
    }
  }

  const agentContextIsObject = pub.agentContext !== null && isPlainObject(pub.agentContext);
  if (agentContextIsObject) {
    const ctx = pub.agentContext as Record<string, unknown>;
    if (!Array.isArray(ctx.pointers)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Agent-context pointers must be an array, got ${describeType(ctx.pointers)}.`,
      });
    } else {
      const pointers = ctx.pointers as unknown[];
      for (let index = 0; index < pointers.length; index += 1) {
        if (!Object.hasOwn(pointers, index)) {
          issues.push({
            code: "contribution_shape_invalid",
            message: `Agent-context pointer at index ${index} is missing (sparse array).`,
            contributionIndex: index,
          });
          continue;
        }
        if (!isPlainObject(pointers[index])) {
          issues.push({
            code: "contribution_shape_invalid",
            message: `Agent-context pointer at index ${index} must be a non-null object, got ${describeType(pointers[index])}.`,
            contributionIndex: index,
          });
        }
      }
    }
  }

  // 3. Publication and identity fields.
  const identity = identityShapeValid && isPlainObject(pub.identity) ? pub.identity : null;
  if (isBlank(pub.surfaceId)) {
    issues.push({ code: "surface_id_blank", message: "Publication surface ID is blank." });
  }
  if (identity != null && isBlank(identity.surfaceId)) {
    issues.push({ code: "surface_id_blank", message: "Identity surface ID is blank." });
  }
  if (identity != null && isBlank(identity.instanceKey)) {
    issues.push({
      code: "instance_key_blank",
      message: "Surface identity instance key is blank.",
    });
  }
  if (identity != null && pub.surfaceId !== identity.surfaceId) {
    issues.push({
      code: "identity_surface_mismatch",
      message:
        `Publication surface ID ${preview(pub.surfaceId)} does not match identity ` +
        `surface ID ${preview(identity.surfaceId)}.`,
    });
  }
  if (isBlank(pub.label)) {
    issues.push({ code: "publication_label_blank", message: "Publication label is blank." });
  }

  // 4. Canvas field checks.
  if (canvasShapeValid && pub.canvas !== null && isPlainObject(pub.canvas)) {
    const canvas = pub.canvas;
    const workObject = canvas.workObject as Record<string, unknown>;
    if (
      isBlank(canvas.canvasId) ||
      isBlank(workObject.kind) ||
      isBlank(workObject.id)
    ) {
      issues.push({
        code: "canvas_identity_invalid",
        message: "Canvas contribution has a blank canvas ID or work-object kind/ID.",
        contributionId: typeof canvas.canvasId === "string" ? canvas.canvasId : "",
      });
    }
  }

  // 5. Agent context field checks.
  if (agentContextIsObject) {
    const context = pub.agentContext as Record<string, unknown>;
    const problems: string[] = [];
    if (isBlank(context.label)) problems.push("label is blank");
    const stringOrNullFields = [
      ["campaignId", context.campaignId],
      ["documentId", context.documentId],
      ["ambientSummary", context.ambientSummary],
    ] as const;
    for (const [field, value] of stringOrNullFields) {
      if (value !== null && typeof value !== "string") {
        problems.push(`${field} must be a string or null, got ${describeType(value)}`);
      }
    }
    if (
      context.sessionNumber !== null &&
      (typeof context.sessionNumber !== "number" || !Number.isFinite(context.sessionNumber))
    ) {
      problems.push(`sessionNumber must be a finite number or null, got ${describeType(context.sessionNumber)}`);
    }
    if (problems.length > 0) {
      issues.push({
        code: "agent_context_invalid",
        message: `Agent-context contribution is invalid: ${problems.join("; ")}.`,
      });
    }

    const ambientSummary = context.ambientSummary;
    if (
      typeof ambientSummary === "string" &&
      ambientSummary.length > SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.ambientSummaryMaxChars
    ) {
      issues.push({
        code: "agent_context_bounds_exceeded",
        message:
          `Agent-context ambientSummary exceeds the ${SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.ambientSummaryMaxChars}-character bound ` +
          `(length ${ambientSummary.length}).`,
      });
    }

    if (Array.isArray(context.pointers)) {
      const pointers = context.pointers as unknown[];
      if (pointers.length > SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries) {
        issues.push({
          code: "agent_context_bounds_exceeded",
          message:
            `Agent-context pointers exceed the ${SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries}-entry bound ` +
            `(count ${pointers.length}).`,
        });
      }

      for (let index = 0; index < pointers.length; index += 1) {
        if (!Object.hasOwn(pointers, index)) continue;
        const pointer = pointers[index];
        if (!isPlainObject(pointer)) continue;
        const kind = pointer.kind;
        const value = pointer.value;
        if (isBlank(kind) || isBlank(value)) {
          issues.push({
            code: "agent_pointer_invalid",
            message: `Agent-context pointer at index ${index} has a blank kind or value.`,
            contributionIndex: index,
          });
        }
        if (
          typeof kind === "string" &&
          kind.length > SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerKindMaxChars
        ) {
          issues.push({
            code: "agent_context_bounds_exceeded",
            message:
              `Agent-context pointer kind exceeds the ${SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerKindMaxChars}-character bound ` +
              `(length ${kind.length}).`,
            contributionIndex: index,
          });
        }
        if (
          typeof value === "string" &&
          value.length > SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerValueMaxChars
        ) {
          issues.push({
            code: "agent_context_bounds_exceeded",
            message:
              `Agent-context pointer value exceeds the ${SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerValueMaxChars}-character bound ` +
              `(length ${value.length}).`,
            contributionIndex: index,
          });
        }
      }
    }
  }

  // 6. Tool field checks in collection order.
  for (let index = 0; index < rawTools.length; index += 1) {
    if (!toolShapeValid[index]) continue;
    const tool = rawTools[index] as Record<string, unknown>;
    const id = typeof tool.id === "string" ? tool.id : "";
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(tool.id)) {
      issues.push({
        code: "contribution_id_blank",
        message: `Tool contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    if (isBlank(tool.label)) {
      issues.push({
        code: "contribution_label_blank",
        message: `Tool contribution "${id}" has a blank label.`,
        ...owner,
      });
    }
    validatePlacementFields(tool.placement as Record<string, unknown>, owner, issues);
    validateAvailability(tool.availability as SurfaceInteractionAvailability, owner, issues);
    const activation = tool.activation as Record<string, unknown>;
    if (activation.kind !== "projection" && activation.kind !== "command") {
      issues.push({
        code: "tool_activation_invalid",
        message: `Tool contribution "${id}" has a missing or unknown activation discriminant (${preview(activation.kind)}).`,
        ...owner,
      });
      continue;
    }
    if (activation.kind === "command" && typeof activation.invoke !== "function") {
      issues.push({
        code: "tool_activation_invalid",
        message: `Tool contribution "${id}" command activation is missing its invoke callback.`,
        ...owner,
      });
    }
  }

  // 7. Edit field checks in collection order.
  for (let index = 0; index < rawEditCommands.length; index += 1) {
    if (!editShapeValid[index]) continue;
    const command = rawEditCommands[index] as Record<string, unknown>;
    const id = typeof command.id === "string" ? command.id : "";
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(command.id)) {
      issues.push({
        code: "contribution_id_blank",
        message: `Edit command contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    if (isBlank(command.label)) {
      issues.push({
        code: "contribution_label_blank",
        message: `Edit command contribution "${id}" has a blank label.`,
        ...owner,
      });
    }
    validatePlacementFields(command.placement as Record<string, unknown>, owner, issues);
    validateAvailability(command.availability as SurfaceInteractionAvailability, owner, issues);
    const target = command.target as Record<string, unknown>;
    if (isBlank(target.kind) || isBlank(target.id)) {
      issues.push({
        code: "command_target_invalid",
        message: `Edit command contribution "${id}" has a blank target kind or ID.`,
        ...owner,
      });
    }
    if (typeof command.invoke !== "function") {
      issues.push({
        code: "edit_command_invoke_invalid",
        message: `Edit command contribution "${id}" is missing its invoke callback.`,
        ...owner,
      });
    }
  }

  // 8. Projection field checks in collection order.
  for (let index = 0; index < rawProjections.length; index += 1) {
    if (!projectionShapeValid[index]) continue;
    const projection = rawProjections[index] as Record<string, unknown>;
    const id = typeof projection.id === "string" ? projection.id : "";
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(projection.id)) {
      issues.push({
        code: "contribution_id_blank",
        message: `Projection contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    const kind = projection.kind;
    if (typeof kind !== "string" || !PROJECTION_KINDS.has(kind)) {
      issues.push({
        code: "projection_kind_unknown",
        message: `Projection "${id}" has unknown kind ${preview(kind)}.`,
        ...owner,
      });
    }
    const preferredSize = projection.preferredSize;
    if (typeof preferredSize !== "string" || !PROJECTION_SIZES.has(preferredSize)) {
      issues.push({
        code: "projection_size_unknown",
        message: `Projection "${id}" has unknown preferred size ${preview(preferredSize)}.`,
        ...owner,
      });
    }
  }

  // 9. Binding field checks in collection order.
  for (let index = 0; index < rawBindings.length; index += 1) {
    if (!bindingShapeValid[index]) continue;
    const binding = rawBindings[index] as Record<string, unknown>;
    if (isBlank(binding.id)) {
      issues.push({
        code: "contribution_id_blank",
        message: `Projection binding at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
  }

  // 10. Cross-reference checks.
  collectDuplicateIds(collectIds(rawTools), "duplicate_tool_id", "Tool contribution", issues);
  collectDuplicateIds(collectIds(rawEditCommands), "duplicate_edit_command_id", "Edit command contribution", issues);
  collectDuplicateIds(collectIds(rawProjections), "duplicate_projection_id", "Projection contribution", issues);
  collectDuplicateIds(collectIds(rawBindings), "duplicate_projection_binding_id", "Projection binding", issues);

  const declaredProjections = new Map<string, Record<string, unknown>>();
  for (let index = 0; index < rawProjections.length; index += 1) {
    const projection = rawProjections[index];
    if (!isPlainObject(projection)) continue;
    const pid = typeof projection.id === "string" ? projection.id : "";
    if (isBlank(pid) || declaredProjections.has(pid)) continue;
    declaredProjections.set(pid, projection);
  }

  for (let index = 0; index < rawTools.length; index += 1) {
    if (!toolShapeValid[index]) continue;
    const tool = rawTools[index] as Record<string, unknown>;
    const activation = tool.activation as Record<string, unknown>;
    if (activation.kind !== "projection") continue;
    const toolId = typeof tool.id === "string" ? tool.id : "";
    const targetId = activation.projectionId;
    const target =
      typeof targetId === "string" && !isBlank(targetId)
        ? declaredProjections.get(targetId)
        : undefined;
    if (!target) {
      issues.push({
        code: "tool_projection_missing",
        message:
          `Tool contribution "${toolId}" targets projection ${preview(targetId)}, ` +
          "which is not declared.",
        contributionId: toolId,
        contributionIndex: index,
        referencedId: typeof targetId === "string" ? targetId : "",
      });
      continue;
    }
    if (target.kind !== "tool") {
      issues.push({
        code: "tool_projection_kind_mismatch",
        message:
          `Tool contribution "${toolId}" targets projection ${preview(target.id)} of kind ` +
          `${preview(target.kind)}; only kind "tool" may be activated.`,
        contributionId: toolId,
        contributionIndex: index,
        referencedId: typeof target.id === "string" ? target.id : "",
      });
    }
  }

  const declaredBindingIds = new Set<string>();
  for (let index = 0; index < rawBindings.length; index += 1) {
    const binding = rawBindings[index];
    if (!isPlainObject(binding)) continue;
    const bid = typeof binding.id === "string" ? binding.id : "";
    if (!isBlank(bid)) declaredBindingIds.add(bid);
  }

  for (let projectionIndex = 0; projectionIndex < rawProjections.length; projectionIndex += 1) {
    if (!projectionShapeValid[projectionIndex]) continue;
    const projection = rawProjections[projectionIndex] as Record<string, unknown>;
    const projectionId = typeof projection.id === "string" ? projection.id : "";
    const bindingIds = projection.bindingIds as string[];
    const seen = new Set<string>();
    for (let elementIndex = 0; elementIndex < bindingIds.length; elementIndex += 1) {
      if (!Object.hasOwn(bindingIds, elementIndex)) continue;
      const bindingId = bindingIds[elementIndex];
      if (typeof bindingId !== "string") continue;
      if (seen.has(bindingId)) {
        issues.push({
          code: "projection_binding_duplicate_reference",
          message: `Projection "${projectionId}" repeats binding reference "${bindingId}".`,
          contributionId: projectionId,
          contributionIndex: projectionIndex,
          referencedId: bindingId,
        });
        continue;
      }
      seen.add(bindingId);
      if (isBlank(bindingId) || !declaredBindingIds.has(bindingId)) {
        issues.push({
          code: "projection_binding_missing",
          message:
            `Projection "${projectionId}" requires binding "${bindingId}", which is not declared.`,
          contributionId: projectionId,
          contributionIndex: projectionIndex,
          referencedId: bindingId,
        });
      }
    }
  }

  // placement_group_conflict: Tool order, then Edit; first declaration canonical.
  const groupCanonical = new Map<
    string,
    { contributionId: string; groupLabel: unknown; groupOrder: unknown }
  >();
  const scanForGroupConflict = (
    entry: Record<string, unknown>,
    contributionId: string,
  ): void => {
    const placement = entry.placement as Record<string, unknown>;
    if (!hasValidPlacementForGroupConflict(placement)) return;
    const groupId = placement.groupId as string;
    const canonical = groupCanonical.get(groupId);
    if (!canonical) {
      groupCanonical.set(groupId, {
        contributionId,
        groupLabel: placement.groupLabel,
        groupOrder: placement.groupOrder,
      });
      return;
    }
    if (
      canonical.groupLabel !== placement.groupLabel ||
      canonical.groupOrder !== placement.groupOrder
    ) {
      issues.push({
        code: "placement_group_conflict",
        message:
          `Group "${groupId}" was first declared by contribution "${canonical.contributionId}" ` +
          `(label ${JSON.stringify(canonical.groupLabel)}, order ${String(canonical.groupOrder)}); ` +
          `contribution "${contributionId}" disagrees ` +
          `(label ${JSON.stringify(placement.groupLabel)}, order ${String(placement.groupOrder)}).`,
        contributionId,
        referencedId: groupId,
      });
    }
  };

  for (let index = 0; index < rawTools.length; index += 1) {
    if (!toolShapeValid[index]) continue;
    const entry = rawTools[index] as Record<string, unknown>;
    scanForGroupConflict(entry, typeof entry.id === "string" ? entry.id : "");
  }
  for (let index = 0; index < rawEditCommands.length; index += 1) {
    if (!editShapeValid[index]) continue;
    const entry = rawEditCommands[index] as Record<string, unknown>;
    scanForGroupConflict(entry, typeof entry.id === "string" ? entry.id : "");
  }

  if (issues.length === 0) {
    return {
      valid: true,
      publication: publication as unknown as SurfaceInteractionPublication,
    };
  }
  return { valid: false, publication, issues };
}
