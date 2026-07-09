import { useCallback, useState } from "react";

import { postCitationSource, resolveRoll } from "../../api/liveApi";
import type { CitationSourceResponse } from "../../api/types";
import type { ReferenceResolution } from "../reference/referenceResolver";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";
import { useOptionalProjection } from "../projection/projectionContext";
import type { PlanSessionDescriptor } from "../types";
import { formatResolvedRoll } from "./formatResolvedRoll";
import { buildSelectedObjectActions } from "./selectedObjectActions";
import {
  buildSelectedObjectCardModel,
  type SelectedObjectAction,
  type SelectedObjectField,
} from "./selectedObjectCardModel";
import {
  SelectedObjectSourcePreview,
  SOURCE_PREVIEW_CHAR_LIMIT,
} from "./SelectedObjectSourcePreview";

export interface SelectedObjectCardProps {
  resolution: ReferenceResolution;
  sessionDescriptor?: PlanSessionDescriptor;
}

type SelectedObjectActionState =
  | { status: "idle" }
  | { status: "rolling" }
  | { status: "rolled"; label: string; resultText: string }
  | { status: "opened_tool"; message: string }
  | { status: "source_loading" }
  | { status: "source_loaded"; source: CitationSourceResponse; uiClipped: boolean }
  | { status: "error"; message: string };

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
  onRoll,
  onPreviewSource,
  rolling,
  sourceLoading,
}: {
  action: SelectedObjectAction;
  onExpand: () => void;
  onOpenStatblock: () => void;
  onRoll: (dice: string) => void;
  onPreviewSource: (sourcePath: string) => void;
  rolling: boolean;
  sourceLoading: boolean;
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
    if (action.id === "roll" && action.payload?.dice) {
      onRoll(action.payload.dice);
    }
    if (action.id === "source_preview" && action.payload?.sourcePath) {
      onPreviewSource(action.payload.sourcePath);
    }
  };

  const isRoll = action.id === "roll";
  const isSourcePreview = action.id === "source_preview";

  return (
    <button
      type="button"
      className="plan-selected-object-action"
      disabled={
        action.disabled
        || (isRoll && rolling)
        || (isSourcePreview && sourceLoading)
      }
      title={action.reason}
      onClick={handleClick}
    >
      {isRoll && rolling
        ? "Rolling…"
        : isSourcePreview && sourceLoading
          ? "Loading source…"
          : action.label}
    </button>
  );
}

function ActionFeedback({ state }: { state: SelectedObjectActionState }) {
  if (
    state.status === "idle"
    || state.status === "rolling"
    || state.status === "source_loading"
    || state.status === "source_loaded"
  ) {
    return null;
  }

  if (state.status === "rolled") {
    return (
      <p className="plan-selected-object-action-feedback plan-selected-object-action-feedback-roll">
        Roll result: {state.resultText}
      </p>
    );
  }

  if (state.status === "opened_tool") {
    return (
      <p className="plan-selected-object-action-feedback plan-selected-object-action-feedback-tool">
        {state.message}
      </p>
    );
  }

  return (
    <p className="plan-selected-object-action-feedback plan-selected-object-action-feedback-error">
      {state.message}
    </p>
  );
}

export function SelectedObjectCard({ resolution, sessionDescriptor }: SelectedObjectCardProps) {
  const projection = useOptionalProjection();
  const [actionState, setActionState] = useState<SelectedObjectActionState>({ status: "idle" });

  const model = buildSelectedObjectCardModel(resolution);
  const ingestHref = sessionDescriptor ? buildPlanIngestHref(sessionDescriptor) : "/ingest";
  const actions = buildSelectedObjectActions(model, { ingestHref });

  const onExpand = useCallback(() => {
    projection?.expandContent();
  }, [projection]);

  const onOpenStatblock = useCallback(() => {
    projection?.openTool("statblock");
    setActionState({
      status: "opened_tool",
      message:
        "Opened statblock tool. Selected object context is not loaded into the workbench yet.",
    });
  }, [projection]);

  const onRoll = useCallback(async (dice: string) => {
    setActionState({ status: "rolling" });
    try {
      const result = await resolveRoll(dice);
      setActionState({
        status: "rolled",
        label: dice,
        resultText: formatResolvedRoll(dice, result),
      });
    } catch (error) {
      setActionState({
        status: "error",
        message: error instanceof Error ? error.message : "Roll failed.",
      });
    }
  }, []);

  const onPreviewSource = useCallback(async (sourcePath: string) => {
    setActionState({ status: "source_loading" });
    try {
      const source = await postCitationSource({ path: sourcePath });
      setActionState({
        status: "source_loaded",
        source,
        uiClipped: source.content.length > SOURCE_PREVIEW_CHAR_LIMIT,
      });
    } catch (error) {
      setActionState({
        status: "error",
        message: `Unable to preview source: ${
          error instanceof Error ? error.message : "Source preview failed."
        }`,
      });
    }
  }, []);

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

      {actions.length > 0 ? (
        <div className="plan-selected-object-actions" aria-label="Follow-up actions">
          {actions.map((action) => (
            <CardAction
              key={`${action.id}-${action.label}`}
              action={action}
              onExpand={onExpand}
              onOpenStatblock={onOpenStatblock}
              onRoll={onRoll}
              onPreviewSource={onPreviewSource}
              rolling={actionState.status === "rolling"}
              sourceLoading={actionState.status === "source_loading"}
            />
          ))}
        </div>
      ) : null}

      {actionState.status === "source_loaded" ? (
        <SelectedObjectSourcePreview
          source={actionState.source}
          uiClipped={actionState.uiClipped}
        />
      ) : null}

      <ActionFeedback state={actionState} />

      {model.diagnostics && model.status !== "resolved" ? (
        <p className="plan-selected-object-diagnostics">{model.diagnostics[0]}</p>
      ) : null}
    </section>
  );
}
