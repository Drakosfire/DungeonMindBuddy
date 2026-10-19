import { useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { useSavedMediaImage } from "../../media/useSavedMediaImage";
import type { WorldPlanCardNode } from "./WorldPlanCardProjection";
import "./PlanCardDeck.css";

function textOf(nodes: readonly JSONContent[]): string {
  return nodes.map(node => node.text ?? (typeof node.attrs?.label === "string" ? node.attrs.label
    : textOf(node.content ?? []))).join(" ").replace(/\s+/g, " ").trim();
}

function firstMedia(nodes: readonly JSONContent[]): JSONContent | undefined {
  for (const node of nodes) {
    if (node.type === "mediaImage") return node;
    const child = firstMedia(node.content ?? []);
    if (child) return child;
  }
}

function ThumbnailImage({ assetId }: { assetId: string }) {
  const image = useSavedMediaImage(assetId);
  return image.url ? <img src={image.url} alt="" loading="lazy" draggable={false} onError={image.onError} />
    : <span className="plan-card-deck__image-placeholder">Image preview</span>;
}

/** A presentation cursor over the current Plan draft; never an editor or writer. */
export function PlanCardDeck({ scenes, nodes, sceneId, onSelect, visible }: {
  visible: boolean;
  scenes: readonly WorldPlanCardNode[];
  nodes: readonly WorldPlanCardNode[];
  sceneId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const [expanded, setExpanded] = useState(() => !(window.matchMedia?.("(max-width: 700px)").matches ?? false));
  const lastRevealedScene = useRef<string | null | undefined>(undefined);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  useEffect(() => {
    const media = window.matchMedia?.("(max-width: 700px)");
    const change = () => setExpanded(!media?.matches);
    media?.addEventListener?.("change", change);
    return () => media?.removeEventListener?.("change", change);
  }, []);
  useEffect(() => {
    if (!expanded || !visible || lastRevealedScene.current === sceneId) return;
    lastRevealedScene.current = sceneId;
    // Scroll only the deck, never the page or the mounted document editor.
    const list = listRef.current;
    const selected = list?.querySelector<HTMLElement>('[aria-current="true"]');
    if (!list || !selected) return;
    const item = selected.closest("li")!;
    const top = item.getBoundingClientRect().top - list.getBoundingClientRect().top + list.scrollTop;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (top + item.offsetHeight > list.scrollTop + list.clientHeight) {
      list.scrollTop = top + item.offsetHeight - list.clientHeight;
    }
  }, [expanded, sceneId, visible]);
  return <nav className="plan-card-deck" data-expanded={expanded} aria-label="Plan card deck">
    <button ref={toggleRef} type="button" className="plan-card-deck__toggle" aria-expanded={expanded}
      onClick={() => setExpanded(value => !value)}>{expanded ? "▾" : "▸"} Scenes · {scenes.length}</button>
    <div hidden={!expanded} className="plan-card-deck__contents">
      <button type="button" className="plan-card-deck__outline" aria-current={sceneId === null ? "true" : undefined}
        onClick={() => onSelect(null)}>Scene outline</button>
      <ul ref={listRef} className="plan-card-deck__list">
        {scenes.map((scene, index) => {
          const beat = nodes.find(node => node.kind === "beat" && node.id === scene.parentId);
          const media = firstMedia(scene.bodyContent);
          const preview = textOf(scene.bodyContent).slice(0, 240);
          return <li key={scene.id}>
            <button type="button" className="plan-card-deck__card" aria-label={`Show scene: ${scene.title || "Untitled scene"}`}
              aria-current={scene.id === sceneId ? "true" : undefined} onClick={() => {
                onSelect(scene.id);
                if (window.matchMedia?.("(max-width: 700px)").matches) {
                  setExpanded(false);
                  toggleRef.current?.focus();
                }
              }}>
              <span className="plan-card-deck__page" aria-hidden="true">
                <strong>{scene.title || "Untitled scene"}</strong>
                {visible && expanded && media && typeof media.attrs?.assetId === "string" ? <ThumbnailImage assetId={media.attrs.assetId} /> : null}
                <span className="plan-card-deck__preview">{preview || "Open scene to read its content"}</span>
              </span>
              <span className="plan-card-deck__label">{index + 1}. {scene.title || "Untitled scene"}</span>
              {beat ? <span className="plan-card-deck__beat">{beat.title}</span> : null}
            </button>
          </li>;
        })}
      </ul>
    </div>
  </nav>;
}
