import type {
  HermesGraphGrounding,
  LiveQueryCitation,
  LiveQueryResponse,
  WorldGraphAnchorCitation,
} from "../../api/types";
import type { PlanSessionDescriptor } from "../types";

export const PREP_MEMORY_PROMPTS = [
  "What changed after the latest ingested recap?",
  "What unresolved threads matter for prep?",
  "Which NPCs are relevant next session?",
  "What threats should I have ready?",
  "What sources support this?",
] as const;

export function prepMemoryLabel(sessionDescriptor: PlanSessionDescriptor): string {
  return `Memory through Session ${sessionDescriptor.memorySession} · preparing Session ${sessionDescriptor.prepSession}`;
}

export function isHermesGraphAgentResponse(answer: LiveQueryResponse): boolean {
  return answer.mode === "hermes_graph_agent";
}

export function isWorldGraphAnchorCitation(
  citation: LiveQueryCitation,
): citation is WorldGraphAnchorCitation {
  return (
    citation.kind === "world_graph_anchor"
    && citation.schema === "dmb_world_graph_anchor_citation_v1"
    && Boolean(citation.anchor_id)
  );
}

function isValidHermesGrounding(
  grounding: HermesGraphGrounding | null | undefined,
): grounding is HermesGraphGrounding {
  return grounding?.schema === "dmb_hermes_graph_grounding_v1";
}

function focusMatches(
  citation: WorldGraphAnchorCitation,
  grounding: HermesGraphGrounding,
): boolean {
  return (
    citation.focus.kind === grounding.focus.kind
    && citation.focus.session_id === grounding.focus.session_id
  );
}

function revisionMatches(
  citation: WorldGraphAnchorCitation,
  grounding: HermesGraphGrounding,
): boolean {
  if (grounding.revision_id === null) return true;
  return citation.revision_id === grounding.revision_id;
}

export function validateHermesGraphCitations(
  citations: LiveQueryCitation[] | null | undefined,
  grounding: HermesGraphGrounding | null | undefined,
): { citations: WorldGraphAnchorCitation[]; contractWarning: string | null } {
  if (!isValidHermesGrounding(grounding)) {
    return { citations: [], contractWarning: "Hermes grounding contract error" };
  }

  const graphCitations = (citations ?? []).filter(isWorldGraphAnchorCitation);

  if (grounding.state === "abstained" || grounding.state === "error") {
    return {
      citations: [],
      contractWarning: graphCitations.length ? "Graph citations ignored for abstained or error grounding." : null,
    };
  }

  if (grounding.state !== "grounded" && grounding.state !== "partial") {
    return { citations: [], contractWarning: "Hermes grounding contract error" };
  }

  const validated = graphCitations.filter((citation) => (
    citation.world_id === grounding.world_id
    && citation.campaign_id === grounding.campaign_id
    && citation.admissibility === grounding.admissibility
    && focusMatches(citation, grounding)
    && revisionMatches(citation, grounding)
  ));

  const droppedCount = graphCitations.length - validated.length;
  if (validated.length === 0) {
    return {
      citations: [],
      contractWarning: droppedCount > 0
        ? "One or more graph citations were dropped due to scope or revision mismatch."
        : "Hermes grounding contract error",
    };
  }

  return {
    citations: validated,
    contractWarning: droppedCount > 0
      ? "One or more graph citations were dropped due to scope or revision mismatch."
      : null,
  };
}

export function hasGrounding(answer: LiveQueryResponse): boolean {
  if (isHermesGraphAgentResponse(answer)) {
    if (!isValidHermesGrounding(answer.grounding)) return false;
    if (answer.grounding.state !== "grounded" && answer.grounding.state !== "partial") return false;
    return validateHermesGraphCitations(answer.citations, answer.grounding).citations.length > 0;
  }

  return Boolean(
    answer.context_packet?.admitted_evidence?.length
    || answer.citations?.length,
  );
}

export function answerHeading(answer: LiveQueryResponse): string {
  if (isHermesGraphAgentResponse(answer)) {
    if (!isValidHermesGrounding(answer.grounding)) {
      return "Hermes grounding contract error";
    }

    switch (answer.grounding.state) {
      case "grounded": {
        const { citations } = validateHermesGraphCitations(answer.citations, answer.grounding);
        return citations.length > 0 ? "Graph-grounded answer" : "Hermes grounding contract error";
      }
      case "partial": {
        const { citations } = validateHermesGraphCitations(answer.citations, answer.grounding);
        return citations.length > 0 ? "Qualified graph answer" : "Hermes grounding contract error";
      }
      case "abstained":
        return "Graph evidence gap";
      case "error":
        return "Hermes graph error";
      default:
        return "Hermes grounding contract error";
    }
  }

  return hasGrounding(answer) ? "Grounded answer" : "Ungrounded draft";
}

export const UNGROUNDED_ANSWER_WARNING =
  "No grounded evidence returned. DungeonBuddy did not find supporting campaign text for this answer. Treat this as ungrounded and verify in /ingest or source memory.";
