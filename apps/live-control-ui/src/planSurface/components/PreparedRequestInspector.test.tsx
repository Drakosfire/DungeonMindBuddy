import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { PreparedRequestInspector } from './PreparedRequestInspector'
it('shows added removed and changed exact components, retaining full current bytes', () => {
  const previousPayloadJson=JSON.stringify({instructions:'Keep it grounded',messages:[{role:'user',content:'Before'}],tools:[{name:'read'}]})
  const payloadJson=JSON.stringify({instructions:'Keep it grounded',messages:[{role:'user',content:'<script>Now</script>'}],temperature:0})
  render(<PreparedRequestInspector {...{payloadJson,previousPayloadJson}} />)
  expect(screen.getByLabelText('Changes since previous model call')).not.toHaveTextContent('System instructions')
  fireEvent.click(screen.getByText('Changed · Message 1 · user · /messages/0'))
  expect(screen.getByText(/"content": "Before"/)).toBeInTheDocument()
  expect(screen.getAllByText(/<script>Now<\/script>/).length).toBeGreaterThan(0)
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getByText('Removed · Tool 1 · /tools/0')).toBeInTheDocument()
  expect(screen.getByText('Added · temperature · /temperature')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('checkbox',{name:'Exact JSON bytes'}))
  expect(screen.getByLabelText('Captured request').querySelector('pre')?.textContent).toBe(payloadJson)
})
it('does not imply there is a comparison without a previous captured request', () => {
  render(<PreparedRequestInspector payloadJson='{"input":"Only capture"}' />)
  expect(screen.queryByLabelText('Changes since previous model call')).not.toBeInTheDocument()
})
