import { invalidateHostedGraphAccess } from "../api/liveApi";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

export type HostedAuthStatus = "checking" | "authenticated" | "signed_out" | "unavailable" | "local_operator";

interface HostedAuthContextValue {
  readonly status: HostedAuthStatus;
  readonly refreshWarning: boolean;
  /** Presentation scope only. The server remains the owner/access authority. */
  readonly subject: string | null;
  readonly displayName: string | null;
}

const HostedAuthContext = createContext<HostedAuthContextValue>({ status: "local_operator", refreshWarning: false, subject: null, displayName: null });

type HostedAuthGateProps = {
  children: ReactNode;
  enabled: boolean;
  /** Permit only the canonical index to render its distinct signed-out playground. */
  allowSignedOutChildren?: boolean;
};

const SESSION_PATH = "/api/auth/session";
const LOGIN_PATH = "/api/auth/login";
const SESSION_REFRESH_MS = 60_000;

export function useHostedAuthStatus(): HostedAuthContextValue {
  return useContext(HostedAuthContext);
}

export function dungeonMindLoginHref(locationHref: string): string {
  const currentLocation = new URL(locationHref, typeof window === "undefined" ? "http://localhost" : window.location.href);
  currentLocation.searchParams.delete("auth_error");
  const returnTo = `${currentLocation.pathname}${currentLocation.search}${currentLocation.hash}`;
  return `${LOGIN_PATH}?return_to=${encodeURIComponent(returnTo)}`;
}

export function HostedAuthGate({ children, enabled, allowSignedOutChildren = false }: HostedAuthGateProps) {
  const [session, setSession] = useState<{ status: HostedAuthStatus; subject: string | null; displayName: string | null }>({
    status: enabled ? "checking" : "local_operator", subject: null, displayName: null,
  });
  const { status, subject, displayName } = enabled ? session : { status: "local_operator" as const, subject: null, displayName: null };
  const requestSequence = useRef(0);

  const refreshSession = useCallback(async () => {
    if (!enabled) return;
    const sequence = ++requestSequence.current;
    const accept = (nextStatus: HostedAuthStatus, nextSubject: string | null = null, nextDisplayName: string | null = null) => {
      invalidateHostedGraphAccess(nextSubject);
      setSession({ status: nextStatus, subject: nextSubject, displayName: nextDisplayName });
    };
    try {
      const response = await fetch(SESSION_PATH, {
        method: "GET",
        credentials: "same-origin",
        redirect: "error",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (sequence !== requestSequence.current) return;
      if (response.status === 401) {
        accept("signed_out");
        return;
      }
      if (!response.ok) throw new Error("Session status is unavailable");
      const payload = await response.json() as { status?: unknown; subject?: unknown; display_name?: unknown };
      if (sequence !== requestSequence.current) return;
      if (payload.status === "authenticated" && typeof payload.subject === "string"
        && payload.subject.length > 0 && payload.subject === payload.subject.trim()) {
        accept("authenticated", payload.subject,
          typeof payload.display_name === "string" ? payload.display_name.trim() || null : null);
      } else if (payload.status === "local_operator") {
        accept("local_operator");
      } else if (payload.status === "signed_out") {
        accept("signed_out");
      } else {
        throw new Error("Session status is unavailable");
      }
    } catch {
      if (sequence !== requestSequence.current) return;
      // Never retain the previous account's sensitive children on an auth outage.
      accept("unavailable");
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
      invalidateHostedGraphAccess(null);
      window.removeEventListener("focus", onFocus);
      window.clearInterval(timer);
    };
  }, [enabled, refreshSession]);

  if (!enabled || status === "authenticated" || status === "local_operator"
    || status === "signed_out" && allowSignedOutChildren) {
    return (
      <HostedAuthContext.Provider
        key={JSON.stringify([status, subject])}
        value={{ status, subject, displayName, refreshWarning: false }}
      >
        {children}
      </HostedAuthContext.Provider>
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
  const loginHref = dungeonMindLoginHref(currentLocation.href);

  return (
    <main className="hosted-auth-state" aria-labelledby="hosted-auth-title">
      <h1 id="hosted-auth-title">Sign in to DungeonMind</h1>
      <p>{message}</p>
      <a href={loginHref}>Sign in with DungeonMind</a>
      <button type="button" onClick={() => void refreshSession()}>Check again</button>
    </main>
  );
}
