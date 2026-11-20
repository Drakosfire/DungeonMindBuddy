import { useState } from "react";
import "./guestReleaseReview.css";
import { GuestReleaseSelection } from "./GuestReleaseSelection";

type Candidate = { release_id: string; created_at: string };
type Published = { release_id: string; published_at: string; current: boolean; reviewable: boolean };
type Source = { id: string; text: string };
type Node = { id: string; label: string; kind: string; name_citations: string[]; kind_citations: string[]; name_temporal: string; kind_temporal: string };
type Edge = { id: string; source: string; target: string; label: string; citations: string[]; temporal: string };
type Review = { digest: string; source_visibility: Record<string, string>; manifest: { graph: { nodes: Node[]; edges: Edge[] }; sources: Source[]; assets: { id: string }[] } };

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin", cache: "no-store", ...init });
  if (!response.ok) throw new Error("Guest release is unavailable or changed. Try again.");
  return response.json() as Promise<T>;
}

/** Owner-only review of server-staged bytes. Rendered text is never interpreted as HTML. */
export function GuestReleaseReview({ worldId }: { worldId: string }) {
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [releases, setReleases] = useState<Published[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedKind, setSelectedKind] = useState<"candidate" | "published">("candidate");
  const [review, setReview] = useState<Review | null>(null);
  const [version, setVersion] = useState<number | null>(null);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [published, setPublished] = useState(false);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [loadedAssets, setLoadedAssets] = useState<Set<string>>(new Set());
  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [revokeConfirmed, setRevokeConfirmed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const base = `/api/live/worlds/${encodeURIComponent(worldId)}/guest-releases`;

  async function load() {
    setBusy(true); setError(null); setNotice(null); setReview(null); setSelected(null); setApproved(false); setPublished(false); setLoadedAssets(new Set()); setRevokeId(null); setRevokeConfirmed(false);
    try {
      const [drafts, history] = await Promise.all([
        readJson<{ candidates: Candidate[] }>(`${base}/candidates`),
        readJson<{ releases: Published[] }>(`${base}/published`),
      ]);
      setCandidates(drafts.candidates); setReleases(history.releases);
    }
    catch { setError("Guest release is unavailable. Try again later."); }
    finally { setBusy(false); }
  }
  async function inspect(id: string, kind: "candidate" | "published") {
    setBusy(true); setError(null); setReview(null); setSelected(null); setApproved(false); setPublished(false); setOperationId(null); setLoadedAssets(new Set());
    try {
      const [candidate, status] = await Promise.all([
        readJson<Review>(`${base}/candidates/${encodeURIComponent(id)}`),
        readJson<{ version: number }>(`${base}/status`),
      ]);
      setReview(candidate); setVersion(status.version); setSelected(id); setSelectedKind(kind);
    } catch { setError("This candidate is unavailable or changed. Reload the list."); }
    finally { setBusy(false); }
  }
  async function publish() {
    if (!approved || !review || !selected || version === null || !imagesReady || !sourcesReady) return;
    setBusy(true); setError(null);
    const op = operationId ?? crypto.randomUUID();
    setOperationId(op);
    try {
      await readJson(`${base}/candidates/${encodeURIComponent(selected)}/${selectedKind === "candidate" ? "publish" : "restore"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedKind === "candidate" ? { digest: review.digest, expected_version: version, operation_id: op } : { expected_version: version }),
      });
      setPublished(true); setApproved(false);
    } catch { setError(selectedKind === "candidate" ? "Publication could not be confirmed. Retry this same request or reload to review again." : "Restore could not be confirmed. Reload to check the current release."); }
    finally { setBusy(false); }
  }
  async function revoke() {
    if (!revokeId || !revokeConfirmed) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const response = await fetch(`${base}/candidates/${encodeURIComponent(revokeId)}/revoke`, {
        method: "POST", credentials: "same-origin", cache: "no-store", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      if (!response.ok) throw new Error("revoke failed");
      setReleases(null); setCandidates(null); setReview(null); setSelected(null); setRevokeId(null); setRevokeConfirmed(false);
      setNotice("Copy revoked. Reload to check which copy, if any, is currently available.");
    } catch { setError("Revocation could not be confirmed. Reload to check its status."); }
    finally { setBusy(false); }
  }
  const names = new Map(review?.manifest.graph.nodes.map(node => [node.id, node.label]) ?? []);
  const sourceNumbers = new Map(review?.manifest.sources.map((source, index) => [source.id, index + 1]) ?? []);
  const citations = (ids: string[]) => ids.map(id => `excerpt ${sourceNumbers.get(id) ?? "unavailable"}`).join(", ");
  const imagesReady = review?.manifest.assets.every(asset => loadedAssets.has(asset.id)) ?? false;
  const sourcesReady = review?.manifest.sources.every(source => ["internal", "player_safe"].includes(review.source_visibility[source.id])) ?? false;
  return <section aria-labelledby="guest-review-heading" className="guest-release-review">
    <h2 id="guest-review-heading">Guest release review</h2>
    <GuestReleaseSelection worldId={worldId} onPrepared={() => { setCandidates(null); setReview(null); setSelected(null); }} />
    <p>Review a prepared copy before making it available to guests.</p>
    <button type="button" onClick={load} disabled={busy}>Load prepared copies</button>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {candidates && candidates.length === 0 && <p>No prepared copies yet.</p>}
    {candidates && candidates.length > 0 && <ul>{candidates.map(candidate => <li key={candidate.release_id}>
      <button type="button" disabled={busy} onClick={() => inspect(candidate.release_id, "candidate")}>Review copy from {new Date(candidate.created_at).toLocaleString()}</button>
    </li>)}</ul>}
    {releases && <div><h3>Published copies</h3>
      {releases.length === 0 ? <p>No published copies.</p> : <ul>{releases.map(release => <li key={release.release_id}>
        <span>{release.current ? "Current copy" : "Earlier copy"} · {new Date(release.published_at).toLocaleString()}</span>{" "}
        {release.reviewable && !release.current && <button type="button" disabled={busy} onClick={() => inspect(release.release_id, "published")}>Review earlier copy</button>}{" "}
        <button type="button" disabled={busy} onClick={() => { setRevokeId(release.release_id); setRevokeConfirmed(false); }}>Withdraw this copy</button>
        {revokeId === release.release_id && <div><p>Withdrawal permanently revokes this copy. A different current copy, if any, stays available.</p><label><input type="checkbox" checked={revokeConfirmed} disabled={busy} onChange={event => setRevokeConfirmed(event.target.checked)} /> I want to revoke this copy.</label>{" "}<button type="button" disabled={busy || !revokeConfirmed} onClick={revoke}>Confirm withdrawal</button></div>}
      </li>)}</ul>}
    </div>}
    {review && selected && <div>
      <h3>Review everything guests will see</h3>
      <p>This copy can include private source material you select for release. Later private edits do not update it. If a source is withdrawn after the publication check begins, it may still appear in the copy; revoke the release to withdraw the copy.</p>
      <h4>Graph</h4>
      <ul>{review.manifest.graph.nodes.map(node => <li key={node.id}>{node.label} · {node.kind} (name: {node.name_temporal}, {citations(node.name_citations)}; classification: {node.kind_temporal}, {citations(node.kind_citations)})</li>)}</ul>
      <ul>{review.manifest.graph.edges.map(edge => <li key={edge.id}>{names.get(edge.source)} — {edge.label} → {names.get(edge.target)} ({edge.temporal}, {citations(edge.citations)})</li>)}</ul>
      <h4>Source excerpts</h4>
      {review.manifest.sources.map((source, index) => <section key={source.id}><h5>Excerpt {index + 1} · {review.source_visibility[source.id] === "internal" ? "private source" : review.source_visibility[source.id] === "player_safe" ? "player-safe source" : "source visibility unavailable"}</h5><p style={{ whiteSpace: "pre-wrap" }}>{source.text}</p></section>)}
      <h4>Images</h4>
      {review.manifest.assets.length === 0 ? <p>No images selected.</p> : review.manifest.assets.map((asset, index) => <img key={asset.id} src={`${base}/candidates/${encodeURIComponent(selected)}/assets/${encodeURIComponent(asset.id)}`} alt={`Selected release image ${index + 1}`} style={{ maxWidth: "100%" }} onLoad={() => setLoadedAssets(previous => new Set(previous).add(asset.id))} onError={() => { setLoadedAssets(previous => { const next = new Set(previous); next.delete(asset.id); return next; }); setApproved(false); setError("An image could not be loaded. Reload this copy before approving it."); }} />)}
      {!imagesReady && <p>All selected images must load before approval.</p>}
      {!sourcesReady && <p>Source visibility must be available before approval.</p>}
      <p>Snapshot digest: <code>{review.digest}</code></p>
      {!published && <><label><input type="checkbox" checked={approved} onChange={event => setApproved(event.target.checked)} disabled={busy || !imagesReady || !sourcesReady} /> I reviewed this copy and approve making these exact contents available to guests.</label><br /><button type="button" disabled={!approved || busy || !imagesReady || !sourcesReady} onClick={publish}>{selectedKind === "candidate" ? "Publish this copy" : "Restore this copy"}</button></>}
      {published && <p role="status">Copy {selectedKind === "candidate" ? "published" : "restored"}. Guest page delivery is not yet available on this deployment. Reload to check the current copy.</p>}
    </div>}
  </section>;
}
