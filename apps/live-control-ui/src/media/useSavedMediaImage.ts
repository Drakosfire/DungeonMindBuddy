import { useEffect, useState, useSyncExternalStore } from "react";
import { authenticatedApiFetch, getNativeGraphAccessGeneration, NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT } from "../api/liveApi";
import { MEDIA_ASSET_ID } from "./mediaReferences";
import { originalImageBlob } from "./originalImageBlob";

function subscribeAccess(listener: () => void) {
  window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, listener);
  return () => window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, listener);
}

/** Resolve an owner-readable asset; occurrences persist only its UUID reference. */
export function useSavedMediaImage(assetId: string) {
  const generation = useSyncExternalStore(subscribeAccess, getNativeGraphAccessGeneration);
  const [result, setResult] = useState({ assetId, generation, url: null as string | null, status: "Loading image…" });
  useEffect(() => {
    const abort = new AbortController();
    let objectUrl: string | undefined;
    const current = () => !abort.signal.aborted && generation === getNativeGraphAccessGeneration();
    const publish = (url: string | null, status: string) => { if (current()) setResult({ assetId, generation, url, status }); };
    publish(null, "Loading image…");
    async function read(path: string) {
      const { response, requestEpoch } = await authenticatedApiFetch(path, { signal: abort.signal, cache: "no-store" });
      if (!response.ok || requestEpoch !== generation || !current()) throw new Error("Unavailable");
      const record = await response.json();
      if (!current() || !record || record.asset_id !== assetId) throw new Error("Unavailable");
      return record;
    }
    async function resolve() {
      if (!MEDIA_ASSET_ID.test(assetId)) throw new Error("Unavailable");
      const record = await read(`/api/live/media/images/${assetId}/metadata`);
      if (record.state === "ready") {
        const delivery = new URL(record.delivery_url);
        if (delivery.protocol !== "https:" || delivery.hostname !== "imagedelivery.net"
          || delivery.username || delivery.password) throw new Error("Unavailable");
        publish(delivery.href, "");
      } else if (record.state === "staged") {
        const original = await read(`/api/live/media/images/${assetId}`);
        if (!["staged", "ready"].includes(original.state) || typeof original.data_url !== "string"
          || !/^[a-f0-9]{64}$/.test(record.content_sha256) || !Number.isSafeInteger(record.byte_length)
          || record.byte_length <= 0 || original.content_sha256 !== record.content_sha256
          || original.byte_length !== record.byte_length || original.mime_type !== record.mime_type) throw new Error("Unavailable");
        const blob = originalImageBlob(original.data_url, record.mime_type);
        if (blob.size !== record.byte_length || !current()) throw new Error("Unavailable");
        objectUrl = URL.createObjectURL(blob);
        publish(objectUrl, "");
      } else throw new Error("Unavailable");
    }
    void resolve().catch(() => publish(null, "Image unavailable. Open Image Studio to inspect the retained asset."));
    return () => { abort.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [assetId, generation]);
  // Never present a previous asset or authenticated owner's private URL.
  const current = result.assetId === assetId && result.generation === generation
    ? result : { url: null, status: "Loading image…" };
  return { ...current, onError: () => {
    if (generation === getNativeGraphAccessGeneration()) setResult({ assetId, generation, url: null, status: "Image unavailable" });
  } };
}
