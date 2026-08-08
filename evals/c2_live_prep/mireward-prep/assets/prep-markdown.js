/**
 * Lightweight markdown → HTML for corpus preview (no external deps).
 */
(function (global) {
  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function stripFrontmatter(src) {
    if (!src.startsWith("---")) return src;
    const end = src.indexOf("\n---", 3);
    if (end === -1) return src;
    const after = src.indexOf("\n", end + 4);
    return after === -1 ? "" : src.slice(after + 1);
  }

  const DMB_REF_TYPES = new Set(["npc", "location", "statblock", "roll-table", "citation"]);
  const DMB_ACTION_TYPES = new Set(["combat"]);

  function parseDmbTypedHref(href) {
    const raw = String(href || "").trim();
    const refMatch = raw.match(/^#dmb-ref:([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_-]*)$/);
    if (refMatch) {
      const type = refMatch[1];
      if (!DMB_REF_TYPES.has(type)) return null;
      return { kind: "ref", type: type, id: refMatch[2] };
    }

    const actionMatch = raw.match(
      /^#dmb-action:([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_-]*)$/,
    );
    if (actionMatch) {
      const type = actionMatch[1];
      if (!DMB_ACTION_TYPES.has(type)) return null;
      return { kind: "action", type: type, id: actionMatch[2] };
    }

    return null;
  }

  function renderDmbRefChip(label, parsed) {
    const classes = ["md-ref-chip"];
    if (parsed.kind === "action") {
      classes.push("md-ref-chip-action", "md-ref-chip-action-" + parsed.type);
    } else {
      classes.push("md-ref-chip-" + parsed.type);
    }

    return (
      '<button type="button" class="' +
      classes.map(escapeHtml).join(" ") +
      '" data-md-ref-kind="' +
      escapeHtml(parsed.kind) +
      '" data-md-ref-type="' +
      escapeHtml(parsed.type) +
      '" data-md-ref-id="' +
      escapeHtml(parsed.id) +
      '">' +
      escapeHtml(label) +
      "</button>"
    );
  }

  function inlineMarkdown(text) {
    let s = escapeHtml(text);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_m, label, href) {
      const typedRef = parseDmbTypedHref(href);
      if (typedRef) return renderDmbRefChip(label, typedRef);
      return (
        '<a href="' +
        escapeHtml(href) +
        '" data-md-link="1">' +
        escapeHtml(label) +
        "</a>"
      );
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/_([^_]+)_/g, "<em>$1</em>");
    return s;
  }

  const CALLOUT_TYPES = {
    "read-aloud": { type: "read-aloud", label: "Read aloud" },
    readaloud: { type: "read-aloud", label: "Read aloud" },
    "read-aloud-text": { type: "read-aloud", label: "Read aloud" },
    "gm-note": { type: "gm-note", label: "GM note" },
    gm: { type: "gm-note", label: "GM note" },
    "dm-note": { type: "gm-note", label: "GM note" },
    dm: { type: "gm-note", label: "GM note" },
    rules: { type: "rules", label: "Rules" },
    rule: { type: "rules", label: "Rules" },
    "rules-note": { type: "rules", label: "Rules" },
    warning: { type: "warning", label: "Warning" },
    warn: { type: "warning", label: "Warning" },
    danger: { type: "warning", label: "Warning" },
  };

  function renderCallout(quoteLines) {
    if (!quoteLines.length) return "";
    const marker = quoteLines[0].match(/^\s*\[!([A-Za-z0-9_/-]+)\]\s*(.*)$/);
    if (!marker) return "";

    const markerKey = marker[1].toLowerCase().replace(/[\s_]+/g, "-");
    if (
      markerKey === "decision-consequence" ||
      markerKey === "decisionconsequence" ||
      markerKey === "decision/consequence" ||
      markerKey === "dc"
    ) {
      return renderDecisionConsequence(quoteLines.slice(1));
    }

    const callout = CALLOUT_TYPES[markerKey];
    if (!callout) return "";

    const customLabel = marker[2].trim();
    const label = customLabel || callout.label;
    const bodyLines = quoteLines.slice(1);
    const bodyHtml = renderMarkdown(bodyLines.join("\n"));

    return (
      '<aside class="md-callout md-callout-' +
      callout.type +
      '" data-md-callout="' +
      callout.type +
      '">' +
      '<div class="md-callout-label">' +
      inlineMarkdown(label) +
      "</div>" +
      '<div class="md-callout-body">' +
      bodyHtml +
      "</div>" +
      "</aside>"
    );
  }

  function splitDecisionConsequenceLines(bodyLines) {
    const decision = [];
    const consequence = [];
    let target = null;
    const heading = /^#{1,3}\s+(decision|consequence)\s*$/i;
    for (let i = 0; i < bodyLines.length; i++) {
      const line = bodyLines[i];
      const match = line.match(heading);
      if (match) {
        target = match[1].toLowerCase();
        continue;
      }
      if (target === "decision") {
        decision.push(line);
      } else if (target === "consequence") {
        consequence.push(line);
      } else if (line.trim()) {
        target = "decision";
        decision.push(line);
      }
    }
    return { decision: decision, consequence: consequence };
  }

  function renderDecisionConsequence(bodyLines) {
    const parts = splitDecisionConsequenceLines(bodyLines);
    const decisionHtml = renderMarkdown(parts.decision.join("\n")) || "<p></p>";
    const consequenceHtml = renderMarkdown(parts.consequence.join("\n")) || "<p></p>";
    return (
      '<aside class="md-decision-consequence" data-md-decision-consequence="true">' +
      '<div class="md-dc-pane md-dc-pane-decision" data-md-dc-pane="decision">' +
      '<div class="md-dc-pane-label">Decision</div>' +
      '<div class="md-dc-pane-body">' +
      decisionHtml +
      "</div></div>" +
      '<div class="md-dc-pane md-dc-pane-consequence" data-md-dc-pane="consequence">' +
      '<div class="md-dc-pane-label">Consequence</div>' +
      '<div class="md-dc-pane-body">' +
      consequenceHtml +
      "</div></div>" +
      "</aside>"
    );
  }

  function isTableRow(line) {
    return /^\s*\|/.test(line);
  }

  function isTableSep(line) {
    return /^\s*\|?[\s:-]+\|[\s|:-]*$/.test(line);
  }

  function parseTableRow(line) {
    const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
    return trimmed.split("|").map(function (cell) {
      return inlineMarkdown(cell.trim());
    });
  }

  function renderTable(lines) {
    if (lines.length < 2) return "";
    const header = parseTableRow(lines[0]);
    const bodyStart = isTableSep(lines[1]) ? 2 : 1;
    let html =
      "<table><thead><tr>" +
      header.map(function (c) {
        return "<th>" + c + "</th>";
      }).join("") +
      "</tr></thead><tbody>";
    for (let i = bodyStart; i < lines.length; i++) {
      const cells = parseTableRow(lines[i]);
      html +=
        "<tr>" +
        cells.map(function (c) {
          return "<td>" + c + "</td>";
        }).join("") +
        "</tr>";
    }
    return html + "</tbody></table>";
  }

  function renderMarkdown(src) {
    const body = stripFrontmatter(src);
    const lines = body.replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      if (/^```/.test(line)) {
        const fence = line.match(/^```(\w*)/);
        const lang = fence && fence[1] ? ' class="lang-' + fence[1] + '"' : "";
        i++;
        const code = [];
        while (i < lines.length && !/^```/.test(lines[i])) {
          code.push(lines[i]);
          i++;
        }
        if (i < lines.length) i++;
        out.push("<pre><code" + lang + ">" + escapeHtml(code.join("\n")) + "</code></pre>");
        continue;
      }

      if (/^#{1,6}\s/.test(line)) {
        const m = line.match(/^(#{1,6})\s+(.*)$/);
        const level = m[1].length;
        out.push("<h" + level + ">" + inlineMarkdown(m[2]) + "</h" + level + ">");
        i++;
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line.trim())) {
        out.push("<hr />");
        i++;
        continue;
      }

      if (isTableRow(line)) {
        const tableLines = [];
        while (i < lines.length && isTableRow(lines[i])) {
          tableLines.push(lines[i]);
          i++;
        }
        out.push(renderTable(tableLines));
        continue;
      }

      if (/^>\s?/.test(line)) {
        const quote = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) {
          quote.push(lines[i].replace(/^>\s?/, ""));
          i++;
        }
        out.push(renderCallout(quote) || "<blockquote><p>" + inlineMarkdown(quote.join(" ")) + "</p></blockquote>");
        continue;
      }

      if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
        const ordered = /^\s*\d+\.\s+/.test(line);
        const tag = ordered ? "ol" : "ul";
        const items = [];
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          const item = lines[i].replace(/^\s*([-*]|\d+\.)\s+/, "");
          items.push("<li>" + inlineMarkdown(item) + "</li>");
          i++;
        }
        out.push("<" + tag + ">" + items.join("") + "</" + tag + ">");
        continue;
      }

      if (!line.trim()) {
        i++;
        continue;
      }

      const para = [];
      while (i < lines.length && lines[i].trim() && !/^#{1,6}\s/.test(lines[i]) && !/^```/.test(lines[i]) && !isTableRow(lines[i]) && !/^>\s?/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s+/.test(lines[i]) && !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i].trim())) {
        para.push(lines[i]);
        i++;
      }
      out.push("<p>" + inlineMarkdown(para.join(" ")) + "</p>");
    }

    return out.join("\n");
  }

  global.MirewardMarkdown = { render: renderMarkdown };
})(window);
