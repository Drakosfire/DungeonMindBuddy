import {useId} from 'react';
import './SourceCitation.css';

/** Shared, keyboard-accessible citation marker. Details never trigger a read. */
export function SourceCitation({number,title,label,onOpen,expanded,controls}:{
  number:string;title:string;label?:string;onOpen:()=>void;expanded?:boolean;controls?:string;
}) {
  const tooltip=useId();
  return <span className="source-citation">
    <button type="button" className="source-citation__button" aria-label={label ?? `Open source ${number}`}
      title={title} aria-describedby={tooltip} aria-expanded={expanded} aria-controls={controls} onClick={onOpen}>{number}</button>
    <span role="tooltip" id={tooltip} className="source-citation__tooltip">{title}</span>
  </span>;
}
