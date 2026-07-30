// Measure a page's horizontal overflow at a given viewport width using
// headless Chrome over the DevTools Protocol (CDP).
//
// Usage: node overflow_check.mjs <file-url> <viewport-width>
// Prints two integers: "<scrollWidth> <innerWidth>"
//   scrollWidth > innerWidth  => the page overflows horizontally at this width.
//
// The SVG in flow.html uses width:100% and .stage uses max-width:100%, so
// overflow should never happen; this is a guard, not a workaround.
//
// Connection strategy: launch Chrome pointed at the target URL, then connect
// directly to that page target's webSocketDebuggerUrl (no browser-level WS, no
// sessionId juggling). Commands sent on a target-specific socket are scoped to
// that target automatically.

import { spawn } from 'node:child_process';

const URL = process.argv[2];
const VP = parseInt(process.argv[3], 10);

const CHROME = process.env.CHROME_PATH
  || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9344;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${PORT}`,
  URL,
], { stdio: 'ignore' });

async function getJson(path) {
  const r = await fetch(`http://127.0.0.1:${PORT}${path}`);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`);
  return r.json();
}

async function waitPort() {
  for (let i = 0; i < 50; i++) {
    try { await getJson('/json/version'); return; } catch { await sleep(200); }
  }
  throw new Error('chrome devtools port timeout');
}

async function findPageTarget() {
  for (const path of ['/json/list', '/json']) {
    try {
      const list = await getJson(path);
      const targets = Array.isArray(list) ? list : (list.targets || []);
      for (const t of targets) {
        if (t.type === 'page' && t.webSocketDebuggerUrl) return t;
      }
    } catch {}
  }
  throw new Error('no page target with webSocketDebuggerUrl found');
}

function openWS(url) {
  if (!url || !/^ws:\/\//.test(url)) throw new Error(`invalid ws url: ${url}`);
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.onopen = () => resolve(ws);
    ws.onerror = (e) => reject(e);
  });
}

async function main() {
  await waitPort();
  const target = await findPageTarget();
  const page = await openWS(target.webSocketDebuggerUrl);
  let id = 0; const pend = {};
  page.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend[m.id]) pend[m.id](m);
  };
  const send = (method, params = {}) => new Promise((res) => {
    const i = ++id; pend[i] = res;
    page.send(JSON.stringify({ id: i, method, params }));
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: VP, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await send('Page.navigate', { url: URL });
  await new Promise((resolve) => {
    const onmsg = (e) => {
      const m = JSON.parse(e.data);
      if (m.method === 'Page.loadEventFired') {
        page.removeEventListener('message', onmsg);
        resolve();
      }
    };
    page.addEventListener('message', onmsg);
  });
  await sleep(300);
  const { result: { result: { value } } } = await send('Runtime.evaluate', {
    expression: 'JSON.stringify([document.documentElement.scrollWidth, window.innerWidth])',
  });
  const arr = JSON.parse(value); // value is the JSON-encoded string "[sw,iw]"
  process.stdout.write(arr.join(' '));
  try { page.close(); } catch {}
  chrome.kill('SIGKILL');
  process.exit(0);
}

main().catch((e) => { console.error('overflow_check error:', e.message); process.exit(2); });
