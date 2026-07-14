import type {
  HermesGraphGrounding,
  HermesGraphGroundingState,
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

const HERMES_GROUNDING_STATES: readonly HermesGraphGroundingState[] = [
  "grounded",
  "partial",
  "abstained",
  "error",
];

const FOCUS_KINDS = ["none", "session"] as const;

export function prepMemoryLabel(sessionDescriptor: PlanSessionDescriptor): string {
  return `Memory through Session ${sessionDescriptor.memorySession} · preparing Session ${sessionDescriptor.prepSession}`;
}

export function isHermesGraphAgentResponse(answer: LiveQueryResponse): boolean {
  return answer.mode === "hermes_graph_agent";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeStringArray(value: unknown): string[] | null {
  if (value == null) return [];
  if (!Array.isArray(value)) return null;
  if (!value.every((item) => typeof item === "string")) return null;
  return value;
}

function parseFocus(
  value: unknown,
): { kind: "none" | "session"; session_id: string | null } | null {
  if (!isRecord(value)) return null;
  if (value.kind !== "none" && value.kind !== "session") return null;
  if (!(value.session_id === null || typeof value.session_id === "string")) return null;
  return {
    kind: value.kind,
    session_id: value.session_id,
  };
}

/** Parse and normalize a Hermes grounding envelope from unknown JSON. */
export function parseHermesGraphGrounding(value: unknown): HermesGraphGrounding | null {
  if (!isRecord(value)) return null;
  if (value.schema !== "dmb_hermes_graph_grounding_v1") return null;
  if (typeof value.state !== "string" || !HERMES_GROUNDING_STATES.includes(value.state as HermesGraphGroundingState)) {
    return null;
  }
  if (!isNonEmptyString(value.world_id)) return null;
  if (!isNonEmptyString(value.campaign_id)) return null;
  if (!isNonEmptyString(value.admissibility)) return null;
  if (!(value.revision_id === null || typeof value.revision_id === "string")) return null;
  if (typeof value.successful_tool_count !== "number" || !Number.isFinite(value.successful_tool_count)) {
    return null;
  }
  if (typeof value.source_anchor_count !== "number" || !Number.isFinite(value.source_anchor_count)) {
    return null;
  }
  const focus = parseFocus(value.focus);
  if (!focus) return null;
  const diagnostic_codes = normalizeStringArray(value.diagnostic_codes);
  const warnings = normalizeStringArray(value.warnings);
  if (diagnostic_codes === null || warnings === null) return null;

  return {
    schema: "dmb_hermes_graph_grounding_v1",
    state: value.state as HermesGraphGroundingState,
    world_id: value.world_id,
    campaign_id: value.campaign_id,
    focus,
    admissibility: value.admissibility,
    revision_id: value.revision_id,
    successful_tool_count: value.successful_tool_count,
    source_anchor_count: value.source_anchor_count,
    diagnostic_codes,
    warnings,
  };
}

/** Parse a graph citation from unknown JSON without throwing on null/primitives. */
export function parseWorldGraphAnchorCitation(value: unknown): WorldGraphAnchorCitation | null {
  if (!isRecord(value)) return null;
  if (value.schema !== "dmb_world_graph_anchor_citation_v1") return null;
  if (value.kind !== "world_graph_anchor") return null;
  if (!isNonEmptyString(value.anchor_id)) return null;
  if (!isNonEmptyString(value.world_id)) return null;
  if (!isNonEmptyString(value.campaign_id)) return null;
  if (!isNonEmptyString(value.admissibility)) return null;
  if (!isNonEmptyString(value.revision_id)) return null;
  const focus = parseFocus(value.focus);
  if (!focus) return null;
  if (!FOCUS_KINDS.includes(focus.kind)) return null;

  return {
    schema: "dmb_world_graph_anchor_citation_v1",
    kind: "world_graph_anchor",
    anchor_id: value.anchor_id,
    world_id: value.world_id,
    campaign_id: value.campaign_id,
    focus,
    admissibility: value.admissibility,
    revision_id: value.revision_id,
  };
}

export function isWorldGraphAnchorCitation(
  citation: unknown,
): citation is WorldGraphAnchorCitation {
  return parseWorldGraphAnchorCitation(citation) !== null;
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

function evidenceRevisionIsPinned(grounding: HermesGraphGrounding): boolean {
  return isNonEmptyString(grounding.revision_id);
}

export function validateHermesGraphCitations(
  citations: unknown,
  grounding: unknown,
): {
  grounding: HermesGraphGrounding | null;
  citations: WorldGraphAnchorCitation[];
  contractWarning: string | null;
} {
  const parsedGrounding = parseHermesGraphGrounding(grounding);
  if (!parsedGrounding) {
    return {
      grounding: null,
      citations: [],
      contractWarning: "Hermes grounding contract error",
    };
  }

  const rawList = Array.isArray(citations) ? citations : [];
  const graphCitations = rawList
    .map((item) => parseWorldGraphAnchorCitation(item))
    .filter((item): item is WorldGraphAnchorCitation => item !== null);

  if (parsedGrounding.state === "abstained" || parsedGrounding.state === "error") {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: graphCitations.length
        ? "Graph citations ignored for abstained or error grounding."
        : null,
    };
  }

  if (parsedGrounding.state !== "grounded" && parsedGrounding.state !== "partial") {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: "Hermes grounding contract error",
    };
  }

  if (!evidenceRevisionIsPinned(parsedGrounding)) {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: "Hermes grounding contract error",
    };
  }

  const validated = graphCitations.filter((citation) => (
    citation.world_id === parsedGrounding.world_id
    && citation.campaign_id === parsedGrounding.campaign_id
    && citation.admissibility === parsedGrounding.admissibility
    && focusMatches(citation, parsedGrounding)
    && citation.revision_id === parsedGrounding.revision_id
  ));

  const droppedCount = graphCitations.length - validated.length;
  if (validated.length === 0) {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: droppedCount > 0
        ? "One or more graph citations were dropped due to scope or revision mismatch."
        : "Hermes grounding contract error",
    };
  }

  return {
    grounding: parsedGrounding,
    citations: validated,
    contractWarning: droppedCount > 0
      ? "One or more graph citations were dropped due to scope or revision mismatch."
      : null,
  };
}

export function hasGrounding(answer: LiveQueryResponse): boolean {
  if (isHermesGraphAgentResponse(answer)) {
    const { citations, grounding } = validateHermesGraphCitations(answer.citations, answer.grounding);
    if (!grounding) return false;
    if (grounding.state !== "grounded" && grounding.state !== "partial") return false;
    return citations.length > 0;
  }

  return Boolean(
    answer.context_packet?.admitted_evidence?.length
    || answer.citations?.length,
  );
}

export function answerHeading(answer: LiveQueryResponse): string {
  if (isHermesGraphAgentResponse(answer)) {
    const validated = validateHermesGraphCitations(answer.citations, answer.grounding);
    if (!validated.grounding) {
      return "Hermes grounding contract error";
    }

    switch (validated.grounding.state) {
      case "grounded":
        return validated.citations.length > 0
          ? "Graph-grounded answer"
          : "Hermes grounding contract error";
      case "partial":
        return validated.citations.length > 0
          ? "Qualified graph answer"
          : "Hermes grounding contract error";
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
