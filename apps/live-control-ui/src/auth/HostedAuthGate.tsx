import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

type HostedAuthStatus = "checking" | "authenticated" | "signed_out" | "unavailable" | "local_operator";

type HostedAuthGateProps = {
  children: ReactNode;
  enabled: boolean;
};

const SESSION_PATH = "/api/auth/session";
const LOGIN_PATH = "/api/auth/login";
const SESSION_REFRESH_MS = 60_000;

export function HostedAuthGate({ children, enabled }: HostedAuthGateProps) {
  const [status, setStatus] = useState<HostedAuthStatus>(enabled ? "checking" : "local_operator");
  const [refreshWarning, setRefreshWarning] = useState(false);
  const confirmedAuthenticated = useRef(false);
  const requestSequence = useRef(0);

  const refreshSession = useCallback(async () => {
    if (!enabled) return;
    const sequence = ++requestSequence.current;
    try {
      const response = await fetch(SESSION_PATH, {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (sequence !== requestSequence.current) return;
      if (response.status === 401) {
        confirmedAuthenticated.current = false;
        setRefreshWarning(false);
        setStatus("signed_out");
        return;
      }
      if (!response.ok) throw new Error("Session status is unavailable");
      const payload = await response.json() as { status?: string };
      if (sequence !== requestSequence.current) return;
      if (payload.status === "authenticated") {
        confirmedAuthenticated.current = true;
        setRefreshWarning(false);
        setStatus("authenticated");
      } else if (payload.status === "local_operator") {
        confirmedAuthenticated.current = false;
        setRefreshWarning(false);
        setStatus("local_operator");
      } else if (payload.status === "signed_out") {
        confirmedAuthenticated.current = false;
        setRefreshWarning(false);
        setStatus("signed_out");
      } else {
        throw new Error("Session status is unavailable");
      }
    } catch {
      if (sequence !== requestSequence.current) return;
      if (confirmedAuthenticated.current) {
        setRefreshWarning(true);
        setStatus("authenticated");
      } else {
        setStatus("unavailable");
      }
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    void refreshSession();
    const onFocus = () => void refreshSession();
    window.addEventListener("focus", onFocus);
    const timer = window.setInterval(onFocus, SESSION_REFRESH_MS);
    return () => {
      requestSequence.current += 1;
      window.removeEventListener("focus", onFocus);
      window.clearInterval(timer);
    };
  }, [enabled, refreshSession]);

  if (!enabled || status === "authenticated" || status === "local_operator") {
    return (
      <>
        {refreshWarning ? (
          <div role="status" className="hosted-auth-refresh-warning">
            DungeonMind could not refresh your session status. Protected requests may ask you to sign in again.
          </div>
        ) : null}
        {children}
      </>
    );
  }

  if (status === "checking") {
    return <main className="hosted-auth-state" role="status">Checking your sign-in…</main>;
  }

  if (status === "unavailable") {
    return (
      <main className="hosted-auth-state" aria-labelledby="hosted-auth-title">
        <h1 id="hosted-auth-title">Sign-in status is unavailable</h1>
        <p>DungeonMind could not check your session. Try again when the authentication service is reachable.</p>
        <button type="button" onClick={() => void refreshSession()}>Retry</button>
      </main>
    );
  }

  const currentLocation = new URL(window.location.href);
  const authError = currentLocation.searchParams.get("auth_error");
  const message = authError === "cancelled"
    ? "Sign-in was cancelled. You can try again when you are ready."
    : authError
      ? "Sign-in did not complete. Please try again."
      : "Sign in with your DungeonMind account to continue.";
  currentLocation.searchParams.delete("auth_error");
  const returnTo = `${currentLocation.pathname}${currentLocation.search}${currentLocation.hash}`;
  const loginHref = `${LOGIN_PATH}?return_to=${encodeURIComponent(returnTo)}`;

  return (
    <main className="hosted-auth-state" aria-labelledby="hosted-auth-title">
      <h1 id="hosted-auth-title">Sign in to DungeonMind</h1>
      <p>{message}</p>
      <a href={loginHref}>Sign in with DungeonMind</a>
      <button type="button" onClick={() => void refreshSession()}>Check again</button>
    </main>
  );
}
