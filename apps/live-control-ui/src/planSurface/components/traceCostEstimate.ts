import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'

type Call = Extract<BuddyTraceObservation, { kind: 'provider_call' }>
// Public gateway catalog checked 2026-10-24: https://ai-gateway.vercel.sh/v1/models
// Exact version and transport only. This is a list-rate estimate, never a billing receipt.
export function traceCostEstimate(call: Call): number | null {
  const model = call.model.replace(/^typesafe-ai\//, '')
  if (!['jev-1.13.0', 'jev-1.14.0'].includes(model)
    || !['typesafe'].includes(call.provider)
    || call.input_tokens == null || !Number.isFinite(call.input_tokens) || call.input_tokens < 0) return null
  return call.input_tokens * 0.042 / 1_000_000
}
