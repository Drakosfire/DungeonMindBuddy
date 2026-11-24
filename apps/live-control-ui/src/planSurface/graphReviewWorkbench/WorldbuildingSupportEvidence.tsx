import { useRef, useState } from "react";

import { buildExtension, extendEvidence, positive, text, witnessFromLines, type Extension } from "../../api/nativeRecapPublicationApi";
import type { getNativeWorldbuildingContext } from "../../api/nativeWorldbuildingPublicationApi";

type Context = Awaited<ReturnType<typeof getNativeWorldbuildingContext>>;
type Props = {
  context: Context;
  sourceProse: string;
  sourceSha256: string;
  isCurrent: () => boolean;
  onBusy: (busy: boolean) => void;
  onCommitted: () => Promise<void>;
};

export function WorldbuildingSupportEvidence({ context, sourceProse, sourceSha256, isCurrent, onBusy, onCommitted }: Props) {
  const coordinates = context.prepareCoordinates;
  const native = context.nativeSource;
  const key = "dmb.worldbuildingSupport.v1:" + JSON.stringify([
    coordinates.managed_world_id, coordinates.run_id, sourceSha256,
  ]);
  const [pending, setPending] = useState(() => localStorage.getItem(key) !== null);
  const [quote, setQuote] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const running = useRef(false);

  async function register() {
    if (!native || running.current || !isCurrent()) return;
    running.current = true;
    setBusy(true);
    onBusy(true);
    setError(undefined);
    try {
      if (!navigator.locks) throw new Error("This browser cannot safely retain evidence requests.");
      await navigator.locks.request(key, async () => {
        if (!isCurrent()) throw new Error("The selected review changed.");
        const raw = localStorage.getItem(key);
        const saved = raw ? JSON.parse(raw) as { quote: string; request: Extension } : null;
        const excerpt = saved?.quote ?? quote;
        const lines = sourceProse.match(/[^\r\n\v\f\u0085\u2028\u2029]*(?:\r\n|[\r\n\v\f\u0085\u2028\u2029]|$)/gu)?.filter(line => line !== "") ?? [];
        const witness = await witnessFromLines({ sourceMarkdown: sourceProse, sourceSha256 }, 1, lines.length, excerpt);
        const parent = saved?.request.expected_parent_revision_id ?? coordinates.expected_parent_revision_id;
        const epoch = saved?.request.expected_source_authority_epoch ?? coordinates.expected_source_authority_epoch;
        if (!text(parent) || !positive(epoch)) throw new Error("The retained evidence request is invalid.");
        const request = buildExtension(
          { worldId: coordinates.managed_world_id, sourceSha256 },
          {
            native_source: native,
            source_support: saved ? [] : context.sourceSupport,
            prepare_coordinates: { expected_parent_revision_id: parent, expected_source_authority_epoch: epoch },
          },
          witness,
          saved?.request.extension_id ?? crypto.randomUUID(),
          saved?.request.created_at ?? new Date().toISOString(),
        );
        if (saved && JSON.stringify(request) !== JSON.stringify(saved.request))
          throw new Error("The retained evidence request differs from this source.");
        if (!isCurrent() || localStorage.getItem(key) !== raw) throw new Error("The selected evidence changed.");
        const retained = raw ?? JSON.stringify({ quote: excerpt, request });
        localStorage.setItem(key, retained);
        if (localStorage.getItem(key) !== retained) throw new Error("The exact evidence request could not be retained.");
        setPending(true);
        await extendEvidence(context, request);
        if (localStorage.getItem(key) !== retained) throw new Error("The retained evidence request changed.");
        localStorage.removeItem(key);
        if (isCurrent()) {
          setPending(false);
          setQuote("");
          await onCommitted();
        }
      });
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "The evidence request could not be verified.");
    } finally {
      running.current = false;
      setBusy(false);
      onBusy(false);
    }
  }

  if (!native || (context.sourceSupport.length > 0 && !pending)) return null;
  return <section aria-label="Worldbuilding support evidence">
    <p>Choose exact words from the saved source to support the selected facts.</p>
    <label>Exact witness text<input value={quote} disabled={busy || pending} onChange={event => setQuote(event.target.value)} /></label>
    <button type="button" disabled={busy || (!pending && !quote)} onClick={() => void register()}>
      {pending ? "Retry exact support request" : "Extend exact support evidence"}
    </button>
    {error && <p role="alert">{error}</p>}
  </section>;
}
