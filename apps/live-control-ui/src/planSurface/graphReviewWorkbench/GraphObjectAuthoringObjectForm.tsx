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
        <p className="graph-object-authoring-field-hint">
          The name this object will be known by everywhere in Graph Review — e.g. “Mireward
          Reach” or “Bonogo”.
        </p>
        <input
          id="graph-object-authoring-label"
          type="text"
          placeholder="e.g. Mireward Reach"
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
        <label htmlFor="graph-object-authoring-role">
          Role <span className="graph-object-authoring-optional">optional</span>
        </label>
        <p className="graph-object-authoring-field-hint">
          A more specific descriptor within Kind — e.g. an npc's role might be “companion”,
          “antagonist”, or “quest giver”. Shown next to Kind as “npc / companion”. Leave blank if
          Kind already says enough.
        </p>
        <input
          id="graph-object-authoring-role"
          type="text"
          placeholder="e.g. companion, antagonist"
          value={formState.role}
          onChange={(event) => onChange("role", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-aliases">Aliases</label>
        <p className="graph-object-authoring-field-hint">
          Other names recap text might use for this object, so mentions of any of them link back
          here automatically.
        </p>
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
        <p className="graph-object-authoring-field-hint">
          The description that shows on this object's card in Graph Review — what a player or GM
          reads to understand who or what this is.
        </p>
        <textarea
          id="graph-object-authoring-summary"
          rows={2}
          placeholder="A sentence or two describing this object"
          value={formState.summary}
          onChange={(event) => onChange("summary", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-operator-note">
          Operator note <span className="graph-object-authoring-optional">optional</span>
        </label>
        <p className="graph-object-authoring-field-hint">
          A private note to yourself about why you're authoring this — never shown as the
          object's description. Kept alongside the assertion for your own audit trail.
        </p>
        <textarea
          id="graph-object-authoring-operator-note"
          rows={2}
          placeholder="e.g. confirmed from session 23 notes"
          value={formState.operatorNote}
          onChange={(event) => onChange("operatorNote", event.target.value)}
        />
      </div>
    </section>
  );
}
