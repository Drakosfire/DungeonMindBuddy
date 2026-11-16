import { useEffect, useState, useSyncExternalStore } from 'react'
import { getReadWaveVersion, subscribeReadWave } from '../../api/inFlightReads'
import { getWorldAgentNativeReplayAssertion, getWorldAgentReplayAssertion } from '../../api/liveApi'
import type { BuddyReplayAssertionResponse, BuddyReplayNativeAssertionResponse, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import type { RetrievalStep } from './BuddyRetrievalReplay'

export function BuddyReplayAssertion({ trace, step, assertionId }: {
  trace: BuddyTurnContextTrace; step: RetrievalStep; assertionId: string
}) {
  const { world_id, turn_id, trace_id } = trace
  const { sequence, revision_pin, scope_mode, campaign_id, native } = step
  const [open, setOpen] = useState(false)
  const wave = useSyncExternalStore(subscribeReadWave, getReadWaveVersion, getReadWaveVersion)
  const [read, setRead] = useState<{ wave: number; assertion: BuddyReplayAssertionResponse['assertion'] | null; excerpts?: BuddyReplayNativeAssertionResponse['excerpts'] }>()
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
        setRead({ wave, assertion: result.assertion, excerpts: nativeResult ? result.excerpts : undefined })
      }).catch(() => { if (owns()) setRead({ wave, assertion: null }) })
    return () => controller.abort()
  }, [open, wave, world_id, turn_id, trace_id, sequence, assertionId, revision_pin, scope_mode, campaign_id, native])

  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Open assertion · {assertionId}</summary>
    {open && (read?.wave !== wave ? <p role="status">Reading the recorded assertion…</p>
      : read.assertion ? <><p>{read.assertion.subject_entity_id} · {read.assertion.predicate}</p>
        <pre>{JSON.stringify(read.assertion.value, null, 2)}</pre>
        {read.excerpts?.map(excerpt => <blockquote key={excerpt.evidence_ref_id}>{excerpt.text}</blockquote>)}</>
      : <p role="alert">The assertion is unavailable at the recorded revision.</p>)}
  </details>
}
