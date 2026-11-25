// Expenses page. Everything here talks to the expenses service only, so the
// page keeps working when the budgets service is down.

const month = monthFromUrl();
const form = document.getElementById("expense-form");

setupMonthNav(month);
resetForm();
wakeUp(CONFIG.BUDGETS_URL);
load();

function resetForm() {
  form.reset();
  form.elements.spent_on.value = todayIso();
  form.elements.spent_on.max = todayIso();
}

async function load() {
  setLoading("Loading…");
  try {
    const [list, totals, categories] = await Promise.all([
      getJson(CONFIG.EXPENSES_URL, `/api/expenses?month=${month}`),
      getJson(CONFIG.EXPENSES_URL, `/api/expenses/totals?month=${month}`),
      getJson(CONFIG.EXPENSES_URL, "/api/expenses/categories"),
    ]);
    renderTotals(totals.totals);
    renderExpenses(list.expenses);
    renderCategories(categories.categories);
  } catch (err) {
    showMessage("error", err.message);
  } finally {
    setLoading("");
  }
}

function renderTotals(totals) {
  const list = document.getElementById("totals");
  const entries = Object.entries(totals);
  const sum = entries.reduce((total, [, cents]) => total + cents, 0);
  document.getElementById("month-total").textContent = `€${formatMoney(sum)}`;
  list.replaceChildren(
    ...entries.map(([category, cents]) =>
      el("li", {}, el("span", { text: category }), el("span", { class: "amount", text: `€${formatMoney(cents)}` })),
    ),
  );
}

function renderExpenses(expenses) {
  const table = document.getElementById("expenses-table");
  const empty = document.getElementById("no-expenses");
  table.hidden = expenses.length === 0;
  empty.hidden = expenses.length > 0;
  empty.textContent = `Nothing logged for ${monthLabel(month)} yet.`;

  document.getElementById("expenses-body").replaceChildren(
    ...expenses.map((e) =>
      el("tr", {},
        el("td", { text: e.spent_on }),
        el("td", { text: e.category }),
        el("td", { text: e.description }),
        el("td", { class: "num", text: `€${formatMoney(e.amount_cents)}` }),
        el("td", { class: "num" }, el("button", { class: "link-button", "data-id": e.id, text: "Delete" })),
      ),
    ),
  );
}

function renderCategories(categories) {
  document.getElementById("category-list").replaceChildren(
    ...categories.map((name) => el("option", { value: name })),
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  clearMessage();
  try {
    await callApi(CONFIG.EXPENSES_URL, "/api/expenses", {
      method: "POST",
      body: Object.fromEntries(new FormData(form)),
    });
    showMessage("success", "Expense added.");
    resetForm();
    await load();
  } catch (err) {
    showMessage("error", err.message);
  } finally {
    button.disabled = false;
  }
});

// One listener for all Delete buttons, including rows added later.
document.getElementById("expenses-body").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  button.disabled = true;
  clearMessage();
  try {
    await callApi(CONFIG.EXPENSES_URL, `/api/expenses/${button.dataset.id}`, { method: "DELETE" });
    showMessage("success", "Expense deleted.");
  } catch (err) {
    showMessage("error", err.message);
  }
  await load();
});
