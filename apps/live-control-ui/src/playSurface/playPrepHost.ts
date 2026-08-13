import { scopePrepCss } from "./scopePrepCss";
import type { PlayPanelId } from "./playPanels";

const PREP_ASSET = {
  css: "/prep/assets/prep.css",
  themesCss: "/prep/assets/prep-markdown-themes.css",
  markdownJs: "/prep/assets/prep-markdown.js",
  themesJs: "/prep/assets/prep-markdown-themes.js",
  prepJs: "/prep/assets/prep.js",
} as const;

const SCOPED_CSS_ID = "play-prep-scoped-css";
const THEMES_CSS_ID = "play-prep-themes-css";

export type MirewardPrepApi = {
  initNav: (activeId: string, navMode?: string) => void;
  wireRepoLinks: () => void;
  initMarkdownEmbeds: () => void;
  initRollTableCorpusIndex: (options?: object) => void;
  initItemWorkspaceIndex: (options?: object) => void;
  initStatblockCorpusIndex: (options?: object) => void;
  initCombatTracker: () => void;
};

declare global {
  interface Window {
    MirewardPrep?: MirewardPrepApi;
  }
}

let assetsPromise: Promise<void> | null = null;

function loadStylesheet(id: string, href: string): Promise<void> {
  const existing = document.getElementById(id);
  if (existing) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load ${href}`));
    document.head.appendChild(link);
  });
}

function loadScript(src: string): Promise<void> {
  const existing = document.querySelector(`script[data-play-prep-src="${src}"]`);
  if (existing) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = false;
    script.dataset.playPrepSrc = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
}

async function loadScopedPrepCss(): Promise<void> {
  if (document.getElementById(SCOPED_CSS_ID)) return;
  const res = await fetch(PREP_ASSET.css);
  if (!res.ok) throw new Error(`Failed to load ${PREP_ASSET.css}: HTTP ${res.status}`);
  const raw = await res.text();
  const style = document.createElement("style");
  style.id = SCOPED_CSS_ID;
  style.setAttribute("data-play-prep-css", "scoped");
  style.textContent = scopePrepCss(raw);
  document.head.appendChild(style);
}

/** Load prep CSS/JS once on the parent document. */
export function ensurePlayPrepAssets(): Promise<void> {
  if (window.MirewardPrep && document.getElementById(SCOPED_CSS_ID)) {
    return Promise.resolve();
  }
  if (!assetsPromise) {
    assetsPromise = (async () => {
      await loadScopedPrepCss();
      await loadStylesheet(THEMES_CSS_ID, PREP_ASSET.themesCss);
      await loadScript(PREP_ASSET.markdownJs);
      await loadScript(PREP_ASSET.themesJs);
      await loadScript(PREP_ASSET.prepJs);
      if (!window.MirewardPrep) {
        throw new Error("MirewardPrep failed to register after loading prep.js");
      }
    })().catch((err) => {
      assetsPromise = null;
      throw err;
    });
  }
  return assetsPromise;
}

/** Test helper: clear the memoized asset loader. */
export function resetPlayPrepAssetsForTests(): void {
  assetsPromise = null;
}

/** Strip scripts; keep .wrap (+ combat floating controls when present). */
export function extractPrepMarkup(html: string): { markup: string; bodyClass: string } {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script").forEach((node) => node.remove());
  const bodyClass = doc.body?.className?.trim() ?? "";
  const wrap = doc.querySelector(".wrap");
  const floating = doc.querySelector(".combat-floating-controls");
  if (wrap && floating) {
    return { markup: `${wrap.outerHTML}${floating.outerHTML}`, bodyClass };
  }
  if (wrap) {
    return { markup: wrap.outerHTML, bodyClass };
  }
  return { markup: doc.body?.innerHTML ?? "", bodyClass };
}

export function initPlayPanel(panel: PlayPanelId): void {
  const api = window.MirewardPrep;
  if (!api) throw new Error("MirewardPrep is not available");

  api.initNav(panel, "product");
  api.wireRepoLinks();

  if (panel === "combat") {
    api.initCombatTracker();
    return;
  }
  if (panel === "roll") {
    api.initRollTableCorpusIndex();
    return;
  }
  if (panel === "items") {
    api.initItemWorkspaceIndex();
    return;
  }
  api.initMarkdownEmbeds();
  api.initStatblockCorpusIndex();
}

export async function mountPlayPrepPanel(
  host: HTMLElement,
  embedSrc: string,
  panel: PlayPanelId,
): Promise<void> {
  await ensurePlayPrepAssets();
  const res = await fetch(embedSrc);
  if (!res.ok) {
    throw new Error(`Failed to load ${embedSrc}: HTTP ${res.status}`);
  }
  const html = await res.text();
  const { markup, bodyClass } = extractPrepMarkup(html);
  const classNames = ["play-surface__host", "prep-embed", bodyClass].filter(Boolean).join(" ");
  host.className = classNames;
  host.setAttribute("data-play-surface-host", panel);
  host.innerHTML = markup;
  initPlayPanel(panel);
}
