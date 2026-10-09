import type { JSONContent } from "@tiptap/core";
import type { ReactNode, Ref } from "react";

import { ReadOnlyBodyContent } from "../markdownReader/ReadOnlyBodyContent";
import "./sceneCard.css";

export type SceneCardIdentity = {
  worldId: string | null;
  campaignId?: string | null;
  documentId: string;
  sceneId: string;
  revision: number | null;
  workRevisionId?: string | null;
  contentSha256: string | null;
  sourceState: "verified" | "draft" | "run-pin";
};

export type SceneCardElement = {
  id: string;
  title: string;
  titleBlock?: JSONContent;
  bodyText: string;
  bodyContent?: JSONContent[];
};

export type SceneCardOption = SceneCardElement & {
  activates?: readonly string[];
  suppresses?: readonly string[];
};

export type SceneCardChoice = SceneCardElement & {
  options: SceneCardOption[];
  associatedSceneId?: string | null;
  selectedOptionId?: string | null;
};

export type SceneCardChoiceActions = {
  writable?: boolean;
  busy?: boolean;
  onSelectOption?: (choiceId: string, optionId: string) => void;
  onClearSelection?: (choiceId: string) => void;
  renderChoiceActions?: (choice: SceneCardChoice) => ReactNode;
  renderOptionActions?: (choice: SceneCardChoice, option: SceneCardOption) => ReactNode;
  renderSelectedContext?: (choice: SceneCardChoice) => ReactNode;
};

function Title({ element, level, className, headingId, headingRef, prefix, testId, onActivateGraphNode, unsupportedMessage }: {
  element: SceneCardElement;
  level: 2 | 3 | 4;
  className: string;
  headingId?: string;
  headingRef?: Ref<HTMLHeadingElement>;
  prefix?: string;
  testId?: string;
  onActivateGraphNode?: (nodeId: string, trigger?: HTMLElement) => void;
  unsupportedMessage?: string;
}) {
  if (element.titleBlock) return (
    <div id={headingId} className={className}>
      <ReadOnlyBodyContent
        content={[element.titleBlock]}
        onActivateGraphNode={onActivateGraphNode}
        unsupportedMessage={unsupportedMessage}
      />
    </div>
  );
  const title = `${prefix ? `${prefix} ` : ""}${element.title || "Untitled Scene"}`;
  if (level === 2) return <h2 id={headingId} ref={headingRef} tabIndex={-1} className={className}>{title}</h2>;
  if (level === 3) return <h3 id={headingId} className={className} data-testid={testId}>{title}</h3>;
  return <h4 id={headingId} className={className}>{title}</h4>;
}

/** One authored Choice renderer for Plan focus and both Play Scene modes. */
export function SceneCardChoices({ choices, variant, actions = {}, onActivateGraphNode, unsupportedMessage }: {
  choices: readonly SceneCardChoice[];
  variant: "plan" | "play";
  actions?: SceneCardChoiceActions;
  onActivateGraphNode?: (nodeId: string, trigger?: HTMLElement) => void;
  unsupportedMessage?: string;
}) {
  if (!choices.length) return null;
  const play = variant === "play";
  return (
    <div className={`shared-scene-choices${play ? " play-decisions" : ""}`} data-testid={play ? "play-decisions" : "scene-card-choices"}>
      {choices.map((choice) => {
        const selected = choice.options.find((option) => option.id === choice.selectedOptionId) ?? null;
        const titleId = `scene-card-choice-${choice.id}`;
        return (
          <section key={choice.id} className={`shared-scene-choice${play ? ` play-decision${selected ? " is-resolved" : ""}` : ""}`}
            data-testid={play ? "play-decision" : undefined} data-element-id={choice.id} data-element-kind="choice" data-choice-id={choice.id}>
            <header className={`shared-scene-choice__header${play ? " play-decision-header" : ""}`}>
              <p className={play ? "play-decision-kicker" : "shared-scene-card__kicker"}>Decision</p>
              <Title element={choice} level={3} className="shared-scene-choice__title" headingId={titleId} testId={play ? "play-decision-prompt" : undefined}
                onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
              {!play && choice.associatedSceneId ? <p className="shared-scene-choice__association">Associated scene: <code>{choice.associatedSceneId}</code></p> : null}
              <ReadOnlyBodyContent content={choice.bodyContent} fallbackText={choice.bodyText}
                className={`shared-scene-choice__body${play ? " play-body play-decision-framing" : ""}`}
                onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
              {actions.renderChoiceActions?.(choice)}
            </header>
            {play ? (
              <div className="play-decision-options" role="radiogroup" aria-labelledby={titleId}>
                {choice.options.map((option) => {
                  const isSelected = selected?.id === option.id;
                  return actions.writable && actions.onSelectOption ? (
                    <button key={option.id} type="button" role="radio" className={`play-decision-option${isSelected ? " is-selected" : ""}`}
                      name={titleId} value={option.id} aria-checked={isSelected} disabled={actions.busy}
                      onClick={() => actions.onSelectOption?.(choice.id, option.id)}>{option.title}</button>
                  ) : (
                    <span key={option.id} role="radio" className={`play-decision-option${isSelected ? " is-selected" : ""}`}
                      aria-checked={isSelected} aria-disabled="true">{option.title}</span>
                  );
                })}
              </div>
            ) : (
              <ol className="shared-scene-choice__options" aria-label={`Options for ${choice.title}`}>
                {choice.options.map((option) => (
                  <li key={option.id} data-element-id={option.id} data-element-kind="option">
                    <Title element={option} level={4} className="shared-scene-choice__option-title"
                      onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
                    <ReadOnlyBodyContent content={option.bodyContent} fallbackText={option.bodyText}
                      className="shared-scene-choice__option-body" onActivateGraphNode={onActivateGraphNode}
                      unsupportedMessage={unsupportedMessage} />
                    {option.activates?.length || option.suppresses?.length ? (
                      <ul className="shared-scene-choice__relations" aria-label="Authored relationships">
                        {option.activates?.map((id) => <li key={`activates:${id}`}>Authored activates: <code>{id}</code></li>)}
                        {option.suppresses?.map((id) => <li key={`suppresses:${id}`}>Authored suppresses: <code>{id}</code></li>)}
                      </ul>
                    ) : null}
                    {actions.renderOptionActions?.(choice, option)}
                  </li>
                ))}
              </ol>
            )}
            {play && selected ? (
              <div className="play-decision-result">
                <ReadOnlyBodyContent content={selected.bodyContent} fallbackText={selected.bodyText}
                  className="play-body play-decision-consequence" testId="play-decision-consequence" />
                {actions.renderSelectedContext?.(choice)}
                {actions.writable && actions.onClearSelection ? (
                  <button type="button" className="play-decision-clear" data-testid="play-decision-clear"
                    disabled={actions.busy} aria-label={`Clear selection for ${choice.title}`}
                    onClick={() => actions.onClearSelection?.(choice.id)}>Clear</button>
                ) : null}
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

/** Shared Scene paper/card. Each surface supplies its own existing action slots. */
export function SceneCard({ identity, scene, choices, variant, kicker, titlePrefix, headingId, headingRef,
  headerRef, className = "", testId, context, status, sceneActions, footer, choiceActions,
  onActivateGraphNode, unsupportedMessage }: {
  identity: SceneCardIdentity;
  scene: SceneCardElement;
  choices: readonly SceneCardChoice[];
  variant: "plan" | "play-current" | "play-inspection";
  kicker: string;
  titlePrefix?: string;
  headingId?: string;
  headingRef?: Ref<HTMLHeadingElement>;
  headerRef?: Ref<HTMLElement>;
  className?: string;
  testId?: string;
  context?: ReactNode;
  status?: ReactNode;
  sceneActions?: ReactNode;
  footer?: ReactNode;
  choiceActions?: SceneCardChoiceActions;
  onActivateGraphNode?: (nodeId: string, trigger?: HTMLElement) => void;
  unsupportedMessage?: string;
}) {
  const plan = variant === "plan";
  return (
    <article className={`shared-scene-card shared-scene-card--${variant}${className ? ` ${className}` : ""}`}
      data-testid={testId} data-scene-card="true" data-element-id={scene.id} data-element-kind="scene"
      data-world-id={identity.worldId ?? ""} data-campaign-id={identity.campaignId ?? ""}
      data-document-id={identity.documentId} data-scene-id={identity.sceneId}
      data-source-revision={identity.revision ?? ""} data-work-revision-id={identity.workRevisionId ?? ""}
      data-content-sha256={identity.contentSha256 ?? ""} data-source-state={identity.sourceState}
      aria-labelledby={headingId}>
      <header ref={headerRef} className={`shared-scene-card__header${plan ? " world-plan-scene-reader__heading" : ""}`}>
        <p className={plan ? "world-plan-card__kind" : "play-kicker"}>{kicker}</p>
        <Title element={scene} level={2} className={plan ? "world-plan-scene-reader__title" : "shared-scene-card__title"}
          headingId={headingId} headingRef={headingRef} prefix={titlePrefix}
          onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
        {plan ? <code className="shared-scene-card__id">{scene.id}</code> : null}
        {context}{status}{sceneActions}
      </header>
      <div className={`shared-scene-card__content${plan ? " world-plan-scene-reader__content" : ""}`}>
        <ReadOnlyBodyContent content={scene.bodyContent} fallbackText={scene.bodyText}
          className={plan ? "shared-scene-card__body world-plan-card__content" : "shared-scene-card__body play-body play-scene-board-body"}
          onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
        <SceneCardChoices choices={choices} variant={plan ? "plan" : "play"} actions={choiceActions}
          onActivateGraphNode={onActivateGraphNode} unsupportedMessage={unsupportedMessage} />
        {footer}
      </div>
    </article>
  );
}
