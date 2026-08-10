import { describe, expect, it, vi } from "vitest";

import type { CreateWorkspaceDocumentRequest, WorkspaceDocumentRecord } from "../api/types";
import {
  createWorkspaceDocumentCreationController,
  createWorkspaceDocumentRequestFromIntent,
  WorkspaceDocumentCreationError,
  type WorkspaceDocumentCreateIntent,
} from "./workspaceDocumentCreation";

function fixtureRecord(
  overrides: Partial<WorkspaceDocumentRecord> = {},
): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    title: "C2 Session 28 Prep",
    campaign_id: "longmont-c2",
    target_session: 28,
    kind: "plan",
    target_relpath:
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 28 Prep.md",
    status: "active",
    content_status: "draft",
    revision: 1,
    created_at: "2026-08-10T00:00:00Z",
    updated_at: "2026-08-10T00:00:00Z",
    ...overrides,
  };
}

describe("createWorkspaceDocumentRequestFromIntent", () => {
  it("maps plan intent without worldbuilding metadata", () => {
    const intent: WorkspaceDocumentCreateIntent = {
      kind: "plan",
      campaignId: "longmont-c2",
      title: "C2 Session 28 Prep",
      targetSession: 28,
      targetRelpath: "corpus/path/Session 28 Prep.md",
    };
    const request = createWorkspaceDocumentRequestFromIntent(intent);
    expect(request).toEqual({
      title: "C2 Session 28 Prep",
      campaign_id: "longmont-c2",
      kind: "plan",
      target_session: 28,
      target_relpath: "corpus/path/Session 28 Prep.md",
    });
    expect(request).not.toHaveProperty("source_domain");
    expect(request).not.toHaveProperty("document_class");
    expect(request).not.toHaveProperty("authority_state");
    expect(request).not.toHaveProperty("visibility_state");
  });

  it("maps runbook intent with session/path and no worldbuilding metadata", () => {
    const request = createWorkspaceDocumentRequestFromIntent({
      kind: "runbook",
      campaignId: "longmont-c2",
      title: "North Gate Runbook",
      targetSession: 22,
      targetRelpath: "corpus/path/runbook.md",
    });
    expect(request.kind).toBe("runbook");
    expect(request.target_session).toBe(22);
    expect(request.target_relpath).toBe("corpus/path/runbook.md");
    expect(request).not.toHaveProperty("source_domain");
  });

  it("maps worldbuilding intent with derived source_domain and no caller target_relpath", () => {
    const request = createWorkspaceDocumentRequestFromIntent({
      kind: "worldbuilding_source",
      campaignId: "longmont-c2",
      title: "Untitled worldbuilding source",
      documentClass: "lore",
      authorityState: "draft",
      visibilityState: "internal",
    });
    expect(request).toEqual({
      title: "Untitled worldbuilding source",
      campaign_id: "longmont-c2",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });
    expect(request).not.toHaveProperty("target_relpath");
    expect(request).not.toHaveProperty("target_session");
  });
});

describe("createWorkspaceDocumentCreationController", () => {
  const planIntent: WorkspaceDocumentCreateIntent = {
    kind: "plan",
    campaignId: "longmont-c2",
    title: "C2 Session 28 Prep",
    targetSession: 28,
    targetRelpath: "corpus/path/Session 28 Prep.md",
  };

  it("exposes the exact server document_id after create", async () => {
    const created = fixtureRecord();
    const create = vi.fn(async (_request: CreateWorkspaceDocumentRequest) => created);
    const controller = createWorkspaceDocumentCreationController({ create });
    const result = await controller.create(planIntent);
    expect(result.record.document_id).toBe(created.document_id);
    expect(result.intentCurrent).toBe(true);
    expect(controller.getState().phase).toBe("created");
    expect(create).toHaveBeenCalledTimes(1);
  });

  it("performs one POST when create is invoked twice while in flight", async () => {
    let resolveCreate: ((value: WorkspaceDocumentRecord) => void) | null = null;
    const create = vi.fn(
      () =>
        new Promise<WorkspaceDocumentRecord>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    const controller = createWorkspaceDocumentCreationController({ create });

    const first = controller.create(planIntent);
    await expect(controller.create(planIntent)).rejects.toMatchObject({ code: "busy" });
    resolveCreate?.(fixtureRecord());
    await first;
    expect(create).toHaveBeenCalledTimes(1);
  });

  it("retains the exact record when activation fails and retry does not POST again", async () => {
    const created = fixtureRecord();
    const create = vi.fn(async () => created);
    const controller = createWorkspaceDocumentCreationController({ create });
    await controller.create(planIntent);

    await expect(
      controller.activate(async () => {
        throw new Error("Workspace document not found");
      }),
    ).rejects.toBeInstanceOf(WorkspaceDocumentCreationError);

    expect(controller.getState()).toMatchObject({
      phase: "activation_failed",
      record: created,
      error: "Workspace document not found",
    });
    expect(create).toHaveBeenCalledTimes(1);

    const activated = await controller.activate(async () => true);
    expect(activated.applied).toBe(true);
    expect(activated.record.document_id).toBe(created.document_id);
    expect(create).toHaveBeenCalledTimes(1);
    expect(controller.getState().phase).toBe("activated");
  });

  it("create after activation_failed returns the retained record without a second POST", async () => {
    const created = fixtureRecord();
    const create = vi.fn(async () => created);
    const controller = createWorkspaceDocumentCreationController({ create });
    await controller.create(planIntent);
    await expect(controller.activate(async () => {
      throw new Error("open failed");
    })).rejects.toThrow(/open failed/);

    const again = await controller.create(planIntent);
    expect(again.record.document_id).toBe(created.document_id);
    expect(again.intentCurrent).toBe(true);
    expect(create).toHaveBeenCalledTimes(1);
  });

  it("marks create_failed without retaining a record so retry may POST again", async () => {
    const create = vi
      .fn()
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(fixtureRecord());
    const controller = createWorkspaceDocumentCreationController({ create });

    await expect(controller.create(planIntent)).rejects.toMatchObject({ code: "create_failed" });
    expect(controller.getState().record).toBeNull();

    const result = await controller.create(planIntent);
    expect(result.record.document_id).toBe("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("treats superseded activation as non-applied without activation_failed", async () => {
    const created = fixtureRecord();
    const create = vi.fn(async () => created);
    const controller = createWorkspaceDocumentCreationController({ create });
    await controller.create(planIntent);
    const result = await controller.activate(async () => false);
    expect(result.applied).toBe(false);
    expect(controller.getState().phase).toBe("created");
    expect(controller.getState().error).toBeNull();
  });

  it("delayed create POST after supersede returns intentCurrent=false and does not retain reuse", async () => {
    let resolveCreate: ((value: WorkspaceDocumentRecord) => void) | null = null;
    const create = vi.fn(
      () =>
        new Promise<WorkspaceDocumentRecord>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    const controller = createWorkspaceDocumentCreationController({ create });
    const pending = controller.create(planIntent);
    controller.supersedePendingCreateIntent();
    resolveCreate?.(fixtureRecord({ document_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" }));
    const result = await pending;
    expect(result.intentCurrent).toBe(false);
    expect(result.record.document_id).toBe("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");
    expect(controller.getState().phase).toBe("idle");
    expect(controller.getState().record).toBeNull();

    const next = fixtureRecord({
      document_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      title: "C2 Session 29 Prep",
    });
    create.mockResolvedValueOnce(next);
    const createdC = await controller.create({
      ...planIntent,
      title: "C2 Session 29 Prep",
      targetSession: 29,
      targetRelpath: "corpus/path/Session 29 Prep.md",
    });
    expect(createdC.record.document_id).toBe("cccccccc-cccc-4ccc-8ccc-cccccccccccc");
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("createThenActivate skips activation when create intent was superseded during POST", async () => {
    let resolveCreate: ((value: WorkspaceDocumentRecord) => void) | null = null;
    const create = vi.fn(
      () =>
        new Promise<WorkspaceDocumentRecord>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    const activateExact = vi.fn(async () => true);
    const controller = createWorkspaceDocumentCreationController({ create });
    const pending = controller.createThenActivate(planIntent, activateExact);
    controller.supersedePendingCreateIntent();
    resolveCreate?.(fixtureRecord());
    const result = await pending;
    expect(result.applied).toBe(false);
    expect(activateExact).not.toHaveBeenCalled();
  });

  it("reconcileActivatedDocument retires activation_failed retention so later create POSTs", async () => {
    const createdB = fixtureRecord({ document_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" });
    const createdC = fixtureRecord({
      document_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      title: "C2 Session 29 Prep",
    });
    const create = vi.fn().mockResolvedValueOnce(createdB).mockResolvedValueOnce(createdC);
    const controller = createWorkspaceDocumentCreationController({ create });
    await controller.create(planIntent);
    await expect(
      controller.activate(async () => {
        throw new Error("activation failed");
      }),
    ).rejects.toMatchObject({ code: "activation_failed" });

    controller.reconcileActivatedDocument("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect(controller.getState().phase).toBe("idle");
    expect(controller.getState().record).toBeNull();

    const result = await controller.create({
      ...planIntent,
      title: "C2 Session 29 Prep",
      targetSession: 29,
      targetRelpath: "corpus/path/Session 29 Prep.md",
    });
    expect(result.record.document_id).toBe("cccccccc-cccc-4ccc-8ccc-cccccccccccc");
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("reconcileActivatedDocument marks the retained created document activated", async () => {
    const created = fixtureRecord();
    const create = vi.fn(async () => created);
    const controller = createWorkspaceDocumentCreationController({ create });
    await controller.create(planIntent);
    controller.reconcileActivatedDocument(created.document_id);
    expect(controller.getState().phase).toBe("activated");
    expect(controller.getState().record?.document_id).toBe(created.document_id);
  });
});
