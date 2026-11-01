import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import type { ExactRunCandidateProjection } from '../../api/exactRunCandidateProjectionApi';
import { GraphReviewCandidateRecapProjection, inertUnknownCandidateLinks } from './GraphReviewCandidateRecapProjection';
import * as live from '../../api/liveApi';
import * as nativeReview from '../../api/recapNativeReviewApi';
import { GraphNodeChipRuntimeProvider } from '../../graphReference/GraphNodeChipRuntime';
import { GraphNodeHoverToken } from '../../graphReference/GraphNodeHoverToken';
import { presentationForNodeId } from '../../graphReference/presentation';
const key = `candidate:run-a:${'a'.repeat(64)}:${'b'.repeat(64)}`;
function fixture(): ExactRunCandidateProjection {
    return { schema: 'dmb_exact_run_candidate_projection_v1', trustBoundary: 'unpublished_candidate', runId: 'run-a', runRevision: 5, runStatus: 'reviewable', profileId: 'recap_category_v1@1.0', sourceDomain: 'recap',
        sourceArtifactId: 'artifact:a', sourceRevisionId: 'sha256:' + 'c'.repeat(64), sourceSha256: 'sha256:' + 'c'.repeat(64), candidateSha256: 'sha256:' + 'a'.repeat(64), spanIndexSha256: 'sha256:' + 'd'.repeat(64),
        campaignId: 'campaign-a', sessionId: 'session-29', managedWorldId: 'managed-a', nativeWorldId: 'native-a', bindingVersion: 1, runWorldBindingStatus: 'source_only',
        sourceMarkdown: '# Raw source\n\nMara is here.', narrativeMarkdown: '# Raw source\n\nMara is here.', projectedMarkdown: `# Recap\n\n[Mara](dmb-node:${key}) is here. [forged](dmb-node:threat:loc_3)`,
        sourceDisplaySegments: [], nodes: [{ viewKey: key, candidateNodeId: 'threat:loc_3', label: 'Mara', nodeType: 'threat', description: 'A'.repeat(1200), confidence: 'medium', semanticState: { lifecycle_state: 'candidate' }, warnings: [], evidence: [{ sourceSpanId: 'span-a', startLine: 3, endLine: 3, paragraphText: 'Mara is here.', anchorQuotes: ['Mara is here.'], canHighlight: true }] }],
        edges: [], nodeViews: { [key]: { node_id: key, label: 'Mara', kind: 'candidate', role: 'unpublished_candidate', aliases: [], source_domains: ['recap'], evidence_badges: [], adjacency: [], anchored_to_focus_session: false } }, sourceSpans: [], mentionsCount: 1, unlinkedNodeCount: 0, beatCount: 2, diagnostics: [] };
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it('renders real chips and only a local candidate inspector, retaining full raw source under Advanced', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    const native = vi.spyOn(live, 'postWorldGraphCompleteObject');
    render(<GraphReviewCandidateRecapProjection projection={fixture()}/>);
    const chip = await screen.findByRole('button', { name: 'Mara', exact: true });
    fireEvent.focus(chip);
    fireEvent.mouseEnter(chip);
    fireEvent.click(chip);
    expect(await screen.findByRole('complementary', { name: 'Candidate: Mara' })).toBeInTheDocument();
    expect(screen.getByText('Extracted description')).toBeInTheDocument();
    expect(screen.getByText('A'.repeat(1200))).toBeInTheDocument();
    expect(screen.getByText(/older extraction has no frozen World context/)).toBeInTheDocument();
    expect(document.querySelector('details[aria-label="Candidate reader advanced details"] pre')?.textContent).toBe('# Raw source\n\nMara is here.');
    expect(screen.getByText(/source graph links outside this candidate/)).toBeInTheDocument();
    expect(document.querySelector('button[data-graph-node-id="threat:loc_3"]')).toBeNull();
    expect(native).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
});
it('resets local selection when exact candidate identity changes', async () => {
    const p = fixture();
    const ui = render(<GraphReviewCandidateRecapProjection projection={p}/>);
    fireEvent.click(await screen.findByRole('button', { name: 'Mara', exact: true }));
    expect(screen.getByRole('complementary')).toBeInTheDocument();
    ui.rerender(<GraphReviewCandidateRecapProjection projection={{ ...p, runId: 'run-b' }}/>);
    expect(screen.queryByRole('complementary')).toBeNull();
});
it('does not rewrite protected code or ordinary external links while neutralizing an unknown graph link', () => {
    const source = '`[code](dmb-node:threat:loc_3)`\n\n[external](https://example.com) and [unknown](dmb-node:threat:loc_3)';
    const safe = inertUnknownCandidateLinks(source, new Set());
    expect(safe.markdown).toBe('`[code](dmb-node:threat:loc_3)`\n\n[external](https://example.com) and unknown');
    expect(safe.count).toBe(1);
});
it('keeps qualified local graph navigation', () => {
    const source = `[Mara](dmb-node:${key})`;
    expect(inertUnknownCandidateLinks(source, new Set([key])).markdown).toBe(source);
});
it('qualified raw threat candidate never hydrates mechanics under a live native exactGraphScope', async () => {
    const p = fixture();
    const fetch = vi.spyOn(globalThis, 'fetch');
    const hydrate = vi.spyOn(live, 'postThreatQueryHydration');
    render(<GraphNodeChipRuntimeProvider value={{ nodeViews: p.nodeViews, activeNodeId: null, onSelectNode: () => undefined,
            exactGraphScope: { worldId: 'native-a', campaignId: 'campaign-a', scopeMode: 'world', revisionId: 'rev:head' } }}>
    <GraphNodeHoverToken presentation={presentationForNodeId(p.nodeViews, key, 'Mara')} label="Mara" pinned={false} onSelect={() => undefined}/>
  </GraphNodeChipRuntimeProvider>);
    const chip = screen.getByRole('button', { name: 'Mara', exact: true });
    fireEvent.mouseEnter(chip);
    fireEvent.focus(chip);
    await Promise.resolve();
    expect(hydrate).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
});
it('neutralizes unknown reference links and encoded raw identities without changing their visible labels', () => {
    const source = '[forged][old] and [encoded](DMB-NODE:threat%3Aloc_3)\n\n[old]: dmb-node:threat:loc_3';
    const safe = inertUnknownCandidateLinks(source, new Set());
    expect(safe.markdown).toBe('forged and encoded\n\n');
});


it.each([
  "---\nnormalization_schema: unknown_story\nstory_fact: The gate is red\n---\n\n",
  "---\nnormalization_schema: [malformed\nstory_fact: The gate is red\n---\n\n",
  "--- document_class: play normalization_schema: dmb_recap_normalized_v1 --- # Recap changed-heading\n\n",
  "--- document_class: play normalization_schema: dmb_recap_normalized_v1 --- # Recap # extra story\n\n",
])("preserves retained source prefix in the final real candidate renderer: %s", async (prefix) => {
  const p = fixture();
  p.sourceMarkdown = prefix + "Mara is here.";
  p.narrativeMarkdown = p.sourceMarkdown;
  p.sourceSpans = [{ span_id: "retained-body", kind: "paragraph", text_excerpt: "Mara is here." }];
  p.projectedMarkdown = prefix + `[Mara](dmb-node:${key}) is here.`;
  const fetch = vi.spyOn(globalThis, "fetch");
  render(<GraphReviewCandidateRecapProjection projection={p} />);
  const reader = document.querySelector(".union-supergraph-tiptap-reader");
  expect(reader?.textContent).toContain(prefix.includes("story_fact") ? "The gate is red" : prefix.trim());
  fireEvent.click(await screen.findByRole("button", { name: "Mara", exact: true }));
  expect(screen.getByRole("complementary", { name: "Candidate: Mara" })).toBeInTheDocument();
  expect(document.querySelector('details[aria-label="Candidate reader advanced details"] pre')?.textContent).toBe(p.sourceMarkdown);
  await waitFor(() => expect(document.querySelector('[data-source-span-id="retained-body"]')?.textContent).toContain(" is here."));
  expect(fetch).not.toHaveBeenCalled();
});

it("does not restore recognized normalization metadata already removed by the producer", () => {
  const p = fixture();
  p.sourceMarkdown = "---\nnormalization_schema: dmb_recap_normalized_v1\n---\n# Recap\n\nMara is here.";
  p.narrativeMarkdown = "# Recap\n\nMara is here.";
  p.projectedMarkdown = `# Recap\n\n[Mara](dmb-node:${key}) is here.`;
  render(<GraphReviewCandidateRecapProjection projection={p} />);
  expect(document.querySelector(".union-supergraph-tiptap-reader")?.textContent).not.toContain("normalization_schema");
  expect(screen.getByRole("heading", { name: "Recap" })).toBeInTheDocument();
  expect(document.querySelector('details[aria-label="Candidate reader advanced details"] pre')?.textContent).toBe(p.sourceMarkdown);
});

it("explicitly compares the actual selected candidate ID through the mounted inspector", async () => {
  const compare = vi.spyOn(nativeReview, "getRecapNativeReview").mockResolvedValue({ source_revision_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", native_context: {
    revision_id: "rev:current", source_authority_epoch: 23, source_admission: { state: "not_found" }, source_evidence: [],
    domain_contract_ref: { domain_id: "world", domain_revision: "2", descriptor_sha256: "a".repeat(64) }, semantic_profile_ref: { profile_id: "game", profile_revision: "1", descriptor_sha256: "b".repeat(64) },
    selections: [{ candidate_node_id: "threat:loc_3", status: "absent", search_is_advisory: true, alternatives: [] }],
  } });
  const p = fixture(); render(<GraphReviewCandidateRecapProjection projection={p}/>);
  fireEvent.click(await screen.findByRole("button", { name: "Mara", exact: true })); expect(compare).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Compare with World", exact: true }));
  expect(await screen.findByText(/not available for comparison yet/)).toBeInTheDocument();
  expect(compare).toHaveBeenCalledExactlyOnceWith(p, "threat:loc_3", expect.any(AbortSignal));
});
