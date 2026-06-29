import { useCallback, useEffect, useMemo, useState } from "react";

import {
  commitPartyRegistrySessionRosterWrite,
  getPartyRegistry,
  preparePartyRegistrySessionRosterWrite,
} from "../api/liveApi";
import type {
  PartyRegistrySessionRosterWritePrepareResponse,
  PartyRegistrySurfaceResponse,
} from "../api/types";
import type { PlanContextDescriptor } from "../planSurface/types";

interface PartyRegistryModuleProps {
  context: PlanContextDescriptor;
}

function requestedSessionFromLocation(): number | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("session")?.trim();
  const match = raw?.match(/^session-(\d+)$/i);
  if (!match) return null;
  const session = Number.parseInt(match[1], 10);
  return Number.isFinite(session) && session > 0 ? session : null;
}

function sessionIdFromNumber(session: number): string {
  return `session-${session}`;
}

function slugsToText(slugs: string[]): string {
  return slugs.join("\n");
}

function textToSlugs(text: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of text.split(/[\n,]+/)) {
    const slug = raw.trim();
    if (!slug || seen.has(slug)) continue;
    seen.add(slug);
    out.push(slug);
  }
  return out;
}

function sortedSessionKeys(keys: string[]): number[] {
  return [...keys]
    .map((key) => Number.parseInt(key, 10))
    .filter((value) => Number.isFinite(value) && value > 0)
    .sort((a, b) => a - b);
}

function addSlugToText(current: string, slug: string): string {
  const slugs = textToSlugs(current);
  if (slugs.includes(slug)) return current;
  return slugsToText([...slugs, slug]);
}

export function PartyRegistryModule({ context }: PartyRegistryModuleProps) {
  const defaultSession = requestedSessionFromLocation() ?? context.ingestSession;
  const [session, setSession] = useState(defaultSession);
  const [payload, setPayload] = useState<PartyRegistrySurfaceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [draftPcText, setDraftPcText] = useState("");
  const [draftCompanionText, setDraftCompanionText] = useState("");
  const [draftDirty, setDraftDirty] = useState(false);
  const [newSessionInput, setNewSessionInput] = useState("");
  const [copyFromSession, setCopyFromSession] = useState<number | "">("");
  const [writePrepare, setWritePrepare] = useState<PartyRegistrySessionRosterWritePrepareResponse | null>(
    null,
  );
  const [showWriteConfirm, setShowWriteConfirm] = useState(false);
  const [writeError, setWriteError] = useState<string | null>(null);
  const [writePending, setWritePending] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const loadRegistry = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPartyRegistry(context.campaignId, session);
      setPayload(response);
      if (!draftDirty) {
        setDraftPcText(slugsToText(response.pc_slugs));
        setDraftCompanionText(slugsToText(response.companion_slugs));
      }
    } catch (err: unknown) {
      setPayload(null);
      setError(err instanceof Error ? err.message : "Failed to load party registry");
    } finally {
      setLoading(false);
    }
  }, [context.campaignId, draftDirty, session]);

  useEffect(() => {
    void loadRegistry();
  }, [loadRegistry, reloadToken]);

  const rosterSessions = useMemo(
    () => sortedSessionKeys(payload?.available_session_keys ?? []),
    [payload?.available_session_keys],
  );

  const draftPcSlugs = useMemo(() => textToSlugs(draftPcText), [draftPcText]);
  const draftCompanionSlugs = useMemo(() => textToSlugs(draftCompanionText), [draftCompanionText]);

  const beginEditSession = (nextSession: number, options?: { copyFrom?: number }) => {
    setSession(nextSession);
    setDraftDirty(false);
    setWritePrepare(null);
    setShowWriteConfirm(false);
    setWriteError(null);
    if (options?.copyFrom != null && payload) {
      const sourceKey = String(options.copyFrom);
      const roster = payload.registry_summary.session_rosters as Record<
        string,
        { pcs?: string[]; companions?: string[] }
      >;
      const source = roster?.[sourceKey];
      setDraftPcText(slugsToText(source?.pcs ?? []));
      setDraftCompanionText(slugsToText(source?.companions ?? []));
      setDraftDirty(true);
    }
  };

  const handleAddSession = () => {
    const next = Number.parseInt(newSessionInput, 10);
    if (!Number.isFinite(next) || next <= 0) {
      setWriteError("Enter a valid session number to add.");
      return;
    }
    if (rosterSessions.includes(next)) {
      setWriteError(`Session ${next} already exists in the registry. Select it from the dropdown.`);
      return;
    }
    beginEditSession(next, {
      copyFrom: copyFromSession === "" ? undefined : copyFromSession,
    });
    setNewSessionInput("");
    setWriteError(null);
  };

  const handlePrepareSave = async () => {
    setWritePending(true);
    setWriteError(null);
    try {
      const prepare = await preparePartyRegistrySessionRosterWrite({
        campaign_id: context.campaignId,
        session,
        pc_slugs: draftPcSlugs,
        companion_slugs: draftCompanionSlugs,
      });
      setWritePrepare(prepare);
      setDraftPcText(slugsToText(prepare.pc_slugs));
      setDraftCompanionText(slugsToText(prepare.companion_slugs));
      setShowWriteConfirm(true);
    } catch (err: unknown) {
      setWriteError(err instanceof Error ? err.message : "Prepare failed");
    } finally {
      setWritePending(false);
    }
  };

  const handleCommitSave = async () => {
    if (!writePrepare?.writer_confirm_token) return;
    setWritePending(true);
    setWriteError(null);
    try {
      await commitPartyRegistrySessionRosterWrite({
        campaign_id: context.campaignId,
        session,
        pc_slugs: writePrepare.pc_slugs,
        companion_slugs: writePrepare.companion_slugs,
        writer_confirm_token: writePrepare.writer_confirm_token,
      });
      setWritePrepare(null);
      setShowWriteConfirm(false);
      setDraftDirty(false);
      setReloadToken((value) => value + 1);
    } catch (err: unknown) {
      setWriteError(err instanceof Error ? err.message : "Commit failed");
    } finally {
      setWritePending(false);
    }
  };

  if (loading && !payload) {
    return <p className="plan-projection-empty">Loading party registry…</p>;
  }

  if (error && !payload) {
    return <p className="plan-projection-empty">Party registry error: {error}</p>;
  }

  if (!payload) {
    return <p className="plan-projection-empty">No party registry data.</p>;
  }

  const pcMembers = payload.members.filter((member) => member.kind === "pc");
  const companionMembers = payload.members.filter((member) => member.kind === "companion");

  return (
    <div className="party-registry-module" data-testid="party-registry-module">
      <header className="ingestion-module-header">
        <div>
          <p className="plan-surface-kicker">Campaign context</p>
          <h3>Party Registry</h3>
        </div>
        <label className="party-registry-session-select">
          Session roster
          <select
            aria-label="Party registry session roster"
            value={rosterSessions.includes(session) ? String(session) : ""}
            onChange={(event) => {
              const next = Number.parseInt(event.target.value, 10);
              if (Number.isFinite(next) && next > 0) {
                beginEditSession(next);
              }
            }}
          >
            <option value="" disabled={rosterSessions.includes(session)}>
              {rosterSessions.includes(session) ? "Select session…" : `Session ${session} (unsaved draft)`}
            </option>
            {rosterSessions.map((key) => (
              <option key={key} value={String(key)}>
                Session {key}
              </option>
            ))}
          </select>
        </label>
      </header>

      <section className="ingestion-flow-card">
        <p className="ingestion-flow-kicker">Add session roster</p>
        <div className="party-registry-add-session">
          <label>
            New session
            <input
              type="number"
              min={1}
              value={newSessionInput}
              aria-label="New session number"
              onChange={(event) => setNewSessionInput(event.target.value)}
            />
          </label>
          <label>
            Copy roster from
            <select
              aria-label="Copy roster from session"
              value={copyFromSession === "" ? "" : String(copyFromSession)}
              onChange={(event) => {
                const raw = event.target.value;
                setCopyFromSession(raw ? Number.parseInt(raw, 10) : "");
              }}
            >
              <option value="">Empty roster</option>
              {rosterSessions.map((key) => (
                <option key={key} value={String(key)}>
                  Session {key}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={handleAddSession}>
            Add &amp; edit
          </button>
        </div>
      </section>

      <section className="ingestion-flow-card">
        <p className="ingestion-flow-kicker">Edit session {session} roster</p>
        {!payload.has_session_roster ? (
          <p className="plan-content-note">
            No roster on file for session {session}. Add slugs below or copy from a prior session, then save.
          </p>
        ) : null}
        <label className="party-registry-slug-editor">
          PC slugs
          <textarea
            rows={6}
            aria-label="PC slugs"
            value={draftPcText}
            onChange={(event) => {
              setDraftPcText(event.target.value);
              setDraftDirty(true);
              setWritePrepare(null);
              setShowWriteConfirm(false);
            }}
          />
        </label>
        <div className="party-registry-known-slugs">
          {payload.known_pc_slugs.map((slug) => (
            <button
              key={slug}
              type="button"
              className="party-registry-slug-chip"
              onClick={() => {
                setDraftPcText((current) => addSlugToText(current, slug));
                setDraftDirty(true);
                setWritePrepare(null);
                setShowWriteConfirm(false);
              }}
            >
              + {slug}
            </button>
          ))}
        </div>
        <label className="party-registry-slug-editor">
          Companion NPC slugs
          <textarea
            rows={4}
            aria-label="Companion NPC slugs"
            value={draftCompanionText}
            onChange={(event) => {
              setDraftCompanionText(event.target.value);
              setDraftDirty(true);
              setWritePrepare(null);
              setShowWriteConfirm(false);
            }}
          />
        </label>
        <div className="party-registry-known-slugs">
          {payload.known_companion_slugs.map((slug) => (
            <button
              key={slug}
              type="button"
              className="party-registry-slug-chip"
              onClick={() => {
                setDraftCompanionText((current) => addSlugToText(current, slug));
                setDraftDirty(true);
                setWritePrepare(null);
                setShowWriteConfirm(false);
              }}
            >
              + {slug}
            </button>
          ))}
        </div>
        <div className="party-registry-save-actions">
          <button type="button" disabled={writePending} onClick={() => void handlePrepareSave()}>
            {writePending ? "Preparing…" : "Save roster"}
          </button>
          {showWriteConfirm && writePrepare ? (
            <>
              <button type="button" disabled={writePending} onClick={() => void handleCommitSave()}>
                Confirm save
              </button>
              <button
                type="button"
                disabled={writePending}
                onClick={() => {
                  setShowWriteConfirm(false);
                  setWritePrepare(null);
                }}
              >
                Cancel
              </button>
            </>
          ) : null}
        </div>
        {writeError ? <p className="plan-projection-empty">{writeError}</p> : null}
        {writePrepare?.writer_diff ? (
          <pre className="party-registry-context-preview" data-testid="party-registry-write-diff">
            {writePrepare.writer_diff}
          </pre>
        ) : null}
      </section>

      <section className="ingestion-flow-card">
        <p className="ingestion-flow-kicker">Registry summary</p>
        <dl className="plan-content-fields">
          <div>
            <dt>Campaign</dt>
            <dd>{payload.campaign_id}</dd>
          </div>
          <div>
            <dt>Session</dt>
            <dd>{sessionIdFromNumber(payload.session)}</dd>
          </div>
          <div>
            <dt>Party names</dt>
            <dd>{payload.party_names.join(", ") || "—"}</dd>
          </div>
          <div>
            <dt>Registry path</dt>
            <dd>
              <code>{payload.registry_relpath ?? "—"}</code>
            </dd>
          </div>
          <div>
            <dt>Roster sessions on file</dt>
            <dd>{payload.available_session_keys.join(", ") || "—"}</dd>
          </div>
        </dl>
      </section>

      {payload.warnings.length > 0 ? (
        <section className="ingestion-toast ingestion-toast-warning" aria-label="Registry warnings">
          <p className="ingestion-toast-header">
            <strong>Warnings</strong>
          </p>
          <ul>
            {payload.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="ingestion-flow-card">
        <p className="ingestion-flow-kicker">Resolved members (session {session})</p>
        {pcMembers.length === 0 && companionMembers.length === 0 ? (
          <p className="plan-projection-empty">No resolved members for this session yet.</p>
        ) : (
          <ul className="party-registry-member-list">
            {pcMembers.map((member) => (
              <li key={member.slug}>
                <strong>{member.display_name}</strong> ({member.slug})
                {member.player ? ` · player ${member.player}` : ""}
                <br />
                <code>{member.hub_rel_path}</code>
              </li>
            ))}
            {companionMembers.map((member) => (
              <li key={member.slug}>
                <strong>{member.display_name}</strong> ({member.slug})
                <br />
                <code>{member.hub_rel_path}</code>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="ingestion-flow-card">
        <p className="ingestion-flow-kicker">Session Graph Context Preview</p>
        <p className="plan-content-note">
          Graph ingest receives this deterministic anchor set after the roster is saved.
        </p>
        <pre className="party-registry-context-preview" data-testid="session-graph-context-preview">
          {JSON.stringify(payload.session_graph_context, null, 2)}
        </pre>
      </section>
    </div>
  );
}
