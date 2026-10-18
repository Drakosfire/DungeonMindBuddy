import { afterEach, expect, it, vi } from "vitest";
import * as live from "./liveApi";
import {confirmWorldbuilding, getWorldbuildingCapabilities, prepareWorldbuilding, type WorldbuildingPlan} from "./worldbuildingPublicationApi";
afterEach(() => vi.restoreAllMocks());
it("uses authenticated transport and exact existing-World contracts without stripping the sealed plan", async () => {
  const fetch = vi.spyOn(live, "authenticatedApiFetch").mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await getWorldbuildingCapabilities();
  expect(fetch).toHaveBeenLastCalledWith("/api/live/extract-promote/worldbuilding/capabilities", undefined);
  fetch.mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await prepareWorldbuilding({runId: "r", expectedParentRevisionId: "rev:1", dispositions: [{assertionId: "n", decision: "bind_existing", targetNodeId: "loc_3"}]});
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({schema: "dmb_worldbuilding_write_plan_prepare_request_v1", runId: "r", expectedParentRevisionId: "rev:1", dispositions: [{assertionId: "n", decision: "bind_existing", targetNodeId: "loc_3"}]});
  const plan = {planId: "p", prepareBinding: "opaque", unknownServerSealedField: {keep: true}} as unknown as WorldbuildingPlan;
  fetch.mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await confirmWorldbuilding(plan);
  expect(JSON.parse(String(fetch.mock.calls[2][1]?.body))).toEqual({schema: "dmb_worldbuilding_write_plan_confirm_request_v1", plan});
});
it("preserves stale-head error code without retrying", async () => {
  const fetch = vi.spyOn(live, "authenticatedApiFetch").mockResolvedValue({response: new Response(JSON.stringify({code: "stale_parent_revision", message: "Head changed"}), {status: 409}), csrf: null, requestEpoch: 1});
  await expect(prepareWorldbuilding({runId: "r", expectedParentRevisionId: "rev:old", dispositions: []})).rejects.toMatchObject({status: 409, code: "stale_parent_revision", message: "Head changed"});
  expect(fetch).toHaveBeenCalledOnce();
});
