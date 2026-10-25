import { createContext, useCallback, useContext, useEffect, useId, useLayoutEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react'
import { getWorldAgentTurnContextTrace, getWorldAgentTurnPrompt } from '../../api/liveApi'
import type { WorldAgentTurnContextTraceResponse, BuddyPromptEvidence, BuddyTracePromptReference, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import type { AgentConversationTurnLifecycleV1 } from '../../api/types'
import { getReadWaveVersion, subscribeReadWave } from '../../api/inFlightReads'

const CLOSED_SNAPSHOT_MAX_BYTES = 256 * 1024
interface Binding { worldId: string; conversationId: string; turnId: string }
interface Snapshot { key: string; data: WorldAgentTurnContextTraceResponse; bytes: number }
interface Inspection extends Binding {
  readPrompt: (trace: BuddyTurnContextTrace, reference: BuddyTracePromptReference, signal: AbortSignal) => Promise<BuddyPromptEvidence>
  running: boolean
  data: WorldAgentTurnContextTraceResponse | null
  error: string | null
  refresh: () => void
  demand: (id: string, enabled: boolean) => void
}
const Context = createContext<Inspection | null>(null)

/** One captured observation for a mounted turn, never a current all-attempts authority. */
export function BuddyTurnInspection({ worldId, conversationId, turnId, lifecycle, load = getWorldAgentTurnContextTrace, loadPrompt = getWorldAgentTurnPrompt, children }: Binding & {
  lifecycle: AgentConversationTurnLifecycleV1; load?: typeof getWorldAgentTurnContextTrace; loadPrompt?: typeof getWorldAgentTurnPrompt; children: ReactNode
}) {
  const wave = useSyncExternalStore(subscribeReadWave, getReadWaveVersion, getReadWaveVersion)
  const running = lifecycle === 'accepted' || lifecycle === 'running'
  const key = JSON.stringify([worldId, conversationId, turnId, lifecycle, wave])
  const consumers = useRef(new Set<string>())
  const [consumerCount, setConsumerCount] = useState(0)
  const demand = useCallback((id: string, enabled: boolean) => {
    const current = consumers.current
    if (current.has(id) === enabled) return
    if (enabled) current.add(id); else current.delete(id)
    setConsumerCount(current.size)
  }, [])
  const enabled = consumerCount > 0
  const [loaded, setLoaded] = useState<Snapshot | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const [retry, setRetry] = useState(0)
  const refresh = useCallback(() => setRetry(value => value + 1), [])
  const cache = useRef<Snapshot | null>(null)
  const handledRetry = useRef(0)
  useEffect(() => {
    if (cache.current?.key !== key) {
      cache.current = null
      setLoaded(current => current?.key === key ? current : null)
      setFailure(current => current?.key === key ? current : null)
    }
    if (!enabled) {
      const snapshot = cache.current
      const reusable = !running && snapshot && snapshot.data.attempts.length > 0
        && snapshot.data.attempts.every(trace => trace.closed_at != null && trace.capture_status === 'complete')
      if (snapshot && (!reusable || snapshot.bytes > CLOSED_SNAPSHOT_MAX_BYTES)) {
        cache.current = null
        setLoaded(null)
      }
      return
    }
    if (!worldId || !conversationId || !turnId) return
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const controller = new AbortController()
    let initialMisses = 0
    const owns = () => active && consumers.current.size > 0 && getReadWaveVersion() === wave
    const read = () => void Promise.resolve().then(() => {
      if (!owns()) throw new Error('Inspection owner retired')
      return load(worldId, turnId, controller.signal)
    }).then(data => {
      if (!owns()) return
      if (data.schema !== 'dmb_agent_turn_context_trace_response_v1' || data.world_id !== worldId
        || data.turn_id !== turnId || !Array.isArray(data.attempts)
        || data.attempts.some(trace => trace.schema !== 'dmb_turn_context_trace_v1' || trace.world_id !== worldId
          || trace.turn_id !== turnId || trace.conversation_id !== conversationId)) {
        throw new Error('Trace does not match this conversation turn.')
      }
      const next = { key, data, bytes: new TextEncoder().encode(JSON.stringify(data)).byteLength }
      cache.current = next
      setLoaded(next)
      setFailure(null)
      if (running) timer = setTimeout(read, 2000)
    }).catch(() => {
      if (owns()) {
        setFailure({ key, message: 'Execution trace is unavailable. The message will not be resent.' })
        // Admission and first capture may trail the submitted request. Retry only
        // initial misses, boundedly; an interrupted established read still pauses.
        if (running && cache.current?.key !== key && initialMisses++ < 5) timer = setTimeout(read, 2000)
      }
    })
    const explicitRetry = handledRetry.current !== retry
    handledRetry.current = retry
    if (cache.current?.key !== key || explicitRetry) {
      setFailure(null)
      read()
    } else if (running) timer = setTimeout(read, 2000)
    return () => { active = false; clearTimeout(timer); controller.abort() }
  }, [enabled, key, worldId, turnId, conversationId, running, load, retry, wave])
  const promptCache = useRef<{ key: string; values: Map<string, BuddyPromptEvidence> }>({ key, values: new Map() })
  useEffect(() => { if (promptCache.current.key !== key) promptCache.current = { key, values: new Map() } }, [key])
  const readPrompt = useCallback(async (trace: BuddyTurnContextTrace, reference: BuddyTracePromptReference, signal: AbortSignal) => {
    if (trace.world_id !== worldId || trace.conversation_id !== conversationId || trace.turn_id !== turnId
      || getReadWaveVersion() !== wave || signal.aborted) throw new Error('Prompt owner retired')
    if (promptCache.current.key !== key) promptCache.current = { key, values: new Map() }
    const owned = promptCache.current
    const identity = JSON.stringify([trace.trace_id, trace.attempt, reference.provider_attempt_id,
      reference.evidence_id, reference.payload_sha256, reference.payload_utf8_bytes])
    const cached = owned.values.get(identity)
    if (cached) return cached
    // The API shares pending transports; this owner retains only validated results
    // for sequential Debug/Evidence Trail inspection of the same immutable call.
    const evidence = await loadPrompt(worldId, turnId, trace.trace_id, reference.provider_attempt_id, signal)
    if (signal.aborted || getReadWaveVersion() !== wave || promptCache.current !== owned) throw new Error('Prompt owner retired')
    if (evidence.schema !== 'dmb_agent_prompt_evidence_v1' || evidence.world_id !== worldId
      || evidence.conversation_id !== conversationId || evidence.turn_id !== turnId
      || evidence.trace_id !== trace.trace_id || evidence.attempt !== trace.attempt
      || evidence.reference.provider_attempt_id !== reference.provider_attempt_id
      || evidence.reference.evidence_id !== reference.evidence_id
      || evidence.reference.payload_sha256 !== reference.payload_sha256
      || evidence.reference.payload_utf8_bytes !== reference.payload_utf8_bytes) throw new Error('Prompt binding differs')
    const body = JSON.parse(evidence.payload_json)
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('Malformed prompt envelope')
    owned.values.set(identity, evidence)
    return evidence
  }, [key, worldId, conversationId, turnId, wave, loadPrompt])
  // Epoch and exact binding are checked during render, before effect cleanup.
  return <Context.Provider value={{ worldId, conversationId, turnId, running, readPrompt,
    data: loaded?.key === key ? loaded.data : null,
    error: failure?.key === key ? failure.message : null, refresh, demand }}>{children}</Context.Provider>
}

export function useBuddyTurnInspection(binding: Binding, enabled: boolean): Inspection {
  const inspection = useContext(Context)
  if (!inspection) throw new Error('Trace inspection requires its turn owner.')
  const id = useId()
  const matches = binding.worldId === inspection.worldId && binding.conversationId === inspection.conversationId
    && binding.turnId === inspection.turnId
  useLayoutEffect(() => {
    inspection.demand(id, enabled && matches)
    return () => inspection.demand(id, false)
  }, [inspection.demand, id, enabled, matches])
  return matches ? inspection : { ...inspection, data: null, error: 'Trace does not match this conversation turn.' }
}

export function useBuddyPromptReader() {
  const inspection = useContext(Context)
  if (!inspection) throw new Error('Prompt inspection requires its turn owner.')
  return inspection.readPrompt
}
