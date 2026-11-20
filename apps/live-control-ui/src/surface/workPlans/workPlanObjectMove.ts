import type {EditorView} from '@tiptap/pm/view';
import {closeHistory} from '@tiptap/pm/history';
import {isTableCaption,tableMoveRange} from '../../tiptap/extensions/EmbeddedTableMove';
import {startProposalDragScroll} from '../proposalDragScroll';
const mime='application/x-dmb-work-plan-move';
/** A moved locator remains the same object; it never saves or dispatches a step. */
export function moveWorkPlan(view:EditorView,from:number,to:number):boolean{
  const node=view.state.doc.nodeAt(from);
  if(!view.editable||node?.type.name!=='surfaceWorkPlan'||view.state.doc.resolve(from).depth!==0
    ||!Number.isInteger(to)||to<0||to>view.state.doc.content.size||view.state.doc.resolve(to).depth!==0)return false;
  if(view.state.doc.nodeAt(to)?.type.name==='table')to=tableMoveRange(view,to)?.from??to;
  if(to>=from&&to<=from+node.nodeSize)return false;
  const target=to>from?to-node.nodeSize:to;
  view.dispatch(closeHistory(view.state.tr).delete(from,from+node.nodeSize).insert(target,node).scrollIntoView());return true;
}
export function workPlanMoveHandle(view:EditorView,getPos:()=>number|undefined){
  let dragging:{token:string;doc:EditorView['state']['doc'];from:number}|null=null;
  let stop:(()=>void)|null=null;
  const end=()=>{dragging=null;stop?.();stop=null;};
  const start=(event:DragEvent)=>{
    const from=getPos();
    if(from===undefined||!view.editable||!event.dataTransfer||view.state.doc.nodeAt(from)?.type.name!=='surfaceWorkPlan'){event.preventDefault();return;}
    end();dragging={token:crypto.randomUUID(),doc:view.state.doc,from};
    event.dataTransfer.setData(mime,dragging.token);event.dataTransfer.effectAllowed='move';event.stopPropagation();
    stop=startProposalDragScroll(view.dom);
  };
  const over=(event:DragEvent)=>{if(dragging&&event.dataTransfer?.types.includes(mime)){event.preventDefault();event.stopPropagation();}};
  const drop=(event:DragEvent)=>{
    if(!dragging||event.dataTransfer?.getData(mime)!==dragging.token)return;
    event.preventDefault();event.stopPropagation();const source=dragging;end();
    if(view.state.doc!==source.doc)return;
    const point=view.posAtCoords({left:event.clientX,top:event.clientY});if(!point)return;
    const pos=view.state.doc.resolve(point.pos);let to=point.pos;
    if(pos.depth){const element=view.nodeDOM(pos.before(1)),rect=element instanceof Element?element.getBoundingClientRect():null;
      to=rect&&event.clientY>rect.top+rect.height/2?pos.after(1):pos.before(1);}
    moveWorkPlan(view,source.from,to);
  };
  const key=(event:KeyboardEvent)=>{
    if(!event.altKey||!['ArrowUp','ArrowDown'].includes(event.key))return;
    event.preventDefault();event.stopPropagation();const from=getPos();if(from===undefined)return;
    const node=view.state.doc.nodeAt(from);if(node?.type.name!=='surfaceWorkPlan')return;
    if(event.key==='ArrowUp'){
      const previous=view.state.doc.resolve(from).nodeBefore;if(!previous)return;
      let to=from-previous.nodeSize;if(previous.type.name==='table')to=tableMoveRange(view,to)?.from??to;
      moveWorkPlan(view,from,to);
    }else{
      const next=view.state.doc.resolve(from+node.nodeSize).nodeAfter;if(!next)return;
      let to=from+node.nodeSize+next.nodeSize;
      if(isTableCaption(next)&&view.state.doc.nodeAt(to)?.type.name==='table')to+=view.state.doc.nodeAt(to)!.nodeSize;
      moveWorkPlan(view,from,to);
    }
  };
  view.dom.addEventListener('dragover',over,true);view.dom.addEventListener('drop',drop,true);
  document.addEventListener('dragend',end,true);
  return {start,key,destroy(){end();view.dom.removeEventListener('dragover',over,true);view.dom.removeEventListener('drop',drop,true);document.removeEventListener('dragend',end,true);}};
}
