import { useEffect, useState } from "react";
import { getPlanActionTerminalDiagnostic } from "../../api/liveApi";
import type { ActionTerminalDiagnosticRead } from "../../api/types";

export function ActionTerminalDiagnostic({ worldId, actionId }: { worldId: string; actionId: string }) {
  return <ScopedDiagnostic key={`${worldId}:${actionId}`} worldId={worldId} actionId={actionId} />;
}
function ScopedDiagnostic({ worldId, actionId }: { worldId: string; actionId: string }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Failure details</summary>
    {open && <DiagnosticRead worldId={worldId} actionId={actionId} />}
  </details>;
}
function DiagnosticRead({ worldId, actionId }: { worldId: string; actionId: string }) {
  const [state, setState] = useState<{ value?: ActionTerminalDiagnosticRead; error?: boolean }>({});
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    getPlanActionTerminalDiagnostic(worldId, actionId, controller.signal).then(value => {
      if (!active) return;
      if (value.schema !== "dmb_plan_action_terminal_diagnostic_read_v1"
        || value.world_id !== worldId || value.action_id !== actionId
        || (value.diagnostic && (value.diagnostic.world_id !== worldId
          || value.diagnostic.action_id !== actionId
          || value.diagnostic.schema_version !== "dmb_plan_action_terminal_diagnostic_v1"))) throw new Error("binding");
      setState({ value });
    }).catch(() => { if (active) setState({ error: true }); });
    return () => { active = false; controller.abort(); };
  }, [worldId, actionId]);
  if (state.error) return <p role="alert">Saved failure details are unavailable.</p>;
  if (!state.value) return <p role="status">Loading saved failure details…</p>;
  const diagnostic = state.value.diagnostic;
  return <div>
    <p>No edit is applied by this report. An uncertain outcome remains uncertain; retrying may send another request.</p>
    {!diagnostic || diagnostic.availability === "unavailable" ? <p>
      No valid terminal report was retained. {diagnostic?.unavailable_reason?.replaceAll("_", " ")}
    </p> : <>
      <p>{diagnostic.attribution === "provider_attempt" ? "Verified provider attempt" : "Action-level report; provider attempt not established"}</p>
      <dl>
        <dt>Reason</dt><dd>{diagnostic.failure?.reason.replaceAll("_", " ")}</dd>
        <dt>Reported transition</dt><dd>{diagnostic.failure?.transition.replaceAll("_", " ")}</dd>
        <dt>Reported acknowledgement</dt><dd>{String(diagnostic.failure?.acknowledged)}</dd>
        {diagnostic.failure?.transportExceptionClass && <><dt>Transport type</dt><dd>{diagnostic.failure.transportExceptionClass}</dd></>}
        {diagnostic.failure?.responseStatus && <><dt>Response status</dt><dd>{diagnostic.failure.responseStatus}</dd></>}
        {diagnostic.failure?.incompleteReason && <><dt>Incomplete reason</dt><dd>{diagnostic.failure.incompleteReason.replaceAll("_", " ")}</dd></>}
        {diagnostic.provider_attempt_id && <><dt>Provider attempt</dt><dd>{diagnostic.provider_attempt_id}</dd>
          <dt>Latest durable outcome</dt><dd>{diagnostic.latest_durable_outcome ?? "Not retained"}</dd></>}
      </dl>
    </>}
  </div>;
}
