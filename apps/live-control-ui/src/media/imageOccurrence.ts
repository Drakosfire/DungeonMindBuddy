import type {Editor} from '@tiptap/core';
import {closeHistory} from '@tiptap/pm/history';
import {MEDIA_ASSET_ID} from './mediaReferences';
/** Pin an occurrence, not every use of this asset. Selection-only changes are safe. */
export function captureImageOccurrence(editor:Editor,getPos:()=>number|undefined,assetId:string) {
 const doc=editor.state.doc;const position=getPos();
 const node=position===undefined?null:doc.nodeAt(position);
 if(editor.isDestroyed||!editor.isEditable||!node||node.type.name!=='mediaImage'||node.attrs.assetId!==assetId)throw new Error('Open the editable image before generating.');
 return (nextAssetId:string)=>{
  if(editor.isDestroyed||!editor.isEditable||editor.state.doc!==doc||getPos()!==position||editor.state.doc.nodeAt(position!)!==node||!MEDIA_ASSET_ID.test(nextAssetId))throw new Error('The page changed. The new image is retained in your library; place it from there.');
  editor.view.dispatch(closeHistory(editor.state.tr).setNodeMarkup(position!,undefined,{...node.attrs,assetId:nextAssetId}).scrollIntoView());
 };
}
