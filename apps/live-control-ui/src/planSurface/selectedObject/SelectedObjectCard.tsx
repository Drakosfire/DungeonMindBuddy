import type { ReferenceResolution } from "../reference/referenceResolver";
import { useOptionalProjection } from "../projection/projectionContext";
import {
  buildSelectedObjectCardModel,
  type SelectedObjectAction,
  type SelectedObjectField,
} from "./selectedObjectCardModel";

export interface SelectedObjectCardProps {
  resolution: ReferenceResolution;
}

function FieldList({
  fields,
  className,
}: {
  fields: SelectedObjectField[];
  className: string;
}) {
  if (fields.length === 0) return null;

  return (
    <dl className={className}>
      {fields.map((field) => (
        <div key={`${field.label}-${field.value}`}>
          <dt>{field.label}</dt>
          <dd>{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CardAction({
  action,
  onExpand,
  onOpenStatblock,
}: {
  action: SelectedObjectAction;
  onExpand: () => void;
  onOpenStatblock: () => void;
}) {
  if (action.href) {
    return (
      <a className="plan-selected-object-action" href={action.href}>
        {action.label}
      </a>
    );
  }

  const handleClick = () => {
    if (action.id === "expand") onExpand();
    if (action.id === "statblock") onOpenStatblock();
  };

  return (
    <button
      type="button"
      className="plan-selected-object-action"
      disabled={action.disabled}
      title={action.reason}
      onClick={handleClick}
    >
      {action.label}
    </button>
  );
}

export function SelectedObjectCard({ resolution }: SelectedObjectCardProps) {
  const projection = useOptionalProjection();
  const model = buildSelectedObjectCardModel(resolution);

  const onExpand = () => projection?.expandContent();
  const onOpenStatblock = () => projection?.openTool("statblock");

  return (
    <section
      className={`plan-selected-object-card plan-selected-object-card--${model.status}`}
      aria-label={`${model.title} selected object`}
    >
      <header className="plan-selected-object-header">
        <div>
          {model.subtitle ? (
            <p className="plan-selected-object-kind">{model.subtitle}</p>
          ) : null}
          <h3 className="plan-selected-object-title">{model.title}</h3>
        </div>
      </header>

      <p className="plan-selected-object-summary">{model.summary}</p>

      <FieldList fields={model.primaryFields} className="plan-selected-object-fields plan-selected-object-fields-primary" />
      <FieldList fields={model.secondaryFields} className="plan-selected-object-fields plan-selected-object-fields-secondary" />

      {model.sourcePath ? (
        <div className="plan-selected-object-source">
          <p className="plan-selected-object-source-label">Source</p>
          <code className="plan-selected-object-source-path">{model.sourcePath}</code>
        </div>
      ) : null}

      {model.actions.length > 0 ? (
        <div className="plan-selected-object-actions" aria-label="Follow-up actions">
          {model.actions.map((action) => (
            <CardAction
              key={action.id}
              action={action}
              onExpand={onExpand}
              onOpenStatblock={onOpenStatblock}
            />
          ))}
        </div>
      ) : null}

      {model.diagnostics && model.status !== "resolved" ? (
        <p className="plan-selected-object-diagnostics">{model.diagnostics[0]}</p>
      ) : null}
    </section>
  );
}
