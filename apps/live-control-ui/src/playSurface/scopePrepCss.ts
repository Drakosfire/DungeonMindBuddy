/**
 * Prefix prep.css selectors under a Play host so globals do not restyle AppChrome.
 * Portal chrome (markdown viewer / popovers) stays document-global.
 */

const DEFAULT_SCOPE = ".play-surface__host";

function isGlobalSelector(sel: string): boolean {
  return /md-viewer|runbook-ref|corpus-write|md-viewer-open/i.test(sel);
}

function mapSelector(raw: string, scope: string): string {
  const sel = raw.trim();
  if (!sel) return sel;
  if (isGlobalSelector(sel)) {
    return sel;
  }
  if (sel === "*" || sel === "*::*") {
    return `${scope}, ${scope} *`;
  }
  if (sel === ":root" || sel === "html" || sel === "body") {
    return scope;
  }
  if (sel.startsWith("body")) {
    // body.prep-embed .wrap → .play-surface__host.prep-embed .wrap
    return `${scope}${sel.slice("body".length)}`;
  }
  if (sel.startsWith("html")) {
    return `${scope}${sel.slice("html".length)}`;
  }
  return `${scope} ${sel}`;
}

function scopeSelectorList(selectorList: string, scope: string): string {
  return selectorList
    .split(",")
    .map((part) => mapSelector(part, scope))
    .filter(Boolean)
    .join(", ");
}

function scopeFlatRules(css: string, scope: string): string {
  return css.replace(
    /(^|\}|\/\*__PLAY_PREP_PARK_\d+__\*\/)\s*([^@}/][^{]*)\{/g,
    (_m, brace: string, selectors: string) =>
      `${brace}\n${scopeSelectorList(selectors, scope)} {`,
  );
}

/**
 * Best-effort CSS scoper. Handles flat rules and @media/@supports.
 * Leaves @keyframes / @font-face bodies untouched via placeholders.
 */
export function scopePrepCss(css: string, scope: string = DEFAULT_SCOPE): string {
  const park: string[] = [];

  function parkBalancedAtRule(source: string, atName: RegExp): string {
    let out = "";
    let i = 0;
    while (i < source.length) {
      const slice = source.slice(i);
      const match = slice.match(atName);
      if (!match || match.index == null) {
        out += source.slice(i);
        break;
      }
      const start = i + match.index;
      out += source.slice(i, start);
      const openBrace = source.indexOf("{", start);
      if (openBrace < 0) {
        out += source.slice(start);
        break;
      }
      let depth = 0;
      let end = openBrace;
      for (; end < source.length; end += 1) {
        const ch = source[end];
        if (ch === "{") depth += 1;
        else if (ch === "}") {
          depth -= 1;
          if (depth === 0) {
            end += 1;
            break;
          }
        }
      }
      const block = source.slice(start, end);
      const idx = park.length;
      park.push(block);
      out += `/*__PLAY_PREP_PARK_${idx}__*/`;
      i = end;
    }
    return out;
  }

  const parked = parkBalancedAtRule(css, /@(?:keyframes|font-face)\b/i);

  const withMedia = parked.replace(
    /(@(?:media|supports)[^{]+)\{([\s\S]*?)\}/g,
    (_m, header: string, inner: string) => `${header}{\n${scopeFlatRules(inner, scope)}\n}`,
  );

  const scoped = scopeFlatRules(withMedia, scope);
  return scoped.replace(/\/\*__PLAY_PREP_PARK_(\d+)__\*\//g, (_m, idx: string) => park[Number(idx)] ?? "");
}
