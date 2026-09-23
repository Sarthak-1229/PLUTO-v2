// Integration test for the voice-input state machine in ui/index.html.
// It extracts the actual app-controller <script> block from the HTML and runs
// it in Node with stubbed DOM / SpeechRecognition / Audio / fetch, then drives
// the recognizer events to assert the four behaviors. This exercises the REAL
// code from the file (not a copy). A browser is still needed for true audio,
// but this verifies the control flow deterministically.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'ui', 'index.html'), 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const appJs = blocks.find(b => b.includes('function toggleVoiceInput'));
if (!appJs) { console.error('could not find app controller script'); process.exit(2); }

// ---- Stubs -------------------------------------------------------------
const timers = [];
function makeEl(id) {
  const e = {
    id, value: '', innerText: '', innerHTML: '', title: '', disabled: false,
    style: {}, _classes: new Set(),
    appendChild() {}, setAttribute() {}, getAttribute() { return null; },
    querySelectorAll() { return []; }, focus() {}, remove() {},
  };
  e.classList = {
    add: c => e._classes.add(c), remove: c => e._classes.delete(c),
    contains: c => e._classes.has(c), toggle: c => e._classes.has(c) ? e._classes.delete(c) : e._classes.add(c),
  };
  return e;
}
const els = {};
function getEl(id) { if (!els[id]) els[id] = makeEl(id); return els[id]; }

let recog = null;
class FakeRecognition {
  constructor() { this.running = false; recog = this; }
  start() { if (this.running) throw new Error('already started'); this.running = true; if (this.onstart) this.onstart(); }
  stop() { if (this.running) { this.running = false; if (this.onend) this.onend(); } else { if (this.onend) this.onend(); } }
  fireResult(text, isFinal) { this.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal })] }); }
  fireError(err) { this.onerror({ error: err }); }
}

let lastAudio = null;
class FakeAudio {
  constructor(uri) { this.uri = uri; lastAudio = this; }
  play() { if (this.onplay) this.onplay(); return Promise.resolve(); }
  pause() {}
  end() { if (this.onended) this.onended(); }
}

const navigator = { onLine: true };
const listeners = {};
const windowStub = {
  webkitSpeechRecognition: FakeRecognition,
  addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
  scrollTo() {}, MathJax: null, _plutoMd: { render: t => t }, markdownit: null,
  texmath: null, katex: null,
};
const documentStub = {
  getElementById: getEl,
  createElement: () => makeEl('created'),
  querySelectorAll: () => [],
  addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
  body: { scrollHeight: 0 },
};
const localStorageStub = { getItem: () => null, setItem() {}, removeItem() {} };
// Split flow: /process returns text only; /speak returns audio separately.
let processCalls = 0, speakCalls = 0;
function routedFetch(url) {
  if (String(url).includes('/speak')) {
    speakCalls++;
    return Promise.resolve({ ok: true, json: async () => ({ audio_uri: 'data:audio/mpeg;base64,AAAA' }) });
  }
  processCalls++;
  return Promise.resolve({ ok: true, json: async () => ({ answer: 'hello there', answer_source: 'local_model' }) });
}

const sandbox = {
  window: windowStub, document: documentStub, navigator,
  localStorage: localStorageStub, console,
  Audio: FakeAudio,
  fetch: (url) => routedFetch(url),
  setTimeout: (fn, ms) => { const t = { fn, ms }; timers.push(t); return t; },
  clearTimeout: (t) => { const i = timers.indexOf(t); if (i >= 0) timers.splice(i, 1); },
  setInterval: () => 0, clearInterval: () => {},
  alert: (m) => console.log('[alert]', m),
};
sandbox.globalThis = sandbox;
// expose window.x as bare globals the script uses (webkitSpeechRecognition check uses 'in window')
vm.createContext(sandbox);
vm.runInContext(appJs, sandbox);

function flushTimers() { const pending = timers.splice(0); pending.forEach(t => t.fn()); }
async function tick() { for (let i = 0; i < 8; i++) await new Promise(r => setImmediate(r)); }

// ---- Assertions --------------------------------------------------------
let pass = 0, fail = 0;
function check(name, cond) { console.log((cond ? 'PASS ' : 'FAIL ') + name); cond ? pass++ : fail++; }

(async () => {
  const S = sandbox;

  // 1. interim + final config
  check('recognition.continuous = true', recog.continuous === true);
  check('recognition.interimResults = true', recog.interimResults === true);

  // Toggle Voice Mode ON
  S.toggleVoiceInput();
  check('start listening on toggle (running)', recog.running === true);
  check('voiceModeOn button label shows listening/on', ['Listening…','Voice Mode: On'].includes(getEl('voiceBtnLabel').innerText));

  // 1. interim result shows live, does NOT send
  recog.fireResult('what is', false);
  check('interim transcript shown live', getEl('userInput').value === 'what is');

  // final result -> stops capture, dispatches handleSend (which reads then clears input)
  const procBefore = processCalls, speakBefore = speakCalls;
  recog.fireResult('what is two plus two', true);
  check('recognizer stopped while awaiting response', recog.running === false);
  await tick();
  check('final transcript dispatched to /process', processCalls === procBefore + 1);
  // Split flow: audio fetched separately via /speak (autoPlay on by default)
  check('/speak called after text render (autoplay on)', speakCalls === speakBefore + 1);
  check('recognizer NOT restarted at text render (still speaking)', recog.running === false);

  // 3. hands-free: after TTS ends, listening resumes (NOT at text render)
  check('audio created for TTS', !!lastAudio);
  lastAudio.end();               // simulate TTS finished
  flushTimers();                 // restart guard timer
  check('listening auto-resumed after TTS ends', recog.running === true);

  // 2a. no-speech recovery: error then end -> auto restart while voice mode on
  recog.fireError('no-speech');
  recog.stop();                  // onend
  flushTimers();
  check('recovered (restarted) after no-speech', recog.running === true);

  // 2b. network error -> stops voice mode + notice, does not restart
  recog.fireError('network');
  flushTimers();
  check('network error turned voice mode OFF', recog.running === false);

  // Restart for offline test
  navigator.onLine = true;
  S.toggleVoiceInput();
  check('voice mode back on', recog.running === true);

  // 4. offline -> buttons disabled with tooltip, loop stopped
  navigator.onLine = false;
  (listeners['offline'] || []).forEach(fn => fn());
  check('offline disables voice button', getEl('voiceModeBtn').disabled === true);
  check('offline tooltip set', /internet connection/i.test(getEl('voiceModeBtn').title));
  check('offline stops the loop', recog.running === false);

  // toggling while offline shows notice, does not start
  S.toggleVoiceInput();
  check('toggle while offline does not start capture', recog.running === false);

  // back online re-enables
  navigator.onLine = true;
  (listeners['online'] || []).forEach(fn => fn());
  check('online re-enables voice button', getEl('voiceModeBtn').disabled === false);

  // 4. auto-play OFF: no /speak call, loop still resumes, no error
  S.saveAutoPlaySetting(false);
  S.toggleVoiceInput();                 // start voice mode again
  const speakBeforeOff = speakCalls;
  recog.fireResult('another question here', true);
  await tick();
  check('autoplay off: /speak NOT called', speakCalls === speakBeforeOff);
  flushTimers();
  check('autoplay off: loop resumes without audio', recog.running === true);
  S.saveAutoPlaySetting(true);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
