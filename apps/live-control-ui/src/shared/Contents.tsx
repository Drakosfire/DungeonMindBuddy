import { isReadableBodyContent } from "../markdownReader/ReadOnlyBodyContent";
import { useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { useSavedMediaImage } from "../media/useSavedMediaImage";
import "./Contents.css";

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
    : <span className="surface-contents__image-placeholder">Image preview</span>;
}

/** A presentation cursor over the current Plan draft; never an editor or writer. */
export type ContentsEntry = {
  id: string;
  title: string;
  bodyContent?: readonly JSONContent[];
  bodyText?: string;
  groupTitle?: string;
  current?: boolean;
};

export function Contents({ entries, selectedId, onSelect, visible, expanded: controlledExpanded,
  onExpandedChange, showToggle = true, outlineAction }: {
  entries: readonly ContentsEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  visible: boolean;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  showToggle?: boolean;
  outlineAction?: { label: string; selected: boolean; onClick: () => void };
}) {
  const [localExpanded, setLocalExpanded] = useState(() => !(window.matchMedia?.("(max-width: 700px)").matches ?? false));
  const expanded = controlledExpanded ?? localExpanded;
  const setExpanded = (next: boolean) => {
    if (controlledExpanded === undefined) setLocalExpanded(next);
    onExpandedChange?.(next);
  };
  const lastRevealedScene = useRef<string | null | undefined>(undefined);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (controlledExpanded !== undefined) return;
    const media = window.matchMedia?.("(max-width: 700px)");
    const change = () => setExpanded(!media?.matches);
    media?.addEventListener?.("change", change);
    return () => media?.removeEventListener?.("change", change);
  }, [controlledExpanded]);
  useEffect(() => {
    if (!expanded || !visible || lastRevealedScene.current === selectedId) return;
    lastRevealedScene.current = selectedId;
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
  }, [expanded, selectedId, visible]);
  return <nav className="surface-contents" data-expanded={expanded} aria-label="Contents">
    {showToggle ? <button ref={toggleRef} type="button" className="surface-contents__toggle" aria-expanded={expanded}
      onClick={() => setExpanded(!expanded)}><span>Contents · {entries.length}</span>
      <svg aria-hidden="true" width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5"><path d={expanded ? "M5 7l5 5 5-5" : "M7 5l5 5-5 5"} /></svg>
    </button> : null}
    <div hidden={!expanded} className="surface-contents__contents">
      {outlineAction ? <button type="button" className="surface-contents__outline" aria-current={outlineAction.selected ? "true" : undefined}
        onClick={outlineAction.onClick}>{outlineAction.label}</button> : null}
      {entries.length === 0 ? <p>No scenes</p> : null}
      <ul ref={listRef} className="surface-contents__list">
        {entries.map((scene, index) => {
          const admitted = scene.bodyContent === undefined || isReadableBodyContent(scene.bodyContent);
          const media = admitted ? firstMedia(scene.bodyContent ?? []) : undefined;
          const preview = !admitted ? "Preview unavailable" : (scene.bodyContent !== undefined
            ? textOf(scene.bodyContent) : scene.bodyText ?? "").slice(0, 240);
          return <li key={scene.id}>
            <button type="button" className="surface-contents__card" data-current={scene.current ? "true" : undefined} aria-label={`Show scene: ${scene.title || "Untitled scene"}`}
              aria-current={scene.id === selectedId ? "true" : undefined} onClick={() => {
                onSelect(scene.id);
                if (controlledExpanded === undefined && window.matchMedia?.("(max-width: 700px)").matches) {
                  setExpanded(false);
                  toggleRef.current?.focus();
                }
              }}>
              <span className="surface-contents__page" aria-hidden="true">
                <strong>{scene.title || "Untitled scene"}</strong>
                {visible && expanded && media && typeof media.attrs?.assetId === "string" ? <ThumbnailImage assetId={media.attrs.assetId} /> : null}
                <span className="surface-contents__preview">{preview || "Open scene to read its content"}</span>
              </span>
              <span className="surface-contents__label">{index + 1}. {scene.title || "Untitled scene"}</span>
              {scene.groupTitle ? <span className="surface-contents__beat">{scene.groupTitle}</span> : null}
              {scene.current ? <span className="surface-contents__beat">Current scene</span> : null}
            </button>
          </li>;
        })}
      </ul>
    </div>
  </nav>;
}
