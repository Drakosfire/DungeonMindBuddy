export const PLAYABLE_ELEMENT_MARKER_VERSION = "v1" as const;
export const PLAYABLE_ELEMENT_MARKER_VERSION_V2 = "v2" as const;
export const PLAYABLE_ELEMENT_MARKER_PREFIX = "dmb-playable-element:" as const;

export const PLAYABLE_ELEMENT_KINDS = ["scene", "beat", "choice", "option"] as const;
export type PlayableElementKind = (typeof PLAYABLE_ELEMENT_KINDS)[number];

export type PlayableElementVersion = "v1" | "v2";

export const PLAYABLE_BEAT_KINDS = ["spine", "optional", "interrupt"] as const;
export type PlayableBeatKind = (typeof PLAYABLE_BEAT_KINDS)[number];

/**
 * Playable element identity carried on editor nodes.
 *
 * `version` selects the grammar: absent/"v1" is the Scene-first grammar
 * (Scene H2, Beat/Choice H3, Option H4); "v2" is the Beat-first grammar
 * (Beat H2, Scene/Choice H3 Beat-owned siblings, Option as a marked list
 * item). v2-only attributes: `beatKind` (beat), `sceneId` (choice Scene
 * association), `activates`/`suppresses` (option transition edges).
 */
export type PlayableElementIdentity = {
  kind: PlayableElementKind;
  id: string;
  version?: PlayableElementVersion;
  beatKind?: PlayableBeatKind;
  sceneId?: string;
  activates?: string[];
  suppresses?: string[];
};

export type PlayableHtmlCommentParse =
  | { status: "not-marker" }
  | { status: "malformed"; reason: string }
  | { status: "canonical"; identity: PlayableElementIdentity };

const CANONICAL_COMMENT_PATTERN =
  /^<!-- dmb-playable-element:v1 kind=(scene|beat|choice|option) id=((?:scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}) -->$/;
const PLAYABLE_ID_PATTERN = /^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$/;

const V2_ID_TAIL = "[a-z0-9][a-z0-9._-]{0,127}";
const V2_ID_SOURCE = `((?:beat|scene|choice|option):${V2_ID_TAIL})`;
const V2_SCENE_ID_SOURCE = `(scene:${V2_ID_TAIL})`;
const V2_EDGE_LIST_SOURCE = `((?:beat|scene):${V2_ID_TAIL}(?:,(?:beat|scene):${V2_ID_TAIL})*)`;
const CANONICAL_COMMENT_PATTERN_V2_BEAT = new RegExp(
  `^<!-- dmb-playable-element:v2 kind=beat id=${V2_ID_SOURCE}(?: beat_kind=(spine|optional|interrupt))? -->$`,
);
const CANONICAL_COMMENT_PATTERN_V2_SCENE = new RegExp(
  `^<!-- dmb-playable-element:v2 kind=scene id=${V2_ID_SOURCE} -->$`,
);
const CANONICAL_COMMENT_PATTERN_V2_CHOICE = new RegExp(
  `^<!-- dmb-playable-element:v2 kind=choice id=${V2_ID_SOURCE}(?: scene=${V2_SCENE_ID_SOURCE})? -->$`,
);
const CANONICAL_COMMENT_PATTERN_V2_OPTION = new RegExp(
  `^<!-- dmb-playable-element:v2 kind=option id=${V2_ID_SOURCE}(?: activates=${V2_EDGE_LIST_SOURCE})?(?: suppresses=${V2_EDGE_LIST_SOURCE})? -->$`,
);
const MARKER_VERSION_PROBE_PATTERN = /dmb-playable-element:(v[0-9]+)/;

export const PLAYABLE_ELEMENT_KIND_HTML_ATTR = "data-dmb-playable-kind" as const;
export const PLAYABLE_ELEMENT_ID_HTML_ATTR = "data-dmb-playable-id" as const;
export const PLAYABLE_ELEMENT_VERSION_HTML_ATTR = "data-dmb-playable-version" as const;
export const PLAYABLE_BEAT_KIND_HTML_ATTR = "data-dmb-playable-beat-kind" as const;
export const PLAYABLE_SCENE_ID_HTML_ATTR = "data-dmb-playable-scene-id" as const;
export const PLAYABLE_ACTIVATES_HTML_ATTR = "data-dmb-playable-activates" as const;
export const PLAYABLE_SUPPRESSES_HTML_ATTR = "data-dmb-playable-suppresses" as const;

export const PLAYABLE_ELEMENT_DIAGNOSTIC = {
  malformed: "Malformed playable element marker; identity was not attached.",
  orphan: "Playable element marker is orphaned; it must immediately precede a heading.",
  orphanOption: "Playable option marker is orphaned; it must immediately precede a list item.",
  levelMismatch: "Playable element kind does not match heading level; identity was not attached.",
  duplicate: "Duplicate playable element id; identity was not attached.",
  invalidAttrs: "Playable heading attributes are invalid; identity cannot be serialized.",
  invalidOptionAttrs: "Playable option list-item attributes are invalid; identity cannot be serialized.",
  duplicateAttrs: "Duplicate playable element id in editor JSON; identity cannot be serialized.",
  nested: "Playable identity is only serializable on a document-root heading.",
  nestedOption: "Playable option identity is only serializable on a top-level list item.",
  mixedVersions: "Mixed v1/v2 playable element markers in one document; identity was not attached.",
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
  return (PLAYABLE_ELEMENT_KINDS as readonly string[]).includes(value as string);
}

export function isPlayableBeatKind(value: unknown): value is PlayableBeatKind {
  return (PLAYABLE_BEAT_KINDS as readonly string[]).includes(value as string);
}

export function isPlayableElementVersion(value: unknown): value is PlayableElementVersion {
  return value === "v1" || value === "v2";
}

export function headingLevelForPlayableKind(kind: PlayableElementKind): 2 | 3 | 4 {
  switch (kind) {
    case "scene":
      return 2;
    case "beat":
    case "choice":
      return 3;
    case "option":
      return 4;
  }
}

/**
 * Beat-first (v2) heading levels. v2 Options are marked list items, not
 * headings, so they have no heading level (null).
 */
export function headingLevelForPlayableKindV2(kind: PlayableElementKind): 2 | 3 | null {
  switch (kind) {
    case "beat":
      return 2;
    case "scene":
    case "choice":
      return 3;
    case "option":
      return null;
  }
}

export function isCanonicalPlayableElementId(kind: PlayableElementKind, id: string): boolean {
  if (!PLAYABLE_ID_PATTERN.test(id)) return false;
  return id.startsWith(`${kind}:`);
}

export function generatePlayableElementId(kind: PlayableElementKind): string {
  return `${kind}:${crypto.randomUUID().toLowerCase()}`;
}

function formatV2EdgeList(ids: readonly string[]): string {
  return ids.join(",");
}

export function formatPlayableElementMarker(identity: PlayableElementIdentity): string {
  if (identity.version === "v2") {
    const base = `<!-- dmb-playable-element:${PLAYABLE_ELEMENT_MARKER_VERSION_V2} kind=${identity.kind} id=${identity.id}`;
    switch (identity.kind) {
      case "beat":
        return `${base}${identity.beatKind ? ` beat_kind=${identity.beatKind}` : ""} -->`;
      case "scene":
        return `${base} -->`;
      case "choice":
        return `${base}${identity.sceneId ? ` scene=${identity.sceneId}` : ""} -->`;
      case "option": {
        const activates = identity.activates?.length
          ? ` activates=${formatV2EdgeList(identity.activates)}`
          : "";
        const suppresses = identity.suppresses?.length
          ? ` suppresses=${formatV2EdgeList(identity.suppresses)}`
          : "";
        return `${base}${activates}${suppresses} -->`;
      }
    }
  }
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
  if (match) {
    const kind = match[1] as PlayableElementKind;
    const id = match[2];
    if (!isCanonicalPlayableElementId(kind, id)) {
      return { status: "malformed", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed };
    }
    return { status: "canonical", identity: { kind, id } };
  }

  const v2 = parseV2PlayableHtmlComment(trimmed);
  if (v2) return { status: "canonical", identity: v2 };
  return { status: "malformed", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed };
}

function parseV2PlayableHtmlComment(trimmed: string): PlayableElementIdentity | null {
  const beat = CANONICAL_COMMENT_PATTERN_V2_BEAT.exec(trimmed);
  if (beat) {
    const identity: PlayableElementIdentity = { kind: "beat", id: beat[1], version: "v2" };
    if (beat[2]) identity.beatKind = beat[2] as PlayableBeatKind;
    return identity;
  }
  const scene = CANONICAL_COMMENT_PATTERN_V2_SCENE.exec(trimmed);
  if (scene) return { kind: "scene", id: scene[1], version: "v2" };
  const choice = CANONICAL_COMMENT_PATTERN_V2_CHOICE.exec(trimmed);
  if (choice) {
    const identity: PlayableElementIdentity = { kind: "choice", id: choice[1], version: "v2" };
    if (choice[2]) identity.sceneId = choice[2];
    return identity;
  }
  const option = CANONICAL_COMMENT_PATTERN_V2_OPTION.exec(trimmed);
  if (option) {
    const identity: PlayableElementIdentity = { kind: "option", id: option[1], version: "v2" };
    if (option[2]) identity.activates = option[2].split(",");
    if (option[3]) identity.suppresses = option[3].split(",");
    return identity;
  }
  return null;
}

/**
 * Version probe for mixed-grammar fail-closed checks: returns the marker
 * version spelling found in a comment line, if any playable marker probe is
 * present (canonical or not).
 */
export function playableMarkerVersionProbe(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = MARKER_VERSION_PROBE_PATTERN.exec(value);
  return match ? match[1] : null;
}

export type PlayableHeadingAttrs = {
  playableElementKind?: unknown;
  playableElementId?: unknown;
  playableElementVersion?: unknown;
  playableBeatKind?: unknown;
  playableSceneId?: unknown;
  level?: unknown;
};

export type PlayableHeadingValidation =
  | { status: "absent" }
  | { status: "invalid"; reason: string }
  | { status: "canonical"; identity: PlayableElementIdentity; level: 2 | 3 | 4 };

export function validatePlayableHeadingAttrs(attrs: PlayableHeadingAttrs | null | undefined): PlayableHeadingValidation {
  const kind = attrs?.playableElementKind ?? null;
  const id = attrs?.playableElementId ?? null;
  const version = attrs?.playableElementVersion ?? null;
  const beatKind = attrs?.playableBeatKind ?? null;
  const sceneId = attrs?.playableSceneId ?? null;
  if (
    (kind == null || kind === "") && (id == null || id === "")
    && (version == null || version === "") && (beatKind == null || beatKind === "")
    && (sceneId == null || sceneId === "")
  ) {
    return { status: "absent" };
  }
  if (!isPlayableElementKind(kind) || typeof id !== "string" || !isCanonicalPlayableElementId(kind, id)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
  }
  if (version != null && version !== "" && !isPlayableElementVersion(version)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
  }
  const resolvedVersion: PlayableElementVersion = isPlayableElementVersion(version) ? version : "v1";
  if (resolvedVersion === "v2") {
    const expectedLevel = headingLevelForPlayableKindV2(kind);
    if (expectedLevel === null) {
      return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
    }
    if (kind === "beat") {
      if (beatKind != null && beatKind !== "" && !isPlayableBeatKind(beatKind)) {
        return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
      }
      if (sceneId != null && sceneId !== "") {
        return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
      }
    } else if (kind === "choice") {
      if (beatKind != null && beatKind !== "") {
        return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
      }
      if (sceneId != null && sceneId !== "") {
        if (typeof sceneId !== "string" || !isCanonicalPlayableElementId("scene", sceneId)) {
          return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
        }
      }
    } else if ((beatKind != null && beatKind !== "") || (sceneId != null && sceneId !== "")) {
      return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
    }
    const requestedLevel = Number(attrs?.level);
    if (!Number.isInteger(requestedLevel) || requestedLevel !== expectedLevel) {
      return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch };
    }
    const identity: PlayableElementIdentity = { kind, id, version: "v2" };
    if (kind === "beat" && isPlayableBeatKind(beatKind)) identity.beatKind = beatKind;
    if (kind === "choice" && typeof sceneId === "string" && sceneId) identity.sceneId = sceneId;
    return { status: "canonical", identity, level: expectedLevel };
  }
  if ((beatKind != null && beatKind !== "") || (sceneId != null && sceneId !== "")) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidAttrs };
  }
  const requestedLevel = Number(attrs?.level);
  const expectedLevel = headingLevelForPlayableKind(kind);
  if (!Number.isInteger(requestedLevel) || requestedLevel !== expectedLevel) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch };
  }
  return { status: "canonical", identity: { kind, id }, level: expectedLevel };
}

export type PlayableOptionItemAttrs = {
  playableElementKind?: unknown;
  playableElementId?: unknown;
  playableElementVersion?: unknown;
  playableActivates?: unknown;
  playableSuppresses?: unknown;
};

export type PlayableOptionItemValidation =
  | { status: "absent" }
  | { status: "invalid"; reason: string }
  | { status: "canonical"; identity: PlayableElementIdentity };

function isCanonicalEdgeIdList(value: unknown): value is string[] {
  if (!Array.isArray(value)) return false;
  return value.every(
    (entry) => typeof entry === "string"
      && PLAYABLE_ID_PATTERN.test(entry)
      && (entry.startsWith("beat:") || entry.startsWith("scene:")),
  );
}

/** v2 Option identity on a list item (options are not headings in v2). */
export function validatePlayableOptionItemAttrs(
  attrs: PlayableOptionItemAttrs | null | undefined,
): PlayableOptionItemValidation {
  const kind = attrs?.playableElementKind ?? null;
  const id = attrs?.playableElementId ?? null;
  const version = attrs?.playableElementVersion ?? null;
  const activates = attrs?.playableActivates ?? null;
  const suppresses = attrs?.playableSuppresses ?? null;
  if (
    (kind == null || kind === "") && (id == null || id === "")
    && (version == null || version === "") && activates == null && suppresses == null
  ) {
    return { status: "absent" };
  }
  if (kind !== "option" || version !== "v2") {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidOptionAttrs };
  }
  if (typeof id !== "string" || !isCanonicalPlayableElementId("option", id)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidOptionAttrs };
  }
  if (activates != null && !isCanonicalEdgeIdList(activates)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidOptionAttrs };
  }
  if (suppresses != null && !isCanonicalEdgeIdList(suppresses)) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidOptionAttrs };
  }
  if (
    Array.isArray(activates) && Array.isArray(suppresses)
    && activates.some((target) => (suppresses as string[]).includes(target))
  ) {
    return { status: "invalid", reason: PLAYABLE_ELEMENT_DIAGNOSTIC.invalidOptionAttrs };
  }
  const identity: PlayableElementIdentity = { kind: "option", id, version: "v2" };
  if (Array.isArray(activates) && activates.length > 0) identity.activates = [...activates];
  if (Array.isArray(suppresses) && suppresses.length > 0) identity.suppresses = [...suppresses];
  return { status: "canonical", identity };
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
  visit: (node: JsonHeadingNode, parentType: string | null, parentNode: JsonHeadingNode | null) => void,
  parentType: string | null = null,
  parentNode: JsonHeadingNode | null = null,
): void {
  if (node === null || typeof node !== "object") return;
  const candidate = node as JsonHeadingNode;
  visit(candidate, parentType, parentNode);
  if (!Array.isArray(candidate.content)) return;
  const type = typeof candidate.type === "string" ? candidate.type : null;
  for (const child of candidate.content) walkJsonNodes(child, visit, type, candidate);
}

export function playableSerializationFailures(document: unknown): string[] {
  const identities: PlayableElementIdentity[] = [];
  const failures: string[] = [];

  const rootLists = new Set<object>();
  if (document !== null && typeof document === "object") {
    const rootContent = (document as { content?: unknown }).content;
    if (Array.isArray(rootContent)) {
      for (const child of rootContent) {
        if (child === null || typeof child !== "object") continue;
        const childType = (child as { type?: unknown }).type;
        if (childType === "bulletList" || childType === "orderedList") {
          rootLists.add(child);
        }
      }
    }
  }

  walkJsonNodes(document, (node, parentType, parentNode) => {
    if (node.type === "heading") {
      const validated = validatePlayableHeadingAttrs(node.attrs);
      if (validated.status === "absent") return;
      if (parentType !== "doc") {
        failures.push(PLAYABLE_ELEMENT_DIAGNOSTIC.nested);
        return;
      }
      if (validated.status === "invalid") failures.push(validated.reason);
      if (validated.status === "canonical") identities.push(validated.identity);
      return;
    }
    if (node.type !== "listItem") return;
    const validated = validatePlayableOptionItemAttrs(node.attrs);
    if (validated.status === "absent") return;
    if (parentNode === null || !rootLists.has(parentNode)) {
      failures.push(PLAYABLE_ELEMENT_DIAGNOSTIC.nestedOption);
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
