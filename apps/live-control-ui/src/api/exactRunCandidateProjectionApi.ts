import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import type { GraphProjectionNodeView, RecapProjectionSourceSpan } from "./types";
export interface CandidateReadEvidence {
    sourceSpanId: string;
    startLine: number;
    endLine: number;
    paragraphText: string;
    anchorQuotes: string[];
    canHighlight: boolean;
}
export interface CandidateReadNode {
    viewKey: string;
    candidateNodeId: string;
    label: string;
    nodeType: string;
    description: string;
    confidence: string;
    semanticState: Record<string, string>;
    warnings: string[];
    evidence: CandidateReadEvidence[];
}
export interface CandidateReadEdge {
    candidateEdgeId: string;
    fromViewKey: string | null;
    toViewKey: string | null;
    fromCandidateId: string;
    toCandidateId: string;
    relationshipType: string;
    label: string;
    evidence: CandidateReadEvidence[];
}
export interface ExactRunCandidateProjection {
    schema: "dmb_exact_run_candidate_projection_v1";
    trustBoundary: "unpublished_candidate";
    runId: string;
    runRevision: number;
    runStatus: "reviewable" | "promoted";
    profileId: "recap_category_v1@1.0";
    sourceDomain: "recap";
    sourceArtifactId: string;
    sourceRevisionId: string;
    sourceSha256: string;
    candidateSha256: string;
    spanIndexSha256: string;
    campaignId: string;
    sessionId: string;
    managedWorldId: string;
    nativeWorldId: string;
    bindingVersion: number;
    runWorldBindingStatus: "frozen_verified" | "source_only";
    sourceMarkdown: string;
    narrativeMarkdown: string;
    projectedMarkdown: string;
    sourceDisplaySegments: Array<{
        sourceStart: number;
        sourceEnd: number;
        displayStart: number;
        displayEnd: number;
    }>;
    nodes: CandidateReadNode[];
    edges: CandidateReadEdge[];
    nodeViews: Record<string, GraphProjectionNodeView>;
    sourceSpans: RecapProjectionSourceSpan[];
    mentionsCount: number;
    unlinkedNodeCount: number;
    beatCount: number;
    diagnostics: string[];
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === "string");
const evidence = (v: unknown): boolean => Array.isArray(v) && v.every(e => record(e) && typeof e.sourceSpanId === "string"
    && Number.isSafeInteger(e.startLine) && Number.isSafeInteger(e.endLine) && Number(e.startLine) > 0 && Number(e.endLine) >= Number(e.startLine)
    && typeof e.paragraphText === "string" && strings(e.anchorQuotes) && typeof e.canHighlight === "boolean");
const digest = (s: unknown): s is string => typeof s === "string" && /^sha256:[a-f0-9]{64}$/.test(s);
function invalid(): never { throw new LiveApiError("The exact candidate response does not match its source, run or World.", 0); }
export async function getExactRunCandidateProjection(runId: string, managedWorldId: string): Promise<ExactRunCandidateProjection> {
    if (!runId.trim() || runId !== runId.trim() || !managedWorldId.trim() || managedWorldId !== managedWorldId.trim())
        invalid();
    const { response } = await authenticatedApiFetch(`/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}/candidate-projection?managed_world_id=${encodeURIComponent(managedWorldId)}`, { cache: "no-store" });
    let body: unknown;
    try {
        body = JSON.parse(await response.text());
    }
    catch {
        throw new LiveApiError(`Candidate response was not JSON (HTTP ${response.status}).`, response.status);
    }
    if (!response.ok) {
        const raw = (record(body) ? body : {}) as {
            detail?: {
                code?: string;
                message?: string;
            } | string;
        };
        throw new LiveApiError(raw.detail !== null && typeof raw.detail === "object" ? raw.detail.message || "Candidate inspection failed." : typeof raw.detail === "string" ? raw.detail : "Candidate inspection failed.", response.status, { code: raw.detail !== null && typeof raw.detail === "object" ? raw.detail.code : null });
    }
    const result = body as ExactRunCandidateProjection;
    if (!result || result.schema !== "dmb_exact_run_candidate_projection_v1" || result.trustBoundary !== "unpublished_candidate"
        || result.runId !== runId || result.managedWorldId !== managedWorldId || result.sourceDomain !== "recap"
        || result.profileId !== "recap_category_v1@1.0" || !["reviewable", "promoted"].includes(result.runStatus)
        || !["frozen_verified", "source_only"].includes(result.runWorldBindingStatus) || !Number.isSafeInteger(result.runRevision) || result.runRevision < 1
        || !result.nativeWorldId || !result.sourceArtifactId || !Number.isSafeInteger(result.bindingVersion) || result.bindingVersion < 1
        || !digest(result.sourceSha256) || result.sourceRevisionId !== result.sourceSha256 || !digest(result.candidateSha256) || !digest(result.spanIndexSha256)
        || typeof result.sourceMarkdown !== "string" || typeof result.narrativeMarkdown !== "string" || typeof result.projectedMarkdown !== "string"
        || typeof result.campaignId !== "string" || !result.campaignId || typeof result.sessionId !== "string" || !result.sessionId
        || !Array.isArray(result.nodes) || !Array.isArray(result.edges) || !Array.isArray(result.sourceDisplaySegments) || !record(result.nodeViews)
        || !Array.isArray(result.sourceSpans) || !strings(result.diagnostics)
        || ![result.mentionsCount, result.unlinkedNodeCount, result.beatCount].every(x => Number.isSafeInteger(x) && x >= 0)
        || result.nodes.some(n => !record(n) || ![n.viewKey, n.candidateNodeId, n.label, n.nodeType, n.description, n.confidence].every(x => typeof x === "string")
            || !record(n.semanticState) || !Object.values(n.semanticState).every(x => typeof x === "string") || !strings(n.warnings) || !evidence(n.evidence))
        || result.edges.some(e => !record(e) || ![e.candidateEdgeId, e.fromCandidateId, e.toCandidateId, e.relationshipType, e.label].every(x => typeof x === "string") || !evidence(e.evidence))
        || result.sourceSpans.some(s => !record(s) || typeof s.span_id !== "string" || typeof s.text_excerpt !== "string" || ![s.line_start, s.line_end, s.ordinal].every(Number.isSafeInteger))
        || Object.values(result.nodeViews).some(v => !record(v) || typeof v.label !== "string" || !strings(v.aliases) || !strings(v.source_domains) || !Array.isArray(v.evidence_badges) || !Array.isArray(v.adjacency))
        || result.sourceDisplaySegments.some(s => !record(s)))
        invalid();
    const rawHash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(result.sourceMarkdown));
    if ("sha256:" + [...new Uint8Array(rawHash)].map(n => n.toString(16).padStart(2, "0")).join("") !== result.sourceSha256)
        invalid();
    const sourcePoints = Array.from(result.sourceMarkdown), narrativePoints = Array.from(result.narrativeMarkdown);
    let priorSource = 0, priorDisplay = 0;
    for (const s of result.sourceDisplaySegments) {
        if (![s.sourceStart, s.sourceEnd, s.displayStart, s.displayEnd].every(Number.isSafeInteger)
            || s.sourceStart < priorSource || s.sourceEnd < s.sourceStart || s.displayStart !== priorDisplay || s.displayEnd < s.displayStart
            || s.sourceEnd > sourcePoints.length || s.displayEnd > narrativePoints.length
            || sourcePoints.slice(s.sourceStart, s.sourceEnd).join("") !== narrativePoints.slice(s.displayStart, s.displayEnd).join(""))
            invalid();
        priorSource = s.sourceEnd;
        priorDisplay = s.displayEnd;
    }
    if (priorDisplay !== narrativePoints.length)
        invalid();
    const prefix = `candidate:${runId}:${result.candidateSha256.slice(7)}:`;
    const keys = new Set(result.nodes.map(n => n.viewKey));
    if (keys.size !== result.nodes.length || Object.keys(result.nodeViews).length !== keys.size
        || result.nodes.some(n => !n.viewKey.startsWith(prefix) || !/^[a-f0-9]{64}$/.test(n.viewKey.slice(prefix.length))
            || !n.candidateNodeId || result.nodeViews[n.viewKey]?.node_id !== n.viewKey || result.nodeViews[n.viewKey]?.role !== "unpublished_candidate" || result.nodeViews[n.viewKey]?.kind !== "candidate")
        || result.edges.some(e => (e.fromViewKey !== null && !keys.has(e.fromViewKey)) || (e.toViewKey !== null && !keys.has(e.toViewKey))))
        invalid();
    return result;
}
