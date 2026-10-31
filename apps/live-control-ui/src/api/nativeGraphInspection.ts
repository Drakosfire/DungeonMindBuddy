/** Native Core records, not the classic WorldGraphProjection dialect. */
export type InspectionScope={managed_world_id:string;scope_mode:'world'|'campaign';campaign_id:string|null};
export type InspectionPin=InspectionScope&{native_world_id:string;binding_version:number;revision_id:string};
export type NativeAssertion={assertion_id:string;subject_entity_id:string;predicate:string;
 value:{kind:'literal';value:unknown}|{kind:'term_ref';term:string}|{kind:'entity_ref';entity_id:string};
 metadata:{scope:{axis:string;value:string}[];visibility:unknown;epistemic_basis:string;claim_mode:string;
 standing:string;evidence_ref_ids:string[];temporal_scope:unknown;domain_metadata:unknown[]}};
export type NativeGraphCatalog={schema:'dmb_native_graph_catalog_v1';scope:InspectionPin;
 catalogue:{identity:{space_id:string;revision_id:string};entities:{entity_id:string}[];
 admitted_assertion_ids:string[];completeness:{status:'complete'|'partial';reason:string|null};
 request_sha256:string;result_digest:string};assertions:NativeAssertion[]};
export type InspectionSelection={kind:'entity';entity_id:string}|{kind:'source';assertion_id:string;evidence_ref_id:string};
export type NativeGraphEntity={schema:'dmb_native_graph_entity_v1';scope:InspectionPin;entity:{found:boolean;
 assertions:NativeAssertion[];evidence:{evidence_ref_id:string;evidence_role:string}[];
 completeness:{status:'complete'|'partial';reason:string|null}}};
export type NativeGraphSource={schema:'dmb_native_graph_source_v1';scope:InspectionPin;source:{status:'available';
 text:string;source_artifact_id:string;source_revision_id:string;body_sha256:string;span_sha256:string;
 span_start_byte:number;span_end_byte:number;source_authority_epoch:number}};
