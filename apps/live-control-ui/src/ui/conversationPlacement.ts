import { useSyncExternalStore } from 'react'
export type ConversationPlacement = 'side' | 'bottom' | 'float'
const key = 'buddy.conversation.placement'
const valid = (value: unknown): value is ConversationPlacement => value === 'side' || value === 'bottom' || value === 'float'
let fallback: ConversationPlacement = 'side'
const listeners = new Set<() => void>()
function read(): ConversationPlacement {
  try { const value = window.localStorage.getItem(key); return valid(value) ? value : fallback } catch { return fallback }
}
function subscribe(listener: () => void) {
  listeners.add(listener)
  const storage = (event: StorageEvent) => { if (event.key === key || event.key === null) listener() }
  window.addEventListener('storage', storage)
  return () => { listeners.delete(listener); window.removeEventListener('storage', storage) }
}
function setPlacement(value: ConversationPlacement) {
  fallback = value
  try { window.localStorage.setItem(key, value) } catch { /* Placement still works when browser storage is unavailable. */ }
  listeners.forEach(listener => listener())
}
/** Shared browser preference, independent of World, surface, conversation and content. */
export function useConversationPlacement() {
  const placement = useSyncExternalStore(subscribe, read, () => 'side' as const)
  return [placement, setPlacement] as const
}
