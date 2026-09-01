/* Of Conks & Cons end-to-end dogfood — boutique packet behavior.
   Station 6 (roll tables) and Station 7 (prepared encounters).
   Data fixtures load from ./local/*.json (gitignored; module-derived bytes
   stay local-only per the dogfood legal boundary). Roll results are
   ephemeral in-memory state — nothing persists (handoff Station 6 rule). */

(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function rollDie(sides) {
    var buf = new Uint32Array(1);
    var limit = Math.floor(0x100000000 / sides) * sides;
    var value;
    do {
      crypto.getRandomValues(buf);
      value = buf[0];
    } while (value >= limit);
    return (value % sides) + 1;
  }

  function fetchFixture(name) {
    return fetch("local/" + name, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    });
  }

  function renderFixtureMissing(host, name) {
    var box = el("div", "oc-error");
    box.appendChild(el("strong", null, "Local fixture missing: packet/local/" + name));
    box.appendChild(
      el(
        "p",
        null,
        "Module-derived table/encounter bytes are local-only under the dogfood legal boundary. " +
          "Populate the fixture from the licensed gold package (see REPORT-of-conks-end-to-end-dogfood.md §0.2)."
      )
    );
    host.appendChild(box);
  }

  /* ---------------- Station 6 — roll tables ---------------- */

  function renderTableCard(table) {
    var card = el("section", "oc-card");
    card.setAttribute("data-table-id", table.id);

    var heading = el("h2", null, table.title);
    card.appendChild(heading);

    var meta = el("div", "oc-meta");
    var dice = el("span", "oc-pill oc-dice", table.dice);
    meta.appendChild(dice);
    meta.appendChild(el("span", "oc-pill", table.id));
    meta.appendChild(el("span", null, table.source_heading));
    var rollBtn = el("button", "oc-roll-btn", "Roll " + table.dice);
    rollBtn.type = "button";
    rollBtn.setAttribute("data-oc-roll", table.id);
    meta.appendChild(rollBtn);
    card.appendChild(meta);

    var result = el("div", "oc-result");
    result.setAttribute("aria-live", "polite");
    card.appendChild(result);

    var rows = el("table", "oc-rows");
    var head = el("thead");
    var headRow = el("tr");
    headRow.appendChild(el("th", null, table.dice));
    headRow.appendChild(el("th", null, "Name"));
    head.appendChild(headRow);
    rows.appendChild(head);
    var body = el("tbody");
    table.rows.forEach(function (row) {
      var tr = el("tr");
      tr.setAttribute("data-oc-row", String(row.roll));
      tr.appendChild(el("td", null, String(row.roll)));
      tr.appendChild(el("td", null, row.name));
      body.appendChild(tr);
    });
    rows.appendChild(body);
    card.appendChild(rows);

    rollBtn.addEventListener("click", function () {
      var sides = table.rows.length;
      var rolled = rollDie(sides);
      var picked = table.rows[rolled - 1];
      body.querySelectorAll("tr.oc-selected").forEach(function (tr) {
        tr.classList.remove("oc-selected");
      });
      var selectedRow = body.querySelector('tr[data-oc-row="' + rolled + '"]');
      if (selectedRow) selectedRow.classList.add("oc-selected");
      result.innerHTML = "";
      result.appendChild(el("strong", null, "Rolled " + rolled + " → " + picked.name));
      result.appendChild(
        el("span", null, " — ephemeral table result; not persisted, not published to World.")
      );
      result.classList.add("oc-visible");
    });

    return card;
  }

  function initTablesPage() {
    var host = document.getElementById("oc-tables");
    if (!host) return;
    fetchFixture("tables.json")
      .then(function (fixture) {
        host.innerHTML = "";
        fixture.tables.forEach(function (table) {
          host.appendChild(renderTableCard(table));
        });
        var guidance = el(
          "div",
          "oc-guidance",
          "GM guidance (gold package): name every villager you improvise. A rolled name stays an " +
            "improvisation aid — it is not promoted into required inventory unless the GM names that villager in play."
        );
        host.appendChild(guidance);
      })
      .catch(function () {
        host.innerHTML = "";
        renderFixtureMissing(host, "tables.json");
      });
  }

  /* ---------------- Station 7 — prepared encounters ---------------- */

  function renderCombatantTable(combatants) {
    var table = el("table", "oc-rows");
    var head = el("thead");
    var headRow = el("tr");
    ["Combatant", "Qty", "AC", "HP", "CR", "Key actions"].forEach(function (label) {
      headRow.appendChild(el("th", null, label));
    });
    head.appendChild(headRow);
    table.appendChild(head);
    var body = el("tbody");
    combatants.forEach(function (c) {
      var tr = el("tr");
      tr.appendChild(el("td", null, c.name));
      tr.appendChild(el("td", null, String(c.quantity)));
      tr.appendChild(el("td", null, c.ac));
      tr.appendChild(el("td", null, c.hp));
      tr.appendChild(el("td", null, c.cr));
      tr.appendChild(el("td", null, c.key_actions));
      body.appendChild(tr);
    });
    table.appendChild(body);
    return table;
  }

  function renderEncounterCard(encounter) {
    var card = el("section", "oc-card");
    card.setAttribute("data-encounter-id", encounter.id);

    card.appendChild(el("h2", null, encounter.title));

    var meta = el("div", "oc-meta");
    meta.appendChild(el("span", "oc-pill", encounter.area));
    meta.appendChild(el("span", null, encounter.source_heading));
    card.appendChild(meta);

    card.appendChild(el("p", null, encounter.summary));

    card.appendChild(el("h3", null, "Combatants"));
    card.appendChild(renderCombatantTable(encounter.combatants));

    if (encounter.mechanics_notes && encounter.mechanics_notes.length) {
      card.appendChild(el("h3", null, "Mechanics"));
      var list = el("ul");
      encounter.mechanics_notes.forEach(function (note) {
        list.appendChild(el("li", null, note));
      });
      card.appendChild(list);
    }

    if (encounter.tactics && encounter.tactics.length) {
      card.appendChild(el("h3", null, "Site tactics"));
      var tactics = el("ul");
      encounter.tactics.forEach(function (note) {
        tactics.appendChild(el("li", null, note));
      });
      card.appendChild(tactics);
    }

    card.appendChild(el("h3", null, "World graph objects (module world: of-conks-cons)"));
    var chips = el("div", "oc-nodechips");
    encounter.graph_nodes.forEach(function (nodeId) {
      chips.appendChild(el("span", "oc-pill", nodeId));
    });
    card.appendChild(chips);
    var link = el(
      "p",
      "oc-meta",
      "Inspect via Build surface → Tools → World Graph objects → Find existing object "
    );
    var anchor = el("a", null, "(open Build for of-conks-cons)");
    anchor.href = "/build?campaign=of-conks-cons";
    anchor.style.color = "var(--oc-accent)";
    link.appendChild(anchor);
    card.appendChild(link);

    return card;
  }

  function initEncountersPage() {
    var host = document.getElementById("oc-encounters");
    if (!host) return;
    fetchFixture("encounters.json")
      .then(function (fixture) {
        host.innerHTML = "";
        fixture.encounters.forEach(function (encounter) {
          host.appendChild(renderEncounterCard(encounter));
        });
      })
      .catch(function () {
        host.innerHTML = "";
        renderFixtureMissing(host, "encounters.json");
      });
  }

  window.OfConksPacket = {
    initTablesPage: initTablesPage,
    initEncountersPage: initEncountersPage,
  };
})();
