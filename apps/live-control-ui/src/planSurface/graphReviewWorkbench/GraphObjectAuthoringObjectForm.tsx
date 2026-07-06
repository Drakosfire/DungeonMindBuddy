import { GRAPH_OBJECT_AUTHORING_KIND_OPTIONS, type GraphObjectAuthoringFormState } from "./graphObjectAuthoringDraft";

export function GraphObjectAuthoringObjectForm({
  formState,
  onChange,
}: {
  formState: GraphObjectAuthoringFormState;
  onChange: <K extends keyof GraphObjectAuthoringFormState>(
    field: K,
    value: GraphObjectAuthoringFormState[K],
  ) => void;
}) {
  return (
    <section className="graph-object-authoring-object-form" aria-label="Declare object">
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-label">Label</label>
        <input
          id="graph-object-authoring-label"
          type="text"
          value={formState.label}
          onChange={(event) => onChange("label", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-kind">Kind</label>
        <select
          id="graph-object-authoring-kind"
          value={formState.kind}
          onChange={(event) => onChange("kind", event.target.value)}
        >
          {GRAPH_OBJECT_AUTHORING_KIND_OPTIONS.map((kind) => (
            <option key={kind} value={kind}>
              {kind}
            </option>
          ))}
        </select>
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-role">Role</label>
        <input
          id="graph-object-authoring-role"
          type="text"
          value={formState.role}
          onChange={(event) => onChange("role", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-aliases">Aliases</label>
        <textarea
          id="graph-object-authoring-aliases"
          rows={2}
          placeholder="Comma or newline separated"
          value={formState.aliasesText}
          onChange={(event) => onChange("aliasesText", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-summary">Summary</label>
        <textarea
          id="graph-object-authoring-summary"
          rows={2}
          value={formState.summary}
          onChange={(event) => onChange("summary", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-operator-note">
          Operator note <span className="graph-object-authoring-optional">optional</span>
        </label>
        <textarea
          id="graph-object-authoring-operator-note"
          rows={2}
          value={formState.operatorNote}
          onChange={(event) => onChange("operatorNote", event.target.value)}
        />
      </div>
    </section>
  );
}
