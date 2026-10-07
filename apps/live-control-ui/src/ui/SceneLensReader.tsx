import { useId, useRef, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import "./SceneLensReader.css";

export interface SceneReadingLens {
  id: string;
  label: string;
  content: ReactNode;
}

export interface SceneLensReaderProps {
  title: ReactNode;
  lenses?: readonly SceneReadingLens[];
  activeLensId: string | null;
  onLensChange: (id: string | null) => void;
  fullScene: ReactNode;
  location?: ReactNode;
  eyebrow?: ReactNode;
  context?: ReactNode;
  contextLabel?: string;
  choices?: ReactNode;
  choicesLabel?: string;
  actions?: ReactNode;
  footer?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

/**
 * Passive, controlled reading views. The caller supplies authored sections,
 * the complete scene projection and any stable choice/note state.
 * No parsing, target capture, source editing or external actions.
 */
export function SceneLensReader({
  title, lenses = [], activeLensId, onLensChange, fullScene, location,
  eyebrow, context, contextLabel = "Scene context", choices,
  choicesLabel = "Choices", actions, footer, className = "", style,
}: SceneLensReaderProps) {
  const id = useId();
  const tabs = useRef<HTMLDivElement>(null);
  const uniqueLenses = new Set(lenses.map(lens=>lens.id)).size === lenses.length ? lenses : [];
  const selectedIndex = uniqueLenses.findIndex(lens => lens.id === activeLensId);
  const selected = selectedIndex >= 0 ? uniqueLenses[selectedIndex] : null;
  const fullSelected = !selected;
  const items = [...uniqueLenses.map(lens => lens.id), null];
  const actualIndex = selected ? selectedIndex : uniqueLenses.length;
  const hasContext = context !== undefined && context !== null && context !== false;
  const hasChoices = choices !== undefined && choices !== null && choices !== false;

  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const rtl = tabs.current && getComputedStyle(tabs.current).direction === "rtl";
    const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1
      : event.key === "ArrowRight" ? (index + (rtl ? items.length - 1 : 1)) % items.length
      : event.key === "ArrowLeft" ? (index + (rtl ? 1 : items.length - 1)) % items.length : null;
    if (next === null) return;
    event.preventDefault();
    onLensChange(items[next]);
    tabs.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[next]?.focus({preventScroll:true});
  }

  return <section className={`scene-lens-reader ${className}`.trim()} style={style}>
    <header className="scene-lens-reader__heading">
      {eyebrow !== undefined && <div className="scene-lens-reader__eyebrow">{eyebrow}</div>}
      <div className="scene-lens-reader__title-row"><h2>{title}</h2>{actions && <div className="scene-lens-reader__actions">{actions}</div>}</div>
      {location !== undefined && <div className="scene-lens-reader__location">{location}</div>}
    </header>
    {uniqueLenses.length > 0 && <div ref={tabs} className="scene-lens-reader__lenses" role="tablist" aria-label="Reading lens">
      {uniqueLenses.map((lens,index)=><button key={lens.id} type="button" role="tab" id={`${id}-lens-${index}`}
        aria-controls={`${id}-content`} aria-selected={selectedIndex===index} tabIndex={actualIndex===index?0:-1}
        onClick={()=>onLensChange(lens.id)} onKeyDown={event=>navigate(event,index)}>{lens.label}</button>)}
      <button type="button" role="tab" id={`${id}-full`} aria-controls={`${id}-content`}
        aria-selected={fullSelected} tabIndex={fullSelected?0:-1} onClick={()=>onLensChange(null)}
        onKeyDown={event=>navigate(event,uniqueLenses.length)}>Full scene</button>
    </div>}
    <div id={`${id}-content`} className="scene-lens-reader__content" role={uniqueLenses.length>0?"tabpanel":undefined}
      tabIndex={uniqueLenses.length>0?0:undefined}
      aria-labelledby={uniqueLenses.length>0?(selected?`${id}-lens-${selectedIndex}`:`${id}-full`):undefined}>
      {selected ? selected.content : fullScene}
    </div>
    {hasChoices && <details className="scene-lens-reader__choices"><summary>{choicesLabel}</summary><div>{choices}</div></details>}
    {hasContext && <details className="scene-lens-reader__context"><summary>{contextLabel}</summary><div>{context}</div></details>}
    {footer !== undefined && <div className="scene-lens-reader__footer">{footer}</div>}
  </section>;
}
