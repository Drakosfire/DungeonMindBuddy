import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { RulesLawyerEvidence } from "./RulesLawyerEvidence";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const evidence = {
  rank: 1, entity_id: "entity-1", assertion_id: "assertion-1",
  evidence_ref_id: "ref-exact", evidence_unit_id: "unit-exact",
  source_artifact_id: "artifact-exact", source_revision_id: "revision-exact",
  source_uri: "https://example.org/source.pdf", source_locator: "page 14",
  locator: "paragraph 2", source_anchor_id: "anchor-exact", excerpt: "The exact source text.",
};

function mockPacket(status: string, items: typeof evidence[] = []) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      schema_version: "dmb_rules_query_packet_v1", query_id: "q1", ruleset_id: "r1",
      rules_space_id: "s1", rules_revision_id: "v1", status, evidence: items,
      trace: { completeness: status === "success" ? "complete" : "partial", reason: "source state" },
    }),
  }));
}

async function submit() {
  fireEvent.change(screen.getByLabelText("Ask a rules question"), { target: { value: "Can I end movement in an occupied space?" } });
  fireEvent.click(screen.getByRole("button", { name: "Find evidence" }));
}

it("submits a query and preserves exact citation identity through inspection", async () => {
  mockPacket("success", [evidence]);
  render(<RulesLawyerEvidence />);
  await submit();
  await screen.findByText("Cited rules evidence");
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/live/rules/query"), expect.objectContaining({
    body: expect.stringContaining("Can I end movement in an occupied space?"),
  }));
  fireEvent.click(screen.getByRole("button", { name: "Inspect citation 1" }));
  const details = screen.getByTestId("citation-1-details");
  expect(details.hidden).toBe(false);
  expect(details.textContent).toContain("unit-exact");
  expect(details.textContent).toContain("ref-exact");
  expect(details.textContent).toContain("artifact-exact");
  expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute("href", "https://example.org/source.pdf");
});

it.each([
  ["no_evidence", "No evidence found"],
  ["insufficient_evidence", "Only partial evidence"],
  ["rules_space_unavailable", "Rules evidence service unavailable"],
  ["downstream_failure", "Rules evidence service unavailable"],
])("shows %s truthfully", async (status, expected) => {
  mockPacket(status);
  render(<RulesLawyerEvidence />);
  await submit();
  await waitFor(() => expect(screen.getByText(new RegExp(expected))).toBeInTheDocument());
});

it("renders cited synthesis with the exact source inspection affordance", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      schema_version: "dmb_rules_query_packet_v1", query_id: "q1", ruleset_id: "r1",
      rules_space_id: "s1", rules_revision_id: "v1", status: "success",
      evidence: [evidence], trace: { completeness: "complete", reason: null },
    }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      schema_version: "dmb_rules_answer_response_v1",
      packet: {
        schema_version: "dmb_rules_query_packet_v1", query_id: "q1", ruleset_id: "r1",
        rules_space_id: "s1", rules_revision_id: "v1", status: "success",
        evidence: [evidence], trace: { completeness: "complete", reason: null },
      },
      answer: {
        status: "supported", answer: "No, the rule prohibits it.",
        citation_evidence_ref_ids: ["ref-exact"], needs_more_evidence: false,
        reason: null, generation_trace_id: "trace-exact",
      },
    }) }));
  render(<RulesLawyerEvidence />);
  await submit();
  fireEvent.click(await screen.findByRole("button", { name: "Synthesize cited answer" }));
  await screen.findByText("No, the rule prohibits it.");
  const answer = screen.getByRole("region", { name: "Cited answer" });
  const citation = answer.querySelector('button[aria-label="Inspect citation 1"]');
  expect(citation).not.toBeNull();
  fireEvent.click(citation!);
  expect(answer.textContent).toContain("unit-exact");
});
