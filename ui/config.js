// Where the two services are. These are the local values for docker compose.
// The deploy workflow overwrites this file with the Azure URLs before it
// uploads ui/ to the storage account, so the URLs are never hardcoded in the
// pages themselves.
window.APP_CONFIG = {
  EXPENSES_URL: "http://localhost:8001",
  BUDGETS_URL: "http://localhost:8002",
};
