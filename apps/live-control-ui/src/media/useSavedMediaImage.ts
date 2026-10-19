import { useEffect, useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import { MEDIA_ASSET_ID } from "./mediaReferences";

/** Resolve a saved asset; document occurrences never persist delivery URLs. */
export function useSavedMediaImage(assetId: string) {
  const [result, setResult] = useState({ assetId, url: null as string | null, status: "Loading image…" });
  useEffect(() => {
    let active = true;
    setResult({ assetId, url: null, status: "Loading image…" });
    if (!MEDIA_ASSET_ID.test(assetId)) {
      setResult({ assetId, url: null, status: "Image unavailable" });
      return;
    }
    authenticatedApiFetch(`/api/live/media/images/${assetId}/metadata`).then(async ({ response }) => {
      if (!response.ok) throw new Error("Unavailable");
      const record = await response.json();
      const delivery = new URL(record.delivery_url);
      if (record.asset_id !== assetId || record.state !== "ready" || delivery.protocol !== "https:"
        || delivery.hostname !== "imagedelivery.net" || delivery.username || delivery.password) throw new Error("Unavailable");
      if (active) setResult({ assetId, url: delivery.href, status: "" });
    }).catch(() => {
      if (active) setResult({ assetId, url: null, status: "Image unavailable. Open Image Studio to inspect the saved asset." });
    });
    return () => { active = false; };
  }, [assetId]);
  // A replacement must not display the previous asset before its effect runs.
  const current = result.assetId === assetId ? result : { url: null, status: "Loading image…" };
  return { ...current, onError: () => setResult({ assetId, url: null, status: "Image unavailable" }) };
}
