// Browser journeys in headless Chrome against the running app (http://localhost:3000), from a user's point of view.
// Writes ../results/browser.json and screenshots to ../shots/. Run: node e2e.js [scenario ...]
//
// Sign-up and password-reset emails: the two POSTs that send email (/api/auth/signup, /api/auth/forgot) are
// intercepted and forwarded to the SMTP-less backend on :8010 (same DB and Dragonfly), whose log holds the code / link.
const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const BASE = "http://localhost:3000";
const MAILER = "http://127.0.0.1:8010";
const HERE = path.resolve(__dirname, "..");
const LOG = path.join(HERE, "backend-8010.log");
const SHOTS = path.join(HERE, "shots");
const PY = path.join(HERE, "venv/bin/python");
const DEMO = ["demo@bachat.pk", "demo12345"];
const ADMIN = ["admin@bachat.pk", "admin12345"];
const STAMP = new Date().toISOString().replace(/\D/g, "").slice(4, 14);
const NEW_EMAIL = `e2e-${STAMP}@example.com`;
const NEW_PW = "E2e-browser-1234";
const NEW_PW2 = "E2e-browser-5678";
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 };
fs.mkdirSync(SHOTS, { recursive: true });

const results = [];
let scenario = "?";
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
function check(name, ok, detail = "", warn = false) {
  const status = ok ? "PASS" : warn ? "WARN" : "FAIL";
  results.push({ section: scenario, name, status, detail: String(detail ?? "").slice(0, 400) });
  console.log(`  [${status}] ${name}${!ok && detail ? "  — " + String(detail).slice(0, 220) : ""}`);
  return ok;
}
const redis = (code) => execFileSync(PY, ["-c", `import redis,sys; r=redis.Redis(host='127.0.0.1',port=6380,decode_responses=True); ${code}`]).toString().trim();
const jwtSid = (at) => JSON.parse(Buffer.from(at.split(".")[1], "base64url").toString()).sid;

// ------------------------------------------------------------------------------------------------ harness
let browser;
async function newPage(viewport = DESKTOP, { mail = false } = {}) {
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  await page.setViewport(viewport);
  if (viewport.isMobile)
    await page.setUserAgent("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1");
  page.issues = { console: [], pageerror: [], failed: [], http: [] };
  page.on("console", (m) => { if (m.type() === "error") page.issues.console.push(m.text().slice(0, 200)); });
  page.on("pageerror", (e) => page.issues.pageerror.push(String(e).slice(0, 200)));
  page.on("requestfailed", (r) => {
    const why = r.failure()?.errorText || "";
    // Navigating away aborts the live chat stream and in-flight prefetches; that's normal.
    if (why.includes("ERR_ABORTED") || r.url().includes("/api/chat/stream")) return;
    page.issues.failed.push(`${r.method()} ${r.url().replace(BASE, "")} ${why}`);
  });
  page.on("response", (r) => {
    const u = r.url();
    if (u.startsWith(BASE + "/api/") && r.status() >= 500) page.issues.http.push(`${r.status()} ${u.replace(BASE, "")}`);
  });
  if (mail) {
    await page.setRequestInterception(true);
    page.on("request", async (req) => {
      const u = req.url();
      if (req.method() === "POST" && (u === `${BASE}/api/auth/signup` || u === `${BASE}/api/auth/forgot`)) {
        const res = await fetch(u.replace(BASE, MAILER), { method: "POST", body: req.postData(), headers: { "content-type": "application/json", "x-requested-with": "bachat" } });
        return req.respond({ status: res.status, contentType: "application/json", body: await res.text() });
      }
      req.continue();
    });
  }
  return page;
}
function cleanIssues(page, label, { allowConsole = [] } = {}) {
  const con = page.issues.console.filter((t) => !allowConsole.some((a) => t.includes(a)));
  const all = [...page.issues.pageerror.map((x) => "pageerror: " + x), ...con.map((x) => "console: " + x),
    ...page.issues.failed.map((x) => "failed: " + x), ...page.issues.http.map((x) => "http: " + x)];
  check(`${label}: no JS errors, failed requests or 5xx`, all.length === 0, all.slice(0, 6).join(" | "));
  page.issues = { console: [], pageerror: [], failed: [], http: [] };
}
async function noOverflow(page, label) {
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  return check(`${label}: no sideways scrolling`, o.sw <= o.cw + 1, `scrollWidth ${o.sw} > ${o.cw}`);
}
async function shot(page, name, full = false) {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: full });
}
async function text(page) {
  return page.evaluate(() => document.body.innerText);
}
async function badText(page, label) {
  const t = await text(page);
  const hits = ["NaN", "undefined", "[object Object]", "Infinity", "Rs null"].filter((w) => new RegExp(`(^|\\W)${w.replace(/[[\]]/g, "\\$&")}(\\W|$)`).test(t));
  return check(`${label}: no NaN / undefined / [object Object] on screen`, hits.length === 0, hits.join(", "));
}
async function goto(page, url, until = "networkidle2") {
  return page.goto(BASE + url, { waitUntil: until, timeout: 90000 });
}
async function signInUI(page, email, pw) {
  await goto(page, "/signin");
  await page.waitForSelector('input[name="email"]');
  await page.type('input[name="email"]', email);
  await page.type('input[name="password"]', pw);
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2", timeout: 60000 }).catch(() => {}), page.click('button[type="submit"]')]);
  await page.waitForFunction(() => !location.pathname.startsWith("/signin"), { timeout: 30000 }).catch(() => {});
}
async function visible(page, sel) {
  for (const h of await page.$$(sel)) {
    const b = await h.boundingBox().catch(() => null);
    if (b && b.width > 0 && b.height > 0) return h;
  }
  return null;
}
async function clickVisible(page, sel) {
  const h = await visible(page, sel);
  if (!h) throw new Error(`no visible ${sel}`);
  await h.click();
  return h;
}
async function retype(page, sel, value) {
  const h = await visible(page, sel);
  await h.evaluate((e) => { e.focus(); e.select?.(); });
  await page.keyboard.down("Control"); await page.keyboard.press("a"); await page.keyboard.up("Control");
  await page.keyboard.press("Backspace");
  await page.type(sel, value);
}
async function byText(page, selector, needle) {
  const handles = await page.$$(selector);
  for (const h of handles) {
    if (!(await h.evaluate((e, n) => (e.innerText || e.getAttribute("aria-label") || "").includes(n), needle))) continue;
    const b = await h.boundingBox().catch(() => null);
    if (b && b.width > 0) return h;
  }
  return null;
}
function logAfter(offset, re, timeout = 15000) {
  const end = Date.now() + timeout;
  return new Promise((resolve) => {
    const tick = () => {
      const m = fs.readFileSync(LOG, "utf8").slice(offset).match(re);
      if (m) return resolve(m);
      if (Date.now() > end) return resolve(null);
      setTimeout(tick, 400);
    };
    tick();
  });
}

// ------------------------------------------------------------------------------------------------ scenarios
const scenarios = {
  async landing() {
    for (const [label, vp] of [["laptop", DESKTOP], ["phone", PHONE], ["small phone", { ...PHONE, width: 320, height: 640 }]]) {
      const page = await newPage(vp);
      const t0 = Date.now();
      await goto(page, "/");
      check(`${label}: landing page loads (${Date.now() - t0} ms)`, (await page.title()).length > 0, await page.title());
      await noOverflow(page, `${label} landing`);
      if (label === "laptop") {
        const t = await text(page);
        check("Landing explains the product (How it works, chat, deals)", /How it works/i.test(t) && /deal/i.test(t) && /chat/i.test(t));
        const links = await page.$$eval("a", (as) => as.map((a) => a.getAttribute("href")));
        check("Landing offers Sign up and Sign in", links.includes("/signup") && links.includes("/signin"), links.slice(0, 12));
        const imgs = await page.$$eval("img", (is) => is.filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
        check("No broken images on the landing page", imgs.length === 0, imgs);
        await shot(page, "landing-laptop", true);
        const signup = await byText(page, "a", "Sign up");
        await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), signup.click()]);
        check("'Sign up' leads to the sign-up form", page.url().endsWith("/signup") && !!(await page.$('input[name="full_name"]')), page.url());
      } else await shot(page, `landing-${label.replace(" ", "-")}`, true);
      cleanIssues(page, `${label} landing`);
      await page.browserContext().close();
    }
  },

  async guards() {
    const page = await newPage();
    for (const p of ["/dashboard", "/goals", "/activity", "/admin"]) {
      await goto(page, p);
      await page.waitForFunction(() => location.pathname === "/signin", { timeout: 15000 }).catch(() => {});
      check(`Signed out, ${p} sends you to sign in`, new URL(page.url()).pathname === "/signin", page.url());
    }
    await page.type('input[name="email"]', DEMO[0]);
    await page.type('input[name="password"]', "wrong-password");
    await page.click('button[type="submit"]');
    await wait(1500);
    const t = await text(page);
    check("A wrong password shows a readable error and stays on sign in", /incorrect|invalid|wrong|didn.t match|don.t match/i.test(t) && page.url().includes("/signin"), t.slice(0, 300));
    await shot(page, "signin-wrong-password");
    const forgot = await byText(page, "a", "Forgot");
    check("Sign in links to 'Forgot password'", !!forgot && (await forgot.evaluate((a) => a.getAttribute("href"))) === "/forgot-password");
    cleanIssues(page, "sign-in page", { allowConsole: ["401"] });
    await page.browserContext().close();
  },

  async signup() {
    const page = await newPage(DESKTOP, { mail: true });
    await goto(page, "/signup");
    await page.type('input[name="full_name"]', "Browser Tester");
    await page.type('input[name="email"]', NEW_EMAIL);
    await page.type('input[name="password"]', "short");
    await page.click('button[type="submit"]');
    await wait(600);
    check("A short password is caught before sending", (await page.$('input[name="code"]')) === null);
    await page.$eval('input[name="password"]', (i) => (i.value = ""));
    await page.click('input[name="password"]', { clickCount: 3 });
    await page.keyboard.press("Backspace");
    await page.type('input[name="password"]', NEW_PW);
    const offset = fs.statSync(LOG).size;
    await page.click('button[type="submit"]');
    const codeBox = await page.waitForSelector('input[name="code"]', { timeout: 20000 }).catch(() => null);
    if (!check("After 'Continue' the app asks for the emailed 6-digit code", !!codeBox, await text(page))) return;
    check("The code screen names the address", (await text(page)).includes(NEW_EMAIL));
    await shot(page, "signup-code");
    const m = await logAfter(offset, new RegExp(`email to ${NEW_EMAIL.replace(/[.+]/g, "\\$&")} not sent\\. Subject=(\\d{6})`));
    if (!check("The verification email was produced", !!m)) return;
    await page.type('input[name="code"]', m[1]);
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => location.pathname === "/dashboard", { timeout: 30000 }).catch(() => {});
    check("The right code creates the account and opens the dashboard", new URL(page.url()).pathname === "/dashboard", page.url());
    await page.waitForSelector('[role="dialog"][aria-label="Chat"]', { timeout: 20000 }).catch(() => {});
    await wait(2500);
    const t = await text(page);
    check("New users land with the chat open, asked to connect Gmail first", /gmail/i.test(t) && /connect/i.test(t), t.slice(0, 400));
    await shot(page, "signup-first-dashboard");
    await badText(page, "new user's dashboard");
    cleanIssues(page, "sign-up flow");

    // Forgot password for the same new account, through the UI.
    const p2 = await newPage(DESKTOP, { mail: true });
    await goto(p2, "/forgot-password");
    await p2.type('input[name="email"]', NEW_EMAIL);
    const off2 = fs.statSync(LOG).size;
    await p2.click('button[type="submit"]');
    await p2.waitForFunction(() => /Check your email/i.test(document.body.innerText), { timeout: 15000 }).catch(() => {});
    check("'Forgot password' confirms a link is on its way", /Check your email/i.test(await text(p2)));
    const link = await logAfter(off2, /(http:\/\/localhost:3000\/forgot-password\?token=[\w-]+)/);
    if (!check("The reset email was produced with a link back to the app", !!link)) return;
    await p2.goto(link[1], { waitUntil: "networkidle2" });
    const pw = await p2.$$('input[type="password"]');
    check("The link opens 'Choose a new password'", pw.length === 2 && /Choose a new password/i.test(await text(p2)));
    await pw[0].type(NEW_PW2);
    await pw[1].type(NEW_PW2 + "x");
    await p2.click('button[type="submit"]');
    await wait(500);
    check("Mismatched passwords are caught", /don.t match/i.test(await text(p2)));
    await pw[1].evaluate((e) => { e.focus(); e.select(); });
    await p2.keyboard.press("Backspace");
    await pw[1].type(NEW_PW2);
    await p2.click('button[type="submit"]');
    await p2.waitForFunction(() => location.pathname === "/signin", { timeout: 15000 }).catch(() => {});
    check("Saving the new password returns to sign in", new URL(p2.url()).pathname === "/signin", p2.url());
    const t2 = await text(p2);
    check("Sign in confirms the password was changed", /password (was |has been )?(changed|updated|reset)|new password/i.test(t2), t2.slice(0, 200), true);
    await shot(p2, "reset-back-to-signin");
    await p2.type('input[name="email"]', NEW_EMAIL);
    await p2.type('input[name="password"]', NEW_PW2);
    await Promise.all([p2.waitForNavigation({ waitUntil: "networkidle2" }).catch(() => {}), p2.click('button[type="submit"]')]);
    await p2.waitForFunction(() => location.pathname === "/dashboard", { timeout: 20000 }).catch(() => {});
    check("The new password signs in", new URL(p2.url()).pathname === "/dashboard", p2.url());
    await page.reload({ waitUntil: "networkidle2" });
    await wait(1500);
    check("The reset signed out the other browser", new URL(page.url()).pathname === "/signin", page.url());
    cleanIssues(p2, "password reset flow", { allowConsole: ["401"] });
    await page.browserContext().close();
    await p2.browserContext().close();
  },

  async dashboard() {
    const page = await newPage(DESKTOP);
    const t0 = Date.now();
    await signInUI(page, ...DEMO);
    check(`Demo signs in and lands on the dashboard (${Date.now() - t0} ms)`, new URL(page.url()).pathname === "/dashboard", page.url());
    await page.waitForSelector("#home", { timeout: 30000 });
    await wait(1500);
    const ids = await page.$$eval("[data-section]", (els) => els.map((e) => e.id).filter(Boolean));
    check("Dashboard shows Home, Goals, Spending, Banks and Deals", ["home", "goals", "spending", "banks", "deals"].every((i) => ids.includes(i)), ids);
    const api = await page.evaluate(async () => (await fetch("/api/dashboard")).json());
    const t = await text(page);
    check("Bank names from the account appear on screen", api.banks.every((b) => t.includes(b.bank) || t.includes(b.bank_short || "@@")), api.banks.map((b) => b.bank));
    const activeGoals = api.goals.filter((g) => g.status === "active");
    check("Active goal names appear on screen", activeGoals.every((g) => t.includes(g.name)), activeGoals.map((g) => g.name));
    check("Monthly cards are labelled per month, not per week", /this month|month/i.test(t) && !/saved this week/i.test(t));
    await badText(page, "dashboard");
    await noOverflow(page, "dashboard");
    await shot(page, "dashboard-laptop", true);
    cleanIssues(page, "dashboard");

    // Goal details
    const goalLink = await visible(page, 'a[href^="/goals/"]');
    if (check("Goals link to their detail page", !!goalLink)) {
      await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), goalLink.click()]);
      await page.waitForSelector("h1", { timeout: 15000 });
      const gt = await text(page);
      check("Goal details show the name, progress and history", /History/.test(gt) && api.goals.some((g) => gt.includes(g.name)), gt.slice(0, 200));
      await badText(page, "goal details");
      await shot(page, "goal-details", true);
      cleanIssues(page, "goal details");
      await goto(page, `/goals/00000000-0000-0000-0000-000000000000`);
      await wait(2000);
      await shot(page, "goal-unknown");
      check("An unknown goal shows a friendly not-found message", /not found|could not be found|doesn.t exist|couldn.t find|no longer/i.test(await text(page)), (await text(page)).slice(0, 200), true);
      page.issues = { console: [], pageerror: [], failed: [], http: [] };
    }

    // Bank modal
    await goto(page, "/dashboard");
    await page.waitForSelector("#banks button[aria-label$='details']");
    await page.evaluate(() => document.getElementById("banks").scrollIntoView({ block: "start" }));
    await wait(600);
    const y0 = await page.evaluate(() => Math.round(window.scrollY));
    await clickVisible(page, "#banks button[aria-label$='details']");
    const modal = await page.waitForSelector('[role="dialog"][aria-modal="true"]', { timeout: 10000 }).catch(() => null);
    await wait(700);
    if (check("Tapping a bank opens its details", !!modal)) {
      const mt = await modal.evaluate((e) => e.innerText);
      check("Bank details list balance, cards and recent transactions", /balance/i.test(mt) && /(Money in|Money out|transactions?|Recent)/i.test(mt + (await modal.evaluate((e) => e.innerHTML))), mt.slice(0, 200));
      check("The page behind doesn't jump when the bank modal opens", Math.abs((await page.evaluate(() => Math.round(window.scrollY))) - y0) <= 2);
      await shot(page, "bank-modal");
      await page.keyboard.press("Escape");
      await wait(500);
      check("Escape closes the bank details", !(await page.$('[role="dialog"][aria-modal="true"]')));
    }

    // Settings sheet + theme
    await clickVisible(page, 'button[aria-label="Account and settings"]');
    const sheet = await page.waitForSelector('[role="dialog"]', { timeout: 10000 }).catch(() => null);
    await wait(600);
    if (check("Settings open from the avatar", !!sheet)) {
      const st = await text(page);
      check("Settings offer Gmail connection, fingerprint/face, appearance and sign out", /Gmail|email/i.test(st) && /fingerprint|face/i.test(st) && !!(await page.$('[role="radiogroup"][aria-label="Appearance"]')) && /Sign out/.test(st));
      await shot(page, "settings");
      const dark = await byText(page, '[role="radio"]', "Dark");
      if (dark) {
        await dark.click();
        await wait(500);
        check("Dark mode switches the whole app", (await page.evaluate(() => document.documentElement.dataset.theme)) === "dark");
        await page.keyboard.press("Escape");
        await wait(400);
        await shot(page, "dashboard-dark", true);
        await clickVisible(page, 'button[aria-label="Account and settings"]');
        await wait(500);
        await (await byText(page, '[role="radio"]', "Light")).click();
        await wait(300);
        check("…and back to light", (await page.evaluate(() => document.documentElement.dataset.theme)) !== "dark");
      }
      await page.keyboard.press("Escape");
    }
    cleanIssues(page, "bank modal & settings");

    // PWA bits
    const sw = await page.evaluate(async () => !!(await navigator.serviceWorker?.getRegistration()));
    check("The service worker is registered (installable, offline shell)", sw);
    // Truly offline: the page's network and the service worker's (page-level emulation alone doesn't reach the SW).
    const swTarget = await browser.waitForTarget((t) => t.type() === "service_worker", { timeout: 10000 }).catch(() => null);
    const swCdp = swTarget && (await swTarget.createCDPSession());
    const cond = (offline) => ({ offline, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    if (swCdp) { await swCdp.send("Network.enable"); await swCdp.send("Network.emulateNetworkConditions", cond(true)); }
    await page.setOfflineMode(true);
    await page.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
    await wait(1500);
    const off = await text(page).catch(() => "");
    check("Offline, the app shows its own offline page", /offline/i.test(off) && !/ERR_INTERNET_DISCONNECTED/i.test(off), off.slice(0, 160));
    await shot(page, "offline");
    if (swCdp) await swCdp.send("Network.emulateNetworkConditions", cond(false));
    await page.setOfflineMode(false);
    page.issues = { console: [], pageerror: [], failed: [], http: [] };

    // Signed-in guard behaviour
    await goto(page, "/signin");
    await page.waitForFunction(() => location.pathname === "/dashboard", { timeout: 10000 }).catch(() => {});
    check("Signed in, /signin sends you to the dashboard", new URL(page.url()).pathname === "/dashboard", page.url());
    await goto(page, "/admin");
    await page.waitForFunction(() => location.pathname === "/dashboard", { timeout: 10000 }).catch(() => {});
    check("A regular user can't open the admin console", new URL(page.url()).pathname === "/dashboard", page.url());
    await goto(page, "/");
    const lt = await text(page);
    check("The landing page knows you're signed in (Dashboard button)", /Dashboard/.test(lt));
    scenarios._demoPage = page;
  },

  async chat() {
    const page = scenarios._demoPage || (await (async () => { const p = await newPage(DESKTOP); await signInUI(p, ...DEMO); return p; })());
    await goto(page, "/dashboard");
    await clickVisible(page, 'button[aria-label^="Open chat"]');
    const dlg = await page.waitForSelector('[role="dialog"][aria-label="Chat"]', { timeout: 10000 }).catch(() => null);
    if (!check("The chat opens from the chat button", !!dlg)) return;
    await wait(2500);
    const ct = await dlg.evaluate((e) => e.innerText);
    check("Chat shows the advisors by name", /Finance Assistant/.test(ct) && /Savings Coach/.test(ct) && /Deals Advisor/.test(ct), ct.slice(0, 200));
    check("Earlier conversation is shown", ct.length > 200, ct.length);
    await shot(page, "chat-open");
    const q = "What is my total balance across all my banks? One short sentence please.";
    await page.type('textarea[aria-label="Message"]', q);
    const t0 = Date.now();
    await clickVisible(page, 'button[aria-label="Send"]');
    await page.waitForFunction((q) => document.querySelector('[role="dialog"][aria-label="Chat"]').innerText.includes(q), { timeout: 10000 }, q).catch(() => {});
    check("My message appears in the chat at once", (await dlg.evaluate((e) => e.innerText)).includes(q));
    const locked = await page.$eval('textarea[aria-label="Message"]', (t) => t.disabled || t.readOnly).catch(() => null);
    const sendDisabled = await page.$eval('button[aria-label="Send"]', (b) => b.disabled).catch(() => null);
    check("Input is locked while the assistant replies", locked === true || sendDisabled === true, `textarea locked=${locked} send disabled=${sendDisabled}`);
    const typing = await page.waitForSelector('[aria-label="Assistant is typing"]', { timeout: 30000 }).then(() => true).catch(() => false);
    check("A typing / progress indicator shows while it works", typing, "", true);
    await shot(page, "chat-thinking");
    // With an empty box the app shows the mic instead of Send, so "unlocked" = the textarea is enabled again.
    const done = await page.waitForFunction(() => {
      const t = document.querySelector('textarea[aria-label="Message"]');
      return t && !t.disabled && !document.querySelector('[aria-label="Assistant is typing"]');
    }, { timeout: 240000, polling: 500 }).then(() => true).catch(() => false);
    const secs = Math.round((Date.now() - t0) / 1000);
    const after = await dlg.evaluate((e) => e.innerText);
    const reply = after.split(q).pop().trim();
    check(`The assistant replies and the input unlocks (${secs} s)`, done && reply.length > 10, reply.slice(0, 300));
    results[results.length - 1].detail = `${secs}s: ${reply.slice(0, 300)}`;
    const api = await page.evaluate(async () => (await fetch("/api/dashboard")).json());
    const total = Math.round(Number(api.total_balance));
    const digits = reply.replace(/[,\s]/g, "");
    const lac = (total / 100000).toFixed(2).replace(/0$/, "");
    check(`The reply quotes the real total balance (Rs ${total.toLocaleString("en-PK")})`, digits.includes(String(total)) || reply.includes(lac) || reply.includes((total / 100000).toFixed(1)), reply.slice(0, 200), true);
    await shot(page, "chat-replied");
    // Voice note via Chrome's fake microphone (plays fixtures/english.wav)
    const mic = await page.$('button[aria-label^="Record a voice message"]');
    if (check("There is a voice-note button", !!mic)) {
      await mic.click();
      await wait(6500);
      const stop = await page.$('button[aria-label="Stop recording"]');
      check("Recording starts (Stop button shown)", !!stop);
      if (stop) await stop.click();
      const got = await page.waitForFunction(() => (document.querySelector('textarea[aria-label="Message"]')?.value || "").trim().length > 3, { timeout: 120000 }).then(() => true).catch(() => false);
      const val = await page.$eval('textarea[aria-label="Message"]', (t) => t.value).catch(() => "");
      check("The voice note becomes editable text in the message box (not sent automatically)", got && !(await dlg.evaluate((e, v) => e.innerText.split("\n").includes(v), val)), val);
      results[results.length - 1].detail = JSON.stringify(val);
      await shot(page, "chat-voice-text");
      await page.$eval('textarea[aria-label="Message"]', (t) => { t.select(); });
      await page.keyboard.press("Backspace");
    }
    await clickVisible(page, 'button[aria-label="Close chat"]').catch(() => {});
    cleanIssues(page, "chat", { allowConsole: ["Permissions policy"] });
  },

  async lock() {
    const page = scenarios._demoPage || (await (async () => { const p = await newPage(DESKTOP); await signInUI(p, ...DEMO); return p; })());
    await goto(page, "/dashboard");
    const at = (await page.cookies()).find((c) => c.name === "at").value;
    redis(`print(r.delete('sess:${jwtSid(at)}:active'))`); // what 5 idle minutes do on the server
    await page.reload({ waitUntil: "networkidle2" });
    await wait(1500);
    let pw = await page.$('input[type="password"]');
    const t = await text(page);
    check("After 5 idle minutes the app shows the lock screen", !!pw && !/Total balance/i.test(t), t.slice(0, 200));
    await shot(page, "lock-screen");
    await goto(page, "/");
    check("The landing page itself is never covered by the lock screen", !(await page.$('input[type="password"]')));
    await goto(page, "/dashboard");
    await wait(1000);
    pw = await visible(page, 'input[type="password"]');
    check("…but heading back into the app asks to unlock", !!pw);
    await page.type('input[type="password"]', "wrong-password");
    await page.keyboard.press("Enter");
    await wait(1200);
    check("A wrong password doesn't unlock", !!(await page.$('input[type="password"]')) && /incorrect|wrong|invalid|didn.t match|don.t match/i.test(await text(page)), (await text(page)).slice(0, 200));
    await shot(page, "lock-wrong-password");
    await retype(page, 'input[type="password"]', DEMO[1]);
    await page.keyboard.press("Enter");
    const back = await page.waitForSelector("#home", { timeout: 15000 }).then(() => true).catch(() => false);
    check("The right password unlocks straight back into the dashboard", back);
    cleanIssues(page, "lock screen", { allowConsole: ["423", "401"] });
    // Sign out
    await clickVisible(page, 'button[aria-label="Account and settings"]');
    await wait(600);
    const so = await byText(page, "button", "Sign out");
    await so.click();
    await page.waitForFunction(() => location.pathname === "/signin", { timeout: 10000 }).catch(() => {});
    check("Sign out returns to sign in", new URL(page.url()).pathname === "/signin", page.url());
    await goto(page, "/dashboard");
    await page.waitForFunction(() => location.pathname === "/signin", { timeout: 10000 }).catch(() => {});
    check("After sign out the dashboard is closed", new URL(page.url()).pathname === "/signin", page.url());
    await page.browserContext().close();
  },

  async phone() {
    const page = await newPage(PHONE);
    await signInUI(page, ...DEMO);
    await page.waitForSelector("#home", { timeout: 30000 });
    await wait(1500);
    await noOverflow(page, "phone dashboard");
    await shot(page, "phone-home", true);
    const nav = await page.$$eval('nav[aria-label="Dashboard sections"] a', (as) => as.filter((a) => a.offsetParent).map((a) => [a.innerText.trim(), a.getAttribute("href")]));
    check("Phone bottom bar has Goals · Spending · Home · Deals · Activity", JSON.stringify(nav.map((n) => n[0])) === JSON.stringify(["Goals", "Spending", "Home", "Deals", "Activity"]), JSON.stringify(nav));
    for (const [label, href] of nav) {
      const link = await visible(page, `nav[aria-label="Dashboard sections"] a[href="${href}"]`);
      await link.tap();
      await page.waitForFunction((h) => location.pathname === h, { timeout: 10000 }, href).catch(() => {});
      await wait(1800); // page transition
      const ok = new URL(page.url()).pathname === href;
      const t = await text(page);
      check(`Phone: '${label}' opens ${href} with content`, ok && t.length > 150, `${page.url()} chars=${t.length}`);
      await noOverflow(page, `phone ${label}`);
      await badText(page, `phone ${label}`);
      const active = await (await visible(page, `nav[aria-label="Dashboard sections"] a[href="${href}"]`))?.evaluate((a) => a.getAttribute("aria-current"));
      check(`Phone: '${label}' is highlighted in the bottom bar`, active === "page", active);
      await shot(page, `phone-${label.toLowerCase()}`, true);
    }
    cleanIssues(page, "phone pages");
    await goto(page, "/dashboard");
    await clickVisible(page, 'button[aria-label^="Open chat"]');
    const dlg = await page.waitForSelector('[role="dialog"][aria-label="Chat"]', { timeout: 10000 }).catch(() => null);
    await wait(1200);
    if (check("Phone: chat opens", !!dlg)) {
      const box = await dlg.boundingBox();
      check("Phone: chat fills the screen", box && box.width >= PHONE.width - 2 && box.height >= PHONE.height * 0.85, JSON.stringify(box));
      await shot(page, "phone-chat");
      await clickVisible(page, 'button[aria-label="Close chat"]');
    }
    await clickVisible(page, 'button[aria-label="Account and settings"]');
    await wait(800);
    await shot(page, "phone-settings");
    await noOverflow(page, "phone settings");
    cleanIssues(page, "phone chat & settings");
    await page.browserContext().close();
  },

  async admin() {
    const page = await newPage(DESKTOP);
    await signInUI(page, ...ADMIN);
    await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 15000 }).catch(() => {});
    check("Admin signs in straight to the admin console", new URL(page.url()).pathname === "/admin", page.url());
    for (const p of ["/admin", "/admin/users", "/admin/agents", "/admin/plans", "/admin/deals", "/admin/companies", "/admin/banks", "/admin/cards", "/admin/assets", "/admin/watchlists"]) {
      await goto(page, p);
      await wait(1200);
      const t = await text(page);
      check(`${p} renders with data`, new URL(page.url()).pathname === p && t.length > 200 && !/Something went wrong|Application error/i.test(t), `${page.url()} chars=${t.length}`);
      await badText(page, p);
      await shot(page, `admin-${p.split("/")[2] || "overview"}`);
      cleanIssues(page, p);
    }
    const t = await (goto(page, "/admin/users").then(() => wait(1000)).then(() => text(page)));
    check("Admin user list shows the demo user but not admins", t.includes(DEMO[0]) && !t.includes(ADMIN[0]));
    await goto(page, "/dashboard");
    await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 10000 }).catch(() => {});
    check("Admins can't open the personal dashboard", new URL(page.url()).pathname.startsWith("/admin"), page.url());
    await page.browserContext().close();
  },
  async signupchat() {
    // Does a brand-new account land with the chat open (/dashboard?chat=1), as the sign-up page intends?
    const page = await newPage(DESKTOP, { mail: true });
    const urls = [];
    page.on("framenavigated", (f) => { if (f === page.mainFrame()) urls.push(f.url().replace(BASE, "")); });
    await page.evaluateOnNewDocument(() => {
      const log = (u) => { (window.__nav = window.__nav || []).push(String(u)); };
      const wrap = (k) => { const o = history[k].bind(history); history[k] = (st, t, u) => { log(u); return o(st, t, u); }; };
      wrap("pushState"); wrap("replaceState");
    });
    const email = `e2e-${STAMP}9@example.com`;
    await goto(page, "/signup");
    await page.type('input[name="full_name"]', "Chat Probe");
    await page.type('input[name="email"]', email);
    await page.type('input[name="password"]', NEW_PW);
    const offset = fs.statSync(LOG).size;
    await page.click('button[type="submit"]');
    await page.waitForSelector('input[name="code"]', { timeout: 20000 });
    const m = await logAfter(offset, new RegExp(`email to ${email.replace(/[.+]/g, "\\$&")} not sent\\. Subject=(\\d{6})`));
    await page.type('input[name="code"]', m[1]);
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => location.pathname === "/dashboard", { timeout: 30000 }).catch(() => {});
    await wait(5000);
    const chatOpen = !!(await visible(page, '[role="dialog"][aria-label="Chat"]'));
    const hist = await page.evaluate(() => window.__nav || []);
    check("After sign-up the dashboard opens with the chat open (?chat=1)", chatOpen, `chat open=${chatOpen}; client-side URL changes: ${JSON.stringify(hist)}; final ${page.url().replace(BASE, "")}`);
    await shot(page, "signup-landing-chat");
    page.issues = { console: [], pageerror: [], failed: [], http: [] };
    await page.browserContext().close();
  },

  async passkey() {
    // Fingerprint / face via Chrome's virtual authenticator: turn it on in Settings, unlock with it, sign in with it.
    const page = await newPage(DESKTOP);
    const cdp = await page.target().createCDPSession();
    await cdp.send("WebAuthn.enable");
    await cdp.send("WebAuthn.addVirtualAuthenticator", { options: { protocol: "ctap2", transport: "internal", hasResidentKey: true,
      hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } });
    await signInUI(page, ...DEMO);
    await page.waitForSelector("#home", { timeout: 30000 });
    const creds = () => page.evaluate(async () => (await fetch("/api/auth/webauthn/credentials")).json());
    const before = await creds();
    let added = [];
    try {
      await clickVisible(page, 'button[aria-label="Account and settings"]');
      await wait(700);
      const btn = await byText(page, "button", "fingerprint / face");
      if (!check("Settings offer to turn on fingerprint / face", !!btn)) return;
      await btn.click();
      await wait(4000);
      const after = await creds();
      added = after.filter((c) => !before.some((b) => b.id === c.id));
      check("Turning it on registers a passkey for this device", added.length === 1, JSON.stringify(after));
      await shot(page, "passkey-registered");
      await page.keyboard.press("Escape");
      const at = (await page.cookies()).find((c) => c.name === "at").value;
      redis(`r.delete('sess:${jwtSid(at)}:active')`);
      await page.reload({ waitUntil: "networkidle2" });
      const unlocked = await page.waitForSelector("#home", { timeout: 20000 }).then(() => true).catch(() => false);
      check("A locked app unlocks with fingerprint / face, no password typed", unlocked, (await text(page)).slice(0, 160));
      await clickVisible(page, 'button[aria-label="Account and settings"]');
      await wait(600);
      await (await byText(page, "button", "Sign out")).click();
      await page.waitForFunction(() => location.pathname === "/signin", { timeout: 10000 }).catch(() => {});
      const fp = await byText(page, "button", "Fingerprint or face");
      if (check("Sign in offers 'Fingerprint or face'", !!fp)) {
        await fp.click();
        await page.waitForFunction(() => location.pathname === "/dashboard", { timeout: 20000 }).catch(() => {});
        check("Fingerprint or face signs in without email or password", new URL(page.url()).pathname === "/dashboard", page.url());
      }
      cleanIssues(page, "passkeys", { allowConsole: ["423", "401"] });
    } finally {
      // Leave the demo account as it was.
      if (new URL(page.url()).pathname !== "/dashboard") await signInUI(page, ...DEMO);
      for (const c of added) await page.evaluate(async (id) => fetch(`/api/auth/webauthn/credentials/${id}`, { method: "DELETE", headers: { "x-requested-with": "bachat" } }), c.id);
      const left = await creds();
      check("Test passkey removed again afterwards", left.length === before.length, JSON.stringify(left));
      await page.browserContext().close();
    }
  },
  async a11y() {
    // axe-core scan of the main screens; only critical / serious issues are reported (as warnings).
    const axe = fs.readFileSync(path.join(__dirname, "node_modules/axe-core/axe.min.js"), "utf8");
    const scan = async (page, label) => {
      await page.addScriptTag({ content: axe });
      const res = await page.evaluate(async () => (await window.axe.run(document, { resultTypes: ["violations"] })).violations
        .filter((v) => ["critical", "serious"].includes(v.impact)).map((v) => `${v.id} (${v.impact}) ×${v.nodes.length}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(", ")}`));
      check(`${label}: no critical / serious accessibility issues`, res.length === 0, res.join(" | "), true);
    };
    const anon = await newPage(DESKTOP);
    for (const p of ["/", "/signin", "/signup"]) { await goto(anon, p); await scan(anon, p); }
    await anon.browserContext().close();
    const page = await newPage(DESKTOP);
    await signInUI(page, ...DEMO);
    await page.waitForSelector("#home", { timeout: 30000 });
    await wait(1500);
    await scan(page, "/dashboard");
    await clickVisible(page, 'button[aria-label^="Open chat"]');
    await wait(2500);
    await scan(page, "chat panel");
    await page.browserContext().close();
  },
  async chatidle() {
    // An advisor's turn that ends with "idle" but no message (it thought, then chose not to answer). Replays exactly
    // those two live events on the person's chat channel and watches the input.
    const page = await newPage(DESKTOP);
    await signInUI(page, ...DEMO);
    await page.waitForSelector("#home", { timeout: 30000 });
    await clickVisible(page, 'button[aria-label^="Open chat"]');
    await page.waitForSelector('textarea[aria-label="Message"]', { timeout: 10000 });
    await wait(2500);
    const uid = JSON.parse(Buffer.from((await page.cookies()).find((c) => c.name === "at").value.split(".")[1], "base64url").toString()).sub;
    const pub = (state) => redis(`import json; r.publish('chat:${uid}', json.dumps({"type": "activity", "activity": {"state": "${state}", "thinking": "", "tool": None, "sender": "Savings Coach"}}))`);
    const locked = () => page.$eval('textarea[aria-label="Message"]', (t) => t.disabled);
    check("Before: the input is free", (await locked()) === false);
    pub("thinking");
    await wait(1500);
    check("While an advisor is thinking, the input locks", (await locked()) === true);
    pub("idle");
    await wait(3000);
    const still = await locked();
    await shot(page, "chat-stuck-after-idle");
    check("When that advisor finishes without a message, the input unlocks again", still === false, "input still locked 3 s after the turn ended (idle)");
    if (still) {
      const t0 = Date.now();
      await page.waitForFunction(() => !document.querySelector('textarea[aria-label="Message"]').disabled, { timeout: 150000, polling: 1000 }).catch(() => {});
      const secs = Math.round((Date.now() - t0) / 1000) + 3;
      const msg = (await text(page)).match(/taking longer than usual[^\n]*/i);
      results.push({ section: scenario, name: "…it only unlocks via the silence fallback", status: "INFO", detail: `after ~${secs} s, showing: ${msg ? msg[0] : "(no message)"}` });
      console.log(`  [INFO] unlocked after ~${secs} s: ${msg ? msg[0] : ""}`);
      await shot(page, "chat-after-fallback");
    }
    await page.browserContext().close();
  },
};

(async () => {
  browser = await puppeteer.launch({
    executablePath: "/usr/bin/google-chrome", headless: true, protocolTimeout: 600000,
    args: ["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
      `--use-file-for-fake-audio-capture=${path.join(HERE, "fixtures/english.wav")}`],
  });
  const want = process.argv.slice(2);
  const order = ["landing", "guards", "signup", "signupchat", "dashboard", "chat", "lock", "phone", "admin", "passkey", "a11y", "chatidle"];
  for (const name of order.filter((n) => !want.length || want.includes(n))) {
    scenario = name;
    console.log(`\n## ${name}`);
    try {
      await scenarios[name]();
    } catch (e) {
      check(`${name} crashed`, false, String(e.stack || e).slice(0, 400));
    }
  }
  await browser.close();
  fs.mkdirSync(path.join(HERE, "results"), { recursive: true });
  fs.writeFileSync(path.join(HERE, "results", "browser.json"), JSON.stringify(results, null, 1));
  const c = {};
  results.forEach((r) => (c[r.status] = (c[r.status] || 0) + 1));
  console.log("\n", c, "new user:", NEW_EMAIL);
  results.filter((r) => r.status !== "PASS").forEach((r) => console.log(`  ${r.status} [${r.section}] ${r.name}: ${r.detail.slice(0, 250)}`));
})();
