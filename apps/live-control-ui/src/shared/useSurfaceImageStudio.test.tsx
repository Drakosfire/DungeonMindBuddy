import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useSurfaceImageStudio } from './useSurfaceImageStudio';

it('preserves the first prompt across duplicate opens and closes only the current session', () => {
  const { result } = renderHook(() => useSurfaceImageStudio('world:plan', true));
  const before = result.current;
  act(() => {
    expect(before.open('First exact prompt\nwith details')).toBe(true);
    expect(before.open('Replacement')).toBe(false);
  });
  expect(result.current.session?.prompt).toBe('First exact prompt\nwith details');
  act(() => before.close());
  expect(result.current.session).not.toBeNull();
  const oldClose = result.current.close;
  act(() => oldClose());
  act(() => { expect(result.current.open('Second')).toBe(true); });
  act(() => oldClose());
  expect(result.current.session?.prompt).toBe('Second');
});

it('refuses unavailable and stale hosts including A to B to A navigation', () => {
  const { result, rerender } = renderHook(({ id, ready }) => useSurfaceImageStudio(id, ready), { initialProps: { id: 'A', ready: true } });
  const original = result.current;
  rerender({ id: 'A', ready: false });
  act(() => { expect(original.open('Unavailable')).toBe(false); });
  rerender({ id: 'B', ready: true });
  rerender({ id: 'A', ready: true });
  act(() => { expect(original.open('Stale A')).toBe(false); });
  act(() => { expect(result.current.open('Current A')).toBe(true); });
  rerender({ id: 'B', ready: true });
  expect(result.current.session).toBeNull();
});
