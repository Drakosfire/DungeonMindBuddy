import type { GraphAuthoringSelection } from "./graphAuthoringSelection";

function fieldValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

export function GraphObjectAuthoringSelectedSource({
  selection,
}: {
  selection: GraphAuthoringSelection;
}) {
  return (
    <section
      className="graph-object-authoring-selected-source"
      aria-label="Selected source"
    >
      <p className="graph-object-authoring-selected-source-lede">
        This is the recap text this draft is grounded in. Nothing has been
        written yet.
      </p>
      <dl className="graph-object-authoring-selected-source-fields">
        <div>
          <dt>Selected text</dt>
          <dd>{selection.selectedText}</dd>
        </div>
        <div>
          <dt>Selection kind</dt>
          <dd>{fieldValue(selection.selectionKind)}</dd>
        </div>
        <div>
          <dt>Campaign / session</dt>
          <dd>
            {selection.campaignId} / {selection.sessionId}
          </dd>
        </div>
        <div>
          <dt>Lane role</dt>
          <dd>{fieldValue(selection.laneRole)}</dd>
        </div>
        <div>
          <dt>Graph id</dt>
          <dd>{fieldValue(selection.graphId)}</dd>
        </div>
        <div>
          <dt>Source artifact</dt>
          <dd>{fieldValue(selection.sourceArtifactPath)}</dd>
        </div>
        {selection.surroundingTextBefore || selection.surroundingTextAfter ? (
          <div>
            <dt>Context</dt>
            <dd>
              …{fieldValue(selection.surroundingTextBefore)}{" "}
              <strong>{selection.selectedText}</strong>{" "}
              {fieldValue(selection.surroundingTextAfter)}…
            </dd>
          </div>
        ) : null}
        {typeof selection.paragraphOrdinal === "number" ? (
          <div>
            <dt>Paragraph</dt>
            <dd>{selection.paragraphOrdinal}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
