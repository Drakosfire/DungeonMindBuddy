import { useEffect, useState, useSyncExternalStore } from "react";
import { authenticatedApiFetch, getNativeGraphAccessGeneration, NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT } from "../api/liveApi";
import { MEDIA_ASSET_ID } from "./mediaReferences";

function subscribeAccess(listener: () => void) {
  window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, listener);
  return () => window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, listener);
}

async function resolveImage(assetId: string, generation: number, signal: AbortSignal) {
  const current = () => !signal.aborted && generation === getNativeGraphAccessGeneration();
  async function read(path: string) {
    const { response, requestEpoch } = await authenticatedApiFetch(path, { signal: signal, cache: "no-store" });
    if (!response.ok || requestEpoch !== generation || !current()) throw new Error("Unavailable");
    const record = await response.json();
    if (!current() || !record || record.asset_id !== assetId) throw new Error("Unavailable");
    return record;
  }
  async function resolve(): Promise<string | Blob> {
    if (!MEDIA_ASSET_ID.test(assetId)) throw new Error("Unavailable");
    const record = await read(`/api/live/media/images/${assetId}/metadata`);
    if (record.state === "ready") {
      const delivery = new URL(record.delivery_url);
      if (delivery.protocol !== "https:" || delivery.hostname !== "imagedelivery.net"
        || delivery.username || delivery.password) throw new Error("Unavailable");
      return delivery.href;
    } else if (record.state === "staged") {
      if (!["image/png", "image/jpeg", "image/webp"].includes(record.mime_type)
        || !/^[a-f0-9]{64}$/.test(record.content_sha256)
        || !Number.isSafeInteger(record.byte_length) || record.byte_length <= 0) {
        throw new Error("Unavailable");
      }
      const { response, requestEpoch } = await authenticatedApiFetch(
        `/api/live/media/images/${assetId}/original`,
        { signal: signal, cache: "no-store" },
      );
      if (!response.ok || requestEpoch !== generation || !current()
        || response.headers.get("content-type") !== record.mime_type
        || response.headers.get("x-media-content-sha256") !== record.content_sha256) {
        throw new Error("Unavailable");
      }
      const blob = await response.blob();
      if (blob.size !== record.byte_length || !current()) throw new Error("Unavailable");
      return blob;
    } else throw new Error("Unavailable");
  }
  return resolve();
}

type PendingImage = {
  promise: Promise<string | Blob>;
  controller: AbortController;
  subscribers: number;
};

const pendingImages = new Map<string, PendingImage>();

function subscribePendingImage(assetId: string, generation: number) {
  const key = `${generation}:${assetId}`;
  let pending = pendingImages.get(key);
  if (!pending) {
    const controller = new AbortController();
    const entry: PendingImage = {
      controller,
      subscribers: 0,
      promise: resolveImage(assetId, generation, controller.signal),
    };
    pendingImages.set(key, entry);
    const clear = () => {
      if (pendingImages.get(key) === entry) pendingImages.delete(key);
    };
    void entry.promise.then(clear, clear);
    pending = entry;
  }
  const entry = pending;
  entry.subscribers += 1;
  return {
    promise: entry.promise,
    release() {
      entry.subscribers -= 1;
      if (entry.subscribers !== 0 || pendingImages.get(key) !== entry) return;
      pendingImages.delete(key);
      entry.controller.abort();
    },
  };
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
    const pending = subscribePendingImage(assetId, generation);
    void pending.promise.then(value => {
      if (!current()) return;
      if (typeof value === "string") {
        publish(value, "");
      } else {
        objectUrl = URL.createObjectURL(value);
        publish(objectUrl, "");
      }
    }).catch(() => publish(null, "Image unavailable. Open Image Studio to inspect the retained asset."));
    return () => {
      abort.abort();
      pending.release();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetId, generation]);
  // Never present a previous asset or authenticated owner's private URL.
  const current = result.assetId === assetId && result.generation === generation
    ? result : { url: null, status: "Loading image…" };
  return { ...current, onError: () => {
    if (generation === getNativeGraphAccessGeneration()) setResult({ assetId, generation, url: null, status: "Image unavailable" });
  } };
}
