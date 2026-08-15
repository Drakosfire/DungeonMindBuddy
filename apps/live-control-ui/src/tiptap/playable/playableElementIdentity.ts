export const PLAYABLE_ELEMENT_MARKER_VERSION = "v1" as const;
export const PLAYABLE_ELEMENT_MARKER_PREFIX = "dmb-playable-element:" as const;

export const PLAYABLE_ELEMENT_KINDS = ["scene", "beat"] as const;
export type PlayableElementKind = (typeof PLAYABLE_ELEMENT_KINDS)[number];

export type PlayableElementIdentity = {
  kind: PlayableElementKind;
  id: string;
};

export type PlayableHtmlCommentParse =
  | { status: "not-marker" }
  | { status: "malformed"; reason: string }
  | { status: "canonical"; identity: PlayableElementIdentity };

const CANONICAL_COMMENT_PATTERN =
  /^<!-- dmb-playable-element:v1 kind=(scene|beat) id=((?:scene|beat):[a-z0-9][a-z0-9._-]{0,127}) -->$/;
const PLAYABLE_ID_PATTERN = /^(scene|beat):[a-z0-9][a-z0-9._-]{0,127}$/;

export const PLAYABLE_ELEMENT_KIND_HTML_ATTR = "data-dmb-playable-kind" as const;
export const PLAYABLE_ELEMENT_ID_HTML_ATTR = "data-dmb-playable-id" as const;

export const PLAYABLE_ELEMENT_DIAGNOSTIC = {
  malformed: "Malformed playable element marker; identity was not attached.",
  orphan: "Playable element marker is orphaned; it must immediately precede a heading.",
  levelMismatch: "Playable element kind does not match heading level; identity was not attached.",
  duplicate: "Duplicate playable element id; identity was not attached.",
  invalidAttrs: "Playable heading attributes are invalid; identity cannot be serialized.",
  duplicateAttrs: "Duplicate playable element id in editor JSON; identity cannot be serialized.",
  nested: "Playable identity is only serializable on a document-root heading.",
} as const;

export class PlayableIdentitySerializationError extends Error {
  readonly failures: readonly string[];

  constructor(failures: readonly string[]) {
    super(failures[0] ?? PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs);
    this.name = "PlayableIdentitySerializationError";
    this.failures = failures;
  }
}

export function isPlayableElementKind(value: unknown): value is PlayableElementKind {
  return value === "scene" || value === "beat";
}

export function headingLevelForPlayableKind(kind: PlayableElementKind): 2 | 3 {
  return kind === "scene" ? 2 : 3;
}

export function isCanonicalPlayableElementId(kind: PlayableElementKind, id: string): boolean {
  if (!PLAYABLE_ID_PATTERN.test(id)) return false;
  return id.startsWith(`${kind}:`);
}

export function generatePlayableElementId(kind: PlayableElementKind): string {
  return `${kind}:${crypto.randomUUID().toLowerCase()}`;
}

export function formatPlayableElementMarker(identity: PlayableElementIdentity): string {
  return `<!-- dmb-playable-element:${PLAYABLE_ELEMENT_MARKER_VERSION} kind=${identity.kind} id=${identity.id} -->`;
}

function normalizeHtmlCommentValue(value: string): string {
  return value.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").trim();
}

export function parsePlayableHtmlComment(value: unknown): PlayableHtmlCommentParse {
  if (typeof value !== "string") return { status: "not-marker" };
  const trimmed = normalizeHtmlCommentValue(value);
  if (!trimmed.includes(PLAYABLE_ELEMENT_MARKER_PREFIX)) return { status: "not-marker" };
  if (trimmed.includes("\n")) {
    return { status: "malformed", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed };
  }

  const match = CANONICAL_COMMENT_PATTERN.exec(trimmed);
  if (!match) {
    return { status: "malformed", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed };
  }

  const kind = match[1] as PlayableElementKind;
  const id = match[2];
  if (!isCanonicalPlayableElementId(kind, id)) {
    return { status: "malformed", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed };
  }
  return { status: "canonical", identity: { kind, id } };
}

export type PlayableHeadingAttrs = {
  playableElementKind?: unknown;
  playableElementId?: unknown;
  level?: unknown;
};

export type PlayableHeadingValidation =
  | { status: "absent" }
  | { status: "invalid"; reason: string }
  | { status: "canonical"; identity: PlayableElementIdentity; level: 2 | 3 };

export function validatePlayableHeadingAttrs(attrs: PlayableHeadingAttrs | null | undefined): PlayableHeadingValidation {
  const kind = attrs?.playableElementKind ?? null;
  const id = attrs?.playableElementId ?? null;
  if ((kind == null || kind === "") && (id == null || id === "")) {
    return { status: "absent" };
  }
  if (!isPlayableElementKind(kind) || typeof id !== "string" || !isCanonicalPlayableElementId(kind, id)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
  }
  const requestedLevel = Number(attrs?.level);
  const expectedLevel = headingLevelForPlayableKind(kind);
  if (!Number.isInteger(requestedLevel) || requestedLevel !== expectedLevel) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch };
  }
  return { status: "canonical", identity: { kind, id }, level: expectedLevel };
}

export type JsonHeadingNode = {
  type?: unknown;
  attrs?: PlayableHeadingAttrs | null;
  content?: unknown;
};

export function collectCanonicalPlayableIdentities(nodes: JsonHeadingNode[]): PlayableElementIdentity[] {
  const identities: PlayableElementIdentity[] = [];
  for (const node of nodes) {
    if (node.type !== "heading") continue;
    const validated = validatePlayableHeadingAttrs(node.attrs);
    if (validated.status === "canonical") identities.push(validated.identity);
  }
  return identities;
}

export function duplicatePlayableIds(identities: Iterable<PlayableElementIdentity>): Set<string> {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const identity of identities) {
    if (seen.has(identity.id)) duplicates.add(identity.id);
    else seen.add(identity.id);
  }
  return duplicates;
}

export function walkJsonNodes(
  node: unknown,
  visit: (node: JsonHeadingNode, parentType: string | null) => void,
  parentType: string | null = null,
): void {
  if (node === null || typeof node !== "object") return;
  const candidate = node as JsonHeadingNode;
  visit(candidate, parentType);
  if (!Array.isArray(candidate.content)) return;
  const type = typeof candidate.type === "string" ? candidate.type : null;
  for (const child of candidate.content) walkJsonNodes(child, visit, type);
}

export function playableSerializationFailures(document: unknown): string[] {
  const identities: PlayableElementIdentity[] = [];
  const failures: string[] = [];
  walkJsonNodes(document, (node, parentType) => {
    if (node.type !== "heading") return;
    const validated = validatePlayableHeadingAttrs(node.attrs);
    if (validated.status === "absent") return;
    if (parentType !== "doc") {
      failures.push(PLAYABLE_ELEMENT_DIAGNOSTIC.nested);
      return;
    }
    if (validated.status === "invalid") failures.push(validated.reason);
    if (validated.status === "canonical") identities.push(validated.identity);
  });
  if (duplicatePlayableIds(identities).size > 0) {
    failures.push(PLAYABLE_ELEMENT_DIAGNOSTIC.duplicateAttrs);
  }
  return failures;
}
