import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { ActionPromptInspector } from './ActionPromptInspector'
import { getPlanActionPromptIndex, getPlanActionPromptBody } from '../../api/liveApi'
import type { ActionPromptEvidence, ActionPromptReference } from '../../api/types'
vi.mock('../../api/liveApi', () => ({ getPlanActionPromptIndex: vi.fn(), getPlanActionPromptBody: vi.fn() }))
const index = vi.mocked(getPlanActionPromptIndex), body = vi.mocked(getPlanActionPromptBody)
const ref = (id: string): ActionPromptReference => ({ owner_kind: 'plan_action', world_id: 'world', action_id: 'action',
  authorization_event_id: `auth-${id}`, provider_attempt_id: id, provider: 'synthetic', model: id,
  api_mode: 'responses', serializer_version: 'openai-sdk-json-v1', payload_sha256: 'a'.repeat(64), payload_utf8_bytes: 20 })
const evidence = (id: string): ActionPromptEvidence => ({ schema: 'dmb_plan_action_prompt_evidence_v1', world_id: 'world', action_id: 'action',
  reference: ref(id), payload_json: JSON.stringify({ instructions: `private-${id}`, input: '<script>literal</script>' }) })
function open() { const details = screen.getByText('The Prompt').closest('details')!; details.open = true; fireEvent(details, new Event('toggle')) }
beforeEach(() => { index.mockReset(); body.mockReset(); index.mockResolvedValue({ schema: 'dmb_plan_action_prompt_index_v1', world_id: 'world', action_id: 'action', references: [ref('one'), ref('two')] }); body.mockImplementation((_w, _a, id) => Promise.resolve(evidence(id))) })
it('loads only after expansion and resets full view on call choice', async () => {
  render(<ActionPromptInspector worldId="world" actionId="action" />)
  expect(index).not.toHaveBeenCalled(); expect(body).not.toHaveBeenCalled()
  open(); await screen.findByRole('heading', { name: 'Full composed request' })
  expect(body).toHaveBeenCalledWith('world', 'action', 'two', expect.any(AbortSignal))
  fireEvent.click(screen.getByRole('button', { name: 'Show full request' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
  expect(screen.getByLabelText('Captured request')).toHaveTextContent('literal')
  expect(document.querySelector('script')).toBeNull()
  fireEvent.change(screen.getByLabelText('Model call'), { target: { value: 'one' } })
  await screen.findByRole('button', { name: 'Show full request' })
  expect(screen.getByRole('checkbox', { name: 'Exact JSON bytes' })).not.toBeChecked()
})
it('aborts and clears private state on owner changes, ignoring late responses', async () => {
  let resolve!: (value: ActionPromptEvidence) => void
  body.mockImplementation(() => new Promise(done => { resolve = done }))
  const view = render(<ActionPromptInspector worldId="world" actionId="action" />)
  open(); await screen.findByLabelText('Model call')
  const signal = body.mock.calls[0][3]!
  view.rerender(<ActionPromptInspector worldId="other" actionId="other-action" />)
  expect(signal.aborted).toBe(true)
  await act(async () => resolve(evidence('two')))
  expect(screen.queryByLabelText('Captured request')).not.toBeInTheDocument()
  expect(index).toHaveBeenCalledTimes(1)
})
it('rejects a response from another action', async () => {
  body.mockResolvedValue({ ...evidence('two'), action_id: 'foreign' })
  render(<ActionPromptInspector worldId="world" actionId="action" />); open()
  expect(await screen.findByRole('alert')).toHaveTextContent('unavailable')
  expect(screen.queryByLabelText('Captured request')).not.toBeInTheDocument()
})
it('keeps missing historical capture unavailable without body reads', async () => {
  index.mockResolvedValue({ schema: 'dmb_plan_action_prompt_index_v1', world_id: 'world', action_id: 'action', references: [] })
  render(<ActionPromptInspector worldId="world" actionId="action" />); open()
  await screen.findByText(/No complete request was captured/); expect(body).not.toHaveBeenCalled()
})
