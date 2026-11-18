import { nodeOverviewRelationship } from "../../graphLens/nodeOverviewRelationship";
import { useEffect, useState, useSyncExternalStore } from 'react'
import { getReadWaveVersion, subscribeReadWave } from '../../api/inFlightReads'
import { getWorldAgentNativeReplayAssertion, getWorldAgentReplayAssertion } from '../../api/liveApi'
import type { BuddyReplayAssertionResponse, BuddyReplayNativeAssertionResponse, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import type { RetrievalStep } from './BuddyRetrievalReplay'

export function useRecordedReplayAssertion({ trace, step, assertionId, open }: {
  trace: BuddyTurnContextTrace; step: RetrievalStep; assertionId: string; open: boolean
}) {
  const { world_id, turn_id, trace_id } = trace
  const { sequence, revision_pin, scope_mode, campaign_id, native } = step
  const wave = useSyncExternalStore(subscribeReadWave, getReadWaveVersion, getReadWaveVersion)
  const binding = JSON.stringify([world_id, turn_id, trace_id, sequence, assertionId, revision_pin, scope_mode, campaign_id, native])
  const [read, setRead] = useState<{ binding: string; wave: number; assertion: (BuddyReplayAssertionResponse['assertion'] & Pick<BuddyReplayNativeAssertionResponse['assertion'], 'metadata'>) | null; excerpts?: BuddyReplayNativeAssertionResponse['excerpts'] }>()
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    setRead(undefined)
    const owns = () => !controller.signal.aborted && getReadWaveVersion() === wave
    const load = native ? getWorldAgentNativeReplayAssertion : getWorldAgentReplayAssertion
    void load(world_id, turn_id, trace_id, sequence, assertionId, controller.signal)
      .then(result => {
        if (!owns()) return
        const nativeResult = result.schema === 'dmb_replay_native_assertion_v1'
        if (nativeResult !== Boolean(native) || result.world_id !== world_id
          || result.turn_id !== turn_id || result.trace_id !== trace_id || result.sequence !== sequence
          || (nativeResult ? result.revision_id !== revision_pin
            : result.schema !== 'dmb_replay_assertion_v1' || result.scope?.managed_world_id !== world_id
              || result.scope.revision_id !== revision_pin || result.scope.scope_mode !== scope_mode
              || result.scope.campaign_id !== campaign_id)
          || result.assertion?.assertion_id !== assertionId) throw new Error('Assertion response binding differs')
        setRead({ binding, wave, assertion: result.assertion, excerpts: nativeResult ? result.excerpts : undefined })
      }).catch(() => { if (owns()) setRead({ binding, wave, assertion: null }) })
    return () => controller.abort()
  }, [open, wave, world_id, turn_id, trace_id, sequence, assertionId, revision_pin, scope_mode, campaign_id, native, binding])

  return read?.binding === binding && read.wave === wave ? read : undefined
}

export function BuddyReplayAssertion({ trace, step, assertionId, labelFor, number }: {
  trace: BuddyTurnContextTrace; step: RetrievalStep; assertionId: string; labelFor?: (id: string) => string | undefined; number?: number
}) {
  const [open, setOpen] = useState(false)
  const read = useRecordedReplayAssertion({ trace, step, assertionId, open })
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Open recorded assertion{number === undefined ? "" : ` ${number}`}</summary>
    {open && (!read ? <p role="status">Reading the recorded assertion…</p>
      : read.assertion ? <RecordedReplayAssertionContent read={read} labelFor={labelFor} />
      : <p role="alert">The assertion is unavailable at the recorded revision.</p>)}
  </details>
}


export function RecordedReplayAssertionContent({
  read, labelFor,
}: { read: NonNullable<ReturnType<typeof useRecordedReplayAssertion>>; labelFor?: (id: string) => string | undefined }) {
  const assertion = read.assertion;
  if (!assertion) return null;
  const subject = labelFor?.(assertion.subject_entity_id) ?? "An unnamed object";
  const relation = assertion.predicate.split(":").at(-1)?.replaceAll("_", " ") ?? "relationship";
  const value = assertion.value;
  let sentence = `The record gives ${subject} a “${relation}” value.`;
  let structuredValue: unknown;
  let literal = value;
  if (value && typeof value === "object" && "kind" in value) {
    if (value.kind === "entity_ref" && "entity_id" in value && typeof value.entity_id === "string") {
      const object = labelFor?.(value.entity_id) ?? "an unnamed object";
      sentence = nodeOverviewRelationship(assertion.predicate, subject, object)
        ?? (relation === "precedes" ? `${subject} happens before “${object}.”` : `The record links ${subject} to ${object} by “${relation}.”`);
      literal = undefined;
    } else if (value.kind === "term_ref" && "term" in value && typeof value.term === "string") {
      const term = value.term.split(":").at(-1)?.replaceAll("_", " ");
      sentence = relation === "classification" ? `The record classifies ${subject} as ${term}.`
        : `The record gives ${subject} the “${relation}” term “${term}.”`;
      literal = undefined;
    } else if (value.kind === "literal" && "value" in value) {
      literal = value.value;
    }
  }
  if (typeof literal === "string" || typeof literal === "number" || typeof literal === "boolean" || literal === null) {
    sentence = relation === "summary" && typeof literal === "string" ? literal
      : `The record gives ${subject} the “${relation}” value “${String(literal)}.”`;
  } else if (literal !== undefined) {
    structuredValue = literal;
  }
  return <>
    <p>{sentence}</p>
    {structuredValue !== undefined && <details>
      <summary>Recorded value</summary>
      <pre>{JSON.stringify(structuredValue, null, 2)}</pre>
    </details>}
    {read.excerpts?.map(excerpt => <blockquote key={excerpt.evidence_ref_id}>{excerpt.text}</blockquote>)}
  </>;
}
