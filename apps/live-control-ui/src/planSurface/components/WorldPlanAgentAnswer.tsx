import { useMemo } from "react";

import { ReadOnlyBodyContent } from "../../markdownReader/ReadOnlyBodyContent";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";

export function WorldPlanAgentAnswer({
  answer,
  className,
  displaySegments,
}: {
  answer: string;
  className?: string;
  displaySegments?: readonly string[];
}) {
  const parsed = useMemo(() => {
    try {
      return markdownToTiptapDoc(answer);
    } catch {
      return null;
    }
  }, [answer]);

  if (displaySegments?.length && displaySegments.join("\n") === answer) {
    return (
      <div className={["world-plan-agent-answer", className].filter(Boolean).join(" ")}>
        {displaySegments.map((segment, index) => (
          <WorldPlanAgentAnswer key={`${index}:${segment}`} answer={segment} />
        ))}
      </div>
    );
  }

  if (parsed == null || parsed.diagnostics.some((diagnostic) => diagnostic.level === "warning")) {
    return (
      <p className={["world-plan-agent-answer", className].filter(Boolean).join(" ")} style={{ whiteSpace: "pre-wrap" }}>
        {answer}
      </p>
    );
  }

  return (
    <ReadOnlyBodyContent
      content={parsed.doc.content ?? []}
      fallbackText={answer}
      className={["world-plan-agent-answer", className].filter(Boolean).join(" ")}
    />
  );
}
