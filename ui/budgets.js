// Budgets page. It only calls the budgets service; the budgets service asks
// the expenses service for the spending (ADR-6). If that call fails, the
// answer has spending_available: false and the page shows a notice instead
// of the totals.

const month = monthFromUrl();
const form = document.getElementById("budget-form");

setupMonthNav(month);
document.getElementById("budgets-title").textContent = `Budgets for ${monthLabel(month)}`;
wakeUp(CONFIG.EXPENSES_URL); // budgets needs it for the spending, so start it now
load();

async function load() {
  setLoading("Loading…");
  try {
    const report = await getJson(CONFIG.BUDGETS_URL, `/api/budgets/status?month=${month}`);
    document.getElementById("spending-notice").hidden = report.spending_available;
    renderBudgets(report.budgets);
    renderUnbudgeted(report.unbudgeted);
  } catch (err) {
    showMessage("error", err.message);
  } finally {
    setLoading("");
  }
}

function usageCell(row) {
  if (row.status === "unknown") {
    return el("td", { class: "usage" }, el("small", { text: "spending unavailable" }));
  }
  const width = Math.min(row.percent_used, 100); // an over-budget bar doesn't spill out
  const left = row.status === "over"
    ? `€${formatMoney(-row.remaining_cents)} over`
    : `€${formatMoney(row.remaining_cents)} left`;
  return el("td", { class: "usage" },
    el("div", { class: "bar" }, el("span", { style: `width: ${width}%` })),
    el("small", { text: `${row.percent_used}% · ${left}` }),
  );
}

function renderBudgets(rows) {
  document.getElementById("budgets-table").hidden = rows.length === 0;
  document.getElementById("no-budgets").hidden = rows.length > 0;
  document.getElementById("budgets-body").replaceChildren(
    ...rows.map((row) =>
      el("tr", { class: `status-${row.status}` },
        el("td", { text: row.category }),
        el("td", { class: "num", text: row.spent_cents === null ? "–" : `€${formatMoney(row.spent_cents)}` }),
        el("td", { class: "num", text: `€${formatMoney(row.limit_cents)}` }),
        usageCell(row),
        el("td", { class: "num" }, el("button", { class: "link-button", "data-id": row.id, text: "Remove" })),
      ),
    ),
  );
}

function renderUnbudgeted(unbudgeted) {
  const entries = Object.entries(unbudgeted);
  document.getElementById("unbudgeted-card").hidden = entries.length === 0;
  document.getElementById("unbudgeted").replaceChildren(
    ...entries.map(([category, cents]) =>
      el("li", {}, el("span", { text: category }), el("span", { class: "amount", text: `€${formatMoney(cents)}` })),
    ),
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  clearMessage();
  try {
    const saved = await callApi(CONFIG.BUDGETS_URL, "/api/budgets", {
      method: "POST",
      body: Object.fromEntries(new FormData(form)),
    });
    showMessage("success", `Budget for '${saved.category}' saved.`);
    form.reset();
    await load();
  } catch (err) {
    showMessage("error", err.message);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("budgets-body").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  button.disabled = true;
  clearMessage();
  try {
    await callApi(CONFIG.BUDGETS_URL, `/api/budgets/${button.dataset.id}`, { method: "DELETE" });
    showMessage("success", "Budget removed.");
  } catch (err) {
    showMessage("error", err.message);
  }
  await load();
});

document.getElementById("retry").addEventListener("click", () => {
  clearMessage();
  load();
});
