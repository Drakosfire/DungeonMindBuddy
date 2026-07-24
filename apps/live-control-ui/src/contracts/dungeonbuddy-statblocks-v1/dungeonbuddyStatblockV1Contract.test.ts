import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import type {
  CreateStatblockRequestV1,
  CreateStatblockResponseV1,
  ErrorEnvelopeV1,
  GenerateCandidateRequestV1,
  GeneratedStatblockCandidateV1,
  StatblockDefinitionV1_Output,
  StatblockRevisionResourceV1,
  ValidateDefinitionRequestV1,
  ValidationReceiptV1,
} from "./client";
import { combatMinimums } from "./combatMinimums";

const here = dirname(fileURLToPath(import.meta.url));
const vendoredClientPath = resolve(here, "client.ts");
const serverRoot = resolve(here, "../../../../../../DungeonMindServer");
const serverClientPath = resolve(
  serverRoot,
  "generated/dungeonbuddy-statblocks-v1/client.ts",
);
const apiFixtures = resolve(
  serverRoot,
  "Docs/Design/fixtures/dungeonbuddy-statblock-v1-api",
);
const humanFixture = resolve(
  serverRoot,
  "Docs/Design/fixtures/dungeonbuddy-statblock-v1/human_adjudicated.json",
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value;
}

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8")) as unknown;
}

function assertRuleset(value: unknown, label: string): void {
  const ruleset = requireRecord(value, label);
  requireString(ruleset.system, `${label}.system`);
  requireString(ruleset.edition, `${label}.edition`);
}

function assertDefinition(value: unknown, label: string): StatblockDefinitionV1_Output {
  const definition = requireRecord(value, label);
  assertRuleset(definition.ruleset, `${label}.ruleset`);
  const identity = requireRecord(definition.identity, `${label}.identity`);
  requireString(identity.name, `${label}.identity.name`);
  const defenses = requireRecord(definition.defenses, `${label}.defenses`);
  requireRecord(defenses.default_armor_class, `${label}.defenses.default_armor_class`);
  if (
    defenses.alternate_armor_classes !== undefined &&
    !Array.isArray(defenses.alternate_armor_classes)
  ) {
    throw new Error(`${label}.defenses.alternate_armor_classes must be an array when present`);
  }
  const vitality = requireRecord(definition.vitality, `${label}.vitality`);
  requireRecord(vitality.hit_points, `${label}.vitality.hit_points`);
  const movement = requireRecord(definition.movement, `${label}.movement`);
  if (!Array.isArray(movement.modes) || movement.modes.length === 0) {
    throw new Error(`${label}.movement.modes must be a non-empty array`);
  }
  requireRecord(definition.abilities, `${label}.abilities`);
  requireRecord(definition.challenge, `${label}.challenge`);
  if (!Array.isArray(definition.rule_elements)) {
    throw new Error(`${label}.rule_elements must be an array`);
  }
  return definition as unknown as StatblockDefinitionV1_Output;
}

function assertGenerateRequest(value: unknown): GenerateCandidateRequestV1 {
  const body = requireRecord(value, "GenerateCandidateRequestV1");
  requireString(body.request_id, "request_id");
  assertRuleset(body.ruleset, "ruleset");
  return body as unknown as GenerateCandidateRequestV1;
}

function assertCandidate(value: unknown): GeneratedStatblockCandidateV1 {
  const body = requireRecord(value, "GeneratedStatblockCandidateV1");
  requireString(body.candidate_id, "candidate_id");
  if (body.contract !== "dungeonmind.dungeonbuddy-statblocks") {
    throw new Error(`unexpected contract ${String(body.contract)}`);
  }
  requireString(body.contract_version, "contract_version");
  assertDefinition(body.definition, "candidate.definition");
  const receipt = requireRecord(body.validation_receipt, "validation_receipt");
  requireString(receipt.definition_digest, "validation_receipt.definition_digest");
  requireString(body.created_at, "created_at");
  requireString(body.expires_at, "expires_at");
  return body as unknown as GeneratedStatblockCandidateV1;
}

function assertCreateRequest(value: unknown): CreateStatblockRequestV1 {
  const body = requireRecord(value, "CreateStatblockRequestV1");
  requireString(body.idempotency_key, "idempotency_key");
  requireString(body.change_summary, "change_summary");
  assertDefinition(body.definition, "create.definition");
  return body as unknown as CreateStatblockRequestV1;
}

function assertCreateResponse(value: unknown): CreateStatblockResponseV1 {
  const body = requireRecord(value, "CreateStatblockResponseV1");
  const statblock = requireRecord(body.statblock, "statblock");
  const revision = requireRecord(body.revision, "revision");
  requireString(statblock.statblock_id, "statblock.statblock_id");
  requireString(revision.revision_id, "revision.revision_id");
  requireString(revision.definition_digest, "revision.definition_digest");
  assertDefinition(revision.definition, "revision.definition");
  return body as unknown as CreateStatblockResponseV1;
}

function assertRevision(value: unknown): StatblockRevisionResourceV1 {
  const body = requireRecord(value, "StatblockRevisionResourceV1");
  requireString(body.statblock_id, "statblock_id");
  requireString(body.revision_id, "revision_id");
  requireString(body.definition_digest, "definition_digest");
  assertDefinition(body.definition, "revision.definition");
  return body as unknown as StatblockRevisionResourceV1;
}

function assertErrorEnvelope(value: unknown): ErrorEnvelopeV1 {
  const body = requireRecord(value, "ErrorEnvelopeV1");
  const error = requireRecord(body.error, "error");
  requireString(error.code, "error.code");
  requireString(error.message, "error.message");
  return body as unknown as ErrorEnvelopeV1;
}

function assertValidateResponse(value: unknown): {
  definition_digest: string;
  validation_receipt: ValidationReceiptV1;
} {
  const body = requireRecord(value, "validate-response");
  requireString(body.definition_digest, "definition_digest");
  const receipt = requireRecord(body.validation_receipt, "validation_receipt");
  requireString(receipt.definition_digest, "validation_receipt.definition_digest");
  return body as unknown as {
    definition_digest: string;
    validation_receipt: ValidationReceiptV1;
  };
}

function clientFingerprint(source: string): string {
  const match = source.match(/Source fingerprint:\s*(sha256:[a-f0-9]+)/);
  if (!match) {
    throw new Error("vendored client is missing Source fingerprint header");
  }
  return match[1];
}

describe("DungeonBuddy statblock v1 contract consumer", () => {
  it("keeps the vendored client identical to the Server artifact", () => {
    const vendored = readFileSync(vendoredClientPath, "utf8");
    const fingerprint = clientFingerprint(vendored);
    expect(fingerprint).toMatch(/^sha256:[a-f0-9]{64}$/);

    if (!existsSync(serverClientPath)) {
      throw new Error(
        `Sibling Server client missing at ${serverClientPath}. ` +
          "Consumer drift proof requires a DungeonMindServer checkout beside DungeonMindBuddy.",
      );
    }
    const serverClient = readFileSync(serverClientPath, "utf8");
    expect(vendored).toBe(serverClient);
    expect(clientFingerprint(serverClient)).toBe(fingerprint);

    const openapiPath = resolve(serverRoot, "openapi/dungeonbuddy-statblocks-v1.json");
    const openapiDigest = createHash("sha256")
      .update(readFileSync(openapiPath))
      .digest("hex");
    expect(fingerprint).toBe(`sha256:${openapiDigest}`);
  });

  it("parses published API fixtures through generated TypeScript types", () => {
    if (!existsSync(apiFixtures)) {
      throw new Error(`API fixtures missing at ${apiFixtures}`);
    }

    const generate = assertGenerateRequest(
      loadJson(resolve(apiFixtures, "generate-request.json")),
    );
    expect(generate.ruleset.system).toBe("dnd5e");

    const candidate = assertCandidate(
      loadJson(resolve(apiFixtures, "candidate-response.json")),
    );
    expect(candidate.candidate_id).toMatch(/^cand_/);

    const validate = assertValidateResponse(
      loadJson(resolve(apiFixtures, "validate-response.json")),
    );
    expect(validate.definition_digest).toMatch(/^sha256:/);

    const createRequest = assertCreateRequest(
      loadJson(resolve(apiFixtures, "create-request.json")),
    );
    expect(createRequest.definition.identity.name).toBeTruthy();

    const createResponse = assertCreateResponse(
      loadJson(resolve(apiFixtures, "create-response.json")),
    );
    expect(createResponse.revision.statblock_id).toBe(
      createResponse.statblock.statblock_id,
    );

    const revision = assertRevision(
      loadJson(resolve(apiFixtures, "exact-revision-response.json")),
    );
    expect(revision.statblock_id).toBe(createResponse.statblock.statblock_id);
    expect(revision.revision_id).toBe(createResponse.revision.revision_id);

    const errors = assertErrorEnvelope(loadJson(resolve(apiFixtures, "errors.json")));
    expect(errors.error.code).toBe("validation_failed");

    const validateRequest: ValidateDefinitionRequestV1 = {
      definition: createRequest.definition,
    };
    expect(validateRequest.definition.identity.name).toBe(
      createRequest.definition.identity.name,
    );
  });

  it("projects human_adjudicated combat minimums in DungeonBuddy", () => {
    const definition = assertDefinition(loadJson(humanFixture), "human_adjudicated");
    const summary = combatMinimums(definition);
    expect(summary.name).toBe("Mirror Oracle");
    expect(summary.armor_class).toBe(12);
    expect(summary.hit_points).toBe(45);
    expect(summary.human_adjudicated_elements).toContain("reflected_fate");
  });
});
