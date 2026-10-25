import {useEffect,useMemo} from 'react';
import {SurfaceNavbarIconButton} from '../../surfaceInteraction/contextHost/SurfaceNavbarIconButton';
import {workPlanMoveHandle} from './workPlanObjectMove';
import {Node} from '@tiptap/core';
import {NodeViewWrapper,ReactNodeViewRenderer,type NodeViewProps} from '@tiptap/react';
import {parseWorkPlanFence,workPlanFence} from './workPlanReference';
import {SurfaceWorkPlan} from './SurfaceWorkPlan';
function WorkPlanView({node,updateAttributes,editor,getPos}:NodeViewProps){
  const movement=useMemo(()=>workPlanMoveHandle(editor.view,()=>{const pos=getPos();return typeof pos==='number'?pos:undefined;}),[editor,getPos]);
  useEffect(()=>()=>movement.destroy(),[movement]);
  try{
    const reference=parseWorkPlanFence(String(node.attrs.source));
    return <NodeViewWrapper contentEditable={false} className="surface-work-plan-node">
      <SurfaceWorkPlan reference={reference} onTitleChange={title=>updateAttributes({source:workPlanFence({...reference,title})})}
        moveHandle={<SurfaceNavbarIconButton icon="move" label="Move work plan" draggable={editor.isEditable} disabled={!editor.isEditable}
          title="Drag to move; hold near an edge to scroll. Alt+Up/Down to reorder."
          onDragStart={event=>movement.start(event.nativeEvent)} onKeyDown={event=>movement.key(event.nativeEvent)}/>}/>
    </NodeViewWrapper>;
  }catch{
    return <NodeViewWrapper contentEditable={false}><p role="alert">This work-plan reference needs recovery. Its source was retained.</p></NodeViewWrapper>;
  }
}
export const WorkPlanNode=Node.create({
  name:'surfaceWorkPlan',group:'block',atom:true,selectable:true,draggable:false,
  addAttributes(){return {source:{default:'',rendered:false}};},
  parseHTML(){return [];},
  renderHTML({node}){
    const ref=parseWorkPlanFence(String(node.attrs.source));
    return ['section',{'data-surface-work-plan':ref.source_turn_id},['strong',{},ref.title],['p',{},'Work plan · open the original page to inspect it.']];
  },
  addNodeView(){return ReactNodeViewRenderer(WorkPlanView);},
});
