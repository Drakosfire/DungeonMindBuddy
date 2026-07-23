import { useEffect, useState } from "react";

function readDocumentIdFromLocation(): string | null {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("documentId")?.trim();
  return raw || null;
}

/**
 * Keep component document selection aligned with `?documentId=` across
 * pushState/replaceState and browser back/forward (popstate).
 */
export function useWorkspaceDocumentUrlSelection(): string | null {
  const [documentId, setDocumentId] = useState<string | null>(() => readDocumentIdFromLocation());

  useEffect(() => {
    const sync = () => {
      setDocumentId(readDocumentIdFromLocation());
    };
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("popstate", sync);
    };
  }, []);

  return documentId;
}
