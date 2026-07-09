import { isManualGraphAuthoringSelection, type GraphAuthoringSelection } from "./graphAuthoringSelection";

function fieldValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

function hasSourceDetails(selection: GraphAuthoringSelection): boolean {
  return Boolean(
    selection.selectionKind ||
      selection.campaignId ||
      selection.sessionId ||
      selection.laneRole ||
      selection.graphId ||
      selection.sourceArtifactPath ||
      typeof selection.paragraphOrdinal === "number",
  );
}

function SelectedSourceContext({ selection }: { selection: GraphAuthoringSelection }) {
  if (selection.surroundingTextBefore || selection.surroundingTextAfter) {
    return (
      <div className="graph-object-authoring-selected-source-context">
        <p className="graph-object-authoring-selected-source-context-label">Context</p>
        <p className="graph-object-authoring-selected-source-context-text">
          …{fieldValue(selection.surroundingTextBefore)}{" "}
          <strong>{selection.selectedText}</strong>{" "}
          {fieldValue(selection.surroundingTextAfter)}…
        </p>
      </div>
    );
  }

  return (
    <p className="graph-object-authoring-selected-source-fallback-context">
      Selected phrase from the recap.
    </p>
  );
}

function SourceDetailsPanel({ selection }: { selection: GraphAuthoringSelection }) {
  if (!hasSourceDetails(selection)) {
    return null;
  }

  return (
    <details
      className="graph-object-authoring-source-details-panel"
      data-testid="graph-object-authoring-source-details"
    >
      <summary>Source details</summary>
      <dl className="graph-object-authoring-selected-source-fields">
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
        {typeof selection.paragraphOrdinal === "number" ? (
          <div>
            <dt>Paragraph</dt>
            <dd>{selection.paragraphOrdinal}</dd>
          </div>
        ) : null}
      </dl>
    </details>
  );
}

export function GraphObjectAuthoringSelectedSource({
  selection,
}: {
  selection: GraphAuthoringSelection;
}) {
  const isManual = isManualGraphAuthoringSelection(selection);

  return (
    <section
      className="graph-object-authoring-selected-source"
      aria-label="Selected source"
    >
      <header className="graph-object-authoring-selected-source-header">
        <p className="graph-object-authoring-selected-source-label">
          {isManual ? "New object" : "Selected source"}
        </p>
        {isManual ? (
          <p className="graph-object-authoring-selected-source-phrase">
            Authored directly — not grounded to recap text.
          </p>
        ) : (
          <p className="graph-object-authoring-selected-source-phrase">“{selection.selectedText}”</p>
        )}
      </header>

      {isManual ? null : <SelectedSourceContext selection={selection} />}

      <p className="graph-object-authoring-selected-source-lede">
        Draft only. Nothing has been written.
      </p>

      <SourceDetailsPanel selection={selection} />
    </section>
  );
}
