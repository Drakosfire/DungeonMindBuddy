/** Offline exports only. No request producer receives the evaluator manifest. */
import {Editor,type JSONContent} from '@tiptap/core';
import {createHash} from 'node:crypto';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {expect,it} from 'vitest';
import dev from './cases.dev.json';
import holdout from './cases.holdout.json';
import buildDev from './routing_build.dev.json';
import buildHoldout from './routing_build.holdout.json';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../apps/live-control-ui/src/tiptap/MarkdownEditorCore';
import {captureProseTargetCatalog,resolveProseTarget} from '../../apps/live-control-ui/src/documentEditing/proseTargetCatalog';
import {compilePlanPlacementOptions} from '../../apps/live-control-ui/src/planSurface/agentEdit/planPlacementCatalog';
const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
const paragraph=(text:string):JSONContent=>({type:'paragraph',content:[{type:'text',text}]});
const heading=(text:string):JSONContent=>({type:'heading',attrs:{level:2},content:[{type:'text',text}]});
const scouts='The scouts have returned, but no one will explain why they were silent.';
it('exports real frozen host choices separately from evaluator-only answers, without editing',()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content:[
  heading('Overview'),paragraph('Unrelated opening; do not change.'),heading('Preparation'),
  paragraph('Opening image: three lantern flashes ripple across the eastern ridge. '+scouts),
  heading('Opening Beat'),paragraph('Keep the playable encounter unchanged.'),heading('Rumours'),paragraph(scouts)]}});
 try{
  editor.commands.setTextSelection(1);
  const snapshot=JSON.stringify(editor.getJSON());
  const plan=compilePlanPlacementOptions(editor,snapshot,'insert_at_caret');
  for(const [split,cases] of [['dev',dev],['holdout',holdout]] as const){
   const fixture=split==='dev'?buildDev:buildHoldout;
   const buildEditor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:{type:'doc',content:fixture.sections.flatMap(([title,passages])=>[heading(title as string),...(passages as string[]).map(paragraph)])}});
   try {
   buildEditor.commands.setTextSelection(1);
   const buildSnapshot=JSON.stringify(buildEditor.getJSON());
   const getState=()=>({editor:buildEditor,scopeKey:`synthetic-${split}`,draftGeneration:0,canEdit:true});
   const build=captureProseTargetCatalog(getState);
   const section=fixture.sections[1][0];
   const anchors=fixture.sections[1][1];
   const boundaryChoices=build.choices.filter(choice=>choice.section===section&&((choice.operation==='insert_after'&&choice.passage===anchors[0])||(choice.operation==='insert_before'&&choice.passage===anchors[1])));
   expect(boundaryChoices).toHaveLength(2);
   const bound=boundaryChoices.map(choice=>resolveProseTarget(build,choice.selector,getState));
   expect(bound[0].from).toBe(bound[1].from);
   expect(bound.every(target=>target.from===target.to&&target.from>1)).toBe(true);
   const inputs:any={schema:'prose_routing_inputs_v1',split,cases:[]};
   const answers:any[]=[];
   const routingCases=[...fixture.cases.map(item=>({...item,surface:'Build',id:'private-build'})),...cases.filter(item=>item.surface==='Plan')];
   routingCases.forEach((item,index)=>{
    const id=`case${index+1}`;
    const rows=item.surface==='Build'?build.choices.map(choice=>({host:choice.selector,public:{operation:choice.operation,section:choice.section,passage:choice.passage},acceptable:(item.expected==='rewrite'&&choice.operation==='replace_paragraph'&&choice.section===section&&choice.passage===anchors[0])||(item.expected==='boundary'&&boundaryChoices.includes(choice))})):
     plan.map(choice=>({host:choice.selector,public:{operation:'insert_at_boundary',label:choice.label},acceptable:item.expected==='after_preparation'&&choice.root_boundary===4}));
    const choices=rows.map((row,i)=>({alias:`choice${i+1}`,...row.public}));
    inputs.cases.push({id,request:item.request,choices});
    answers.push({id,fixture_id:item.id,disposition:item.expected==='clarify'?'clarify':item.expected==='discuss'?'discuss':'target',
     target_available:rows.some(row=>row.acceptable),acceptable_aliases:rows.flatMap((row,i)=>row.acceptable?[`choice${i+1}`]:[]),
     snapshot_sha256:hash(item.surface==='Build'?buildSnapshot:snapshot),host_bindings:Object.fromEntries(rows.map((row,i)=>[`choice${i+1}`,row.host]))});
   });
   const bytes=JSON.stringify(inputs,null,2)+'\n';
   const manifest={schema:'prose_routing_answers_v1',inputs_sha256:hash(bytes),split,source_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),cases:answers};
   expect(JSON.stringify(inputs)).not.toMatch(/expected|acceptable_aliases|snapshot_sha256|fixture_id|host_bindings|replace_scouts|after_preparation/);
   expect(inputs.cases.every((item:any)=>item.choices.every((choice:any)=>/^choice\d+$/.test(choice.alias)))).toBe(true);
   expect(answers[0].acceptable_aliases).toHaveLength(1);
   expect(answers[2].acceptable_aliases).toHaveLength(2);
   // Actual exported Build aliases go through the real Python scorer. These are
   // evaluator controls, never model outputs or holdout routing accuracy.
   const scoreAlias=(alias:string)=>JSON.parse(execFileSync(process.env.PROSE_PYTHON??'python3',['-c',
    'import json,sys; from evals.inline_prose_targeting.replay_score import score; x=json.load(sys.stdin); print(json.dumps(score(x[0].encode(),x[1],x[2])))'],
    {encoding:'utf8',input:JSON.stringify([bytes,manifest,{schema:'prose_routing_replay_v1',inputs_sha256:hash(bytes),provenance:'scripted',decisions:[{id:'case3',decision:{alias}}]}])}));
   for(const alias of answers[2].acceptable_aliases){
    const result=scoreAlias(alias);expect(result.hard_failure).toBe(false);expect(result.counts.correct_target).toBe(1);
    expect(result.ordinary_routing_qualified).toBe(false);expect(result.transactions).toBe('not run');
   }
   const rejected=inputs.cases[2].choices.filter((choice:any)=>choice.operation==='insert_after'&&choice.section!==section);
   expect(rejected).toHaveLength(2); // plausible opening and duplicate in wrong section
   for(const choice of rejected){const result=scoreAlias(choice.alias);expect(result.hard_failure).toBe(true);expect(result.counts.wrong_target_nomination).toBe(1);}
   const top=inputs.cases[2].choices.find((choice:any)=>choice.operation==='insert_before');
   expect(scoreAlias(top.alias).hard_failure).toBe(true);
   if(split==='dev'){
    expect(answers[4].acceptable_aliases).toHaveLength(2);
    expect(answers[5].target_available).toBe(false);
    expect(inputs.cases[4].choices[0].label).toBe('At the captured text caret');
   }
   expect(JSON.stringify(buildEditor.getJSON())).toBe(buildSnapshot);
   expect(buildEditor.state.selection.empty).toBe(true);expect(buildEditor.state.selection.from).toBe(1);
   if(process.env.PROSE_ROUTING_EXPORT){
    const root=resolve(process.env.PROSE_ROUTING_EXPORT);
    if(root===process.cwd()||root.startsWith(process.cwd()+'/'))throw Error('Use a new external evidence directory');
    mkdirSync(join(root,'producer'),{recursive:true});mkdirSync(join(root,'evaluator-private'),{recursive:true});
    writeFileSync(join(root,'producer',`${split}.json`),bytes,{flag:'wx'});
    writeFileSync(join(root,'evaluator-private',`${split}.json`),JSON.stringify(manifest,null,2)+'\n',{flag:'wx',mode:0o600});
   }
   } finally {buildEditor.destroy();}
  }
  expect(buildDev.sections.flatMap(([,passages])=>passages).every(passage=>!JSON.stringify(buildHoldout.sections).includes(passage as string))).toBe(true);
  expect(JSON.stringify(editor.getJSON())).toBe(snapshot);expect(editor.state.selection.empty).toBe(true);expect(editor.state.selection.from).toBe(1);
 }finally{editor.destroy();}
});
