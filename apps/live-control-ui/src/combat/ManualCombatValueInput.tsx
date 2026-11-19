import {useEffect,useRef,useState} from 'react';

/** Keep incomplete keystrokes local; retain each complete valid value immediately. */
export function ManualCombatValueInput({value,onValue,kind,label,disabled,maxLength=256}:{
  value:string|number|null;onValue:(value:string|number|null)=>boolean;kind:'integer'|'text'|'name';label:string;disabled:boolean;maxLength?:number;
}) {
  const [text,setText]=useState(value===null?'':String(value));
  const focused=useRef(false),edited=useRef(false),last=useRef(value);
  useEffect(()=>{last.current=value;if(!focused.current)setText(value===null?'':String(value));},[value]);
  function commit(raw:string):boolean {
    if(kind==='name')return !!raw.trim()&&onValue(raw.trim());
    if(kind==='text')return onValue(raw);
    if(raw==='')return onValue(null);
    if(!/^-?\d+$/.test(raw))return false;
    const number=Number(raw);
    return Number.isSafeInteger(number)&&Math.abs(number)<=999999&&onValue(number);
  }
  return <span className="manual-combat-value-input"><input aria-label={label} value={text} maxLength={maxLength} disabled={disabled}
    inputMode={kind==='integer'?'numeric':undefined} placeholder={value===null?'Unset':undefined}
    onFocus={()=>{focused.current=true;edited.current=false;}} onChange={event=>{edited.current=true;setText(event.target.value);commit(event.target.value);}}
    onBlur={()=>{focused.current=false;if(edited.current&&!commit(text))setText(last.current===null?'':String(last.current));else if(kind==='name')setText(text.trim());}}
    onKeyDown={event=>{if(event.key==='Enter')event.currentTarget.blur();}}/>
    {kind==='text'&&value!==null&&<button type="button" disabled={disabled} aria-label={`Unset ${label}`} onClick={()=>{if(onValue(null))setText('');}}>Unset</button>}
  </span>;
}
