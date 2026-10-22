/** Real exclusion semantics for same-origin recovery tests; each test gets its own manager. */
export function testCombatLocks(): LockManager {
  const held = new Set<string>();
  return {request: async (name: string, _options: unknown, callback: (lock: Lock | null) => unknown) => {
    // Native lock callbacks run after the prior callback's release settles.
    await Promise.resolve(); await Promise.resolve();
    if (held.has(name)) return callback(null);
    held.add(name);
    try {return await callback({name, mode:'exclusive'} as Lock);}
    finally {held.delete(name);}
  }} as unknown as LockManager;
}
