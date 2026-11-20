import { useEffect, useRef, useState } from "react";
import { connectNativeGraphSession, ensureNativeGraphSession, revokeNativeGraphSession } from "../api/liveApi";

export function NativeGraphAccessControl({ onChanged }: { onChanged: (available: boolean) => void }) {
  const [status, setStatus] = useState<string | null>(null);
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;
  useEffect(() => {
    let mounted = true;
    void ensureNativeGraphSession().then(() => {
      if (mounted) { setStatus("Local Graph session active."); onChangedRef.current(true); }
    }).catch(() => {
      if (mounted) { setStatus("Local Graph session unavailable."); onChangedRef.current(false); }
    });
    return () => { mounted = false; };
  }, []);
  return (
    <section aria-label="Native Graph access">
      <button type="button" onClick={() => { void connectNativeGraphSession().then(() => { setStatus("Local Graph session active."); onChanged(true); }).catch(() => setStatus("Local Graph session unavailable.")); }}>Connect local Graph session</button>
      <button type="button" onClick={() => { void revokeNativeGraphSession().then(() => { setStatus("Local Graph session revoked."); onChanged(false); }).catch(() => setStatus("Local Graph session could not be revoked.")); }}>Revoke local Graph session</button>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
