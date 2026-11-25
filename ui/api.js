// Helpers shared by both pages: calling the services, months and money.
// Plain browser JavaScript, no framework and no build step (ADR-6).

const CONFIG = window.APP_CONFIG;

// Container Apps scales both services to zero. The first request after a
// quiet period starts the container, and Azure answers 503 after about 30 s
// if it isn't ready yet. So a request may take a while, but never forever.
const REQUEST_TIMEOUT_MS = 35000;
const GET_ATTEMPTS = 3;
const RETRY_DELAY_MS = 5000;

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status; // 0 means no answer at all (stopped, or timed out)
  }
}

async function callApi(baseUrl, path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(baseUrl + path, {
      method: options.method || "GET",
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    throw new ApiError(
      "The service didn't answer. It may be stopped, or starting up after a quiet period. Try again in a minute.",
      0,
    );
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 204) return null;
  let body = null;
  try {
    body = await response.json();
  } catch (err) {
    // Not JSON, e.g. Azure's own 503 page while a container starts.
  }
  if (!response.ok) {
    const fallback = response.status === 503
      ? "The service is starting up. Try again in a few seconds."
      : `Request failed (${response.status}).`;
    throw new ApiError((body && body.error) || fallback, response.status);
  }
  return body;
}

// GETs are safe to repeat, so they retry by themselves while a service is
// waking up. POST and DELETE don't, so nothing is saved twice.
async function getJson(baseUrl, path) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await callApi(baseUrl, path);
    } catch (err) {
      const wakingUp = err.status === 0 || err.status === 503;
      if (!wakingUp || attempt === GET_ATTEMPTS) throw err;
      setLoading(`The service is waking up after a quiet period. Retrying (${attempt + 1} of ${GET_ATTEMPTS})…`);
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }
}

// Ping a service without waiting for it, so a scaled-to-zero container (and
// its database) starts now rather than when the user opens the other page.
function wakeUp(baseUrl) {
  fetch(baseUrl + "/health").catch(() => {});
}

// --- messages ----------------------------------------------------------------

function showMessage(kind, text) {
  const box = document.getElementById("message");
  box.className = `flash flash-${kind}`;
  box.textContent = text;
  box.hidden = false;
}

function clearMessage() {
  document.getElementById("message").hidden = true;
}

function setLoading(text) {
  const line = document.getElementById("loading");
  line.textContent = text;
  line.hidden = !text;
}

// --- months and money --------------------------------------------------------

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function todayIso() {
  const now = new Date();
  return `${currentMonth()}-${String(now.getDate()).padStart(2, "0")}`;
}

function monthFromUrl() {
  const month = new URLSearchParams(window.location.search).get("month");
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(month || "") ? month : currentMonth();
}

// shiftMonth("2026-01", -1) -> "2025-12", same idea as shift_month() in A1
function shiftMonth(month, delta) {
  const [year, mon] = month.split("-").map(Number);
  const index = year * 12 + (mon - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

function monthLabel(month) {
  const [year, mon] = month.split("-").map(Number);
  return new Date(year, mon - 1, 1).toLocaleString("en-GB", { month: "long", year: "numeric" });
}

// 1250 -> "12.50", 123456 -> "1,234.56", -500 -> "-5.00" (format_money() in A1)
function formatMoney(cents) {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const euros = Math.floor(abs / 100).toLocaleString("en-US");
  return `${sign}${euros}.${String(abs % 100).padStart(2, "0")}`;
}

// Month arrows, page title and nav links keep the selected month.
function setupMonthNav(month) {
  document.getElementById("month-title").textContent = monthLabel(month);
  document.getElementById("prev-month").href = `?month=${shiftMonth(month, -1)}`;
  document.getElementById("next-month").href = `?month=${shiftMonth(month, 1)}`;
  document.getElementById("nav-expenses").href = `index.html?month=${month}`;
  document.getElementById("nav-budgets").href = `budgets.html?month=${month}`;
}

// --- building HTML safely ----------------------------------------------------

// Creates an element. Text always goes in as text, never as HTML, so a
// description like "<script>" is shown, not run.
function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) node.append(child);
  return node;
}
