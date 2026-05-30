import type { RecapIngestStatus } from "../api/types";

interface AuthorityTransitionPanelProps {
  result: RecapIngestStatus | null;
}

const FALLBACK_AUTHORITY: Record<string, string> = {
  staged_raw_notes: "pre_canonical_evidence",
  canonical_recap: "canon_play",
  normalized_recap: "canon_play_prepared",
  breadcrumbed_recap: "canon_play_routed",
  session_memory: "derived_memory",
};

export function AuthorityTransitionPanel({ result }: AuthorityTransitionPanelProps) {
  const authority = result?.authority ?? FALLBACK_AUTHORITY;

  return (
    <section className="authority-transition-panel">
      <h4>Authority transition</h4>
      <ul>
        <li>raw notes -&gt; {authority.staged_raw_notes ?? FALLBACK_AUTHORITY.staged_raw_notes}</li>
        <li>canonical recap -&gt; {authority.canonical_recap ?? FALLBACK_AUTHORITY.canonical_recap}</li>
        <li>
          normalized recap -&gt; {authority.normalized_recap ?? FALLBACK_AUTHORITY.normalized_recap}
        </li>
        <li>
          breadcrumbed recap -&gt;{" "}
          {authority.breadcrumbed_recap ?? FALLBACK_AUTHORITY.breadcrumbed_recap}
        </li>
        <li>session memory -&gt; {authority.session_memory ?? FALLBACK_AUTHORITY.session_memory}</li>
      </ul>
      <p className="module-muted">
        Raw notes are not normal retrieval evidence after a recap exists.
      </p>
      <p className="module-muted">
        Planning scaffold is not proof of what happened.
      </p>
      <p className="module-muted">Roll tables are reference tools, not play facts.</p>
    </section>
  );
}
