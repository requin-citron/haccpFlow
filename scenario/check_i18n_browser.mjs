import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const BASE_URL = (process.env.WEB_BASE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
const API_BASE_URL = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
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
const hydrationErrors = [];
let apiToken = "";
let testEquipmentId = "";

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
      } else if (message.method === "Runtime.consoleAPICalled") {
        const text = message.params.args
          .map((arg) => arg.value ?? arg.description ?? "")
          .join(" ");
        if (text.includes("Hydration failed") || text.includes("didn't match")) {
          hydrationErrors.push(text);
        }
      } else if (message.method === "Runtime.exceptionThrown") {
        const text = message.params.exceptionDetails.exception?.description ?? "";
        if (text.includes("Hydration failed") || text.includes("didn't match")) {
          hydrationErrors.push(text);
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

async function clickUntil(selector, condition, attempts = 30) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await evaluate(`document.querySelector(${JSON.stringify(selector)})?.click()`);
    if (await waitFor(condition, 500)) {
      return true;
    }
    await sleep(200);
  }
  return false;
}

async function apiRequest(path, options = {}, token = apiToken) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API ${options.method ?? "GET"} ${path}: ${response.status}`);
  }
  return response;
}

async function loginApi() {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: EMAIL, password: PASSWORD }),
  });
  if (!response.ok) {
    throw new Error(`Connexion API impossible: ${response.status}`);
  }
  const payload = await response.json();
  apiToken = payload.access_token;
}

async function createReadingEquipment() {
  const response = await apiRequest("/api/v1/equipment", {
    method: "POST",
    body: JSON.stringify({
      name: `Frigo navigateur ${Date.now()}`,
      type: "fridge",
      min_temperature_celsius: 0,
      max_temperature_celsius: 4,
    }),
  });
  const equipment = await response.json();
  testEquipmentId = equipment.id;
  return equipment;
}

async function setFormValue(selector, value) {
  return evaluate(`(() => {
    const control = document.querySelector(${JSON.stringify(selector)});
    if (!control) return false;
    const prototype =
      control instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    setter?.call(control, ${JSON.stringify(value)});
    control.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
}

async function cleanup() {
  if (apiToken && testEquipmentId) {
    try {
      await apiRequest(
        `/api/v1/equipment/${testEquipmentId}`,
        { method: "DELETE" },
        apiToken,
      );
    } catch {
      // Best effort: the test equipment is uniquely named.
    }
  }
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
  fs.rmSync(profile, {
    recursive: true,
    force: true,
    maxRetries: 5,
    retryDelay: 100,
  });
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

  console.log("\n=== Frontend — langue, mobile et corrections de température");

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

  await send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 3,
    mobile: true,
  });
  await reload();
  await sleep(1500);

  const mobileState = await evaluate(`(() => {
    const menu = document.querySelector('button[aria-label="Ouvrir le menu"]');
    const sidebar = document.querySelector("aside");
    const visible = (node) => !!node && getComputedStyle(node).display !== "none";
    return {
      menuVisible: visible(menu),
      desktopSidebarHidden: !!sidebar && getComputedStyle(sidebar).display === "none",
      bottomNavigationAbsent:
        document.querySelector('nav[aria-label="Navigation mobile"]') === null,
    };
  })()`);
  report("barre supérieure mobile visible", mobileState.menuVisible);
  report("rail permanent masqué sur mobile", mobileState.desktopSidebarHidden);
  report("bottom navigation absente", mobileState.bottomNavigationAbsent);

  const equipmentCarousel = await evaluate(`(() => {
    const root = document.querySelector("[data-equipment-carousel]");
    if (!root) return null;
    const groups = [...root.querySelectorAll("[data-equipment-group]")];
    return {
      groupCount: groups.length,
      visibleGroups: groups.filter(
        (group) => getComputedStyle(group).display !== "none",
      ).length,
      dotCount: root.querySelectorAll("[data-equipment-dot]").length,
      controlsVisible:
        getComputedStyle(
          root.querySelector("[data-equipment-previous]")?.parentElement?.parentElement ??
            root,
        ).display !== "none",
      statsAbsent: document.querySelector("[data-equipment-stats]") === null,
    };
  })()`);
  report("carrousel Matériel présent", equipmentCarousel !== null);
  if (equipmentCarousel) {
    report(
      "groupes Matériel disponibles",
      equipmentCarousel.groupCount >= 2 && equipmentCarousel.groupCount <= 4,
    );
    report("un seul groupe mobile visible", equipmentCarousel.visibleGroups === 1);
    report(
      "un point par groupe",
      equipmentCarousel.dotCount === equipmentCarousel.groupCount,
    );
    report("contrôles du carrousel visibles", equipmentCarousel.controlsVisible);
    report("statistiques absentes", equipmentCarousel.statsAbsent);

    const nextGroup = await clickUntil(
      "[data-equipment-next]",
      `[...document.querySelectorAll("[data-equipment-dot]")].findIndex(
        (dot) => dot.getAttribute("aria-pressed") === "true",
      ) === 1`,
    );
    report("flèche suivante : groupe 2", nextGroup);

    await evaluate(`
      document.querySelectorAll("[data-equipment-dot]")[
        document.querySelectorAll("[data-equipment-dot]").length - 1
      ]?.click()
    `);
    await waitFor(
      `[...document.querySelectorAll("[data-equipment-dot]")].findIndex(
        (dot) => dot.getAttribute("aria-pressed") === "true",
      ) === document.querySelectorAll("[data-equipment-dot]").length - 1`,
    );
    const looped = await clickUntil(
      "[data-equipment-next]",
      `[...document.querySelectorAll("[data-equipment-dot]")].findIndex(
        (dot) => dot.getAttribute("aria-pressed") === "true",
      ) === 0`,
    );
    report("navigation circulaire dernier → premier", looped);

    const swiped = await evaluate(`(() => {
      const target = document.querySelector("[data-equipment-swipe]");
      if (!target) return false;
      const start = new Event("touchstart", { bubbles: true, cancelable: true });
      Object.defineProperty(start, "touches", {
        value: [{ clientX: 320, clientY: 240 }],
      });
      target.dispatchEvent(start);
      const end = new Event("touchend", { bubbles: true, cancelable: true });
      Object.defineProperty(end, "changedTouches", {
        value: [{ clientX: 120, clientY: 235 }],
      });
      target.dispatchEvent(end);
      return true;
    })()`);
    report(
      "swipe horizontal vers la gauche",
      swiped &&
        (await waitFor(
          `[...document.querySelectorAll("[data-equipment-dot]")].findIndex(
            (dot) => dot.getAttribute("aria-pressed") === "true",
          ) === 1`,
        )),
    );
  }

  await evaluate(`(() => {
    if (document.documentElement.scrollHeight > window.innerHeight + 600) return;
    const spacer = document.createElement("div");
    spacer.dataset.scrollTestSpacer = "true";
    spacer.style.height = "1600px";
    document.body.appendChild(spacer);
  })()`);
  await evaluate("window.scrollTo(0, 500)");
  report(
    "header masqué en descendant",
    await waitFor(
      'document.querySelector("[data-mobile-header]")?.getAttribute("aria-hidden") === "true"',
    ),
  );
  report(
    "header retiré du focus en position masquée",
    (await evaluate(
      'document.querySelector("[data-mobile-header]")?.hasAttribute("inert")',
    )) === true,
  );

  await evaluate("window.scrollTo(0, 420)");
  report(
    "header réaffiché en remontant",
    await waitFor(
      'document.querySelector("[data-mobile-header]")?.getAttribute("aria-hidden") === "false"',
    ),
  );

  await evaluate("window.scrollTo(0, 500)");
  await waitFor(
    'document.querySelector("[data-mobile-header]")?.getAttribute("aria-hidden") === "true"',
  );
  await evaluate("window.scrollTo(0, 0)");
  report(
    "header visible au sommet",
    await waitFor(
      'document.querySelector("[data-mobile-header]")?.getAttribute("aria-hidden") === "false"',
    ),
  );
  await evaluate('document.querySelector("[data-scroll-test-spacer]")?.remove()');

  const drawerOpened = await clickUntil(
    'button[aria-label="Ouvrir le menu"]',
    'document.querySelector("#mobile-navigation-drawer") !== null',
  );
  report("drawer mobile ouvert", drawerOpened);
  await sleep(250);
  const drawerState = await evaluate(`(() => {
    const drawer = document.querySelector("#mobile-navigation-drawer");
    return {
      focusInside: !!drawer && drawer.contains(document.activeElement),
      bodyLocked: document.body.style.overflow === "hidden",
      linkCount: drawer?.querySelectorAll("nav a").length ?? 0,
    };
  })()`);
  report("focus déplacé dans le drawer", drawerState.focusInside);
  report("scroll arrière-plan verrouillé", drawerState.bodyLocked);
  report("navigation complète dans le drawer", drawerState.linkCount > 0);

  await evaluate(
    'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))',
  );
  const drawerClosed = await waitFor(
    'document.querySelector("#mobile-navigation-drawer") === null',
  );
  report("drawer fermé avec Échap", drawerClosed);
  report(
    "scroll restauré après fermeture",
    (await evaluate("document.body.style.overflow")) !== "hidden",
  );

  await clickUntil(
    'button[aria-label="Ouvrir le menu"]',
    'document.querySelector("#mobile-navigation-drawer") !== null',
  );
  const routeTarget = await evaluate(`(() => {
    const links = [...document.querySelectorAll("#mobile-navigation-drawer nav a")];
    const link = links.find((item) => item.getAttribute("href") !== location.pathname);
    if (!link) return null;
    const href = link.getAttribute("href");
    link.click();
    return href;
  })()`);
  report("lien de navigation trouvé", typeof routeTarget === "string" && routeTarget.startsWith("/"));
  if (typeof routeTarget === "string") {
    report(
      "drawer fermé après navigation",
      await waitFor(
        `location.pathname === ${JSON.stringify(routeTarget)} &&
         document.querySelector("#mobile-navigation-drawer") === null`,
        20_000,
      ),
    );
  }

  await loginApi();
  const readingEquipment = await createReadingEquipment();
  await navigate(`${BASE_URL}/readings`);
  const readingCardVisible = await waitFor(
    `document.body.innerText.includes(${JSON.stringify(readingEquipment.name)})`,
    20_000,
  );
  report("matériel de correction affiché sur mobile", readingCardVisible);

  const readingSelector = `[data-equipment-id="${readingEquipment.id}"][data-reading-action="enter"]`;
  const openedReading = await clickUntil(
    readingSelector,
    "document.querySelector('[data-reading-dialog-panel]') !== null",
  );
  report("formulaire de relevé ouvert", openedReading);
  await sleep(250);
  const sheetPosition = await evaluate(`(() => {
    const overlay = document.querySelector("[data-reading-dialog-overlay]");
    const panel = document.querySelector("[data-reading-dialog-panel]");
    if (!overlay || !panel) return null;
    const overlayRect = overlay.getBoundingClientRect();
    const rect = panel.getBoundingClientRect();
    return {
      anchoredBottom: Math.abs(rect.bottom - overlayRect.bottom) < 2,
      leavesTopSpace: rect.top > overlayRect.top,
    };
  })()`);
  report("formulaire mobile en bottom sheet", sheetPosition?.anchoredBottom === true);
  report("bottom sheet laisse voir le fond", sheetPosition?.leavesTopSpace === true);
  report(
    "aucune justification demandée pour une création",
    (await evaluate('document.querySelector("#morning_justification") === null')) === true,
  );

  await setFormValue("#morning_celsius", "2.5");
  await setFormValue("#evening_celsius", "3.5");
  const initialReady = await waitFor(
    '!document.querySelector("[data-reading-form] button[type=submit]")?.disabled',
  );
  report("création matin/soir prête", initialReady);
  await evaluate('document.querySelector("[data-reading-form]")?.requestSubmit()');
  const initialSaved = await waitFor(
    `document.querySelector(${JSON.stringify(
      `[data-equipment-id="${readingEquipment.id}"][data-reading-action="correct"]`,
    )}) !== null && document.querySelector("[data-reading-dialog-panel]") === null`,
    20_000,
  );
  report("création matin/soir enregistrée", initialSaved);

  const correctionSelector = `[data-equipment-id="${readingEquipment.id}"][data-reading-action="correct"]`;
  await clickUntil(
    correctionSelector,
    "document.querySelector('[data-reading-dialog-panel]') !== null",
  );
  await setFormValue("#morning_celsius", "3.5");
  const justificationRevealed = await waitFor(
    'document.querySelector("#morning_justification") !== null',
  );
  report("justification révélée après modification", justificationRevealed);
  const correctionBlocked = await evaluate(`(() => {
    const submit = document.querySelector("[data-reading-form] button[type=submit]");
    const justification = document.querySelector("#morning_justification");
    return {
      submitDisabled: submit?.disabled === true,
      justificationRequired: justification?.required === true,
    };
  })()`);
  report("enregistrement bloqué sans justification", correctionBlocked.submitDisabled);
  report("justification marquée obligatoire", correctionBlocked.justificationRequired);

  await setFormValue("#morning_justification", "Thermomètre mal positionné");
  const correctionReady = await waitFor(
    '!document.querySelector("[data-reading-form] button[type=submit]")?.disabled',
  );
  report("correction prête après justification", correctionReady);
  await evaluate('document.querySelector("[data-reading-form]")?.requestSubmit()');
  const correctionSaved = await waitFor(
    `document.querySelector(${JSON.stringify(
      `[data-equipment-id="${readingEquipment.id}"]`,
    )})?.closest("article")?.querySelector("[data-reading-corrected]") !== null &&
     document.querySelector("[data-reading-dialog-panel]") === null`,
    20_000,
  );
  report("correction enregistrée et badge affiché", correctionSaved);

  const correctionDetails = await evaluate(`(() => {
    const trigger = document.querySelector(${JSON.stringify(
      `[data-equipment-id="${readingEquipment.id}"]`,
    )});
    const article = trigger?.closest("article");
    const details = article?.querySelector("[data-correction-details]");
    if (!details) return null;
    details.open = true;
    return details.innerText;
  })()`);
  report(
    "détail : mesure originale",
    typeof correctionDetails === "string" && correctionDetails.includes("2,5 °C"),
  );
  report(
    "détail : valeur corrigée",
    typeof correctionDetails === "string" && correctionDetails.includes("3,5 °C"),
  );
  report(
    "détail : justification",
    typeof correctionDetails === "string" &&
      correctionDetails.includes("Thermomètre mal positionné"),
  );

  await clickUntil(
    correctionSelector,
    "document.querySelector('[data-reading-dialog-panel]') !== null",
  );
  await setFormValue("#morning_celsius", "3.8");
  await waitFor('document.querySelector("#morning_justification") !== null');
  report(
    "justification précédente reprise pour une nouvelle correction",
    (await evaluate(
      'document.querySelector("#morning_justification")?.value === "Thermomètre mal positionné"',
    )) === true,
  );
  await evaluate(
    'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))',
  );
  await waitFor('document.querySelector("[data-reading-dialog-panel]") === null');

  await reload();
  report(
    "correction conservée après rechargement",
    await waitFor(
      `document.querySelector(${JSON.stringify(
        `[data-equipment-id="${readingEquipment.id}"]`,
      )})?.closest("article")?.querySelector("[data-reading-corrected]") !== null`,
      20_000,
    ),
  );

  await evaluate(`
    localStorage.setItem("haccpflow.locale", "en");
    document.cookie = "haccp_locale=en; path=/; SameSite=Lax";
  `);
  await reload();
  await waitFor('document.documentElement.lang === "en"', 20_000);
  const englishCorrection = await evaluate(`(() => {
    const trigger = document.querySelector(${JSON.stringify(
      `[data-equipment-id="${readingEquipment.id}"]`,
    )});
    const article = trigger?.closest("article");
    return {
      trigger: trigger?.textContent?.trim(),
      badge: article?.querySelector("[data-reading-corrected]")?.textContent?.trim(),
      detail:
        article?.querySelector("[data-correction-details] summary")?.textContent?.trim(),
    };
  })()`);
  report("bouton anglais Correct", englishCorrection.trigger === "Correct");
  report("badge anglais Corrected", englishCorrection.badge === "Corrected");
  report(
    "détail anglais Correction details",
    englishCorrection.detail === "Correction details",
  );

  await evaluate(`
    localStorage.setItem("haccpflow.locale", "fr");
    document.cookie = "haccp_locale=fr; path=/; SameSite=Lax";
  `);
  await navigate(`${BASE_URL}/equipment`);
  await sleep(1000);
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await reload();
  await sleep(1500);
  const desktopEquipment = await evaluate(`(() => {
    const root = document.querySelector("[data-equipment-carousel]");
    if (!root) return null;
    const groups = [...root.querySelectorAll("[data-equipment-group]")];
    return {
      allGroupsVisible:
        groups.length > 0 &&
        groups.every((group) => getComputedStyle(group).display !== "none"),
      controlsHidden:
        !root.querySelector("[data-equipment-previous]") ||
        getComputedStyle(
          root.querySelector("[data-equipment-previous]").parentElement.parentElement,
        ).display === "none",
      statsAbsent: document.querySelector("[data-equipment-stats]") === null,
    };
  })()`);
  if (desktopEquipment) {
    report("tous les groupes Matériel visibles sur desktop", desktopEquipment.allGroupsVisible);
    report("contrôles carrousel masqués sur desktop", desktopEquipment.controlsHidden);
    report("statistiques absentes sur desktop", desktopEquipment.statsAbsent);
  }
  const collapseClicked = await clickUntil(
    'button[aria-label="Réduire la navigation"]',
    'document.querySelector(\'button[aria-label="Développer la navigation"]\') !== null',
  );
  report("sidebar desktop repliée", collapseClicked);
  report(
    "repli desktop mémorisé",
    (await evaluate('localStorage.getItem("haccpflow.sidebar.collapsed")')) === "1",
  );
  await reload();
  await sleep(1000);
  report(
    "repli restauré après rechargement",
    (await evaluate(
      'document.querySelector(\'button[aria-label="Développer la navigation"]\') !== null',
    )) === true,
  );
  report(
    "aucune erreur d'hydratation React",
    hydrationErrors.length === 0,
    hydrationErrors[0] ?? "",
  );

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
  await cleanup();
}
