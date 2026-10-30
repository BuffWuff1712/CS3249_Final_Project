import { test, expect, type Page } from "@playwright/test";

async function ready(page: Page) {
  await page.goto("/shop");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
}
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(text);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
}
async function current(page: Page) { return page.getByRole("article", { name: "Current recommendation", exact: true }); }

test("local backend conversation, real catalogue evidence, selection and receipt survive refresh", async ({ page }) => {
  const paid: string[] = [];
  page.on("request", request => { if (/openai\.com|browser-use\.com/.test(request.url())) paid.push(request.url()); });
  await ready(page);
  await expect(page.getByText("Mock LLM: offline test responses", { exact: false })).toBeVisible();
  await send(page, "Find headphones under SGD200");
  await expect(await current(page)).toBeVisible();
  await expect(await current(page)).not.toContainText("Echo Quiet");
  const history = page.getByRole("region", { name: "Conversation history" });
  await expect(history.getByLabel("Comparison activity", { exact: true })).toHaveCount(1);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("No receipt");
  await page.reload(); await expect(page.getByLabel("Selected offer", { exact: true })).toBeVisible();
  await send(page, "What do reviews say?");
  await expect(history).toContainText("aggregate ratings");
  await expect(page.getByLabel("Selected offer", { exact: true })).toBeVisible();
  await expect(history.getByLabel("Comparison activity", { exact: true })).toHaveCount(1);
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByLabel("Simulated receipt", { exact: true })).toContainText("No real order or payment");
  await page.reload(); await expect(page.getByLabel("Simulated receipt", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Other models", exact: true })).toHaveCount(0);
  expect(paid).toEqual([]);
});

test("needs editor uses server fields, clears selection, and impossible budget does not relax", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit budget: 200", exact: true }).click();
  await page.getByLabel("Amount", { exact: true }).fill("1");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Finish decision", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Compare current needs", exact: true }).click();
  await expect(page.getByRole("region", { name: "Current decision", exact: true })).toContainText("No eligible offer");
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("SGD1");
});

test("three local categories and historical comparison evidence remain inspectable", async ({ page }) => {
  await ready(page);
  await send(page, "Find running shoes under SGD200 size 42");
  await expect(await current(page)).toBeVisible();
  await send(page, "Find backpacks under SGD100");
  await expect(await current(page)).toBeVisible();
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("Backpacks");
  const sources = page.getByRole("button", { name: "View evidence for this comparison", exact: true });
  await expect(sources).toHaveCount(2);
  await sources.first().click();
  const historical = page.getByLabel("Historical comparison evidence", { exact: true });
  await expect(historical).toContainText("Historical proposal snapshot");
  await expect(historical).toContainText("Running shoes");
  await expect(historical.getByRole("button", { name: "Select this offer", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Back to current decision", exact: true }).click();
  await expect(await current(page)).toBeVisible();
});

test("site reputation comes from backend and blocked offers have disabled selection", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  await page.getByText(/^Compare all \d+ eligible offers$/).click();
  const offers = page.getByRole("row", { name: /^Catalogue offer / });
  await expect(offers.filter({ hasText: "Website reputation: Good" }).first()).toBeVisible();
  await expect(offers.filter({ hasText: "Website reputation: Mid" }).first()).toBeVisible();
  await expect(offers.filter({ hasText: "Website reputation: Poor" }).first()).toBeVisible();
  const blocked = offers.filter({ hasText: "Blocked by backend policy" }).first();
  await expect(blocked.getByRole("button", { name: "Compare this offer", exact: true })).toBeDisabled();
  const poor = offers.filter({ hasText: "Website reputation: Poor" }).first();
  await poor.getByRole("button", { name: /^Details for / }).click();
  await expect(page.locator(".cui-expanded-offer")).toContainText("uncertain assessment");
});

test("a failed mutation retains draft and requires a state reload without resending", async ({ page }) => {
  await ready(page);
  await page.route("**/shop/sessions/*/messages/stream", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Backend temporarily unavailable" }) }));
  await sendFailure();
  async function sendFailure() {
    await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.getByRole("region", { name: "Shopping conversation", exact: true }).getByRole("alert")).toContainText("Backend temporarily unavailable");
    await expect(page.getByRole("textbox", { name: "Message Beany" })).toHaveValue("Find headphones under SGD200");
    await expect(page.getByRole("textbox", { name: "Message Beany" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeDisabled();
  }
  await page.unroute("**/shop/sessions/*/messages/stream");
  await page.getByRole("button", { name: "Reload workspace", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect(await current(page)).toHaveCount(0);
});

test("reset ignores an old response and truthful pending state never invents completed checks", async ({ page }) => {
  await ready(page);
  let release!: () => void; const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/shop/sessions/*/messages/stream", async route => { const response = await route.fetch(); await gate; await route.fulfill({ response }); });
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("Backend request in progress", { exact: true })).toContainText("Starting your request");
  await expect(page.getByLabel("Comparison activity", { exact: true })).toHaveCount(0);
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Keep this draft");
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  release();
  await expect(await current(page)).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Conversation history" })).not.toContainText("Find headphones under SGD200");
});

test("desktop and 320px evidence spacing, keyboard and console are usable", async ({ page }, testInfo) => {
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1280, height: 900 });
  await ready(page); await send(page, "Find headphones under SGD200");
  await (await current(page)).getByText("View comparison and sources", { exact: true }).press("Enter");
  const record = (await current(page)).getByRole("region", { name: /^Product evidence for / });
  await expect(record).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("backend-shop-evidence.png"), fullPage: true });
  expect(errors).toEqual([]);
});


test("draft typed during a delayed fresh-session reset is preserved", async ({ page }) => {
  await ready(page);
  let release!: () => void; const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/shop/sessions", async route => { const response = await route.fetch(); await gate; await route.fulfill({ response }); });
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Old draft");
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await expect(input).toHaveValue(""); await input.fill("New draft while resetting");
  release(); await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect(input).toHaveValue("New draft while resetting");
});

test("a temporary restore error retains the session ID instead of silently creating another", async ({ page }) => {
  await ready(page);
  const sid = await page.evaluate(() => localStorage.getItem("beany-shop-backend-session"));
  let created = 0;
  await page.route("**/shop/sessions", route => { created++; return route.continue(); });
  await page.route(`**/shop/sessions/${sid}`, route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary restore failure" }) }));
  await page.reload();
  await expect(page.getByRole("region", { name: "Conversation history", exact: true }).getByRole("alert")).toContainText("Temporary restore failure");
  expect(created).toBe(0);
  expect(await page.evaluate(() => localStorage.getItem("beany-shop-backend-session"))).toBe(sid);
  await page.unroute(`**/shop/sessions/${sid}`);
  await page.getByRole("button", { name: "Reload workspace", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
});

test("seller changes keep the exact product and invalidate an earlier selection", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  await page.getByText(/^Compare all \d+ eligible offers$/).click();
  await page.getByRole("row", { name: "Catalogue offer study-hp-target-trusted", exact: true }).getByRole("button", { name: "Compare this offer", exact: true }).click();
  await expect((await current(page)).getByRole("heading", { name: "Lumen Hush ANC", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Find another seller", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect(page.getByLabel("Selected offer", { exact: true })).toHaveCount(0);
  await expect((await current(page)).getByRole("heading", { name: "Lumen Hush ANC", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Prefer lowest price", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect((await current(page)).getByRole("heading", { name: "Lumen Hush ANC", exact: true })).toBeVisible();
});

test("a vague request asks one clarification without inventing a spending limit", async ({ page }) => {
  await ready(page); await send(page, "shoes");
  const history = page.getByRole("region", { name: "Conversation history", exact: true });
  await expect(history.getByText("Will you use them for running or everyday wear?", { exact: true })).toHaveCount(1);
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("No budget is confirmed");
  await expect(await current(page)).toHaveCount(0);
  await send(page, "Running shoes under SGD200 size 42");
  await expect(await current(page)).toBeVisible();
});
