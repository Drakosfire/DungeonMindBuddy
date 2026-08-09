import { NodeViewWrapper } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";

import {
  GraphNodeHoverToken,
  presentationForNodeId,
  useGraphNodeChipRuntime,
} from "../../graphReference";
import {
  GRAPH_NODE_REF_TYPE,
  hydratePersistedRunbookReferenceAttrs,
  isSupportedRunbookReference,
  runbookReferenceClasses,
  type RunbookReferenceAttrs,
} from "../references/runbookReferences";

/**
 * TipTap NodeView for Plan runbook references.
 * Graph-native chips get the shared CSS hover glance; corpus chips stay md-ref spans.
 */
export function RunbookReferenceView({ node }: NodeViewProps) {
  // Hydrate legacy escaped labels for display; fresh semantic labels pass through.
  const attrs = hydratePersistedRunbookReferenceAttrs(node.attrs as Partial<RunbookReferenceAttrs>);
  const { nodeViews, activeNodeId, onSelectNode } = useGraphNodeChipRuntime();
  const supported = isSupportedRunbookReference(attrs);
  const isGraphNode = supported && attrs.refType === GRAPH_NODE_REF_TYPE;

  if (isGraphNode) {
    const presentation = presentationForNodeId(nodeViews, attrs.refId, attrs.label);
    return (
      <NodeViewWrapper as="span" className="runbook-reference-view">
        <GraphNodeHoverToken
          presentation={presentation}
          label={attrs.label || attrs.refId}
          pinned={activeNodeId === attrs.refId}
          onSelect={() => onSelectNode(attrs.refId)}
          tokenClassName={runbookReferenceClasses(attrs)}
          buttonProps={{
            "data-md-ref-kind": attrs.kind,
            "data-md-ref-type": attrs.refType,
            "data-md-ref-id": attrs.refId,
          }}
        />
      </NodeViewWrapper>
    );
  }

  const className = supported ? runbookReferenceClasses(attrs) : "md-ref-invalid";
  return (
    <NodeViewWrapper as="span" className="runbook-reference-view">
      <span
        className={className}
        data-md-ref-kind={supported ? attrs.kind : "invalid"}
        data-md-ref-type={attrs.refType}
        data-md-ref-id={attrs.refId}
        contentEditable={false}
        title={supported ? undefined : "Invalid runbook reference"}
      >
        {attrs.label}
      </span>
    </NodeViewWrapper>
  );
}
