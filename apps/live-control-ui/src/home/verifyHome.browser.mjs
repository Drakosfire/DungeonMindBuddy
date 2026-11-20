/** Production-bundle presentation witness using synthetic session responses only.
 * Run: node src/home/verifyHome.browser.mjs <external-output-directory>
 * Requires the task-owned Vite preview on 127.0.0.1:5187 and installed Chrome.
 */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const output = process.argv[2];
if (!output) throw new Error('External evidence directory required');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome', headless: true, chromiumSandbox: true });
const results = [];
try {
  for (const width of [1440, 768, 390, 320]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' });
    const errors = [];
    const privateCalls = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname;
      if (path !== '/api/auth/session') privateCalls.push(path);
      return route.fulfill({ status: path === '/api/auth/session' ? 401 : 500, contentType: 'application/json', body: JSON.stringify({ status: 'signed_out' }) });
    });
    await page.goto('http://127.0.0.1:5187/');
    await page.getByRole('heading', { name: 'Your world, ready for the table.' }).waitFor();
    await page.locator('.buddy-home__preview img').evaluate(img => img.decode());
    const skip = page.getByRole('link', { name: 'Skip to content' });
    assert.ok((await skip.boundingBox()).y + (await skip.boundingBox()).height <= 0);
    await skip.focus();
    assert.ok((await skip.boundingBox()).y >= 0);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#buddy-home-main').evaluate(el => el === document.activeElement), true);
    await page.goto('http://127.0.0.1:5187/');
    await page.getByRole('heading', { name: 'Your world, ready for the table.' }).waitFor();
    assert.equal(await page.getByRole('link', { name: 'Sign in with DungeonMind' }).getAttribute('href'), '/api/auth/login?return_to=%2F');
    for (const link of await page.getByRole('link', { name: /DungeonMind.net/ }).all()) {
      assert.equal(await link.getAttribute('href'), 'https://www.dungeonmind.net/');
    }
    await page.locator('.buddy-home').screenshot({ path: `${output}/home-${width}.png` });
    await page.getByRole('link', { name: 'Explore the idea' }).click();
    assert.equal(new URL(page.url()).hash, '#buddy-about');
    await page.reload();
    await page.getByRole('heading', { name: 'Your world, ready for the table.' }).waitFor();
    for (const name of ['Old Mill', 'Mara Venn', 'The sealed door', 'From: Session recap']) {
      const trigger = page.getByRole('button', { name, exact: true });
      await trigger.focus();
      await page.keyboard.press('Enter');
      await page.getByRole('region', { name: 'Sample note' }).waitFor();
      assert.equal(await trigger.getAttribute('aria-expanded'), 'true');
      await page.getByRole('button', { name: 'Close note' }).click();
      assert.equal(await trigger.evaluate(el => el === document.activeElement), true);
    }
    await page.locator('.buddy-home__footer').scrollIntoViewIfNeeded();
    await page.locator('.buddy-home').screenshot({ path: `${output}/home-${width}-footer.png` });
    const layout = await page.locator('.buddy-home').evaluate(el => ({ client: el.clientWidth, scroll: el.scrollWidth }));
    assert.ok(layout.scroll <= layout.client + 1, `Home overflows at ${width}: ${JSON.stringify(layout)}`);
    assert.deepEqual(errors, []);
    assert.deepEqual(privateCalls, []);
    const credits = page.getByRole('link', { name: 'Font credits', exact: true });
    const creditsHref = await credits.getAttribute('href');
    assert.match(creditsHref, /^\/assets\/.+-[A-Za-z0-9_-]{8}\.txt$/);
    const notice = await page.request.get(new URL(creditsHref, page.url()).href);
    assert.equal(notice.status(), 200);
    assert.equal(notice.headers()['content-type']?.split(';')[0], 'text/plain');
    const noticeText = await notice.text();
    assert.ok(noticeText.includes('Bookinsanity Remake by Solbera and Ners.'));
    assert.ok(noticeText.includes('https://creativecommons.org/licenses/by-sa/4.0/legalcode'));
    await credits.click();
    await page.waitForURL(url => url.pathname === creditsHref);
    assert.ok((await page.locator('body').innerText()).includes(noticeText.trim()));
    results.push({ width, layout, errors, privateCalls, anchorsAndSamples: 'passed',
      fontCredits: { href: creditsHref, status: notice.status(), readableText: true } });
    await page.close();
  }
  await writeFile(`${output}/browser-results.json`, JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results));
} finally { await browser.close(); }
