/**
 * Mireward prep static HTML — shared nav, repo links, localStorage persistence.
 */
(function () {
  const STORAGE_PREFIX = "mireward-prep.";
  const COMBAT_STORAGE_KEY = "combat.northReachGate";
  const COMBAT_STATE_UPDATED_EVENT = "mireward-prep:combat-state-updated";
  const STATBLOCK_DOGFOOD_DRAFT_KEY = "statblockDogfood.lastDraft";
  const STATBLOCK_CORPUS_INDEX_REFRESH_EVENT = "mireward-prep:statblock-corpus-index-refresh";
  const REPO_UP = "../../../";
  const PREP_WEB_PREFIX = location.pathname.startsWith("/evals/c2_live_prep/mireward-prep/")
    ? "/evals/c2_live_prep/mireward-prep/"
    : "/";

  const NAV = [
    { id: "index", label: "Index", href: "index.html" },
    { id: "live-play", label: "Live play", href: "live-play.html" },
    { id: "retrieval", label: "Retrieval", href: "retrieval.html" },
    { id: "combat", label: "Combat tracker", href: "combat.html" },
    { id: "live-notes", label: "Live notes", href: "live-notes.html" },
    { id: "timeline", label: "Timeline", href: "timeline.html" },
    { id: "locations", label: "Locations", href: "locations.html" },
    { id: "npcs", label: "NPCs", href: "npcs.html" },
    { id: "roll-tables", label: "Roll tables", href: "roll-tables.html" },
    { id: "statblocks", label: "Statblocks", href: "statblocks.html" },
    { id: "markdown-theme-fixtures", label: "Theme fixtures", href: "markdown-theme-fixtures.html" },
  ];

  function isFileProtocol() {
    return location.protocol === "file:";
  }

  function encodeRepoPath(repoRelative) {
    return repoRelative
      .split("/")
      .map(function (seg) {
        return encodeURIComponent(seg);
      })
      .join("/");
  }

  /** @param {string} repoRelative e.g. corpus/eldyrwild-markdown/... or Docs/Plans/... */
  function repoHref(repoRelative) {
    if (isFileProtocol()) {
      if (repoRelative.startsWith("evals/c2_live_prep/artifacts/")) {
        return "../" + repoRelative.slice("evals/c2_live_prep/".length);
      }
      return REPO_UP + repoRelative;
    }
    return "/" + encodeRepoPath(repoRelative);
  }

  function navHref(page) {
    if (isFileProtocol()) return page;
    return PREP_WEB_PREFIX + page;
  }

  function get(key, fallback) {
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + key);
      if (raw === null) return fallback;
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  function set(key, value) {
    try {
      localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
    } catch {
      /* quota / private mode */
    }
  }

  function bindTextarea(key, el, defaultValue) {
    if (!el) return;
    el.value = get(key, defaultValue ?? "");
    el.addEventListener("input", () => set(key, el.value));
  }

  function bindCheckbox(key, el, defaultChecked) {
    if (!el) return;
    el.checked = get(key, defaultChecked ?? false);
    el.addEventListener("change", () => set(key, el.checked));
  }

  function bindTimelineBeat(beatId) {
    const el = document.querySelector('[data-beat-check="' + beatId + '"]');
    if (!el) return;
    const storeKey = "timelineChecked";
    const all = get(storeKey, {
      "s22-end-gate": true,
      "lysandro-reveal": true,
      "vale-warning": true,
    });
    el.checked = !!all[beatId];
    el.addEventListener("change", () => {
      const next = get(storeKey, {});
      next[beatId] = el.checked;
      set(storeKey, next);
    });
  }

  function initNav(activeId) {
    const host = document.getElementById("site-nav");
    if (!host) return;
    host.innerHTML = NAV.map(function (item) {
      const cls = item.id === activeId ? "active" : "";
      return (
        '<a class="' +
        cls +
        '" href="' +
        navHref(item.href) +
        '">' +
        item.label +
        "</a>"
      );
    }).join("");
  }

  function initScratchBand() {
    const details = document.getElementById("scratch-band");
    const ta = document.getElementById("scratch-pad");
    const preview = document.getElementById("scratch-preview");
    if (!details || !ta) return;

    details.open = get("scratchOpen", true);
    bindTextarea("tableNotes", ta, "");

    function updatePreview() {
      if (!preview) return;
      const line =
        ta.value
          .trim()
          .split("\n")
          .find(function (l) {
            return l.trim();
          }) || "";
      preview.textContent = line
        ? line.length > 72
          ? line.slice(0, 72) + "…"
          : line
        : "Empty — expand to write";
    }

    ta.addEventListener("input", updatePreview);
    updatePreview();

    details.addEventListener("toggle", function () {
      set("scratchOpen", details.open);
      updatePreview();
    });
  }

  function isMarkdownRepoPath(repoRelative) {
    return /\.md$/i.test(repoRelative || "");
  }

  let markdownClickBound = false;

  function ensureMarkdownModal() {
    let root = document.getElementById("md-viewer");
    if (root) return root;

    root = document.createElement("div");
    root.id = "md-viewer";
    root.className = "md-viewer";
    root.hidden = true;
    root.innerHTML =
      '<div class="md-viewer-backdrop" data-md-close="1"></div>' +
      '<div class="md-viewer-panel" role="dialog" aria-modal="true" aria-labelledby="md-viewer-title">' +
      '<header class="md-viewer-hd">' +
      '<div class="md-viewer-meta">' +
      '<div id="md-viewer-title" class="md-viewer-title"></div>' +
      '<div id="md-viewer-path" class="md-viewer-path mono"></div>' +
      "</div>" +
      '<div class="md-viewer-actions">' +
      '<a id="md-viewer-raw" class="md-viewer-raw" href="#" target="_blank" rel="noopener">Open raw</a>' +
      '<button type="button" class="md-viewer-close" data-md-close="1" aria-label="Close preview">×</button>' +
      "</div>" +
      "</header>" +
      '<div id="md-viewer-body" class="md-viewer-body md-content"></div>' +
      "</div>";
    document.body.appendChild(root);

    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-md-close]")) closeMarkdownViewer();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !root.hidden) closeMarkdownViewer();
    });

    return root;
  }

  function closeMarkdownViewer() {
    const root = document.getElementById("md-viewer");
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("md-viewer-open");
  }

  function applyMarkdownContentTheme(el, themeId) {
    const resolvedThemeId = themeId || "command";
    const tools = window.MirewardMarkdownThemeTools;
    if (!el || !tools || typeof tools.applyMarkdownTheme !== "function") {
      if (el && resolvedThemeId && el.setAttribute) {
        el.setAttribute("data-md-theme", resolvedThemeId);
      }
      return resolvedThemeId;
    }

    return tools.applyMarkdownTheme(el, resolvedThemeId);
  }

  function setMarkdownViewerState(kind, repoRelative, message, viewerMeta) {
    viewerMeta = viewerMeta || {};
    const root = ensureMarkdownModal();
    const title = document.getElementById("md-viewer-title");
    const path = document.getElementById("md-viewer-path");
    const body = document.getElementById("md-viewer-body");
    const raw = document.getElementById("md-viewer-raw");

    root.hidden = false;
    document.body.classList.add("md-viewer-open");

    const filename = (repoRelative || "").split("/").pop() || "markdown";
    if (title) title.textContent = viewerMeta.displayTitle || filename;
    if (path) {
      path.textContent =
        viewerMeta.sourceLabel != null ? viewerMeta.sourceLabel : repoRelative || "";
    }
    if (raw) {
      raw.href = repoRelative ? repoHref(repoRelative) : "#";
      raw.hidden = viewerMeta.hideRaw || !repoRelative;
    }

    if (!body) return;

    const themeId = viewerMeta.theme || "command";
    applyMarkdownContentTheme(body, themeId);

    if (kind === "loading") {
      body.innerHTML = '<p class="md-viewer-status">' + escapeHtml(message) + "</p>";
      return;
    }

    if (kind === "error") {
      body.innerHTML =
        '<div class="callout callout-warn"><strong>Could not preview</strong><p>' +
        escapeHtml(message) +
        "</p></div>";
      return;
    }

    body.innerHTML = message;
    wireMarkdownBodyLinks(body, repoRelative);
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function slugifyForId(text) {
    return String(text || "generated")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48) || "generated";
  }

  function resolveMarkdownLink(href, baseRepoPath) {
    if (!href || /^[a-z]+:/i.test(href) || href.startsWith("#")) return href;
    const baseDir = baseRepoPath.includes("/")
      ? baseRepoPath.slice(0, baseRepoPath.lastIndexOf("/") + 1)
      : "";
    const parts = (baseDir + href).split("/");
    const stack = [];
    parts.forEach(function (part) {
      if (!part || part === ".") return;
      if (part === "..") stack.pop();
      else stack.push(part);
    });
    return stack.join("/");
  }

  function wireMarkdownBodyLinks(body, baseRepoPath) {
    body.querySelectorAll("a[data-md-link]").forEach(function (a) {
      const href = a.getAttribute("href");
      if (!href) return;
      const resolved = resolveMarkdownLink(href, baseRepoPath);
      if (isMarkdownRepoPath(resolved)) {
        a.setAttribute("data-repo", resolved);
        a.setAttribute("href", repoHref(resolved));
        a.classList.add("repo-md");
        a.setAttribute("title", "Click to preview markdown");
      } else if (!/^[a-z]+:/i.test(href) && !href.startsWith("#")) {
        a.setAttribute("href", repoHref(resolved));
        a.setAttribute("target", "_blank");
        a.setAttribute("rel", "noopener");
      }
    });
  }

  const RUNBOOK_REFERENCE_PLACEHOLDER_ACTIONS = {
    npc: ["Open NPC card", "Pin to session context"],
    location: ["Open location card", "Show nearby context"],
    statblock: ["Preview statblock", "Add to encounter"],
    "roll-table": ["Open roll table", "Roll on table"],
    citation: ["Open source note", "Copy citation"],
    combat: ["Launch combat", "Preview encounter seed"],
  };
  let runbookReferencePopoverBound = false;
  let activeRunbookReferenceTrigger = null;
  let suppressRunbookReferenceFocusOpen = false;

  function runbookReferenceHref(ref) {
    return "#dmb-" + ref.kind + ":" + ref.type + ":" + ref.id;
  }

  function runbookReferencePlaceholderActions(ref) {
    return RUNBOOK_REFERENCE_PLACEHOLDER_ACTIONS[ref.type] || ["Open reference", "Copy ref id"];
  }

  function readRunbookReferenceChip(trigger) {
    if (!trigger || !trigger.classList || !trigger.classList.contains("md-ref-chip")) return null;
    const kind = trigger.getAttribute("data-md-ref-kind");
    const type = trigger.getAttribute("data-md-ref-type");
    const id = trigger.getAttribute("data-md-ref-id");
    if ((kind !== "ref" && kind !== "action") || !type || !id) return null;
    const ref = {
      label: (trigger.textContent || "").trim(),
      kind: kind,
      type: type,
      id: id,
      isAction: kind === "action",
    };
    ref.href = runbookReferenceHref(ref);
    return ref;
  }

  function ensureRunbookReferencePopover() {
    let popover = document.getElementById("runbook-ref-popover");
    if (popover) return popover;

    popover = document.createElement("div");
    popover.id = "runbook-ref-popover";
    popover.className = "runbook-ref-popover";
    popover.setAttribute("role", "dialog");
    popover.setAttribute("aria-modal", "false");
    popover.setAttribute("aria-labelledby", "runbook-ref-popover-title");
    popover.hidden = true;
    popover.innerHTML =
      '<div class="runbook-ref-popover-card">' +
      '<header class="runbook-ref-popover-header"><div>' +
      '<p class="runbook-ref-popover-kicker">Reference shell</p>' +
      '<h2 id="runbook-ref-popover-title"></h2></div>' +
      '<button type="button" class="runbook-ref-popover-close" aria-label="Close reference details">&times;</button>' +
      '</header><dl class="runbook-ref-popover-meta"></dl>' +
      '<div class="runbook-ref-popover-status">Resolver pending. This shell does not fetch canon yet.</div>' +
      '<div class="runbook-ref-popover-actions"></div></div>';
    document.body.appendChild(popover);
    popover.querySelector(".runbook-ref-popover-close").addEventListener("click", function () {
      closeRunbookReferencePopover({ restoreFocus: true });
    });
    return popover;
  }

  function renderRunbookReferencePopoverContent(ref) {
    const popover = ensureRunbookReferencePopover();
    popover.querySelector("#runbook-ref-popover-title").textContent = ref.label;
    const meta = popover.querySelector(".runbook-ref-popover-meta");
    meta.textContent = "";
    [
      ["Kind", ref.kind, false],
      ["Type", ref.type, false],
      ["ID", ref.id, true],
      ["Href", ref.href, true],
    ].forEach(function (entry) {
      const row = document.createElement("div");
      const term = document.createElement("dt");
      const detail = document.createElement("dd");
      term.textContent = entry[0];
      detail.textContent = entry[1];
      if (entry[2]) detail.className = "mono";
      row.appendChild(term);
      row.appendChild(detail);
      meta.appendChild(row);
    });

    const actions = popover.querySelector(".runbook-ref-popover-actions");
    actions.textContent = "";
    runbookReferencePlaceholderActions(ref).forEach(function (label) {
      const button = document.createElement("button");
      button.type = "button";
      button.disabled = true;
      button.textContent = label;
      actions.appendChild(button);
    });
    return popover;
  }

  function positionRunbookReferencePopover(popover, trigger) {
    const gap = 8;
    const edge = 12;
    const triggerRect = trigger.getBoundingClientRect();
    const popoverRect = popover.getBoundingClientRect();
    const width = popoverRect.width || Math.min(360, window.innerWidth - edge * 2);
    const height = popoverRect.height;
    const left = Math.min(
      Math.max(edge, triggerRect.left),
      Math.max(edge, window.innerWidth - width - edge)
    );
    const fitsBelow = triggerRect.bottom + gap + height <= window.innerHeight - edge;
    const top = fitsBelow
      ? triggerRect.bottom + gap
      : Math.max(edge, triggerRect.top - height - gap);
    popover.style.left = Math.round(left) + "px";
    popover.style.top = Math.round(top) + "px";
  }

  function enhanceRunbookReferenceChip(trigger) {
    if (!readRunbookReferenceChip(trigger)) return false;
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-controls", "runbook-ref-popover");
    if (trigger !== activeRunbookReferenceTrigger) trigger.setAttribute("aria-expanded", "false");
    return true;
  }

  function enhanceRunbookReferenceChips(root) {
    if (!root || typeof root.querySelectorAll !== "function") return;
    root
      .querySelectorAll(".md-ref-chip[data-md-ref-kind][data-md-ref-type][data-md-ref-id]")
      .forEach(enhanceRunbookReferenceChip);
  }

  function openRunbookReferencePopover(trigger) {
    const ref = readRunbookReferenceChip(trigger);
    if (!ref) return;
    if (activeRunbookReferenceTrigger && activeRunbookReferenceTrigger !== trigger) {
      activeRunbookReferenceTrigger.setAttribute("aria-expanded", "false");
    }
    enhanceRunbookReferenceChip(trigger);
    activeRunbookReferenceTrigger = trigger;
    trigger.setAttribute("aria-expanded", "true");
    const popover = renderRunbookReferencePopoverContent(ref);
    popover.hidden = false;
    positionRunbookReferencePopover(popover, trigger);
  }

  function closeRunbookReferencePopover(options) {
    const trigger = activeRunbookReferenceTrigger;
    const popover = document.getElementById("runbook-ref-popover");
    if (popover) popover.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    activeRunbookReferenceTrigger = null;
    if (options && options.restoreFocus && trigger && typeof trigger.focus === "function") {
      suppressRunbookReferenceFocusOpen = true;
      trigger.focus();
      suppressRunbookReferenceFocusOpen = false;
    }
  }

  function initRunbookReferencePopoverShell() {
    ensureRunbookReferencePopover();
    enhanceRunbookReferenceChips(document);
    if (runbookReferencePopoverBound) return;
    runbookReferencePopoverBound = true;

    document.addEventListener("click", function (event) {
      const target = event.target instanceof Element ? event.target : null;
      const chip = target && target.closest(".md-ref-chip");
      if (chip) {
        openRunbookReferencePopover(chip);
      } else if (!target || !target.closest("#runbook-ref-popover")) {
        closeRunbookReferencePopover();
      }
    });
    document.addEventListener("focusin", function (event) {
      if (suppressRunbookReferenceFocusOpen) return;
      const target = event.target instanceof Element ? event.target : null;
      const chip = target && target.closest(".md-ref-chip");
      if (chip) openRunbookReferencePopover(chip);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && activeRunbookReferenceTrigger) {
        event.preventDefault();
        closeRunbookReferencePopover({ restoreFocus: true });
      }
    });
    window.addEventListener("resize", function () {
      const popover = document.getElementById("runbook-ref-popover");
      if (popover && !popover.hidden && activeRunbookReferenceTrigger) {
        positionRunbookReferencePopover(popover, activeRunbookReferenceTrigger);
      }
    });
    window.addEventListener(
      "scroll",
      function () {
        const popover = document.getElementById("runbook-ref-popover");
        if (popover && !popover.hidden && activeRunbookReferenceTrigger) {
          positionRunbookReferencePopover(popover, activeRunbookReferenceTrigger);
        }
      },
      true
    );
  }

  function renderMarkdownHtml(markdownText) {
    const markdown = String(markdownText || "");
    if (!window.MirewardMarkdown || typeof window.MirewardMarkdown.render !== "function") {
      return "<pre><code>" + escapeHtml(markdown) + "</code></pre>";
    }
    return window.MirewardMarkdown.render(markdown);
  }

  function openMarkdownFromText(displayTitle, sourceLabel, markdownText, options) {
    const markdown = String(markdownText || "");
    const viewerMeta = {
      displayTitle: displayTitle || "Statblock draft",
      sourceLabel: sourceLabel || "Generated draft",
      hideRaw: true,
      theme: (options && options.theme) || "command",
    };
    if (!markdown.trim()) {
      setMarkdownViewerState("error", "", "No markdown content to preview.", viewerMeta);
      return;
    }
    setMarkdownViewerState("ready", "", renderMarkdownHtml(markdown), viewerMeta);
  }

  function openGeneratedStatblockFromCombatEntity(entityId) {
    const state = normalizeCombatState(get(COMBAT_STORAGE_KEY, null));
    const entity = (state.entities || []).find(function (row) {
      return row.id === entityId;
    });
    if (!entity || !entity.generatedMarkdown) {
      openMarkdownFromText(
        (entity && entity.name) || "Generated combatant",
        "Generated draft · local combat tracker",
        "No stored markdown for this combatant.",
        { theme: "statblock" }
      );
      return;
    }
    openMarkdownFromText(
      entity.generatedTitle || entity.name,
      "Generated draft · local combat tracker",
      entity.generatedMarkdown,
      { theme: "statblock" }
    );
  }

  function apiPostJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var detail = data && data.detail;
          var message =
            typeof detail === "string"
              ? detail
              : detail && detail.message
                ? detail.message
                : detail && detail.error && detail.error.message
                  ? detail.error.message
                  : "HTTP " + res.status;
          throw new Error(message);
        }
        return data;
      });
    });
  }

  function apiGetJson(url) {
    return fetch(url).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var detail = data && data.detail;
          var message =
            typeof detail === "string"
              ? detail
              : detail && detail.message
                ? detail.message
                : "HTTP " + res.status;
          throw new Error(message);
        }
        return data;
      });
    });
  }

  let corpusWriteModalBound = false;

  function closeCorpusWriteModal() {
    const root = document.getElementById("corpus-write-viewer");
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("md-viewer-open");
  }

  function ensureCorpusWriteModal() {
    let root = document.getElementById("corpus-write-viewer");
    if (root) return root;

    root = document.createElement("div");
    root.id = "corpus-write-viewer";
    root.className = "md-viewer corpus-write-viewer";
    root.hidden = true;
    root.innerHTML =
      '<div class="md-viewer-backdrop" data-corpus-close="1"></div>' +
      '<div class="md-viewer-panel" role="dialog" aria-modal="true" aria-labelledby="corpus-write-title">' +
      '<header class="md-viewer-hd">' +
      '<div class="md-viewer-meta">' +
      '<div id="corpus-write-title" class="md-viewer-title"></div>' +
      '<div id="corpus-write-path" class="md-viewer-path mono"></div>' +
      "</div>" +
      '<div class="md-viewer-actions">' +
      '<button type="button" class="md-viewer-close" data-corpus-close="1" aria-label="Close corpus promotion">×</button>' +
      "</div>" +
      "</header>" +
      '<div id="corpus-write-body" class="md-viewer-body md-content"></div>' +
      '<pre id="corpus-write-diff" class="corpus-write-diff" hidden></pre>' +
      '<footer class="corpus-write-footer">' +
      '<span id="corpus-write-status" class="corpus-write-status muted"></span>' +
      '<div class="corpus-write-actions">' +
      '<button type="button" id="corpus-write-commit" class="primary" disabled>Confirm corpus write</button>' +
      "</div>" +
      "</footer>" +
      "</div>";
    document.body.appendChild(root);

    if (!corpusWriteModalBound) {
      corpusWriteModalBound = true;
      root.addEventListener("click", function (e) {
        if (e.target.closest("[data-corpus-close]")) closeCorpusWriteModal();
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && root && !root.hidden) closeCorpusWriteModal();
      });
    }

    return root;
  }

  function renderCorpusPreviewWarnings(preview) {
    if (!preview || !preview.warnings || !preview.warnings.length) return "";
    return (
      '<div class="callout callout-warn"><strong>Promotion warnings</strong>' +
      preview.warnings
        .map(function (warning) {
          return "<p>" + escapeHtml(warning.message || warning.code || "Warning") + "</p>";
        })
        .join("") +
      "</div>"
    );
  }

  function renderCorpusPromoteSuccessBanner(corpusPath, bytesWritten) {
    const pathText = corpusPath || "corpus file";
    const bytesText =
      bytesWritten !== null && bytesWritten !== undefined && bytesWritten !== ""
        ? '<p class="muted">' + escapeHtml(String(bytesWritten)) + " bytes written.</p>"
        : "";
    return (
      '<div class="callout callout-success statblock-corpus-success corpus-write-success-banner" role="status">' +
      "<strong>Promoted to corpus</strong>" +
      "<p>The statblock file was written successfully.</p>" +
      '<p class="mono">' +
      escapeHtml(pathText) +
      "</p>" +
      bytesText +
      '<p class="muted">Linked combat rows update when the combat tracker is open.</p>' +
      "</div>"
    );
  }

  function isArtifactCorpusPromoted(artifact) {
    if (!artifact || typeof artifact !== "object") return false;
    if (artifact.corpus_status === "promotion_confirmed") return true;
    return !!(artifact.corpus_display_path && artifact.corpus_status !== "not_promoted");
  }

  function artifactCorpusDisplayPath(artifact) {
    return (artifact && artifact.corpus_display_path) || "";
  }

  function renderDraftStatusPills(artifact) {
    const corpusStatus = (artifact && artifact.corpus_status) || "not_promoted";
    const storageStatus = (artifact && artifact.storage_status) || "not_stored";
    const provenance = (artifact && artifact.provenance) || {};
    const pills = [];
    if (corpusStatus === "promotion_confirmed") {
      pills.push('<span class="pill pill-success">In corpus</span>');
    } else if (storageStatus === "stored_draft") {
      pills.push('<span class="pill pill-neutral">Stored draft</span>');
    } else {
      pills.push('<span class="pill pill-neutral">Live draft</span>');
    }
    pills.push(
      '<span class="pill pill-neutral">' +
        escapeHtml((artifact && artifact.review_status) || "needs_dm_review") +
        "</span>"
    );
    if (provenance.generator) {
      pills.push(
        '<span class="pill pill-neutral">' + escapeHtml(String(provenance.generator)) + "</span>"
      );
    }
    return pills.join("");
  }

  function openCorpusWriteModal(preview, artifactId, onCommitted) {
    ensureCorpusWriteModal();
    const root = document.getElementById("corpus-write-viewer");
    const title = document.getElementById("corpus-write-title");
    const path = document.getElementById("corpus-write-path");
    const body = document.getElementById("corpus-write-body");
    const diff = document.getElementById("corpus-write-diff");
    const commitBtn = document.getElementById("corpus-write-commit");
    const statusEl = document.getElementById("corpus-write-status");
    let prepareState = null;

    if (title) title.textContent = preview.title || "Graduate to corpus";
    if (path) path.textContent = preview.proposed_corpus_display_path || "";
    if (body) {
      body.innerHTML =
        '<div class="callout callout-info"><strong>Corpus promotion preview</strong><p>Review the statblock below, then confirm to create the corpus file.</p></div>' +
        renderCorpusPreviewWarnings(preview) +
        (preview.validation && preview.validation.writer_allowed_now === false
          ? '<div class="callout callout-warn"><strong>Writer blocked</strong><p>' +
            escapeHtml(
              preview.validation.writer_reason ||
                "Corpus writer allowlist rejected this target path."
            ) +
            "</p></div>"
          : "") +
        renderMarkdownHtml(preview.full_markdown || preview.markdown_body || "");
    }
    if (diff) {
      diff.hidden = true;
      diff.textContent = "";
    }
    if (statusEl) {
      statusEl.className = "corpus-write-status muted";
      statusEl.textContent = "";
    }
    if (commitBtn) {
      commitBtn.disabled = !!(preview.validation && preview.validation.writer_allowed_now === false);
      commitBtn.textContent = "Confirm corpus write";
      commitBtn.onclick = function () {
        commitBtn.disabled = true;
        if (statusEl) {
          statusEl.className = "corpus-write-status muted";
          statusEl.textContent = "Preparing and writing to corpus…";
        }
        apiPostJson(
          "/api/live/statblocks/workbench/drafts/" +
            encodeURIComponent(artifactId) +
            "/corpus-write/prepare",
          { preview_token: preview.preview_token }
        )
          .then(function (prepare) {
            prepareState = prepare;
            if (!prepare.writer_ok) {
              const corpusPath =
                prepare.proposed_corpus_display_path ||
                preview.proposed_corpus_display_path ||
                "corpus file";
              const diagnostics = Array.isArray(prepare.diagnostics)
                ? prepare.diagnostics.join(" ")
                : "";
              const alreadyExists = /already exists/i.test(diagnostics);
              if (diff) {
                diff.hidden = true;
                diff.textContent = "";
              }
              if (statusEl) {
                statusEl.className = "corpus-write-status warn";
                statusEl.textContent = alreadyExists
                  ? "Already saved to corpus: " + corpusPath + ". No second write needed."
                  : "Corpus writer blocked. " + (diagnostics || "No corpus write was performed.");
              }
              if (body) {
                body.querySelectorAll(".corpus-write-success-banner").forEach(function (node) {
                  node.remove();
                });
                body.insertAdjacentHTML(
                  "afterbegin",
                  '<div class="callout callout-warn corpus-write-success-banner" role="status">' +
                    "<strong>" +
                    (alreadyExists ? "Already saved to corpus" : "Corpus writer blocked") +
                    "</strong>" +
                    '<p class="mono">' +
                    escapeHtml(corpusPath) +
                    "</p>" +
                    '<p class="muted">' +
                    escapeHtml(diagnostics || "No corpus write was performed.") +
                    "</p>" +
                    "</div>"
                );
                body.scrollTop = 0;
              }
              if (alreadyExists && onCommitted) {
                onCommitted(
                  {
                    artifact_id: artifactId,
                    proposed_corpus_display_path: corpusPath,
                    already_exists: true,
                  },
                  preview
                );
              }
              if (commitBtn) {
                commitBtn.disabled = false;
                commitBtn.textContent = alreadyExists ? "Done" : "Try again";
                if (alreadyExists) commitBtn.onclick = closeCorpusWriteModal;
              }
              return null;
            }
            return apiPostJson(
              "/api/live/statblocks/workbench/drafts/" +
                encodeURIComponent(artifactId) +
                "/corpus-write/commit",
              {
                preview_token: prepare.preview_token,
                writer_confirm_token: prepare.writer_confirm_token,
              }
            );
          })
          .then(function (commit) {
            if (!commit) return;
            const corpusPath =
              commit.proposed_corpus_display_path ||
              preview.proposed_corpus_display_path ||
              "corpus";
            const successBanner = renderCorpusPromoteSuccessBanner(
              corpusPath,
              commit.bytes_written
            );
            if (body) {
              body.querySelectorAll(".corpus-write-success-banner").forEach(function (node) {
                node.remove();
              });
              body.insertAdjacentHTML("afterbegin", successBanner);
              body.scrollTop = 0;
            }
            if (diff) diff.hidden = true;
            if (statusEl) {
              statusEl.className = "corpus-write-status saved";
              statusEl.textContent = "Write complete — close when ready.";
            }
            if (commitBtn) {
              commitBtn.disabled = false;
              commitBtn.textContent = "Done";
              commitBtn.onclick = function () {
                closeCorpusWriteModal();
                const toolboxOutput = document.getElementById("statblock-dogfood-output");
                if (toolboxOutput && toolboxOutput.scrollIntoView) {
                  toolboxOutput.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
              };
            }
            if (onCommitted) onCommitted(commit, preview);
          })
          .catch(function (err) {
            if (statusEl) {
              statusEl.className = "corpus-write-status warn";
              statusEl.textContent = (err && err.message) || "Corpus write failed.";
            }
            commitBtn.disabled = false;
          });
      };
    }

    if (root) {
      root.hidden = false;
      document.body.classList.add("md-viewer-open");
    }
  }

  function openMarkdownViewer(repoRelative) {
    setMarkdownViewerState("loading", repoRelative, "Loading…");

    if (isFileProtocol()) {
      setMarkdownViewerState(
        "error",
        repoRelative,
        "Markdown preview needs the local HTTP server (fetch is blocked on file://). " +
          "Run the live-control UI dev server and open http://localhost:5173/."
      );
      return;
    }

    const url = repoHref(repoRelative);
    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status + " for " + repoRelative);
        return res.text();
      })
      .then(function (text) {
        if (!window.MirewardMarkdown || typeof window.MirewardMarkdown.render !== "function") {
          throw new Error("Markdown renderer not loaded (prep-markdown.js).");
        }
        setMarkdownViewerState("ready", repoRelative, renderMarkdownHtml(text));
      })
      .catch(function (err) {
        setMarkdownViewerState(
          "error",
          repoRelative,
          (err && err.message) || "Failed to load markdown file."
        );
      });
  }

  function bindMarkdownLinkClicks() {
    if (markdownClickBound) return;
    markdownClickBound = true;

    document.addEventListener(
      "click",
      function (e) {
        const generatedLink = e.target.closest("a[data-generated-statblock]");
        if (generatedLink) {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
          e.preventDefault();
          openGeneratedStatblockFromCombatEntity(
            generatedLink.getAttribute("data-generated-statblock")
          );
          return;
        }

        const a = e.target.closest("a[data-repo]");
        if (!a) return;
        const rel = a.getAttribute("data-repo");
        if (!isMarkdownRepoPath(rel)) return;
        if (e.defaultPrevented) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;

        e.preventDefault();
        openMarkdownViewer(rel);
      },
      true
    );
  }

  function wireRepoLinks() {
    document.querySelectorAll("[data-repo]").forEach(function (a) {
      const rel = a.getAttribute("data-repo");
      if (rel) a.setAttribute("href", repoHref(rel));
      if (rel && isMarkdownRepoPath(rel)) {
        a.classList.add("repo-md");
        a.setAttribute("title", "Click to preview markdown");
      }
    });
    bindMarkdownLinkClicks();
  }

  function initRollTableToggle() {
    const btn = document.getElementById("toggle-t-dil-g");
    const panel = document.getElementById("t-dil-g-table");
    if (!btn || !panel) return;
    const open = get("rollExpanded.t-dil-g", false);
    panel.hidden = !open;
    btn.textContent = open ? "Collapse" : "Expand table";
    btn.addEventListener("click", function () {
      const next = panel.hidden;
      panel.hidden = !next;
      btn.textContent = next ? "Collapse" : "Expand table";
      set("rollExpanded.t-dil-g", next);
    });
  }

  function excerptMarkdown(text, startMarker, endMarker) {
    let out = text;
    if (startMarker) {
      const start = out.indexOf(startMarker);
      if (start >= 0) out = out.slice(start);
    }
    if (endMarker) {
      const end = out.indexOf(endMarker, startMarker ? startMarker.length : 0);
      if (end >= 0) out = out.slice(0, end);
    }
    return out;
  }

  function markdownEmbedThemeId(el) {
    if (!el || !el.getAttribute) return "command";
    return el.getAttribute("data-md-theme") || "command";
  }

  function setMarkdownEmbedContent(host, themeId, html) {
    if (!host) return null;
    host.innerHTML = '<div class="md-content"></div>';
    const content = host.querySelector(".md-content");
    applyMarkdownContentTheme(content, themeId || "command");
    content.innerHTML = html;
    return content;
  }

  function setMarkdownEmbedMessage(host, themeId, html) {
    setMarkdownEmbedContent(host, themeId, html);
  }

  function initMarkdownEmbeds() {
    document.querySelectorAll("[data-md-embed]").forEach(function (host) {
      const rel = host.getAttribute("data-md-embed");
      if (!rel) return;
      if (host.dataset.mdEmbedLoading === "true" || host.dataset.mdEmbedLoaded === "true") return;

      host.dataset.mdEmbedLoading = "true";
      const themeId = markdownEmbedThemeId(host);
      const rawLink = host.parentElement && host.parentElement.querySelector("[data-md-embed-link]");
      if (rawLink) {
        rawLink.setAttribute("data-repo", rel);
        rawLink.setAttribute("href", repoHref(rel));
      }

      if (isFileProtocol()) {
        setMarkdownEmbedMessage(
          host,
          themeId,
          '<div class="callout callout-warn"><strong>Cannot embed on file://</strong><p>Run the live-control UI dev server and open <code>http://localhost:5173/</code> so roll tables load inline.</p></div>'
        );
        host.dataset.mdEmbedLoading = "false";
        return;
      }

      setMarkdownEmbedMessage(host, themeId, '<p class="muted">Loading table…</p>');
      fetch(repoHref(rel))
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status + " for " + rel);
          return res.text();
        })
        .then(function (text) {
          if (!window.MirewardMarkdown || typeof window.MirewardMarkdown.render !== "function") {
            throw new Error("Markdown renderer not loaded (prep-markdown.js).");
          }
          const start = host.getAttribute("data-md-start") || "";
          const end = host.getAttribute("data-md-end") || "";
          const content = setMarkdownEmbedContent(
            host,
            themeId,
            window.MirewardMarkdown.render(excerptMarkdown(text, start, end))
          );
          wireMarkdownBodyLinks(content, rel);
          host.dataset.mdEmbedLoading = "false";
          host.dataset.mdEmbedLoaded = "true";
        })
        .catch(function (err) {
          host.dataset.mdEmbedLoading = "false";
          setMarkdownEmbedMessage(
            host,
            themeId,
            '<div class="callout callout-warn"><strong>Could not embed table</strong><p>' +
              escapeHtml((err && err.message) || "Failed to load markdown file.") +
              "</p></div>"
          );
        });
    });
  }

  function rollTableSectionTag(item) {
    if (item.section === "session_22") return ["S22", "pill-info"];
    if (item.section === "mireward_scaffold") return ["scaffold", "pill-warn"];
    if (item.section === "roads") return ["road", "pill-neutral"];
    if (item.section === "wilderness") return ["wilderness", "pill-neutral"];
    return ["table", "pill-neutral"];
  }

  function rollTableSummaryLabel(item) {
    var title = String(item.title || "").trim();
    if (!title) return "Roll table";
    var sessionMatch = title.match(/^Session\s+\d+\s+[—-]\s+(.+)$/i);
    if (sessionMatch) return sessionMatch[1];
    return title;
  }

  function renderRollTableIndexDetails(item) {
    var tag = rollTableSectionTag(item);
    var summaryText = rollTableSummaryLabel(item);
    var embedAttrs = "";
    if (item.embed_start) {
      embedAttrs += ' data-md-start="' + escapeHtml(item.embed_start) + '"';
    }
    if (item.embed_end) {
      embedAttrs += ' data-md-end="' + escapeHtml(item.embed_end) + '"';
    }

    var html =
      '<details class="fold rolltable-row">' +
      "<summary>" +
      escapeHtml(summaryText) +
      "</summary>" +
      '<div class="fold-bd">';

    html += '<div class="table-summary rolltable-row-meta">';
    html +=
      '<span class="pill ' +
      escapeHtml(tag[1]) +
      '">' +
      escapeHtml(tag[0]) +
      "</span>";
    if (item.table_id) {
      html += '<span class="pill pill-neutral">' + escapeHtml(item.table_id) + "</span>";
    }
    if (item.dice) {
      html += '<span class="pill pill-info">' + escapeHtml(item.dice) + "</span>";
    }
    html +=
      '<a data-repo="' +
      escapeHtml(item.corpus_display_path) +
      '" data-md-embed-link="1">source</a>';
    html += "</div>";

    if (item.table_note) {
      html += '<p class="muted rolltable-row-note">' + escapeHtml(item.table_note) + "</p>";
    }

    html +=
      '<div class="md-content md-embed" data-md-embed="' +
      escapeHtml(item.corpus_display_path) +
      '"' +
      embedAttrs +
      "></div>";
    html += "</div></details>";
    return html;
  }

  function renderRollTableIndexSection(title, items, options) {
    options = options || {};
    if (!items.length) return "";
    var openAttr = options.open ? " open" : "";
    var mutedClass = options.muted ? " fold-muted" : "";
    var html =
      '<details class="fold fold-section' +
      mutedClass +
      '"' +
      openAttr +
      ">" +
      "<summary>" +
      escapeHtml(title) +
      ' <span class="pill pill-neutral">' +
      items.length +
      "</span></summary>" +
      '<div class="fold-bd rolltable-index-list">';
    items.forEach(function (entry) {
      html += renderRollTableIndexDetails(entry);
    });
    html += "</div></details>";
    return html;
  }

  function initRollTableCorpusIndex(options) {
    options = options || {};
    var host = document.getElementById("rolltable-corpus-index");
    if (!host) return;

    if (isFileProtocol()) {
      host.innerHTML =
        '<div class="callout callout-warn"><strong>Cannot load roll-table index on file://</strong><p>Run the Vite dev server at <code>http://127.0.0.1:5173/roll-tables.html</code>.</p></div>';
      return;
    }

    if (!options.silent) {
      host.innerHTML = '<p class="muted">Loading corpus roll tables…</p>';
    }

    apiGetJson("/api/live/roll-tables/index")
      .then(function (body) {
        var items = Array.isArray(body.roll_tables) ? body.roll_tables : [];
        var session22 = items.filter(function (entry) {
          return entry.section === "session_22";
        });
        var scaffold = items.filter(function (entry) {
          return entry.section === "mireward_scaffold";
        });
        var roads = items.filter(function (entry) {
          return entry.section === "roads";
        });
        var wilderness = items.filter(function (entry) {
          return entry.section === "wilderness";
        });
        var html = "";

        html += renderRollTableIndexSection("Session 22 table tools", session22, { open: true });
        html += renderRollTableIndexSection("Mireward scaffold excerpts", scaffold, { open: true });
        html += renderRollTableIndexSection("Road and name tables", roads, { open: false });
        html += renderRollTableIndexSection("Wilderness tables", wilderness, { open: false });

        if (!items.length) {
          html += '<p class="muted">No roll tables indexed yet.</p>';
        }

        if (body.diagnostics && body.diagnostics.length) {
          html += '<details class="fold fold-section fold-muted"><summary>Index diagnostics</summary><div class="fold-bd"><ul class="rolltable-diagnostics">';
          body.diagnostics.forEach(function (diagnostic) {
            html += "<li>" + escapeHtml(diagnostic) + "</li>";
          });
          html += "</ul></div></details>";
        }

        host.innerHTML = html;
        wireRepoLinks();
        initMarkdownEmbeds();

        var countHost = document.getElementById("rolltable-index-count");
        if (countHost) {
          countHost.textContent = items.length + " indexed";
        }
      })
      .catch(function (err) {
        host.innerHTML =
          '<div class="callout callout-warn"><strong>Could not load roll-table index</strong><p>' +
          escapeHtml((err && err.message) || "Request failed.") +
          "</p></div>";
      });
  }

  function locationSummaryLabel(item) {
    var title = String(item.title || "").trim();
    if (!title) return "Location";
    title = title.replace(/\s*—\s*location hub(?:\s*\([^)]*\))?/i, "");
    title = title.replace(/\s*\(location hub[^)]*\)/i, "");
    title = title.replace(/\s*—\s*place build scaffold/i, "");
    return title.trim() || String(item.title || "Location");
  }

  function locationSectionTag(item) {
    if (item.section === "mireward") return ["Mireward", "pill-info"];
    if (item.section === "reach_travel") return ["reach", "pill-neutral"];
    if (item.section === "mossford_reference") return ["Mossford", "pill-warn"];
    if (item.section === "related_hubs") return ["related", "pill-neutral"];
    return ["place", "pill-neutral"];
  }

  function locationDocKindPill(item) {
    var kind = String(item.subject_doc_kind || "").trim();
    if (!kind) return "";
    var cls = kind === "hub_index" ? "pill-info" : kind === "location_dossier" ? "pill-success" : "pill-neutral";
    return '<span class="pill ' + cls + '">' + escapeHtml(kind.replace(/_/g, " ")) + "</span>";
  }

  function renderLocationIndexDetails(item) {
    var tag = locationSectionTag(item);
    var summaryText = locationSummaryLabel(item);
    var embedAttrs = "";
    if (item.embed_start) {
      embedAttrs += ' data-md-start="' + escapeHtml(item.embed_start) + '"';
    }
    if (item.embed_end) {
      embedAttrs += ' data-md-end="' + escapeHtml(item.embed_end) + '"';
    }

    var html =
      '<details class="fold location-row">' +
      "<summary>" +
      escapeHtml(summaryText) +
      "</summary>" +
      '<div class="fold-bd">';

    html += '<div class="table-summary location-row-meta">';
    html +=
      '<span class="pill ' +
      escapeHtml(tag[1]) +
      '">' +
      escapeHtml(tag[0]) +
      "</span>";
    html += locationDocKindPill(item);
    if (item.document_class) {
      html +=
        '<span class="pill pill-neutral">' + escapeHtml(item.document_class) + "</span>";
    }
    if (item.canon_layer) {
      html += '<span class="pill pill-neutral">' + escapeHtml(item.canon_layer) + "</span>";
    }
    html +=
      '<a data-repo="' +
      escapeHtml(item.corpus_display_path) +
      '" data-md-embed-link="1">source</a>';
    if (item.hub_path && item.hub_path !== item.corpus_display_path) {
      html += '<a data-repo="' + escapeHtml(item.hub_path) + '">hub</a>';
    }
    html += "</div>";

    if (item.table_note) {
      html += '<p class="muted location-row-note">' + escapeHtml(item.table_note) + "</p>";
    }

    html +=
      '<div class="md-content md-embed" data-md-embed="' +
      escapeHtml(item.corpus_display_path) +
      '"' +
      embedAttrs +
      "></div>";
    html += "</div></details>";
    return html;
  }

  function renderLocationIndexSection(title, items, options) {
    options = options || {};
    if (!items.length) return "";
    var openAttr = options.open ? " open" : "";
    var mutedClass = options.muted ? " fold-muted" : "";
    var html =
      '<details class="fold fold-section' +
      mutedClass +
      '"' +
      openAttr +
      ">" +
      "<summary>" +
      escapeHtml(title) +
      ' <span class="pill pill-neutral">' +
      items.length +
      "</span></summary>" +
      '<div class="fold-bd location-index-list">';
    items.forEach(function (entry) {
      html += renderLocationIndexDetails(entry);
    });
    html += "</div></details>";
    return html;
  }

  function initLocationCorpusIndex(options) {
    options = options || {};
    var host = document.getElementById("location-corpus-index");
    if (!host) return;

    if (isFileProtocol()) {
      host.innerHTML =
        '<div class="callout callout-warn"><strong>Cannot load location index on file://</strong><p>Run the Vite dev server at <code>http://127.0.0.1:5173/locations.html</code>.</p></div>';
      return;
    }

    if (!options.silent) {
      host.innerHTML = '<p class="muted">Loading corpus locations…</p>';
    }

    apiGetJson("/api/live/locations/index")
      .then(function (body) {
        var items = Array.isArray(body.locations) ? body.locations : [];
        var mireward = items.filter(function (entry) {
          return entry.section === "mireward";
        });
        var reach = items.filter(function (entry) {
          return entry.section === "reach_travel";
        });
        var mossford = items.filter(function (entry) {
          return entry.section === "mossford_reference";
        });
        var related = items.filter(function (entry) {
          return entry.section === "related_hubs";
        });
        var html = "";

        html += renderLocationIndexSection("Mireward hub & build", mireward, { open: true });
        html += renderLocationIndexSection("Reach & travel context", reach, { open: true });
        html += renderLocationIndexSection("Mossford reference shape", mossford, { open: false });
        html += renderLocationIndexSection("Related location hubs", related, { open: false });

        if (!items.length) {
          html += '<p class="muted">No location docs indexed yet.</p>';
        }

        if (body.diagnostics && body.diagnostics.length) {
          html += '<details class="fold fold-section fold-muted"><summary>Index diagnostics</summary><div class="fold-bd"><ul class="location-diagnostics">';
          body.diagnostics.forEach(function (diagnostic) {
            html += "<li>" + escapeHtml(diagnostic) + "</li>";
          });
          html += "</ul></div></details>";
        }

        host.innerHTML = html;
        wireRepoLinks();
        initMarkdownEmbeds();

        var countHost = document.getElementById("location-index-count");
        if (countHost) {
          countHost.textContent = items.length + " indexed";
        }
      })
      .catch(function (err) {
        host.innerHTML =
          '<div class="callout callout-warn"><strong>Could not load location index</strong><p>' +
          escapeHtml((err && err.message) || "Request failed.") +
          "</p></div>";
      });
  }

  function npcIndexSummaryLabel(item) {
    var title = String(item.title || "").trim();
    return title.split(" — ")[0] || title || item.slug || "NPC";
  }

  function npcSectionTag(item) {
    if (item.section === "campaign_2") return ["campaign", "pill-success"];
    if (item.section === "mireward_setting") return ["Mireward", "pill-warn"];
    return ["corpus", "pill-neutral"];
  }

  function renderNpcPathLink(path, label) {
    if (!path) return "";
    return (
      '<a data-repo="' +
      escapeHtml(path) +
      '">' +
      escapeHtml(label) +
      "</a>"
    );
  }

  function renderNpcIndexDetails(item) {
    var tag = npcSectionTag(item);
    var summaryText = npcIndexSummaryLabel(item);
    var primaryPath = item.primary_doc_path || item.hub_path;
    var seen = {};
    var links = [
      ["hub", item.hub_path],
      ["primary", item.primary_doc_path],
      ["seed", item.seed_path],
      ["dossier", item.dossier_path],
      ["timeline", item.timeline_path],
    ].filter(function (entry) {
      var path = entry[1];
      if (!path || seen[path]) return false;
      seen[path] = true;
      return true;
    });

    var html =
      '<details class="fold npc-row">' +
      "<summary>" +
      escapeHtml(summaryText) +
      ' <span class="pill ' +
      escapeHtml(tag[1]) +
      '">' +
      escapeHtml(tag[0]) +
      "</span>" +
      "</summary>" +
      '<div class="fold-bd">';

    if (item.table_note) {
      html += '<p class="muted npc-row-note">' + escapeHtml(item.table_note) + "</p>";
    }

    html += '<div class="table-summary npc-row-meta">';
    links.forEach(function (entry) {
      html += renderNpcPathLink(entry[1], entry[0]);
    });
    html += "</div>";

    if (primaryPath) {
      html +=
        '<div class="md-content md-embed" data-md-embed="' +
        escapeHtml(primaryPath) +
        '"></div>';
    }

    html += "</div></details>";
    return html;
  }

  function renderNpcIndexSection(title, items, options) {
    options = options || {};
    if (!items.length) return "";
    var openAttr = options.open ? " open" : "";
    var mutedClass = options.muted ? " fold-muted" : "";
    var html =
      '<details class="fold fold-section' +
      mutedClass +
      '"' +
      openAttr +
      ">" +
      "<summary>" +
      escapeHtml(title) +
      ' <span class="pill pill-neutral">' +
      items.length +
      "</span></summary>" +
      '<div class="fold-bd npc-index-list">';
    items.forEach(function (entry) {
      html += renderNpcIndexDetails(entry);
    });
    html += "</div></details>";
    return html;
  }

  function initNpcCorpusIndex(options) {
    options = options || {};
    var host = document.getElementById("npc-corpus-index");
    if (!host) return;

    if (isFileProtocol()) {
      host.innerHTML =
        '<div class="callout callout-warn"><strong>Cannot load NPC index on file://</strong><p>Run the Vite dev server at <code>http://127.0.0.1:5173/npcs.html</code>.</p></div>';
      return;
    }

    if (!options.silent) {
      host.innerHTML = '<p class="muted">Loading corpus NPCs…</p>';
    }

    apiGetJson("/api/live/npcs/index")
      .then(function (body) {
        var items = Array.isArray(body.npcs) ? body.npcs : [];
        var mireward = items.filter(function (entry) {
          return entry.section === "mireward_setting";
        });
        var campaign = items.filter(function (entry) {
          return entry.section === "campaign_2";
        });
        var html = "";

        html += renderNpcIndexSection("Mireward table faces", mireward, { open: true });
        html += renderNpcIndexSection("Campaign 2 recurring NPCs", campaign, { open: false });

        if (!mireward.length && !campaign.length) {
          html += '<p class="muted">No NPC hubs indexed yet.</p>';
        }

        if (body.diagnostics && body.diagnostics.length) {
          html += '<details class="fold fold-section fold-muted"><summary>Index diagnostics</summary><div class="fold-bd"><ul class="npc-diagnostics">';
          body.diagnostics.forEach(function (diagnostic) {
            html += "<li>" + escapeHtml(diagnostic) + "</li>";
          });
          html += "</ul></div></details>";
        }

        host.innerHTML = html;
        wireRepoLinks();
        initMarkdownEmbeds();

        var countHost = document.getElementById("npc-index-count");
        if (countHost) {
          countHost.textContent = items.length + " indexed";
        }
      })
      .catch(function (err) {
        host.innerHTML =
          '<div class="callout callout-warn"><strong>Could not load NPC index</strong><p>' +
          escapeHtml((err && err.message) || "Request failed.") +
          "</p></div>";
      });
  }

  function statblockIndexSummaryLabel(item) {
    var title = String(item.title || "").trim();
    var shortTitle = title.split(" — ")[0] || title;
    if (/\(CR\s/i.test(title) || /\bCR\s[\d/]/i.test(title)) {
      return shortTitle;
    }
    if (item.challenge_rating) {
      return shortTitle + " (CR " + item.challenge_rating + ")";
    }
    return shortTitle || "Statblock";
  }

  function renderStatblockIndexDetails(item) {
    var pillClass = item.role_pill_class || "pill-neutral";
    var roleTag = item.role_tag || "";
    var summaryText = statblockIndexSummaryLabel(item);
    return (
      '<details class="fold statblock-row">' +
      "<summary>" +
      escapeHtml(summaryText) +
      (roleTag
        ? ' <span class="pill ' + escapeHtml(pillClass) + '">' + escapeHtml(roleTag) + "</span>"
        : "") +
      "</summary>" +
      '<div class="fold-bd">' +
      '<div class="table-summary statblock-row-meta">' +
      '<a data-repo="' +
      escapeHtml(item.corpus_display_path) +
      '" data-md-embed-link="1">corpus file</a>' +
      "</div>" +
      '<div class="md-content md-embed" data-md-embed="' +
      escapeHtml(item.corpus_display_path) +
      '"></div>' +
      "</div></details>"
    );
  }

  function renderStatblockIndexSection(title, items, options) {
    options = options || {};
    if (!items.length) return "";
    var openAttr = options.open ? " open" : "";
    var mutedClass = options.muted ? " fold-muted" : "";
    var html =
      '<details class="fold fold-section' +
      mutedClass +
      '"' +
      openAttr +
      ">" +
      "<summary>" +
      escapeHtml(title) +
      ' <span class="pill pill-neutral">' +
      items.length +
      "</span></summary>" +
      '<div class="fold-bd statblock-index-list">';
    items.forEach(function (entry) {
      html += renderStatblockIndexDetails(entry);
    });
    html += "</div></details>";
    return html;
  }

  function initStatblockCorpusIndex(options) {
    options = options || {};
    var host = document.getElementById("statblock-corpus-index");
    if (!host) return;

    if (isFileProtocol()) {
      host.innerHTML =
        '<div class="callout callout-warn"><strong>Cannot load corpus index on file://</strong><p>Run the Vite dev server at <code>http://127.0.0.1:5173/statblocks.html</code>.</p></div>';
      return;
    }

    if (!options.silent) {
      host.innerHTML = '<p class="muted">Loading corpus statblocks…</p>';
    }

    apiGetJson("/api/live/statblocks/index")
      .then(function (body) {
        var items = Array.isArray(body.statblocks) ? body.statblocks : [];
        var generated = items.filter(function (entry) {
          return entry.section === "generated";
        });
        var flock = items.filter(function (entry) {
          return entry.section === "shepherds_flock";
        });
        var html = "";

        html += renderStatblockIndexSection("Generated from toolbox", generated, { open: true });
        html += renderStatblockIndexSection("Shepherd's Flock sheets", flock, { open: false });

        if (!generated.length && !flock.length) {
          html += '<p class="muted">No statblocks indexed yet.</p>';
        }

        if (body.diagnostics && body.diagnostics.length) {
          html += '<details class="fold fold-section fold-muted"><summary>Index diagnostics</summary><div class="fold-bd"><ul class="statblock-diagnostics">';
          body.diagnostics.forEach(function (diagnostic) {
            html += "<li>" + escapeHtml(diagnostic) + "</li>";
          });
          html += "</ul></div></details>";
        }

        host.innerHTML = html;
        wireRepoLinks();
        initMarkdownEmbeds();

        var countHost = document.getElementById("statblock-index-count");
        if (countHost) {
          countHost.textContent = items.length + " indexed";
        }

        document.dispatchEvent(
          new CustomEvent(STATBLOCK_CORPUS_INDEX_REFRESH_EVENT, {
            detail: { count: items.length },
          })
        );
      })
      .catch(function (err) {
        host.innerHTML =
          '<div class="callout callout-warn"><strong>Could not load statblock index</strong><p>' +
          escapeHtml((err && err.message) || "Request failed.") +
          "</p></div>";
      });
  }

  function refreshStatblockCorpusIndex() {
    initStatblockCorpusIndex({ silent: true });
  }

  function renderDogfoodArtifact(artifact, options) {
    options = options || {};
    const markdown = artifact && artifact.markdown ? String(artifact.markdown) : "";
    const combatDefaults = (artifact && artifact.combat_defaults) || {};
    const warnings = Array.isArray(artifact && artifact.warnings) ? artifact.warnings : [];
    const corpusStatus = (artifact && artifact.corpus_status) || "not_promoted";
    const corpusPath =
      options.corpusDisplayPath ||
      (artifact && artifact.corpus_display_path) ||
      "";
    const renderedMarkdown = renderMarkdownHtml(markdown);
    const actionList = Array.isArray(combatDefaults.primary_actions)
      ? combatDefaults.primary_actions.join(", ")
      : "";
    const warningHtml = warnings.length
      ? '<div class="callout callout-warn"><strong>Review warnings</strong>' +
        warnings
          .map(function (warning) {
            return "<p>" + escapeHtml(warning.message || warning.code || "Review warning") + "</p>";
          })
          .join("") +
        "</div>"
      : "";
    const promoteBanner =
      options.promoteSuccess
        ? renderCorpusPromoteSuccessBanner(
            options.promoteSuccess.path,
            options.promoteSuccess.bytesWritten
          )
        : corpusStatus === "promotion_confirmed" && corpusPath
          ? renderCorpusPromoteSuccessBanner(corpusPath, null)
          : "";
    return (
      promoteBanner +
      '<div class="statblock-dogfood-result">' +
      '<div class="table-summary">' +
      renderDraftStatusPills(artifact) +
      '<button type="button" class="statblock-dogfood-open-md">View full statblock</button>' +
      "</div>" +
      '<div class="grid-2 statblock-dogfood-grid">' +
      '<div class="md-content md-embed">' +
      renderedMarkdown +
      "</div>" +
      '<div class="card">' +
      '<div class="card-hd">Combat defaults</div>' +
      '<div class="card-bd">' +
      '<div class="file-row"><span class="label">Name</span><span>' +
      escapeHtml(combatDefaults.name || artifact.title || "Generated combatant") +
      "</span></div>" +
      '<div class="file-row"><span class="label">AC</span><span>' +
      escapeHtml(combatDefaults.armor_class ?? "") +
      "</span></div>" +
      '<div class="file-row"><span class="label">HP</span><span>' +
      escapeHtml(combatDefaults.hit_points ?? "") +
      "</span></div>" +
      '<div class="file-row"><span class="label">Initiative bonus</span><span>' +
      escapeHtml(combatDefaults.initiative_bonus ?? "") +
      "</span></div>" +
      '<div class="file-row"><span class="label">Actions</span><span>' +
      escapeHtml(actionList || "none listed") +
      "</span></div>" +
      "</div>" +
      "</div>" +
      "</div>" +
      warningHtml +
      "</div>"
    );
  }

  function generatedCombatEntityFromArtifact(artifact, state) {
    const defaults = (artifact && artifact.combat_defaults) || {};
    const name = String(defaults.name || artifact.title || "Generated combatant").trim();
    const baseId = "generated-" + slugifyForId(name);
    const existing = {};
    (state.entities || []).forEach(function (entity) {
      existing[entity.id] = true;
    });
    let id = baseId;
    let suffix = 2;
    while (existing[id]) {
      id = baseId + "-" + suffix;
      suffix += 1;
    }
    const hp =
      defaults.hit_points === null || defaults.hit_points === undefined
        ? ""
        : String(defaults.hit_points);
    const ac =
      defaults.armor_class === null || defaults.armor_class === undefined
        ? ""
        : String(defaults.armor_class);
    const actions = Array.isArray(defaults.primary_actions)
      ? defaults.primary_actions.join(", ")
      : "";
    const tactics = Array.isArray(defaults.suggested_tactics)
      ? defaults.suggested_tactics.join(" ")
      : "";
    const initBonus =
      defaults.initiative_bonus === null || defaults.initiative_bonus === undefined
        ? ""
        : "init +" + defaults.initiative_bonus + "; ";
    return {
      id: id,
      name: name,
      team: "enemy",
      order: state.entities.length,
      init: "",
      ac: ac,
      hp: hp,
      maxHp: hp,
      delta: "",
      notes: (initBonus + "generated draft; " + actions + (tactics ? "; " + tactics : "")).trim(),
      defeated: false,
      statblockPath: "",
      generatedArtifactId: artifact.artifact_id || artifact.draft_id || "",
      generatedTitle: artifact.title || name,
      generatedMarkdown: artifact.markdown || "",
    };
  }

  function linkGeneratedCombatEntitiesToCorpus(artifactId, corpusPath) {
    if (!artifactId || !corpusPath) return false;
    const state = normalizeCombatState(get(COMBAT_STORAGE_KEY, null));
    let changed = false;
    state.entities.forEach(function (entity) {
      if (entity.generatedArtifactId === artifactId) {
        entity.statblockPath = corpusPath;
        changed = true;
      }
    });
    if (changed) {
      saveCombatState(state);
      notifyCombatStateUpdated({ source: "corpus-promote" });
    }
    return changed;
  }

  function addGeneratedArtifactToCombat(artifact) {
    const state = normalizeCombatState(get(COMBAT_STORAGE_KEY, null));
    const entity = generatedCombatEntityFromArtifact(artifact, state);
    state.entities.push(entity);
    saveCombatState(state);
    notifyCombatStateUpdated({
      source: "toolbox",
      entityId: entity.id,
      entityName: entity.name,
    });
    return entity;
  }

  let toolboxInitialized = false;
  let statblockDogfoodInitialized = false;

  function formatGenerationCostSuffix(generationInfo) {
    if (!generationInfo || typeof generationInfo !== "object") return "";
    const parts = [];
    const preferredKeys = [
      "estimated_cost_usd",
      "scenario_estimated_cost_usd",
      "total_cost_usd",
      "generation_cost_usd",
    ];
    preferredKeys.forEach(function (key) {
      const value = generationInfo[key];
      if (value === null || value === undefined || value === "") return;
      const amount = Number(value);
      if (!Number.isFinite(amount)) return;
      parts.push(key.replace(/_/g, " ") + " $" + amount.toFixed(4));
    });
    if (!parts.length) {
      Object.keys(generationInfo).forEach(function (key) {
        if (!/cost/i.test(key)) return;
        const value = generationInfo[key];
        if (typeof value !== "number" || !Number.isFinite(value)) return;
        parts.push(key.replace(/_/g, " ") + " $" + value.toFixed(4));
      });
    }
    return parts.length ? " Cost: " + parts.join("; ") + "." : "";
  }

  function providerReadyStatus(mode) {
    if (mode === "http_command") {
      return "Live draft ready (DungeonMind API).";
    }
    return "Mock draft ready (mock provider).";
  }

  function formatGenerateSuccessStatus(body) {
    let message = providerReadyStatus(body && body.mode);
    const genInfo =
      body &&
      body.artifact &&
      body.artifact.provenance &&
      body.artifact.provenance.generation_info;
    message += formatGenerationCostSuffix(genInfo);
    message += " Use View full statblock to preview, then accept into combat if useful.";
    return message;
  }

  function formatGenerateErrorStatus(err, diagnostics) {
    const diagList = Array.isArray(diagnostics) ? diagnostics : [];
    let msg = (err && err.message) || "Generation failed.";
    if (err && err.remoteDetail) {
      const detailText =
        typeof err.remoteDetail === "string"
          ? err.remoteDetail
          : Array.isArray(err.remoteDetail)
            ? err.remoteDetail
                .map(function (item) {
                  if (!item || typeof item !== "object") return "";
                  const loc = Array.isArray(item.loc)
                    ? item.loc.filter(function (part) {
                        return part !== "body";
                      }).join(".")
                    : "";
                  return loc ? loc + ": " + (item.msg || "") : item.msg || "";
                })
                .filter(Boolean)
                .join("; ")
            : "";
      if (detailText) msg = msg + " — " + detailText;
    }
    const haystack = (msg + " " + diagList.join(" ")).toLowerCase();
    if (/api[_\s-]?key|openai|credential|unauthorized|missing key|provider config|not configured/.test(haystack)) {
      return (
        "Generation failed — check server API key / provider config (see server logs). " +
        (diagList.length ? diagList.slice(0, 2).join(" ") : msg)
      );
    }
    if (diagList.length) {
      return msg + " (" + diagList.slice(0, 2).join("; ") + ")";
    }
    return msg;
  }

  function statblockDogfoodPanelHtml() {
    return (
      '<section id="statblock-dogfood" class="prep-toolbox-panel statblock-dogfood" data-tool-panel="statblock">' +
      '<p class="muted">' +
      "Generate a draft through the local API, preview the full sheet, accept into the browser-local combat tracker, or promote to corpus." +
      "</p>" +
      '<div class="field">' +
      '<label for="statblock-dogfood-prompt">Generation prompt / table need</label>' +
      '<textarea id="statblock-dogfood-prompt" rows="6">Palisade Gnawer, CR 5 — Large monstrosity, AC 16, HP 140, burrow 30 ft.; a beaver-rat siege beast with a plated skull and stone-saw teeth. It makes a Bite and Skull-Ram Multiattack, deals double damage to wood and stone structures with Foundation Gnaw, and can use Splinter Spray after damaging a barricade to fire shrapnel in a cone; it is not clever, but it is brutally durable and ignores difficult terrain caused by rubble.</textarea>' +
      "</div>" +
      '<div class="statblock-dogfood-actions">' +
      '<button type="button" id="statblock-dogfood-generate" class="primary">Generate reinforcement</button>' +
      '<button type="button" id="statblock-dogfood-accept">Accept to combat tracker</button>' +
      '<button type="button" id="statblock-dogfood-promote" class="statblock-dogfood-promote" title="Two-phase corpus write to campaign Statblocks/generated/">Promote to corpus</button>' +
      "</div>" +
      '<div id="statblock-dogfood-toast" class="statblock-dogfood-toast" hidden role="status" aria-live="polite"></div>' +
      '<span id="statblock-dogfood-status" class="statblock-dogfood-status muted">Ready. Provider is chosen server-side; no corpus write until promoted.</span>' +
      '<div id="statblock-dogfood-output" class="statblock-dogfood-output"></div>' +
      "</section>"
    );
  }

  function ensureToolboxDrawer() {
    let root = document.getElementById("prep-toolbox");
    if (root) return root;

    root = document.createElement("div");
    root.id = "prep-toolbox";
    root.className = "prep-toolbox";
    root.innerHTML =
      '<button type="button" id="prep-toolbox-toggle" class="prep-toolbox-toggle" aria-expanded="false" aria-controls="prep-toolbox-drawer" title="Command toolbox">' +
      "Tools" +
      "</button>" +
      '<div id="prep-toolbox-backdrop" class="prep-toolbox-backdrop" hidden data-toolbox-close="1"></div>' +
      '<aside id="prep-toolbox-drawer" class="prep-toolbox-drawer" aria-label="Command toolbox">' +
      '<header class="prep-toolbox-hd">' +
      "<div>" +
      '<div class="prep-toolbox-eyebrow">Command Board</div>' +
      '<h2 class="prep-toolbox-title">Toolbox</h2>' +
      "</div>" +
      '<button type="button" class="prep-toolbox-close" data-toolbox-close="1" aria-label="Close toolbox">×</button>' +
      "</header>" +
      '<nav class="prep-toolbox-nav" aria-label="Toolbox tools">' +
      '<button type="button" class="prep-toolbox-nav-btn active" data-toolbox-tool="statblock">Statblock</button>' +
      "</nav>" +
      '<div class="prep-toolbox-body">' +
      statblockDogfoodPanelHtml() +
      "</div>" +
      "</aside>";
    document.body.appendChild(root);
    return root;
  }

  function setToolboxOpen(isOpen, toolId) {
    const root = document.getElementById("prep-toolbox");
    const toggle = document.getElementById("prep-toolbox-toggle");
    const drawer = document.getElementById("prep-toolbox-drawer");
    const backdrop = document.getElementById("prep-toolbox-backdrop");
    if (!root || !toggle || !drawer || !backdrop) return;

    if (toolId) setToolboxTool(toolId);

    root.classList.toggle("open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    backdrop.hidden = !isOpen;
    document.body.classList.toggle("prep-toolbox-open", isOpen);
    set("toolboxOpen", isOpen);
    if (toolId) set("toolboxTool", toolId);
  }

  function setToolboxTool(toolId) {
    document.querySelectorAll("[data-toolbox-tool]").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-toolbox-tool") === toolId);
    });
    document.querySelectorAll("[data-tool-panel]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-tool-panel") !== toolId;
    });
    set("toolboxTool", toolId);
  }

  function wireToolboxControls() {
    const root = document.getElementById("prep-toolbox");
    if (!root || root.dataset.wired === "1") return;
    root.dataset.wired = "1";

    const toggle = document.getElementById("prep-toolbox-toggle");
    const savedOpen = get("toolboxOpen", false);
    const savedTool = get("toolboxTool", "statblock");
    setToolboxTool(savedTool);
    if (savedOpen) setToolboxOpen(true);

    if (toggle) {
      toggle.addEventListener("click", function () {
        setToolboxOpen(!root.classList.contains("open"));
      });
    }

    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-toolbox-close]")) {
        setToolboxOpen(false);
        return;
      }
      const toolButton = e.target.closest("[data-toolbox-tool]");
      if (toolButton) {
        setToolboxTool(toolButton.getAttribute("data-toolbox-tool") || "statblock");
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !root.classList.contains("open")) return;
      if (document.body.classList.contains("md-viewer-open")) return;
      setToolboxOpen(false);
    });

    document.addEventListener("click", function (e) {
      const opener = e.target.closest("[data-open-toolbox]");
      if (!opener) return;
      e.preventDefault();
      setToolboxOpen(true, opener.getAttribute("data-open-toolbox") || "statblock");
    });
  }

  function initToolbox() {
    if (toolboxInitialized) return;
    toolboxInitialized = true;
    ensureToolboxDrawer();
    wireToolboxControls();
    initStatblockGeneratorDogfood();
  }

  function initStatblockGeneratorDogfood() {
    if (statblockDogfoodInitialized) return;
    const root = document.getElementById("statblock-dogfood");
    if (!root) return;
    statblockDogfoodInitialized = true;
    const prompt = document.getElementById("statblock-dogfood-prompt");
    const generateButton = document.getElementById("statblock-dogfood-generate");
    const acceptButton = document.getElementById("statblock-dogfood-accept");
    const promoteButton = document.getElementById("statblock-dogfood-promote");
    const status = document.getElementById("statblock-dogfood-status");
    const output = document.getElementById("statblock-dogfood-output");
    const toast = document.getElementById("statblock-dogfood-toast");
    let currentArtifact = get(STATBLOCK_DOGFOOD_DRAFT_KEY, null);
    let toastHideTimer = null;

    function setStatus(message, kind) {
      if (!status) return;
      status.textContent = message;
      status.className = "statblock-dogfood-status " + (kind || "muted");
    }

    function showStatblockToast(message, kind) {
      if (!toast) return;
      toast.hidden = false;
      toast.textContent = message;
      toast.className = "statblock-dogfood-toast " + (kind || "info");
      if (toastHideTimer) window.clearTimeout(toastHideTimer);
      toastHideTimer = window.setTimeout(function () {
        toast.hidden = true;
      }, 6000);
    }

    function syncPromoteButtonState(isBusy) {
      if (!promoteButton) return;
      const promoted = isArtifactCorpusPromoted(currentArtifact);
      const corpusPath = artifactCorpusDisplayPath(currentArtifact);
      promoteButton.disabled =
        !!isBusy || !currentArtifact || promoted;
      promoteButton.textContent = promoted ? "In corpus" : "Promote to corpus";
      promoteButton.classList.toggle("is-promoted", promoted);
      promoteButton.title = promoted
        ? "Already saved to corpus" + (corpusPath ? ": " + corpusPath : "")
        : "Two-phase corpus write to campaign Statblocks/generated/";
    }

    function setBusy(isBusy) {
      if (generateButton) generateButton.disabled = isBusy;
      if (acceptButton) {
        acceptButton.disabled = isBusy || !currentArtifact;
      }
      syncPromoteButtonState(isBusy);
    }

    function openCurrentArtifactPreview() {
      if (!currentArtifact) return;
      openMarkdownFromText(
        currentArtifact.title || "Statblock draft",
        "Command Board statblock generator",
        currentArtifact.markdown,
        { theme: "statblock" }
      );
    }

    function renderCurrentArtifact(options) {
      if (!output) return;
      if (!currentArtifact) {
        output.innerHTML =
          '<p class="muted">No generated draft yet. Generate a reinforcement to start dogfooding.</p>';
        setBusy(false);
        return;
      }
      output.innerHTML = renderDogfoodArtifact(currentArtifact, options || {});
      setBusy(false);
    }

    function showToolboxStatus(message, kind) {
      setStatus(message, kind);
      if (status && status.scrollIntoView) {
        status.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }

    function buildDogfoodCommandBody() {
      const promptText = prompt ? prompt.value : "";
      return {
        command_type: "statblock.draft.generate",
        requested_by: "human",
        as_artifact: true,
        payload: {
          request_id: "command-board-dogfood-" + Date.now(),
          mode: "generate_from_prompt",
          prompt: promptText,
          surface: "command_board_static",
          intent: {
            mode: "generate_from_prompt",
            summary: promptText,
            creature_name: "Palisade Gnawer",
            challenge_rating: "5",
            role: "siege beast",
            tone: "brutally durable structure-wrecker, not clever",
          },
          encounter_context: {
            party_level: 5,
            party_size: 4,
            environment: "Mireward north reach gate siege",
            encounter_role: "palisade / barricade pressure",
            constraints: [
              "command board dogfood",
              "do not persist until promoted",
            ],
          },
          output_options: {
            include_markdown: true,
            include_json: true,
            include_combat_defaults: true,
            include_review_warnings: true,
            persist: false,
          },
        },
      };
    }

    function runGenerateCommand() {
      if (isFileProtocol()) {
        setStatus("Generation needs the Vite dev server so /api can proxy to FastAPI.", "warn");
        return;
      }
      setBusy(true);
      setStatus("Generating reinforcement…", "muted");
      fetch("/api/live/statblocks/workbench/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildDogfoodCommandBody()),
      })
        .then(function (res) {
          return res.json().then(function (body) {
            if (!res.ok) {
              const detail = body && body.detail;
              const detailError =
                detail && typeof detail === "object" && detail.error ? detail.error : null;
              const message =
                typeof detail === "string"
                  ? detail
                  : detailError && (detailError.message || detailError.code)
                    ? detailError.message || detailError.code
                    : detail && detail.message
                      ? detail.message
                      : body && body.error && (body.error.message || body.error.code)
                        ? body.error.message || body.error.code
                        : "HTTP " + res.status;
              const err = new Error(message);
              err.diagnostics =
                (detail && typeof detail === "object" && detail.diagnostics) ||
                (body && body.diagnostics) ||
                [];
              if (detailError && detailError.details && detailError.details.remote_detail) {
                err.remoteDetail = detailError.details.remote_detail;
              }
              throw err;
            }
            return body;
          });
        })
        .then(function (body) {
          if (!body.artifact) {
            const err = new Error(
              (body.error && (body.error.message || body.error.code)) || "No artifact returned"
            );
            err.diagnostics = body.diagnostics || [];
            throw err;
          }
          currentArtifact = body.artifact;
          set(STATBLOCK_DOGFOOD_DRAFT_KEY, currentArtifact);
          renderCurrentArtifact();
          setStatus(formatGenerateSuccessStatus(body), "saved");
        })
        .catch(function (err) {
          setStatus(formatGenerateErrorStatus(err, err.diagnostics), "warn");
          setBusy(false);
        });
    }

    function promoteCurrentArtifactToCorpus() {
      if (!currentArtifact || isFileProtocol()) {
        if (isFileProtocol()) {
          setStatus("Corpus promotion needs the Vite dev server so /api can proxy to FastAPI.", "warn");
        }
        return;
      }
      if (isArtifactCorpusPromoted(currentArtifact)) {
        const corpusPath = artifactCorpusDisplayPath(currentArtifact);
        const message =
          "Already saved to corpus" + (corpusPath ? ": " + corpusPath : ".") + " No second write needed.";
        showStatblockToast(message, "saved");
        showToolboxStatus(message, "saved");
        return;
      }
      setBusy(true);
      setStatus("Storing draft and building corpus preview…", "muted");
      apiPostJson("/api/live/statblocks/workbench/drafts", {
        artifact: currentArtifact,
        source: "workbench",
      })
        .then(function (storeResponse) {
          const storedArtifact = storeResponse.record && storeResponse.record.artifact;
          if (storedArtifact) {
            currentArtifact = storedArtifact;
            set(STATBLOCK_DOGFOOD_DRAFT_KEY, currentArtifact);
            renderCurrentArtifact();
          }
          const artifactId =
            (storedArtifact && storedArtifact.artifact_id) || currentArtifact.artifact_id;
          return apiPostJson(
            "/api/live/statblocks/workbench/drafts/" +
              encodeURIComponent(artifactId) +
              "/corpus-preview",
            { include_writer_allowlist_check: true }
          ).then(function (preview) {
            return { preview: preview, artifactId: artifactId };
          });
        })
        .then(function (result) {
          setBusy(false);
          setStatus("Review corpus promotion, then confirm the write.", "saved");
          openCorpusWriteModal(result.preview, result.artifactId, function (commit, preview) {
            const corpusPath =
              commit.proposed_corpus_display_path ||
              preview.proposed_corpus_display_path ||
              "corpus file";
            currentArtifact =
              (commit.stored_record && commit.stored_record.artifact) || currentArtifact;
            if (commit.stored_record) {
              if (commit.stored_record.corpus_display_path) {
                currentArtifact.corpus_display_path = commit.stored_record.corpus_display_path;
              }
              currentArtifact.corpus_status = "promotion_confirmed";
              currentArtifact.lifecycle_state =
                (commit.stored_record.artifact && commit.stored_record.artifact.lifecycle_state) ||
                "corpus_promoted";
            } else {
              currentArtifact.corpus_display_path = corpusPath;
              currentArtifact.corpus_status = "promotion_confirmed";
            }
            set(STATBLOCK_DOGFOOD_DRAFT_KEY, currentArtifact);
            renderCurrentArtifact({
              promoteSuccess: {
                path: corpusPath,
                bytesWritten: commit.bytes_written,
              },
            });
            linkGeneratedCombatEntitiesToCorpus(commit.artifact_id, corpusPath);
            syncPromoteButtonState(false);
            const successMessage = commit.already_exists
              ? "Already saved to corpus: " + corpusPath + ". No second write needed."
              : "Promoted to corpus: " +
                corpusPath +
                (commit.bytes_written ? " (" + commit.bytes_written + " bytes)" : "") +
                ".";
            showStatblockToast(successMessage, "saved");
            showToolboxStatus(successMessage, "saved");
            refreshStatblockCorpusIndex();
          });
        })
        .catch(function (err) {
          setStatus((err && err.message) || "Corpus promotion failed.", "warn");
          setBusy(false);
        });
    }

    if (output) {
      output.addEventListener("click", function (e) {
        if (!e.target.closest(".statblock-dogfood-open-md")) return;
        openCurrentArtifactPreview();
      });
    }
    if (generateButton) {
      generateButton.addEventListener("click", function () {
        runGenerateCommand();
      });
    }
    if (acceptButton) {
      acceptButton.addEventListener("click", function () {
        if (!currentArtifact) return;
        const entity = addGeneratedArtifactToCombat(currentArtifact);
        const onCombatPage = !!document.getElementById("combat-rows");
        setStatus(
          onCombatPage
            ? "Added " + entity.name + " to the roster below. Set initiative when ready."
            : "Added " + entity.name + " to the local combat tracker. Open combat.html to place initiative.",
          "saved"
        );
        setBusy(false);
      });
    }
    if (promoteButton) {
      promoteButton.addEventListener("click", function () {
        promoteCurrentArtifactToCorpus();
      });
    }
    renderCurrentArtifact();
    if (isArtifactCorpusPromoted(currentArtifact)) {
      const corpusPath = artifactCorpusDisplayPath(currentArtifact);
      const alreadyMessage =
        "Already in corpus" + (corpusPath ? ": " + corpusPath : "") + ". Promote is disabled.";
      setStatus(alreadyMessage, "saved");
      showStatblockToast(alreadyMessage, "saved");
    }
    syncPromoteButtonState(false);
  }

  const COMBAT_TABLE_COLS = 7;
  const COMBAT_QUEUE_MODEL = "hybrid-barrel-v1";

  const PC_STATBLOCK_ROOT =
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/";
  const ENEMY_STATBLOCK_ROOT =
    "corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/";
  const LYSANDRA_STATBLOCK =
    "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md";

  function parseArmorClassFromMarkdown(text) {
    if (!text) return null;
    var tableMatch = text.match(/\|\s*Armor Class\s*\|\s*([^|\n]+)\|/i);
    if (tableMatch) {
      var tableAc = String(tableMatch[1]).trim().match(/\d+/);
      if (tableAc) return tableAc[0];
    }
    var proseMatch = text.match(/\*\*AC\*\*\s*(\d+)/i);
    if (proseMatch) return proseMatch[1];
    var lineMatch = text.match(/Armor Class\s*:?\s*(\d+)/i);
    if (lineMatch) return lineMatch[1];
    return null;
  }

  function defaultAcForBase(base) {
    if (base.defaultAc === null || base.defaultAc === undefined) return "";
    return String(base.defaultAc);
  }

  function hydrateAcFromStatblocks(state, done) {
    const paths = [];
    const seen = {};
    state.entities.forEach(function (entity) {
      const path = entity.statblockPath;
      if (!path || seen[path]) return;
      seen[path] = true;
      paths.push(path);
    });
    if (!paths.length || isFileProtocol()) {
      done(false);
      return;
    }
    Promise.all(
      paths.map(function (path) {
        return fetch(repoHref(path))
          .then(function (res) {
            return res.ok ? res.text() : "";
          })
          .catch(function () {
            return "";
          });
      })
    ).then(function (texts) {
      const acByPath = {};
      paths.forEach(function (path, index) {
        const ac = parseArmorClassFromMarkdown(texts[index]);
        if (ac) acByPath[path] = ac;
      });
      let changed = false;
      state.entities.forEach(function (entity) {
        const path = entity.statblockPath;
        if (!path || !acByPath[path]) return;
        if (entity.ac === "" || entity.ac === null || entity.ac === undefined) {
          entity.ac = acByPath[path];
          changed = true;
        }
      });
      done(changed);
    });
  }

  const COMBAT_DEFAULTS = [
    {
      id: "baergrom",
      name: "Baergrom",
      team: "pc",
      maxHp: null,
      defaultAc: 19,
      statblockPath: PC_STATBLOCK_ROOT + "baergrom/baergrom_statblock_dnd_beyond_level5.md",
    },
    {
      id: "bonogo",
      name: "Bonogo",
      team: "pc",
      maxHp: null,
      defaultAc: 16,
      statblockPath: PC_STATBLOCK_ROOT + "bonogo/bonogo_statblock_dnd_beyond_level5.md",
    },
    {
      id: "caelynn",
      name: "Caelynn",
      team: "pc",
      maxHp: null,
      defaultAc: 12,
      statblockPath: PC_STATBLOCK_ROOT + "caelynn/caelynn_statblock_dnd_beyond_level5.md",
    },
    {
      id: "ephanna",
      name: "Ephanna",
      team: "pc",
      maxHp: null,
      defaultAc: 14,
      statblockPath: PC_STATBLOCK_ROOT + "ephanna/ephanna_statblock_dnd_beyond_level5.md",
    },
    {
      id: "karsemine",
      name: "Karsemine",
      team: "pc",
      maxHp: null,
      defaultAc: 16,
      statblockPath: PC_STATBLOCK_ROOT + "karsemine/karsemine_statblock_dnd_beyond_level5.md",
    },
    {
      id: "stafl",
      name: "Stafl",
      team: "pc",
      maxHp: null,
      defaultAc: 13,
      statblockPath: PC_STATBLOCK_ROOT + "stafl/stafl_statblock_dnd_beyond_level5.md",
    },
    {
      id: "lysandra",
      name: "Lysandra",
      team: "ally",
      maxHp: null,
      defaultAc: 16,
      statblockPath: LYSANDRA_STATBLOCK,
    },
    { id: "thrinn", name: "Thrinn", team: "ally", maxHp: null },
    {
      id: "sewer-meat-a",
      name: "Sewer Meat Creature A",
      team: "enemy",
      maxHp: 37,
      defaultAc: 12,
      statblockPath: ENEMY_STATBLOCK_ROOT + "sewer_meat_creature_statblock_cr3.md",
    },
    {
      id: "sewer-meat-b",
      name: "Sewer Meat Creature B",
      team: "enemy",
      maxHp: 37,
      defaultAc: 12,
      statblockPath: ENEMY_STATBLOCK_ROOT + "sewer_meat_creature_statblock_cr3.md",
    },
    {
      id: "corrupted-meat-golem-a",
      name: "Corrupted Meat Golem A",
      team: "enemy",
      maxHp: 55,
      defaultAc: 12,
      statblockPath: ENEMY_STATBLOCK_ROOT + "corrupted_meat_golem_statblock_cr3.md",
    },
    {
      id: "tripod-null-calf-a",
      name: "Tripod Null-Calf A",
      team: "enemy",
      maxHp: 95,
      defaultAc: 15,
      statblockPath: ENEMY_STATBLOCK_ROOT + "tripod_null_calf_statblock_cr5.md",
    },
    {
      id: "tripod-null-calf-b",
      name: "Tripod Null-Calf B",
      team: "enemy",
      maxHp: 95,
      defaultAc: 15,
      statblockPath: ENEMY_STATBLOCK_ROOT + "tripod_null_calf_statblock_cr5.md",
    },
    {
      id: "fleshborn-hybrid-a",
      name: "Fleshborn Hybrid A",
      team: "enemy",
      maxHp: 45,
      defaultAc: 13,
      statblockPath: ENEMY_STATBLOCK_ROOT + "fleshborn_hybrid_statblock_cr3.md",
    },
    {
      id: "fleshborn-hybrid-b",
      name: "Fleshborn Hybrid B",
      team: "enemy",
      maxHp: 45,
      defaultAc: 13,
      statblockPath: ENEMY_STATBLOCK_ROOT + "fleshborn_hybrid_statblock_cr3.md",
    },
    {
      id: "aberrant-meatwing-a",
      name: "Aberrant Meatwing A",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-b",
      name: "Aberrant Meatwing B",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-c",
      name: "Aberrant Meatwing C",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-d",
      name: "Aberrant Meatwing D",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-e",
      name: "Aberrant Meatwing E",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-f",
      name: "Aberrant Meatwing F",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-g",
      name: "Aberrant Meatwing G",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-h",
      name: "Aberrant Meatwing H",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-i",
      name: "Aberrant Meatwing I",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
    {
      id: "aberrant-meatwing-j",
      name: "Aberrant Meatwing J",
      team: "enemy",
      maxHp: 18,
      defaultAc: 11,
      statblockPath: ENEMY_STATBLOCK_ROOT + "aberrant_meat_wing_statblock_cr1.md",
    },
  ];

  const LOCKED_COMBAT_ENTITY_IDS = Object.create(null);
  COMBAT_DEFAULTS.forEach(function (entity) {
    LOCKED_COMBAT_ENTITY_IDS[entity.id] = true;
  });

  const COMBAT_INIT_BAND_SIZE = 5;
  const COMBAT_INIT_MAX = 30;

  function initiativeBandMeta(initValue) {
    if (initValue === "" || initValue === null || initValue === undefined) {
      return {
        key: "unassigned",
        start: null,
        end: null,
        label: "No initiative set",
        sort: -1,
      };
    }
    const n = Number(initValue);
    if (!Number.isFinite(n)) {
      return {
        key: "unassigned",
        start: null,
        end: null,
        label: "No initiative set",
        sort: -1,
      };
    }
    const capped = Math.max(1, Math.min(n, COMBAT_INIT_MAX));
    const start = Math.floor((capped - 1) / COMBAT_INIT_BAND_SIZE) * COMBAT_INIT_BAND_SIZE + 1;
    const end = Math.min(start + COMBAT_INIT_BAND_SIZE - 1, COMBAT_INIT_MAX);
    return {
      key: start + "-" + end,
      start: start,
      end: end,
      label: "Initiative " + start + "–" + end,
      sort: start,
    };
  }

  function groupLivingByInitBands(livingItems) {
    const byKey = {};
    livingItems.forEach(function (item) {
      const band = initiativeBandMeta(item.entity.init);
      if (!byKey[band.key]) {
        byKey[band.key] = {
          key: band.key,
          start: band.start,
          end: band.end,
          label: band.label,
          sort: band.sort,
          items: [],
        };
      }
      byKey[band.key].items.push(item);
    });
    return Object.keys(byKey)
      .map(function (key) {
        return byKey[key];
      })
      .sort(function (a, b) {
        return b.sort - a.sort;
      })
      .map(function (band) {
        band.items.sort(function (a, b) {
          const ai = Number(a.entity.init);
          const bi = Number(b.entity.init);
          const av = Number.isFinite(ai) ? ai : -999;
          const bv = Number.isFinite(bi) ? bi : -999;
          if (bv !== av) return bv - av;
          return a.index - b.index;
        });
        return band;
      });
  }

  function teamLabel(team) {
    if (team === "pc") return '<span class="pill pill-success">PC</span>';
    if (team === "ally") return '<span class="pill pill-info">ally</span>';
    return '<span class="pill pill-warn">enemy</span>';
  }

  function clampNumber(value, min, max) {
    const n = Number(value);
    if (!Number.isFinite(n)) return null;
    if (typeof min === "number" && n < min) return min;
    if (typeof max === "number" && n > max) return max;
    return n;
  }

  function statblockGroupLabel(statblockPath) {
    const file = statblockPath.split("/").pop() || statblockPath;
    const stem = file.replace(/_statblock_[^.]*\.md$/i, "").replace(/\.md$/i, "");
    return stem
      .split("_")
      .filter(Boolean)
      .map(function (part) {
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(" ");
  }

  function segmentCollapseKey(memberIds) {
    return memberIds.slice().sort().join("|");
  }

  function combatEntityDefeated(entity) {
    const hp = Number(entity.hp);
    return !!entity.defeated || (Number.isFinite(hp) && hp <= 0);
  }

  function firstLivingIndexInList(entities) {
    const index = entities.findIndex(function (entity) {
      return !combatEntityDefeated(entity);
    });
    return index >= 0 ? index : 0;
  }

  function resolveRoundStartIndex(entities, saved) {
    if (typeof saved === "number" && saved >= 0 && saved < entities.length) {
      if (!combatEntityDefeated(entities[saved])) {
        return saved;
      }
    }
    return firstLivingIndexInList(entities);
  }

  function sortEntitiesByInitiative(entities) {
    entities.sort(function (a, b) {
      if (combatEntityDefeated(a) !== combatEntityDefeated(b)) {
        return combatEntityDefeated(a) ? 1 : -1;
      }
      const ai = Number(a.init);
      const bi = Number(b.init);
      const av = Number.isFinite(ai) ? ai : -999;
      const bv = Number.isFinite(bi) ? bi : -999;
      if (bv !== av) return bv - av;
      return a.order - b.order;
    });
  }

  function buildCombatSegmentsFromItems(items, isEntityDefeatedFn) {
    const segments = [];
    let i = 0;
    while (i < items.length) {
      const entity = items[i].entity;
      const path = entity.statblockPath || "";
      if (path) {
        let j = i + 1;
        while (j < items.length && items[j].entity.statblockPath === path) {
          j += 1;
        }
        if (j - i >= 2) {
          const members = items.slice(i, j);
          segments.push({
            type: "group",
            statblockPath: path,
            label: statblockGroupLabel(path),
            members: members,
            allDefeated: members.every(function (m) {
              return isEntityDefeatedFn(m.entity);
            }),
            collapseKey: segmentCollapseKey(
              members.map(function (m) {
                return m.entity.id;
              })
            ),
          });
          i = j;
          continue;
        }
      }
      segments.push({ type: "single", entity: entity, index: items[i].index });
      i += 1;
    }
    return segments;
  }

  function freshCombatState() {
    return {
      queueModel: COMBAT_QUEUE_MODEL,
      round: 1,
      turnIndex: 0,
      roundStartIndex: 0,
      groupCollapsed: {},
      deadBucketCollapsed: false,
      entities: COMBAT_DEFAULTS.map(function (entity, index) {
        const hp = entity.maxHp === null ? "" : entity.maxHp;
        return {
          id: entity.id,
          name: entity.name,
          team: entity.team,
          order: index,
          init: "",
          ac: defaultAcForBase(entity),
          hp: hp,
          maxHp: entity.maxHp === null ? "" : entity.maxHp,
          delta: "",
          notes: "",
          defeated: false,
          statblockPath: entity.statblockPath || "",
        };
      }),
    };
  }

  function normalizeCombatState(raw) {
    const state = raw && Array.isArray(raw.entities) ? raw : freshCombatState();
    const savedTurnIndex =
      clampNumber(state.turnIndex, 0, Math.max(state.entities.length - 1, 0)) || 0;
    const activeId =
      state.entities[savedTurnIndex] && state.entities[savedTurnIndex].id;
    const byId = {};
    state.entities.forEach(function (entity) {
      byId[entity.id] = entity;
    });
    const defaultIds = {};
    COMBAT_DEFAULTS.forEach(function (base) {
      defaultIds[base.id] = true;
    });
    const entities = COMBAT_DEFAULTS.map(function (base, index) {
      const current = byId[base.id] || {};
      const defaultHp = base.maxHp === null ? "" : base.maxHp;
      return {
        id: base.id,
        name: base.name,
        team: base.team,
        order: typeof current.order === "number" ? current.order : index,
        init: current.init ?? "",
        ac:
          current.ac !== undefined && current.ac !== null && current.ac !== ""
            ? current.ac
            : defaultAcForBase(base),
        hp: current.hp ?? defaultHp,
        maxHp: current.maxHp ?? defaultHp,
        delta: current.delta ?? "",
        notes: current.notes ?? "",
        defeated: !!current.defeated,
        statblockPath: base.statblockPath || current.statblockPath || "",
      };
    }).concat(
      state.entities
        .filter(function (entity) {
          return entity && entity.id && !defaultIds[entity.id];
        })
        .map(function (entity, index) {
          return {
            id: String(entity.id),
            name: String(entity.name || entity.id),
            team: entity.team === "pc" || entity.team === "ally" ? entity.team : "enemy",
            order:
              typeof entity.order === "number"
                ? entity.order
                : COMBAT_DEFAULTS.length + index,
            init: entity.init ?? "",
            ac: entity.ac ?? "",
            hp: entity.hp ?? "",
            maxHp: entity.maxHp ?? entity.hp ?? "",
            delta: entity.delta ?? "",
            notes: entity.notes ?? "",
            defeated: !!entity.defeated,
            statblockPath: entity.statblockPath ?? "",
            generatedArtifactId: entity.generatedArtifactId ?? "",
            generatedTitle: entity.generatedTitle ?? "",
            generatedMarkdown: entity.generatedMarkdown ?? "",
          };
        })
    ).sort(function (a, b) {
      return a.order - b.order;
    });
    const migratedQueue = state.queueModel !== COMBAT_QUEUE_MODEL;
    if (migratedQueue) {
      sortEntitiesByInitiative(entities);
    }
    const turnIndex =
      activeId
        ? entities.findIndex(function (entity) {
            return entity.id === activeId;
          })
        : savedTurnIndex;
    const normalizedTurnIndex =
      turnIndex >= 0 && turnIndex < entities.length ? turnIndex : firstLivingIndexInList(entities);
    const roundStartIndex = migratedQueue
      ? firstLivingIndexInList(entities)
      : resolveRoundStartIndex(entities, state.roundStartIndex);
    return {
      queueModel: COMBAT_QUEUE_MODEL,
      round: clampNumber(state.round, 1, null) || 1,
      turnIndex: normalizedTurnIndex,
      roundStartIndex: roundStartIndex,
      groupCollapsed:
        state.groupCollapsed && typeof state.groupCollapsed === "object"
          ? state.groupCollapsed
          : {},
      deadBucketCollapsed: !!state.deadBucketCollapsed,
      entities: entities,
    };
  }

  function saveCombatState(state) {
    state.entities.forEach(function (entity, index) {
      entity.order = index;
    });
    set(COMBAT_STORAGE_KEY, state);
  }

  function notifyCombatStateUpdated(detail) {
    document.dispatchEvent(
      new CustomEvent(COMBAT_STATE_UPDATED_EVENT, {
        detail: detail || {},
      })
    );
  }

  const COMBAT_STATE_SCHEMA = "mireward_combat_state_v1";
  const LEGACY_COMBAT_SAVE_BOOTSTRAP = "saves/mireward-north-reach-gate-combat-state.json";

  function padCombatSessionNumber(session) {
    const n = Number(session);
    if (!Number.isFinite(n) || n < 0) return "00";
    return String(Math.trunc(n)).padStart(2, "0");
  }

  function readCombatSaveProfile() {
    const root =
      document.getElementById("combat-tracker") ||
      document.querySelector("[data-combat-save-campaign]");
    if (!root) {
      return {
        campaign_id: "longmont-c2",
        session: 22,
        encounter_slug: "north_reach_gate",
      };
    }
    return {
      campaign_id: root.getAttribute("data-combat-save-campaign") || "longmont-c2",
      session: Number(root.getAttribute("data-combat-save-session") || "22"),
      encounter_slug: root.getAttribute("data-combat-save-encounter") || "north_reach_gate",
    };
  }

  function buildCombatSaveRelPath(profile) {
    const campaign = profile.campaign_id || "unknown-campaign";
    const session = padCombatSessionNumber(profile.session);
    const slug = profile.encounter_slug || "encounter";
    return (
      "saves/combat/" +
      campaign +
      "__session_" +
      session +
      "__" +
      slug +
      "__combat_state_v1.json"
    );
  }

  function buildCombatSaveExportFilename(profile) {
    const parts = buildCombatSaveRelPath(profile).split("/");
    return parts[parts.length - 1];
  }

  function combatSaveFetchUrl(relPathFromPrepRoot) {
    const path = String(relPathFromPrepRoot || "").replace(/^\/+/, "");
    if (isFileProtocol()) return path;
    const prefix = PREP_WEB_PREFIX.endsWith("/") ? PREP_WEB_PREFIX : PREP_WEB_PREFIX + "/";
    return prefix + path;
  }

  function buildCombatExportPayload(state, profile, source) {
    return {
      schema: COMBAT_STATE_SCHEMA,
      campaign_id: profile.campaign_id,
      session: profile.session,
      encounter_slug: profile.encounter_slug,
      exportedAt: new Date().toISOString(),
      source: source || "export",
      state: state,
    };
  }

  function fetchCombatSaveFile(relPath) {
    return fetch(combatSaveFetchUrl(relPath)).then(function (res) {
      if (!res.ok) throw new Error("save missing");
      return res.json();
    });
  }

  function bootstrapCombatState(done) {
    const cached = get(COMBAT_STORAGE_KEY, null);
    if (cached !== null) {
      const normalized = normalizeCombatState(cached);
      saveCombatState(normalized);
      done(normalized, "local", null);
      return;
    }
    if (isFileProtocol()) {
      done(normalizeCombatState(null), "fresh", null);
      return;
    }
    const profile = readCombatSaveProfile();
    const canonicalPath = buildCombatSaveRelPath(profile);
    fetchCombatSaveFile(canonicalPath)
      .catch(function () {
        return fetchCombatSaveFile(LEGACY_COMBAT_SAVE_BOOTSTRAP);
      })
      .then(function (payload) {
        const imported = normalizeCombatState(payload && payload.state ? payload.state : payload);
        saveCombatState(imported);
        done(imported, "file", canonicalPath);
      })
      .catch(function () {
        done(normalizeCombatState(null), "fresh", null);
      });
  }

  function initCombatTracker() {
    const tbody = document.getElementById("combat-rows");
    if (!tbody) return;

    const currentTurn = document.getElementById("combat-current-turn");
    const roundLabel = document.getElementById("combat-round");
    const floatingRound = document.getElementById("floating-round");
    const floatingTurn = document.getElementById("floating-turn");
    const floatingActive = document.getElementById("floating-active");
    const importFile = document.getElementById("combat-import-file");
    const saveStatus = document.getElementById("combat-save-status");
    let state = normalizeCombatState(null);
    let saveStatusTimer = null;

    function setSaveStatus(message) {
      if (!saveStatus) return;
      saveStatus.textContent = message;
      saveStatus.classList.add("saved");
      if (saveStatusTimer) window.clearTimeout(saveStatusTimer);
      saveStatusTimer = window.setTimeout(function () {
        saveStatus.classList.remove("saved");
        saveStatus.textContent = "Order and HP save locally in this browser.";
      }, 2200);
    }

    function isEntityDefeated(entity) {
      const hp = Number(entity.hp);
      return !!entity.defeated || (Number.isFinite(hp) && hp <= 0);
    }

    function isSegmentCollapsed(segment) {
      const hasActiveTurn = segment.members.some(function (member) {
        return member.index === state.turnIndex;
      });
      if (hasActiveTurn) return false;
      const key = segment.collapseKey;
      if (state.groupCollapsed && Object.prototype.hasOwnProperty.call(state.groupCollapsed, key)) {
        return !!state.groupCollapsed[key];
      }
      return segment.allDefeated;
    }

    function removeEntityAt(index) {
      const entity = state.entities[index];
      if (!entity || LOCKED_COMBAT_ENTITY_IDS[entity.id]) return;
      state.entities.splice(index, 1);
      if (state.turnIndex >= state.entities.length) {
        state.turnIndex = Math.max(0, state.entities.length - 1);
      } else if (index < state.turnIndex) {
        state.turnIndex -= 1;
      }
      if (state.roundStartIndex >= state.entities.length) {
        state.roundStartIndex = firstLivingIndex();
      } else if (index < state.roundStartIndex) {
        state.roundStartIndex = Math.max(0, state.roundStartIndex - 1);
      }
    }

    function renderEntityRow(entity, index, options) {
      const opts = options || {};
      const isTurn = index === state.turnIndex;
      const hpNum = Number(entity.hp);
      const maxNum = Number(entity.maxHp);
      const hpPct =
        Number.isFinite(hpNum) && Number.isFinite(maxNum) && maxNum > 0
          ? Math.max(0, Math.min(100, Math.round((hpNum / maxNum) * 100)))
          : "";
      const isDefeated = isEntityDefeated(entity);
      const nameHtml = entity.statblockPath
        ? '<a class="combat-statblock-link repo-md" data-repo="' +
          escapeHtml(entity.statblockPath) +
          '" href="' +
          repoHref(entity.statblockPath) +
          '" title="Click to preview statblock">' +
          escapeHtml(entity.name) +
          "</a>"
        : entity.generatedMarkdown
          ? '<a class="combat-statblock-link repo-md" href="#" data-generated-statblock="' +
            escapeHtml(entity.id) +
            '" title="Click to preview generated statblock">' +
            escapeHtml(entity.name) +
            "</a>"
          : escapeHtml(entity.name);
      return (
        '<tr class="' +
        (isTurn ? "active-turn" : "") +
            (isDefeated ? " defeated" : "") +
            (opts.groupMember ? " combat-group-member" : "") +
            (opts.inDeadZone ? " combat-dead-zone" : "") +
            '" data-combat-id="' +
        entity.id +
        '"' +
        (opts.groupKey ? ' data-group-key="' + escapeHtml(opts.groupKey) + '"' : "") +
        (opts.hidden ? " hidden" : "") +
        ">" +
        '<td class="combat-move">' +
        '<button type="button" data-row-action="up" aria-label="Move ' +
        escapeHtml(entity.name) +
        ' up">↑</button>' +
        '<button type="button" data-row-action="down" aria-label="Move ' +
        escapeHtml(entity.name) +
        ' down">↓</button>' +
        '<button type="button" data-row-action="turn" aria-label="Set turn to ' +
        escapeHtml(entity.name) +
        '">●</button>' +
        "</td>" +
        "<td>" +
        '<div class="combat-name' +
        (opts.groupMember ? " combat-group-member-name" : "") +
        '">' +
        nameHtml +
        "</div>" +
        '<div class="combat-team">' +
        teamLabel(entity.team) +
        (isTurn ? ' <span class="pill pill-neutral">turn</span>' : "") +
        "</div>" +
        "</td>" +
        '<td><input class="combat-input combat-init" type="text" inputmode="numeric" autocomplete="off" data-field="init" value="' +
        escapeHtml(entity.init) +
        '" /></td>' +
        '<td><input class="combat-input combat-ac" type="text" inputmode="numeric" autocomplete="off" data-field="ac" value="' +
        escapeHtml(entity.ac) +
        '" /></td>' +
        "<td>" +
        '<div class="combat-hp-row">' +
        '<input class="combat-input combat-hp" type="number" inputmode="numeric" data-field="hp" value="' +
        escapeHtml(entity.hp) +
        '" />' +
        '<span class="combat-hp-sep">/</span>' +
        '<input class="combat-input combat-hp" type="number" inputmode="numeric" data-field="maxHp" value="' +
        escapeHtml(entity.maxHp) +
        '" />' +
        "</div>" +
        '<div class="combat-hp-bar" aria-hidden="true"><span style="width:' +
        hpPct +
        '%"></span></div>' +
        "</td>" +
        "<td>" +
        '<div class="combat-delta-row">' +
        '<input class="combat-input combat-delta" type="number" inputmode="numeric" data-field="delta" value="' +
        escapeHtml(entity.delta) +
        '" placeholder="amt" />' +
        '<button type="button" data-row-action="damage">−</button>' +
        '<button type="button" data-row-action="heal">+</button>' +
        '<button type="button" class="dead-toggle" data-row-action="toggle-defeated">' +
        (entity.defeated ? "Revive" : "Dead") +
        "</button>" +
        (!LOCKED_COMBAT_ENTITY_IDS[entity.id]
          ? '<button type="button" class="combat-remove" data-row-action="remove" title="Remove from tracker">Remove</button>'
          : "") +
        "</div>" +
        "</td>" +
        '<td><input class="combat-input combat-notes" type="text" data-field="notes" value="' +
        escapeHtml(entity.notes) +
        '" placeholder="conditions, concentration, marks…" /></td>' +
        "</tr>"
      );
    }

    function partitionCombatItems() {
      const living = [];
      const dead = [];
      state.entities.forEach(function (entity, index) {
        const item = { entity: entity, index: index };
        if (isEntityDefeated(entity)) dead.push(item);
        else living.push(item);
      });
      return { living: living, dead: dead };
    }

    function renderSegmentsHtml(items, inDeadZone) {
      const segments = buildCombatSegmentsFromItems(items, isEntityDefeated);
      const bucketHidden = inDeadZone && isDeadBucketCollapsed();
      return segments
        .map(function (segment) {
          if (segment.type === "single") {
            return renderEntityRow(segment.entity, segment.index, {
              inDeadZone: inDeadZone,
              hidden: bucketHidden,
            });
          }
          const collapsed = bucketHidden || isSegmentCollapsed(segment);
          return (
            renderGroupHeader(segment, collapsed, inDeadZone) +
            segment.members
              .map(function (member) {
                return renderEntityRow(member.entity, member.index, {
                  groupMember: true,
                  groupKey: segment.collapseKey,
                  inDeadZone: inDeadZone,
                  hidden: collapsed,
                });
              })
              .join("")
          );
        })
        .join("");
    }

    function renderInitBandHeader(band, hasActiveTurn) {
      return (
        '<tr class="combat-init-band-row' +
        (hasActiveTurn ? " active-turn" : "") +
        '" data-init-band="' +
        escapeHtml(band.key) +
        '">' +
        '<td colspan="' + COMBAT_TABLE_COLS + '">' +
        '<div class="combat-init-band-head">' +
        '<span class="combat-init-band-title">' +
        escapeHtml(band.label) +
        "</span>" +
        '<span class="combat-init-band-meta">' +
        band.items.length +
        " unit" +
        (band.items.length === 1 ? "" : "s") +
        "</span>" +
        "</div>" +
        "</td>" +
        "</tr>"
      );
    }

    function renderRoundTopMarker() {
      return (
        '<tr class="combat-round-top-row" data-round-marker="top">' +
        '<td colspan="' +
        COMBAT_TABLE_COLS +
        '">' +
        '<div class="combat-round-marker-head">' +
        '<span class="combat-round-marker-title">Top of Round</span>' +
        '<span class="combat-round-marker-meta">Round ' +
        escapeHtml(String(state.round)) +
        " starts here</span>" +
        "</div>" +
        "</td>" +
        "</tr>"
      );
    }

    function renderRoundBottomMarker() {
      return (
        '<tr class="combat-round-bottom-row" data-round-marker="bottom">' +
        '<td colspan="' +
        COMBAT_TABLE_COLS +
        '">' +
        '<div class="combat-round-marker-head">' +
        '<span class="combat-round-marker-title">Bottom of Round</span>' +
        '<span class="combat-round-marker-meta">Last turn this round · next actor opens Round ' +
        escapeHtml(String((state.round || 1) + 1)) +
        "</span>" +
        "</div>" +
        "</td>" +
        "</tr>"
      );
    }

    function lastInRoundIndex() {
      return previousLivingIndex(state.roundStartIndex).index;
    }

    function livingItemsInTurnOrder(livingItems) {
      if (!livingItems.length) return [];
      const itemByIndex = {};
      livingItems.forEach(function (item) {
        itemByIndex[item.index] = item;
      });
      const ordered = [];
      const visited = {};
      let idx = state.turnIndex;
      if (!itemByIndex[idx] || isEntityDefeated(state.entities[idx])) {
        idx = firstLivingIndex();
      }
      for (let step = 0; step < livingItems.length; step += 1) {
        if (visited[idx]) break;
        if (itemByIndex[idx]) {
          ordered.push(itemByIndex[idx]);
          visited[idx] = true;
        }
        idx = nextLivingIndex(idx).index;
      }
      return ordered;
    }

    function buildLivingDisplayRows(orderedItems) {
      if (!orderedItems.length) return [];
      const roundStart = state.roundStartIndex;
      const roundEnd = lastInRoundIndex();
      const rows = [];
      orderedItems.forEach(function (item) {
        if (item.index === roundStart) {
          rows.push({ kind: "marker", marker: "top" });
        }
        rows.push({ kind: "entity", item: item });
        if (item.index === roundEnd) {
          rows.push({ kind: "marker", marker: "bottom" });
        }
      });
      return rows;
    }

    function renderCombatSegment(segment, inDeadZone, segmentOptions) {
      const segOpts = segmentOptions || {};
      const bucketHidden = inDeadZone && isDeadBucketCollapsed();
      if (segment.type === "single") {
        return renderEntityRow(segment.entity, segment.index, {
          inDeadZone: inDeadZone,
          hidden: bucketHidden,
        });
      }
      let collapsed = bucketHidden || isSegmentCollapsed(segment);
      if (segOpts.roundBoundaryAdjacent) collapsed = false;
      return (
        renderGroupHeader(segment, collapsed, inDeadZone, {
          roundBoundaryAdjacent: segOpts.roundBoundaryAdjacent,
        }) +
        segment.members
          .map(function (member) {
            return renderEntityRow(member.entity, member.index, {
              groupMember: true,
              groupKey: segment.collapseKey,
              inDeadZone: inDeadZone,
              hidden: collapsed,
            });
          })
          .join("")
      );
    }

    function renderEntityRunHtml(items, markerBefore, markerAfter) {
      if (!items.length) return "";
      const combatSegments = buildCombatSegmentsFromItems(items, isEntityDefeated);
      return combatSegments
        .map(function (segment, segIdx) {
          const isFirst = segIdx === 0;
          const isLast = segIdx === combatSegments.length - 1;
          return renderCombatSegment(segment, false, {
            roundBoundaryAdjacent: (markerBefore && isFirst) || (markerAfter && isLast),
          });
        })
        .join("");
    }

    function renderLivingDisplayRows(displayRows) {
      let html = "";
      let i = 0;
      while (i < displayRows.length) {
        const row = displayRows[i];
        if (row.kind === "marker") {
          html += row.marker === "top" ? renderRoundTopMarker() : renderRoundBottomMarker();
          i += 1;
          continue;
        }
        const entityRun = [];
        while (i < displayRows.length && displayRows[i].kind === "entity") {
          entityRun.push(displayRows[i].item);
          i += 1;
        }
        const markerBefore =
          i - entityRun.length - 1 >= 0 &&
          displayRows[i - entityRun.length - 1].kind === "marker";
        const markerAfter = i < displayRows.length && displayRows[i].kind === "marker";
        html += renderEntityRunHtml(entityRun, markerBefore, markerAfter);
      }
      return html;
    }

    function ensureRoundStartIndex() {
      if (
        state.roundStartIndex < 0 ||
        state.roundStartIndex >= state.entities.length ||
        isEntityDefeated(state.entities[state.roundStartIndex])
      ) {
        state.roundStartIndex = firstLivingIndex();
      }
    }

    function buildQueueNodesFromTurnIndex(livingItems) {
      ensureRoundStartIndex();
      const ordered = livingItemsInTurnOrder(livingItems);
      return buildLivingDisplayRows(ordered);
    }

    function renderLivingHtml(livingItems) {
      if (!livingItems.length) return "";
      const displayRows = buildQueueNodesFromTurnIndex(livingItems);
      return renderLivingDisplayRows(displayRows);
    }

    function isDeadBucketCollapsed() {
      return !!state.deadBucketCollapsed;
    }

    function renderDeadBucketHeader(deadCount) {
      const collapsed = isDeadBucketCollapsed();
      return (
        '<tr class="combat-dead-bucket-row' +
        (collapsed ? " is-collapsed" : "") +
        '">' +
        '<td colspan="' + COMBAT_TABLE_COLS + '">' +
        '<div class="combat-dead-bucket-head">' +
        '<button type="button" class="combat-dead-bucket-toggle" data-dead-bucket-action="toggle" aria-expanded="' +
        (!collapsed) +
        '" aria-label="' +
        (collapsed ? "Expand dead bucket" : "Collapse dead bucket") +
        '">' +
        (collapsed ? "▶" : "▼") +
        "</button>" +
        '<span class="combat-dead-bucket-title">Dead</span>' +
        '<span class="combat-dead-bucket-meta">' +
        deadCount +
        " unit" +
        (deadCount === 1 ? "" : "s") +
        " · skipped in turn rotation</span>" +
        "</div>" +
        "</td>" +
        "</tr>"
      );
    }

    function renderGroupHeader(segment, collapsed, inDeadZone, options) {
      const opts = options || {};
      const roundBoundaryAdjacent = !!opts.roundBoundaryAdjacent;
      if (roundBoundaryAdjacent) collapsed = false;
      const living = segment.members.filter(function (member) {
        return !isEntityDefeated(member.entity);
      }).length;
      const dead = segment.members.length - living;
      const hasActiveTurn = segment.members.some(function (member) {
        return member.index === state.turnIndex;
      });
      const activeMember = hasActiveTurn ? state.entities[state.turnIndex] : null;
      const statblockLink =
        '<a class="combat-statblock-link repo-md" data-repo="' +
        escapeHtml(segment.statblockPath) +
        '" href="' +
        repoHref(segment.statblockPath) +
        '" title="Click to preview statblock">' +
        escapeHtml(segment.label) +
        "</a>";
      return (
        '<tr class="combat-group-row' +
        (collapsed ? " is-collapsed" : "") +
        (segment.allDefeated ? " all-defeated" : "") +
        (hasActiveTurn ? " active-turn" : "") +
        (inDeadZone ? " combat-dead-zone" : "") +
        (roundBoundaryAdjacent ? " round-boundary-adjacent" : "") +
        '" data-group-key="' +
        escapeHtml(segment.collapseKey) +
        '">' +
        '<td colspan="' + COMBAT_TABLE_COLS + '">' +
        '<div class="combat-group-head">' +
        '<button type="button" class="combat-group-toggle" data-group-action="toggle" aria-expanded="' +
        (!collapsed) +
        '" aria-label="' +
        (collapsed ? "Expand" : "Collapse") +
        " " +
        escapeHtml(segment.label) +
        ' group">' +
        (collapsed ? "▶" : "▼") +
        "</button>" +
        '<div class="combat-group-title">' +
        statblockLink +
        '<span class="combat-group-meta">' +
        segment.members.length +
        " units · " +
        living +
        " up · " +
        dead +
        " down</span>" +
        (roundBoundaryAdjacent
          ? ' <span class="combat-group-round-boundary">round boundary</span>'
          : "") +
        (activeMember && collapsed
          ? ' <span class="pill pill-neutral">turn: ' + escapeHtml(activeMember.name) + "</span>"
          : "") +
        "</div>" +
        teamLabel("enemy") +
        "</div>" +
        "</td>" +
        "</tr>"
      );
    }

    function render(options) {
      if (!state.entities.length) {
        tbody.innerHTML = "";
        if (roundLabel) roundLabel.textContent = "Round 1";
        if (floatingRound) floatingRound.textContent = "Round 1";
        if (floatingTurn) floatingTurn.textContent = "Turn 0/0";
        if (floatingActive) floatingActive.textContent = "No active unit";
        if (currentTurn) currentTurn.textContent = "No combatants loaded.";
        return;
      }

      if (state.turnIndex >= state.entities.length) state.turnIndex = 0;
      if (state.turnIndex < 0) state.turnIndex = 0;
      if (!state.round || state.round < 1) state.round = 1;

      const parts = partitionCombatItems();
      let html = renderLivingHtml(parts.living);
      if (parts.dead.length) {
        html += renderDeadBucketHeader(parts.dead.length);
        html += renderSegmentsHtml(parts.dead, true);
      }
      tbody.innerHTML = html;

      if (currentTurn) {
        const active = state.entities[state.turnIndex];
        currentTurn.innerHTML = active
          ? teamLabel(active.team) + " " + escapeHtml(active.name)
          : "No active turn.";
      }
      if (roundLabel) {
        roundLabel.textContent = "Round " + state.round;
      }
      const active = state.entities[state.turnIndex];
      const livingEntities = state.entities.filter(function (entity) {
        return !isEntityDefeated(entity);
      });
      const livingTurnIndex = active
        ? livingEntities.findIndex(function (entity) {
            return entity.id === active.id;
          })
        : -1;
      if (floatingRound) floatingRound.textContent = "Round " + state.round;
      if (floatingTurn) {
        floatingTurn.textContent =
          "Turn " +
          (livingTurnIndex >= 0 ? livingTurnIndex + 1 : 0) +
          "/" +
          livingEntities.length;
      }
      if (floatingActive) {
        floatingActive.textContent = active ? active.name : "No active unit";
      }
      if (options && options.scrollActive) {
        const activeRow = tbody.querySelector("tr.active-turn[data-combat-id]");
        if (activeRow) {
          activeRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
      } else if (options && options.scrollToEntityId) {
        const targetRow = tbody.querySelector(
          'tr[data-combat-id="' + CSS.escape(options.scrollToEntityId) + '"]'
        );
        if (targetRow) {
          targetRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
      }
    }

    function entityForRow(target) {
      const row = target.closest("[data-combat-id]");
      if (!row) return null;
      const id = row.getAttribute("data-combat-id");
      const index = state.entities.findIndex(function (entity) {
        return entity.id === id;
      });
      if (index < 0) return null;
      return { entity: state.entities[index], index: index };
    }

    function segmentForGroupKey(groupKey) {
      const parts = partitionCombatItems();
      const segments = buildCombatSegmentsFromItems(parts.living, isEntityDefeated).concat(
        buildCombatSegmentsFromItems(parts.dead, isEntityDefeated)
      );
      return segments.find(function (segment) {
        return segment.type === "group" && segment.collapseKey === groupKey;
      });
    }

    function firstLivingIndex() {
      const index = state.entities.findIndex(function (entity) {
        return !isEntityDefeated(entity);
      });
      return index >= 0 ? index : 0;
    }

    function nextLivingIndex(fromIndex) {
      if (!state.entities.length) return { index: 0, wrapped: false };
      for (let step = 1; step <= state.entities.length; step += 1) {
        const index = (fromIndex + step) % state.entities.length;
        if (!isEntityDefeated(state.entities[index])) {
          return { index: index, wrapped: index <= fromIndex };
        }
      }
      return { index: fromIndex, wrapped: false };
    }

    function previousLivingIndex(fromIndex) {
      if (!state.entities.length) return { index: 0, wrapped: false };
      for (let step = 1; step <= state.entities.length; step += 1) {
        const index = (fromIndex - step + state.entities.length) % state.entities.length;
        if (!isEntityDefeated(state.entities[index])) {
          return { index: index, wrapped: index >= fromIndex };
        }
      }
      return { index: fromIndex, wrapped: false };
    }

    function moveDefeatedToBottom(index) {
      if (index < 0 || index >= state.entities.length) return;
      const activeId = state.entities[state.turnIndex] && state.entities[state.turnIndex].id;
      const [entity] = state.entities.splice(index, 1);
      state.entities.push(entity);

      if (entity.id === activeId) {
        state.turnIndex = firstLivingIndex();
        return;
      }

      const activeIndex = state.entities.findIndex(function (candidate) {
        return candidate.id === activeId;
      });
      state.turnIndex = activeIndex >= 0 ? activeIndex : 0;
    }

    function moveRevivedBeforeDeadBucket(index) {
      if (index < 0 || index >= state.entities.length) return;
      const activeId = state.entities[state.turnIndex] && state.entities[state.turnIndex].id;
      const [entity] = state.entities.splice(index, 1);
      if (isEntityDefeated(entity)) {
        state.entities.splice(index, 0, entity);
        return;
      }
      let insertAt = state.entities.findIndex(function (candidate) {
        return isEntityDefeated(candidate);
      });
      if (insertAt < 0) insertAt = state.entities.length;
      state.entities.splice(insertAt, 0, entity);

      if (entity.id === activeId) {
        state.turnIndex = insertAt;
        return;
      }
      const activeIndex = state.entities.findIndex(function (candidate) {
        return candidate.id === activeId;
      });
      state.turnIndex = activeIndex >= 0 ? activeIndex : 0;
    }

    function persistAndRender(options) {
      saveCombatState(state);
      render(options);
    }

    function exportCombatState() {
      saveCombatState(state);
      const profile = readCombatSaveProfile();
      const payload = buildCombatExportPayload(state, profile, "export");
      const filename = buildCombatSaveExportFilename(profile);
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setSaveStatus("Combat state exported as " + filename + ".");
    }

    function importCombatStateFromFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function () {
        try {
          const parsed = JSON.parse(String(reader.result || ""));
          const importedState = parsed && parsed.state ? parsed.state : parsed;
          state = normalizeCombatState(importedState);
          persistAndRender({ scrollActive: true });
          setSaveStatus("Combat state imported and saved locally.");
        } catch (err) {
          setSaveStatus("Import failed: invalid combat JSON.");
        } finally {
          if (importFile) importFile.value = "";
        }
      };
      reader.onerror = function () {
        setSaveStatus("Import failed: could not read file.");
        if (importFile) importFile.value = "";
      };
      reader.readAsText(file);
    }

    tbody.addEventListener("input", function (e) {
      const field = e.target.getAttribute("data-field");
      if (!field) return;
      const found = entityForRow(e.target);
      if (!found) return;
      found.entity[field] = e.target.value;
      if (field === "init") {
        persistAndRender();
        setSaveStatus("Initiative saved — band updated.");
      } else {
        saveCombatState(state);
        setSaveStatus("Saved locally.");
      }
    });

    tbody.addEventListener("click", function (e) {
      const deadBucketAction = e.target.getAttribute("data-dead-bucket-action");
      if (deadBucketAction === "toggle") {
        state.deadBucketCollapsed = !isDeadBucketCollapsed();
        persistAndRender();
        setSaveStatus(
          state.deadBucketCollapsed ? "Dead bucket collapsed." : "Dead bucket expanded."
        );
        return;
      }

      const groupAction = e.target.getAttribute("data-group-action");
      if (groupAction === "toggle") {
        const groupRow = e.target.closest("[data-group-key]");
        if (!groupRow) return;
        const groupKey = groupRow.getAttribute("data-group-key");
        const segment = segmentForGroupKey(groupKey);
        if (!segment) return;
        if (!state.groupCollapsed) state.groupCollapsed = {};
        state.groupCollapsed[groupKey] = !isSegmentCollapsed(segment);
        persistAndRender();
        setSaveStatus(
          state.groupCollapsed[groupKey]
            ? "Group collapsed and saved locally."
            : "Group expanded and saved locally."
        );
        return;
      }

      const action = e.target.getAttribute("data-row-action");
      if (!action) return;
      const found = entityForRow(e.target);
      if (!found) return;
      const { entity, index } = found;

      if (action === "up" && index > 0) {
        const previous = state.entities[index - 1];
        if (isEntityDefeated(entity) !== isEntityDefeated(previous)) return;
        state.entities[index - 1] = entity;
        state.entities[index] = previous;
        if (state.turnIndex === index) state.turnIndex = index - 1;
        else if (state.turnIndex === index - 1) state.turnIndex = index;
      } else if (action === "down" && index < state.entities.length - 1) {
        const next = state.entities[index + 1];
        if (isEntityDefeated(entity) !== isEntityDefeated(next)) return;
        state.entities[index + 1] = entity;
        state.entities[index] = next;
        if (state.turnIndex === index) state.turnIndex = index + 1;
        else if (state.turnIndex === index + 1) state.turnIndex = index;
      } else if (action === "turn") {
        state.turnIndex = index;
      } else if (action === "damage" || action === "heal") {
        const amount = Number(entity.delta);
        const hp = Number(entity.hp);
        if (Number.isFinite(amount) && Number.isFinite(hp)) {
          const nextHp = action === "damage" ? hp - amount : hp + amount;
          entity.hp = String(Math.max(0, nextHp));
          if (action === "damage" && nextHp <= 0) {
            entity.defeated = true;
            moveDefeatedToBottom(index);
          } else if (action === "heal" && nextHp > 0) {
            entity.defeated = false;
            moveRevivedBeforeDeadBucket(index);
          }
        }
      } else if (action === "toggle-defeated") {
        entity.defeated = !entity.defeated;
        if (entity.defeated) {
          entity.hp = "0";
          moveDefeatedToBottom(index);
        } else {
          moveRevivedBeforeDeadBucket(index);
        }
      } else if (action === "remove") {
        if (!window.confirm("Remove " + entity.name + " from this combat tracker?")) return;
        removeEntityAt(index);
      }

      persistAndRender(action === "turn" ? { scrollActive: true } : undefined);
      if (action === "up" || action === "down") {
        setSaveStatus("Manual order saved locally.");
      } else if (action === "damage" || action === "heal") {
        setSaveStatus("HP saved locally.");
      } else if (action === "toggle-defeated") {
        setSaveStatus(entity.defeated ? "Marked dead and moved to bottom." : "Marked alive locally.");
      } else if (action === "remove") {
        setSaveStatus("Removed from local combat tracker.");
      } else if (action === "turn") {
        setSaveStatus("Turn marker saved locally.");
      }
    });

    document.querySelectorAll("[data-combat-action]").forEach(function (button) {
      button.addEventListener("click", function () {
        const action = button.getAttribute("data-combat-action");
        if (action === "sort-init") {
          const activeId = state.entities[state.turnIndex] && state.entities[state.turnIndex].id;
          sortEntitiesByInitiative(state.entities);
          state.queueModel = COMBAT_QUEUE_MODEL;
          const nextTurn = state.entities.findIndex(function (entity) {
            return entity.id === activeId;
          });
          state.turnIndex =
            nextTurn >= 0 && !isEntityDefeated(state.entities[nextTurn])
              ? nextTurn
              : firstLivingIndex();
          state.roundStartIndex = firstLivingIndex();
          persistAndRender({ scrollActive: true });
          setSaveStatus("Initiative order sorted and saved locally.");
          return;
        } else if (action === "next-turn") {
          const next = nextLivingIndex(state.turnIndex);
          state.turnIndex = next.index;
          if (next.wrapped) {
            state.round = (state.round || 1) + 1;
            state.roundStartIndex = next.index;
          }
        } else if (action === "previous-turn") {
          const previous = previousLivingIndex(state.turnIndex);
          state.turnIndex = previous.index;
          if (previous.wrapped) {
            state.round = Math.max(1, (state.round || 1) - 1);
            state.roundStartIndex = previous.index;
          }
        } else if (action === "reset-turn") {
          ensureRoundStartIndex();
          state.turnIndex = state.roundStartIndex;
          if (isEntityDefeated(state.entities[state.turnIndex])) {
            state.turnIndex = firstLivingIndex();
          }
          state.round = 1;
        } else if (action === "export-state") {
          exportCombatState();
          return;
        } else if (action === "import-state") {
          if (importFile) importFile.click();
          return;
        } else if (action === "reset-all") {
          if (!window.confirm("Reset initiative, HP, dead/alive flags, notes, and turn state for this combat?")) return;
          state = freshCombatState();
        }
        const scrollTurn =
          action === "next-turn" || action === "previous-turn" || action === "reset-turn";
        persistAndRender(scrollTurn ? { scrollActive: true } : undefined);
        if (action === "next-turn" || action === "previous-turn") {
          setSaveStatus("Turn marker and round saved locally.");
        } else if (action === "reset-turn") {
          setSaveStatus("Turn marker and round reset locally.");
        } else if (action === "reset-all") {
          setSaveStatus("Combat state reset locally.");
        }
      });
    });

    if (importFile) {
      importFile.addEventListener("change", function () {
        importCombatStateFromFile(importFile.files && importFile.files[0]);
      });
    }

    document.addEventListener(COMBAT_STATE_UPDATED_EVENT, function (event) {
      const detail = (event && event.detail) || {};
      state = normalizeCombatState(get(COMBAT_STORAGE_KEY, null));
      hydrateAcFromStatblocks(state, function (changed) {
        if (changed) saveCombatState(state);
        render({
          scrollActive: false,
          scrollToEntityId: detail.entityId || null,
        });
        wireRepoLinks();
        if (detail.entityName) {
          setSaveStatus("Added " + detail.entityName + " from toolbox.");
        } else if (detail.source === "corpus-promote") {
          setSaveStatus("Combat roster refreshed after corpus promotion.");
        } else {
          setSaveStatus("Combat roster updated.");
        }
      });
    });

    bootstrapCombatState(function (loaded, source, savePath) {
      state = loaded;
      hydrateAcFromStatblocks(state, function (changed) {
        if (changed) saveCombatState(state);
        render({ scrollActive: false });
        wireRepoLinks();
        if (source === "file") {
          setSaveStatus(
            "Restored combat from " + (savePath || buildCombatSaveRelPath(readCombatSaveProfile())) + "."
          );
        } else if (source === "local") {
          setSaveStatus("Loaded saved combat state from this browser.");
        } else if (changed) {
          setSaveStatus("Armor Class loaded from statblocks.");
        }
      });
    });
  }

  window.MirewardPrep = {
    repoHref: repoHref,
    initNav: initNav,
    bindTextarea: bindTextarea,
    bindCheckbox: bindCheckbox,
    bindTimelineBeat: bindTimelineBeat,
    initScratchBand: initScratchBand,
    wireRepoLinks: wireRepoLinks,
    initRollTableToggle: initRollTableToggle,
    initMarkdownEmbeds: initMarkdownEmbeds,
    initRollTableCorpusIndex: initRollTableCorpusIndex,
    initLocationCorpusIndex: initLocationCorpusIndex,
    initNpcCorpusIndex: initNpcCorpusIndex,
    initStatblockCorpusIndex: initStatblockCorpusIndex,
    refreshStatblockCorpusIndex: refreshStatblockCorpusIndex,
    initToolbox: initToolbox,
    initStatblockGeneratorDogfood: initStatblockGeneratorDogfood,
    initCombatTracker: initCombatTracker,
    openMarkdownViewer: openMarkdownViewer,
    openMarkdownFromText: openMarkdownFromText,
    closeMarkdownViewer: closeMarkdownViewer,
    initRunbookReferencePopoverShell: initRunbookReferencePopoverShell,
    closeRunbookReferencePopover: closeRunbookReferencePopover,
    enhanceRunbookReferenceChips: enhanceRunbookReferenceChips,
    openToolbox: function (toolId) {
      initToolbox();
      setToolboxOpen(true, toolId || "statblock");
    },
  };

  function bootMirewardPrepChrome() {
    initToolbox();
    initRunbookReferencePopoverShell();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootMirewardPrepChrome);
  } else {
    bootMirewardPrepChrome();
  }
})();
