import { describe, expect, it } from 'vitest'
import { traceCostEstimate } from './traceCostEstimate'
const call = {kind:'provider_call' as const, sequence:0, elapsed_ms:0, provider:'typesafe', model:'jev-1.14.0', outcome:'response_received' as const, input_tokens:6689, output_tokens:88}
describe('trace list-rate cost', () => {
  it('prices reported Jev input and free output without using the ceiling', () => {
    expect(traceCostEstimate({...call,input_upper_bound:21159})).toBeCloseTo(0.000280938, 12)
    expect(traceCostEstimate({...call,input_tokens:0})).toBe(0)
  })
  it.each([{model:'other'}, {model:'jev-latest'}, {provider:'other'}, {input_tokens:null}, {input_tokens:-1}, {input_tokens:NaN}, {input_tokens:Infinity}])('does not invent a price for %j', fields => {
    expect(traceCostEstimate({...call,...fields})).toBeNull()
  })
})
