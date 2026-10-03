import { useId, useState } from "react";
import { setNativeGraphAccessToken } from "../api/liveApi";

/** The same tab-local credential API used by the Plan surface. */
export function NativeGraphAccessControl({ onChanged }: { onChanged: (available: boolean) => void }) {
  const id = useId();
  const [credential, setCredential] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  function update(value: string | null) {
    setNativeGraphAccessToken(value);
    setCredential("");
    setStatus(value ? "Graph credential set in this tab's memory." : "Graph credential cleared.");
    onChanged(Boolean(value));
  }
  return (
    <section aria-label="Native Graph access">
      <form onSubmit={(event) => { event.preventDefault(); update(credential.trim() || null); }}>
        <label htmlFor={id}>Local operator Graph credential</label>
        <input id={id} type="password" autoComplete="off" maxLength={4096} value={credential} onChange={(event) => setCredential(event.currentTarget.value)} />
        <button type="submit">Set Graph access</button>
        <button type="button" onClick={() => update(null)}>Clear Graph access</button>
      </form>
      <p>The credential stays in memory in this tab and is sent through the existing native Graph authorization header.</p>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
