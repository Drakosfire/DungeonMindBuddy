/**
 * Mireward prep static HTML — shared nav, repo links, localStorage persistence.
 */
(function () {
  const STORAGE_PREFIX = "mireward-prep.";
  const REPO_UP = "../../../";
  const PREP_WEB_PREFIX = "/evals/c2_live_prep/mireward-prep/";

  const NAV = [
    { id: "index", label: "Command board", href: "index.html" },
    { id: "live-notes", label: "Live notes", href: "live-notes.html" },
    { id: "timeline", label: "Timeline", href: "timeline.html" },
    { id: "locations", label: "Locations", href: "locations.html" },
    { id: "npcs", label: "NPCs", href: "npcs.html" },
    { id: "roll-tables", label: "Roll tables", href: "roll-tables.html" },
    { id: "statblocks", label: "Statblocks", href: "statblocks.html" },
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

  function setMarkdownViewerState(kind, repoRelative, message) {
    const root = ensureMarkdownModal();
    const title = document.getElementById("md-viewer-title");
    const path = document.getElementById("md-viewer-path");
    const body = document.getElementById("md-viewer-body");
    const raw = document.getElementById("md-viewer-raw");

    root.hidden = false;
    document.body.classList.add("md-viewer-open");

    const filename = (repoRelative || "").split("/").pop() || "markdown";
    if (title) title.textContent = filename;
    if (path) path.textContent = repoRelative || "";
    if (raw) {
      raw.href = repoRelative ? repoHref(repoRelative) : "#";
      raw.hidden = !repoRelative;
    }

    if (!body) return;

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

  function openMarkdownViewer(repoRelative) {
    setMarkdownViewerState("loading", repoRelative, "Loading…");

    if (isFileProtocol()) {
      setMarkdownViewerState(
        "error",
        repoRelative,
        "Markdown preview needs the local HTTP server (fetch is blocked on file://). " +
          "Run: cd DungeonMindBuddy && python -m http.server 8765 — then use Open raw, or reload via localhost."
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
        setMarkdownViewerState("ready", repoRelative, window.MirewardMarkdown.render(text));
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

  function initMarkdownEmbeds() {
    document.querySelectorAll("[data-md-embed]").forEach(function (host) {
      const rel = host.getAttribute("data-md-embed");
      if (!rel) return;

      const rawLink = host.parentElement && host.parentElement.querySelector("[data-md-embed-link]");
      if (rawLink) {
        rawLink.setAttribute("data-repo", rel);
        rawLink.setAttribute("href", repoHref(rel));
      }

      if (isFileProtocol()) {
        host.innerHTML =
          '<div class="callout callout-warn"><strong>Cannot embed on file://</strong><p>Serve from repo root with <code>python -m http.server 8765</code> so the roll tables can load inline.</p></div>';
        return;
      }

      host.innerHTML = '<p class="muted">Loading table…</p>';
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
          host.innerHTML = window.MirewardMarkdown.render(excerptMarkdown(text, start, end));
          wireMarkdownBodyLinks(host, rel);
        })
        .catch(function (err) {
          host.innerHTML =
            '<div class="callout callout-warn"><strong>Could not embed table</strong><p>' +
            escapeHtml((err && err.message) || "Failed to load markdown file.") +
            "</p></div>";
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
    openMarkdownViewer: openMarkdownViewer,
    closeMarkdownViewer: closeMarkdownViewer,
  };
})();
