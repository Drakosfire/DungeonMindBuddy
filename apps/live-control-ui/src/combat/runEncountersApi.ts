import {authenticatedApiFetch} from '../api/liveApi';
import type {WorldPlayRunRecordV2,PlayRunReferenceManifest} from '../api/types';
import type {CombatEncounterRecord} from './combatTypes';
import {exactIntent} from './exactIntent';

export type TemplatePin={encounter_id:string;revision:number;digest:string};
export type RunEncounterScope={runId:string;sceneId:string};
export type SessionSource={playable_artifact_id:string;expected_playable_revision:number;expected_playable_work_revision_id:string;expected_playable_content_sha256:string};
export type WorldSessionRequest=SessionSource&{schema_version:'dmb_world_session_create_v1';entry_scene_id:string|null;encounters:{scene_id:string;template:TemplatePin|null}[]};
export type PreparationPreview={request:WorldSessionRequest;scenes:{scene_id:string;name:string;encounter_name:string|null;enemies:string[];template:TemplatePin|null}[];excluded_orphan_count:number};
export type SessionApplied={schema_version:'dmb_world_session_creation_v1';state:'applied';run:WorldPlayRunRecordV2;manifest:PlayRunReferenceManifest;receipt:{world_id:string;run_id:string;request:WorldSessionRequest;preparation_digest:string}};
export type SessionCanceled={state:'canceled';world_id:string;run_id:string;request_digest:string;request:WorldSessionRequest};
export type SessionOutcome=SessionApplied|SessionCanceled;
export type EncounterPreview={world_id:string;run_id:string;scene_id:string;preparation_digest:string;template:TemplatePin;initialization_policy:'dmb_fresh_scene_encounter_v1';title:string;preview_digest:string;actors:{actor_id:string;name:string;hp_before:number|string|null;hp_after:number|string|null;typed_maximum:boolean;temp_hp_before:number;conditions_before:string[];defeated_before:boolean}[]};
export type MaterializeRequest={schema_version:'dmb_scene_encounter_materialize_v1';operation_id:string;expected_preparation_digest:string;template:TemplatePin;initialization_policy:'dmb_fresh_scene_encounter_v1';preview_digest:string};
export type EncounterApplied={state:'applied';encounter:CombatEncounterRecord;receipt:{encounter_id:string;intent:{world_id:string;run_id:string;scene_id:string;request:MaterializeRequest}}};
export type EncounterOutcome=EncounterApplied|{state:'canceled';world_id:string;run_id:string;scene_id:string;request:MaterializeRequest};

export async function sessionFetch<T>(path:string,body?:unknown,method=body===undefined?'GET':'POST'):Promise<T>{
 const {response}=await authenticatedApiFetch(path,{method,...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
 const data=await response.json();if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:`Session request failed (${response.status})`);Object.assign(error,{status:response.status});throw error;}return data as T;
}
const sessionPath=(worldId:string,runId:string,suffix='')=>`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}${suffix}?${new URLSearchParams({world_id:worldId})}`;
export const encounterPath=(worldId:string,scope:RunEncounterScope,suffix='')=>`/api/live/combat/run-encounters/${encodeURIComponent(scope.runId)}/scenes/${encodeURIComponent(scope.sceneId)}${suffix}?${new URLSearchParams({world_id:worldId})}`;
export async function previewSession(worldId:string,source:SessionSource,sceneId?:string|null){
 const query=new URLSearchParams({world_id:worldId});if(sceneId)query.set('entry_scene_id',sceneId);
 return sessionFetch<PreparationPreview>(`/api/live/world-play-runs/v2/preparation?${query}`,source);
}
export function assertSessionOutcome(result:SessionOutcome,worldId:string,runId:string,request:WorldSessionRequest){
 if(result.state==='canceled'){if(result.world_id!==worldId||result.run_id!==runId||exactIntent(result.request)!==exactIntent(request))throw new Error('Cancellation belongs to another session');return;}
 if(result.schema_version!=='dmb_world_session_creation_v1'||result.run.playable_artifact_id!==request.playable_artifact_id||result.run.playable_revision!==request.expected_playable_revision||result.run.playable_work_revision_id!==request.expected_playable_work_revision_id||result.run.playable_content_sha256!==request.expected_playable_content_sha256||result.receipt.world_id!==worldId||result.receipt.run_id!==runId||result.run.world_id!==worldId||result.run.run_id!==runId||exactIntent(result.receipt.request)!==exactIntent(request))throw new Error('Session receipt differs from confirmed preparation');
 if(result.manifest.run_id!==runId||result.manifest.playable_artifact_id!==request.playable_artifact_id||result.manifest.playable_revision!==request.expected_playable_revision||result.manifest.playable_content_sha256!==request.expected_playable_content_sha256)throw new Error('Session manifest differs from confirmed source');
}
export const inspectSession=(world:string,id:string)=>sessionFetch<SessionOutcome|null>(sessionPath(world,id,'/creation'));
export const cancelSession=(world:string,id:string,body:WorldSessionRequest)=>sessionFetch<SessionOutcome>(sessionPath(world,id,'/creation:cancel'),body);
export const readRunEncounter=(world:string,scope:RunEncounterScope)=>sessionFetch<EncounterApplied|null>(encounterPath(world,scope));
export const previewRunEncounter=(world:string,scope:RunEncounterScope)=>sessionFetch<EncounterPreview>(encounterPath(world,scope,'/preview'));
export const materializeRunEncounter=(world:string,scope:RunEncounterScope,body:MaterializeRequest,action:''|'/cancel'|'/inspect'='')=>sessionFetch<EncounterOutcome|null>(encounterPath(world,scope,action),body);
