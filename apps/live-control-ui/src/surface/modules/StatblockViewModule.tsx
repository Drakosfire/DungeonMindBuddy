import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  getGeneratedStatblock,
  listGeneratedStatblocks,
} from "../../api/liveApi";
import { addGeneratedStatblockToEncounter, listWorldCombatEncounters } from "../../combat/combatApi";
import type {
  AddGeneratedStatblockRequest,
  AddGeneratedStatblockResponse,
  CombatEncounterRecord,
} from "../../combat/combatTypes";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import type {
  CombatTeam,
  GeneratedStatblockDetailResponse,
  GeneratedStatblockListItem,
  GeneratedStatblockListResponse,
  StatblockWorkbenchAction,
} from "../../api/types";

function formatMaybe(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

function retrievalLabel(status?: string | null): string {
  if (status === "retrieval_verified") {
    return "Retrieval verified";
  }
  if (status === "manifest_activated") {
    return "Retrieval activated";
  }
  return "Retrieval not activated";
}

function DisabledActions({ actions }: { actions: StatblockWorkbenchAction[] }) {
  const futureActions = actions.filter((action) => action.action_id !== "add_to_combat");
  if (futureActions.length === 0) {
    return null;
  }
  return (
    <div className="statblock-view-actions" aria-label="Future actions">
      {futureActions.map((action) => {
        const disabledReason = action.disabled_reason ?? "Future Statblock View workflow.";
        return (
          <button key={action.action_id} type="button" disabled title={disabledReason}>
            {action.label}
          </button>
        );
      })}
    </div>
  );
}

function StatblockList({
  statblocks,
  selectedId,
  onSelect,
}: {
  statblocks: GeneratedStatblockListItem[];
  selectedId: string | null;
  onSelect: (artifactId: string) => void;
}) {
  return (
    <ul className="statblock-view-list" aria-label="Generated statblocks">
      {statblocks.map((item) => (
        <li key={item.artifact_id}>
          <button
            type="button"
            className={item.artifact_id === selectedId ? "selected" : undefined}
            onClick={() => onSelect(item.artifact_id)}
          >
            <strong>{item.title}</strong>
            <span>AC {formatMaybe(item.armor_class)} · HP {formatMaybe(item.hit_points)} · CR {formatMaybe(item.challenge_rating)}</span>
            <span>{formatMaybe(item.creature_type)} · {retrievalLabel(item.retrieval_status)}</span>
            <span>{item.corpus_status} · warnings {item.warning_count}</span>
            <small>{item.corpus_display_path}</small>
            {item.primary_actions.length > 0 ? <small>Actions: {item.primary_actions.join(", ")}</small> : null}
          </button>
        </li>
      ))}
    </ul>
  );
}

function AddToCombatPanel({
  detail,
  worldId,
  encounterId,
  encounter,
  onAdded,
}: {
  detail: GeneratedStatblockDetailResponse;
  worldId: string;
  encounterId: string;
  encounter: CombatEncounterRecord | null;
  onAdded: (response: AddGeneratedStatblockResponse) => void;
}) {
  const [team, setTeam] = useState<CombatTeam>("enemy");
  const [count, setCount] = useState("1");
  const [initiative, setInitiative] = useState("");
  const [nameOverride, setNameOverride] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const targetGeneration = useRef(0);

  useLayoutEffect(() => {
    targetGeneration.current += 1;
    setError(null);
    setSuccess(null);
    setSubmitting(false);
    return () => {
      targetGeneration.current += 1;
    };
  }, [detail.artifact_id, encounterId, worldId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!encounter || encounter.encounter_id !== encounterId) {
      setError("Choose the encounter that should receive this statblock.");
      return;
    }
    const generation = targetGeneration.current;
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    const parsedCount = Number.parseInt(count, 10);
    const parsedInitiative = initiative.trim() === "" ? null : Number.parseInt(initiative, 10);
    const request: AddGeneratedStatblockRequest = {
      expected_revision: encounter.revision,
      team,
      count: Number.isFinite(parsedCount) ? parsedCount : 1,
    };
    if (parsedInitiative !== null && Number.isFinite(parsedInitiative)) {
      request.initiative = parsedInitiative;
    }
    if (nameOverride.trim()) {
      request.name_override = nameOverride.trim();
    }
    if (notes.trim()) {
      request.notes = notes.trim();
    }
    try {
      const response = await addGeneratedStatblockToEncounter(worldId, encounterId, detail.artifact_id, request);
      if (generation !== targetGeneration.current) return;
      const names = response.added_entities.map((entity) => entity.name).join(", ");
      setSuccess(`Added ${names} to ${response.encounter.draft.title}.`);
      onAdded(response);
    } catch (caught: unknown) {
      if (generation === targetGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === targetGeneration.current) setSubmitting(false);
    }
  }

  return (
    <section aria-label="Add to encounter">
      <h4>Add to encounter</h4>
      <form className="statblock-add-combat-form" onSubmit={submit}>
        <label>
          Team
          <select value={team} onChange={(event) => setTeam(event.target.value as CombatTeam)}>
            <option value="enemy">Enemy</option>
            <option value="ally">Ally</option>
            <option value="neutral">Neutral</option>
            <option value="pc">PC</option>
          </select>
        </label>
        <label>
          Count
          <input type="number" min="1" max="20" value={count} onChange={(event) => setCount(event.target.value)} />
        </label>
        <label>
          Initiative
          <input type="number" value={initiative} onChange={(event) => setInitiative(event.target.value)} placeholder="optional" />
        </label>
        <label>
          Name override
          <input value={nameOverride} onChange={(event) => setNameOverride(event.target.value)} placeholder={detail.combat_defaults.name ?? detail.title} />
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional combat notes" />
        </label>
        <button
          type="submit"
          disabled={submitting || !encounterId || !encounter}
        >
          {submitting ? "Adding…" : "Add to encounter"}
        </button>
      </form>
      {success ? <p className="module-success">{success}</p> : null}
      {error ? <p className="module-error">Unable to add to combat: {error}</p> : null}
    </section>
  );
}

function CurrentCombatReadback({ encounter }: { encounter: CombatEncounterRecord | null }) {
  if (!encounter) {
    return (
      <section aria-label="Selected encounter snapshot">
        <h4>Selected encounter snapshot</h4>
        <p className="module-muted">Choose the encounter that should receive this statblock.</p>
      </section>
    );
  }
  const recent = encounter.draft.entities.slice(-5);
  return (
    <section aria-label="Selected encounter snapshot">
      <h4>{encounter.draft.title}</h4>
      <p>Round {encounter.draft.round} · {encounter.draft.entities.length} combatant{encounter.draft.entities.length === 1 ? "" : "s"} · rev {encounter.revision}</p>
      {recent.length === 0 ? (
        <p className="module-muted">No combatants in this encounter yet.</p>
      ) : (
        <ul>
          {recent.map((entity) => (
            <li key={entity.id}>
              {entity.name} · {entity.team} · AC {formatMaybe(entity.ac)} · HP {formatMaybe(entity.hp)}/{formatMaybe(entity.max_hp)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Detail({
  detail,
  worldId,
  encounterId,
  encounter,
  onAdded,
}: {
  detail: GeneratedStatblockDetailResponse;
  worldId: string;
  encounterId: string;
  encounter: CombatEncounterRecord | null;
  onAdded: (response: AddGeneratedStatblockResponse) => void;
}) {
  const combat = detail.combat_defaults;
  const actions = detail.available_actions;
  return (
    <article className="statblock-view-detail">
      <header>
        <p className="eyebrow">Corpus-backed generated statblock</p>
        <h3>{detail.title}</h3>
        <p className="module-muted">{detail.corpus_display_path}</p>
      </header>

      <section aria-label="Status rail" className="statblock-view-status">
        <span>Corpus-backed ✅</span>
        <span>{retrievalLabel(String(detail.retrieval.status ?? ""))}</span>
        <span>Combat-ready ✅</span>
      </section>

      <AddToCombatPanel
        detail={detail}
        worldId={worldId}
        encounterId={encounterId}
        encounter={encounter}
        onAdded={onAdded}
      />
      <CurrentCombatReadback encounter={encounter} />

      <section aria-label="Combat summary">
        <h4>Combat summary</h4>
        <dl className="statblock-view-summary">
          <div><dt>AC</dt><dd>{formatMaybe(combat.armor_class)}</dd></div>
          <div><dt>HP</dt><dd>{formatMaybe(combat.hit_points)}</dd></div>
          <div><dt>Initiative</dt><dd>{formatMaybe(combat.initiative_bonus)}</dd></div>
          <div><dt>Speed</dt><dd>{formatMaybe(combat.speed_summary ?? combat.speed)}</dd></div>
          <div><dt>Senses</dt><dd>{formatMaybe(combat.senses_summary)}</dd></div>
        </dl>
        {combat.primary_actions?.length ? <p>Primary actions: {combat.primary_actions.join(", ")}</p> : null}
      </section>

      <section aria-label="Corpus markdown preview">
        <h4>Corpus markdown</h4>
        <pre className="statblock-view-markdown">{detail.corpus_markdown}</pre>
      </section>

      <section aria-label="Warnings needing DM review">
        <h4>Warnings needing DM review</h4>
        {detail.warnings.length === 0 ? (
          <p className="module-muted">No review warnings.</p>
        ) : (
          <ul>{detail.warnings.map((warning, index) => <li key={`${warning.code ?? "warning"}-${index}`}>{warning.message}</li>)}</ul>
        )}
      </section>

      <section aria-label="Retrieval status">
        <h4>Retrieval status</h4>
        <p>{retrievalLabel(String(detail.retrieval.status ?? ""))}</p>
        <p className="module-muted">Verified at: {formatMaybe(detail.retrieval.verified_at)}</p>
        <p className="module-muted">Evidence: {formatMaybe(detail.retrieval.evidence_path)}</p>
      </section>

      <section aria-label="Provenance and breadcrumbs">
        <h4>Provenance / source refs / breadcrumbs</h4>
        <p>Source refs: {detail.source_refs.length}</p>
        <p>Breadcrumbs: {detail.breadcrumbs.map((crumb) => crumb.label).join(" → ") || "—"}</p>
        <p className="module-muted">Fingerprint: {formatMaybe(detail.corpus_file_fingerprint)}</p>
      </section>

      <section aria-label="Disabled future actions">
        <h4>Future actions</h4>
        <DisabledActions actions={actions} />
      </section>
    </article>
  );
}

export function StatblockViewModule() {
  const selectedWorld = useSelectedWorld();
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [list, setList] = useState<GeneratedStatblockListResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GeneratedStatblockDetailResponse | null>(null);
  const [encounters, setEncounters] = useState<CombatEncounterRecord[]>([]);
  const [selectedEncounterId, setSelectedEncounterId] = useState("");
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [encounterError, setEncounterError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingList(true);
    listGeneratedStatblocks()
      .then((response) => {
        if (cancelled) return;
        setList(response);
        setSelectedId(response.statblocks[0]?.artifact_id ?? null);
        setListError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setListError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setEncounters([]);
    setSelectedEncounterId("");
    setEncounterError(null);
    if (!worldId) return () => { cancelled = true; };
    listWorldCombatEncounters(worldId)
      .then((response) => { if (!cancelled) setEncounters(response); })
      .catch((error: unknown) => {
        if (!cancelled) setEncounterError(error instanceof Error ? error.message : String(error));
      });
    return () => { cancelled = true; };
  }, [worldId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    setDetailError(null);
    getGeneratedStatblock(selectedId)
      .then((response) => {
        if (!cancelled) setDetail(response);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDetail(null);
          setDetailError(error instanceof Error ? error.message : String(error));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const statblocks = useMemo(() => list?.statblocks ?? [], [list]);
  const selectedEncounter = encounters.find((item) => item.encounter_id === selectedEncounterId) ?? null;
  const worldMessage = selectedWorld.kind === "loading"
    ? "Verifying selected World…"
    : selectedWorld.kind === "error"
      ? selectedWorld.message
      : selectedWorld.kind === "legacy"
        ? "Choose a verified World before adding a statblock to Combat."
        : null;

  return (
    <div className="module-panel statblock-view" data-module-id="statblock_view">
      <header className="statblock-view-header">
        <p className="eyebrow">Combat consumer surface</p>
        <h2 className="module-title">Statblock View</h2>
        <p className="module-muted">Browse generated statblocks, choose a saved encounter, and add the exact statblock revision there.</p>
      </header>

      {worldMessage ? <p className="module-muted">{worldMessage}</p> : null}
      {loadingList ? <p className="module-muted">Loading generated statblocks…</p> : null}
      {listError ? <p className="module-error">Unable to load generated statblocks: {listError}</p> : null}
      {encounterError ? <p className="module-error">Unable to load World encounters: {encounterError}</p> : null}
      {worldId ? (
        <label>
          Encounter to receive statblock
          <select
            aria-label="Encounter to receive statblock"
            value={selectedEncounterId}
            onChange={(event) => setSelectedEncounterId(event.target.value)}
          >
            <option value="">Choose a saved encounter…</option>
            {encounters.map((encounter) => (
              <option key={encounter.encounter_id} value={encounter.encounter_id}>
                {encounter.draft.title} · rev {encounter.revision}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {list?.diagnostics.length ? <ul className="module-muted">{list.diagnostics.map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)}</ul> : null}
      {!loadingList && !listError && statblocks.length === 0 ? <p className="module-muted">No corpus-backed generated statblocks yet.</p> : null}

      {statblocks.length > 0 ? (
        <div className="statblock-view-grid">
          <StatblockList statblocks={statblocks} selectedId={selectedId} onSelect={setSelectedId} />
          <div>
            {loadingDetail ? <p className="module-muted">Loading selected statblock…</p> : null}
            {detailError ? <p className="module-error">Unable to load selected statblock: {detailError}</p> : null}
            {!loadingDetail && !detailError && detail ? (
              <Detail
                detail={detail}
                worldId={worldId ?? ""}
                encounterId={selectedEncounterId}
                encounter={selectedEncounter}
                onAdded={(response) => {
                  setEncounters((current) => [response.encounter, ...current.filter((item) => item.encounter_id !== response.encounter.encounter_id)]);
                  setEncounterError(null);
                }}
              />
            ) : null}
            {!loadingDetail && !detailError && !detail ? <p className="module-muted">Select a statblock.</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
