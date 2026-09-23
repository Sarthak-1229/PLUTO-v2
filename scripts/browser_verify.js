// scripts/browser_verify.js
// Real-Chromium verification of the three unverified PLUTO v2 changes:
//   1. LaTeX rendering (markdown-it-texmath + KaTeX)  -> KaTeX DOM, no leakage
//   2. Repetition fix (bounded generation)            -> no line repeated 3+x
//   3. TTS speed split (/process text, /speak audio)  -> text lands before audio
//   4. Voice Mode (Web Speech API)                    -> best-effort + honest
//
// The Playwright headless-shell download failed on this machine, but the FULL
// chromium build is present, so we launch with channel:'chromium' (new headless
// mode) rather than the default (which needs chrome-headless-shell).
//
// Run (server must already be up on :8000):  node scripts/browser_verify.js
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:8000';
const SHOT_DIR = path.join(__dirname, 'verification_screenshots');
fs.mkdirSync(SHOT_DIR, { recursive: true });

// ---- a valid 1s 16kHz mono silent WAV for --use-file-for-fake-audio-capture
function writeSilenceWav(file) {
  const sr = 16000, secs = 1, n = sr * secs;
  const buf = Buffer.alloc(44 + n * 2);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22); buf.writeUInt32LE(sr, 24); buf.writeUInt32LE(sr * 2, 28);
  buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(n * 2, 40); // samples already zero = silence
  fs.writeFileSync(file, buf);
  return file;
}
const WAV = writeSilenceWav(path.join(SHOT_DIR, '_fake_audio.wav'));

const results = [];
function record(name, passed, detail) {
  results.push({ name, passed, detail });
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}\n      ${detail}`);
}

// Submit `text` and wait until a NEW assistant answer bubble (content_*) lands.
// Returns { contentSel, innerText, msToText } or throws on timeout / error bubble.
async function sendAndWait(page, text, timeoutMs) {
  const before = await page.evaluate(() =>
    document.querySelectorAll('[id^="content_"]').length);
  const errBefore = await page.evaluate(() =>
    document.querySelectorAll('.msg-assistant-card').length);

  const t0 = Date.now();
  await page.fill('#userInput', text);
  await page.evaluate(() => handleSend());

  // Wait for either a new answer bubble OR an error/notice card to appear.
  await page.waitForFunction(
    (n) => document.querySelectorAll('[id^="content_"]').length > n
        || !!document.querySelector('.msg-assistant-card[style*="ffdad6"]'),
    before,
    { timeout: timeoutMs, polling: 300 }
  );
  const msToText = Date.now() - t0;

  const err = await page.evaluate(() => {
    const e = document.querySelector('.msg-assistant-card[style*="ffdad6"]');
    return e ? e.innerText : null;
  });
  if (err) throw new Error('assistant error bubble: ' + err.replace(/\s+/g, ' ').trim());

  // Grab the most recently appended content_ element.
  const info = await page.evaluate(() => {
    const els = [...document.querySelectorAll('[id^="content_"]')];
    const el = els[els.length - 1];
    return { id: el.id, innerText: el.innerText, html: el.innerHTML };
  });
  return { id: info.id, innerText: info.innerText, html: info.html, msToText };
}

// Count verbatim repeats of substantial lines (>=15 chars) in rendered text.
function maxLineRepeat(innerText) {
  const counts = {};
  for (const raw of innerText.split('\n')) {
    const line = raw.trim();
    if (line.length < 15) continue;
    counts[line] = (counts[line] || 0) + 1;
  }
  let worst = 0, worstLine = '';
  for (const [line, c] of Object.entries(counts)) {
    if (c > worst) { worst = c; worstLine = line; }
  }
  return { worst, worstLine };
}

// Any backslash-command, math delimiter, or PLUTO_LATEX marker left in the
// VISIBLE text is a real leak: KaTeX keeps raw TeX only in a CSS-hidden
// <annotation>, which innerText excludes — so a rendered formula contributes
// zero backslashes here. A surviving "\cos"/"\frac"/"\(" means it did NOT
// render (bad delimiter config, or a truncation-tail fragment).
function findLeaks(innerText) {
  const m = innerText.match(/\\[a-zA-Z]+|\\[()[\]]|\$\$|PLUTO_LATEX\w*/g);
  return m ? [...new Set(m)] : [];
}

async function main() {
  const browser = await chromium.launch({
    channel: 'chromium',            // full build + new headless (no headless-shell)
    headless: true,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${WAV}`,
      '--autoplay-policy=no-user-gesture-required',
    ],
  });
  const context = await browser.newContext();
  try { await context.grantPermissions(['microphone'], { origin: BASE }); } catch (_) {}
  const page = await context.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('   [browser console.error]', m.text()); });

  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => !!window._plutoMd || !!window.markdownit, null, { timeout: 15000 })
    .catch(() => {});
  const mdEngine = await page.evaluate(() => ({
    plutoMd: !!window._plutoMd,
    texmath: !!window.texmath,
    katex: !!window.katex,
    markdownit: !!window.markdownit,
  }));
  console.log('markdown/katex engine:', JSON.stringify(mdEngine));

  // ---- CHECK 1: LaTeX quadratic formula renders cleanly ----
  // Core requirement: KaTeX renders the formula and NO raw LaTeX leaks. Whether
  // it lands as display vs inline is the model's delimiter choice (\[..\]/$$..$$
  // -> display, \(..\)/$..$ -> inline), so we report it but don't gate on it.
  try {
    const r = await sendAndWait(page, 'show me the quadratic formula as a standalone equation', 120000);
    const dom = await page.evaluate((id) => {
      const el = document.getElementById(id);
      return {
        katex: el.querySelectorAll('.katex').length,
        display: el.querySelectorAll('.katex-display').length,
      };
    }, r.id);
    const leaks = findLeaks(r.innerText);
    const ok = dom.katex > 0 && leaks.length === 0;
    await page.screenshot({ path: path.join(SHOT_DIR, '01_latex_quadratic.png'), fullPage: true });
    record('LaTeX / quadratic renders (no leak)', ok,
      `.katex=${dom.katex} (${dom.display > 0 ? 'display' : 'inline'}) leaks=[${leaks.join(', ')}] ` +
      `(rendered in ${r.msToText}ms) -> 01_latex_quadratic.png`);
  } catch (e) {
    await page.screenshot({ path: path.join(SHOT_DIR, '01_latex_quadratic.png'), fullPage: true }).catch(()=>{});
    record('LaTeX / quadratic renders (no leak)', false, e.message + ' -> 01_latex_quadratic.png');
  }

  // ---- CHECK 1b: LaTeX trig formulas (inline math present, no leakage) ----
  try {
    const r = await sendAndWait(page, 'list all trigonometry formulas', 120000);
    const dom = await page.evaluate((id) => {
      const el = document.getElementById(id);
      return { katex: el.querySelectorAll('.katex').length };
    }, r.id);
    const leaks = findLeaks(r.innerText);
    const ok = dom.katex > 0 && leaks.length === 0;
    await page.screenshot({ path: path.join(SHOT_DIR, '02_latex_trig.png'), fullPage: true });
    record('LaTeX / trigonometry formulas', ok,
      `.katex=${dom.katex} leaks=[${leaks.join(', ')}] -> 02_latex_trig.png`);
  } catch (e) {
    await page.screenshot({ path: path.join(SHOT_DIR, '02_latex_trig.png'), fullPage: true }).catch(()=>{});
    record('LaTeX / trigonometry formulas', false, e.message + ' -> 02_latex_trig.png');
  }

  // ---- CHECK 2: Repetition fix (Trojan War skit) ----
  try {
    const r = await sendAndWait(page, 'create a skit about the Trojan War', 210000);
    const { worst, worstLine } = maxLineRepeat(r.innerText);
    const words = r.innerText.trim().split(/\s+/).length;
    const ok = worst < 3;
    await page.screenshot({ path: path.join(SHOT_DIR, '03_repetition_skit.png'), fullPage: true });
    record('Repetition / Trojan War skit', ok,
      `${words} words, max verbatim line repeat=${worst}` +
      (worst >= 2 ? ` ("${worstLine.slice(0, 50)}")` : '') + ` -> 03_repetition_skit.png`);
  } catch (e) {
    await page.screenshot({ path: path.join(SHOT_DIR, '03_repetition_skit.png'), fullPage: true }).catch(()=>{});
    record('Repetition / Trojan War skit', false, e.message + ' -> 03_repetition_skit.png');
  }

  // ---- CHECK 3: TTS speed split — text lands before audio ----
  // /process returns text only; /speak is fetched separately, so the answer
  // text must appear in the DOM strictly before the audio pill is injected.
  try {
    await page.evaluate(() => { if (typeof saveAutoPlaySetting === 'function') saveAutoPlaySetting(true); });
    const before = await page.evaluate(() => document.querySelectorAll('[id^="content_"]').length);
    const t0 = Date.now();
    await page.fill('#userInput', 'give me a quick answer about the moon');
    await page.evaluate(() => handleSend());

    await page.waitForFunction(n => document.querySelectorAll('[id^="content_"]').length > n,
      before, { timeout: 120000, polling: 200 });
    const msToText = Date.now() - t0;
    const suffix = await page.evaluate(() => {
      const els = [...document.querySelectorAll('[id^="content_"]')];
      return els[els.length - 1].id.replace('content_', '');
    });

    // Wait (bounded) for the audio pill produced by the separate /speak fetch.
    let msToAudio = null;
    try {
      await page.waitForFunction(s => !!document.querySelector('#audioSlot_' + s + ' .audio-pill'),
        suffix, { timeout: 60000, polling: 200 });
      msToAudio = Date.now() - t0;
    } catch (_) { /* /speak slow or tts_unavailable — text was still unblocked */ }

    await page.screenshot({ path: path.join(SHOT_DIR, '04_tts_split.png'), fullPage: true });
    const audioLater = msToAudio === null || msToAudio > msToText;
    const ok = msToText > 0 && audioLater;
    record('TTS split — text before audio', ok,
      `text at ${msToText}ms, audio ` +
      (msToAudio === null ? 'pill did not arrive within 60s (text unaffected)'
                          : `at ${msToAudio}ms (+${msToAudio - msToText}ms after text)`) +
      ` -> 04_tts_split.png`);
  } catch (e) {
    await page.screenshot({ path: path.join(SHOT_DIR, '04_tts_split.png'), fullPage: true }).catch(()=>{});
    record('TTS split — text before audio', false, e.message + ' -> 04_tts_split.png');
  }

  // ---- CHECK 4a: Voice Mode — Web Speech availability + engage (best-effort) ----
  // Honest note: vanilla Chromium has no Google Speech backend, so webkitSpeech
  // Recognition usually cannot return a real transcription headless. We verify
  // the API exists and the UI state machine engages; transcription itself is
  // not asserted (it can't be, reliably, in this build).
  try {
    const api = await page.evaluate(() =>
      ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window));
    await page.click('#voiceModeBtn').catch(() => {});
    await page.waitForTimeout(1500);
    const state = await page.evaluate(() => {
      const btn = document.getElementById('voiceModeBtn');
      const label = document.getElementById('voiceBtnLabel');
      const notice = [...document.querySelectorAll('.msg-assistant-card')]
        .some(e => /internet connection/i.test(e.innerText || ''));
      return { label: label ? label.innerText : '(none)',
               listening: btn ? btn.classList.contains('voice-listening') : false,
               networkNotice: notice };
    });
    await page.screenshot({ path: path.join(SHOT_DIR, '05_voice_online_click.png'), fullPage: true });
    // Best-effort: PASS if the API exists and the toggle produced a coherent
    // reaction (engaged listening OR an honest "needs internet" notice).
    const ok = api && (state.listening || /On|Listening/i.test(state.label) || state.networkNotice);
    record('Voice Mode — API present + toggle reacts', ok,
      `speechAPI=${api} label="${state.label}" listening=${state.listening} ` +
      `networkNotice=${state.networkNotice} -> 05_voice_online_click.png`);
    await page.evaluate(() => { if (typeof stopVoiceMode === 'function') stopVoiceMode(); }).catch(()=>{});
    await page.waitForTimeout(300);
  } catch (e) {
    await page.screenshot({ path: path.join(SHOT_DIR, '05_voice_online_click.png'), fullPage: true }).catch(()=>{});
    record('Voice Mode — API present + toggle reacts', false, e.message + ' -> 05_voice_online_click.png');
  }

  // ---- CHECK 4b: Voice Mode offline gray-out (deterministic) ----
  try {
    await context.setOffline(true);
    await page.evaluate(() => window.dispatchEvent(new Event('offline')));
    await page.waitForTimeout(600);
    const off = await page.evaluate(() => {
      const b = document.getElementById('voiceModeBtn'), m = document.getElementById('micBtn');
      return { vDisabled: b.disabled, vOpacity: b.style.opacity, mDisabled: m.disabled };
    });
    await page.screenshot({ path: path.join(SHOT_DIR, '06_voice_offline_grayout.png'), fullPage: true });

    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await page.waitForTimeout(600);
    const on = await page.evaluate(() => {
      const b = document.getElementById('voiceModeBtn');
      return { vDisabled: b.disabled };
    });
    const ok = off.vDisabled === true && off.mDisabled === true &&
               off.vOpacity === '0.45' && on.vDisabled === false;
    record('Voice Mode — offline gray-out', ok,
      `offline: disabled=${off.vDisabled} opacity=${off.vOpacity} mic=${off.mDisabled}; ` +
      `back online: disabled=${on.vDisabled} -> 06_voice_offline_grayout.png`);
  } catch (e) {
    record('Voice Mode — offline gray-out', false, e.message);
  }

  await browser.close();

  // ---- summary ----
  console.log('\n================ VERIFICATION SUMMARY ================');
  let passN = 0;
  for (const r of results) { console.log(`${r.passed ? 'PASS' : 'FAIL'}  ${r.name}`); passN += r.passed ? 1 : 0; }
  console.log(`\n${passN}/${results.length} checks passed`);
  console.log('Screenshots in scripts/verification_screenshots/');
  process.exit(results.every(r => r.passed) ? 0 : 1);
}

main().catch(err => { console.error('FATAL', err); process.exit(2); });

