/** Pending transport sharing only: no response, error or TTL survives settlement. */
type Entry<T> = { promise: Promise<T>; controller: AbortController; subscribers: number; settled: boolean };
const pending = new Map<string, Entry<unknown>>();
const MAX_TRACKED_READS = 64;
let readWaveVersion = 0;
const readWaveListeners = new Set<() => void>();
export function getReadWaveVersion(): number { return readWaveVersion; }
export function subscribeReadWave(listener: () => void): () => void {
  readWaveListeners.add(listener);
  return () => { readWaveListeners.delete(listener); };
}

/** A mutation starts a fresh acquisition wave; existing owners keep their reads. */
export function startReadWave(): void {
  pending.clear();
  readWaveVersion += 1;
  for (const listener of [...readWaveListeners]) {
    try { listener(); } catch (error) { console.error("Read-wave observer failed", error); }
  }
}

export function shareInFlightRead<T>(key: string, loader: (signal: AbortSignal) => Promise<T>, signal?: AbortSignal | null): Promise<T> {
  if (signal?.aborted) return Promise.reject(signal.reason ?? new DOMException("Read cancelled", "AbortError"));
  let entry = pending.get(key) as Entry<T> | undefined;
  if (!entry) {
    const controller = new AbortController();
    let owned: Entry<T>;
    owned = { controller, subscribers: 0, settled: false, promise: Promise.resolve().then(() => {
      // A caller can release and an equivalent owner can subscribe again in
      // the same commit (React StrictMode rehearses effects this way). Avoid
      // dispatching when the read was abandoned before its loader starts.
      if (controller.signal.aborted || !owned.subscribers) {
        throw controller.signal.reason ?? new DOMException("Read cancelled", "AbortError");
      }
      return loader(controller.signal);
    }) };
    entry = owned;
    // Beyond the bounded registry, reads still work with their own cancellation.
    if (pending.size < MAX_TRACKED_READS) pending.set(key, owned);
    const settle = () => {
      owned.settled = true;
      if (pending.get(key) === owned) pending.delete(key);
    };
    void owned.promise.then(settle, settle);
  }
  const owned = entry;
  owned.subscribers += 1;
  return new Promise<T>((resolve, reject) => {
    let done = false;
    const release = () => {
      done = true;
      signal?.removeEventListener("abort", cancel);
      owned.subscribers -= 1;
      if (!owned.subscribers && !owned.settled) {
        // Keep the pending identity through this synchronous turn so a
        // replacement effect can take ownership before transport is aborted.
        // The loader also checks subscriber count before dispatch, so an
        // already-abandoned read never starts merely because cancellation is
        // deferred by one microtask.
        queueMicrotask(() => {
          if (owned.subscribers || owned.settled) return;
          if (pending.get(key) === owned) pending.delete(key);
          owned.controller.abort();
        });
      }
    };
    const cancel = () => {
      if (done) return;
      release();
      reject(signal?.reason ?? new DOMException("Read cancelled", "AbortError"));
    };
    signal?.addEventListener("abort", cancel, { once: true });
    void owned.promise.then(value => {
      if (done) return;
      release(); resolve(value);
    }, error => {
      if (done) return;
      release(); reject(error);
    });
  });
}
