import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
const API = "http://localhost:8100";
const researchHeaders = { "X-Research-Key": "e2e-key" };
async function ready(page: Page, sid?: string) {
  if (sid) await page.addInitScript(id => localStorage.setItem("beany-session", id), sid);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
}
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(text);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
}
async function study(request: APIRequestContext, scenario: string) {
  const created = await request.post(`${API}/research/scenarios/${scenario}/sessions`, { headers: researchHeaders });
  expect(created.ok()).toBeTruthy();
  const s = await created.json();
  const triggered = await request.post(`${API}/research/sessions/${s.id}/trigger`, { headers: researchHeaders });
  expect(triggered.ok()).toBeTruthy();
  return triggered.json();
}

test("brief field selector restores each field's hard constraint", async ({ page, request }) => {
  const session = await (await request.post(`${API}/sessions`)).json();
  for (const [field, value, hard] of [["budget", "300", true], ["features", "wireless", false]] as const) {
    await request.put(`${API}/sessions/${session.id}/brief`, { data: { field, fact: { value, source: "confirmed", hard } } });
  }
  await ready(page, session.id);
  await page.getByRole("button", { name: "Edit spending limit: 300", exact: true }).click();
  const selector = page.getByRole("combobox", { name: "Purchase field", exact: true });
  const hard = page.getByRole("checkbox", { name: "Must have", exact: true });
  await expect(hard).toBeChecked(); await selector.selectOption("features"); await expect(hard).not.toBeChecked();
  await selector.selectOption("budget"); await expect(hard).toBeChecked();
  await selector.selectOption("other"); await expect(hard).not.toBeChecked();
  await selector.selectOption("features");
  await page.getByRole("textbox", { name: "Preference value", exact: true }).fill("wireless, comfortable");
  await page.getByRole("button", { name: "Save need", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit features / priorities: wireless, comfortable", exact: true })).toBeEnabled();
  await page.reload();
  await page.getByRole("button", { name: "Edit features / priorities: wireless, comfortable", exact: true }).click();
  await expect(hard).not.toBeChecked(); await selector.selectOption("budget"); await expect(hard).toBeChecked();
  await expect(page.getByRole("textbox", { name: "Preference value", exact: true })).toHaveValue("300");
});

test("conversation, specific approval and simulated receipt", async ({ page }) => {
  await ready(page); await expect(page.getByText("Mock LLM: offline test responses", { exact: false })).toBeVisible();
  await send(page, "Find headphones under SGD150");
  await page.getByRole("button", { name: "Add to cart", exact: true }).click();
  await page.getByRole("link", { name: "Cart (1)", exact: true }).click();
  await page.getByRole("button", { name: "Review checkout", exact: true }).click();
  await page.getByRole("button", { name: "Confirm simulated checkout", exact: true }).click();
  await page.getByRole("link", { name: "View receipts", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Simulated receipt", exact: true })).toHaveCount(1);
  await page.reload(); await expect(page.getByRole("heading", { name: "Simulated receipt", exact: true })).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test("vague request, repair and cancellation", async ({ page }) => {
  await ready(page); await send(page, "I need some shoes");
  const history = page.getByRole("region", { name: "Conversation history", exact: true });
  await expect(history.getByText("Will you use them for running or everyday wear?", { exact: true })).toHaveCount(1);
  await send(page, "Find running shoes under SGD150");
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toBeVisible();
  await send(page, "cancel");
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Cancel shopping task", exact: true })).toBeDisabled();
});

test("study hard block supports reject and refine while preventing checkout and preserving CSV export", async ({ page, request }) => {
  const s = await study(request, "budget"); await ready(page, s.id);
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current.getByRole("button", { name: "Select this offer", exact: true })).toBeDisabled();
  await expect(current.getByRole("button", { name: "Add to cart", exact: true })).toBeDisabled();
  await expect(current.getByText("Blocked by backend policy", { exact: true })).toBeVisible();
  await expect(current.getByRole("button", { name: "Change needs", exact: true })).toBeEnabled();
  await expect(current.getByRole("button", { name: "Find another merchant", exact: true })).toBeEnabled();
  await current.getByRole("button", { name: "Reject offer", exact: true }).click();
  await expect(current).toHaveCount(0);
  const csv = await request.get(`${API}/research/sessions/${s.id}/export`, { headers: researchHeaders });
  const text = await csv.text(); expect(text).toContain("intervention"); expect(text).toContain("reject");
});

test("keyboard submission and recoverable network errors", async ({ page }, testInfo) => {
  await ready(page);
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await page.route("**/shop/sessions/*/messages/stream", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "OpenAI temporarily unavailable. Retry your message." }) }));
  await input.fill("Find headphones under SGD150"); await input.press("Enter");
  await expect(page.getByRole("region", { name: "Conversation history", exact: true }).getByRole("alert")).toContainText("OpenAI temporarily unavailable");
  await expect(input).toHaveValue("Find headphones under SGD150");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeDisabled();
  await page.unroute("**/shop/sessions/*/messages/stream");
  await page.getByRole("button", { name: "Reload workspace", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await input.fill("Find headphones under SGD150");
  await input.press("Shift+Enter"); await expect(input).toHaveValue("Find headphones under SGD150\n");
  await input.press("Enter");
  await expect(page.getByRole("button", { name: "Select this offer", exact: true })).toBeEnabled();
  await page.screenshot({ path: testInfo.outputPath("beany-review.png"), fullPage: true });
  await page.getByRole("button", { name: "Cancel shopping task", exact: true }).click();
  await expect(page.getByRole("button", { name: "Select this offer", exact: true })).toHaveCount(0);
});

test("merchant evidence is public but hidden truth is research-only", async ({ page, request }) => {
  const s = await study(request, "risk-h");
  const state = await (await request.get(`${API}/sessions/${s.id}`)).json();
  expect(state.experiment).toBeUndefined(); expect(JSON.stringify(state)).not.toContain("MALICIOUS");
  await ready(page, s.id);
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await current.getByText("View comparison and sources", { exact: true }).click();
  await current.getByText("Review merchant details: City Goods", { exact: true }).click();
  const details = current.locator(".merchant-details");
  await expect(details).toContainText(new URL(state.proposals.at(-1).merchant_details.website).host);
  await expect(page.getByText("MALICIOUS", { exact: true })).toHaveCount(0);
  expect((await request.get(`${API}/research/sessions/${s.id}/risk-report`)).status()).toBe(403);
  const report = await request.get(`${API}/research/sessions/${s.id}/risk-report`, { headers: researchHeaders });
  expect((await report.json()).metrics.fn).toBe(1);
});

test("risky offer can be replaced with another merchant without losing brief", async ({ page, request }) => {
  const s = await study(request, "risk-i"); await ready(page, s.id);
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current).toContainText("Merchant risk: high predicted risk");
  await current.getByRole("button", { name: "Find another merchant", exact: true }).click();
  await expect(current).toContainText("Demo Store");
  const result = await (await request.get(`${API}/sessions/${s.id}`)).json();
  expect(result.brief.budget.value).toBe("150");
});
