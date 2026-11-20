import type {MouseEventHandler,ReactNode,Ref} from 'react';
import {SurfaceCardLayout} from '../../shared/SurfaceCardLayout';
import '../../tiptap/prepMarkdownThemes.css';
import '../../tiptap/tiptapSpike.css';
import '../../graphReference/graphReference.css';
import '../planSurface.css';

/**
 * Shared visible Plan canvas frame for editors with a different persistence
 * owner. This keeps the World-owned writer independent without forking the
 * established canvas boundary and Markdown theme composition.
 */
export function PlanSurfaceCanvasFrame({
  identityLabel,
  cardLayout = false,
  themeId,
  className,
  testId,
  editorRef,
  onEditorClick,
  beforeEditor,
  afterEditor,
  children,
}: {
  identityLabel: string;
  cardLayout?: boolean;
  themeId: string;
  className?: string;
  testId?: string;
  editorRef?: Ref<HTMLDivElement>;
  onEditorClick?: MouseEventHandler<HTMLDivElement>;
  beforeEditor?: ReactNode;
  afterEditor?: ReactNode;
  children: ReactNode;
}) {
  return (
    <SurfaceCardLayout as="section" active={cardLayout}
      className={`plan-surface-canvas${className ? ` ${className}` : ""}`}
      aria-label="Plan content"
      data-testid={testId ?? "plan-surface-canvas-frame"}
    >
      <p className="plan-surface-kicker" data-testid="plan-authoring-identity">
        {identityLabel}
      </p>
      {beforeEditor}
      <div
        ref={editorRef}
        className={`tiptap-spike-editor md-content md-theme-${themeId}`}
        data-md-theme={themeId}
        onClick={onEditorClick}
      >
        {children}
      </div>
      {afterEditor}
    </SurfaceCardLayout>
  );
}
