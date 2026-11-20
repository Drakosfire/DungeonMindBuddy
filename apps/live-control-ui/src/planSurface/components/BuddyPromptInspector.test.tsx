import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BuddyPromptInspector as PromptInspector } from './BuddyPromptInspector'
import { startReadWave } from '../../api/inFlightReads'
import { BuddyTurnInspection } from './BuddyTurnInspection'
import { ResponseEvidenceTabs } from './ResponseEvidenceTabs'
import type { BuddyPromptEvidence, BuddyTracePromptReference, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import { getWorldAgentTurnPrompt } from '../../api/liveApi'
import { PreparedRequestInspector } from './PreparedRequestInspector'
vi.mock('../../api/liveApi', () => ({ getWorldAgentTurnPrompt: vi.fn(), getWorldAgentTurnContextTrace: vi.fn() }))
const load = vi.mocked(getWorldAgentTurnPrompt)
const reference = (id: string, sequence = 0): BuddyTracePromptReference => ({ kind: 'prompt_reference', sequence, elapsed_ms: 0,
  provider_attempt_id: id, evidence_id: `evidence-${id}`, provider: 'synthetic', model: `model-${id}`, api_mode: 'responses',
  serializer_version: 'fixture', payload_sha256: 'a'.repeat(64), payload_utf8_bytes: 12 })
function trace(ids = ['one']): BuddyTurnContextTrace {
  return { schema: 'dmb_turn_context_trace_v1', world_id: 'world', conversation_id: 'conversation', turn_id: 'turn', trace_id: 'trace', attempt: 1,
    execution_start_sequence: 0, started_at: '', closed_at: null, terminal_status: null, capture_status: 'recording', capture_failure_code: null,
    observations: ids.map(reference) }
}
function payload(t: BuddyTurnContextTrace, ref: BuddyTracePromptReference, instructions = 'Be a helpful GM'): BuddyPromptEvidence {
  return { schema: 'dmb_agent_prompt_evidence_v1', world_id: t.world_id, conversation_id: t.conversation_id,
    turn_id: t.turn_id, trace_id: t.trace_id, attempt: t.attempt, reference: ref,
    payload_json: JSON.stringify({ model: ref.model, instructions, input: [{ role: 'user', content: '<script>Literal text</script>' }], tools: [{ type: 'function', name: 'read_graph' }] }) }
}
function BuddyPromptInspector({ trace: t }: { trace: BuddyTurnContextTrace | null }) {
  return <BuddyTurnInspection worldId={t?.world_id ?? 'world'} conversationId={t?.conversation_id ?? 'conversation'}
    turnId={t?.turn_id ?? 'turn'} lifecycle="completed"><PromptInspector trace={t} /></BuddyTurnInspection>
}
beforeEach(() => { load.mockReset() })
describe('The Prompt in response evidence', () => {
  it('pretty prints JSON-valued input strings while keeping exact input and envelope bytes available', () => {
    const input = '{"instruction":"Make a table","draft_markdown":"# Edge\\nA fort town"}'
    const payloadJson = JSON.stringify({ input, instructions: 'Ordinary prose' })
    render(<PreparedRequestInspector payloadJson={payloadJson} />)
    fireEvent.click(screen.getByRole('button', { name: 'input /input' }))
    const text = () => screen.getByLabelText('Captured request').querySelector('pre')?.textContent
    expect(text()).toBe(JSON.stringify(JSON.parse(input), null, 2))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
    expect(text()).toBe(input)
    fireEvent.click(screen.getByRole('button', { name: 'Show full request' }))
    expect(text()).toBe(payloadJson)
    fireEvent.click(screen.getByRole('button', { name: 'System instructions /instructions' }))
    expect(text()).toBe('Ordinary prose')
  })
  it('is a separate tab, loads only when opened, and shows exact envelope components', async () => {
    const t = trace()
    load.mockResolvedValue(payload(t, reference('one')))
    render(<ResponseEvidenceTabs evidence={<p>Saved evidence</p>} prompt={<BuddyPromptInspector trace={t} />} />)
    expect(screen.getByRole('tab', { name: 'Evidence Trail' })).toHaveAttribute('aria-selected', 'true')
    expect(load).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('tab', { name: 'The Prompt' }))
    await screen.findByRole('heading', { name: 'Full composed request' })
    expect(load).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: /System instructions/ }))
    expect(screen.getByLabelText('Captured request').querySelector('pre')).toHaveTextContent('Be a helpful GM')
    expect(screen.getByLabelText('Captured request').querySelector('pre')).not.toHaveTextContent('Literal text')
    fireEvent.click(screen.getByRole('button', { name: 'Show full request' }))
    expect(screen.getByLabelText('Captured request').querySelector('pre')).toHaveTextContent('Literal text')
    expect(document.querySelector('script')).toBeNull()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
    expect(screen.getByLabelText('Captured request').querySelector('pre')?.textContent).toBe(payload(t, reference('one')).payload_json)
  })
  it('does not reconstruct older uncaptured calls', () => {
    const t = trace([])
    t.observations = [{ kind: 'provider_call', provider: 'openai', model: 'old', outcome: 'authorized', provider_attempt_id: 'old', sequence: 0, elapsed_ms: 0 }]
    render(<BuddyPromptInspector trace={t} />)
    expect(screen.getByText(/No complete request was captured for this call/)).toBeInTheDocument()
    expect(load).not.toHaveBeenCalled()
  })
  it('clears the old body on call changes and ignores late responses', async () => {
    const t = trace(['one', 'two'])
    let resolveTwo!: (value: BuddyPromptEvidence) => void
    load.mockImplementation((_world, _turn, _trace, id) => id === 'two'
      ? new Promise(resolve => { resolveTwo = resolve }) : Promise.resolve(payload(t, reference('one'), 'First request')))
    render(<BuddyPromptInspector trace={t} />)
    fireEvent.change(screen.getByLabelText('Model call'), { target: { value: 'one' } })
    await screen.findByRole('heading', { name: 'Full composed request' })
    fireEvent.click(screen.getByRole('button', { name: /System instructions/ }))
    await act(async () => resolveTwo(payload(t, reference('two'), 'Stale second request')))
    expect(screen.queryByText(/Stale second request/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Captured request')).toHaveTextContent('First request')
    fireEvent.change(screen.getByLabelText('Model call'), { target: { value: 'two' } })
    expect(screen.queryByText('First request')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Loading')
  })
  it('clears synchronously on a World/turn change and rejects foreign response identity', async () => {
    const t = trace()
    load.mockResolvedValue(payload(t, reference('one'), 'Old body'))
    const { rerender } = render(<BuddyPromptInspector trace={t} />)
    await screen.findByRole('heading', { name: 'Full composed request' })
    load.mockResolvedValue(payload(t, reference('one')))
    rerender(<BuddyPromptInspector trace={{ ...t, world_id: 'other-world' }} />)
    expect(screen.queryByText(/Old body/)).not.toBeInTheDocument()
    await screen.findByRole('alert')
    expect(screen.queryByLabelText('Captured request')).not.toBeInTheDocument()
  })
  it('refuses missing or corrupted evidence without a fallback', async () => {
    let reject!: (error: Error) => void
    load.mockImplementation(() => new Promise((_resolve, no) => { reject = no }))
    render(<BuddyPromptInspector trace={trace()} />)
    await act(async () => reject(new Error('integrity failure')))
    expect(screen.getByRole('alert')).toHaveTextContent('No reconstructed request')
  })
})

describe('turn-owned captured request reuse', () => {
  it('reuses validated bytes when Debug and Evidence Trail inspect the same call sequentially', async () => {
    const t = trace()
    load.mockResolvedValue(payload(t, reference('one')))
    const owner = (show: boolean) => <BuddyTurnInspection worldId="world" conversationId="conversation" turnId="turn" lifecycle="completed">
      {show ? <PromptInspector trace={t} /> : null}</BuddyTurnInspection>
    const view = render(owner(true))
    await screen.findByRole('heading', { name: 'Full composed request' })
    expect(load).toHaveBeenCalledTimes(1)
    view.rerender(owner(false))
    view.rerender(owner(true))
    await screen.findByRole('heading', { name: 'Full composed request' })
    expect(load).toHaveBeenCalledTimes(1)
  })
  it('does not retain a rejected body and reacquires on an explicit new inspection', async () => {
    const t = trace()
    load.mockResolvedValueOnce({...payload(t, reference('one')), turn_id:'foreign'}).mockResolvedValue(payload(t, reference('one')))
    const owner = (show: boolean) => <BuddyTurnInspection worldId="world" conversationId="conversation" turnId="turn" lifecycle="completed">
      {show ? <PromptInspector trace={t} /> : null}</BuddyTurnInspection>
    const view = render(owner(true))
    await screen.findByRole('alert')
    view.rerender(owner(false))
    view.rerender(owner(true))
    await screen.findByRole('heading', { name: 'Full composed request' })
    expect(load).toHaveBeenCalledTimes(2)
  })
})

it('fences the previous prompt synchronously when a new read wave retires its owner', async () => {
  const t = trace()
  load.mockResolvedValueOnce(payload(t, reference('one'), 'Old private request')).mockReturnValue(new Promise(() => {}))
  render(<BuddyTurnInspection worldId="world" conversationId="conversation" turnId="turn" lifecycle="completed">
    <PromptInspector trace={t} /></BuddyTurnInspection>)
  await screen.findByRole('heading', { name: 'Full composed request' })
  fireEvent.click(screen.getByRole('button', { name: /System instructions/ }))
  expect(screen.getByLabelText('Captured request')).toHaveTextContent('Old private request')
  act(() => startReadWave())
  expect(screen.queryByLabelText('Captured request')).not.toBeInTheDocument()
  expect(load).toHaveBeenCalledTimes(2)
})
