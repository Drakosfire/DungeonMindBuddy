import type { BuddyTraceObservation, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import { traceCostEstimate } from './traceCostEstimate'

export function traceSnapshotLabel(event: Extract<BuddyTraceObservation, {kind: 'context_snapshot'}>): string {
  return event.snapshot_kind === 'provider_input' ? 'Working context · prepared input'
    : event.snapshot_kind === 'provider_response' ? 'Provider response · unvalidated'
    : event.snapshot_kind === 'validated_answer' ? 'Validated reply · captured context'
    : event.snapshot_kind === 'compaction_input' ? 'Working context · before compaction'
    : event.snapshot_kind === 'compaction_output' ? 'Working context · after compaction'
    : `Working context · ${event.stage} this turn`
}

function describe(event: BuddyTraceObservation): string {
  switch (event.kind) {
    case 'failure': return `${event.phase === 'trace_capture' ? 'Trace capture incomplete' : 'Execution failed'} · ${event.code}\n   Stage: ${event.stage ?? event.phase}${event.exception_type ? ` · ${event.exception_type}` : ''}${event.diagnostic_id ? `\n   Private diagnostic: ${event.diagnostic_id}` : ''}`
    case 'provider_call': {
      const cost = traceCostEstimate(event)
      return `${event.model} · ${event.outcome}\n   Provider call: ${event.provider_attempt_id ?? 'identity not captured'}${event.duration_ms == null ? '' : `\n   Provider duration: ${(event.duration_ms / 1000).toFixed(2)}s`}${event.input_tokens == null && event.output_tokens == null ? '\n   Actual token usage not captured.' : `\n   Provider-reported usage: ${event.input_tokens ?? 'unavailable'} input · ${event.output_tokens ?? 'unavailable'} output`}${event.input_upper_bound == null ? '' : `\n   Input ceiling: ${event.input_upper_bound} · conservative estimate, not actual usage`}${cost == null ? '' : `\n   Estimated cost: $${cost.toFixed(6)} USD · list rate, not billed cost (input × $0.042/million; output free; rates checked Oct 24, 2026)`}`
    }
    case 'source_passage':
    case 'source_passage_reuse': return `${event.source_name?.trim() || 'Source name unavailable'}${event.line_start == null ? '' : ` · lines ${event.line_start}–${event.line_end}`} · ${event.kind === 'source_passage_reuse' ? 'reused' : event.outcome}`
    case 'graph_tool': return `Explore World graph · ${event.request.operation} · ${event.result.outcome} · coverage ${event.result.coverage_status}`
    case 'prompt_reference': return `Working context · composed input prompt · ${event.model}\n   Captured prompt reference: ${event.evidence_id}`
    case 'context_snapshot': return `${traceSnapshotLabel(event)} · ${event.materials.length} captured material items`
    case 'context_decision': return `Context ${event.action} · ${event.reason_code} · ${event.policy_version}`
  }
}

/** Export captured data only; no lazy prompt/source fetches or private exception files. */
export function buddyTraceText(trace: BuddyTurnContextTrace): string {
  const failed = trace.terminal_status === 'failed' || trace.terminal_status === 'interrupted'
  const failures = trace.observations.filter(event => event.kind === 'failure' && event.phase !== 'trace_capture')
  // A JSON string avoids Markdown fences in user-authored captured prose closing the record block.
  const record = JSON.stringify(trace, null, 2).split('\n').map(line => `    ${line}`).join('\n')
  return [
    `# ${failed ? 'Reply error report' : 'How Buddy built this reply'}`,
    `World: ${trace.world_id}\nConversation: ${trace.conversation_id}\nTurn: ${trace.turn_id}\nTrace: ${trace.trace_id}\nAttempt: ${trace.attempt}`,
    `Reply status: ${trace.terminal_status ?? 'in progress'}\nCapture status: ${trace.capture_status}${trace.capture_failure_code ? ` · ${trace.capture_failure_code}` : ''}\nStarted: ${trace.started_at}\nClosed: ${trace.closed_at ?? 'not closed'}`,
    ...(failed && !failures.length ? ['The specific cause was not recorded for this attempt.'] : []),
    'Capture completeness is separate from reply success. Historical observations grant no new evidence authority.',
    '## Execution timeline',
    'Each recorded observation is listed, including lifecycle and usage updates for the same provider call; do not sum those updates as separate charges.',
    ...trace.observations.map(event => `${event.sequence + 1}. ${(event.elapsed_ms / 1000).toFixed(1)}s · ${describe(event)}`),
    '## Complete captured record',
    'This attempt only. Includes recorded payloads and source excerpts. Referenced prompts and historical passages remain references; no additional material was fetched. Private exception diagnostic files are not included.',
    record,
  ].join('\n\n') + '\n'
}
