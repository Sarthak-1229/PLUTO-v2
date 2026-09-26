// scripts/verify_responsive.js
// Real-Chromium verification of the two UI fixes:
//   1. Responsive layout — no overlap / no horizontal overflow at 375/600/1200px
//   2. VRAM widget removed — sidebar badge + drawer GPU panel gone, /vram unused,
//      online status preserved (#sidebarOnlineTag), no console errors.
//
// Usage (server up on :8000):  node scripts/verify_responsive.js [before|after]
//   'before' just screenshots the current on-disk UI (used with a git-checkout
//   swap to capture the pre-fix layout). 'after' (default) also runs assertions.
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:8000';
const VARIANT = (process.argv[2] || 'after').toLowerCase();
const WIDTHS = [375, 600, 1200];
const SHOT_DIR = path.join(__dirname, 'verification_screenshots');
fs.mkdirSync(SHOT_DIR, { recursive: true });

const results = [];
const rec = (name, passed, detail) => {
  results.push({ name, passed, detail });
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}\n      ${detail}`);
};

// pixel overlap between two DOMRect-likes (positive area => overlap)
function overlaps(a, b) {
  const ix = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
  const iy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  return ix > 1 && iy > 1;
}

async function main() {
  const browser = await chromium.launch({ channel: 'chromium', headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const pageErrors = [];
  const badResponses = [];   // {url,status} for any 4xx/5xx seen by the page
  const vramRequests = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('request', r => { if (r.url().includes('/vram')) vramRequests.push(r.url()); });
  page.on('response', r => { if (r.status() >= 400) badResponses.push({ url: r.url(), status: r.status() }); });

  for (const w of WIDTHS) {
    await page.setViewportSize({ width: w, height: 820 });
    await page.goto(BASE, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200); // let fonts/layout + one pollStats tick settle
    await page.screenshot({ path: path.join(SHOT_DIR, `${VARIANT}_layout_${w}.png`), fullPage: true });

    if (VARIANT !== 'after') continue;

    const m = await page.evaluate(() => {
      const R = sel => { const e = document.querySelector(sel); return e ? e.getBoundingClientRect() : null; };
      return {
        scrollW: document.documentElement.scrollWidth,
        innerW: window.innerWidth,
        sidebar: R('.app-sidebar'),
        main: R('.app-main'),
        headTitle: R('#headerTitle'),
        headActions: R('.app-header > div:last-child'),
        online: !!document.querySelector('#sidebarOnlineTag'),
        vramGone: ['#sidebarVramPercent', '#sidebarVramFill', '#sidebarVramMb',
                   '#drawerVramText', '#drawerVramFill'].every(s => !document.querySelector(s)),
      };
    });

    const noHScroll = m.scrollW <= m.innerW + 1;
    const sideVsMain = m.sidebar && m.main ? !overlaps(m.sidebar, m.main) : true;
    const headOk = m.headTitle && m.headActions ? !overlaps(m.headTitle, m.headActions) : true;
    const layoutOk = noHScroll && sideVsMain && headOk;

    rec(`[${w}px] no overlap / no horizontal overflow`, layoutOk,
      `scrollW=${m.scrollW} innerW=${m.innerW} noHScroll=${noHScroll} ` +
      `sidebar↔main clear=${sideVsMain} headerTitle↔actions clear=${headOk}`);
    rec(`[${w}px] VRAM widget gone, online status kept`, m.vramGone && m.online,
      `vramElementsAbsent=${m.vramGone} sidebarOnlineTag=${m.online}`);
  }

  if (VARIANT === 'after') {
    // Drawer no longer carries the GPU ALLOCATION panel, but keeps ACTIVE ENGINES.
    await page.setViewportSize({ width: 1200, height: 820 });
    await page.goto(BASE, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await page.evaluate(() => { if (typeof toggleDrawer === 'function') toggleDrawer(); });
    await page.waitForTimeout(500);
    const drawer = await page.evaluate(() => ({
      gpuPanelGone: !document.querySelector('#drawerVramText') && !document.querySelector('#drawerVramFill'),
      activeEngines: [...document.querySelectorAll('*')].some(e => e.textContent.trim() === 'ACTIVE ENGINES'),
    }));
    await page.screenshot({ path: path.join(SHOT_DIR, 'after_drawer_1200.png'), fullPage: true });
    rec('drawer GPU ALLOCATION panel removed (ACTIVE ENGINES kept)',
      drawer.gpuPanelGone && drawer.activeEngines,
      `gpuPanelGone=${drawer.gpuPanelGone} activeEnginesPresent=${drawer.activeEngines} -> after_drawer_1200.png`);

    // /vram endpoint must be gone — checked OUT-OF-PAGE (APIRequestContext) so
    // the probe does not pollute the page's own request/response/error audit.
    const epResp = await context.request.get(BASE + '/vram');
    rec('/vram endpoint removed (server)', epResp.status() === 404 || epResp.status() === 405,
      `GET /vram -> HTTP ${epResp.status()} (expected 404)`);

    rec('UI fires no /vram requests', vramRequests.length === 0,
      vramRequests.length ? `saw: ${vramRequests.join(', ')}` : 'none');

    // Network health: the only tolerated 4xx is the browser's automatic
    // /favicon.ico probe (no favicon link exists — pre-existing, unrelated).
    const realBad = badResponses.filter(r => !/\/favicon\.ico$/.test(r.url));
    const faviconBad = badResponses.filter(r => /\/favicon\.ico$/.test(r.url));
    rec('no broken UI requests (excluding pre-existing favicon)', realBad.length === 0,
      realBad.length ? realBad.map(r => `${r.status} ${r.url}`).join(' | ')
                     : `clean${faviconBad.length ? ` (ignored ${faviconBad.length}x favicon.ico 404)` : ''}`);

    rec('no JavaScript runtime errors', pageErrors.length === 0,
      pageErrors.length ? pageErrors.slice(0, 5).join(' | ') : 'clean');
  }

  await browser.close();

  console.log(`\n================ RESPONSIVE / VRAM-REMOVAL (${VARIANT}) ================`);
  let passN = 0;
  for (const r of results) { console.log(`${r.passed ? 'PASS' : 'FAIL'}  ${r.name}`); passN += r.passed ? 1 : 0; }
  console.log(`\n${passN}/${results.length} checks passed`);
  console.log('Screenshots in scripts/verification_screenshots/');
  process.exit(results.length && results.every(r => r.passed) ? 0 : (VARIANT === 'before' ? 0 : 1));
}

main().catch(err => { console.error('FATAL', err); process.exit(2); });
