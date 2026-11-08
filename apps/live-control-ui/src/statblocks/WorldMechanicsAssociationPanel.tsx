import {worldCreatureChoiceKey} from '../api/worldMechanicsTypes';
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  associateWorldMechanics, listWorldMechanicsAssociations,
  listWorldCreatures, getThreatDraft, findWorldMechanicsAssociationRequest, LiveApiError,
} from "../api/liveApi";
import type { ThreatDraftV2 } from "../api/types";
import type {
  AssociateWorldMechanicsRequest, HistoricalAssociateWorldMechanicsRequest, SavedMechanicsLocator, WorldMechanicsAssociation, WorldCreatureCatalog,
} from "../api/worldMechanicsTypes";

async function pendingStorage<T>(key: string, live: () => boolean, action: () => T): Promise<T> {
  if (!navigator.locks) throw new Error("This browser cannot safely retain associations across tabs.");
  return navigator.locks.request(key, () => {
    if (!live()) throw new Error("Association view is no longer active.");
    return action();
  });
}

type Props={worldId:string;draftId:string;locator:SavedMechanicsLocator;disabledReason?:string|null;onBusyChange?:(busy:boolean)=>void};
type RetainedRequest=AssociateWorldMechanicsRequest|HistoricalAssociateWorldMechanicsRequest;
const explicit=(request:RetainedRequest):request is AssociateWorldMechanicsRequest=>'locator' in request;
function sameJSON(a:unknown,b:unknown):boolean {
  if(a===b)return true;
  if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)||Array.isArray(b))return false;
  const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&sameJSON((a as Record<string,unknown>)[k],(b as Record<string,unknown>)[k]));
}
/** The same saved editor supplies identity to every association entry point. */
export function WorldMechanicsAssociationPanel(props:Props) {
  return <AssociationPanel key={JSON.stringify([props.worldId,props.draftId,props.locator])} {...props}/>;
}
function AssociationPanel({worldId,draftId,locator,disabledReason,onBusyChange}:Props) {
  const [draft,setDraft]=useState<ThreatDraftV2|null>(null);
  const key = `dmb.worldMechanics.pending:${worldId}:${draftId}`;
  const [initial] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return { pending: null, error: null };
      const request = JSON.parse(raw) as RetainedRequest;
      if (request.draft_id !== draftId || request.target?.managed_world_id !== worldId
          || typeof request.request_id !== "string") throw new Error("Stored association scope is invalid");
      return { pending: request, error: null };
    } catch (error) { return { pending: null, error: String(error) }; }
  });
  const [pending, setPending] = useState<RetainedRequest | null>(initial.pending);
  const [error, setError] = useState<string | null>(initial.error);
  const [view, setView] = useState<WorldCreatureCatalog | null>(null);
  const [current, setCurrent] = useState<WorldMechanicsAssociation[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [historicalMissing,setHistoricalMissing]=useState(false);
  const [conflict, setConflict] = useState(false);
  const [saved, setSaved] = useState<WorldMechanicsAssociation | null>(null);
  const [savedReplay, setSavedReplay] = useState(false);
  const live = useRef(true);
  const flight = useRef(false);
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  useLayoutEffect(()=>{onBusyChange?.(busy);return ()=>onBusyChange?.(false);},[busy,onBusyChange]);
  const nodes = view?.targets ?? [];
  const selectedTarget = nodes.find(node => worldCreatureChoiceKey(node) === selected);
  const previous = current.find(record => record.request.target.node_id === selectedTarget?.node_id);

  async function load() {
    if (flight.current || pending || disabledReason) return;
    flight.current = true; setBusy(true); setError(null); setView(null); setSelected("");
    try {
      const [projection, associations, currentDraft] = await Promise.all([
        listWorldCreatures(worldId),
        listWorldMechanicsAssociations(worldId),
        getThreatDraft(draftId),
      ]);
      if(currentDraft.schema!=="dmb_threat_draft_v2"||currentDraft.world_id!==worldId||currentDraft.draft_id!==draftId
        ||currentDraft.workflow_state!=="mechanics_saved"||!currentDraft.accepted_mechanics_ref)throw new Error("Saved draft belongs to another World or is unavailable.");
      if (associations.some(record => record.request.target.managed_world_id !== worldId)) {
        throw new Error("Association records belong to a different World");
      }
      if (live.current) { setView(projection); setCurrent(associations);setDraft(currentDraft); }
    } catch (e) { if (live.current) setError(String(e)); }
    finally { flight.current = false; if (live.current) setBusy(false); }
  }

  async function submit(request: AssociateWorldMechanicsRequest) {
    if (flight.current || disabledReason) return;
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
      const response = await associateWorldMechanics(worldId, request);
      const actual=response.association.request;
      if(!sameJSON(actual,request)||response.association.version!==request.expected_version+1
        ||!sameJSON(response.association.proof.locator,request.locator)) {
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

  async function clearPending(request: RetainedRequest) {
    await pendingStorage(key, () => live.current, () => {
      const stored = localStorage.getItem(key);
      if (stored !== null && stored !== JSON.stringify(request)) {
        throw new Error("Another view retained an association request. Reload to recover it before continuing.");
      }
      if (stored !== null) localStorage.removeItem(key);
    });
  }

  async function recoverHistorical() {
    if(flight.current||!pending||explicit(pending)||disabledReason)return;
    flight.current=true;setBusy(true);setError(null);setHistoricalMissing(false);
    try {
      const record=await findWorldMechanicsAssociationRequest(worldId,pending.request_id);
      if(!live.current)return;
      if(record===null){setHistoricalMissing(true);return;}
      if(!sameJSON(record.request,pending)||record.request.target.managed_world_id!==worldId
        ||record.version!==pending.expected_version+1)throw new Error("Historical acknowledgement differs from the retained request.");
      await clearPending(pending);
      if(live.current){setSaved(record);setSavedReplay(true);setPending(null);setCurrent([]);setView(null);setSelected("");}
    }catch(e){if(live.current)setError(String(e));}
    finally{flight.current=false;if(live.current)setBusy(false);}
  }

  async function refreshAfterConflict() {
    if (flight.current || !pending || disabledReason) return;
    flight.current = true; setBusy(true);
    try {
      await clearPending(pending);
      if (!live.current) return;
      setPending(null);setHistoricalMissing(false); setConflict(false); setView(null); setSelected(""); setError(null);
    } catch (e) { if (live.current) setError(String(e)); }
    finally { flight.current = false; if (live.current) setBusy(false); }
  }

  function start() {
    const node = selectedTarget;
    if (!view || !node || !draft || initial.error || disabledReason) return;
    void submit({
      request_id: crypto.randomUUID(), draft_id: draftId,
      locator, expected_draft_version: draft.version, expected_version: previous?.version ?? 0,
      target: {...node},
    });
  }

  return <section className="statblock-section" aria-label="Associate World creature">
    <h3>Associate saved mechanics with a World creature</h3>
    <p>Links the displayed saved version to an explicitly selected creature. World facts and existing encounters stay unchanged.</p>
    <button type="button" onClick={() => void load()} disabled={!!disabledReason || busy || !!pending || !!initial.error}>
      {view ? "Refresh creatures" : "Load creatures"}
    </button>
    {view ? <>
      {view.completeness === "partial" && <p>Some creature records are unavailable in this view.</p>}
      <label>World creature
        <select aria-label="World creature" value={selected} onChange={e => setSelected(e.target.value)} disabled={!!disabledReason || busy || !!pending}>
          <option value="">Choose a creature</option>
          {nodes.map(node => <option key={worldCreatureChoiceKey(node)} value={worldCreatureChoiceKey(node)}>
            {node.label} · {node.kind}{node.campaign_scope ? ` · ${node.campaign_scope}` : ""} · {node.node_id}
          </option>)}
        </select>
      </label>
      {nodes.length === 0 ? <p>No selectable creatures are available in this view.</p> : null}
      {previous ? <p>This creature already has associated mechanics. Replacing them keeps the previous association in history.</p> : null}
      <button type="button" onClick={start} disabled={!!disabledReason || !selected || busy || !!pending || !!initial.error}>
        {previous ? "Replace creature mechanics" : "Associate creature mechanics"}
      </button>
      {current.filter(r => r.request.draft_id === draftId).map(record => <p key={record.association_id}>
        Saved association: {record.request.target.label} · version {record.version}
      </p>)}
    </> : null}
    {pending ? <>
      <p>{explicit(pending)?`Association for saved version ${pending.locator.revision_id} is retained. Resume this exact request to check its outcome.`:"An earlier association request is retained. Check its saved acknowledgement before starting another."}</p>
      {explicit(pending)
        ?<button type="button" disabled={!!disabledReason||busy||!!initial.error} onClick={()=>void submit(pending)}>Resume same association</button>
        :<button type="button" disabled={!!disabledReason||busy||!!initial.error} onClick={()=>void recoverHistorical()}>Check earlier association</button>}
      {historicalMissing&&<><p>No saved acknowledgement exists for this earlier request. It cannot be submitted by the current writer.</p><button type="button" disabled={!!disabledReason||busy} onClick={()=>void refreshAfterConflict()}>Release earlier request</button></>}
      {conflict ? <button type="button" disabled={!!disabledReason || busy} onClick={() => void refreshAfterConflict()}>Refresh after conflict</button> : null}
    </> : null}
    {saved ? <p role="status">{savedReplay
      ? `Association receipt recovered for ${saved.request.target.label}. Load creatures to check the current association.`
      : `Mechanics associated with ${saved.request.target.label}. Existing encounters are unchanged.`}</p> : null}
    {disabledReason&&<p>{disabledReason}</p>}
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
