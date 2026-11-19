import { deferredComponent } from '../../ui/deferredComponent'
import { useBuddyTurnInspection } from './BuddyTurnInspection'

const BuddyContextTrace = deferredComponent(() => import('./BuddyContextTrace').then(module => ({default: module.BuddyContextTrace})), 'execution trace')

interface Props {
  replyDetails?: boolean
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId, replyDetails }: Props) {
  const { data, error: message, refresh, running } = useBuddyTurnInspection({ worldId, conversationId, turnId }, enabled)
  if (!enabled) return null
  const error = message ? <div><p role="alert">{message}</p><button type="button" onClick={refresh}>Retry trace read</button></div> : null
  if (error && !data) return error
  if (!data) return <p role="status">Loading execution trace…</p>
  const attempts = data.attempts
  const captureControls = <>{error}{!running && attempts.some(trace => trace.closed_at == null || trace.capture_status === 'incomplete')
    ? <p role="note">The turn has ended, but the saved trace is incomplete. Refresh to check for a later capture.</p> : null}
    <button type="button" onClick={refresh}>Refresh trace</button></>
  return <div>{!replyDetails && captureControls}
    {!attempts.length ? running ? <p role="status">Trace capture has not started yet.</p> : <DebugAttempt trace={null} running={running} replyDetails={replyDetails} />
      : attempts.map((trace, index) => index === attempts.length - 1
        ? <DebugAttempt key={trace.trace_id} trace={trace} running={running} replyDetails={replyDetails} />
        : <details key={trace.trace_id}><summary>Earlier attempt {trace.attempt} · {trace.terminal_status ?? 'recording'}</summary><DebugAttempt trace={trace} running={running} replyDetails={replyDetails} /></details>)}
    {replyDetails && <details><summary>Trace status</summary>{captureControls}</details>}
  </div>
}

function DebugAttempt({ trace, running, replyDetails }: { trace: import('../../api/buddyContextTraceTypes').BuddyTurnContextTrace | null; running: boolean; replyDetails?: boolean }) {
  return <BuddyContextTrace trace={trace} ownerActive={running} replyDetails={replyDetails} />
}
