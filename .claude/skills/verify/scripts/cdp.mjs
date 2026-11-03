// A tiny Chrome DevTools Protocol driver with no dependencies (Node 22+ has WebSocket).
// It drives the headless Chrome that launch.sh starts, the way a user would: real mouse
// clicks at an element's centre and real typed text, never React state or test hooks.
//
//   import { connect, APP } from "./cdp.mjs";
//   const page = await connect();
//   await page.goto(APP);
//   await page.click('text=Analyze');
//
// A target is a CSS selector ('[aria-label="Article link"]', '#news') or 'text=Label',
// which matches the first visible button, label or tab whose text is exactly Label.

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

export const APP = "http://localhost:5174/";
const CDP = "http://127.0.0.1:9223";

export function evidenceDir(name) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = join(process.env.TMPDIR ?? tmpdir(), "pnm-verify-evidence", `${stamp}-${name}`);
  mkdirSync(dir, { recursive: true });
  return dir;
}

export async function connect() {
  const pages = await (await fetch(`${CDP}/json/list`)).json();
  const target = pages.find((p) => p.type === "page");
  if (!target) throw new Error("no Chrome page; run launch.sh and doctor.sh");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((ok, fail) => ((ws.onopen = ok), (ws.onerror = fail)));
  let next = 0;
  const waiting = new Map();
  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    const pending = waiting.get(msg.id);
    if (!pending) return;
    waiting.delete(msg.id);
    msg.error ? pending.fail(new Error(`${pending.method}: ${msg.error.message}`)) : pending.ok(msg.result);
  };
  const send = (method, params = {}) =>
    new Promise((ok, fail) => {
      const id = ++next;
      waiting.set(id, { ok, fail, method });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const { result, exceptionDetails } = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
    return result.value;
  };

  const find = (target) =>
    target.startsWith("text=")
      ? `[...document.querySelectorAll('button, label, [role=tab]')].find(e => e.offsetParent !== null && e.textContent.trim() === ${JSON.stringify(target.slice(5))})`
      : `document.querySelector(${JSON.stringify(target)})`;

  const waitFor = async (expression, what, timeout = 30_000) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await new Promise((r) => setTimeout(r, 200));
    }
    throw new Error(`timed out after ${timeout} ms waiting for ${what}`);
  };

  const centre = async (target) => {
    await waitFor(find(target), target);
    return evaluate(`(() => { const e = ${find(target)}; e.scrollIntoView({ block: "center" });
      const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
  };

  const page = {
    send,
    evaluate,
    waitFor,
    async goto(url) {
      await send("Page.enable");
      await send("Page.navigate", { url });
      await waitFor(`document.readyState === "complete" && document.querySelector("#root")?.children.length`, `load ${url}`);
    },
    async click(target) {
      const { x, y } = await centre(target);
      for (const type of ["mousePressed", "mouseReleased"])
        await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
    },
    /** Replace the field's contents the way a user does: click, select all, type. */
    async fill(target, text) {
      await page.click(target);
      await send("Input.dispatchKeyEvent", { type: "rawKeyDown", commands: ["selectAll"] });
      await send("Input.dispatchKeyEvent", { type: "keyUp" });
      if (text) await send("Input.insertText", { text });
      else await send("Input.dispatchKeyEvent", { type: "rawKeyDown", windowsVirtualKeyCode: 8, key: "Backspace" });
    },
    text: (target) => evaluate(`${find(target)}?.innerText ?? null`),
    attr: (target, name) => evaluate(`${find(target)}?.getAttribute(${JSON.stringify(name)}) ?? null`),
    waitForText: (text, timeout) => waitFor(`document.body.innerText.includes(${JSON.stringify(text)})`, `text "${text}"`, timeout),
    async screenshot(dir, name) {
      const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
      const file = join(dir, `${name}.png`);
      writeFileSync(file, Buffer.from(data, "base64"));
      return file;
    },
    close: () => ws.close(),
  };
  return page;
}
