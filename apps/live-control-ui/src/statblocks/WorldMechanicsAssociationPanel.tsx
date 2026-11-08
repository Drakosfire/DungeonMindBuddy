import {worldCreatureChoiceKey} from '../api/worldMechanicsTypes';
import { useEffect, useRef, useState } from "react";
import {
  associateWorldMechanics, listWorldMechanicsAssociations,
  listWorldCreatures, LiveApiError,
} from "../api/liveApi";
import type { ThreatDraftV2 } from "../api/types";
import type {
  AssociateWorldMechanicsRequest, WorldMechanicsAssociation, WorldCreatureCatalog,
} from "../api/worldMechanicsTypes";

async function pendingStorage<T>(key: string, live: () => boolean, action: () => T): Promise<T> {
  if (!navigator.locks) throw new Error("This browser cannot safely retain associations across tabs.");
  return navigator.locks.request(key, () => {
    if (!live()) throw new Error("Association view is no longer active.");
    return action();
  });
}

/** Explicit association action, shared by every host of the statblock workbench. */
export function WorldMechanicsAssociationPanel({ draft }: { draft: ThreatDraftV2 }) {
  return <AssociationPanel key={JSON.stringify([draft.world_id,draft.draft_id])} draft={draft}/>;
}
function AssociationPanel({ draft }: { draft: ThreatDraftV2 }) {
  const key = `dmb.worldMechanics.pending:${draft.world_id}:${draft.draft_id}`;
  const [initial] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return { pending: null, error: null };
      const request = JSON.parse(raw) as AssociateWorldMechanicsRequest;
      if (request.draft_id !== draft.draft_id || request.target?.managed_world_id !== draft.world_id
          || typeof request.request_id !== "string") throw new Error("Stored association scope is invalid");
      return { pending: request, error: null };
    } catch (error) { return { pending: null, error: String(error) }; }
  });
  const [pending, setPending] = useState<AssociateWorldMechanicsRequest | null>(initial.pending);
  const [error, setError] = useState<string | null>(initial.error);
  const [view, setView] = useState<WorldCreatureCatalog | null>(null);
  const [current, setCurrent] = useState<WorldMechanicsAssociation[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [saved, setSaved] = useState<WorldMechanicsAssociation | null>(null);
  const [savedReplay, setSavedReplay] = useState(false);
  const live = useRef(true);
  const flight = useRef(false);
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  const nodes = view?.targets ?? [];
  const selectedTarget = nodes.find(node => worldCreatureChoiceKey(node) === selected);
  const previous = current.find(record => record.request.target.node_id === selectedTarget?.node_id);

  async function load() {
    if (flight.current || pending) return;
    flight.current = true; setBusy(true); setError(null); setView(null); setSelected("");
    try {
      const [projection, associations] = await Promise.all([
        listWorldCreatures(draft.world_id),
        listWorldMechanicsAssociations(draft.world_id),
      ]);
      if (associations.some(record => record.request.target.managed_world_id !== draft.world_id)) {
        throw new Error("Association records belong to a different World");
      }
      if (live.current) { setView(projection); setCurrent(associations); }
    } catch (e) { if (live.current) setError(String(e)); }
    finally { flight.current = false; if (live.current) setBusy(false); }
  }

  async function submit(request: AssociateWorldMechanicsRequest) {
    if (flight.current) return;
    flight.current = true; setBusy(true); setError(null);
    try {
      // Reserve before POST without overwriting another view's recovery request.
      await pendingStorage(key, () => live.current, () => {
        const stored = localStorage.getItem(key);
        if (stored !== null && stored !== JSON.stringify(request)) {
          throw new Error("Another view retained an association request. Reload to recover it before continuing.");
        }
        localStorage.setItem(key, JSON.stringify(request));
      });
      if (!live.current) return;
      setPending(request);
      const response = await associateWorldMechanics(draft.world_id, request);
      const actual = response.association.request;
      const locator = response.association.proof.locator;
      const accepted = draft.accepted_mechanics_ref;
      const locatorFields = ["provider", "statblock_id", "revision_id", "contract", "contract_version", "definition_digest"] as const;
      if (actual.request_id !== request.request_id || actual.draft_id !== request.draft_id
          || actual.expected_draft_version !== request.expected_draft_version
          || actual.expected_version !== request.expected_version
          || response.association.version !== request.expected_version + 1
          || !Object.entries(request.target).every(([field, value]) => actual.target[field as keyof typeof actual.target] === value)
          || !accepted || !locatorFields.every(field => locator[field] === accepted[field])
          || Object.keys(locator).length !== 6) {
        throw new Error("Association response did not match the saved request; resume to verify");
      }
      await clearPending(request);
      if (!live.current) return;
      setSaved(response.association); setSavedReplay(response.replayed);
      if (response.replayed) {
        // A recovered historical acknowledgement is not current-slot authority.
        setCurrent([]); setView(null); setSelected("");
      } else {
        setCurrent(old => [...old.filter(r => r.request.target.node_id !== request.target.node_id), response.association]);
      }
      setPending(null); setConflict(false);
    } catch (e) {
      if (live.current) {
        setError(String(e));
        setConflict(e instanceof LiveApiError && e.status === 409);
      }
    } finally { flight.current = false; if (live.current) setBusy(false); }
  }

  async function clearPending(request: AssociateWorldMechanicsRequest) {
    await pendingStorage(key, () => live.current, () => {
      const stored = localStorage.getItem(key);
      if (stored !== null && stored !== JSON.stringify(request)) {
        throw new Error("Another view retained an association request. Reload to recover it before continuing.");
      }
      if (stored !== null) localStorage.removeItem(key);
    });
  }

  async function refreshAfterConflict() {
    if (flight.current || !pending) return;
    flight.current = true; setBusy(true);
    try {
      await clearPending(pending);
      if (!live.current) return;
      setPending(null); setConflict(false); setView(null); setSelected(""); setError(null);
    } catch (e) { if (live.current) setError(String(e)); }
    finally { flight.current = false; if (live.current) setBusy(false); }
  }

  function start() {
    const node = selectedTarget;
    if (!view || !node || initial.error) return;
    void submit({
      request_id: crypto.randomUUID(), draft_id: draft.draft_id,
      expected_draft_version: draft.version, expected_version: previous?.version ?? 0,
      target: {...node},
    });
  }

  return <section className="statblock-section" aria-label="Associate World creature">
    <h3>Associate saved mechanics with a World creature</h3>
    <p>Uses the accepted mechanics saved for this draft. Choose an existing creature explicitly; its World facts stay unchanged.</p>
    <button type="button" onClick={() => void load()} disabled={busy || !!pending || !!initial.error}>
      {view ? "Refresh creatures" : "Load creatures"}
    </button>
    {view ? <>
      {view.completeness === "partial" && <p>Some creature records are unavailable in this view.</p>}
      <label>World creature
        <select aria-label="World creature" value={selected} onChange={e => setSelected(e.target.value)} disabled={busy || !!pending}>
          <option value="">Choose a creature</option>
          {nodes.map(node => <option key={worldCreatureChoiceKey(node)} value={worldCreatureChoiceKey(node)}>
            {node.label} · {node.kind}{node.campaign_scope ? ` · ${node.campaign_scope}` : ""} · {node.node_id}
          </option>)}
        </select>
      </label>
      {nodes.length === 0 ? <p>No selectable creatures are available in this view.</p> : null}
      {previous ? <p>This creature already has associated mechanics. Replacing them keeps the previous association in history.</p> : null}
      <button type="button" onClick={start} disabled={!selected || busy || !!pending || !!initial.error}>
        {previous ? "Replace creature mechanics" : "Associate creature mechanics"}
      </button>
      {current.filter(r => r.request.draft_id === draft.draft_id).map(record => <p key={record.association_id}>
        Saved association: {record.request.target.label} · version {record.version}
      </p>)}
    </> : null}
    {pending ? <>
      <p>The exact association request is retained. Resume it to check the outcome.</p>
      <button type="button" disabled={busy || !!initial.error} onClick={() => void submit(pending)}>Resume same association</button>
      {conflict ? <button type="button" disabled={busy} onClick={() => void refreshAfterConflict()}>Refresh after conflict</button> : null}
    </> : null}
    {saved ? <p role="status">{savedReplay
      ? `Association receipt recovered for ${saved.request.target.label}. Load creatures to check the current association.`
      : `Mechanics associated with ${saved.request.target.label}. Existing encounters are unchanged.`}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
