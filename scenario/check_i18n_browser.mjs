import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const BASE_URL = (process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000").replace(/\/+$/, "");
const EMAIL = process.env.ADMIN_EMAIL ?? "";
const PASSWORD = process.env.ADMIN_PASSWORD ?? "";
const CHROMIUM = process.env.CHROMIUM_BIN ?? "/usr/bin/chromium";
const PORT = Number(process.env.CHROMIUM_DEBUG_PORT ?? "9223");

if (!EMAIL || !PASSWORD) {
  console.error("ADMIN_EMAIL et ADMIN_PASSWORD sont requis.");
  process.exit(1);
}

const profile = fs.mkdtempSync(path.join(os.tmpdir(), "haccp-i18n-browser-"));
let browser;
let socket;
let nextId = 1;
let failures = 0;
const pending = new Map();

function report(label, ok, detail = "") {
  console.log(`  [${ok ? "OK" : "ÉCHEC"}] ${label}${!ok && detail ? ` — ${detail}` : ""}`);
  if (!ok) {
    failures += 1;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function debuggerPage() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const pages = await response.json();
      const page = pages.find((item) => item.type === "page");
      if (page?.webSocketDebuggerUrl) {
        return page.webSocketDebuggerUrl;
      }
    } catch {
      // Chromium is still starting.
    }
    await sleep(100);
  }
  throw new Error("Chromium n'a pas exposé de page DevTools.");
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.addEventListener("open", () => resolve(ws), { once: true });
    ws.addEventListener("error", reject, { once: true });
    ws.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id && pending.has(message.id)) {
        const { resolve: done, reject: fail } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) {
          fail(new Error(message.error.message));
        } else {
          done(message.result);
        }
      }
    });
  });
}

function send(method, params = {}) {
  const id = nextId;
  nextId += 1;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? "Erreur JavaScript dans le navigateur.");
  }
  return result.result.value;
}

async function waitFor(expression, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) {
      return true;
    }
    await sleep(150);
  }
  return false;
}

async function navigate(url) {
  await send("Page.navigate", { url });
  await waitFor("document.readyState === 'complete'");
}

async function reload() {
  await send("Page.reload", { ignoreCache: true });
  await waitFor("document.readyState === 'complete'");
}

function cleanup() {
  try {
    socket?.close();
  } catch {
    // Best effort.
  }
  try {
    browser?.kill("SIGKILL");
  } catch {
    // Best effort.
  }
  fs.rmSync(profile, { recursive: true, force: true });
}

async function main() {
  browser = spawn(
    CHROMIUM,
    [
      "--headless=new",
      "--no-sandbox",
      "--disable-gpu",
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${profile}`,
      "about:blank",
    ],
    { stdio: "ignore" },
  );
  socket = await connect(await debuggerPage());
  await send("Page.enable");
  await send("Runtime.enable");

  console.log("\n=== Frontend — changement de langue dans le navigateur");

  await navigate(`${BASE_URL}/login`);
  await evaluate(`
    localStorage.setItem("haccpflow.locale", "fr");
    document.cookie = "haccp_locale=fr; path=/; SameSite=Lax";
  `);
  await reload();
  report("connexion initialement en français", (await evaluate("document.documentElement.lang")) === "fr");

  const submitted = await evaluate(`
    (() => {
      const email = document.querySelector("#email");
      const password = document.querySelector("#password");
      const form = document.querySelector("form");
      if (!email || !password || !form) return false;
      email.value = ${JSON.stringify(EMAIL)};
      password.value = ${JSON.stringify(PASSWORD)};
      form.requestSubmit();
      return true;
    })()
  `);
  report("formulaire de connexion soumis", submitted);
  const loggedIn = await waitFor("location.pathname !== '/login'", 20_000);
  report("session navigateur ouverte", loggedIn, await evaluate("location.pathname"));
  if (!loggedIn) {
    throw new Error("Impossible d'ouvrir une session dans le navigateur.");
  }

  // Let React hydrate the server-rendered shell before clicking its controls.
  await sleep(1500);
  const clicked = await evaluate(`
    (() => {
      const button = [...document.querySelectorAll("button")]
        .find((item) => item.textContent?.trim() === "FR / EN");
      if (!button) return false;
      button.click();
      return true;
    })()
  `);
  report("bouton FR / EN trouvé et cliqué", clicked);
  const switched = await waitFor("document.documentElement.lang === 'en'");
  report("passage immédiat en anglais", switched);

  await sleep(1200);
  const state = await evaluate(`({
    lang: document.documentElement.lang,
    cookie: document.cookie,
    stored: localStorage.getItem("haccpflow.locale"),
    text: document.body.innerText,
  })`);
  report("cookie miroir mis à jour", state.cookie.includes("haccp_locale=en"), state.cookie);
  report("localStorage mis à jour", state.stored === "en", String(state.stored));
  report("interface anglaise rendue", /Equipment|Readings|Cleaning/.test(state.text));

  await reload();
  await sleep(1000);
  report(
    "anglais conservé après rechargement",
    (await evaluate("document.documentElement.lang")) === "en" &&
      (await evaluate('localStorage.getItem("haccpflow.locale")')) === "en",
  );

  await evaluate(`
    localStorage.setItem("haccpflow.locale", "fr");
    document.cookie = "haccp_locale=en; path=/; SameSite=Lax";
  `);
  await reload();
  const synchronized = await waitFor(
    `document.documentElement.lang === "fr" &&
     document.cookie.includes("haccp_locale=fr") &&
     localStorage.getItem("haccpflow.locale") === "fr"`,
  );
  report("localStorage resynchronise le cookie au chargement", synchronized);

  if (failures > 0) {
    throw new Error(`${failures} vérification(s) navigateur en échec`);
  }
  console.log("\n  tout est vert");
}

try {
  await main();
} catch (error) {
  console.error(`\nECHEC: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
} finally {
  cleanup();
}
