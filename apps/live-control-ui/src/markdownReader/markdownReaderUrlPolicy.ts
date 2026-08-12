/**
 * Centralized URL/media classification for the Markdown document reader.
 * Do not scatter ad-hoc scheme checks across node renderers.
 */

export type LinkUrlKind =
  | "safe_external"
  | "safe_mailto"
  | "fragment"
  | "relative_visible"
  | "unsafe";

export type ImageUrlKind = "safe_http" | "unresolved" | "unsafe";

function trimUrl(raw: string): string {
  return raw.trim();
}

function hasExecutableScheme(url: string): boolean {
  return /^(?:javascript|vbscript|data):/i.test(url);
}

/**
 * Classify a Markdown link destination for safe read-only presentation.
 *
 * Clickable: https / http / mailto / same-document #fragment.
 * Relative paths stay visible but are not navigable until a source-relative
 * contract exists. Unknown/executable schemes are never anchors.
 */
export function classifyLinkUrl(rawUrl: string): LinkUrlKind {
  const url = trimUrl(rawUrl);
  if (!url) return "unsafe";
  if (url.startsWith("#") && !url.startsWith("#/")) return "fragment";
  if (hasExecutableScheme(url)) return "unsafe";

  const lower = url.toLowerCase();
  if (lower.startsWith("https:") || lower.startsWith("http:")) return "safe_external";
  if (lower.startsWith("mailto:")) return "safe_mailto";

  // Scheme-like but not allowlisted (e.g. file:, ftp:, custom:) → unsafe.
  if (/^[a-z][a-z0-9+.-]*:/i.test(url)) return "unsafe";

  // Path-like / relative references — visible, non-navigating for this slice.
  return "relative_visible";
}

/**
 * Classify an image destination. Only explicit http(s) URLs render as <img>.
 * Relative/local paths are unresolved media; executable schemes are unsafe.
 */
export function classifyImageUrl(rawUrl: string): ImageUrlKind {
  const url = trimUrl(rawUrl);
  if (!url) return "unsafe";
  if (hasExecutableScheme(url)) return "unsafe";

  const lower = url.toLowerCase();
  if (lower.startsWith("https:") || lower.startsWith("http:")) return "safe_http";

  // Any other scheme (file:, data: image, blob:, …) is not allowlisted.
  if (/^[a-z][a-z0-9+.-]*:/i.test(url)) return "unsafe";

  return "unresolved";
}
