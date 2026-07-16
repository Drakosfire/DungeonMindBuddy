import type {
  AgentInteractionTurn,
  HermesGraphGrounding,
  HermesGraphGroundingState,
  LiveQueryCitation,
  LiveQueryResponse,
  WorldGraphAnchorCitation,
} from "../../api/types";
import type { PlanSessionDescriptor } from "../types";

const HERMES_GROUNDING_STATES: readonly HermesGraphGroundingState[] = [
  "grounded",
  "partial",
  "abstained",
  "error",
  "conversation_context",
];

const FOCUS_KINDS = ["none", "session"] as const;

export function prepMemoryLabel(sessionDescriptor: PlanSessionDescriptor): string {
  return sessionDescriptor.memorySession == null
    ? "World graph (all sessions)"
    : `Memory through Session ${sessionDescriptor.memorySession}`;
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

/** Authoritative focus: session requires non-empty session_id; none requires null. */
function parseFocus(
  value: unknown,
): { kind: "none" | "session"; session_id: string | null } | null {
  if (!isRecord(value)) return null;
  if (value.kind === "none") {
    if (value.session_id !== null) return null;
    return { kind: "none", session_id: null };
  }
  if (value.kind === "session") {
    if (!isNonEmptyString(value.session_id)) return null;
    return { kind: "session", session_id: value.session_id };
  }
  return null;
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
    acceptance_state: typeof value.acceptance_state === "string" ? value.acceptance_state : null,
    accepted_claim_ids: Array.isArray(value.accepted_claim_ids)
      ? value.accepted_claim_ids.filter((item): item is string => typeof item === "string")
      : undefined,
    rejected_claim_ids: Array.isArray(value.rejected_claim_ids)
      ? value.rejected_claim_ids.filter((item): item is string => typeof item === "string")
      : undefined,
    reason_codes: Array.isArray(value.reason_codes)
      ? value.reason_codes.filter((item): item is string => typeof item === "string")
      : undefined,
    graph_reference_count:
      typeof value.graph_reference_count === "number" && Number.isFinite(value.graph_reference_count)
        ? value.graph_reference_count
        : null,
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

/** Hermes answered from the visible conversation; no graph query this turn. */
export function isConversationContext(grounding: HermesGraphGrounding | null | undefined): boolean {
  return grounding?.state === "conversation_context";
}

/** S1 named-gap / admitted-recap partials are valid with zero graph claims. */
export function hasNamedEvidenceGap(grounding: HermesGraphGrounding): boolean {
  if (grounding.state !== "partial") return false;
  const reasons = grounding.reason_codes ?? [];
  return (
    reasons.includes("named_gap")
    || reasons.includes("latest_recap_memory_lag_disclosed")
    || reasons.includes("admitted_recap_source_read")
    || reasons.includes("hermes_agent_answer")
  );
}

function hasVisibleEvidenceSupport(
  grounding: HermesGraphGrounding,
  citations: WorldGraphAnchorCitation[],
  answer?: LiveQueryResponse,
): boolean {
  return (
    citations.length > 0
    || (grounding.accepted_claim_ids?.length ?? 0) > 0
    || (grounding.graph_reference_count ?? 0) > 0
    || (answer?.graph_references?.length ?? 0) > 0
    || (answer?.source_citations?.length ?? 0) > 0
  );
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

  if (parsedGrounding.state === "conversation_context") {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: graphCitations.length
        ? "Graph citations ignored for conversation-context turns."
        : null,
    };
  }

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
  const hasClaimLedgerSupport = (
    (parsedGrounding.accepted_claim_ids?.length ?? 0) > 0
    || (parsedGrounding.graph_reference_count ?? 0) > 0
    || (parsedGrounding.source_anchor_count ?? 0) > 0
  );
  const namedGapOk = hasNamedEvidenceGap(parsedGrounding);

  if (validated.length === 0) {
    return {
      grounding: parsedGrounding,
      citations: [],
      contractWarning: droppedCount > 0
        ? "One or more graph citations were dropped due to scope or revision mismatch."
        : hasClaimLedgerSupport || namedGapOk
          ? null
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
    if (hasNamedEvidenceGap(grounding)) return true;
    return hasVisibleEvidenceSupport(grounding, citations, answer);
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

    const hasSupport = hasVisibleEvidenceSupport(
      validated.grounding,
      validated.citations,
      answer,
    );

    switch (validated.grounding.state) {
      case "grounded":
        return hasSupport
          ? "Graph-grounded answer"
          : "Hermes grounding contract error";
      case "partial":
        if (hasNamedEvidenceGap(validated.grounding)) {
          const reasons = validated.grounding.reason_codes ?? [];
          if (reasons.includes("hermes_agent_answer")) {
            return "Hermes answer";
          }
          return "No Hermes answer";
        }
        return hasSupport
          ? "Qualified graph answer"
          : "Hermes grounding contract error";
      case "abstained":
        return "Graph evidence gap";
      case "error":
        return "Hermes graph error";
      case "conversation_context":
        return "Answered from conversation";
      default:
        return "Hermes grounding contract error";
    }
  }

  return hasGrounding(answer) ? "Grounded answer" : "Ungrounded draft";
}

export type AgentInteractionTurnS1Support = {
  lagDisclosure?: string | null;
  admittedRecapExcerpt?: string | null;
} | null;

/** S1 lag / admitted-recap support — never the Hermes chat bubble body. */
export function s1SupportFromAnswer(answer: LiveQueryResponse | null | undefined): AgentInteractionTurnS1Support {
  if (!answer) return null;
  const fromSupport = answer.s1_support;
  const fromLatest = isRecord(answer.latest_recap_change) ? answer.latest_recap_change : null;
  const lag =
    (typeof fromSupport?.lag_disclosure === "string" && fromSupport.lag_disclosure.trim()
      ? fromSupport.lag_disclosure.trim()
      : null)
    || (fromLatest && typeof fromLatest.lag_disclosure === "string" && fromLatest.lag_disclosure.trim()
      ? fromLatest.lag_disclosure.trim()
      : null);
  const excerpt =
    (typeof fromSupport?.admitted_recap_excerpt === "string" && fromSupport.admitted_recap_excerpt.trim()
      ? fromSupport.admitted_recap_excerpt.trim()
      : null)
    || (fromLatest && typeof fromLatest.admitted_recap_excerpt === "string"
      && fromLatest.admitted_recap_excerpt.trim()
      ? fromLatest.admitted_recap_excerpt.trim()
      : null);
  if (!lag && !excerpt) return null;
  return { lagDisclosure: lag, admittedRecapExcerpt: excerpt };
}

/** Resolve persisted turn S1 support, falling back to wire response fields. */
export function s1SupportFromTurn(
  turn: Pick<AgentInteractionTurn, "s1Support"> | null | undefined,
  wire?: LiveQueryResponse | null,
): AgentInteractionTurnS1Support {
  const persisted = turn?.s1Support;
  if (persisted?.lagDisclosure || persisted?.admittedRecapExcerpt) {
    return persisted;
  }
  return s1SupportFromAnswer(wire);
}

export const UNGROUNDED_ANSWER_WARNING =
  "No grounded evidence returned. DungeonBuddy did not find supporting campaign text for this answer. Treat this as ungrounded and verify in /ingest or source memory.";
