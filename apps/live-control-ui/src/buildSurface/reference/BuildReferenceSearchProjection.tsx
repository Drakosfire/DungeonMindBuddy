import {NativeGraphInspection} from '../../graphLens/NativeGraphInspection';
import type {BuildReferenceContextBinding} from './buildBuildSurfaceInteractionPublication';
import {BUILD_REFERENCE_CONTEXT_BINDING_ID} from './buildReferenceIds';

export function readBuildReferenceContextBinding(bindings:Readonly<Record<string,unknown>>):BuildReferenceContextBinding {
 const value=bindings[BUILD_REFERENCE_CONTEXT_BINDING_ID] as Partial<BuildReferenceContextBinding>|null|undefined;
 if(!value||value.schema!=='dmb_build_reference_context_v3'||typeof value.documentId!=='string'||typeof value.worldId!=='string'||!value.worldId.trim()||typeof value.insertChip!=='function'||typeof value.editorInsertDisabled!=='boolean')throw new Error('Open a current World document to find its objects.');
 return value as BuildReferenceContextBinding;
}
export function BuildReferenceSearchProjection({bindings}:{bindings:Readonly<Record<string,unknown>>}) {
 const context=readBuildReferenceContextBinding(bindings);
 return <div data-testid="build-reference-search-projection"><NativeGraphInspection key={`${context.worldId}:${context.documentId}`} worldId={context.worldId} onChoose={context.insertChip} disabled={context.editorInsertDisabled} selectionAction="Insert link"/></div>;
}
