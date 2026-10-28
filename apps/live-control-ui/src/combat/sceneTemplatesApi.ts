import {authenticatedApiFetch} from '../api/liveApi';
import type {CombatEncounterRecord} from './combatTypes';
export type PlanEncounterContext={worldId:string;documentId:string;sceneId:string;sceneTitle:string;canCreate:boolean;objectRevision:number|null;contentSha256:string|null;verifiedPlan?:{revisionN:number;workRevisionId:string;contentSha256:string}|null};
export type SceneTemplateIntent={schema_version:'dmb_scene_template_create_v1';operation_id:string;pin:{document_id:string;scene_id:string;revision_n:number;work_revision_id:string;content_sha256:string};encounter:{title:string}};
export type SceneTemplateView={binding:{schema_version:'dmb_scene_template_binding_v1';world_id:string;encounter_id:string;origin:SceneTemplateIntent['pin'];operation_id:string;request_digest:string;created_at:string};encounter:CombatEncounterRecord;versions:{revision:number;digest:string;saved_at:string}[];scene_present:boolean};
async function request<T>(worldId:string,path:string,body?:SceneTemplateIntent):Promise<T>{
 const response=(await authenticatedApiFetch(`/api/live/combat/scene-templates${path}?${new URLSearchParams({world_id:worldId})}`,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined)).response;
 const data=await response.json();
 if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:`Encounter preparation failed (HTTP ${response.status})`);
 return data as T;
}
export const sceneTemplatePath=(context:Pick<PlanEncounterContext,'documentId'|'sceneId'>)=>`/${encodeURIComponent(context.documentId)}/scenes/${encodeURIComponent(context.sceneId)}`;
export const getSceneTemplate=(context:PlanEncounterContext)=>request<SceneTemplateView|null>(context.worldId,sceneTemplatePath(context));
export const createSceneTemplate=(worldId:string,intent:SceneTemplateIntent)=>request<SceneTemplateView>(worldId,'',intent);
export const inspectSceneTemplateCreation=(worldId:string,operationId:string)=>request<SceneTemplateView|null>(worldId,`/operations/${encodeURIComponent(operationId)}`);
export const getSceneTemplateVersion=(context:PlanEncounterContext,revision:number)=>request<CombatEncounterRecord>(context.worldId,`${sceneTemplatePath(context)}/versions/${revision}`);
export function assertSceneTemplate(view:SceneTemplateView,context:PlanEncounterContext){
 if(view.binding.schema_version!=='dmb_scene_template_binding_v1'||view.binding.world_id!==context.worldId||view.binding.origin.document_id!==context.documentId||view.binding.origin.scene_id!==context.sceneId||view.encounter.world_id!==context.worldId||view.encounter.encounter_id!==view.binding.encounter_id)throw new Error('Prepared encounter response belongs to another scene.');
 return view;
}

export async function sceneCreationDigest(worldId:string,intent:SceneTemplateIntent){
 const normalized={world_id:worldId,request:{...intent,encounter:{campaign_id:null,session:null,ruleset_id:'generic.manual-tracking',...intent.encounter}}};
 function ordered(value:unknown):unknown{if(Array.isArray(value))return value.map(ordered);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,ordered(item)]));return value;}
 const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(ordered(normalized))));
 return 'sha256:'+Array.from(new Uint8Array(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');
}
export async function assertSceneCreation(view:SceneTemplateView,context:PlanEncounterContext,intent:SceneTemplateIntent){
 assertSceneTemplate(view,context);
 const expected=await sceneCreationDigest(context.worldId,intent);
 const samePin=Object.entries(intent.pin).every(([key,value])=>view.binding.origin[key as keyof SceneTemplateIntent['pin']]===value);
 if(view.binding.operation_id!==intent.operation_id||view.binding.request_digest!==expected||!samePin)throw new Error('Creation acknowledgement differs from the retained exact request.');
}

export type SceneCreationCancellation={state:'applied';view:SceneTemplateView}|{state:'canceled';operation_id:string;world_id:string;request_digest:string};
export const cancelSceneTemplateCreation=(worldId:string,intent:SceneTemplateIntent)=>request<SceneCreationCancellation>(worldId,'/cancel',intent);
