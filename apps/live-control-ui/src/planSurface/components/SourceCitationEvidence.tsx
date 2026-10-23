import {useId,useLayoutEffect,useRef,useState} from 'react';
import {SourceCitation} from './SourceCitation';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';

export type CitationChoice={key:string;number:number;segmentIndex?:number;title:string;label:string;kind:'passage'|'section';load:()=>Promise<string>};
/** One disclosure owner; transport adapters must verify the exact cited bytes. */
export function SourceCitationEvidence({identity,statements}:{identity:string;statements:{text?:string;choices:CitationChoice[]}[]}) {
  const panel=useId(),epoch=useRef(0);
  const [opened,setOpened]=useState<{choice:CitationChoice;status:'loading'|'ready'|'unavailable';content?:string}|null>(null);
  useLayoutEffect(()=>{epoch.current++;setOpened(null);return()=>{epoch.current++;};},[identity]);
  function close(){epoch.current++;setOpened(null);}
  async function open(choice:CitationChoice) {
    if(opened?.choice.key===choice.key){close();return;}
    const current=++epoch.current;setOpened({choice,status:'loading'});
    try {const content=await choice.load();if(current===epoch.current)setOpened({choice,status:'ready',content});}
    catch {if(current===epoch.current)setOpened({choice,status:'unavailable'});}
  }
  return <div className="source-citation-evidence">
    {statements.map(({text,choices},i)=>text!==undefined
      ? <WorldPlanAgentAnswer key={i} answer={text} displaySegments={[text]} inlineCitations={choices.map(c=>({
          segmentIndex:0,label:String(c.number),title:c.title,ariaLabel:c.label,
          expanded:opened?.choice.key===c.key,controls:opened?.choice.key===c.key ? panel : undefined,
          onOpen:()=>{void open(c);},
        }))}/>
      : <span key={i}>{choices.map(c=><SourceCitation key={c.key} number={String(c.number)} title={c.title}
          label={c.label} expanded={opened?.choice.key===c.key}
          controls={opened?.choice.key===c.key ? panel : undefined} onOpen={()=>{void open(c);}}/>)}</span>)}
    {opened ? <section id={panel} className="source-citation-evidence__panel" aria-label={`Opened source ${opened.choice.kind}`} aria-live="polite">
      <header><strong>{opened.choice.title}</strong><button type="button" onClick={close}>Close {opened.choice.kind}</button></header>
      {opened.status==='loading' ? <p>Opening {opened.choice.kind}…</p> : opened.status==='unavailable'
        ? <p>The exact cited {opened.choice.kind} is unavailable. No newer text has been substituted.</p>
        : <WorldPlanAgentAnswer answer={opened.content ?? ''}/>}
    </section>:null}
  </div>;
}
