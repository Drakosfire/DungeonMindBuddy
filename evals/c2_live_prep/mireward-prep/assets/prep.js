/**
 * Mireward prep static HTML — shared nav, repo links, localStorage persistence.
 */
(function () {
  const STORAGE_PREFIX = "mireward-prep.";
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
          '<div class="callout callout-warn"><strong>Cannot embed on file://</strong><p>Run the live-control UI dev server and open <code>http://localhost:5173/</code> so roll tables load inline.</p></div>';
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
    }).sort(function (a, b) {
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
    set("combat.northReachGate", state);
  }

  const COMBAT_SAVE_BOOTSTRAP = "saves/mireward-north-reach-gate-combat-state.json";

  function bootstrapCombatState(done) {
    const cached = get("combat.northReachGate", null);
    if (cached !== null) {
      const normalized = normalizeCombatState(cached);
      saveCombatState(normalized);
      done(normalized, "local");
      return;
    }
    if (isFileProtocol()) {
      done(normalizeCombatState(null), "fresh");
      return;
    }
    fetch(COMBAT_SAVE_BOOTSTRAP)
      .then(function (res) {
        if (!res.ok) throw new Error("save missing");
        return res.json();
      })
      .then(function (payload) {
        const imported = normalizeCombatState(payload && payload.state ? payload.state : payload);
        saveCombatState(imported);
        done(imported, "file");
      })
      .catch(function () {
        done(normalizeCombatState(null), "fresh");
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
      const payload = {
        schema: "mireward_north_reach_gate_combat_state_v1",
        exportedAt: new Date().toISOString(),
        state: state,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mireward-north-reach-gate-combat-state.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setSaveStatus("Combat state exported as JSON.");
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
      }

      persistAndRender(action === "turn" ? { scrollActive: true } : undefined);
      if (action === "up" || action === "down") {
        setSaveStatus("Manual order saved locally.");
      } else if (action === "damage" || action === "heal") {
        setSaveStatus("HP saved locally.");
      } else if (action === "toggle-defeated") {
        setSaveStatus(entity.defeated ? "Marked dead and moved to bottom." : "Marked alive locally.");
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

    bootstrapCombatState(function (loaded, source) {
      state = loaded;
      hydrateAcFromStatblocks(state, function (changed) {
        if (changed) saveCombatState(state);
        render({ scrollActive: false });
        wireRepoLinks();
        if (source === "file") {
          setSaveStatus("Restored combat from saves/mireward-north-reach-gate-combat-state.json.");
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
    initCombatTracker: initCombatTracker,
    openMarkdownViewer: openMarkdownViewer,
    closeMarkdownViewer: closeMarkdownViewer,
  };
})();
