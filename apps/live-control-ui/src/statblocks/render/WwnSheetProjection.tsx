type SheetValue = string | number;

type FieldLocation = {
  page: number;
  bbox_pdf_points: readonly number[];
};

type FieldEvidence = {
  label: string;
  method: string;
  occurrences?: readonly FieldLocation[];
  page?: number;
  bbox_pdf_points?: readonly number[];
};

type ReviewedField =
  | { state: "confirmed"; value: SheetValue; evidence: FieldEvidence }
  | {
      state: "blank" | "unknown" | "ambiguous" | "unconfirmed_default";
      value: null;
      evidence: FieldEvidence | null;
    };

export type WwnSheetProjectionConfig = {
  sections: readonly {
    title: string;
    fields: readonly { key: string; label: string }[];
  }[];
};

export type WwnSheetProjectionInput = {
  sheet: {
    ruleset: "wwn";
    source_sha256: string;
    fields: Readonly<Record<string, ReviewedField | undefined>>;
  };
  config: WwnSheetProjectionConfig;
  overrides?: Readonly<Record<string, { value: SheetValue; reason: string } | undefined>>;
};

const STATUS_LABELS = {
  blank: "Blank on sheet",
  unknown: "Unknown",
  ambiguous: "Needs review",
  unconfirmed_default: "Unconfirmed template default",
} as const;

function FieldSource({ evidence }: { evidence: FieldEvidence }) {
  const locations = evidence.occurrences ?? (
    evidence.page === undefined || !evidence.bbox_pdf_points
      ? []
      : [{ page: evidence.page, bbox_pdf_points: evidence.bbox_pdf_points }]
  );
  return (
    <details>
      <summary>Sheet source</summary>
      <p>{evidence.label}</p>
      <ul>
        {locations.map((location, index) => (
          <li key={index}>
            PDF page {location.page}, bounds {location.bbox_pdf_points.join(", ")}
          </li>
        ))}
      </ul>
    </details>
  );
}

export function WwnSheetProjection({ sheet, config, overrides }: WwnSheetProjectionInput) {
  const identity = sheet.fields["identity.name"];
  const name = identity?.state === "confirmed" ? identity.value : "Character";
  return (
    <article className="statblock-renderer" data-statblock-renderer
      data-resource-kind="reviewed-sheet" aria-label={`WWN statblock for ${name}`}>
      <header className="statblock-renderer-header">
        <h3>{name}</h3>
        {identity?.state === "confirmed" && <FieldSource evidence={identity.evidence} />}
        <p className="statblock-renderer-identity">Worlds Without Number</p>
        <details>
          <summary>Reviewed sheet revision</summary>
          <code>{sheet.source_sha256}</code>
        </details>
      </header>
      {config.sections.map((section) => (
        <section key={section.title} className="statblock-renderer-section">
          <h4>{section.title}</h4>
          <dl className="statblock-renderer-core">
            {section.fields.map(({ key, label }) => {
              const field = sheet.fields[key];
              const override = overrides?.[key];
              const isOverride = Boolean(override?.reason.trim());
              const value = field?.state === "confirmed"
                ? field.value
                : STATUS_LABELS[field?.state ?? "unknown"];
              return (
                <div key={key}>
                  <dt>{label}</dt>
                  <dd>{isOverride ? override?.value : value}</dd>
                  {isOverride && <dd>Override: {override?.reason}</dd>}
                  {field?.evidence && <dd><FieldSource evidence={field.evidence} /></dd>}
                </div>
              );
            })}
          </dl>
        </section>
      ))}
    </article>
  );
}
