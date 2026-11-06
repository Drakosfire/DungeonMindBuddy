import type {NativeGraphCatalog} from '../api/nativeGraphInspection';

/** A view of admitted native names/classes, never an identity-matching authority. */
export type ConnectedPageIdentity={nodeId:string;label:string;names:string[];kind:'npc'|'location'};
export function connectedPageIdentities(packet:NativeGraphCatalog,worldId:string):ConnectedPageIdentity[]{
 const {scope,catalogue}=packet;
 if(packet.schema!=='dmb_native_graph_catalog_v1'||scope.managed_world_id!==worldId
  ||scope.scope_mode!=='world'||scope.campaign_id!==null
  ||catalogue.identity.space_id!==scope.native_world_id||catalogue.identity.revision_id!==scope.revision_id
  ||catalogue.completeness.status!=='complete')throw new Error('Existing Graph identities could not be checked completely. Refresh before choosing an existing object.');
 const admitted=new Set(catalogue.admitted_assertion_ids),entities=new Set(catalogue.entities.map(n=>n.entity_id));
 const names=new Map<string,Set<string>>(),classes=new Map<string,Set<string>>();
 for(const a of packet.assertions){
  if(!admitted.has(a.assertion_id))throw new Error('The identity catalogue includes an unadmitted assertion.');
  if(!entities.has(a.subject_entity_id))continue;
  if(a.predicate==='dnd5e:name'&&a.value.kind==='literal'&&typeof a.value.value==='string'){
   const set=names.get(a.subject_entity_id)??new Set<string>();set.add(a.value.value);names.set(a.subject_entity_id,set);
  }
  if(a.predicate==='dnd5e:classification'&&a.value.kind==='term_ref'){
   const set=classes.get(a.subject_entity_id)??new Set<string>();set.add(a.value.term);classes.set(a.subject_entity_id,set);
  }
 }
 const result:ConnectedPageIdentity[]=[];
 for(const nodeId of entities){
  const labels=[...(names.get(nodeId)??[])].sort(),terms=classes.get(nodeId);
  if(!labels.length||!terms)continue;
  for(const kind of ['npc','location'] as const){
   if(kind==='npc'?terms.has('dnd5e:npc')||terms.has('dungeonbuddy:character'):terms.has('dnd5e:location'))
    result.push({nodeId,label:labels[0],names:labels,kind});
  }
 }
 return result;
}
