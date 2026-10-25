import { DurableWorkPlan,type ReviewedRow } from './DurableWorkPlan'
import type {WorkPlan,WorkDispatch} from '../../api/conversationWorkPlanApi'
import { useState } from 'react'
import type {ConversationCollaboration,ConversationConnectedPageProposal} from '../../api/types'
import { parseMarkdownAst } from '../../tiptap/markdown/parseMarkdownAst'

type Mode = 'plan' | 'questions'
type Row = { text: string; include: boolean; answer: string; kind?:'discuss'|'prepare_insertion' }
type Notes = { rows: Row[]; blocked: boolean; warning: string | null }
function prose(node: unknown): string {
  if (!node || typeof node !== 'object') return ''
  const value = node as {value?: string; children?: unknown[]}
  return typeof value.value === 'string' ? value.value : (value.children ?? []).map(prose).join(' ')
}
function candidates(source: string): string[] {
  try {
    const rows = parseMarkdownAst(source).children.filter(node => node.type === 'list')
      .flatMap(node => node.type === 'list' ? node.children.map(prose) : [])
      .map(text => text.trim()).filter(Boolean)
    return rows
  } catch { return [] }
}
function Card({source, identity, mode, items, onAdd, disabled, onSavePlan}: {
  source: string; identity: string; mode: Mode; items: Row[]; onAdd: (text: string) => void; disabled: boolean; onSavePlan?:(rows:ReviewedRow[])=>Promise<void>
}) {
  const storageKey = `dmb:conversation-workbook:v1:${identity}:${mode}`
  const [notes, setNotes] = useState<Notes>(() => {
    const initial: Notes = {rows:items.map(row=>({...row})),blocked:false,warning:null}
    try {
      const raw = window.sessionStorage.getItem(storageKey)
      if (raw === null) return initial
      const value = JSON.parse(raw)
      if (value.schema !== 'dmb_conversation_workbook_v1' || value.identity !== identity || value.mode !== mode || value.source !== source
        || !Array.isArray(value.rows) || !value.rows.every((row: Row) => row && typeof row.text === 'string'
          && typeof row.answer === 'string' && typeof row.include === 'boolean' && (row.kind===undefined||['discuss','prepare_insertion'].includes(row.kind)))) throw new Error('scope')
      return {...initial,rows:value.rows}
    } catch {return {...initial,blocked:true,warning:'Local notes could not be restored. Existing stored notes were left untouched.'}}
  })
  const [added, setAdded] = useState(false)
  function change(rows: Row[]) {
    setAdded(false)
    setNotes(current => {
      let warning = current.warning
      if (!current.blocked) {
        try {
          const bytes=JSON.stringify({schema:'dmb_conversation_workbook_v1',identity,mode,source,rows})
          window.sessionStorage.setItem(storageKey,bytes)
          if(window.sessionStorage.getItem(storageKey)!==bytes)throw new Error('write')
          warning=null
        } catch {warning='These edits could not be saved locally. Keep a copy before reloading.'}
      }
      return {...current,rows,warning}
    })
  }
  function edit(index: number, update: Partial<Row>) {change(notes.rows.map((row,i)=>i===index?{...row,...update}:row))}
  const selected = notes.rows.filter(row=>row.include&&row.text.trim()&&(mode==='plan'||row.answer.trim()))
  return <section className="conversation-workbook" aria-label={mode==='plan'?'Plan for review':'Clarifying questions'}>
    <h4>{mode==='plan'?'Plan for review':'Clarifying questions'}</h4>
    <p>Select what to keep and edit directly. These are your local working notes; nothing is executed or added to the page.</p>
    {notes.warning&&<p role="alert">{notes.warning}</p>}
    {notes.rows.map((row,index)=><div className="conversation-workbook__row" key={index}>
      <label><input type="checkbox" checked={row.include} disabled={disabled} onChange={event=>edit(index,{include:event.target.checked})}/> Include {mode==='plan'?'step':'question'} {index+1}</label>
      <textarea aria-label={`${mode==='plan'?'Step':'Question'} ${index+1}`} value={row.text} disabled={disabled} onChange={event=>edit(index,{text:event.target.value})}/>
      {mode==='plan'&&onSavePlan&&<label>Action <select aria-label={`Action ${index+1}`} value={row.kind??'discuss'} disabled={disabled} onChange={event=>edit(index,{kind:event.target.value as Row['kind']})}><option value="discuss">Discuss</option><option value="prepare_insertion">Prepare an insertion</option></select></label>}
      {mode==='questions'&&<textarea aria-label={`Answer ${index+1}`} placeholder="Your answer…" value={row.answer} disabled={disabled} onChange={event=>edit(index,{answer:event.target.value})}/>}
    </div>)}
    <button type="button" disabled={disabled} onClick={()=>change([...notes.rows,{text:'',include:true,answer:''}])}>Add {mode==='plan'?'step':'question'}</button>{' '}
    <button type="button" disabled={disabled||!selected.length} onClick={()=>{
      const body=selected.map((row,index)=>mode==='plan'?`${index+1}. ${row.text.trim()}`:`Question: ${row.text.trim()}\nMy answer: ${row.answer.trim()}`).join('\n\n')
      onAdd(`${mode==='plan'?'My reviewed plan':'My answers to your clarifying questions'}:\n\n${body}`);setAdded(true)
    }}>Add to message</button>
    {mode==='plan'&&onSavePlan&&<button type="button" disabled={disabled||!notes.rows.length||notes.rows.some(row=>!row.text.trim())} onClick={()=>{void onSavePlan(notes.rows)}}>Save reviewed plan</button>}
    {added&&<p role="status">Added to your message. Review it and Send when ready.</p>}
    {notes.blocked&&<button type="button" onClick={()=>{
      try {window.sessionStorage.removeItem(storageKey);setNotes(current=>({...current,blocked:false,warning:null}))}
      catch {setNotes(current=>({...current,warning:'Local storage is unavailable. Keep a copy before reloading.'}))}
    }}>Replace unreadable local copy</button>}
  </section>
}

/** The author chooses the interpretation. Lists are never promoted to facts or executed. */
export function ConversationWorkbook({source, worldId, conversationId, turnId, onAdd, disabled=false, durable, collaboration}: {
  collaboration?:ConversationCollaboration|ConversationConnectedPageProposal|null; source: string; worldId: string; conversationId: string; turnId: string; onAdd: (text: string) => void; disabled?: boolean; durable?:{disabled:boolean;onContinue:(plan:WorkPlan,dispatch:WorkDispatch)=>void}
}) {
  const [chosenMode,setMode]=useState<Mode|null|undefined>(undefined)
  const mode=chosenMode===undefined?(collaboration?.kind==='plan'?'plan':collaboration?.kind==='questions'?'questions':null):chosenMode
  const items:Row[]=collaboration?.kind==='plan'?collaboration.steps.map(s=>({...s,include:true,answer:''})):collaboration?.kind==='questions'?collaboration.questions.map(q=>({...q,include:true,answer:''})):collaboration===undefined?candidates(source).map(text=>({text,include:true,answer:''})):[]
  const noteSource=collaboration?JSON.stringify([source,collaboration]):source
  if(!items.length)return null
  const identity=JSON.stringify([worldId,conversationId,turnId])
  return <div><div className="conversation-workbook__choices" hidden={collaboration!==undefined}>
    <button type="button" disabled={disabled} aria-pressed={mode==='plan'} onClick={()=>setMode(mode==='plan'?null:'plan')}>Review plan</button>{' '}
    <button type="button" disabled={disabled} aria-pressed={mode==='questions'} onClick={()=>setMode(mode==='questions'?null:'questions')}>Answer questions</button>
  </div>{mode==='plan'&&durable?<DurableWorkPlan key={`${identity}:${source}`} scope={{worldId,conversationId,turnId,source}} disabled={disabled||durable.disabled} onContinue={durable.onContinue}
    renderDraft={(onSavePlan,busy)=><Card {...{source:noteSource,identity,mode:'plan',items,onAdd,onSavePlan}} disabled={disabled||durable.disabled||busy}/>}/>:mode&&<Card key={`${identity}:${mode}:${noteSource}`} {...{source:noteSource,identity,mode,items,onAdd,disabled}}/>}</div>
}
