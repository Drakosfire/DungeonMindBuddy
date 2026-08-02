/**
 * Whole-publication structural validation (SIH-01).
 *
 * Authority: handoff §6.3–§6.10. Pure, deterministic, non-throwing for any
 * malformed input. Never invokes callbacks, never inspects binding values,
 * never clones the input, never coerces malformed collections, and never
 * converts untrusted values (no String()/toString/Symbol.toPrimitive paths —
 * diagnostics name malformed types instead). Nullability means exactly null,
 * required arrays must be dense (indexed iteration with own-property checks),
 * discriminant set checks require primitive strings via typeof, and every
 * record position holds the data-record boundary: own data-property
 * descriptors only (accessors are malformed, never invoked), standard
 * prototypes only (inherited fields never satisfy or violate the contract),
 * and guarded inspection (throwing proxy traps become shape issues, never
 * escaped exceptions). Each untrusted field is read exactly once; field and
 * cross-reference checks consume those same snapshotted values. Any material
 * contradiction invalidates the whole publication; no partially accepted
 * contribution set is ever returned.
 */

import type {
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

const PUBLICATION_KEYS = [
  "surfaceId",
  "label",
  "identity",
  "canvas",
  "agentContext",
  "tools",
  "editCommands",
  "projections",
  "projectionBindings",
] as const;
const TOOL_KEYS = ["id", "label", "eyebrow", "placement", "availability", "activation"] as const;
const EDIT_KEYS = ["id", "label", "eyebrow", "placement", "availability", "target", "invoke"] as const;
const PROJECTION_KEYS = ["id", "kind", "preferredSize", "bindingIds"] as const;
const BINDING_KEYS = ["id", "value"] as const;
const PLACEMENT_KEYS = ["groupId", "groupLabel", "groupOrder", "itemOrder"] as const;
const AVAILABILITY_KEYS = ["status", "disabledReason"] as const;
const ACTIVATION_KEYS = ["kind", "invoke", "projectionId"] as const;
const TARGET_KEYS = ["kind", "id"] as const;
const IDENTITY_KEYS = ["surfaceId", "instanceKey"] as const;
const CANVAS_KEYS = ["canvasId", "workObject"] as const;
const WORK_OBJECT_KEYS = ["kind", "id"] as const;
const AGENT_CONTEXT_KEYS = [
  "label",
  "campaignId",
  "documentId",
  "sessionNumber",
  "ambientSummary",
  "pointers",
] as const;
const POINTER_KEYS = ["kind", "value"] as const;

// ---------------------------------------------------------------------------
// Safe untrusted-input access layer.
//
// Every read of untrusted input goes through these helpers. They never invoke
// user code (accessor properties are detected from their descriptor, not
// read), they reject prototype-backed records (inherited fields would still
// resolve through a type-narrowed value), and they guard every operation that
// can throw on proxies (descriptor reads, getPrototypeOf, Array.isArray,
// length reads), converting trap failures into structural malformation.
// ---------------------------------------------------------------------------

/** Result of inspecting one field of an untrusted record without invoking user code. */
type FieldRead =
  | { readonly kind: "data"; readonly value: unknown }
  | { readonly kind: "absent" }
  | { readonly kind: "nonData" }; // accessor property, or inspection itself threw (proxy trap)

function readOwnDataField(record: object, key: string): FieldRead {
  let descriptor: PropertyDescriptor | undefined;
  try {
    descriptor = Object.getOwnPropertyDescriptor(record, key);
  } catch {
    return { kind: "nonData" };
  }
  if (descriptor === undefined) return { kind: "absent" };
  if (!("value" in descriptor)) return { kind: "nonData" };
  return { kind: "data", value: descriptor.value };
}

/** Guarded Array.isArray — a revoked proxy throws on any inspection. */
function isArrayValue(value: unknown): boolean {
  try {
    return Array.isArray(value);
  } catch {
    return false;
  }
}

/**
 * Data-record prototype boundary: only Object.prototype or null. Inherited
 * properties must never satisfy or violate contract fields — a prototype-
 * inherited disabledReason would still resolve through the narrowed value.
 * Guarded: a throwing getPrototypeOf trap fails the boundary.
 */
function hasDataRecordPrototype(value: object): boolean {
  let prototype: unknown;
  try {
    prototype = Object.getPrototypeOf(value);
  } catch {
    return false;
  }
  return prototype === Object.prototype || prototype === null;
}

function isDataRecord(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !isArrayValue(value) &&
    hasDataRecordPrototype(value)
  );
}

/** A record position's own data fields, each read exactly once. */
type RecordSnapshot = {
  readonly isRecord: boolean;
  readonly fields: ReadonlyMap<string, unknown>;
  readonly nonDataFields: ReadonlySet<string>;
};

const EMPTY_FIELDS: ReadonlyMap<string, unknown> = new Map();

const EMPTY_RECORD_SNAPSHOT: RecordSnapshot = {
  isRecord: false,
  fields: EMPTY_FIELDS,
  nonDataFields: new Set(),
};

function snapshotRecord(value: unknown, keys: readonly string[]): RecordSnapshot {
  if (!isDataRecord(value)) return EMPTY_RECORD_SNAPSHOT;
  const fields = new Map<string, unknown>();
  const nonDataFields = new Set<string>();
  for (const key of keys) {
    const read = readOwnDataField(value, key);
    if (read.kind === "data") fields.set(key, read.value);
    else if (read.kind === "nonData") nonDataFields.add(key);
  }
  return { isRecord: true, fields, nonDataFields };
}

/** An array position's own data elements, each read exactly once. */
type ArraySnapshot = {
  readonly isArray: boolean;
  readonly lengthReadable: boolean;
  readonly length: number;
  readonly elements: ReadonlyMap<number, unknown>;
  readonly nonDataIndices: ReadonlySet<number>;
};

function snapshotArray(value: unknown): ArraySnapshot {
  const notArray: ArraySnapshot = {
    isArray: false,
    lengthReadable: false,
    length: 0,
    elements: new Map(),
    nonDataIndices: new Set(),
  };
  if (!isArrayValue(value)) return notArray;
  let length: unknown;
  try {
    length = (value as readonly unknown[]).length;
  } catch {
    return { ...notArray, isArray: true };
  }
  if (typeof length !== "number" || !Number.isInteger(length) || length < 0) {
    return { ...notArray, isArray: true };
  }
  const elements = new Map<number, unknown>();
  const nonDataIndices = new Set<number>();
  for (let index = 0; index < length; index += 1) {
    const read = readOwnDataField(value as object, String(index));
    if (read.kind === "data") elements.set(index, read.value);
    else if (read.kind === "nonData") nonDataIndices.add(index);
  }
  return { isArray: true, lengthReadable: true, length, elements, nonDataIndices };
}

function isBlank(value: unknown): boolean {
  return typeof value !== "string" || value.trim().length === 0;
}

/** Type name for diagnostics — never invokes conversions on untrusted values. */
function describeType(value: unknown): string {
  if (value === null) return "null";
  if (isArrayValue(value)) return "array";
  return typeof value;
}

/** Safe diagnostic rendering: strings are quoted verbatim; anything else is named by type. */
function preview(value: unknown): string {
  return typeof value === "string" ? JSON.stringify(value) : describeType(value);
}

function describeNonDataFields(nonDataFields: ReadonlySet<string>): string {
  return [...nonDataFields].join(", ");
}

function validateAvailability(
  availability: RecordSnapshot,
  owner: { contributionId: string; contributionIndex: number },
  issues: SurfaceInteractionValidationIssue[],
): void {
  const status = availability.fields.get("status");
  if (status === "disabled" && isBlank(availability.fields.get("disabledReason"))) {
    issues.push({
      code: "disabled_reason_missing",
      message: `Contribution "${owner.contributionId}" is disabled without a human-readable reason.`,
      ...owner,
    });
  }
  // The enabled union member is `disabledReason?: never` — supplying the
  // property at all (even null or undefined) violates it. Presence here means
  // an own data property: accessor fields were rejected as non-data shape and
  // inherited fields failed the record's prototype boundary.
  if (status === "enabled" && availability.fields.has("disabledReason")) {
    issues.push({
      code: "enabled_has_disabled_reason",
      message: `Contribution "${owner.contributionId}" is enabled but supplies a disabled reason.`,
      ...owner,
    });
  }
}

function validatePlacementFields(
  placement: RecordSnapshot,
  owner: { contributionId: string; contributionIndex: number },
  issues: SurfaceInteractionValidationIssue[],
): void {
  const groupId = placement.fields.get("groupId");
  const groupLabel = placement.fields.get("groupLabel");
  const groupOrder = placement.fields.get("groupOrder");
  const itemOrder = placement.fields.get("itemOrder");
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

function hasValidPlacementForGroupConflict(placement: RecordSnapshot): boolean {
  const groupId = placement.fields.get("groupId");
  if (groupId === null || isBlank(groupId)) return false;
  const groupLabel = placement.fields.get("groupLabel");
  const groupOrder = placement.fields.get("groupOrder");
  const itemOrder = placement.fields.get("itemOrder");
  if ((groupId === null) !== (groupLabel === null)) return false;
  if (groupLabel !== null && isBlank(groupLabel)) return false;
  if (!Number.isInteger(groupOrder) || !Number.isInteger(itemOrder)) return false;
  return true;
}

/** Primitive-string IDs only, from the already-snapshotted entry fields. */
function collectIds(fieldMaps: readonly ReadonlyMap<string, unknown>[]): string[] {
  return fieldMaps.map((fields) => {
    const id = fields.get("id");
    return typeof id === "string" ? id : "";
  });
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

type ToolSnapshot =
  | { readonly shapeValid: false; readonly fields: ReadonlyMap<string, unknown> }
  | {
      readonly shapeValid: true;
      readonly fields: ReadonlyMap<string, unknown>;
      readonly placement: RecordSnapshot;
      readonly availability: RecordSnapshot;
      readonly activation: RecordSnapshot;
    };

type EditSnapshot =
  | { readonly shapeValid: false; readonly fields: ReadonlyMap<string, unknown> }
  | {
      readonly shapeValid: true;
      readonly fields: ReadonlyMap<string, unknown>;
      readonly placement: RecordSnapshot;
      readonly availability: RecordSnapshot;
      readonly target: RecordSnapshot;
    };

type ProjectionSnapshot =
  | { readonly shapeValid: false; readonly fields: ReadonlyMap<string, unknown> }
  | {
      readonly shapeValid: true;
      readonly fields: ReadonlyMap<string, unknown>;
      readonly bindingIds: ArraySnapshot;
    };

type BindingSnapshot = {
  readonly shapeValid: boolean;
  readonly fields: ReadonlyMap<string, unknown>;
};

function stringField(fields: ReadonlyMap<string, unknown>, key: string): string {
  const value = fields.get(key);
  return typeof value === "string" ? value : "";
}

export function validateSurfaceInteractionPublication(
  publication: unknown,
): SurfaceInteractionValidationResult {
  const issues: SurfaceInteractionValidationIssue[] = [];

  // 1. Publication shape — the data-record boundary applies first.
  const pubSnap = snapshotRecord(publication, PUBLICATION_KEYS);
  if (!pubSnap.isRecord) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication must be a non-null object, got ${describeType(publication)}.`,
    });
    return { valid: false, publication, issues };
  }
  const pubNonData = pubSnap.nonDataFields;
  for (const field of pubNonData) {
    issues.push({
      code: "publication_shape_invalid",
      message:
        `Publication field "${field}" is an accessor property or unreadable; ` +
        "only plain data properties are valid.",
    });
  }

  const collectionFields = ["tools", "editCommands", "projections", "projectionBindings"] as const;
  const collectionSnapshots: Record<(typeof collectionFields)[number], ArraySnapshot> = {
    tools: snapshotArray(pubSnap.fields.get("tools")),
    editCommands: snapshotArray(pubSnap.fields.get("editCommands")),
    projections: snapshotArray(pubSnap.fields.get("projections")),
    projectionBindings: snapshotArray(pubSnap.fields.get("projectionBindings")),
  };
  for (const field of collectionFields) {
    if (pubNonData.has(field)) continue;
    const snapshot = collectionSnapshots[field];
    if (!snapshot.isArray) {
      issues.push({
        code: "publication_shape_invalid",
        message: `Publication "${field}" must be an array, got ${describeType(pubSnap.fields.get(field))}.`,
      });
    } else if (!snapshot.lengthReadable) {
      issues.push({
        code: "publication_shape_invalid",
        message: `Publication "${field}" array length is unreadable; only plain data arrays are valid.`,
      });
    }
  }
  const canvasValue = pubSnap.fields.get("canvas");
  if (!pubNonData.has("canvas") && canvasValue !== null && !isDataRecord(canvasValue)) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication canvas must be exactly null or an object, got ${describeType(canvasValue)}.`,
    });
  }
  const agentContextValue = pubSnap.fields.get("agentContext");
  if (!pubNonData.has("agentContext") && agentContextValue !== null && !isDataRecord(agentContextValue)) {
    issues.push({
      code: "publication_shape_invalid",
      message: `Publication agentContext must be exactly null or an object, got ${describeType(agentContextValue)}.`,
    });
  }

  // 2. Per-collection entry shape (Tool, Edit, Projection, binding order),
  //    indexed so sparse arrays and accessor elements cannot skip entries.
  const toolsArr = collectionSnapshots.tools;
  const toolSnaps: ToolSnapshot[] = [];
  for (let index = 0; index < toolsArr.length; index += 1) {
    if (toolsArr.nonDataIndices.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Tool contribution at index ${index} is an accessor property or unreadable; only plain data elements are valid.`,
        contributionIndex: index,
      });
      toolSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (!toolsArr.elements.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Tool contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      toolSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    const snap = snapshotRecord(toolsArr.elements.get(index), TOOL_KEYS);
    if (!snap.isRecord) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Tool contribution at index ${index} must be a non-null object, got ${describeType(toolsArr.elements.get(index))}.`,
        contributionIndex: index,
      });
      toolSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (snap.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Tool contribution at index ${index} has non-data fields (accessor or unreadable): ` +
          `${describeNonDataFields(snap.nonDataFields)}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      toolSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    const placement = snapshotRecord(snap.fields.get("placement"), PLACEMENT_KEYS);
    const availability = snapshotRecord(snap.fields.get("availability"), AVAILABILITY_KEYS);
    const activation = snapshotRecord(snap.fields.get("activation"), ACTIVATION_KEYS);
    const nestedProblems: string[] = [];
    if (!placement.isRecord) {
      nestedProblems.push("placement");
    } else if (placement.nonDataFields.size > 0) {
      nestedProblems.push(`placement has non-data fields (accessor or unreadable): ${describeNonDataFields(placement.nonDataFields)}`);
    }
    if (!availability.isRecord) {
      nestedProblems.push("availability");
    } else if (availability.nonDataFields.size > 0) {
      nestedProblems.push(`availability has non-data fields (accessor or unreadable): ${describeNonDataFields(availability.nonDataFields)}`);
    } else {
      const status = availability.fields.get("status");
      if (status !== "enabled" && status !== "disabled") {
        nestedProblems.push(`availability status discriminant is neither "enabled" nor "disabled" (got ${preview(status)})`);
      }
    }
    if (!activation.isRecord) {
      nestedProblems.push("activation");
    } else if (activation.nonDataFields.size > 0) {
      nestedProblems.push(`activation has non-data fields (accessor or unreadable): ${describeNonDataFields(activation.nonDataFields)}`);
    }
    const eyebrow = snap.fields.get("eyebrow");
    if (eyebrow !== undefined && typeof eyebrow !== "string") {
      nestedProblems.push(`supplied eyebrow is not a string (got ${describeType(eyebrow)})`);
    }
    if (nestedProblems.length > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Tool contribution at index ${index} has malformed structure: ` +
          `${nestedProblems.join("; ")}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      toolSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    toolSnaps.push({ shapeValid: true, fields: snap.fields, placement, availability, activation });
  }

  const editCommandsArr = collectionSnapshots.editCommands;
  const editSnaps: EditSnapshot[] = [];
  for (let index = 0; index < editCommandsArr.length; index += 1) {
    if (editCommandsArr.nonDataIndices.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Edit command contribution at index ${index} is an accessor property or unreadable; only plain data elements are valid.`,
        contributionIndex: index,
      });
      editSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (!editCommandsArr.elements.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Edit command contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      editSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    const snap = snapshotRecord(editCommandsArr.elements.get(index), EDIT_KEYS);
    if (!snap.isRecord) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Edit command contribution at index ${index} must be a non-null object, got ${describeType(editCommandsArr.elements.get(index))}.`,
        contributionIndex: index,
      });
      editSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (snap.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Edit command contribution at index ${index} has non-data fields (accessor or unreadable): ` +
          `${describeNonDataFields(snap.nonDataFields)}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      editSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    const placement = snapshotRecord(snap.fields.get("placement"), PLACEMENT_KEYS);
    const availability = snapshotRecord(snap.fields.get("availability"), AVAILABILITY_KEYS);
    const target = snapshotRecord(snap.fields.get("target"), TARGET_KEYS);
    const nestedProblems: string[] = [];
    if (!placement.isRecord) {
      nestedProblems.push("placement");
    } else if (placement.nonDataFields.size > 0) {
      nestedProblems.push(`placement has non-data fields (accessor or unreadable): ${describeNonDataFields(placement.nonDataFields)}`);
    }
    if (!availability.isRecord) {
      nestedProblems.push("availability");
    } else if (availability.nonDataFields.size > 0) {
      nestedProblems.push(`availability has non-data fields (accessor or unreadable): ${describeNonDataFields(availability.nonDataFields)}`);
    } else {
      const status = availability.fields.get("status");
      if (status !== "enabled" && status !== "disabled") {
        nestedProblems.push(`availability status discriminant is neither "enabled" nor "disabled" (got ${preview(status)})`);
      }
    }
    if (!target.isRecord) {
      nestedProblems.push("target");
    } else if (target.nonDataFields.size > 0) {
      nestedProblems.push(`target has non-data fields (accessor or unreadable): ${describeNonDataFields(target.nonDataFields)}`);
    }
    const eyebrow = snap.fields.get("eyebrow");
    if (eyebrow !== undefined && typeof eyebrow !== "string") {
      nestedProblems.push(`supplied eyebrow is not a string (got ${describeType(eyebrow)})`);
    }
    if (nestedProblems.length > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Edit command contribution at index ${index} has malformed structure: ` +
          `${nestedProblems.join("; ")}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      editSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    editSnaps.push({ shapeValid: true, fields: snap.fields, placement, availability, target });
  }

  const projectionsArr = collectionSnapshots.projections;
  const projectionSnaps: ProjectionSnapshot[] = [];
  for (let index = 0; index < projectionsArr.length; index += 1) {
    if (projectionsArr.nonDataIndices.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} is an accessor property or unreadable; only plain data elements are valid.`,
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (!projectionsArr.elements.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    const snap = snapshotRecord(projectionsArr.elements.get(index), PROJECTION_KEYS);
    if (!snap.isRecord) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} must be a non-null object, got ${describeType(projectionsArr.elements.get(index))}.`,
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (snap.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Projection contribution at index ${index} has non-data fields (accessor or unreadable): ` +
          `${describeNonDataFields(snap.nonDataFields)}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    const projectionId = stringField(snap.fields, "id");
    const bindingIds = snapshotArray(snap.fields.get("bindingIds"));
    if (!bindingIds.isArray) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} bindingIds must be an array, got ${describeType(snap.fields.get("bindingIds"))}.`,
        contributionId: projectionId,
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    if (!bindingIds.lengthReadable) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection contribution at index ${index} bindingIds array length is unreadable; only plain data arrays are valid.`,
        contributionId: projectionId,
        contributionIndex: index,
      });
      projectionSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    let bindingIdsValid = true;
    for (let elementIndex = 0; elementIndex < bindingIds.length; elementIndex += 1) {
      if (bindingIds.nonDataIndices.has(elementIndex)) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Projection "${projectionId}" bindingIds index ${elementIndex} is an accessor property or unreadable; only plain data elements are valid.`,
          contributionId: projectionId,
          contributionIndex: index,
        });
        bindingIdsValid = false;
        continue;
      }
      if (!bindingIds.elements.has(elementIndex)) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Projection "${projectionId}" bindingIds index ${elementIndex} is missing (sparse array).`,
          contributionId: projectionId,
          contributionIndex: index,
        });
        bindingIdsValid = false;
        continue;
      }
      const element = bindingIds.elements.get(elementIndex);
      if (typeof element !== "string") {
        issues.push({
          code: "contribution_shape_invalid",
          message:
            `Projection "${projectionId}" bindingIds index ${elementIndex} must be a string, ` +
            `got ${describeType(element)}.`,
          contributionId: projectionId,
          contributionIndex: index,
        });
        bindingIdsValid = false;
      }
    }
    if (!bindingIdsValid) {
      projectionSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    projectionSnaps.push({ shapeValid: true, fields: snap.fields, bindingIds });
  }

  const bindingsArr = collectionSnapshots.projectionBindings;
  const bindingSnaps: BindingSnapshot[] = [];
  for (let index = 0; index < bindingsArr.length; index += 1) {
    if (bindingsArr.nonDataIndices.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} is an accessor property or unreadable; only plain data elements are valid.`,
        contributionIndex: index,
      });
      bindingSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (!bindingsArr.elements.has(index)) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} is missing (sparse array).`,
        contributionIndex: index,
      });
      bindingSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    const snap = snapshotRecord(bindingsArr.elements.get(index), BINDING_KEYS);
    if (!snap.isRecord) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} must be a non-null object, got ${describeType(bindingsArr.elements.get(index))}.`,
        contributionIndex: index,
      });
      bindingSnaps.push({ shapeValid: false, fields: EMPTY_FIELDS });
      continue;
    }
    if (snap.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message:
          `Projection binding at index ${index} has non-data fields (accessor or unreadable): ` +
          `${describeNonDataFields(snap.nonDataFields)}.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      bindingSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    // Presence only — the value is opaque and is never read; snapshotting
    // inspected the property descriptor without invoking getters.
    if (!snap.fields.has("value")) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Projection binding at index ${index} is missing its required value field.`,
        contributionId: stringField(snap.fields, "id"),
        contributionIndex: index,
      });
      bindingSnaps.push({ shapeValid: false, fields: snap.fields });
      continue;
    }
    bindingSnaps.push({ shapeValid: true, fields: snap.fields });
  }

  let identitySnap: RecordSnapshot | null = null;
  if (!pubNonData.has("identity")) {
    const candidate = snapshotRecord(pubSnap.fields.get("identity"), IDENTITY_KEYS);
    if (!candidate.isRecord) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Publication identity must be a non-null object, got ${describeType(pubSnap.fields.get("identity"))}.`,
      });
    } else if (candidate.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Publication identity has non-data fields (accessor or unreadable): ${describeNonDataFields(candidate.nonDataFields)}.`,
      });
    } else {
      identitySnap = candidate;
    }
  }

  let canvasSnap: RecordSnapshot | null = null;
  let workObjectSnap: RecordSnapshot | null = null;
  if (canvasValue !== null && isDataRecord(canvasValue)) {
    const candidate = snapshotRecord(canvasValue, CANVAS_KEYS);
    if (candidate.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Canvas contribution has non-data fields (accessor or unreadable): ${describeNonDataFields(candidate.nonDataFields)}.`,
      });
    } else {
      canvasSnap = candidate;
      const workObject = snapshotRecord(candidate.fields.get("workObject"), WORK_OBJECT_KEYS);
      const canvasId = stringField(candidate.fields, "canvasId");
      if (!workObject.isRecord) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Canvas workObject must be a non-null object, got ${describeType(candidate.fields.get("workObject"))}.`,
          contributionId: canvasId,
        });
      } else if (workObject.nonDataFields.size > 0) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Canvas workObject has non-data fields (accessor or unreadable): ${describeNonDataFields(workObject.nonDataFields)}.`,
          contributionId: canvasId,
        });
      } else {
        workObjectSnap = workObject;
      }
    }
  }

  let agentCtxSnap: RecordSnapshot | null = null;
  let pointersArr: ArraySnapshot | null = null;
  const pointerSnaps: Array<RecordSnapshot | null> = [];
  if (agentContextValue !== null && isDataRecord(agentContextValue)) {
    agentCtxSnap = snapshotRecord(agentContextValue, AGENT_CONTEXT_KEYS);
    if (agentCtxSnap.nonDataFields.size > 0) {
      issues.push({
        code: "contribution_shape_invalid",
        message: `Agent-context contribution has non-data fields (accessor or unreadable): ${describeNonDataFields(agentCtxSnap.nonDataFields)}.`,
      });
    }
    if (!agentCtxSnap.nonDataFields.has("pointers")) {
      const candidate = snapshotArray(agentCtxSnap.fields.get("pointers"));
      if (!candidate.isArray) {
        issues.push({
          code: "contribution_shape_invalid",
          message: `Agent-context pointers must be an array, got ${describeType(agentCtxSnap.fields.get("pointers"))}.`,
        });
      } else if (!candidate.lengthReadable) {
        issues.push({
          code: "contribution_shape_invalid",
          message: "Agent-context pointers array length is unreadable; only plain data arrays are valid.",
        });
      } else {
        pointersArr = candidate;
        for (let index = 0; index < candidate.length; index += 1) {
          if (candidate.nonDataIndices.has(index)) {
            issues.push({
              code: "contribution_shape_invalid",
              message: `Agent-context pointer at index ${index} is an accessor property or unreadable; only plain data elements are valid.`,
              contributionIndex: index,
            });
            pointerSnaps.push(null);
            continue;
          }
          if (!candidate.elements.has(index)) {
            issues.push({
              code: "contribution_shape_invalid",
              message: `Agent-context pointer at index ${index} is missing (sparse array).`,
              contributionIndex: index,
            });
            pointerSnaps.push(null);
            continue;
          }
          const pointerSnap = snapshotRecord(candidate.elements.get(index), POINTER_KEYS);
          if (!pointerSnap.isRecord) {
            issues.push({
              code: "contribution_shape_invalid",
              message: `Agent-context pointer at index ${index} must be a non-null object, got ${describeType(candidate.elements.get(index))}.`,
              contributionIndex: index,
            });
            pointerSnaps.push(null);
            continue;
          }
          if (pointerSnap.nonDataFields.size > 0) {
            issues.push({
              code: "contribution_shape_invalid",
              message: `Agent-context pointer at index ${index} has non-data fields (accessor or unreadable): ${describeNonDataFields(pointerSnap.nonDataFields)}.`,
              contributionIndex: index,
            });
            pointerSnaps.push(null);
            continue;
          }
          pointerSnaps.push(pointerSnap);
        }
      }
    }
  }

  // 3. Publication and identity fields.
  const pubSurfaceId = pubSnap.fields.get("surfaceId");
  if (!pubNonData.has("surfaceId") && isBlank(pubSurfaceId)) {
    issues.push({ code: "surface_id_blank", message: "Publication surface ID is blank." });
  }
  if (identitySnap !== null && isBlank(identitySnap.fields.get("surfaceId"))) {
    issues.push({ code: "surface_id_blank", message: "Identity surface ID is blank." });
  }
  if (identitySnap !== null && isBlank(identitySnap.fields.get("instanceKey"))) {
    issues.push({
      code: "instance_key_blank",
      message: "Surface identity instance key is blank.",
    });
  }
  if (
    identitySnap !== null &&
    !pubNonData.has("surfaceId") &&
    pubSurfaceId !== identitySnap.fields.get("surfaceId")
  ) {
    issues.push({
      code: "identity_surface_mismatch",
      message:
        `Publication surface ID ${preview(pubSurfaceId)} does not match identity ` +
        `surface ID ${preview(identitySnap.fields.get("surfaceId"))}.`,
    });
  }
  if (!pubNonData.has("label") && isBlank(pubSnap.fields.get("label"))) {
    issues.push({ code: "publication_label_blank", message: "Publication label is blank." });
  }

  // 4. Canvas field checks.
  if (canvasSnap !== null && workObjectSnap !== null) {
    const canvasId = canvasSnap.fields.get("canvasId");
    if (
      isBlank(canvasId) ||
      isBlank(workObjectSnap.fields.get("kind")) ||
      isBlank(workObjectSnap.fields.get("id"))
    ) {
      issues.push({
        code: "canvas_identity_invalid",
        message: "Canvas contribution has a blank canvas ID or work-object kind/ID.",
        contributionId: typeof canvasId === "string" ? canvasId : "",
      });
    }
  }

  // 5. Agent context field checks.
  if (agentCtxSnap !== null) {
    const fields = agentCtxSnap.fields;
    const problems: string[] = [];
    if (isBlank(fields.get("label"))) problems.push("label is blank");
    const stringOrNullFields = [
      ["campaignId", fields.get("campaignId")],
      ["documentId", fields.get("documentId")],
      ["ambientSummary", fields.get("ambientSummary")],
    ] as const;
    for (const [field, value] of stringOrNullFields) {
      if (value !== null && typeof value !== "string") {
        problems.push(`${field} must be a string or null, got ${describeType(value)}`);
      }
    }
    const sessionNumber = fields.get("sessionNumber");
    if (
      sessionNumber !== null &&
      (typeof sessionNumber !== "number" || !Number.isFinite(sessionNumber))
    ) {
      problems.push(`sessionNumber must be a finite number or null, got ${describeType(sessionNumber)}`);
    }
    if (problems.length > 0) {
      issues.push({
        code: "agent_context_invalid",
        message: `Agent-context contribution is invalid: ${problems.join("; ")}.`,
      });
    }

    const ambientSummary = fields.get("ambientSummary");
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

    if (pointersArr !== null) {
      if (pointersArr.length > SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries) {
        issues.push({
          code: "agent_context_bounds_exceeded",
          message:
            `Agent-context pointers exceed the ${SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries}-entry bound ` +
            `(count ${pointersArr.length}).`,
        });
      }

      for (let index = 0; index < pointerSnaps.length; index += 1) {
        const pointerSnap = pointerSnaps[index];
        if (pointerSnap === null || pointerSnap === undefined) continue;
        const kind = pointerSnap.fields.get("kind");
        const value = pointerSnap.fields.get("value");
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
  for (let index = 0; index < toolSnaps.length; index += 1) {
    const snap = toolSnaps[index];
    if (!snap.shapeValid) continue;
    const id = stringField(snap.fields, "id");
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(snap.fields.get("id"))) {
      issues.push({
        code: "contribution_id_blank",
        message: `Tool contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    if (isBlank(snap.fields.get("label"))) {
      issues.push({
        code: "contribution_label_blank",
        message: `Tool contribution "${id}" has a blank label.`,
        ...owner,
      });
    }
    validatePlacementFields(snap.placement, owner, issues);
    validateAvailability(snap.availability, owner, issues);
    const activationKind = snap.activation.fields.get("kind");
    if (activationKind !== "projection" && activationKind !== "command") {
      issues.push({
        code: "tool_activation_invalid",
        message: `Tool contribution "${id}" has a missing or unknown activation discriminant (${preview(activationKind)}).`,
        ...owner,
      });
      continue;
    }
    if (activationKind === "command" && typeof snap.activation.fields.get("invoke") !== "function") {
      issues.push({
        code: "tool_activation_invalid",
        message: `Tool contribution "${id}" command activation is missing its invoke callback.`,
        ...owner,
      });
    }
  }

  // 7. Edit field checks in collection order.
  for (let index = 0; index < editSnaps.length; index += 1) {
    const snap = editSnaps[index];
    if (!snap.shapeValid) continue;
    const id = stringField(snap.fields, "id");
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(snap.fields.get("id"))) {
      issues.push({
        code: "contribution_id_blank",
        message: `Edit command contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    if (isBlank(snap.fields.get("label"))) {
      issues.push({
        code: "contribution_label_blank",
        message: `Edit command contribution "${id}" has a blank label.`,
        ...owner,
      });
    }
    validatePlacementFields(snap.placement, owner, issues);
    validateAvailability(snap.availability, owner, issues);
    if (isBlank(snap.target.fields.get("kind")) || isBlank(snap.target.fields.get("id"))) {
      issues.push({
        code: "command_target_invalid",
        message: `Edit command contribution "${id}" has a blank target kind or ID.`,
        ...owner,
      });
    }
    if (typeof snap.fields.get("invoke") !== "function") {
      issues.push({
        code: "edit_command_invoke_invalid",
        message: `Edit command contribution "${id}" is missing its invoke callback.`,
        ...owner,
      });
    }
  }

  // 8. Projection field checks in collection order.
  for (let index = 0; index < projectionSnaps.length; index += 1) {
    const snap = projectionSnaps[index];
    if (!snap.shapeValid) continue;
    const id = stringField(snap.fields, "id");
    const owner = { contributionId: id, contributionIndex: index };
    if (isBlank(snap.fields.get("id"))) {
      issues.push({
        code: "contribution_id_blank",
        message: `Projection contribution at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
    const kind = snap.fields.get("kind");
    if (typeof kind !== "string" || !PROJECTION_KINDS.has(kind)) {
      issues.push({
        code: "projection_kind_unknown",
        message: `Projection "${id}" has unknown kind ${preview(kind)}.`,
        ...owner,
      });
    }
    const preferredSize = snap.fields.get("preferredSize");
    if (typeof preferredSize !== "string" || !PROJECTION_SIZES.has(preferredSize)) {
      issues.push({
        code: "projection_size_unknown",
        message: `Projection "${id}" has unknown preferred size ${preview(preferredSize)}.`,
        ...owner,
      });
    }
  }

  // 9. Binding field checks in collection order.
  for (let index = 0; index < bindingSnaps.length; index += 1) {
    const snap = bindingSnaps[index];
    if (!snap.shapeValid) continue;
    if (isBlank(snap.fields.get("id"))) {
      issues.push({
        code: "contribution_id_blank",
        message: `Projection binding at index ${index} has a blank ID.`,
        contributionId: "",
        contributionIndex: index,
      });
    }
  }

  // 10. Cross-reference checks over the snapshotted values.
  collectDuplicateIds(collectIds(toolSnaps.map((snap) => snap.fields)), "duplicate_tool_id", "Tool contribution", issues);
  collectDuplicateIds(collectIds(editSnaps.map((snap) => snap.fields)), "duplicate_edit_command_id", "Edit command contribution", issues);
  collectDuplicateIds(collectIds(projectionSnaps.map((snap) => snap.fields)), "duplicate_projection_id", "Projection contribution", issues);
  collectDuplicateIds(collectIds(bindingSnaps.map((snap) => snap.fields)), "duplicate_projection_binding_id", "Projection binding", issues);

  const declaredProjections = new Map<string, ReadonlyMap<string, unknown>>();
  for (const snap of projectionSnaps) {
    const pid = stringField(snap.fields, "id");
    if (isBlank(pid) || declaredProjections.has(pid)) continue;
    declaredProjections.set(pid, snap.fields);
  }

  for (let index = 0; index < toolSnaps.length; index += 1) {
    const snap = toolSnaps[index];
    if (!snap.shapeValid) continue;
    if (snap.activation.fields.get("kind") !== "projection") continue;
    const toolId = stringField(snap.fields, "id");
    const targetId = snap.activation.fields.get("projectionId");
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
    if (target.get("kind") !== "tool") {
      issues.push({
        code: "tool_projection_kind_mismatch",
        message:
          `Tool contribution "${toolId}" targets projection ${preview(target.get("id"))} of kind ` +
          `${preview(target.get("kind"))}; only kind "tool" may be activated.`,
        contributionId: toolId,
        contributionIndex: index,
        referencedId: stringField(target, "id"),
      });
    }
  }

  const declaredBindingIds = new Set<string>();
  for (const snap of bindingSnaps) {
    const bid = stringField(snap.fields, "id");
    if (!isBlank(bid)) declaredBindingIds.add(bid);
  }

  for (let projectionIndex = 0; projectionIndex < projectionSnaps.length; projectionIndex += 1) {
    const snap = projectionSnaps[projectionIndex];
    if (!snap.shapeValid) continue;
    const projectionId = stringField(snap.fields, "id");
    const bindingIds = snap.bindingIds;
    const seen = new Set<string>();
    for (let elementIndex = 0; elementIndex < bindingIds.length; elementIndex += 1) {
      if (!bindingIds.elements.has(elementIndex)) continue;
      const bindingId = bindingIds.elements.get(elementIndex);
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
    placement: RecordSnapshot,
    contributionId: string,
  ): void => {
    if (!hasValidPlacementForGroupConflict(placement)) return;
    const groupId = placement.fields.get("groupId") as string;
    const groupLabel = placement.fields.get("groupLabel");
    const groupOrder = placement.fields.get("groupOrder");
    const canonical = groupCanonical.get(groupId);
    if (!canonical) {
      groupCanonical.set(groupId, { contributionId, groupLabel, groupOrder });
      return;
    }
    if (canonical.groupLabel !== groupLabel || canonical.groupOrder !== groupOrder) {
      issues.push({
        code: "placement_group_conflict",
        message:
          `Group "${groupId}" was first declared by contribution "${canonical.contributionId}" ` +
          `(label ${JSON.stringify(canonical.groupLabel)}, order ${String(canonical.groupOrder)}); ` +
          `contribution "${contributionId}" disagrees ` +
          `(label ${JSON.stringify(groupLabel)}, order ${String(groupOrder)}).`,
        contributionId,
        referencedId: groupId,
      });
    }
  };

  for (let index = 0; index < toolSnaps.length; index += 1) {
    const snap = toolSnaps[index];
    if (!snap.shapeValid) continue;
    scanForGroupConflict(snap.placement, stringField(snap.fields, "id"));
  }
  for (let index = 0; index < editSnaps.length; index += 1) {
    const snap = editSnaps[index];
    if (!snap.shapeValid) continue;
    scanForGroupConflict(snap.placement, stringField(snap.fields, "id"));
  }

  if (issues.length === 0) {
    return {
      valid: true,
      publication: publication as unknown as SurfaceInteractionPublication,
    };
  }
  return { valid: false, publication, issues };
}
