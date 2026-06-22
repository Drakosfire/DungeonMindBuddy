import { useState, type FormEvent } from "react";

import { getSourceBundle, postLiveQuery } from "../../api/liveApi";
import type {
  IngestionSourceBundle,
  LiveQueryBackend,
  LiveQueryResponse,
  PlanViewProjection,
  SourceUnit,
} from "../../api/types";

import { ContextSufficiencyPanel } from "./ContextSufficiencyPanel";
import { buildPacketReview } from "./contextSufficiencyLadder";

interface PlanAgentInteractionBarProps {
  planView: PlanViewProjection;
  loadBundle?: typeof getSourceBundle;
  askCorpus?: typeof postLiveQuery;
}

type BundleStatus = "idle" | "loading" | "ready" | "error";
type AskStatus = "idle" | "asking" | "answered" | "error";

const REQUIRED_INGEST_STAGES = [
  "canon_recap",
  "normalized",
  "breadcrumbed",
  "frontmatter_seed",
  "session_memory_jsonl",
  "session_memory_meta",
];

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function sourceKind(unit: SourceUnit): string {
  return stringField(unit.fields.sourceKind) ?? unit.unitKind;
}

function unitsForSession(bundle: IngestionSourceBundle, session: number): SourceUnit[] {
  return bundle.units
    .filter((unit) => unit.evidenceRole !== "diagnostic_only")
    .filter((unit) => numberField(unit.fields.sessionNumber) === session);
}

function representativeUnits(bundle: IngestionSourceBundle, activeSession: number): SourceUnit[] {
  const activeSessionUnits = unitsForSession(bundle, activeSession);
  const fallbackUnits = bundle.units.filter((unit) => unit.evidenceRole !== "diagnostic_only");
  return (activeSessionUnits.length ? activeSessionUnits : fallbackUnits)
    .slice(0, 8);
}

function sessionNumbers(bundle: IngestionSourceBundle): number[] {
  const sessions = new Set<number>();
  for (const unit of bundle.units) {
    const session = numberField(unit.fields.sessionNumber);
    if (session !== null) sessions.add(session);
  }
  return Array.from(sessions).sort((a, b) => b - a);
}

export function PlanAgentInteractionBar({
  planView,
  loadBundle = getSourceBundle,
  askCorpus = postLiveQuery,
}: PlanAgentInteractionBarProps) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<BundleStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<IngestionSourceBundle | null>(null);
  const [question, setQuestion] = useState("");
  const [queryBackend, setQueryBackend] = useState<LiveQueryBackend>("live");
  const [askStatus, setAskStatus] = useState<AskStatus>("idle");
  const [askError, setAskError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<LiveQueryResponse | null>(null);

  async function openPane() {
    setOpen(true);
    if (bundle || status === "loading") return;
    setStatus("loading");
    setError(null);
    try {
      const response = await loadBundle("campaign-ingested", planView.campaign_id);
      setBundle(response);
      setStatus("ready");
    } catch (loadError) {
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Unable to load source bundle");
    }
  }

  async function toggleDrawer() {
    if (open) {
      setOpen(false);
      return;
    }
    await openPane();
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || askStatus === "asking") return;
    setAskStatus("asking");
    setAskError(null);
    try {
      const response = await askCorpus(
        trimmed,
        planView.campaign_id,
        planView.session,
        queryBackend,
      );
      setAnswer(response);
      setAskStatus("answered");
    } catch (loadError) {
      setAskStatus("error");
      setAskError(loadError instanceof Error ? loadError.message : "Unable to ask corpus");
    }
  }

  const coverage = bundle?.coverage ?? {};
  const unitCount = numberField(coverage.unitCount) ?? bundle?.units.length ?? 0;
  const artifactCount = numberField(coverage.artifactCount) ?? bundle?.artifacts.length ?? 0;
  const routesOnDisk = numberField(coverage.ingestRoutesOnDisk);
  const dogfoodRoutes = numberField(coverage.ingestRoutesInDogfoodFullManifest);
  const slimRoutes = numberField(coverage.ingestRoutesInC2S23Manifest);
  const activeSessionUnits = bundle ? unitsForSession(bundle, planView.session) : [];
  const activeStageKinds = new Set(activeSessionUnits.map(sourceKind));
  const missingStages = REQUIRED_INGEST_STAGES.filter((stage) => !activeStageKinds.has(stage));
  const activeSessionComplete = bundle ? missingStages.length === 0 : false;
  const latestSessions = bundle ? sessionNumbers(bundle).slice(0, 5) : [];
  const packetReview = answer ? buildPacketReview(answer) : null;

  return (
    <section
      className={`plan-agent-shell ${open ? "open" : "closed"}`}
      aria-label="Agent Interaction placeholder"
    >
      {open ? (
        <div className="plan-agent-pane" role="complementary" aria-label="Agent Interaction drawer">
          <header className="plan-agent-pane-header">
            <div>
              <p className="plan-surface-kicker">Mock proof surface</p>
              <h2>Ingested corpus interaction proof</h2>
              <p>
                This local `/plan` pane consumes the future Agent Interaction contract before the
                global provider is built.
              </p>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close Agent Interaction drawer">
              Close
            </button>
          </header>

          {status === "loading" ? <p className="plan-agent-muted">Loading source bundle…</p> : null}
          {status === "error" ? (
            <p className="plan-agent-error">{error ?? "Unable to load source bundle."}</p>
          ) : null}
          {bundle ? (
            <div className="plan-agent-content">
              <form className="plan-agent-ask" onSubmit={submitQuestion}>
                <h3>Ask ingested corpus</h3>
                <p>
                  Ask first. Results show admitted campaign text, a preliminary sufficiency verdict,
                  and suggested source reads before advanced metadata.
                </p>
                <fieldset className="plan-agent-backend-picker">
                  <legend>Query backend</legend>
                  <label>
                    <input
                      type="radio"
                      name="plan-agent-query-backend"
                      value="live"
                      checked={queryBackend === "live"}
                      onChange={() => setQueryBackend("live")}
                    />
                    <span>Live loop</span>
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="plan-agent-query-backend"
                      value="hermes"
                      checked={queryBackend === "hermes"}
                      onChange={() => setQueryBackend("hermes")}
                    />
                    <span>Hermes tools</span>
                  </label>
                </fieldset>
                <label>
                  <span>Question</span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.currentTarget.value)}
                    placeholder="What changed after the latest ingested recap?"
                    rows={3}
                  />
                </label>
                <button type="submit" disabled={!question.trim() || askStatus === "asking"}>
                  {askStatus === "asking" ? "Asking…" : "Ask"}
                </button>
                {askStatus === "error" ? (
                  <p className="plan-agent-error">{askError ?? "Unable to ask corpus."}</p>
                ) : null}
                {answer && packetReview ? (
                  <div className="plan-agent-answer">
                    <ContextSufficiencyPanel review={packetReview} />
                    {answer.citations?.length ? (
                      <p className="plan-agent-muted plan-agent-citation-count">
                        Citations returned: {answer.citations.length}
                      </p>
                    ) : null}
                  </div>
                ) : answer ? (
                  <div className="plan-agent-answer">
                    <p className="plan-agent-muted">No context packet returned for this query.</p>
                    <p>{answer.answer}</p>
                  </div>
                ) : null}
              </form>

              <section className="plan-agent-proof" aria-label="Ingestion proof">
                <div>
                  <p className="plan-surface-kicker">Ingestion proof</p>
                  <h3>
                    {activeSessionComplete
                      ? `Session ${planView.session} has all expected ingest layers`
                      : `Session ${planView.session} is missing ${missingStages.length} ingest layers`}
                  </h3>
                  <p>
                    The bundle exposes {unitCount} SourceUnits across {artifactCount} artifacts.
                    Latest sessions visible in the scan:{" "}
                    {latestSessions.length ? latestSessions.join(", ") : "none"}.
                  </p>
                  {!activeSessionComplete ? (
                    <p className="plan-agent-warning">Missing: {missingStages.join(", ")}</p>
                  ) : null}
                </div>
                <div className="plan-agent-proof-pills">
                  {REQUIRED_INGEST_STAGES.map((stage) => (
                    <span key={stage} data-present={activeStageKinds.has(stage)}>
                      {stage.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </section>

              <details className="plan-agent-advanced">
                <summary>Advanced source metadata</summary>
                <div className="plan-agent-proof-grid">
                  <div className="plan-agent-stat">
                    <span>Ingest routes</span>
                    <strong>{routesOnDisk ?? "n/a"}</strong>
                  </div>
                  <div className="plan-agent-stat">
                    <span>Dogfood-full overlap</span>
                    <strong>{dogfoodRoutes ?? "n/a"}</strong>
                  </div>
                  <div className="plan-agent-stat">
                    <span>Slim overlap</span>
                    <strong>{slimRoutes ?? "n/a"}</strong>
                  </div>

                  <div className="plan-agent-units">
                    <h3>Representative SourceUnits</h3>
                    <ul>
                      {representativeUnits(bundle, planView.session).map((unit) => (
                        <li key={unit.unitId}>
                          <strong>{unit.label}</strong>
                          <span>
                            {sourceKind(unit)} · {unit.authorityState} · {unit.evidenceRole} ·{" "}
                            <code>{unit.sourceAnchor.locator.value}</code>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="plan-agent-diagnostics">
                    <h3>Diagnostics</h3>
                    <ul>
                      {bundle.diagnostics.map((diagnostic) => (
                        <li key={diagnostic}>{diagnostic}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </details>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="plan-agent-bar">
        <div>
          <p className="plan-surface-kicker">Agent Interaction</p>
          <strong>Plan context · ingested corpus proof</strong>
          <span>
            Placeholder bar for the future app-level pane. Current scope: `/plan` proof and ask
            dogfood.
          </span>
        </div>
        <button type="button" onClick={toggleDrawer} aria-expanded={open}>
          {open ? "Close drawer" : "Open drawer"}
        </button>
      </div>
    </section>
  );
}
