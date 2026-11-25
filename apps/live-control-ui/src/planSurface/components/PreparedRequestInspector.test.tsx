import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { PreparedRequestInspector } from './PreparedRequestInspector'

it('presents instructions before ordered messages and keeps exact bytes in request details', () => {
  const payloadJson = JSON.stringify({
    input: [{ role: 'user', content: 'First message' }, { role: 'assistant', content: 'Second message' }],
    instructions: 'Ground the answer', model: 'example-model', temperature: 0,
  }, null, 1)
  render(<PreparedRequestInspector payloadJson={payloadJson} />)
  const request = screen.getByLabelText('Captured request')
  const headings = within(request).getAllByRole('heading').map(heading => heading.textContent)
  expect(headings).toEqual(['System instructions', 'Message 1 · user', 'Message 2 · assistant'])
  expect(request).toHaveTextContent('Ground the answer')
  expect(request).toHaveTextContent('First message')
  expect(request).not.toHaveTextContent('example-model')
  fireEvent.click(screen.getByText('Request details and exact JSON'))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
  expect(screen.getByLabelText('Request details').querySelector('pre')?.textContent).toBe(payloadJson)
})

it.each(['Normal prose', '42', 'true', 'null'])('preserves message text %s', content => {
  render(<PreparedRequestInspector payloadJson={JSON.stringify({ input: [{ role: 'user', content }] })} />)
  expect(screen.getByLabelText('Captured request').querySelector('pre')?.textContent).toBe(content)
})

it('renders JSON-valued content safely and retains tool details and comparison', () => {
  const content = JSON.stringify({ text: '<script>Evidence</script>', literal: '42' })
  const payloadJson = JSON.stringify({ input: [{ role: 'user', content }], tools: [{ name: 'read' }] })
  render(<PreparedRequestInspector payloadJson={payloadJson} previousPayloadJson='{"input":[]}' />)
  expect(screen.getByLabelText('Captured request')).toHaveTextContent('<script>Evidence</script>')
  expect(document.querySelector('script')).toBeNull()
  fireEvent.click(screen.getByText('Request details and exact JSON'))
  fireEvent.click(screen.getByRole('button', { name: /Tool 1/ }))
  expect(screen.getByLabelText('Request details')).toHaveTextContent('read')
  fireEvent.click(screen.getByText('Changes since previous captured call'))
  expect(screen.getByLabelText('Changes since previous model call')).toHaveTextContent('Added · Message 1')
})

it('retains component comparison and the exact unmodified envelope', () => {
  const previousPayloadJson = JSON.stringify({ instructions: 'Keep it grounded', messages: [{ role: 'user', content: 'Before' }], tools: [{ name: 'read' }] })
  const payloadJson = JSON.stringify({ instructions: 'Keep it grounded', messages: [{ role: 'user', content: '<script>Now</script>' }], temperature: 0 })
  render(<PreparedRequestInspector {...{ payloadJson, previousPayloadJson }} />)
  const changes = screen.getByLabelText('Changes since previous model call')
  expect(changes).not.toHaveAttribute('open')
  fireEvent.click(screen.getByText('Changes since previous captured call'))
  fireEvent.click(screen.getByText('Changed · Message 1 · user · /messages/0'))
  expect(screen.getByText(/"content": "Before"/)).toBeInTheDocument()
  expect(screen.getByText('Removed · Tool 1 · /tools/0')).toBeInTheDocument()
  expect(screen.getByText('Added · temperature · /temperature')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Request details and exact JSON'))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
  expect(screen.getByLabelText('Request details').querySelector('pre')?.textContent).toBe(payloadJson)
})

it('keeps scalar input text and system instructions readable', () => {
  const input = '{"instruction":"Make a table","draft_markdown":"# Edge\\nA fort town"}'
  render(<PreparedRequestInspector payloadJson={JSON.stringify({ input, instructions: 'Ordinary prose' })} />)
  const request = screen.getByLabelText('Captured request')
  expect(request).toHaveTextContent('Ordinary prose')
  expect(request).toHaveTextContent('Make a table')
  fireEvent.click(screen.getByText('Request details and exact JSON'))
  fireEvent.click(screen.getByRole('button', { name: 'input /input' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Exact JSON bytes' }))
  expect(screen.getByLabelText('Request details').querySelector('pre')?.textContent).toBe(input)
})
