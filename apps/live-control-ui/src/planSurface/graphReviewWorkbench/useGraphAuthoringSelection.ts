import { useEffect, useRef, useState } from "react";
import type { Editor } from "@tiptap/core";

import {
  buildGraphAuthoringSelectionFromEditor,
  graphAuthoringSelectionsEqual,
  type GraphAuthoringContext,
  type GraphAuthoringSelection,
} from "./graphAuthoringSelection";

interface UseGraphAuthoringSelectionOptions {
  editor: Editor | null;
  authoringEnabled?: boolean;
  authoringContext?: GraphAuthoringContext | null;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
}

function authoringContextKey(context: GraphAuthoringContext | null | undefined): string | null {
  if (!context) {
    return null;
  }
  return [
    context.campaignId,
    context.sessionId,
    context.graphId ?? "",
    context.laneRole ?? "",
    context.sourceArtifactPath ?? "",
    context.sourceArtifactSha256 ?? "",
  ].join("|");
}

export function useGraphAuthoringSelection({
  editor,
  authoringEnabled = false,
  authoringContext,
  onGraphAuthoringSelection,
}: UseGraphAuthoringSelectionOptions): GraphAuthoringSelection | null {
  const [pendingSelection, setPendingSelection] = useState<GraphAuthoringSelection | null>(null);
  const pendingSelectionRef = useRef<GraphAuthoringSelection | null>(null);
  const onSelectionRef = useRef(onGraphAuthoringSelection);
  const authoringContextRef = useRef(authoringContext);

  onSelectionRef.current = onGraphAuthoringSelection;
  authoringContextRef.current = authoringContext;

  const contextKey = authoringContextKey(authoringContext);

  useEffect(() => {
    if (!editor || !authoringEnabled || !authoringContextRef.current) {
      if (!graphAuthoringSelectionsEqual(pendingSelectionRef.current, null)) {
        pendingSelectionRef.current = null;
        setPendingSelection(null);
        onSelectionRef.current?.(null);
      }
      return;
    }

    const publishSelection = (nextSelection: GraphAuthoringSelection | null) => {
      if (graphAuthoringSelectionsEqual(pendingSelectionRef.current, nextSelection)) {
        return;
      }
      pendingSelectionRef.current = nextSelection;
      setPendingSelection(nextSelection);
      onSelectionRef.current?.(nextSelection);
    };

    const syncSelection = () => {
      const context = authoringContextRef.current;
      if (!context) {
        publishSelection(null);
        return;
      }
      publishSelection(buildGraphAuthoringSelectionFromEditor(editor, context));
    };

    syncSelection();
    editor.on("selectionUpdate", syncSelection);
    return () => {
      editor.off("selectionUpdate", syncSelection);
    };
  }, [authoringEnabled, editor, contextKey]);

  return pendingSelection;
}
