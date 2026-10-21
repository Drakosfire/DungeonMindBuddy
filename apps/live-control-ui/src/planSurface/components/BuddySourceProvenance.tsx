import type { WorldPlanSourceOpenTargetV2 } from '../../api/types'

export function sourceCitationTitle(target: WorldPlanSourceOpenTargetV2): string {
  const session = target.kind === 'related_recap_context'
    ? [target.source_campaign_id, target.canonical_heading.replace(/^#{1,6}\s*/, '')].filter(Boolean).join(' · ')
    : null
  return [session, `Source: ${target.source_artifact_id}`, `Revision: ${target.source_revision_id}`].filter(Boolean).join('\n')
}

/** Identity comes from the validated saved target, never model prose or ID guessing. */
export function BuddySourceProvenance({ target, lines }: { target: WorldPlanSourceOpenTargetV2; lines?: { start: number; end: number } }) {
  return <dl className="buddy-source-provenance">
    <dt>Source</dt><dd>{target.source_artifact_id}</dd>
    <dt>Revision</dt><dd>{target.source_revision_id}</dd>
    {lines && <><dt>Passage</dt><dd>{lines.start === lines.end ? `Line ${lines.start}` : `Lines ${lines.start}–${lines.end}`}</dd></>}
    {target.kind === 'related_recap_context' && <><dt>Session</dt><dd>{target.canonical_heading.replace(/^#{1,6}\s*/, '')}</dd>
      {target.source_campaign_id && <><dt>Campaign</dt><dd>{target.source_campaign_id}</dd></>}</>}
  </dl>
}
