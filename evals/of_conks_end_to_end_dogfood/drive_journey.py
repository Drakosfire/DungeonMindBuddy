"""Dogfood-only Playwright driver for the Of Conks & Cons end-to-end journey.

Evidence capture utility: drives the real UI at 127.0.0.1:5190 (Vite) backed by
the lane API at 127.0.0.1:8020. Not a product change; safe to delete.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5190"
SHOTS = Path(__file__).parent / "screenshots"
SHOTS.mkdir(exist_ok=True)

PLAN_MARKDOWN = """# Of Conks & Cons — Hempholm Adaptation
## Source premise
A stolen magical [conk](dmb-node:item:the-conk) is sold to a desperate village boy, [Torbin Jove](dmb-node:npc:torbin-jove), planted, and grows into a [grotesque tree](dmb-node:threat:grotesque-tree) in [Hempholm](dmb-node:location:hempholm). The visible tree threatens [the Jove home](dmb-node:location:jove-home); beneath the village, [hollow root corridors](dmb-node:location:root-corridors) with [caretakers](dmb-node:threat:caretakers) guard a deeper plant-metal structure, [the Marrow](dmb-node:location:the-marrow).

Authority: SOURCE (module v2.1, gold package `of-conks-cons-gold-v0`). Graph references resolve against the module's own reviewed world (`of-conks-cons`, worldbuilding_draft) — independent of Eldyrwild and campaign 1/2.

## What the module world carries
Initialized 2026-09-01 via reviewed first-world initialization (24 nodes / 24 edges):
- [Hempholm](dmb-node:location:hempholm) — the village
- [grotesque tree](dmb-node:threat:grotesque-tree) at [its site](dmb-node:location:grotesque-tree-site) — the visible threat
- [Mark Jove](dmb-node:npc:mark-jove) and [Torbin Jove](dmb-node:npc:torbin-jove) — the family at [the Jove home](dmb-node:location:jove-home)
- [the Shacks](dmb-node:location:the-shacks) ([Nar Granitetooth](dmb-node:npc:nar-granitetooth)), [Morwin's store](dmb-node:location:morwins-store) ([Morwin Blackwell](dmb-node:npc:morwin-blackwell)), [Saladin's wagon](dmb-node:location:saladins-wagon) ([Saladin](dmb-node:npc:saladin))
- [caretakers](dmb-node:threat:caretakers) in the [root corridors](dmb-node:location:root-corridors); the [Guardian](dmb-node:threat:guardian) in [the Marrow](dmb-node:location:the-marrow)
- [Lord Fiddlestick](dmb-node:npc:lord-fiddlestick) and [the conk](dmb-node:item:the-conk); [Paelias Sian](dmb-node:npc:paelias-sian) of the [Baldur's Gate mages' guild](dmb-node:faction:baldurs-gate-mages-guild)
- [Maglubiyet's statue](dmb-node:item:maglubiyets-statue), [Belly's mouthwash](dmb-node:item:bellys-mouthwash), [metal leaves](dmb-node:item:metal-leaves)

## Adaptation decisions
- Run the module as itself, in its own world; no Eldyrwild canon entanglement.
- Torbin Jove's purchase stays SOURCE until play confirms it.
- The strange child ([helix child](dmb-node:npc:helix-child)) disposition is a Decision, not a preset outcome.

## Threats / mechanics
- [grotesque tree](dmb-node:threat:grotesque-tree): long reach, hard bark, thorned branches, [metal leaves](dmb-node:item:metal-leaves), fire vulnerability (SOURCE mechanics; threat card copied, not generated).
- [caretakers](dmb-node:threat:caretakers): retaliation wave after the tree falls (twig blight binding per threat card).
- [Guardian](dmb-node:threat:guardian): iron-reinforced spikes, needle barrage (SOURCE).

## Runbook shape
Beat — Arrival / The Visible Problem; Beat — False Victory; Beat — Retaliation; Beat — Descent; Beat — The Marrow; Optional: guild cleanup.

## Open questions / changes from source
- Hooks are alternatives, not three simultaneous facts (gold inventory rule).
- Paelias Sian / guild cleanup is a continuation hook only.
"""

RUNBOOK_MARKDOWN = """# Runbook — Of Conks & Cons: Hempholm

<!-- dmb-playable-element:v2 kind=beat id=beat:arrival-visible-problem beat_kind=spine -->
## Beat — Arrival / The Visible Problem

<!-- dmb-playable-element:v2 kind=scene id=scene:hempholm-jove-home -->
### Scene — Hempholm / Jove Home

The party arrives at [Hempholm](dmb-node:location:hempholm). A [grotesque tree](dmb-node:threat:grotesque-tree) occupies [the Jove home](dmb-node:location:jove-home) garden and damages the house. [Mark Jove](dmb-node:npc:mark-jove) is furious about the damage and the family's lost food stores. [Torbin Jove](dmb-node:npc:torbin-jove) bought [the conk](dmb-node:item:the-conk) from [Lord Fiddlestick](dmb-node:npc:lord-fiddlestick) and planted it, hoping it would feed the family.

<!-- dmb-playable-element:v2 kind=scene id=scene:grotesque-tree -->
### Scene — The Grotesque Tree

The tree attacks anything that comes near: long reach, hard bark, thorned branches, [metal leaves](dmb-node:item:metal-leaves); arcane aura; vulnerability to fire (SOURCE mechanics, threat card copied not generated). If the party delays, the tree grows and risks fire spreading to homes.

<!-- dmb-playable-element:v2 kind=choice id=choice:tree-approach scene=scene:grotesque-tree -->
### Decision — Dealing with the visible tree

<!-- dmb-playable-element:v2 kind=option id=option:tree-burn activates=beat:false-victory -->
- Burn it where it stands — fast, exploits the fire vulnerability, but risks the Jove home and neighboring roofs.

<!-- dmb-playable-element:v2 kind=option id=option:tree-dismantle activates=beat:false-victory -->
- Dismantle it piecemeal from range — slower and safer; the village watches nervously.

<!-- dmb-playable-element:v2 kind=option id=option:tree-investigate-first suppresses=beat:false-victory -->
- Investigate the roots before acting — delays resolution while the tree keeps growing.

<!-- dmb-playable-element:v2 kind=beat id=beat:false-victory beat_kind=spine -->
## Beat — False Victory

<!-- dmb-playable-element:v2 kind=scene id=scene:shacks-celebration -->
### Scene — The Shacks / Premature Celebration

If the visible tree falls without catastrophe, villagers celebrate at [the Shacks](dmb-node:location:the-shacks) with food and drink; [Nar Granitetooth](dmb-node:npc:nar-granitetooth) presides. Let the party enjoy it.

<!-- dmb-playable-element:v2 kind=beat id=beat:retaliation beat_kind=spine -->
## Beat — Retaliation

<!-- dmb-playable-element:v2 kind=scene id=scene:caretaker-rampage -->
### Scene — Caretaker Rampage

Hours later, [caretakers](dmb-node:threat:caretakers) erupt from openings across the village and attack villagers and livestock.

<!-- dmb-playable-element:v2 kind=choice id=choice:defend-villagers scene=scene:caretaker-rampage -->
### Decision — Defending Hempholm

<!-- dmb-playable-element:v2 kind=option id=option:defend-direct activates=beat:descent -->
- Fight the caretakers directly in the streets, then follow the tunnels down.

<!-- dmb-playable-element:v2 kind=option id=option:defend-evacuate activates=beat:descent -->
- Evacuate villagers to [Morwin's store](dmb-node:location:morwins-store) first, then descend.

<!-- dmb-playable-element:v2 kind=beat id=beat:descent beat_kind=spine -->
## Beat — Descent

<!-- dmb-playable-element:v2 kind=scene id=scene:hollow-root-corridors -->
### Scene — Hollow Root Corridors

Openings torn through the village lead into the warm, hollow [root corridors](dmb-node:location:root-corridors) with a stone-or-metal feel.

<!-- dmb-playable-element:v2 kind=scene id=scene:guardian-approach -->
### Scene — Guardian / Approach to the Marrow

The corridors converge toward the [Guardian](dmb-node:threat:guardian): iron-reinforced spikes and a needle barrage (SOURCE mechanics).

<!-- dmb-playable-element:v2 kind=beat id=beat:the-marrow beat_kind=spine -->
## Beat — The Marrow

<!-- dmb-playable-element:v2 kind=scene id=scene:the-marrow -->
### Scene — The Marrow

[The Marrow](dmb-node:location:the-marrow): a wooden helix, metal resin, and a glowing translucent sack holding [a strange child-like being](dmb-node:npc:helix-child). Its disposition is a Decision, not a preset outcome.

<!-- dmb-playable-element:v2 kind=choice id=choice:strange-child scene=scene:the-marrow -->
### Decision — Disposition of the strange child

<!-- dmb-playable-element:v2 kind=option id=option:child-free activates=beat:guild-cleanup -->
- Free the child and accept whatever follows.

<!-- dmb-playable-element:v2 kind=option id=option:child-leave -->
- Leave the helix undisturbed and seal the corridors.

<!-- dmb-playable-element:v2 kind=option id=option:child-destroy activates=beat:guild-cleanup -->
- Destroy the sack and the helix — and answer for it later.

<!-- dmb-playable-element:v2 kind=beat id=beat:guild-cleanup beat_kind=optional -->
## Beat — Mages' Guild Cleanup (optional continuation)

<!-- dmb-playable-element:v2 kind=scene id=scene:guild-cleanup -->
### Scene — Guild Cleanup

[Paelias Sian](dmb-node:npc:paelias-sian) of the [Baldur's Gate mages' guild](dmb-node:faction:baldurs-gate-mages-guild) arrives to erase evidence, compensate witnesses, and track the strange child or the adventurers.
"""


def dump_interactive(page, label: str) -> None:
    """Print buttons/inputs/links with accessible names for recon."""
    items = page.evaluate(
        """() => {
        const out = [];
        const els = document.querySelectorAll('button, a, input, textarea, select, [role="tab"], [role="combobox"], [contenteditable="true"]');
        for (const el of els) {
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            out.push({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role'),
                name: (el.getAttribute('aria-label') || el.innerText || el.getAttribute('placeholder') || '').trim().slice(0, 90),
                type: el.getAttribute('type'),
                disabled: el.disabled === true,
            });
        }
        return out;
    }"""
    )
    print(f"--- {label} ({len(items)} interactive) ---")
    for it in items:
        print(json.dumps(it, ensure_ascii=False))


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "recon-plan"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()

        if step == "build-find":
            doc_id = "9e7786d8-2253-4f8d-b37f-e0720feeaeda"
            page.goto(f"{BASE}/build?campaign=of-conks-cons&documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(5000)
            find_btn = page.get_by_role("button", name="Find existing object")
            print("find-btn:", find_btn.count())
            if find_btn.count():
                tools_btn = page.get_by_role("button", name="Tools", exact=True)
                if tools_btn.count():
                    tools_btn.first.click()
                    page.wait_for_timeout(800)
                find_btn.first.evaluate("el => el.scrollIntoView({block: 'center'})")
                page.wait_for_timeout(400)
                find_btn.first.click()
                page.wait_for_timeout(2500)
                page.screenshot(path=str(SHOTS / "41-build-find-open.png"), full_page=False)
                dump_interactive(page, "build-find-open")
                search = page.locator("input[type='search']")
                print("search-inputs:", search.count())
                if search.count():
                    search.first.fill("grotesque")
                    page.wait_for_timeout(2000)
                    page.screenshot(path=str(SHOTS / "42-build-find-grotesque.png"), full_page=False)
                    dump_interactive(page, "build-find-grotesque")
                    view_btns = page.get_by_role("button", name="View", exact=True)
                    print("view-btns:", view_btns.count())
                    if view_btns.count():
                        view_btns.first.click()
                        page.wait_for_timeout(3000)
                        page.screenshot(path=str(SHOTS / "43-build-object-sheet-grotesque.png"), full_page=False)
                        dump_interactive(page, "build-object-sheet")
                        # Traverse to the threat sheet via the relationship row.
                        rel = page.get_by_role("button", name="Open related object Grotesque Tree")
                        print("rel-traverse:", rel.count())
                        if rel.count():
                            rel.first.click()
                            page.wait_for_timeout(3000)
                            page.screenshot(path=str(SHOTS / "44-build-object-sheet-threat.png"), full_page=False)
                            dump_interactive(page, "build-threat-sheet")

        if step == "build-graph-tool":
            doc_id = "9e7786d8-2253-4f8d-b37f-e0720feeaeda"
            page.goto(f"{BASE}/build?campaign=of-conks-cons&documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(5000)
            dump_interactive(page, "build-full")
            tabs = page.evaluate("""() => Array.from(document.querySelectorAll('[role="tab"], [role="tablist"] button, button')).map(e => ({role: e.getAttribute('role'), name: (e.innerText||'').replace(/\\n/g,' ').slice(0,50)})).slice(0, 60)""")
            print(json.dumps(tabs, indent=1))

        if step == "build-dom-probe":
            doc_id = "9e7786d8-2253-4f8d-b37f-e0720feeaeda"
            page.goto(f"{BASE}/build?campaign=of-conks-cons&documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(5000)
            info = page.evaluate("""() => {
                const out = {tokens: 0, chips: 0, anchors: 0, hempholmHits: [], bodyHasHempholm: false, editors: 0};
                out.tokens = document.querySelectorAll('button.recap-node-token').length;
                out.chips = document.querySelectorAll('[class*="chip"]').length;
                out.anchors = document.querySelectorAll('a[href*="dmb-node"]').length;
                out.editors = document.querySelectorAll('.ProseMirror').length;
                const body = document.body.innerText || '';
                out.bodyHasHempholm = body.includes('Hempholm');
                out.bodyLen = body.length;
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let n; let count = 0;
                while ((n = walker.nextNode()) && count < 5) {
                    if (n.textContent.includes('dmb-node') || (n.textContent.includes('Hempholm') && n.textContent.length < 200)) {
                        const el = n.parentElement;
                        out.hempholmHits.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,60), text: n.textContent.slice(0,60)});
                        count++;
                    }
                }
                return out;
            }""")
            print(json.dumps(info, indent=1)[:2000])
            page.screenshot(path=str(SHOTS / "38-build-dom-probe-localonly.png"), full_page=False)

        if step == "build-inspect":
            doc_id = "9e7786d8-2253-4f8d-b37f-e0720feeaeda"
            proj_requests = []
            def on_resp_build(resp):
                if "world-graph/projection" in resp.url:
                    try:
                        body = resp.json()
                        snap = body.get("snapshot", {})
                        proj_requests.append({"status": resp.status, "snap": {k: snap.get(k) for k in ("worldId","campaignId","scopeMode","revisionId")}, "nodes": (body.get("summary") or {}).get("nodeCount")})
                    except Exception as e:
                        proj_requests.append({"status": resp.status, "err": str(e)[:80]})
            page.on("response", on_resp_build)
            page.goto(f"{BASE}/build?campaign=of-conks-cons&documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(5000)
            tokens = page.locator("button.recap-node-token")
            print("token-count:", tokens.count())
            print(json.dumps(proj_requests, indent=1))
            tree = page.locator("button.recap-node-token[data-graph-node-id='threat:grotesque-tree']").first
            print("tree-token-count:", tree.count())
            if tree.count():
                tree.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
                tree.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=str(SHOTS / "37-build-object-sheet-grotesque.png"), full_page=False)
                dump_interactive(page, "build-object-sheet")

        if step == "import-build-source":
            gold_prep = Path("/home/drakosfire/Downloads/of-conks-cons-v21-gold/playable/hempholm-prep.md")
            markdown = gold_prep.read_text(encoding="utf-8")
            page.goto(f"{BASE}/build?campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3000)
            page.get_by_test_id("build-document-import-open").click()
            page.wait_for_timeout(800)
            dest = page.get_by_test_id("build-document-create-destination")
            options = dest.locator("option").all_inner_texts()
            values = dest.locator("option").evaluate_all("els => els.map(e => e.value)")
            print("destination-options:", list(zip(values, options)))
            # Prefer an existing of-conks-cons destination; else New world.
            target_value = None
            for v, label in zip(values, options):
                if "of-conks-cons" in (v + " " + label):
                    target_value = v
                    break
            if target_value:
                dest.select_option(target_value)
            else:
                dest.select_option("__new_world__")
                page.wait_for_timeout(400)
                wn = page.get_by_test_id("build-document-create-world-name")
                if wn.count():
                    wn.fill("of-conks-cons")
            page.get_by_test_id("build-document-create-title").fill("Hempholm — run packet")
            page.get_by_test_id("build-document-import-markdown").fill(markdown)
            page.screenshot(path=str(SHOTS / "35-build-import-form-localonly.png"), full_page=False)
            page.get_by_test_id("build-document-import-submit").click()
            page.wait_for_timeout(4000)
            page.screenshot(path=str(SHOTS / "36-build-imported-localonly.png"), full_page=False)
            print("url_after_import:", page.url)
            err = page.get_by_test_id("build-document-import-error")
            if err.count():
                print("import-error:", err.first.inner_text())
            act_err = page.get_by_test_id("build-document-import-activation-error")
            if act_err.count():
                print("activation-error:", act_err.first.inner_text())

        if step == "recon-build":
            page.goto(f"{BASE}/build?campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3500)
            page.screenshot(path=str(SHOTS / "34-build-surface-module-world.png"), full_page=False)
            dump_interactive(page, "build-surface")
            testids = page.evaluate("""() => Array.from(document.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid'))""")
            print("testids:", sorted(set(testids)))

        if step == "recon-plan":
            page.goto(f"{BASE}/plan", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "01-plan-surface-initial.png"), full_page=False)
            dump_interactive(page, "plan-surface")

        if step == "recon-world-pill":
            page.goto(f"{BASE}/plan", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="World ·").click()
            page.wait_for_timeout(800)
            page.screenshot(path=str(SHOTS / "02-world-pill-open.png"), full_page=False)
            dump_interactive(page, "world-pill-open")

        if step == "create-plan":
            # Of Conks & Cons is an independent module: no ?campaign= override.
            # The prep document inherits the live session packet's context only.
            page.goto(f"{BASE}/plan", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.get_by_test_id("plan-document-create-open").click()
            page.wait_for_timeout(500)
            suggested_session = page.get_by_test_id("plan-document-create-session").input_value()
            suggested_title = page.get_by_test_id("plan-document-create-title").input_value()
            print(f"suggested_session={suggested_session} suggested_title={suggested_title!r}")
            page.get_by_test_id("plan-document-create-title").fill("Of Conks & Cons — Hempholm adaptation")
            page.screenshot(path=str(SHOTS / "03-plan-create-form.png"), full_page=False)
            page.get_by_test_id("plan-document-create-submit").click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "04-plan-created.png"), full_page=False)
            print("url_after_create:", page.url)
            dump_interactive(page, "plan-created")

        if step == "author-plan":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3000)
            # Editing starts locked; unlock via the canvas lock toggle (toolbar button by name).
            lock_btn = page.get_by_role("button", name="Unlock editing")
            print("lock-buttons:", lock_btn.count())
            if lock_btn.count():
                lock_btn.first.click()
                page.wait_for_timeout(500)
            markdown = PLAN_MARKDOWN
            page.evaluate("async (text) => { await navigator.clipboard.writeText(text); }", markdown)
            page.locator(".ProseMirror").first.click()
            # Replace existing content entirely.
            page.keyboard.press("ControlOrMeta+a")
            page.wait_for_timeout(200)
            page.keyboard.press("ControlOrMeta+v")
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SHOTS / "28-plan-authored-module-world.png"), full_page=False)
            # Ordinary Plan Save ("Save to Markdown").
            page.get_by_role("button", name="Save to Markdown").first.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SHOTS / "29-plan-saved-module-world.png"), full_page=False)
            print("saved, url:", page.url)

        if step == "recon-doc":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaigns=longmont-c1,longmont-c2", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "05-doc-recon.png"), full_page=False)
            dump_interactive(page, "doc-recon")
            testids = page.evaluate("""() => Array.from(document.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid'))""")
            print("testids:", sorted(set(testids)))

        if step == "recon-search":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            page.goto(f"{BASE}/plan?documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            # Open the Tools drawer, then the World Graph objects tool.
            tools_btn = page.get_by_role("button", name="Tools", exact=True)
            if tools_btn.count():
                tools_btn.first.click()
                page.wait_for_timeout(600)
            # Close the Ask panel if it opened (PR #674 lease: do not exercise Agent).
            close_ask = page.get_by_role("button", name="Close Ask DungeonBuddy")
            if close_ask.count():
                close_ask.first.click()
                page.wait_for_timeout(400)
            # The toolbar toggle mounts the World Graph objects tool in the tool host.
            wgo = page.get_by_role("button", name="World Graph objects")
            print("wgo-buttons:", wgo.count())
            if wgo.count():
                wgo.first.click()
                page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "08-after-open.png"), full_page=False)
            dump_interactive(page, "after-open")
            search = page.locator("input[type='search']")
            print("search-inputs:", search.count())
            if search.count():
                search.first.fill("hempholm")
                page.wait_for_timeout(1800)
                page.screenshot(path=str(SHOTS / "08-search-hempholm.png"), full_page=False)
                dump_interactive(page, "search-hempholm")

        if step == "reload-plan":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3500)
            body = page.locator(".ProseMirror").first.inner_text()
            print("contains-source-premise:", "Source premise" in body)
            print("contains-hempholm:", "Hempholm" in body)
            print("contains-runbook-shape:", "Runbook shape" in body)
            print("content-len:", len(body))
            chips = page.locator("button.recap-node-token")
            print("token-count:", chips.count())
            page.screenshot(path=str(SHOTS / "30-plan-hard-reload-module-world.png"), full_page=False)

        if step == "probe-links":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_selector(".ProseMirror >> text=Source premise", timeout=20000)
            page.wait_for_timeout(4000)
            info = page.evaluate("""() => {
                const ed = document.querySelector('.ProseMirror');
                const out = {html: '', chipCount: 0, anchorCount: 0};
                if (!ed) return out;
                out.chipCount = ed.querySelectorAll('[class*="chip"]').length;
                out.anchorCount = ed.querySelectorAll('a').length;
                // Find the first element whose text is exactly a reference label.
                const walker = document.createTreeWalker(ed, NodeFilter.SHOW_TEXT);
                const hits = [];
                let n;
                while ((n = walker.nextNode())) {
                    if (n.textContent.includes('Hempholm')) {
                        const el = n.parentElement;
                        hits.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,80), outer: el.outerHTML.slice(0,220)});
                        if (hits.length >= 4) break;
                    }
                }
                out.hits = hits;
                return out;
            }""")
            print(json.dumps(info, indent=1)[:2500])

        if step == "inspect-object-plan":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            proj_requests = []
            def on_resp(resp):
                if "world-graph/projection" in resp.url:
                    try:
                        body = resp.json()
                        snap = body.get("snapshot", {})
                        proj_requests.append({"status": resp.status, "req": resp.request.post_data, "snap": {k: snap.get(k) for k in ("worldId","campaignId","scopeMode","revisionId")}, "nodes": (body.get("summary") or {}).get("nodeCount")})
                    except Exception as e:
                        proj_requests.append({"status": resp.status, "err": str(e)[:80]})
            page.on("response", on_resp)
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_selector(".ProseMirror >> text=Source premise", timeout=20000)
            try:
                page.wait_for_selector("button.recap-node-token[data-graph-node-id='location:hempholm']", timeout=15000)
                print("tokens-resolved: True")
            except Exception:
                print("tokens-resolved: False (timeout)")
            pill = page.get_by_test_id("app-chrome-world-graph-status")
            if pill.count():
                print("pill:", (pill.first.inner_text() or "").replace("\n", " ")[:140])
            print(json.dumps(proj_requests, indent=1))
            page.screenshot(path=str(SHOTS / "31-plan-state-module-world.png"), full_page=False)
            chip = page.locator("button.recap-node-token[data-graph-node-id='threat:grotesque-tree']").first
            print("tree-token-count:", chip.count())
            if chip.count():
                chip.click()
                page.wait_for_timeout(2500)
                page.screenshot(path=str(SHOTS / "33-object-sheet-grotesque.png"), full_page=False)
                dump_interactive(page, "object-sheet")
            chip_info = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('[class*="chip"]').forEach(e => {
                    const t = (e.innerText||'').trim();
                    if (t && t.length < 80) out.push({cls: e.className.toString().slice(0,70), text: t.slice(0,45), tag: e.tagName});
                });
                return out.slice(0, 25);
            }""")
            print(json.dumps(chip_info, indent=1))
            print("url:", page.url)

        if step == "inspect-object":
            run_id = "fa299cd6-596a-448f-ba36-642b1d352983"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            chip_info = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('[class*="chip"], [class*="ref"], [data-ref-id], [data-node-id]').forEach(e => {
                    const t = (e.innerText||'').trim();
                    if (t && t.length < 80) out.push({cls: e.className.toString().slice(0,60), text: t.slice(0,50), tag: e.tagName});
                });
                return out.slice(0, 20);
            }""")
            print(json.dumps(chip_info, indent=1))

        if step == "play-inspect-reload":
            run_id = "fa299cd6-596a-448f-ba36-642b1d352983"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            # Open the Scenes tab and inspect another scene WITHOUT moving current.
            page.get_by_role("button", name="Scenes 2").click()
            page.wait_for_timeout(1200)
            page.screenshot(path=str(SHOTS / "24-scenes-tab.png"), full_page=False)
            # Inspect Jove Home (must NOT move current).
            page.get_by_role("button", name="Inspect Scene — Hempholm / Jove Home").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "25-inspect-jove-home.png"), full_page=False)
            print("inspect done")

        if step == "play-inspect-reload2":
            run_id = "fa299cd6-596a-448f-ba36-642b1d352983"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            # Hard reload resume check happens on this very load; capture the cockpit.
            page.screenshot(path=str(SHOTS / "26-hard-reload-resume.png"), full_page=False)
            body = page.locator("body").inner_text()
            print("resume-has-grotesque:", "The Grotesque Tree" in body)
            print("resume-has-investigate:", "Investigate the roots" in body)

        if step == "play-decision-cycle":
            run_id = "fa299cd6-596a-448f-ba36-642b1d352983"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            make_current = page.get_by_role("button", name="Make Scene — The Grotesque Tree current")
            if make_current.count():
                make_current.first.click()
                page.wait_for_timeout(1500)
            # Select "Burn it where it stands" (activates beat:false-victory).
            page.get_by_role("radio", name="Burn it where it stands").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "20-option-burn-selected.png"), full_page=False)
            # Change option to "Dismantle".
            page.get_by_role("radio", name="Dismantle it piecemeal").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "21-option-dismantle-selected.png"), full_page=False)
            # Clear by clicking the selected option again (toggle) if supported.
            page.get_by_role("radio", name="Dismantle it piecemeal").click()
            page.wait_for_timeout(1200)
            page.screenshot(path=str(SHOTS / "22-option-cleared.png"), full_page=False)
            # Reselect "Investigate the roots" (suppresses false-victory).
            page.get_by_role("radio", name="Investigate the roots").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / "23-option-investigate-selected.png"), full_page=False)
            print("decision-cycle done, url:", page.url)

        if step == "play-decision":
            run_id = "fa299cd6-596a-448f-ba36-642b1d352983"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Make Scene — The Grotesque Tree current").click()
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SHOTS / "19-scene-grotesque-current.png"), full_page=False)
            dump_interactive(page, "grotesque-scene")

        if step == "start-run":
            page.goto(f"{BASE}/play", wait_until="networkidle")
            page.wait_for_timeout(2500)
            rb = page.get_by_test_id("play-start-runbook-3ae3eb70-6042-4d7a-be94-065045a6a45e")
            print("runbook-listed:", rb.count())
            if rb.count():
                rb.first.click()
                page.wait_for_timeout(800)
            page.screenshot(path=str(SHOTS / "17-runbook-selected.png"), full_page=False)
            start_btn = page.get_by_test_id("play-start-run-submit")
            print("start-disabled:", start_btn.is_disabled())
            if not start_btn.is_disabled():
                start_btn.click()
                page.wait_for_timeout(4000)
                print("after-start-url:", page.url)
                page.screenshot(path=str(SHOTS / "18-run-started.png"), full_page=False)
                dump_interactive(page, "run-started")

        if step == "reload-runbook":
            doc_id = "3ae3eb70-6042-4d7a-be94-065045a6a45e"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3500)
            body = page.locator(".ProseMirror").first.inner_text()
            for probe in ["Arrival / The Visible Problem", "False Victory", "Retaliation", "Descent", "The Marrow", "Guild Cleanup", "Disposition of the strange child"]:
                print(f"contains[{probe}]:", probe in body)
            chips = page.locator("button.recap-node-token")
            print("token-count:", chips.count())
            page.screenshot(path=str(SHOTS / "32-runbook-hard-reload-module-world.png"), full_page=False)

        if step == "author-runbook":
            doc_id = "3ae3eb70-6042-4d7a-be94-065045a6a45e"
            page.goto(f"{BASE}/plan?documentId={doc_id}&campaign=of-conks-cons", wait_until="networkidle")
            page.wait_for_timeout(3000)
            lock_btn = page.get_by_role("button", name="Unlock editing")
            if lock_btn.count():
                lock_btn.first.click()
                page.wait_for_timeout(500)
            page.evaluate("async (text) => { await navigator.clipboard.writeText(text); }", RUNBOOK_MARKDOWN)
            editor = page.locator(".ProseMirror").first
            editor.click()
            # Replace the blank beat entirely.
            page.keyboard.press("ControlOrMeta+a")
            page.wait_for_timeout(200)
            page.keyboard.press("ControlOrMeta+v")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "14-runbook-authored.png"), full_page=False)
            page.get_by_role("button", name="Save to Markdown").first.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SHOTS / "15-runbook-saved.png"), full_page=False)
            print("runbook saved, url:", page.url)

        if step == "create-runbook":
            page.goto(f"{BASE}/play", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.get_by_test_id("play-create-blank-runbook-campaign").fill("longmont-c2")
            page.wait_for_timeout(400)
            page.get_by_test_id("play-create-blank-runbook-submit").click()
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SHOTS / "12-runbook-created.png"), full_page=False)
            # The created runbook becomes selected; open authoring.
            edit_btn = page.get_by_test_id("play-edit-runbook")
            print("edit-disabled:", edit_btn.is_disabled())
            if not edit_btn.is_disabled():
                edit_btn.click()
                page.wait_for_timeout(3000)
                print("authoring-url:", page.url)
                page.screenshot(path=str(SHOTS / "13-runbook-authoring.png"), full_page=False)

        if step == "recon-play":
            page.goto(f"{BASE}/play", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "11-play-surface.png"), full_page=False)
            dump_interactive(page, "play-surface")
            testids = page.evaluate("""() => Array.from(document.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid'))""")
            print("testids:", sorted(set(testids)))

        if step == "recon-network":
            doc_id = "bfbed067-30d8-486a-846b-824c713e6a49"
            requests = []
            def on_response(resp):
                if "world-graph" in resp.url or "projection" in resp.url:
                    try:
                        body = resp.json()
                        summary = body.get("summary") or body.get("message") or list(body.keys())[:6]
                    except Exception:
                        summary = f"status={resp.status}"
                    requests.append({"url": resp.url, "status": resp.status, "req": resp.request.post_data, "summary": str(summary)[:200]})
            page.on("response", on_response)
            page.goto(f"{BASE}/plan?documentId={doc_id}", wait_until="networkidle")
            page.wait_for_timeout(4000)
            page.screenshot(path=str(SHOTS / "09-network-recon.png"), full_page=False)
            print(json.dumps(requests, indent=1))

        if step == "roll-station":
            page.goto(
                f"{BASE}/evals/of_conks_end_to_end_dogfood/packet/of-conks-tables.html",
                wait_until="networkidle",
            )
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "50-roll-tables-loaded-localonly.png"), full_page=True)
            cards = page.locator(".oc-card")
            print("table-cards:", cards.count())
            # Roll each table once; the selected row highlights and a result banner appears.
            for idx, shot in [(0, "51-roll-male-localonly"), (1, "52-roll-female-localonly"), (2, "53-roll-nicknames-localonly")]:
                btn = cards.nth(idx).get_by_role("button", name="Roll 1d12")
                if btn.count():
                    btn.first.click()
                    page.wait_for_timeout(600)
                    result = cards.nth(idx).locator(".oc-result").inner_text()
                    print(f"roll[{idx}]:", result.strip())
                    cards.nth(idx).screenshot(path=str(SHOTS / f"{shot}.png"))
            page.screenshot(path=str(SHOTS / "54-roll-tables-after-rolls-localonly.png"), full_page=True)

        if step == "encounter-station":
            page.goto(
                f"{BASE}/evals/of_conks_end_to_end_dogfood/packet/of-conks-encounters.html",
                wait_until="networkidle",
            )
            page.wait_for_timeout(2500)
            cards = page.locator(".oc-card")
            print("encounter-cards:", cards.count())
            for idx, shot in [(0, "55-encounter-grotesque-tree-localonly"), (1, "56-encounter-caretakers-localonly"), (2, "57-encounter-guardian-localonly")]:
                if idx < cards.count():
                    cards.nth(idx).scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    cards.nth(idx).screenshot(path=str(SHOTS / f"{shot}.png"))
            page.screenshot(path=str(SHOTS / "58-encounters-full-localonly.png"), full_page=True)

        if step == "asset-station":
            page.goto(
                f"{BASE}/evals/of_conks_end_to_end_dogfood/packet/of-conks-assets.html",
                wait_until="networkidle",
            )
            page.wait_for_timeout(2500)
            imgs = page.locator(".oc-asset img")
            print("asset-images:", imgs.count())
            for i in range(imgs.count()):
                ok = imgs.nth(i).evaluate("el => el.complete && el.naturalWidth > 0")
                print(f"  img[{i}] loaded:", ok, imgs.nth(i).get_attribute("src"))
            page.screenshot(path=str(SHOTS / "59-source-assets-localonly.png"), full_page=True)

        if step == "start-run-v3":
            # Start a fresh Run from the re-authored Runbook (revision 3, module-world refs).
            page.goto(f"{BASE}/play", wait_until="networkidle")
            page.wait_for_timeout(2500)
            # The cockpit resumes the latest run; open the start panel explicitly.
            new_run = page.get_by_test_id("play-start-new-run")
            if new_run.count():
                new_run.first.click()
                page.wait_for_timeout(1500)
            rb = page.get_by_test_id("play-start-runbook-3ae3eb70-6042-4d7a-be94-065045a6a45e")
            print("runbook-listed:", rb.count())
            if rb.count():
                rb.first.click()
                page.wait_for_timeout(800)
            page.screenshot(path=str(SHOTS / "60-runbook-v3-selected.png"), full_page=False)
            start_btn = page.get_by_test_id("play-start-run-submit")
            print("start-disabled:", start_btn.is_disabled())
            if not start_btn.is_disabled():
                start_btn.click()
                page.wait_for_timeout(4000)
                print("after-start-url:", page.url)
                page.screenshot(path=str(SHOTS / "61-run-v3-started.png"), full_page=False)
                # Cockpit: module-world tokens render as chips (sheet opening is OC-009 gap).
                tokens = page.locator("button.recap-node-token")
                print("cockpit-token-count:", tokens.count())
                page.screenshot(path=str(SHOTS / "62-run-v3-cockpit.png"), full_page=False)
                # Hard reload: run state must persist.
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(3000)
                tokens_after = page.locator("button.recap-node-token")
                print("cockpit-token-count-after-reload:", tokens_after.count())
                page.screenshot(path=str(SHOTS / "63-run-v3-reloaded.png"), full_page=False)

        if step == "play-v3-decision":
            # Exercise the Scene Decision on the module-world run, then prove persistence.
            run_id = "2224fbd7-07d0-4e12-8b84-7b9543c7acdd"
            page.goto(f"{BASE}/play?run={run_id}", wait_until="networkidle")
            page.wait_for_timeout(3500)
            # The Decision belongs to scene:grotesque-tree; make it current first.
            mc = page.locator("button", has_text="Make Current")
            if mc.count() == 0:
                page.locator("button", has_text="Scenes").first.click()
                page.wait_for_timeout(1500)
                mc = page.locator("button", has_text="Make Current")
            for i in range(mc.count()):
                card_text = mc.nth(i).evaluate(
                    "el => { let n = el.closest('section,article,div[class*=card],li') || el.parentElement; return (n.innerText||''); }"
                )
                if "Grotesque" in card_text:
                    mc.nth(i).click()
                    break
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SHOTS / "71-run-v3-grotesque-current.png"), full_page=False)
            investigate = page.get_by_role("radio", name="Investigate the roots")
            print("investigate-option:", investigate.count())
            if investigate.count():
                investigate.first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=str(SHOTS / "64-run-v3-decision-selected.png"), full_page=False)
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(3500)
                checked = page.get_by_role("radio", name="Investigate the roots").first.is_checked()
                print("investigate-checked-after-reload:", checked)
                page.screenshot(path=str(SHOTS / "65-run-v3-decision-reloaded.png"), full_page=False)

        browser.close()


if __name__ == "__main__":
    main()
