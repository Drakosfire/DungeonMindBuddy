const { chromium } = require(process.env.DMB_BENCHMARK_PLAYWRIGHT);
const { writeFileSync } = require("node:fs");
const { setTimeout: delay } = require("node:timers/promises");

async function pollBrowserRead(read, timeout, interval, description) {
  const deadline = performance.now() + timeout;
  while (performance.now() < deadline) {
    const value = await read();
    if (value) return value;
    await delay(interval);
  }
  throw new Error("Timed out waiting for " + description);
}

async function run() {
  const origin = process.env.DMB_BENCHMARK_BROWSER_ORIGIN;
  const browser = await chromium.launch({
    executablePath: process.env.DMB_BENCHMARK_CHROMIUM, headless: true, args: ["--no-sandbox"],
  });
  try {
    const context = await browser.newContext({ serviceWorkers: "block" });
    await context.route("**/*", route => {
      if (new URL(route.request().url()).origin !== origin) return route.abort();
      return route.continue({ headers: { ...route.request().headers(),
        authorization: "Bearer " + process.env.DMB_BENCHMARK_BROWSER_TOKEN } });
    });
    const page = await context.newPage();
    const apiFailures = [];
    const turnNetworkFailures = [];
    let turnPosts = 0;
    page.on("request", request => {
      if (request.method() === "POST" && new URL(request.url()).pathname === "/api/live/agent/turn") {
        turnPosts += 1;
      }
    });
    page.on("requestfailed", request => {
      if (new URL(request.url()).pathname === "/api/live/agent/turn") {
        turnNetworkFailures.push(request.failure()?.errorText ?? "unknown");
      }
    });
    page.on("response", response => {
      const pathname = new URL(response.url()).pathname;
      if (pathname.startsWith("/api/") && response.status() >= 400) {
        apiFailures.push({ pathname, status: response.status() });
      }
    });
    const documentId = process.env.DMB_BENCHMARK_DOCUMENT_ID;
    const build = process.env.DMB_BENCHMARK_SURFACE === "build";
    const imagePreview = process.env.DMB_BENCHMARK_IMAGE_PREVIEW === "1";
    if (process.env.DMB_BENCHMARK_PLAY_CHOICE) {
      const pin = JSON.parse(process.env.DMB_BENCHMARK_PLAY_CHOICE);
      const world = process.env.DMB_BENCHMARK_WORLD;
      const runRoute = "/api/live/world-play-runs/v2/" + pin.run_id;
      const progressPath = runRoute + "/progress";
      const url = origin + "/play?" + new URLSearchParams({world, run: pin.run_id});
      let progressPuts = 0;
      page.on("request", request => {
        if (request.method() === "PUT" && new URL(request.url()).pathname === progressPath) progressPuts++;
      });
      const option = page.locator(`[data-choice-id="${pin.choice_id}"] button[role="radio"][value="${pin.option_id}"]`);
      const result = {};
      try {
        await page.goto(url);
        await option.waitFor({timeout: 15000});
        if (await option.getAttribute("aria-checked") !== "false") throw new Error("Option must be initially unselected");
        const response = page.waitForResponse(res => res.request().method() === "PUT"
          && new URL(res.url()).pathname === progressPath, {timeout: 15000});
        response.catch(() => {});
        const started = performance.now();
        await option.click();
        result.response_status = (await response).status();
        result.choice_to_response_ms = performance.now() - started;
        await page.reload();
        await option.waitFor({timeout: 15000});
        result.reopened_selected = await option.getAttribute("aria-checked") === "true";
      } catch (error) {
        result.error = String(error);
        result.page = await page.evaluate(() => ({
          route: location.pathname + location.search,
          headings: [...document.querySelectorAll("h1,h2,h3")].slice(0, 12).map(heading => heading.innerText),
          alerts: [...document.querySelectorAll('[role="alert"]')].slice(0, 8).map(alert => alert.innerText),
          choices: [...document.querySelectorAll("[data-choice-id]")].slice(0, 12).map(
            choice => ({id: choice.dataset.choiceId,
              options: [...choice.querySelectorAll('[role="radio"]')].map(option => ({
                tag: option.tagName, value: option.getAttribute("value"),
                selected: option.getAttribute("aria-checked"),
              })),
            })),
        })).catch(() => null);
        result.api_failures = apiFailures;
      } finally {
        result.progress_puts = progressPuts;
        result.turn_posts = turnPosts;
        writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({play_choice: result}, null, 2));
      }
      return;
    }
    const mounted = imagePreview ? page.waitForResponse(response =>
      new URL(response.url()).pathname === "/api/live/workspace-documents/" + documentId + "/snapshot"
      && response.request().method() === "GET" && response.ok()
    ) : null;
    mounted?.catch(() => {});
    await page.goto(origin + (build ? "/build?world=" : "/plan?world=") +
      encodeURIComponent(process.env.DMB_BENCHMARK_WORLD) + "&documentId=" + encodeURIComponent(documentId));
    if (imagePreview) {
      const { generatePrivatePreview, regeneratePrivatePreview, selectLibraryImage, recoverImageSave } = require("./image_studio.cjs");
      const { createHash } = require("node:crypto");
      let generationPosts = 0;
      const writeRequests = [];
      let documentCommitPosts = 0;
      page.on("request", request => {
        const path = new URL(request.url()).pathname;
        const method = request.method();
        if (method === "POST" && path === "/api/live/tiptap/markdown-write/commit") documentCommitPosts++;
        if (method === "POST" && (path === "/api/live/media/images/generate" || path.endsWith("/regenerate"))) generationPosts++;
        if (/\/api\/live\/media\/images\/.*\/(save|place)$/.test(path)
            || (!["GET", "HEAD"].includes(method) && path.startsWith("/api/live/workspace-documents/"))) {
          writeRequests.push({ method, path });
        }
      });
      const result = { preview: null };
      try {
        const snapshot = await (await mounted).json();
        const pin = JSON.parse(process.env.DMB_BENCHMARK_IMAGE_PAGE_PIN);
        const record = snapshot.record;
        if (record?.world_id !== process.env.DMB_BENCHMARK_WORLD ||
            record.document_id !== documentId || record.revision !== pin.expected_revision ||
            snapshot.loaded_revision !== pin.expected_revision ||
            snapshot.committed_content_sha256 !== pin.expected_content_sha256) {
          throw new Error("Mounted Build image preview differs from the pinned page");
        }
        result.mounted_page = {
          record: { world_id: record.world_id, document_id: record.document_id, revision: record.revision },
          loaded_revision: snapshot.loaded_revision,
          committed_content_sha256: snapshot.committed_content_sha256,
        };
        const editor = page.locator(".build-surface-shell .ProseMirror[contenteditable=true]:visible");
        const readDocument = () => editor.evaluate(element => {
          const doc = element.pmViewDesc?.node;
          if (!doc?.type?.isBlock || typeof doc.toJSON !== "function") {
            throw new Error("Mounted Build editor has no readable document model");
          }
          return doc.toJSON();
        });
        const editorBefore = await readDocument();
        await page.getByRole("button", { name: "Open Image Studio", exact: true }).click();
        const parent = JSON.parse(process.env.DMB_BENCHMARK_IMAGE_PARENT || "null");
        const placement = JSON.parse(process.env.DMB_BENCHMARK_IMAGE_PLACEMENT || "null");
        if (placement) {
          const studio = await selectLibraryImage(page, origin, parent);
          const blocks = editorBefore.content;
          const text = node => node.text ?? (node.content ?? []).map(text).join("");
          const matches = blocks.flatMap((node, index) =>
            node.type === "paragraph" && text(node) === placement.anchor ? [index] : []
          );
          if (matches.length !== 1) throw new Error("Expected one exact image-placement paragraph");
          const anchor = editor.locator("p").filter({ hasText: placement.anchor });
          const snapshotPath = "/api/live/workspace-documents/" + documentId + "/snapshot";
          const committed = async () => {
            const response = await page.request.get(origin + snapshotPath + "?view=committed", {
              headers: { authorization: "Bearer " + process.env.DMB_BENCHMARK_BROWSER_TOKEN },
            });
            if (!response.ok()) throw new Error("Committed placement page could not be read");
            const body = await response.json();
            return { revision: body.loaded_revision, sha256: body.committed_content_sha256 };
          };
          const initial = await committed();
          if (initial.revision !== pin.expected_revision || initial.sha256 !== pin.expected_content_sha256)
            throw new Error("Placement page changed before the interaction");
          if (placement.lose_save_ack)
            result.save_recovery = await recoverImageSave(page, origin, studio, parent.asset_id);
          const started = performance.now();
          await studio.getByRole("button", { name: "Place on page", exact: true }).click();
          await editor.and(page.locator(".is-media-placement-target")).waitFor();
          await anchor.click();
          const index = matches[0] + 1;
          const after = await pollBrowserRead(async () => {
            const doc = await readDocument();
            return doc.content.length === blocks.length + 1 && doc;
          }, 5000, 100, "one mounted image block");
          const inserted = after.content[index];
          const retained = after.content.filter((_, i) => i !== index);
          if (inserted?.content?.length !== 1 || inserted.content[0].type !== "mediaImage"
              || inserted.content[0].attrs?.assetId !== parent.asset_id
              || JSON.stringify(retained) !== JSON.stringify(blocks))
            throw new Error("Mounted image placement differs from the pinned target and neighbors");
          result.placement = { index, asset_id: parent.asset_id, initial };
          result.placement.after_save = await pollBrowserRead(async () => {
            const saved = await committed();
            return saved.revision > initial.revision && saved;
          }, 10000, 100, "committed image placement");
          await page.reload();
          result.placement.reopened = await pollBrowserRead(async () => {
            const doc = await readDocument();
            return doc.content.length === after.content.length && doc;
          }, 10000, 100, "mounted placed image after reload");
          result.placement.mounted_reopened_exact = JSON.stringify(result.placement.reopened) === JSON.stringify(after);
          delete result.placement.reopened;
          result.placement.elapsed_ms = performance.now() - started;
        } else if (parent) {
          result.preview = await regeneratePrivatePreview(page, origin, parent, process.env.DMB_BENCHMARK_QUESTION);
        } else {
          const { asset, model, elapsedMs } = await generatePrivatePreview(
            page, origin, process.env.DMB_BENCHMARK_QUESTION
          );
          const encoded = /^data:image\/(?:png|jpeg|webp);base64,(.+)$/.exec(asset.data_url);
          if (!encoded) throw new Error("Generated preview has no supported image bytes");
          result.preview = {
            asset: { asset_id: asset.asset_id, state: asset.state },
            sha256: createHash("sha256").update(Buffer.from(encoded[1], "base64")).digest("hex"),
            model, elapsedMs,
          };
        }
        if (!placement) result.editor_unchanged = JSON.stringify(editorBefore) === JSON.stringify(await readDocument());
      } finally {
        writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
          ...result, generation_posts: generationPosts, document_commit_posts: documentCommitPosts,
          write_requests: writeRequests, turn_posts: turnPosts,
        }, null, 2));
      }
      return;
    }
    const composer = build ? page.getByLabel("Message DungeonBuddy") :
      page.getByPlaceholder("Ask Buddy, or tell it what to change…");
    async function openComposer() {
      if (!(await composer.isVisible())) {
        const conversation = page.locator(build ? ".conversation-dock__launcher" : ".plan-conversation-dock__launcher").getByRole("button");
        await conversation.click({ timeout: 15000 });
      }
      await composer.waitFor({ timeout: 20000 });
    }
    await openComposer();
    const draft = process.env.DMB_BENCHMARK_QUESTION;
    const unsentDraft = process.env.DMB_BENCHMARK_UNSENT_DRAFT === "1";
    if (unsentDraft && await composer.inputValue() !== "") throw new Error("Unsent draft fixture composer is not empty");
    await composer.fill(draft);
    if (unsentDraft) {
      if (await composer.inputValue() !== draft) throw new Error("Draft entry did not match fixture");
      await page.reload();
      await openComposer();
      await composer.locator("xpath=self::*[not(@disabled)]").waitFor({ timeout: 15000 });
      const restored = await composer.inputValue() === draft;
      writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
        draft_restore: { restored, attemptedTurnPosts: turnPosts }, apiFailures, turnNetworkFailures,
      }, null, 2));
      return;
    }
    if (build || process.env.DMB_BENCHMARK_LIVE_BROWSER === "1") {
      const selected = process.env.DMB_BENCHMARK_SELECTION;
      const documentStart = process.env.DMB_BENCHMARK_DOCUMENT_START === "1";
      const editor = page.locator((build ? ".build-surface-shell" : ".world-plan-visual-editor") + " .ProseMirror[contenteditable=true]:visible");
      if (await editor.count() !== 1) throw new Error("Placement fixture needs one editable editor");
      await editor.focus();
      if (documentStart) {
        await editor.press("Control+Home");
      } else {
        await editor.evaluate((root, text) => {
          const matches = [];
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          while (walker.nextNode()) {
            const node = walker.currentNode;
            let at = node.data.indexOf(text);
            while (at !== -1) { matches.push([node, at]); at = node.data.indexOf(text, at + 1); }
          }
          if (matches.length !== 1) throw new Error("Selected text must occur exactly once in one editor text node");
          const [node, at] = matches[0], range = document.createRange(), selection = window.getSelection();
          range.setStart(node, at); range.setEnd(node, at + text.length);
          selection.removeAllRanges(); selection.addRange(range);
          document.dispatchEvent(new Event("selectionchange"));
          if (selection.toString() !== text) throw new Error("Browser selection did not match fixture");
        }, selected);
      }
    }
    const live = process.env.DMB_BENCHMARK_LIVE_BROWSER === "1";
    const send = page.getByRole("button", { name: build || live ? /^(Send message|Propose edit)$/ : /^Send message$/ });
    await send.waitFor({ state: "visible" });
    if (process.env.DMB_BENCHMARK_PANE_SETTLED === "1") {
      await page.waitForLoadState("networkidle", { timeout: 30000 });
    }
    const calibrate = () => page.evaluate(async () => {
      const bounds = [];
      for (let i = 0; i < 20; i += 1) {
        const start = performance.now();
        const value = Number(await (await fetch("/__benchmark/clock", { cache: "no-store" })).text());
        const end = performance.now();
        bounds.push([value - end, value - start]);
      }
      return bounds;
    });
    const before = await calibrate();
    await send.evaluate(button => {
      button.addEventListener("click", () => performance.mark("benchmark-browser-send"), { once: true, capture: true });
    });
    const response = page.waitForResponse(result =>
      new URL(result.url()).pathname === "/api/live/agent/turn" && result.request().method() === "POST",
    { timeout: 60000 });
    response.catch(() => {});
    let delivered;
    try {
      await send.click({ timeout: 12000 });
      delivered = await response;
    } catch (error) {
      const alerts = await page.getByRole("alert").allTextContents();
      writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
        alerts, apiFailures, composerHasQuestion: await composer.inputValue() === process.env.DMB_BENCHMARK_QUESTION,
        planTarget: build ? undefined : await page.getByLabel("Actual Plan change target").allTextContents(),
      }, null, 2));
      throw error;
    }
    if (delivered.headers()["x-benchmark-placement-rejected"] === "1") {
      throw new Error("Plan placement failed benchmark preflight; rejected request retained");
    }
    let buildCheckpoint;
    if (process.env.DMB_BENCHMARK_LIVE_BROWSER === "1") {
      // Keep the page alive while its ordinary client consumes the terminal event.
      buildCheckpoint = await pollBrowserRead(() => page.evaluate(async () => {
        const response = await fetch("/__benchmark/browser-response-retained", { cache: "no-store" });
        const checkpoint = await response.json();
        return checkpoint.retained === true ? checkpoint : false;
      }), 75000, 250, "retained Build response");
    }
    const after = await calibrate();
    const browserMarks = await page.evaluate(() => {
      const click = performance.getEntriesByName("benchmark-browser-send").at(-1)?.startTime;
      const resources = performance.getEntriesByType("resource");
      const request = resources.filter(entry => new URL(entry.name).pathname === "/api/live/agent/turn")
        .map(entry => entry.startTime).at(-1);
      const preflight = resources.filter(entry => entry.startTime >= click && entry.startTime < request)
        .map(entry => ({
          phase: new URL(entry.name).pathname.endsWith("/committed-revision") ? "committed_plan_revision" : "other_resource",
          start: entry.startTime, requestStart: entry.requestStart,
          responseStart: entry.responseStart, end: entry.responseEnd,
        }));
      return { click, request, preflight };
    });
    let terminalBuildFailure;
    if (process.env.DMB_BENCHMARK_TERMINAL_BUILD_FAILURE === "1") {
      const checkpoint = buildCheckpoint;
      const world = process.env.DMB_BENCHMARK_WORLD;
      const failed = await pollBrowserRead(() => page.evaluate(async ({ world, checkpoint }) => {
        const path = "/api/live/agent/worlds/" + encodeURIComponent(world)
          + "/conversation?include_turn_correlation=true";
        const response = await fetch(path, { cache: "no-store" });
        if (!response.ok) return false;
        const history = await response.json();
        if (history.active_conversation_id !== checkpoint.conversation_id) return false;
        return history.turns.find(turn => turn.idempotency_key === checkpoint.idempotency_key
          && ["failed", "interrupted"].includes(turn.lifecycle_status)) || false;
      }, { world, checkpoint }), 10000, 250, "bound terminal Build turn");
      await page.reload();
      await openComposer();
      const turn = page.locator(`article[data-turn-id="${failed.turn_id}"]`);
      await turn.waitFor({timeout: 12000});
      const trace = turn.locator("summary").filter({hasText: /^Trace$/});
      if (await trace.count() === 1 && !await trace.evaluate(summary => summary.parentElement.open)) {
        await trace.click();
      }
      const retry = turn.getByRole("button", { name: "Retry question", exact: true });
      const retryVisible = await retry.first().isVisible();
      terminalBuildFailure = {
        turn_id: failed.turn_id,
        retry_visible: retryVisible,
        retry_enabled: retryVisible && await retry.first().isEnabled(),
        check_insertion_visible: await page.getByRole("button", { name: "Check insertion", exact: true }).first().isVisible(),
        turn_posts: turnPosts,
      };
    }
    let confirmation;
    if (process.env.DMB_BENCHMARK_CONFIRM_SAVE === "1") {
      confirmation = { attempted: false };
      try {
        const checkpoint = buildCheckpoint;
        confirmation.checkpoint = { retained: checkpoint.retained === true,
          has_action: Boolean(checkpoint.action_id), has_correlation: Boolean(checkpoint.idempotency_key) };
        let action = checkpoint.action_id;
        const world = process.env.DMB_BENCHMARK_WORLD;
        if (!action && checkpoint.idempotency_key) {
          const recovered = await pollBrowserRead(() => page.evaluate(async ({ world, checkpoint }) => {
            const path = "/api/live/agent/worlds/" + encodeURIComponent(world)
              + "/conversation?include_turn_correlation=true";
            const response = await fetch(path, { cache: "no-store" });
            if (!response.ok) return false;
            const history = await response.json();
            if (history.active_conversation_id !== checkpoint.conversation_id) return false;
            const turns = history.turns.filter(turn => turn.idempotency_key === checkpoint.idempotency_key);
            if (turns.length !== 1 || ["accepted", "running"].includes(turns[0].lifecycle_status)) return false;
            const turn = turns[0];
            const actionId = turn.knowledge_context?.completion?.action_id;
            if (turn.lifecycle_status === "completed" && !actionId) return false;
            return { action_id: actionId ?? null, lifecycle: turn.lifecycle_status };
          }, { world, checkpoint }), 40000, 500, "bound durable proposal");
          confirmation.recovered_lifecycle = recovered.lifecycle;
          action = recovered.action_id;
          if (action) await page.reload();
        }
        if (!action || !/^[a-f0-9-]{36}$/i.test(action)) throw new Error("Turn has no bound proposal to confirm");
        const reviewPath = "/api/live/agent/worlds/" + encodeURIComponent(world)
          + "/build-proposals/" + encodeURIComponent(action) + "/review";
        confirmation.action_id = action;
        const review = page.getByRole("region", { name: "Suggestion review", exact: true });
        await review.waitFor({ timeout: 15000 });
        const beforeSave = await page.evaluate(async ({ id, reviewPath }) => {
          async function read(path) {
            const response = await fetch(path, { cache: "no-store" });
            return { status: response.status, body: await response.json() };
          }
          return { page: await read("/api/live/workspace-documents/" + encodeURIComponent(id) + "/snapshot?view=committed"),
            review: await read(reviewPath) };
        }, { id: documentId, reviewPath });
        confirmation.beforeSave = beforeSave;
        const exactReview = beforeSave.review.body.review ?? beforeSave.review.body;
        if (beforeSave.page.status !== 200 || beforeSave.review.status !== 200
          || exactReview.action_id !== action || exactReview.world_id !== world || exactReview.state !== "editing") {
          throw new Error("The exact editable proposal or committed page could not be read");
        }
        const text = await review.getByRole("textbox", { name: "Suggestion text" }).innerText();
        if (text.trim() !== exactReview.markdown.trim()) throw new Error("Visible suggestion differs from the bound proposal");
        if (process.env.DMB_BENCHMARK_LOSE_CONFIRM_ACK === "1") {
          const exactPath = url => url.origin === origin && url.pathname === reviewPath && !url.search;
          const confirmPosts = [];
          let confirmRequest;
          confirmation.confirm_posts = confirmPosts;
          confirmation.retry_exercised = false;
          page.on("request", request => {
            if (request.method() !== "POST" || !exactPath(new URL(request.url()))) return;
            const command = request.postDataJSON();
            if (command?.operation === "confirm") {
              confirmRequest = request;
              confirmPosts.push({apply_id: command.apply_id, expected_revision: command.expected_revision});
            }
          });
          let held;
          let intercepting = false;
          const intercept = async route => {
            const request = route.request();
            if (intercepting || request.method() !== "POST" || request.postDataJSON()?.operation !== "confirm") {
              return route.fallback();
            }
            // This fixture withholds only the response to the real owner command.
            // Receipt and Save still run through the application exactly once.
            intercepting = true;
            const response = await route.fetch({
              headers: { ...request.headers(), authorization: "Bearer " + process.env.DMB_BENCHMARK_BROWSER_TOKEN },
              maxRedirects: 0,
              maxRetries: 0,
            });
            const receipt = { status: response.status(), body: await response.json(), request: request.postDataJSON() };
            await route.abort("failed");
            held = receipt;
            confirmation.withheld = receipt;
          };
          const readOwners = () => page.evaluate(async ({ id, reviewPath }) => {
            const snapshotPath = "/api/live/workspace-documents/" + encodeURIComponent(id) + "/snapshot?view=committed";
            const [pageResponse, reviewResponse] = await Promise.all(
              [snapshotPath, reviewPath].map(path => fetch(path, { cache: "no-store" })));
            return {
              page: { status: pageResponse.status, body: await pageResponse.json() },
              review: { status: reviewResponse.status, body: await reviewResponse.json() },
            };
          }, { id: documentId, reviewPath });
          await page.route(exactPath, intercept);
          let waitFailure;
          try {
            confirmation.attempted = true;
            await review.getByRole("button", { name: "Save", exact: true }).click();
            try {
              await pollBrowserRead(() => held || false, 20000, 200, "confirmation response to withhold");
            } catch (error) {
              waitFailure = error;
            }
            if (!held) {
              if (intercepting || confirmPosts.length !== 0) throw waitFailure;
              const committed = await readOwners();
              const pending = committed.review.body.review ?? committed.review.body;
              const savedPage = committed.page.body;
              if (committed.page.status !== 200 || committed.review.status !== 200
                  || pending.state !== "applying" || pending.world_id !== world || pending.action_id !== action
                  || pending.reservation_sha256 !== exactReview.reservation_sha256 || !pending.apply?.apply_id
                  || savedPage.record?.document_id !== documentId || savedPage.record?.world_id !== world
                  || savedPage.record.revision !== beforeSave.page.body.record.revision + 1
                  || !/^[a-f0-9]{64}$/.test(savedPage.committed_content_sha256 ?? "")) {
                throw waitFailure;
              }
              confirmation.pending_after_save = committed;
              await page.reload();
              await openComposer();
              const check = page.getByRole("region", { name: "Check suggestion insertion", exact: true })
                .getByRole("button", { name: "Check insertion", exact: true });
              await check.waitFor({ timeout: 10000 });
              await check.evaluate((button, binding) => {
                const originalFetch = window.fetch;
                let click = null;
                const requests = [];
                const observeClick = event => {
                  if (event.isTrusted) click = performance.now();
                };
                button.addEventListener("click", observeClick, { capture: true, once: true });
                window.fetch = function(input, init) {
                  if (typeof input === "string" && init?.method === "POST" && typeof init.body === "string") {
                    const url = new URL(input, location.href);
                    if (url.origin === location.origin && url.pathname === binding.path && !url.search) {
                      let command;
                      try { command = JSON.parse(init.body); } catch { /* Preserve the original fetch. */ }
                      if (command?.operation === "confirm" && command.apply_id === binding.applyId
                          && command.expected_revision === binding.revision) {
                        requests.push({ at_ms: performance.now(), after_click: click !== null });
                      }
                    }
                  }
                  return Reflect.apply(originalFetch, this, arguments);
                };
                window.finishBenchmarkCheckInsertion = () => {
                  window.fetch = originalFetch;
                  button.removeEventListener("click", observeClick, true);
                  delete window.finishBenchmarkCheckInsertion;
                  return { click_ms: click, requests };
                };
              }, {path: reviewPath, applyId: pending.apply.apply_id, revision: pending.revision});
              try {
                if (confirmPosts.length !== 0) throw new Error("Confirmation arrived before Check insertion");
                await check.click();
                await pollBrowserRead(() => held || false, 12000, 200, "confirmation response to withhold after Check insertion");
              } finally {
                confirmation.browser_check = await page.evaluate(() => window.finishBenchmarkCheckInsertion());
              }
              const observed = confirmation.browser_check;
              confirmation.retry_exercised = observed.click_ms !== null;
              if (held.request.apply_id !== pending.apply.apply_id
                  || held.request.expected_revision !== pending.revision) {
                throw new Error("Check insertion confirmed a different review");
              }
              const startedAt = confirmRequest?.timing().startTime;
              if (confirmPosts.length === 1) {
                confirmPosts[0].started_at_ms = Number.isFinite(startedAt) && startedAt > 0 ? startedAt : null;
              }
              if (!confirmation.retry_exercised || confirmPosts.length !== 1
                  || observed.requests.length !== 1 || !observed.requests[0].after_click
                  || observed.requests[0].at_ms < observed.click_ms) {
                throw new Error("Confirmation did not follow the explicit Check insertion");
              }
            }
          } finally {
            await page.unroute(exactPath, intercept);
          }
          confirmation.fault_injected = true;
          const saved = held.body.review ?? held.body;
          if (held.status !== 200 || saved.state !== "applied" || saved.action_id !== action
              || saved.world_id !== world || saved.apply?.apply_id !== held.request.apply_id) {
            throw new Error("The withheld response was not a committed confirmation");
          }
          confirmation.afterSave = await readOwners();
          await page.reload();
          await openComposer();
          confirmation.afterReopen = await readOwners();
          const before = confirmation.afterSave;
          const after = confirmation.afterReopen;
          const receiptMatches = observation => {
            const observed = observation.body.review ?? observation.body;
            return observation.status === 200 && observed.state === "applied"
              && observed.action_id === action && observed.world_id === world
              && observed.reservation_sha256 === exactReview.reservation_sha256
              && observed.revision === saved.revision
              && observed.apply?.apply_id === held.request.apply_id;
          };
          const pageMatches = observation => observation.status === 200
            && observation.body.record?.document_id === documentId
            && observation.body.record?.world_id === world
            && /^[a-f0-9]{64}$/.test(observation.body.committed_content_sha256 ?? "");
          const savedRevision = before.page.body.record?.revision;
          const committedBeforeCheck = confirmation.pending_after_save?.page.body;
          confirmation.verified = confirmPosts.length === 1
            && confirmPosts[0].apply_id === held.request.apply_id
            && confirmPosts[0].expected_revision === held.request.expected_revision
            && [beforeSave.page, before.page, after.page].every(pageMatches)
            && receiptMatches(before.review) && receiptMatches(after.review)
            && Number.isInteger(savedRevision)
            && savedRevision === beforeSave.page.body.record.revision + 1
            && savedRevision === after.page.body.record.revision
            && (!committedBeforeCheck || (savedRevision === committedBeforeCheck.record.revision
              && before.page.body.committed_content_sha256 === committedBeforeCheck.committed_content_sha256))
            && before.page.body.committed_content_sha256 === after.page.body.committed_content_sha256;
        } else {
          const confirmed = page.waitForResponse(result => {
            const request = result.request();
            return request.method() === "POST" && new URL(result.url()).pathname === reviewPath
              && request.postDataJSON()?.operation === "confirm";
          }, { timeout: 20000 });
          confirmed.catch(() => {});
          confirmation.attempted = true;
          await review.getByRole("button", { name: "Save", exact: true }).click();
          const receipt = await confirmed;
          confirmation.request = receipt.request().postDataJSON();
          confirmation.status = receipt.status();
          confirmation.body = await receipt.json();
          const saved = confirmation.body.review ?? confirmation.body;
          confirmation.verified = receipt.ok() && saved.state === "applied" && saved.action_id === action
            && saved.world_id === world && saved.apply?.apply_id === confirmation.request.apply_id;
        }
      } catch (error) {
        confirmation.error = String(error);
      }
    }
    writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
      before, after, browserMarks, confirmation, terminal_build_failure: terminalBuildFailure, status: delivered.status(), chromiumVersion: browser.version(),
      playwrightVersion: require(require("node:path").join(process.env.DMB_BENCHMARK_PLAYWRIGHT, "package.json")).version,
      request: delivered.request().postDataJSON(), turnNetworkFailures,
    }, null, 2));
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  console.error(error.stack ?? error.message);
  process.exitCode = 1;
});
