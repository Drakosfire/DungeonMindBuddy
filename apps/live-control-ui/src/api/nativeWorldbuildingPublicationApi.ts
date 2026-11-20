import { authenticatedApiFetch, LiveApiError } from "./liveApi";

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Packet = Record<string, Json>;

export interface NativeWorldbuildingPrepareInput {
  managed_world_id: string;
  run_id: string;
  expected_run_revision: number;
  candidate_sha256: string;
  expected_parent_revision_id: string;
  expected_source_authority_epoch: number;
  workspace_document_id: string;
  workspace_document_revision: number;
  selections: Packet[];
}

export interface NativeWorldbuildingConfirmation {
  envelope: Packet;
  prepared: Packet;
  token: string;
}

const record = (value: unknown): value is Packet =>
  value !== null && typeof value === "object" && !Array.isArray(value);

// The server expands schema defaults in the signed review.
function matchesSubmitted(actual: Json | undefined, submitted: Json): boolean {
  if (Array.isArray(submitted)) {
    return Array.isArray(actual) && actual.length === submitted.length &&
      submitted.every((value, index) => matchesSubmitted(actual[index], value));
  }
  if (record(submitted)) {
    return record(actual) && Object.entries(submitted).every(([key, value]) =>
      matchesSubmitted(actual[key], value));
  }
  return actual === submitted;
}

async function post(operation: "prepare" | "confirm" | "worldbuilding-context", body: object): Promise<Packet> {
  const { response } = await authenticatedApiFetch(
    `/api/live/extract-promote/native-${operation}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
  );
  const value: unknown = await response.json();
  if (!response.ok) {
    const detail = record(value) && record(value.detail) ? value.detail : {};
    throw new LiveApiError(
      typeof detail.message === "string" ? detail.message : "Native Worldbuilding publication failed.",
      response.status,
      { code: typeof detail.code === "string" ? detail.code : null },
    );
  }
  if (!record(value)) throw new LiveApiError("Invalid native Worldbuilding response.", response.status);
  return value;
}

export async function prepareNativeWorldbuilding(input: NativeWorldbuildingPrepareInput) {
  const value = await post("prepare", input);
  if (value.publication !== "not_performed" ||
      value.run_id !== input.run_id || value.run_revision !== input.expected_run_revision ||
      value.candidate_sha256 !== input.candidate_sha256 ||
      value.expected_parent_revision_id !== input.expected_parent_revision_id ||
      value.expected_source_authority_epoch !== input.expected_source_authority_epoch ||
      !Array.isArray(value.records)) {
    throw new LiveApiError("Native preparation changed the selected review scope.", 0);
  }
  if (value.status === "held" && value.envelope === null && value.prepared === null && value.token === null) {
    return { status: "held" as const, records: value.records };
  }
  const { envelope, prepared, token } = value;
  if (value.status !== "prepared" || !record(envelope) || !record(prepared) ||
      typeof token !== "string" || !token || envelope.purpose !== "dmb_native_worldbuilding_confirm_v1" ||
      !matchesSubmitted(envelope.review, { ...input })) {
    throw new LiveApiError("Invalid native Worldbuilding confirmation packet.", 0);
  }
  return { status: "prepared" as const, records: value.records, confirmation: { envelope, prepared, token } };
}

export async function confirmNativeWorldbuilding(packet: NativeWorldbuildingConfirmation) {
  const { envelope } = packet;
  const review = envelope.review;
  if (!record(review) || typeof envelope.prepared_change_id !== "string" ||
      !envelope.prepared_change_id || typeof review.expected_parent_revision_id !== "string" ||
      envelope.purpose !== "dmb_native_worldbuilding_confirm_v1") {
    throw new LiveApiError("Invalid native Worldbuilding confirmation packet.", 0);
  }
  const value = await post("confirm", packet);
  if (value.status !== "committed" || typeof value.recovered !== "boolean" ||
      !record(value.result) || typeof value.result.child_revision_id !== "string" ||
      !value.result.child_revision_id ||
      value.result.prepared_change_id !== envelope.prepared_change_id ||
      value.result.dungeonmind_publication_id !== envelope.prepared_change_id ||
      value.result.expected_parent_revision_id !== review.expected_parent_revision_id) {
    throw new LiveApiError("Invalid native Worldbuilding receipt.", 0);
  }
  return { result: value.result, recovered: value.recovered };
}

type ReviewSource = Pick<NativeWorldbuildingPrepareInput, "managed_world_id" | "run_id"> & {
  source_artifact_id: string;
  source_sha256: string;
};

export async function getNativeWorldbuildingContext(source: ReviewSource) {
  const value = await post("worldbuilding-context", source);
  const coordinates = value.prepare_coordinates;
  const binding = value.binding;
  if (value.schema !== "dmb_native_worldbuilding_review_context_v1" ||
      value.source_artifact_id !== source.source_artifact_id || value.source_sha256 !== source.source_sha256 ||
      !record(binding) || typeof binding.native_world_id !== "string" || !binding.native_world_id ||
      !record(coordinates) || coordinates.managed_world_id !== source.managed_world_id ||
      coordinates.run_id !== source.run_id ||
      typeof coordinates.expected_run_revision !== "number" || !Number.isSafeInteger(coordinates.expected_run_revision) ||
      coordinates.expected_run_revision < 1 ||
      typeof coordinates.candidate_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(coordinates.candidate_sha256) ||
      typeof coordinates.expected_parent_revision_id !== "string" || !coordinates.expected_parent_revision_id ||
      typeof coordinates.expected_source_authority_epoch !== "number" || !Number.isSafeInteger(coordinates.expected_source_authority_epoch) ||
      coordinates.expected_source_authority_epoch < 1 ||
      typeof coordinates.workspace_document_id !== "string" || !coordinates.workspace_document_id ||
      typeof coordinates.workspace_document_revision !== "number" || !Number.isSafeInteger(coordinates.workspace_document_revision) ||
      coordinates.workspace_document_revision < 1) {
    throw new LiveApiError("Native Worldbuilding context changed the selected review scope.", 0);
  }
  const prepareCoordinates: Omit<NativeWorldbuildingPrepareInput, "selections"> = {
    managed_world_id: source.managed_world_id,
    run_id: source.run_id,
    expected_run_revision: coordinates.expected_run_revision,
    candidate_sha256: coordinates.candidate_sha256,
    expected_parent_revision_id: coordinates.expected_parent_revision_id,
    expected_source_authority_epoch: coordinates.expected_source_authority_epoch,
    workspace_document_id: coordinates.workspace_document_id,
    workspace_document_revision: coordinates.workspace_document_revision,
  };
  const records = value.records;
  const sourceSupport = value.source_support;
  if (!Array.isArray(records) || !Array.isArray(sourceSupport) ||
      records.some(row => !record(row) || (row.kind !== "node" && row.kind !== "edge" && row.kind !== "source_observation") ||
        typeof row.record_id !== "string" || !row.record_id || !record(row.fields)) ||
      sourceSupport.some(row => !record(row) || typeof row.evidence_ref_id !== "string" ||
        !row.evidence_ref_id || typeof row.text !== "string" ||
        typeof row.start_byte !== "number" || !Number.isSafeInteger(row.start_byte) || row.start_byte < 0 ||
        typeof row.end_byte !== "number" || !Number.isSafeInteger(row.end_byte) || row.end_byte <= row.start_byte)) {
    throw new LiveApiError("Invalid native Worldbuilding review inventory.", 0);
  }
  return { prepareCoordinates, nativeWorldId: binding.native_world_id, records, sourceSupport };
}
