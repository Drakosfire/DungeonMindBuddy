import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import {SourceCitation} from './SourceCitation';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';

export type CitationChoice={key:string;number:number;buttonText?:string;savedReferenceMarkdown?:string;segmentIndex?:number;resolveTitle?:boolean;title:string;label:string;kind:'passage'|'section';load:()=>Promise<string|{content:string;title:string}|{pngBase64:string;title:string}>};
/** One disclosure owner; transport adapters must verify the exact cited bytes. */
export function SourceCitationEvidence({identity,statements,answer,displaySegments,allowedInternalLinks=[],inlineProse=false,prefetchTitles=false}:{identity:string;statements:{text?:string;choices:CitationChoice[]}[];answer?:string;displaySegments?:readonly string[];allowedInternalLinks?:readonly string[];inlineProse?:boolean;prefetchTitles?:boolean}) {
  const panel=useId(),epoch=useRef(0);
  const [opened,setOpened]=useState<{choice:CitationChoice;status:'loading'|'ready'|'unavailable';content?:string;title?:string;pngBase64?:string}|null>(null);
  const [copyStatus,setCopyStatus]=useState<string|null>(null);
  const reads=useRef(new Map<string,Promise<Awaited<ReturnType<CitationChoice['load']>>>>());
  const [titles,setTitles]=useState<Record<string,string>>({});
  useLayoutEffect(()=>{epoch.current++;reads.current=new Map();setTitles({});setOpened(null);setCopyStatus(null);return()=>{epoch.current++;};},[identity]);
  useEffect(()=>{
    if(!prefetchTitles)return;
    let cancelled=false;
    const pending=statements.flatMap(statement=>statement.choices).filter(choice=>choice.resolveTitle);
    async function resolve() {
      for(const choice of pending) {
        if(cancelled)return;
        const read=reads.current.get(choice.key) ?? Promise.resolve().then(choice.load);
        reads.current.set(choice.key,read);
        try {
          const result=await read;
          if(!cancelled) {
            const title=typeof result==='object' && 'title' in result && result.title.trim()
              ? result.title.replace(/ · Full document$/, '') : 'Source name unavailable';
            setTitles(current=>({...current,[choice.key]:title}));
          }
        } catch {
          if(reads.current.get(choice.key)===read) reads.current.delete(choice.key);
          if(!cancelled) setTitles(current=>({...current,[choice.key]:'Source name unavailable'}));
        }
      }
    }
    void resolve();
    return()=>{cancelled=true;};
  },[identity,prefetchTitles]);
  function close(){epoch.current++;setOpened(null);setCopyStatus(null);}
  async function open(choice:CitationChoice) {
    if(opened?.choice.key===choice.key){close();return;}
    const current=++epoch.current;setCopyStatus(null);setOpened({choice,status:'loading'});
    try {const result=await (reads.current.get(choice.key) ?? choice.load());if(current===epoch.current)setOpened({choice,status:'ready',...(typeof result==='string' ? {content:result} : result)});}
    catch {if(current===epoch.current)setOpened({choice,status:'unavailable'});}
  }
  const choices=statements.flatMap(s=>s.choices);
  const markers=(items:CitationChoice[])=>items.map(c=><SourceCitation key={c.key} number={String(c.number)} title={c.title}
    label={c.label} expanded={opened?.choice.key===c.key} controls={opened?.choice.key===c.key ? panel : undefined} onOpen={()=>{void open(c);}}/>);
  const aligned=displaySegments?.join("\n")===answer;
  return <div className="source-citation-evidence">
    {answer!==undefined ? <>
      <WorldPlanAgentAnswer answer={answer} allowedInternalLinks={allowedInternalLinks} displaySegments={displaySegments} inlineCitations={aligned ? choices.map(c=>({
        segmentIndex:c.segmentIndex!,label:String(c.number),title:c.title,ariaLabel:c.label,
        expanded:opened?.choice.key===c.key,controls:opened?.choice.key===c.key ? panel : undefined,onOpen:()=>{void open(c);},
      })) : []}/>
      {!aligned&&choices.length>0 ? <span aria-label="Sources for this reply">{markers(choices)}</span> : null}
    </> : inlineProse ? <p>{statements.map(({text, choices}, i) =>
      <span key={i}>{i > 0 ? " " : ""}{text}{markers(choices)}</span>
    )}</p> : statements.map(({text,choices},i)=>text!==undefined
      ? <WorldPlanAgentAnswer key={i} answer={text} displaySegments={[text]} inlineCitations={choices.map(c=>({
          segmentIndex:0,label:String(c.number),title:c.title,ariaLabel:c.label,
          expanded:opened?.choice.key===c.key,controls:opened?.choice.key===c.key ? panel : undefined,
          onOpen:()=>{void open(c);},
        }))}/>
       : <span key={i}>{choices.map(c=>c.buttonText
        ? <button key={c.key} type="button" aria-expanded={opened?.choice.key===c.key}
          aria-controls={opened?.choice.key===c.key ? panel : undefined}
          onClick={()=>{void open(c);}}>{titles[c.key] ? `${c.number}. ${titles[c.key]}` : c.buttonText}</button>
        : <SourceCitation key={c.key} number={String(c.number)} title={c.title}
          label={c.label} expanded={opened?.choice.key===c.key}
          controls={opened?.choice.key===c.key ? panel : undefined} onOpen={()=>{void open(c);}}/>)}</span>)}
    {opened ? <section id={panel} className="source-citation-evidence__panel" aria-label={`Opened source ${opened.choice.kind}`} aria-live="polite">
      <header><strong>{opened.title ?? opened.choice.title}</strong><button type="button" onClick={close}>Close {opened.choice.kind}</button></header>
      {opened.status==='ready' && opened.choice.savedReferenceMarkdown ? <button type="button" onClick={async()=>{
        const current=epoch.current;
        try {
          await navigator.clipboard.writeText(opened.choice.savedReferenceMarkdown!);
          if(epoch.current===current)setCopyStatus('Citation copied');
        } catch {
          if(epoch.current===current)setCopyStatus('Could not copy citation');
        }
      }}>Copy Plan citation</button> : null}
      {copyStatus ? <span role="status">{copyStatus}</span> : null}
      {opened.status==='loading' ? <p>Opening {opened.choice.kind}…</p> : opened.status==='unavailable'
        ? <p>The exact cited {opened.choice.kind} is unavailable. No newer text has been substituted.</p>
        : opened.pngBase64 ? <img src={`data:image/png;base64,${opened.pngBase64}`} alt={opened.title}/>
        : <WorldPlanAgentAnswer answer={opened.content ?? ''}/>}
    </section>:null}
  </div>;
}
