import { useMemo } from "react";
import { diffWithContext, workspaceTextDiff } from "./workspaceTextDiff";

export function WorkspaceConflictDiff({ saved, local }: {saved:string;local:string}) {
  const lines=useMemo(()=>workspaceTextDiff(saved,local),[saved,local]);
  const removed=lines.filter(line=>line.kind==="removed").length, added=lines.filter(line=>line.kind==="added").length;
  return <section className="workspace-conflict-diff" aria-label="Changes from saved document to browser draft">
    <h3>What changed</h3>
    {added || removed ? <>
      <p>Saved → browser draft: <strong>− {removed} removed</strong>, <strong>+ {added} added</strong> line{added+removed===1?"":"s"}. Red − is saved text; green + is browser text.</p>
      <pre>{diffWithContext(lines).map((line,index)=><span className={`workspace-conflict-diff__${line.kind}`} key={index}>{line.kind==="removed"?"− ":line.kind==="added"?"+ ":line.kind==="same"?"  ":""}{line.text || " "}</span>)}</pre>
    </> : <p>The Markdown is identical. The browser’s full editor data is still preserved separately below; this comparison does not treat editor-only state as a text change.</p>}
  </section>;
}
