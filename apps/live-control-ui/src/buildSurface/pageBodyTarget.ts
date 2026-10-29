import type {JSONContent} from '@tiptap/core';

const ordinary=new Set(['doc','paragraph','text','heading','blockquote','bulletList','orderedList','listItem','table','tableRow','tableHeader','tableCell','hardBreak','codeBlock','horizontalRule','image']);
const marks=new Set(['bold','italic','strike','code','link']);
/** Exact round-trip admission is checked by the editor owner before this inventory. */
export function pageBodyReferences(doc:JSONContent):string[] {
  const references:string[]=[];
  function visit(node:JSONContent){
    if(!node.type||!ordinary.has(node.type))throw new Error('This page contains an embedded object. Revise a selected passage instead.');
    if(node.type==='image')references.push(JSON.stringify(node));
    for(const mark of node.marks??[]){
      if(!marks.has(mark.type))throw new Error('This page contains a protected reference. Revise a selected passage instead.');
      if(mark.type==='link')references.push(JSON.stringify(mark));
    }
    for(const child of node.content??[])visit(child);
  }
  visit(doc);return references;
}
export function preservePageBodyReferences(before:JSONContent,after:JSONContent){
  if(JSON.stringify(pageBodyReferences(before))!==JSON.stringify(pageBodyReferences(after)))
    throw new Error('Whole-page revision must preserve every link and image reference. Nothing was replaced.');
}
