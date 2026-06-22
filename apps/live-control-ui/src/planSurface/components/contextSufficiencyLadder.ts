import type {
  AgentInteractionAdmittedContextItem,
  LiveContextEvidenceRef,
  LiveContextRejectedRef,
  LiveQueryResponse,
} from "../../api/types";

export type EvidenceQualityTier = "strong" | "okay" | "weak" | "debug";

export type ContextSufficiencyStatus =
  | "enough_context"
  | "weak_context"
  | "missing_context"
  | "wrong_context";

export interface ClassifiedEvidence {
  evidence: LiveContextEvidenceRef;
  tier: EvidenceQualityTier;
  label: string;
}

export interface EvidenceQualitySummary {
  strong: ClassifiedEvidence[];
  okay: ClassifiedEvidence[];
  weak: ClassifiedEvidence[];
  debug: ClassifiedEvidence[];
  summaryLine: string;
}

export interface SourceReviewItem {
  path: string;
  status: "excerpt_available" | "needs_source_read";
  excerpt: string | null;
  sourceRole: string;
  authority: string;
  preferred: boolean;
}

export interface ContextSufficiencyVerdict {
  status: ContextSufficiencyStatus;
  reason: string;
  loadedRoutes: string[];
  missingRoutes: string[];
  answerableNow: boolean;
}

export interface PacketReview {
  quality: EvidenceQualitySummary;
  campaignTextExcerpts: string[];
  admittedContextItems: AgentInteractionAdmittedContextItem[];
  weakItems: ClassifiedEvidence[];
  rejectedSummary: string[];
  suggestedRoutes: string[];
  sourceReviewWorklist: SourceReviewItem[];
  verdict: ContextSufficiencyVerdict;
}

const DEBUG_ROLES = new Set([
  "live_packet",
  "live_event",
  "planning_scaffold",
  "prep_scaffold",
  "reference_tool",
]);

const DEBUG_PATH_MARKERS = [
  "live_packet.json",
  "event_log.jsonl",
  "/manifest.json",
  "bootstrap",
  "evals/c2_live_prep/live/",
];

function isDebugMetadataPath(path: string): boolean {
  const normalized = normPath(path);
  if (normalized.endsWith(".records_meta.json")) return true;
  return DEBUG_PATH_MARKERS.some((marker) => normalized.includes(marker));
}

const STRONG_ROLES = new Set(["play_recap", "hub_evidence"]);
const STRONG_AUTHORITIES = new Set(["canon_play", "played_truth"]);

function normPath(path: string): string {
  return path.replace(/\\/g, "/").toLowerCase();
}

function looksLikeJsonBlob(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{")) return false;
  return (
    trimmed.includes('"schema"') ||
    trimmed.includes('"source_recap_path"') ||
    trimmed.includes('"schema_version"')
  );
}

function isDebugEvidence(evidence: LiveContextEvidenceRef): boolean {
  const role = evidence.source_role ?? "";
  const path = normPath(evidence.path ?? "");
  const excerpt = (evidence.text_excerpt ?? "").trim();
  if (DEBUG_ROLES.has(role) && !excerpt) return true;
  if (isDebugMetadataPath(path)) return true;
  if (excerpt && looksLikeJsonBlob(excerpt)) return true;
  if (role === "fresh_recap" && path.includes("evals/c2_live_prep/live/")) return true;
  return false;
}

function isBroadRecapRoute(path: string): boolean {
  const normalized = normPath(path);
  return (
    normalized.includes("/session recaps/_normalized/") ||
    (normalized.includes("/session recaps/session ") &&
      !normalized.includes("_breadcrumbed") &&
      !normalized.includes("_session_memory"))
  );
}

function isCanonRecapPath(path: string): boolean {
  const normalized = normPath(path);
  return (
    normalized.includes("/session recaps/session ") &&
    !normalized.includes("/_normalized/") &&
    !normalized.includes("/_breadcrumbed/") &&
    !normalized.includes("/_session_memory/")
  );
}

export function classifyEvidence(evidence: LiveContextEvidenceRef): ClassifiedEvidence {
  const excerpt = (evidence.text_excerpt ?? "").trim();
  const path = evidence.path ?? "";
  const role = evidence.source_role ?? "";
  const authority = evidence.authority ?? "";

  if (isDebugEvidence(evidence)) {
    return {
      evidence,
      tier: "debug",
      label: `${role || "metadata"} · ${path.split("/").pop() ?? path}`,
    };
  }

  const hasLineRange =
    evidence.line_start != null &&
    evidence.line_end != null &&
    evidence.line_start === evidence.line_end;
  const hasUsefulExcerpt =
    excerpt.length >= 40 &&
    !looksLikeJsonBlob(excerpt) &&
    !excerpt.startsWith("{");

  if (
    hasUsefulExcerpt &&
    (STRONG_ROLES.has(role) || STRONG_AUTHORITIES.has(authority) || role === "session_memory")
  ) {
    return { evidence, tier: "strong", label: `${role} · excerpt` };
  }

  if (hasUsefulExcerpt && (hasLineRange || evidence.unit_id)) {
    return { evidence, tier: "okay", label: `${role} · anchored excerpt` };
  }

  if (isBroadRecapRoute(path) && !hasUsefulExcerpt) {
    return { evidence, tier: "weak", label: `${role} · broad recap route` };
  }

  if (!excerpt && path) {
    return { evidence, tier: "weak", label: `${role} · route only` };
  }

  if (hasUsefulExcerpt) {
    return { evidence, tier: "okay", label: `${role} · excerpt` };
  }

  return { evidence, tier: "weak", label: `${role} · low-signal excerpt` };
}

export function summarizeEvidenceQuality(
  admitted: LiveContextEvidenceRef[],
): EvidenceQualitySummary {
  const classified = admitted.map(classifyEvidence);
  const strong = classified.filter((item) => item.tier === "strong");
  const okay = classified.filter((item) => item.tier === "okay");
  const weak = classified.filter((item) => item.tier === "weak");
  const debug = classified.filter((item) => item.tier === "debug");

  const parts: string[] = [];
  if (strong.length) parts.push(`${strong.length} campaign-text excerpt${strong.length === 1 ? "" : "s"}`);
  if (okay.length) parts.push(`${okay.length} anchored excerpt${okay.length === 1 ? "" : "s"}`);
  if (weak.length) parts.push(`${weak.length} broad route${weak.length === 1 ? "" : "s"}`);
  if (debug.length) parts.push(`${debug.length} debug/metadata item${debug.length === 1 ? "" : "s"}`);

  const tierLabel =
    strong.length >= 1
      ? "Strong"
      : okay.length >= 1
        ? "Okay"
        : weak.length >= 1
          ? "Weak"
          : debug.length
            ? "Debug only"
            : "Empty";

  const summaryLine =
    parts.length > 0 ? `${tierLabel}: ${parts.join(", ")}.` : `${tierLabel}: no admitted evidence.`;

  return { strong, okay, weak, debug, summaryLine };
}

function preferCanonOverNormalized(routes: string[]): string[] {
  const bySession = new Map<number, { canon?: string; normalized?: string; other: string[] }>();

  for (const route of routes) {
    const sessionMatch = route.match(/session\s+(\d+)/i);
    const session = sessionMatch ? Number(sessionMatch[1]) : -1;
    const bucket = bySession.get(session) ?? { other: [] };
    if (isCanonRecapPath(route)) {
      bucket.canon = route;
    } else if (normPath(route).includes("/_normalized/")) {
      bucket.normalized = route;
    } else {
      bucket.other.push(route);
    }
    bySession.set(session, bucket);
  }

  const preferred: string[] = [];
  for (const bucket of bySession.values()) {
    if (bucket.canon) preferred.push(bucket.canon);
    else if (bucket.normalized) preferred.push(bucket.normalized);
    preferred.push(...bucket.other);
  }
  return [...new Set(preferred)];
}

export function buildSourceReviewWorklist(
  classified: ClassifiedEvidence[],
): SourceReviewItem[] {
  const routesSeen = new Set<string>();
  const items: SourceReviewItem[] = [];

  for (const { evidence, tier } of classified) {
    const path = evidence.path?.trim();
    if (!path || routesSeen.has(path)) continue;
    routesSeen.add(path);

    const excerpt = evidence.text_excerpt?.trim() || null;
    const hasCampaignExcerpt =
      excerpt != null && excerpt.length >= 40 && !looksLikeJsonBlob(excerpt);

    items.push({
      path,
      status: hasCampaignExcerpt ? "excerpt_available" : "needs_source_read",
      excerpt: hasCampaignExcerpt ? excerpt : null,
      sourceRole: evidence.source_role ?? "unknown",
      authority: evidence.authority ?? "unknown",
      preferred: isCanonRecapPath(path) || tier === "strong",
    });
  }

  const preferredPaths = preferCanonOverNormalized(items.map((item) => item.path));
  const rank = new Map(preferredPaths.map((path, index) => [path, index]));
  return items.sort((a, b) => (rank.get(a.path) ?? 999) - (rank.get(b.path) ?? 999));
}

const ENDING_BEAT_MARKERS = [
  "lightning bolt",
  "turn the tide",
  "overrun",
  "will this be enough",
  "cliffhanger",
  "and that is how",
  "that's when",
  "finally",
  "at the end",
];

function looksLikeSessionEndingExcerpt(text: string | null | undefined): boolean {
  const lc = (text ?? "").toLowerCase();
  return ENDING_BEAT_MARKERS.some((marker) => lc.includes(marker));
}

function recapLinePosition(evidence: LiveContextEvidenceRef): number {
  return evidence.line_end ?? evidence.line_start ?? 0;
}

function sessionNumberFromPath(path: string): number | null {
  const match = path.match(/session\s+(\d{1,2})/i);
  return match ? Number(match[1]) : null;
}

export function filterAdmittedToTargetSession(
  admitted: LiveContextEvidenceRef[],
  sessionNumbers?: number[],
): LiveContextEvidenceRef[] {
  if (!sessionNumbers || sessionNumbers.length !== 1) {
    return admitted;
  }
  const target = sessionNumbers[0];
  return admitted.filter((evidence) => {
    const session = sessionNumberFromPath(evidence.path);
    return session === null || session === target;
  });
}

function filterRoutesToTargetSession(routes: string[], sessionNumbers?: number[]): string[] {
  if (!sessionNumbers || sessionNumbers.length !== 1) {
    return routes;
  }
  const target = sessionNumbers[0];
  const sessionPattern = new RegExp(`session\\s+${target}\\b`, "i");
  return routes.filter((path) => sessionPattern.test(path));
}

function maxRecapLine(admitted: LiveContextEvidenceRef[]): number {
  return admitted.reduce((max, evidence) => Math.max(max, recapLinePosition(evidence)), 0);
}

function isLateRecapBeat(evidence: LiveContextEvidenceRef, maxLine: number): boolean {
  if (looksLikeSessionEndingExcerpt(evidence.text_excerpt)) return true;
  const line = recapLinePosition(evidence);
  if (line >= 25) return true;
  if (maxLine >= 25 && line >= maxLine * 0.65) return true;
  return false;
}

function summarizeRejected(rejected: LiveContextRejectedRef[]): string[] {
  const counts = new Map<string, number>();
  for (const item of rejected) {
    const code = item.reason_code || "unknown";
    counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  return [...counts.entries()].map(([code, count]) => `${code}: ${count}`);
}

export function computeSufficiencyVerdict(
  quality: EvidenceQualitySummary,
  worklist: SourceReviewItem[],
  options?: {
    asksForLastOrFinal?: boolean;
    admitted?: LiveContextEvidenceRef[];
  },
): ContextSufficiencyVerdict {
  const loadedRoutes = worklist
    .filter((item) => item.status === "excerpt_available")
    .map((item) => item.path);
  const missingRoutes = worklist
    .filter((item) => item.status === "needs_source_read")
    .map((item) => item.path);

  const admitted = options?.admitted ?? [];
  const maxLine = maxRecapLine(admitted);
  const hasClosingBeat = [...quality.strong, ...quality.okay].some(({ evidence }) =>
    isLateRecapBeat(evidence, maxLine),
  );

  if (quality.strong.length >= 1) {
    if (options?.asksForLastOrFinal && !hasClosingBeat) {
      return {
        status: "weak_context",
        reason:
          "Admitted excerpts are from earlier session beats; open the recap closing lines before answering.",
        loadedRoutes,
        missingRoutes,
        answerableNow: false,
      };
    }
    return {
      status: "enough_context",
      reason: "At least one strong campaign-text excerpt was admitted.",
      loadedRoutes,
      missingRoutes,
      answerableNow: true,
    };
  }

  if (quality.okay.length >= 1 && quality.weak.length === 0 && quality.debug.length === 0) {
    return {
      status: "enough_context",
      reason: "Anchored excerpts were admitted without broad fallback routes.",
      loadedRoutes,
      missingRoutes,
      answerableNow: true,
    };
  }

  if (quality.weak.length >= 1 && quality.strong.length === 0 && quality.okay.length === 0) {
    return {
      status: "weak_context",
      reason: "Only broad recap routes or low-signal items were admitted; open source reads next.",
      loadedRoutes,
      missingRoutes,
      answerableNow: false,
    };
  }

  if (quality.debug.length >= 1 && quality.strong.length === 0 && quality.okay.length === 0) {
    return {
      status: "weak_context",
      reason: "Admitted evidence is mostly operational metadata, not campaign text.",
      loadedRoutes,
      missingRoutes,
      answerableNow: false,
    };
  }

  if (quality.strong.length === 0 && quality.okay.length === 0 && missingRoutes.length > 0) {
    return {
      status: "missing_context",
      reason: "No usable excerpts were admitted; inspect the suggested source routes.",
      loadedRoutes,
      missingRoutes,
      answerableNow: false,
    };
  }

  if (quality.weak.length > quality.strong.length + quality.okay.length) {
    return {
      status: "weak_context",
      reason: "Weak or broad admitted items outnumber strong campaign-text excerpts.",
      loadedRoutes,
      missingRoutes,
      answerableNow: false,
    };
  }

  return {
    status: "weak_context",
    reason: "Some excerpts were admitted, but additional source reads are still recommended.",
    loadedRoutes,
    missingRoutes,
    answerableNow: false,
  };
}

export function buildPacketReview(answer: LiveQueryResponse): PacketReview | null {
  const packet = answer.context_packet;
  if (!packet) return null;

  const sessionNumbers = packet.query_signals?.session_numbers;
  const admitted = filterAdmittedToTargetSession(packet.admitted_evidence ?? [], sessionNumbers);
  const quality = summarizeEvidenceQuality(admitted);
  const allClassified = [...quality.strong, ...quality.okay, ...quality.weak, ...quality.debug];
  const sourceReviewWorklist = buildSourceReviewWorklist(allClassified);
  const asksForLastOrFinal = packet.query_signals?.asks_for_last_or_final === true;
  const verdict = computeSufficiencyVerdict(quality, sourceReviewWorklist, {
    asksForLastOrFinal,
    admitted,
  });

  const campaignTextExcerpts = [...quality.strong, ...quality.okay]
    .sort(
      (a, b) =>
        recapLinePosition(b.evidence) - recapLinePosition(a.evidence) ||
        (b.evidence.text_excerpt?.length ?? 0) - (a.evidence.text_excerpt?.length ?? 0),
    )
    .map(({ evidence }) => evidence.text_excerpt?.trim())
    .filter((text): text is string => Boolean(text))
    .slice(0, asksForLastOrFinal ? 3 : 6);

  const admittedContextItems = admitted
    .map((evidence) => ({
      path: evidence.path,
      source_role: evidence.source_role,
      authority: evidence.authority,
      line_start: evidence.line_start ?? null,
      line_end: evidence.line_end ?? null,
      text_excerpt: evidence.text_excerpt?.trim() ?? "",
    }));

  const suggestedRoutes = filterRoutesToTargetSession(
    preferCanonOverNormalized(
      sourceReviewWorklist
        .filter((item) => item.status === "needs_source_read" || item.preferred)
        .filter((item) => !isDebugMetadataPath(item.path))
        .map((item) => item.path),
    ),
    sessionNumbers,
  ).slice(0, 6);

  return {
    quality,
    campaignTextExcerpts,
    admittedContextItems,
    weakItems: [...quality.weak, ...quality.debug],
    rejectedSummary: summarizeRejected(packet.rejected_evidence ?? []),
    suggestedRoutes,
    sourceReviewWorklist,
    verdict,
  };
}

export function admittedCampaignText(answer: LiveQueryResponse): string[] {
  const review = buildPacketReview(answer);
  if (review?.campaignTextExcerpts.length) {
    return review.campaignTextExcerpts;
  }
  const fallback = answer.context_packet?.admitted_evidence
    .map((evidence) => evidence.text_excerpt?.trim())
    .filter((excerpt): excerpt is string => Boolean(excerpt && !looksLikeJsonBlob(excerpt)));
  return fallback?.length ? fallback : [];
}
