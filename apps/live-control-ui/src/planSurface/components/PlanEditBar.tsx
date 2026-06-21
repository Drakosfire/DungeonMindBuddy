import type { AppChromeTools } from "../../chrome/AppChrome";
import { useEditCapability } from "../edit/editCapability";

interface PlanEditBarProps {
  editorTools: AppChromeTools | null;
}

function EditActionButton({
  eyebrow,
  label,
  onClick,
  disabled,
  pressed,
}: {
  eyebrow?: string;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-pressed={pressed}>
      {eyebrow ? <span>{eyebrow}</span> : null}
      <strong>{label}</strong>
    </button>
  );
}

export function PlanEditBar({ editorTools }: PlanEditBarProps) {
  const { isLocked, toggleLock } = useEditCapability();
  const pinned = editorTools?.pinnedActions ?? [];
  const sections = editorTools?.sections ?? [];
  const hasTools = pinned.length > 0 || sections.length > 0;

  if (!hasTools) {
    return (
      <aside className="plan-edit-bar" aria-label="Edit bar">
        <header>
          <p className="plan-surface-kicker">Edit</p>
          <h2>Canvas controls</h2>
        </header>
        <p className="plan-edit-bar-empty">
          Canvas editing is locked by default. Unlock only when you intend to change the local planning board.
        </p>
        <button type="button" onClick={toggleLock} aria-pressed={isLocked}>
          {isLocked ? "Unlock canvas editing" : "Lock canvas editing"}
        </button>
      </aside>
    );
  }

  return (
    <aside className="plan-edit-bar" aria-label="Edit bar">
      <header>
        <p className="plan-surface-kicker">Canvas</p>
        <h2>Edit</h2>
        <p className="plan-edit-bar-empty">
          Document controls for the selected planning canvas. Corpus writes still require reviewed commit flows.
        </p>
      </header>
      <div className="plan-edit-actions">
        <EditActionButton
          eyebrow={isLocked ? "Editing locked" : "Editing unlocked"}
          label={isLocked ? "Unlock editing" : "Lock editing"}
          onClick={toggleLock}
          pressed={isLocked}
        />
        {pinned.map((action) => (
          <EditActionButton
            key={action.id}
            eyebrow={action.eyebrow}
            label={action.label}
            onClick={action.onClick}
            disabled={action.disabled}
            pressed={action.pressed}
          />
        ))}
      </div>
      {sections.map((section) => (
        <details key={section.id} className="plan-edit-fold" open={section.defaultOpen}>
          <summary>{section.title}</summary>
          <div className="plan-edit-fold-body">
            {section.actions.map((action) => (
              <EditActionButton
                key={action.id}
                eyebrow={action.eyebrow}
                label={action.label}
                onClick={action.onClick}
                disabled={action.disabled}
                pressed={action.pressed}
              />
            ))}
          </div>
        </details>
      ))}
    </aside>
  );
}
