import { useLayoutEffect, useRef, useState } from 'react';
import type { RulesPassageTarget } from '../api/rulesLookupTypes';
import { getNativeGraphAccessGeneration, NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT } from '../api/liveApi';
import { deferredComponent } from '../ui/deferredComponent';
const Reader = deferredComponent(() => import('./RulesHistoricalPassage'), 'cited Rules excerpt');

/** No source read or reader import until the citation is explicitly opened. */
export function RulesHistoricalCitation({ target, label }: { target: RulesPassageTarget; label: string }) {
  const [openedTarget, setOpenedTarget] = useState<string | null>(null);
  const epoch = useRef(getNativeGraphAccessGeneration());
  useLayoutEffect(() => {
    const changed = () => { const next = getNativeGraphAccessGeneration(); if (next !== epoch.current) { epoch.current = next; setOpenedTarget(null); } };
    window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
    return () => window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
  }, []);
  const key = [target.worldId, target.conversationId, target.turnId, target.attempt, target.supportId, target.supportSha256].join(':');
  const open = openedTarget === key;
  useLayoutEffect(() => setOpenedTarget(null), [key]);
  return <div><button type="button" aria-expanded={open} onClick={() => setOpenedTarget(value => value === key ? null : key)}>{open ? 'Hide' : 'Inspect'} Rules source: {label}</button>
    {open && <Reader key={key} target={target} onClose={() => setOpenedTarget(null)} />}</div>;
}
