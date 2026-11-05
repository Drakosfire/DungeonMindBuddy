import type {InspectionPin} from './nativeGraphInspection';
export type NativeSourceMetadata={
 source_artifact:{source_artifact_id:string;source_classification:string};
 source_revision:{source_revision_id:string;content_sha256:string};evidence_ref_ids:string[];
 origin:{namespace:string;object_id:string;revision_id:string}|null;
 navigation:{label:string|null;kind:'recap'|'worldbuilding'|'other';campaign_id:string|null;
 session_id:string|null;status:'available'|'unavailable';metadata_revision:string|null;
 origin_matches_current_metadata:boolean|null};
};
export type NativeSourceCatalog={schema:'dmb_native_source_catalog_v1';scope:InspectionPin;
 catalogue:{space_id:string;revision_id:string;source_authority_epoch:number;
 sources:NativeSourceMetadata[];complete:boolean};navigation_complete:boolean};
export type NativeSourceSelection={source_artifact_id:string;source_revision_id:string;evidence_ref_id:string};
export type NativeSourceBody={schema:'dmb_native_source_body_v1';scope:InspectionPin;
 source:{status:'available';source_artifact_id:string;source_revision_id:string;
 body_text:string;body_sha256:string;evidence_ref_id:string;source_authority_epoch:number}};
