import { readFileSync } from "node:fs";
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
const serverRoot = resolve(here, "../../../../../../DungeonMindServer");
const apiFixtures = resolve(
  serverRoot,
  "Docs/Design/fixtures/dungeonbuddy-statblock-v1-api",
);
const humanFixture = resolve(
  serverRoot,
  "Docs/Design/fixtures/dungeonbuddy-statblock-v1/human_adjudicated.json",
);

function loadJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

describe("DungeonBuddy statblock v1 contract consumer", () => {
  it("parses published API fixtures through generated TypeScript types", () => {
    const generate = loadJson<GenerateCandidateRequestV1>(
      resolve(apiFixtures, "generate-request.json"),
    );
    expect(generate.request_id).toBeTruthy();
    expect(generate.ruleset.system).toBe("dnd5e");

    const candidate = loadJson<GeneratedStatblockCandidateV1>(
      resolve(apiFixtures, "candidate-response.json"),
    );
    expect(candidate.candidate_id).toMatch(/^cand_/);
    expect(candidate.contract).toBe("dungeonmind.dungeonbuddy-statblocks");

    const validate = loadJson<{
      definition_digest: string;
      validation_receipt: ValidationReceiptV1;
    }>(resolve(apiFixtures, "validate-response.json"));
    expect(validate.definition_digest).toMatch(/^sha256:/);

    const createRequest = loadJson<CreateStatblockRequestV1>(
      resolve(apiFixtures, "create-request.json"),
    );
    expect(createRequest.idempotency_key).toBeTruthy();
    expect(createRequest.definition.identity.name).toBeTruthy();

    const createResponse = loadJson<CreateStatblockResponseV1>(
      resolve(apiFixtures, "create-response.json"),
    );
    expect(createResponse.statblock.statblock_id).toBeTruthy();
    expect(createResponse.revision.revision_id).toBeTruthy();

    const revision = loadJson<StatblockRevisionResourceV1>(
      resolve(apiFixtures, "exact-revision-response.json"),
    );
    expect(revision.statblock_id).toBe(createResponse.statblock.statblock_id);
    expect(revision.revision_id).toBe(createResponse.revision.revision_id);

    const errors = loadJson<ErrorEnvelopeV1>(resolve(apiFixtures, "errors.json"));
    expect(errors.error.code).toBeTruthy();

    // Keep ValidateDefinitionRequestV1 referenced so the smoke fails if the type vanishes.
    const validateRequest: ValidateDefinitionRequestV1 = {
      definition: createRequest.definition,
    };
    expect(validateRequest.definition.identity.name).toBe(
      createRequest.definition.identity.name,
    );
  });

  it("projects human_adjudicated combat minimums in DungeonBuddy", () => {
    const definition = loadJson<StatblockDefinitionV1_Output>(humanFixture);
    const summary = combatMinimums(definition);
    expect(summary.name).toBe("Mirror Oracle");
    expect(summary.armor_class).toBe(12);
    expect(summary.hit_points).toBe(45);
    expect(summary.human_adjudicated_elements).toContain("reflected_fate");
  });
});
