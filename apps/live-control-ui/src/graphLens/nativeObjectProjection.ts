import {sameInspectionPin, type InspectionPin, type NativeGraphEntity} from '../api/nativeGraphInspection';
import {buildNodeExplorer} from './nodeExplorerModel';

/** An admitted native subject, not a review candidate or a grant of edit authority. */
export type NativeObjectSubject = {kind: 'admitted-native'; entityId: string; pin: InspectionPin};
export function nativeObjectSubjectKey(subject: NativeObjectSubject): string {
 const p=subject.pin;
 return JSON.stringify([subject.kind,p.managed_world_id,p.native_world_id,p.binding_version,p.revision_id,p.scope_mode,p.campaign_id,subject.entityId]);
}
/** Pure read projection. Hosts own navigation, capabilities and authoritative commands. */
export function projectNativeObject(subject: NativeObjectSubject, detail: NativeGraphEntity, labels: ReadonlyMap<string,string>) {
 if (!sameInspectionPin(subject.pin,detail.scope)) throw new Error('Object does not match the selected World revision and scope');
 return {
  subject, key:nativeObjectSubjectKey(subject), found:detail.entity.found,
  completeness:detail.entity.completeness, records:detail.entity.assertions,
  evidence:detail.entity.evidence, dossier:buildNodeExplorer(detail,subject.entityId,labels),
 };
}
