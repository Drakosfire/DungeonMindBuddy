import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BuddyTurnInspection, useBuddyTurnInspection } from './BuddyTurnInspection'
import type { WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { startReadWave } from '../../api/inFlightReads'
import { setNativeGraphAccessToken } from '../../api/liveApi'

const binding = { worldId: 'world', conversationId: 'conversation', turnId: 'turn', lifecycle: 'completed' as const }
function response(id = 'captured', current = binding, recording = false): WorldAgentTurnContextTraceResponse {
  return { schema: 'dmb_agent_turn_context_trace_response_v1', world_id: current.worldId, turn_id: current.turnId,
    attempts: [{ schema: 'dmb_turn_context_trace_v1', trace_id: id, world_id: current.worldId,
      conversation_id: current.conversationId, turn_id: current.turnId, attempt: 1, execution_start_sequence: 0,
      started_at: '2026-10-13T00:00:00Z', closed_at: recording ? null : '2026-10-13T00:00:01Z',
      terminal_status: recording ? null : 'completed', capture_status: recording ? 'recording' : 'complete',
      capture_failure_code: null, observations: [] }] }
}
function Probe({ name, enabled, current = binding }: { name: string; enabled: boolean; current?: typeof binding }) {
  const value = useBuddyTurnInspection(current, enabled)
  return enabled ? <section aria-label={name}><p>{name}: {value.data?.attempts[0]?.trace_id ?? 'loading'}</p>
    {value.error && <p role="alert">{value.error}</p>}<button onClick={value.refresh}>Refresh {name}</button></section> : null
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
afterEach(() => vi.useRealTimers())

describe('one captured observation for an inspected turn', () => {
  it('shares Debug and Prompt demand, retains a closed observation, and explicitly refreshes new attempts', async () => {
    const load = vi.fn().mockResolvedValueOnce(response('first')).mockResolvedValue(response('new-attempt'))
    const view = render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /><Probe name="Prompt" enabled={false} /></BuddyTurnInspection>)
    await screen.findByText('Debug: first')
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled={false} /><Probe name="Prompt" enabled /></BuddyTurnInspection>)
    await screen.findByText('Prompt: first')
    expect(load).toHaveBeenCalledTimes(1)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled={false} /><Probe name="Prompt" enabled={false} /></BuddyTurnInspection>)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /><Probe name="Prompt" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: first')
    expect(load).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Refresh Prompt' }))
    await screen.findByText('Debug: new-attempt')
    expect(screen.getByText('Prompt: new-attempt')).toBeInTheDocument()
    expect(load).toHaveBeenCalledTimes(2)
  })

  it('reacquires when the owning turn lifecycle reveals a new attempt', async () => {
    const load = vi.fn().mockResolvedValueOnce(response('closed-attempt'))
      .mockResolvedValueOnce(response('recording-attempt', binding, true)).mockResolvedValue(response('new-terminal'))
    const view = render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: closed-attempt')
    view.rerender(<BuddyTurnInspection {...binding} lifecycle="running" load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: recording-attempt')
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: new-terminal')
    expect(load).toHaveBeenCalledTimes(3)
  })

  it('keeps a mismatched or disabled consumer from acquiring private bytes', async () => {
    const load = vi.fn().mockResolvedValue(response())
    render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled current={{...binding, turnId:'foreign'}} /><Probe name="Prompt" enabled={false} /></BuddyTurnInspection>)
    await screen.findByRole('alert')
    await act(async () => {})
    expect(load).not.toHaveBeenCalled()
  })

  it('closing one pending consumer preserves the other; closing both cancels and fences the late body', async () => {
    const old = deferred<WorldAgentTurnContextTraceResponse>()
    const load = vi.fn().mockReturnValueOnce(old.promise).mockResolvedValue(response('fresh'))
    const view = render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /><Probe name="Prompt" enabled /></BuddyTurnInspection>)
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    const signal = load.mock.calls[0][2] as AbortSignal
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled={false} /><Probe name="Prompt" enabled /></BuddyTurnInspection>)
    expect(signal.aborted).toBe(false)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled={false} /><Probe name="Prompt" enabled={false} /></BuddyTurnInspection>)
    expect(signal.aborted).toBe(true)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /><Probe name="Prompt" enabled={false} /></BuddyTurnInspection>)
    await screen.findByText('Debug: fresh')
    await act(async () => old.resolve(response('late-private')))
    expect(screen.queryByText('Debug: late-private')).not.toBeInTheDocument()
  })

  it('runs one recording poller for two views and stops after terminal capture', async () => {
    vi.useFakeTimers()
    const load = vi.fn().mockResolvedValueOnce(response('recording', binding, true)).mockResolvedValue(response('finished'))
    render(<BuddyTurnInspection {...binding} lifecycle="running" load={load}><Probe name="Debug" enabled /><Probe name="Prompt" enabled /></BuddyTurnInspection>)
    await act(async () => {})
    expect(load).toHaveBeenCalledTimes(1)
    await act(async () => vi.advanceTimersByTimeAsync(2000))
    expect(screen.getByText('Debug: finished')).toBeInTheDocument()
    expect(screen.getByText('Prompt: finished')).toBeInTheDocument()
    await act(async () => vi.advanceTimersByTimeAsync(10000))
    expect(load).toHaveBeenCalledTimes(2)
  })

  it.each(['credential', 'mutation'])('hides retained private bytes on a %s wave and rejects the previous completion', async kind => {
    let credential = 0
    const advance = () => kind === 'credential' ? setNativeGraphAccessToken(`inspection-credential-${++credential}`) : startReadWave()
    const retired = deferred<WorldAgentTurnContextTraceResponse>(), fresh = deferred<WorldAgentTurnContextTraceResponse>()
    const load = vi.fn().mockResolvedValueOnce(response('private-old')).mockReturnValueOnce(retired.promise).mockReturnValueOnce(fresh.promise)
    render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: private-old')
    act(advance)
    expect(screen.queryByText('Debug: private-old')).not.toBeInTheDocument()
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
    act(advance)
    await waitFor(() => expect(load).toHaveBeenCalledTimes(3))
    expect((load.mock.calls[1][2] as AbortSignal).aborted).toBe(true)
    await act(async () => fresh.resolve(response('new-authority')))
    await act(async () => retired.resolve(response('late-old-authority')))
    expect(screen.getByText('Debug: new-authority')).toBeInTheDocument()
    expect(screen.queryByText('Debug: late-old-authority')).not.toBeInTheDocument()
  })

  it.each(['worldId', 'conversationId', 'turnId'] as const)('fences %s ABA and never admits the first owner after returning', async field => {
    const old = deferred<WorldAgentTurnContextTraceResponse>()
    const other = { ...binding, [field]: 'other' }
    const load = vi.fn().mockReturnValueOnce(old.promise).mockResolvedValueOnce(response('other', other)).mockResolvedValueOnce(response('returned'))
    const view = render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    view.rerender(<BuddyTurnInspection {...other} load={load}><Probe name="Debug" enabled current={other} /></BuddyTurnInspection>)
    await screen.findByText('Debug: other')
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: returned')
    await act(async () => old.resolve(response('retired-A')))
    expect(screen.queryByText('Debug: retired-A')).not.toBeInTheDocument()
  })

  it('releases oversized closed snapshots while preserving active display and truthful refresh failure', async () => {
    const large = response('large')
    large.attempts[0].observations = [{ kind: 'context_snapshot', sequence: 0, elapsed_ms: 0, stage: 'before',
      materials: [{ item_id: 'large', state: 'model_context', role: 'user', text: 'x'.repeat(270000) }] }]
    const load = vi.fn().mockResolvedValueOnce(large).mockResolvedValueOnce(response('reopened'))
      .mockRejectedValueOnce(new Error('offline')).mockResolvedValue(response('retried'))
    const view = render(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: large')
    expect(load).toHaveBeenCalledTimes(1)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled={false} /></BuddyTurnInspection>)
    view.rerender(<BuddyTurnInspection {...binding} load={load}><Probe name="Debug" enabled /></BuddyTurnInspection>)
    await screen.findByText('Debug: reopened')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh Debug' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The message will not be resent')
    expect(screen.getByText('Debug: reopened')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh Debug' }))
    await screen.findByText('Debug: retried')
    expect(load).toHaveBeenCalledTimes(4)
  })
})
