import { webcrypto } from "node:crypto";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contentSha256 } from "../playRunEffectiveContent";
import type { PlayRunContent } from "../playRunContentTypes";
import { writePlayRunContentJournal } from "./playRunContentJournal";
import { PlaySessionContentEditor } from "./PlaySessionContentEditor";

vi.mock("../../api/playRunContentApi", () => ({ getWorldPlayRunContent: vi.fn(), getWorldPlayRunContentCommand: vi.fn(), putWorldPlayRunContentCommand: vi.fn() }));

const identity = { worldId: "world", runId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  origin: { playable_artifact_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", playable_revision: 1,
    playable_work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", playable_content_sha256: "" } };
let content: PlayRunContent;

beforeEach(async () => {
  vi.stubGlobal("crypto", webcrypto);
  window.localStorage.clear();
  const markdown = "# Gate\n\nOriginal prose.\n";
  identity.origin.playable_content_sha256 = await contentSha256(markdown);
  content = { schema_version: "dmb_world_play_run_content_v1", world_id: identity.worldId, run_id: identity.runId,
    origin: identity.origin, source: "pinned", edition_revision: 0, edition_revision_id: null, markdown,
    content_sha256: await contentSha256(markdown), structure_sha256: "e".repeat(64), committed_at: "2026-10-18T00:00:00Z", observed_run_revision: 1 };
});

describe("Play session-copy editor", () => {
  it("replaces an already-open visual document when the durable recovery journal restores a draft", async () => {
    const recovered = "# Gate\n\nRecovered prose from the local journal.\n";
    writePlayRunContentJournal(identity, { schema_version: "dmb_play_run_content_journal_v1", identity, accepted: content,
      draft_markdown: recovered, draft_generation: 1, pending: null });
    let releaseDigest!: () => void;
    const digestGate = new Promise<void>(resolve => { releaseDigest = resolve; });
    const digest = webcrypto.subtle.digest.bind(webcrypto.subtle);
    vi.stubGlobal("crypto", { randomUUID: webcrypto.randomUUID.bind(webcrypto), subtle: {
      digest: async (...args: Parameters<typeof digest>) => { await digestGate; return digest(...args); },
    } });
    const { putWorldPlayRunContentCommand } = await import("../../api/playRunContentApi");
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(() => new Promise(() => undefined));
    const user = userEvent.setup();
    render(<PlaySessionContentEditor content={content} currentSceneId="scene:gate" originLabel="Saved Plan" onAcceptedContent={vi.fn()} onUnsubmittedChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    expect(await screen.findByText("Original prose.")).toBeInTheDocument();
    const rawBefore = window.localStorage.getItem((await import("./playRunContentJournal")).playRunContentJournalKey(identity));
    expect(screen.getByTestId("play-session-copy-visual").querySelector(".ProseMirror")).toHaveAttribute("contenteditable", "false");
    await user.click(screen.getByRole("button", { name: "Markdown" }));
    const source = screen.getByRole("textbox", { name: "Session copy Markdown" });
    expect(source).toBeDisabled();
    await user.type(source, "Too early");
    expect(window.localStorage.getItem((await import("./playRunContentJournal")).playRunContentJournalKey(identity))).toBe(rawBefore);
    expect(source).toHaveValue("# Gate\n\nOriginal prose.\n");
    await user.click(screen.getByRole("button", { name: "Visual" }));
    releaseDigest();
    await waitFor(() => expect(screen.getByText("Recovered prose from the local journal.")).toBeInTheDocument());
    expect(screen.queryByText("Original prose.")).not.toBeInTheDocument();
  });

  it("replaces an open visual editor only after the user discards a reviewed draft for the latest copy", async () => {
    const localDraft = "# Gate\n\nMy reviewed local draft.\n";
    const latestMarkdown = "# Gate\n\nLatest remote version.\n";
    const latest: PlayRunContent = { ...content, source: "edition", edition_revision: 2,
      edition_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", markdown: latestMarkdown,
      content_sha256: await contentSha256(latestMarkdown), committed_at: "2026-10-18T02:00:00Z" };
    writePlayRunContentJournal(identity, { schema_version: "dmb_play_run_content_journal_v1", identity, accepted: content,
      draft_markdown: localDraft, draft_generation: 1, pending: null });
    const user = userEvent.setup();
    render(<PlaySessionContentEditor content={latest} currentSceneId="scene:gate" originLabel="Saved Plan" onAcceptedContent={vi.fn()} onUnsubmittedChange={vi.fn()} />);
    expect(await screen.findByText("Another saved version needs review")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    expect(await screen.findByText("My reviewed local draft.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use latest and discard my draft" }));
    expect(await screen.findByText("Latest remote version.")).toBeInTheDocument();
    expect(screen.queryByText("My reviewed local draft.")).not.toBeInTheDocument();
  });
  it("opens without writing and preserves YAML, table, callout and distinct media descriptors in source edits", async () => {
    const { putWorldPlayRunContentCommand } = await import("../../api/playRunContentApi");
    vi.mocked(putWorldPlayRunContentCommand).mockReset();
    const yaml = "---\r\ntitle: Session\r\n---\r\n";
    const media = "![First](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd \"dmb-image:v1 width=35 collapsed=true\")\n\n![Second](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd \"dmb-image:v1 width=80 collapsed=false\")";
    const body = "# Gate\n\nOriginal prose.\n\n| Die | Result |\n| --- | --- |\n| 1 | Rain |\n\n> [!NOTE] Reminder\n> Keep the gate.\n\n" + media + "\n";
    const rich = { ...content, markdown: yaml + body, content_sha256: await contentSha256(yaml + body) };
    const user = userEvent.setup();
    const mounted = render(<PlaySessionContentEditor content={rich} currentSceneId={null} originLabel="Saved Plan" onAcceptedContent={vi.fn()} onUnsubmittedChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    await user.click(screen.getByRole("button", { name: "Markdown" }));
    expect(putWorldPlayRunContentCommand).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("textbox", { name: "Session copy Markdown" }), { target: { value: body.replace("Original prose.", "Edited prose.") } });
    const raw = window.localStorage.getItem((await import("./playRunContentJournal")).playRunContentJournalKey(identity))!;
    const saved = JSON.parse(raw).draft_markdown;
    expect(saved.startsWith(yaml)).toBe(true);
    expect(saved).toContain(media);
    expect(saved).toContain("| 1 | Rain |");
    expect(saved).toContain("> [!NOTE] Reminder");
    expect(saved).toContain("Edited prose.");
    mounted.unmount();
  });

  it("navigates to the canonical marked Scene heading in the visual editor", async () => {
    const markdown = "<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## First\n\nOpening.\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n## Gate\n\nCurrent scene.\n";
    const marked = { ...content, markdown, content_sha256: await contentSha256(markdown) };
    const user = userEvent.setup();
    render(<PlaySessionContentEditor content={marked} currentSceneId="scene:gate" originLabel="Saved Plan" onAcceptedContent={vi.fn()} onUnsubmittedChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    const heading = screen.getByRole("heading", { name: "Gate" });
    const scroll = vi.fn();
    heading.scrollIntoView = scroll;
    await user.click(screen.getByRole("button", { name: "Go to current scene" }));
    expect(scroll).toHaveBeenCalledWith({ block: "center", behavior: "smooth" });
    await waitFor(() => expect(window.getSelection()?.anchorNode?.parentElement?.closest("h2")).toBe(heading));
    await user.click(screen.getByRole("button", { name: "Markdown" }));
    expect(screen.queryByRole("button", { name: "Go to current scene" })).not.toBeInTheDocument();
  });

});
