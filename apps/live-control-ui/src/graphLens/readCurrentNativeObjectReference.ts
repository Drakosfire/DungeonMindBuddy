import {getNativeGraphCatalog} from '../api/liveApi';
import {isCatalogForWorld} from '../api/nativeGraphInspection';
import type {AuthoredGraphReferenceV1} from '../api/types';
import {isValidGraphNodeId} from '../tiptap/references/runbookReferences';

/** Document navigation resolves current objects; evidence citations keep their captured pin. */
export async function readCurrentNativeObjectReference(worldId:string,nodeId:string,signal:AbortSignal):Promise<AuthoredGraphReferenceV1> {
 if(!isValidGraphNodeId(nodeId))throw new Error('This Graph reference has an invalid node ID.');
 const catalog=await getNativeGraphCatalog({managed_world_id:worldId,scope_mode:'world',campaign_id:null},signal);
 if(!isCatalogForWorld(catalog,worldId))throw new Error('The object catalogue did not match this World.');
 if(!catalog.catalogue.entities.some(entity=>entity.entity_id===nodeId))throw new Error('This object is unavailable in the current reviewed Graph.');
 const name=catalog.assertions.find(a=>a.subject_entity_id===nodeId&&a.predicate==='dnd5e:name'&&a.value.kind==='literal'&&typeof a.value.value==='string');
 const label=name?.value.kind==='literal'?String(name.value.value):nodeId;
 const pin=catalog.scope;
 return {schema:'dmb_authored_graph_reference_v1',managed_world_id:pin.managed_world_id,native_world_id:pin.native_world_id,binding_version:pin.binding_version,graph_revision:pin.revision_id,node_id:nodeId,label};
}
