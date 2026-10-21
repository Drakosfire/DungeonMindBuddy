import type { WorldPlanSourceOpenTargetV2 } from '../../api/types'

export function sourceCitationTitle(target: WorldPlanSourceOpenTargetV2): string {
  return target.kind === 'related_recap_context'
    ? target.canonical_heading.replace(/^#{1,6}\s*/, '')
    : 'Open cited source'
}

/** Names come from registered source metadata, never opaque IDs or model prose. */
export function BuddySourceProvenance({ target, name, lines }: {
  target: WorldPlanSourceOpenTargetV2; name?: string | null; lines?: { start: number; end: number }
}) {
  return <div className="buddy-source-provenance">
    <strong>{name || (target.kind === 'related_recap_context' ? sourceCitationTitle(target) : 'Source name unavailable')}</strong>
    {lines && <p>{lines.start === lines.end ? `Line ${lines.start}` : `Lines ${lines.start}–${lines.end}`}</p>}
  </div>
}
