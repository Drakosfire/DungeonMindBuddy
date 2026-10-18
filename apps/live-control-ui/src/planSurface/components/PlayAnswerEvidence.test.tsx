import { act, fireEvent, render, screen } from '@testing-library/react'
import { webcrypto } from 'node:crypto'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { PlayAnswerEvidence } from './PlayAnswerEvidence'
import { getWorldOwnedRunbookCommittedRevision, getWorldOwnedPlanCommittedRevision, LiveApiError } from '../../api/liveApi'
import type { AgentConversationTurnProvenanceV1, WorldOwnedRunbookCommittedRevisionV2 } from '../../api/types'
vi.mock('../../api/liveApi', async original => ({
  ...await original<typeof import('../../api/liveApi')>(),
  getWorldOwnedRunbookCommittedRevision: vi.fn(), getWorldOwnedPlanCommittedRevision: vi.fn(),
}))
const read = vi.mocked(getWorldOwnedRunbookCommittedRevision)
const id = '00000000-0000-4000-8000-000000000001'
const work = '00000000-0000-4000-8000-000000000002'
const markdown = '# Saved arrival\n\nThe lake lies below the peaks.'
let sha: string
beforeAll(async () => {
  Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true })
  sha = Buffer.from(await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(markdown))).toString('hex')
})
function provenance(): AgentConversationTurnProvenanceV1 {
  const absent = { resolution: 'absent' as const, kind: null, object_id: null, revision: null,
    content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null }
  return { world_id: 'world', surface_resolution: 'resolved', surface_id: 'play', surface_instance_id: 'play',
    primary_work: { ...absent, resolution: 'resolved', kind: 'run', object_id: id, revision: '4' },
    supporting_work: [
      { ...absent, resolution: 'resolved', kind: 'dmb_play_runbook_v1', object_id: id,
        content_sha256: sha, work_revision_id: work, revision_n: 2 },
      { ...absent, resolution: 'resolved', kind: 'dmb_play_current_beat_v1', object_id: 'beat:arrival', revision: 'v2' },
      { ...absent, resolution: 'resolved', kind: 'dmb_play_current_scene_v1', object_id: 'scene:approach', revision: 'v2' },
    ], selected_object: absent }
}
function source(): WorldOwnedRunbookCommittedRevisionV2 {
  return { schema_version: 'dmb_workspace_committed_revision_v2', scope_mode: 'world', world_id: 'world', campaign_id: null,
    document_id: id, kind: 'runbook', title: 'Saved Runbook', status: 'draft', object_revision: 9,
    work_revision_id: work, revision_n: 2, markdown, content_sha256: sha,
    has_divergent_working_copy: true, target_relpath: null }
}
beforeEach(() => { read.mockReset(); vi.mocked(getWorldOwnedPlanCommittedRevision).mockReset() })
function open() { fireEvent.click(screen.getByRole('button', { name: 'Open pinned Runbook' })) }
describe('Play answer source evidence', () => {
  it('shows saved references without reading, then opens only the exact historical source', async () => {
    read.mockResolvedValue(source())
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    expect(screen.getByText('beat:arrival')).toBeInTheDocument()
    expect(screen.getByText('scene:approach')).toBeInTheDocument()
    expect(read).not.toHaveBeenCalled()
    open()
    expect(await screen.findByRole('heading', { name: 'Saved arrival' })).toBeInTheDocument()
    expect(read).toHaveBeenCalledExactlyOnceWith(id, 'world', 2, sha)
    expect(screen.getByText(/not proof that every passage/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close pinned source' }))
    expect(screen.queryByRole('heading', { name: 'Saved arrival' })).not.toBeInTheDocument()
  })
  it.each(['world_id', 'document_id', 'work_revision_id', 'content_sha256', 'revision_n', 'markdown', 'scope_mode', 'kind'])('rejects mismatched source %s', async field => {
    read.mockResolvedValue({ ...source(), [field]: field === 'revision_n' ? 3 : 'different' } as WorldOwnedRunbookCommittedRevisionV2)
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    open()
    expect(await screen.findByText(/exact saved revision is unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Saved arrival' })).not.toBeInTheDocument()
  })
  it.each(['other world', 'duplicate', 'missing', 'bad pin'])('never reads an invalid saved basis: %s', mode => {
    const p = provenance()
    if (mode === 'other world') p.world_id = 'elsewhere'
    if (mode === 'duplicate') p.supporting_work.push(p.supporting_work[0])
    if (mode === 'missing') p.supporting_work = []
    if (mode === 'bad pin') p.supporting_work[0].revision_n = 0
    render(<PlayAnswerEvidence provenance={p} worldId="world" turnId="turn" />)
    expect(screen.getByText(/exact Runbook reference is unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open pinned Runbook' })).not.toBeInTheDocument()
    expect(read).not.toHaveBeenCalled()
  })
  it.each(['turn', 'world', 'basis', 'unmount'])('discards late private source after %s changes', async mode => {
    let resolve!: (value: WorldOwnedRunbookCommittedRevisionV2) => void
    read.mockReturnValue(new Promise(r => { resolve = r }))
    const p = provenance()
    const mounted = render(<PlayAnswerEvidence provenance={p} worldId="world" turnId="turn" />)
    open()
    if (mode === 'unmount') mounted.unmount()
    else {
      const next = provenance()
      if (mode === 'basis') next.supporting_work[0].revision_n = 3
      mounted.rerender(<PlayAnswerEvidence provenance={next} worldId={mode === 'world' ? 'other' : 'world'} turnId={mode === 'turn' ? 'new' : 'turn'} />)
    }
    await act(async () => { resolve(source()); await Promise.resolve() })
    expect(screen.queryByRole('heading', { name: 'Saved arrival' })).not.toBeInTheDocument()
  })
  it('reads a pinned Plan used as a Runbook only after a 404 on the same identity', async () => {
    read.mockRejectedValue(new LiveApiError('Different kind', 404))
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockResolvedValue({ ...source(), kind: 'plan' })
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    open()
    expect(await screen.findByRole('heading', { name: 'Saved arrival' })).toBeInTheDocument()
    expect(getWorldOwnedPlanCommittedRevision).toHaveBeenCalledExactlyOnceWith(id, 2)
  })
  it.each([401, 403, 409, 500])('does not fall back after HTTP %s', async status => {
    read.mockRejectedValue(new LiveApiError('Refused', status))
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    open()
    expect(await screen.findByText(/exact saved revision is unavailable/)).toBeInTheDocument()
    expect(getWorldOwnedPlanCommittedRevision).not.toHaveBeenCalled()
  })
  it('rejects a foreign Plan returned by the historical reader', async () => {
    read.mockRejectedValue(new LiveApiError('Different kind', 404))
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockResolvedValue({ ...source(), kind: 'plan', world_id: 'foreign' })
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    open()
    expect(await screen.findByText(/exact saved revision is unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Saved arrival' })).not.toBeInTheDocument()
  })
  it('reports read failures without substituting current text', async () => {
    read.mockRejectedValue(new Error('gone'))
    render(<PlayAnswerEvidence provenance={provenance()} worldId="world" turnId="turn" />)
    open()
    expect(await screen.findByText(/exact saved revision is unavailable/)).toBeInTheDocument()
    expect(read).toHaveBeenCalledTimes(1)
  })
})
