import { webcrypto, createHash } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";
import type { ExactRunCandidateProjection } from "./exactRunCandidateProjectionApi";
function payload(): ExactRunCandidateProjection {
    const source = "😀 Mara meets Lysandro.\r\n";
    const sha = "sha256:" + createHash('sha256').update(source).digest('hex');
    const key = `candidate:run-a:${'c'.repeat(64)}:${'d'.repeat(64)}`;
    return { schema: "dmb_exact_run_candidate_projection_v1", trustBoundary: "unpublished_candidate", runId: "run-a", runRevision: 5, runStatus: "reviewable",
        profileId: "recap_category_v1@1.0", sourceDomain: "recap", sourceArtifactId: "artifact:a", sourceRevisionId: sha, sourceSha256: sha,
        candidateSha256: "sha256:" + 'c'.repeat(64), spanIndexSha256: "sha256:" + 'b'.repeat(64), campaignId: "campaign-a", sessionId: "session-29",
        managedWorldId: "managed-a", nativeWorldId: "native-a", bindingVersion: 1, runWorldBindingStatus: "source_only", sourceMarkdown: source, narrativeMarkdown: source,
        projectedMarkdown: source.replace('Mara', `[Mara](dmb-node:${key})`), sourceDisplaySegments: [{ sourceStart: 0, sourceEnd: Array.from(source).length, displayStart: 0, displayEnd: Array.from(source).length }],
        nodes: [{ viewKey: key, candidateNodeId: "threat:loc_3", label: "Mara", nodeType: "threat", description: "Extracted description", confidence: "medium", semanticState: { lifecycle_state: "candidate" }, warnings: [], evidence: [] }],
        edges: [], nodeViews: { [key]: { node_id: key, label: "Mara", kind: "candidate", role: "unpublished_candidate", aliases: [], source_domains: ["recap"], evidence_badges: [], adjacency: [], anchored_to_focus_session: false } },
        sourceSpans: [], mentionsCount: 1, unlinkedNodeCount: 0, beatCount: 0, diagnostics: [] };
}
let api: typeof import('./liveApi') | null = null;
afterEach(() => { api?.setNativeGraphAccessToken(null); api = null; vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules(); });
async function client(base = "") {
    vi.resetModules();
    vi.stubEnv('VITE_LIVE_API_BASE_URL', base);
    vi.stubGlobal('crypto', webcrypto);
    api = await import('./liveApi');
    return import('./exactRunCandidateProjectionApi');
}
it('reads exact source through real bearer transport and validates astral/CRLF coordinate planes', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const data = payload();
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(data));
    expect(await c.getExactRunCandidateProjection('run-a', 'managed-a')).toEqual(data);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch.mock.calls[0][0]).toBe('/api/live/graph-preview/extraction-runs/run-a/candidate-projection?managed_world_id=managed-a');
    const init = fetch.mock.calls[0][1];
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer synthetic-test-credential');
    expect(init?.cache).toBe('no-store');
    expect(init?.redirect).toBe('error');
});
it('restores the existing local session without a domain mutation', async () => {
    const c = await client();
    const fetch = vi.spyOn(globalThis, 'fetch')
        .mockResolvedValueOnce(Response.json({ status: 'active', csrf_token: 'synthetic-csrf' })).mockResolvedValueOnce(Response.json(payload()));
    await c.getExactRunCandidateProjection('run-a', 'managed-a');
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[0][0]).toBe('/api/live/agent/local-session');
    expect(fetch.mock.calls.every(([, i]) => i?.method === undefined || i.method === 'GET')).toBe(true);
});
it.each(['runId', 'managedWorldId', 'trustBoundary', 'sourceSha256', 'sourceRevisionId'] as const)('rejects contradictory %s', async (key) => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ ...payload(), [key]: 'foreign' }));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('rejects tampered source text despite matching metadata digests', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ ...payload(), sourceMarkdown: 'changed' }));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('rejects native or threat presentation even for a qualified map key', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const p = payload();
    p.nodeViews[p.nodes[0].viewKey].kind = 'threat';
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(p));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('rejects a map forwarding the raw native-looking ID as presentation identity', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const p = payload();
    p.nodeViews[p.nodes[0].viewKey].node_id = 'threat:loc_3';
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(p));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('rejects a shifted source coordinate mapping', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const p = payload();
    p.sourceDisplaySegments[0].sourceStart = 1;
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(p));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('blocks nonloopback before exposing credentials or source selectors', async () => {
    const c = await client('https://example.invalid');
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const fetch = vi.spyOn(globalThis, 'fetch');
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ message: expect.stringContaining('loopback') });
    expect(fetch).not.toHaveBeenCalled();
});
it.each(['warnings', 'evidence', 'semanticState'] as const)('rejects malformed nested candidate %s before rendering', async (field) => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const p = payload();
    Object.assign(p.nodes[0], { [field]: null });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json(p));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 0 });
});
it('reports non-JSON and null error bodies without falling through to another reader', async () => {
    const c = await client();
    api!.setNativeGraphAccessToken('synthetic-test-credential');
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('<html>error</html>', { status: 500 })).mockResolvedValueOnce(Response.json(null, { status: 422 }));
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 500 });
    await expect(c.getExactRunCandidateProjection('run-a', 'managed-a')).rejects.toMatchObject({ status: 422 });
    expect(fetch).toHaveBeenCalledTimes(2);
});
