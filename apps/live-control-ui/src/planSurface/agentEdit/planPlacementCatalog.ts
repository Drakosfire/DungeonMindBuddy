import type {Editor} from '@tiptap/core';
import type {PlanOriginalAuthoringCapture,PlanAuthoringCapture,PlanPlacementCatalog} from '../../api/planAuthoringReviewApi';
import {canonical} from '../../shared/sourcePassageProtocol';
import {isTableCaptionAt} from '../../tiptap/markdown/tableCaption';
import type {JSONContent} from '@tiptap/core';
import type {PlanPlacementCatalogV2} from '../../api/planAuthoringReviewApi';

/** Navigation over one frozen editor snapshot. Positions never enter model state. */
export interface PlanPlacementOption {
  selector: string;
  kind: 'captured_target'|'before_heading'|'after_heading'|'after_section'|'end_page';
  label: string;
  root_boundary: number|null;
  position: number|null;
}
export class PlanPlacementError extends Error {}

export interface PlanParagraphPlacementOption extends Omit<PlanPlacementOption,'kind'> {
  kind: PlanPlacementCatalogV2['entries'][number]['kind'];
  source_root_index: number|null;
}

function paragraphLabel(content:readonly JSONContent[],index:number,kind:'before_paragraph'|'after_paragraph'):string|null {
  const node=content[index],inline=node?.content??[];
  if(node?.type!=='paragraph'||inline.some(child=>child.type!=='hardBreak'
    &&(child.type!=='text'||typeof child.text!=='string')))return null;
  const passage=inline.map(child=>child.type==='hardBreak'?'\n':child.text).join('').trim();
  if(!passage)return null;
  const ancestors:Array<{level:number;text:string}>=[];
  content.slice(0,index).forEach((heading,root)=>{
    const level=heading.attrs?.level;
    if(heading.type!=='heading'||!Number.isInteger(level)||level<1||level>6||isTableCaptionAt(content,root))return;
    const text=(heading.content??[]).filter(child=>child.type==='text').map(child=>child.text??'').join('').trim();
    if(!text)return;
    while(ancestors.length&&ancestors.at(-1)!.level>=level)ancestors.pop();
    ancestors.push({level,text});
  });
  const section=ancestors.map(heading=>heading.text).join(' / ')||'this page';
  return `${kind==='before_paragraph'?'Before':'After'} paragraph in ${section}: ${passage}`;
}

/** V2 is explicit until ordinary producer activation is qualified. */
export function compilePlanParagraphPlacementOptions(
  editor:Editor,editorJson:string,targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
):readonly PlanParagraphPlacementOption[] {
  const legacy=compilePlanPlacementOptions(editor,editorJson,targetKind);
  const content=editor.getJSON().content??[];
  if(content.some(node=>['pageRow','pageImageText','pageSlot'].includes(node.type??'')))
    throw new PlanPlacementError('Paragraph placement currently requires a plain Plan.');
  let serial=0;
  const options:PlanParagraphPlacementOption[]=legacy.map(option=>({...option,
    selector:option.kind==='captured_target'?'captured':`place${++serial}`,
    source_root_index:option.kind==='captured_target'||option.kind==='end_page'?null:Number(option.selector.split(':')[1]),
  }));
  if(targetKind==='insert_at_caret')editor.state.doc.forEach((node,position,index)=>{
    for(const kind of ['before_paragraph','after_paragraph'] as const){
      const label=paragraphLabel(content,index,kind);
      if(label===null)continue;
      options.push({selector:`place${++serial}`,kind,label,source_root_index:index,
        root_boundary:index+Number(kind==='after_paragraph'),
        position:position+(kind==='after_paragraph'?node.nodeSize:0)});
    }
  });
  return Object.freeze(options.map(option=>Object.freeze(option)));
}

export function resolvePlanParagraphPlacementOption(
  editor:Editor,editorJson:string,targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
  offered:PlanParagraphPlacementOption,
):PlanParagraphPlacementOption {
  const actual=compilePlanParagraphPlacementOptions(editor,editorJson,targetKind).find(row=>row.selector===offered.selector);
  if(!actual||canonical(actual)!==canonical(offered))
    throw new PlanPlacementError('The offered paragraph location no longer identifies this captured boundary.');
  if(actual.root_boundary!==null&&planRootBoundaryPosition(editor,actual.root_boundary)!==actual.position)
    throw new PlanPlacementError('The paragraph boundary differs from its live editor position.');
  return actual;
}

export function planParagraphPlacementModelChoices(options:readonly PlanParagraphPlacementOption[]) {
  return options.map(({selector,label})=>({selector,label}));
}

type Heading = {index:number;level:number;text:string;path:string};

export function compilePlanPlacementOptions(
  editor:Editor, editorJson:string, targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
):readonly PlanPlacementOption[] {
  if(JSON.stringify(editor.getJSON())!==editorJson)
    throw new PlanPlacementError('The page changed before its locations could be captured.');
  const current:PlanPlacementOption={selector:'captured',kind:'captured_target',
    label:targetKind==='insert_at_caret'?'At the captured text caret'
      :targetKind==='replace_selection'?'Replace only the captured selection':'Replace only the captured playable body',
    root_boundary:null,position:null};
  // An explicit replacement never offers broader insertion authority.
  if(targetKind!=='insert_at_caret')return Object.freeze([Object.freeze(current)]);
  const doc=editor.state.doc,content=doc.toJSON().content??[];
  const offsets:number[]=[],headings:Heading[]=[],ancestors:Heading[]=[];
  doc.forEach((node,position,index)=>{
    offsets[index]=position;
    if(node.type.name!=='heading'||isTableCaptionAt(content,index))return;
    const level=Number(node.attrs.level),text=node.textContent.trim();
    if(!Number.isInteger(level)||level<1||level>6||!text)return;
    while(ancestors.length&&ancestors.at(-1)!.level>=level)ancestors.pop();
    const heading={index,level,text,path:[...ancestors.map(row=>row.text),text].join(' / ')};
    headings.push(heading);ancestors.push(heading);
  });
  offsets[doc.childCount]=doc.content.size;
  const totals=new Map<string,number>(),seen=new Map<string,number>();
  for(const heading of headings)totals.set(heading.path,(totals.get(heading.path)??0)+1);
  const options:PlanPlacementOption[]=[current];
  headings.forEach((heading,index)=>{
    const ordinal=(seen.get(heading.path)??0)+1;seen.set(heading.path,ordinal);
    const total=totals.get(heading.path)??1;
    const label=heading.path+(total>1?` · ${ordinal} of ${total}`:'');
    const end=headings.slice(index+1).find(next=>next.level<=heading.level)?.index??doc.childCount;
    options.push({selector:`before:${heading.index}`,kind:'before_heading',label:`Before ${label}`,
      root_boundary:heading.index,position:offsets[heading.index]!});
    options.push({selector:`under:${heading.index}`,kind:'after_heading',label:`Directly below the heading ${label}, before its existing body`,
      root_boundary:heading.index+1,position:offsets[heading.index+1]!});
    options.push({selector:`after:${heading.index}`,kind:'after_section',label:`After the entire section ${label}`,
      root_boundary:end,position:offsets[end]!});
  });
  options.push({selector:'end',kind:'end_page',label:'At the end of the page',
    root_boundary:doc.childCount,position:doc.content.size});
  return Object.freeze(options.map(option=>Object.freeze(option)));
}

/** Recompute from the matching live editor; never trust a returned numeric offset. */
export function resolvePlanPlacementOption(
  editor:Editor,editorJson:string,targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
  offered:PlanPlacementOption,
):PlanPlacementOption {
  const actual=compilePlanPlacementOptions(editor,editorJson,targetKind).find(row=>row.selector===offered.selector);
  if(!actual||actual.kind!==offered.kind||actual.label!==offered.label
    ||actual.root_boundary!==offered.root_boundary||actual.position!==offered.position)
    throw new PlanPlacementError('The offered page location no longer identifies this captured boundary.');
  return actual;
}

/** Deliberately excludes editor positions, root indices and target digests. */
export function planPlacementModelChoices(options:readonly PlanPlacementOption[]) {
  return options.map(({selector,label})=>({selector,label}));
}


export function planRootBoundaryPosition(editor:Editor,index:number):number {
  const doc=editor.state.doc;
  if(!Number.isSafeInteger(index)||index<0||index>doc.childCount
    ||index>0&&isTableCaptionAt(doc.toJSON().content??[],index-1))
    throw new PlanPlacementError('The location is not an indivisible page boundary.');
  if(index===doc.childCount)return doc.content.size;
  let position:number|undefined;
  doc.forEach((_node,offset,rootIndex)=>{if(rootIndex===index)position=offset;});
  if(position===undefined)throw new PlanPlacementError('The page boundary is unavailable.');
  return position;
}
async function digest(value:unknown) {
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value)));
  return Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');
}
export async function capturePlanPlacementCatalog(editor:Editor,original:PlanOriginalAuthoringCapture,paragraphTargets=false):Promise<PlanPlacementCatalog> {
  // Composed pages retain their separately qualified placement contract.
  if(paragraphTargets&&!editor.getJSON().content?.some(node=>['pageRow','pageImageText','pageSlot'].includes(node.type??'')))
    return capturePlanParagraphPlacementCatalog(editor,original);
  const options=compilePlanPlacementOptions(editor,original.editor_json,original.target_kind);
  const entries=await Promise.all(options.map(async option=>{
    const target:PlanAuthoringCapture=option.kind==='captured_target'?original:{...original,
      schema:'dmb_plan_authoring_boundary_capture_v1',target_kind:'insert_at_boundary',
      root_boundary:option.root_boundary!,from:option.position!,to:option.position!};
    return {...option,target_capture_sha256:await digest(target)};
  }));
  const originalHash=await digest(original);
  // Hashing can yield. Navigation may move the live selection; every target above
  // still uses the immutable Send-time capture. A document edit invalidates it.
  if(JSON.stringify(editor.getJSON())!==original.editor_json)
    throw new PlanPlacementError('The page changed while capturing its locations.');
  return {schema:'dmb_plan_placement_catalog_v1',original_capture_sha256:originalHash,
    editor_sha256:original.editor_sha256,entries};
}

export async function capturePlanParagraphPlacementCatalog(editor:Editor,original:PlanOriginalAuthoringCapture):Promise<PlanPlacementCatalogV2> {
  const options=compilePlanParagraphPlacementOptions(editor,original.editor_json,original.target_kind);
  const entries=await Promise.all(options.map(async option=>{
    const target:PlanAuthoringCapture=option.kind==='captured_target'?original:{...original,
      schema:'dmb_plan_authoring_boundary_capture_v1',target_kind:'insert_at_boundary',
      root_boundary:option.root_boundary!,from:option.position!,to:option.position!};
    return {...option,target_capture_sha256:await digest(target)};
  }));
  const originalHash=await digest(original);
  if(JSON.stringify(editor.getJSON())!==original.editor_json)
    throw new PlanPlacementError('The page changed while capturing its paragraph locations.');
  return {schema:'dmb_plan_placement_catalog_v2',original_capture_sha256:originalHash,
    editor_sha256:original.editor_sha256,entries};
}
