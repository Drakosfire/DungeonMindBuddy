/** Exclusive Web Locks for tests, with a fresh queue per manager. */
export function createTestLocks(): LockManager {
  const pending = new Map<string, Promise<unknown>>();
  return {
    async request(
      name: string,
      optionsOrCallback: LockOptions | LockGrantedCallback<unknown>,
      callback?: LockGrantedCallback<unknown>,
    ) {
      const options = typeof optionsOrCallback === "function" ? {} : optionsOrCallback;
      const work = typeof optionsOrCallback === "function" ? optionsOrCallback : callback!;
      if (options.ifAvailable) {
        await Promise.resolve();
        await Promise.resolve();
      }
      const previous = pending.get(name);
      if (previous && options.ifAvailable) {
        return Promise.resolve().then(() => work(null));
      }
      const task = (previous ?? Promise.resolve()).then(async () => {
        try {
          return await work({ name, mode: "exclusive" });
        } finally {
          if (pending.get(name) === settled) pending.delete(name);
        }
      });
      const settled = task.then(() => undefined, () => undefined);
      pending.set(name, settled);
      return task;
    },
  } as LockManager;
}
