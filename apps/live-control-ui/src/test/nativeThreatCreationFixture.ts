import type {PreparedNativeThreat,PublishedNativeThreat} from '../api/nativeThreatCreation';
export const threatDraftId='11111111-1111-4111-8111-111111111111';
export async function threatPacket(world='elderwyld',draft=threatDraftId):Promise<PreparedNativeThreat> {
  const source_text='# Rolling ooze\n\nProposed creature; not a played event.';
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(source_text))),b=>b.toString(16).padStart(2,'0')).join('');
  return {state:'prepared',source_text,prepared:{schema:'opaque-test-packet',value:{retained:true}},token:'signed-test-token',
    review:{schema:'dmb_native_threat_review_v1',world_id:world,draft_id:draft,draft_version:3,label:'Rolling ooze',body_sha256:digest,
      binding:{managed_world_id:world,native_world_id:'native-world',binding_version:2},publication_id:'dmb-native-threat:v1:'+draft,
      source_evidence_id:'evidence:one',source_artifact_id:'artifact:one',source_revision_id:'source-revision:one',
      prepared_digest:'b'.repeat(64),principal:'operator',expires_at:'2026-11-09T00:00:00Z'}};
}
export function threatCreated(world='elderwyld',draft=threatDraftId):PublishedNativeThreat {
  return {state:'published',world_id:world,draft_id:draft,native_world_id:'native-world',binding_version:2,
    node_id:'ent:creature',publication_id:'dmb-native-threat:v1:'+draft,published_revision_id:'rev:created',replayed:false};
}
