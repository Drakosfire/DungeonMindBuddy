import { useState } from "react";
import { useSavedMediaImage } from "./useSavedMediaImage";
import "../tiptap/extensions/MediaImageNode.css";

/** Reading collapse is local to this occurrence; it never edits authored state. */
export function SavedMediaImage({ assetId, alt, width = 100, collapsed = false }: {
  assetId: string; alt: string; width?: number; collapsed?: boolean;
}) {
  const image = useSavedMediaImage(assetId);
  const [isCollapsed, setCollapsed] = useState(collapsed);
  return <span className="document-media-image" style={{ width: `${width}%` }}>
    <span className="document-media-image__toolbar">
      <span className="document-media-image__title" title={alt}>{alt || "Image"}</span>
      <button type="button" aria-label={`${isCollapsed ? "Expand" : "Collapse"} image: ${alt || "Image"}`}
        aria-expanded={!isCollapsed} onClick={() => setCollapsed(value => !value)}>
        {isCollapsed ? "Expand" : "Collapse"}
      </button>
    </span>
    <span className="document-media-image__body" hidden={isCollapsed}>
      {image.url ? <img src={image.url} alt={alt} draggable={false} loading="lazy" onError={image.onError} />
        : <span role="status">{image.status}</span>}
    </span>
  </span>;
}
