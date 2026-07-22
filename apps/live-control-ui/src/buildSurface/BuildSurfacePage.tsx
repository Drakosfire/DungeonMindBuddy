import { useState } from "react";

import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import { BuildSurfaceShell } from "./BuildSurfaceShell";

export function BuildSurfacePage() {
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  return (
    <AppChrome activeRoute="build" editorTools={editorTools} editToolboxLayout="dock">
      <BuildSurfaceShell onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}
