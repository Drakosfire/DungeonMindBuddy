import { useCallback, useMemo, useState } from "react";
import { fromMarkdown } from "mdast-util-from-markdown";
import type { ExactRunCandidateProjection } from "../../api/exactRunCandidateProjectionApi";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { PeekClaim } from "../../surfaceInteraction/peekHost";
/** Unknown source graph links become inert text before the real chip runtime
 * sees them. Its threat-hover hook can otherwise treat a raw threat: ID as native. */
export function inertUnknownCandidateLinks(markdown: string, keys: Set<string>): {
    markdown: string;
    count: number;
} {
    const tree = fromMarkdown(markdown);
    const edits: Array<{
        start: number;
        end: number;
        text: string;
    }> = [];
    const textOf = (node: unknown): string => {
        const n = node as {
            value?: string;
            alt?: string;
            children?: unknown[];
        };
        return n.value ?? n.alt ?? n.children?.map(textOf).join("") ?? "";
    };
    const unknownDefinitions = new Set<string>();
    for (const n of tree.children) {
        if (n.type === "definition" && /^dmb-node:/i.test(n.url)) {
            let id = n.url.slice(9);
            try {
                id = decodeURIComponent(id);
            }
            catch { /* unresolved */ }
            if (!keys.has(id))
                unknownDefinitions.add(n.identifier);
        }
    }
    const visit = (node: unknown) => {
        const n = node as {
            type: string;
            url?: string;
            identifier?: string;
            children?: unknown[];
            position?: {
                start: {
                    offset?: number;
                };
                end: {
                    offset?: number;
                };
            };
        };
        if ((n.type === "link" || n.type === "definition") && /^dmb-node:/i.test(n.url ?? "")) {
            let id = (n.url ?? "").slice(9);
            try {
                id = decodeURIComponent(id);
            }
            catch { /* malformed is unresolved */ }
            if (!keys.has(id) && n.position?.start.offset !== undefined && n.position.end.offset !== undefined) {
                const text = n.type === "definition" ? "" : textOf(n).replace(/[\\`*_[\]<>]/g, "\\$&");
                edits.push({ start: n.position.start.offset, end: n.position.end.offset, text });
                return;
            }
        }
        if (n.type === "linkReference" && n.identifier && unknownDefinitions.has(n.identifier)
            && n.position?.start.offset !== undefined && n.position.end.offset !== undefined) {
            edits.push({ start: n.position.start.offset, end: n.position.end.offset, text: textOf(n).replace(/[\\`*_[\]<>]/g, "\\$&") });
            return;
        }
        n.children?.forEach(visit);
    };
    visit(tree);
    let result = markdown;
    for (const e of edits.sort((a, b) => b.start - a.start))
        result = result.slice(0, e.start) + e.text + result.slice(e.end);
    return { markdown: result, count: edits.length };
}
export function GraphReviewCandidateRecapProjection({ projection }: {
    projection: ExactRunCandidateProjection;
}) {
    const key = [projection.managedWorldId, projection.runId, projection.sourceSha256, projection.candidateSha256, projection.spanIndexSha256].join(":");
    return <LocalCandidateReader key={key} projection={projection}/>;
}
function LocalCandidateReader({ projection: p }: {
    projection: ExactRunCandidateProjection;
}) {
    const [active, setActive] = useState<string | null>(null);
    const selected = p.nodes.find(n => n.viewKey === active);
    const inspect = useCallback((key: string) => { if (p.nodes.some(n => n.viewKey === key))
        setActive(key); }, [p.nodes]);
    const dismiss = useCallback(() => setActive(null), []);
    const safeMarkdown = useMemo(() => inertUnknownCandidateLinks(p.projectedMarkdown, new Set(p.nodes.map(n => n.viewKey))), [p.projectedMarkdown, p.nodes]);
    const incident = selected ? p.edges.filter(e => e.fromViewKey === selected.viewKey || e.toViewKey === selected.viewKey) : [];
    return <section aria-label="Exact extraction candidate" className="graph-review-historical-recap-projection">
    <p role="status">Extraction candidate · {p.nodes.length} nodes · {p.edges.length} relationships. These are reviewable proposals, not an admitted World view.</p>
    {p.runWorldBindingStatus === "source_only" ? <p>Source ownership is verified. This older extraction has no frozen World context; inspection does not approve it for publication.</p> : null}
    <GraphProjectionReader frontmatterPolicy="preserve" markdown={safeMarkdown.markdown} nodeViews={p.nodeViews} sourceSpans={p.sourceSpans} graphId={`candidate:${p.runId}:${p.candidateSha256}`} documentLabel="Candidate-enriched recap" documentScroll="page" onInspectNode={inspect} authoringEnabled={false} resetKey={p.candidateSha256}/>
    <details><summary>All extracted nodes ({p.nodes.length})</summary>
      <p>{p.unlinkedNodeCount} nodes have no unambiguous literal mention linked in this view.</p>
      <ul>{p.nodes.map(n => <li key={n.viewKey}><button type="button" onClick={() => inspect(n.viewKey)}>{n.label} · candidate</button></li>)}</ul>
    </details>
    <details aria-label="Candidate reader advanced details"><summary>Advanced source and extraction details</summary>
      <p>Run {p.runId} · {p.runStatus} · {p.sourceArtifactId} · {p.sourceSha256}</p>
      <p>{p.beatCount} extracted narrative beats are retained; this view projects nodes and relationships.</p>
      <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{p.sourceMarkdown}</pre>
      {safeMarkdown.count ? <p>{safeMarkdown.count} source graph links outside this candidate are displayed as plain text.</p> : null}
      {p.diagnostics.length ? <ul>{p.diagnostics.map(d => <li key={d}>{d}</li>)}</ul> : null}
    </details>
    <PeekClaim kind="projection" active={!!selected} label={selected ? `Candidate: ${selected.label}` : "Candidate"} onDismiss={dismiss}>
      {selected ? <aside className="recap-graph-object-panel" aria-label={`Candidate: ${selected.label}`}>
        <button type="button" onClick={dismiss} aria-label="Close candidate">×</button>
        <h3>{selected.label}</h3><p>Candidate · {selected.nodeType} · confidence {selected.confidence}</p>
        <details open={selected.description.length < 600}><summary>Extracted description</summary><p style={{ whiteSpace: "pre-wrap" }}>{selected.description}</p></details>
        {selected.warnings.length ? <ul>{selected.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul> : null}
        <details><summary>Semantic state</summary><pre>{JSON.stringify(selected.semanticState, null, 2)}</pre></details>
        <h4>Candidate relationships</h4>
        <ul>{incident.map(e => {
                const other = e.fromViewKey === selected.viewKey ? e.toViewKey : e.fromViewKey;
                const target = other ? p.nodes.find(n => n.viewKey === other) : null;
                return <li key={e.candidateEdgeId}>{e.label} · {e.relationshipType} {target ? <button type="button" onClick={() => inspect(target.viewKey)}>{target.label} · candidate</button> : <span>Unresolved candidate endpoint</span>}</li>;
            })}</ul>
        <h4>Pinned source evidence</h4>
        {selected.evidence.map((e, i) => <details key={i}><summary>Source lines {e.startLine}–{e.endLine}{!e.canHighlight ? " · quote needs review" : ""}</summary>
          <blockquote>{e.paragraphText}</blockquote><p>{e.anchorQuotes.join("\n")}</p></details>)}
      </aside> : null}
    </PeekClaim>
  </section>;
}
