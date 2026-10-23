import { useEffect, useState } from "react";
import { getBuddyReadiness, type BuddyReadinessResponse } from "../api/liveApi";

/** Configuration is not a provider health guarantee. Pending request locks belong to the host. */
export function BuddyReadiness({ active, surface, worldGraph, blockedReason }: {
  active: boolean; surface: BuddyReadinessResponse["surface"]; worldGraph: boolean; blockedReason: string | null;
}) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{key: string; message: string; configured: boolean} | null>(null);
  const key = `${surface}:${worldGraph}:${attempt}`;
  useEffect(() => {
    if (!active) return;
    let current = true;
    setResult(null);
    void getBuddyReadiness(surface, worldGraph).then(value => {
      if (!current) return;
      if (value.schema !== "dmb_agent_readiness_v1" || value.surface !== surface || value.world_graph !== worldGraph
          || typeof value.configured !== "boolean" || !Array.isArray(value.issues)
          || !value.issues.every(issue => typeof issue === "string")
          || value.configured !== (value.issues.length === 0)) throw new Error("Invalid readiness response");
      setResult({key, configured: value.configured, message: value.issues.join(" ")});
    }).catch(() => {
      if (current) setResult({key, configured: false, message: "Could not check Buddy. Check the local connection or session, then try again."});
    });
    return () => { current = false; };
  }, [active, surface, worldGraph, key]);
  const checked = result?.key === key ? result : null;
  return <details className="buddy-readiness">
    <summary>{blockedReason ? "Buddy · waiting" : !checked ? "Checking Buddy…" : checked.configured ? "Buddy · configured" : "Buddy · needs attention"}</summary>
    <p role="status">{(blockedReason ?? (!checked ? "Checking local runtime configuration…" : checked.message)) || "Local configuration checked. Remote providers can still fail; this is not a live inference test."}</p>
    <button type="button" onClick={() => setAttempt(value => value + 1)}>Check readiness</button>
  </details>;
}
