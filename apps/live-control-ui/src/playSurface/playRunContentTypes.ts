/** Run content is Play-owned. Its edition identity is never a WorkRevision. */
export interface PlayRunContentOrigin {
  playable_artifact_id: string;
  playable_revision: number;
  playable_work_revision_id: string;
  playable_content_sha256: string;
}
export interface PlayRunContent {
  schema_version: "dmb_world_play_run_content_v1";
  world_id: string;
  run_id: string;
  origin: PlayRunContentOrigin;
  source: "pinned" | "edition";
  edition_revision: number;
  edition_revision_id: string | null;
  markdown: string;
  content_sha256: string;
  committed_at: string;
  observed_run_revision: number;
  structure_sha256: string;
}

export interface PlayRunContentCommitRequest {
  schema_version: "dmb_world_play_run_content_commit_v1";
  expected_origin: PlayRunContentOrigin;
  expected_edition_revision: number;
  expected_content_sha256: string;
  expected_run_revision?: number;
  markdown: string;
}

export interface PlayRunContentReceipt {
  schema_version: "dmb_world_play_run_content_receipt_v1";
  world_id: string;
  run_id: string;
  command_id: string;
  request_sha256: string;
  origin: PlayRunContentOrigin;
  expected_edition_revision: number;
  expected_content_sha256: string;
  accepted_edition_revision: number;
  accepted_edition_revision_id: string;
  accepted_content_sha256: string;
  committed_at: string;
  observed_run_revision: number;
}
