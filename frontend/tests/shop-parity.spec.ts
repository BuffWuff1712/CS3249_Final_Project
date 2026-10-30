import { test, expect, type Page } from "@playwright/test";
const API = "http://localhost:8100";
async function ready(page: Page) { await page.goto("/shop"); await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled(); }
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(text);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
}
test("explicit reject, general alternative and cancellation preserve user control", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  const current = page.getByRole("article", { name: "Current recommendation" });
  const first = await current.getByRole("heading", { level: 3 }).innerText();
  await current.getByRole("button", { name: "Find another merchant", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect(current).toBeVisible();
  await current.getByRole("button", { name: "Reject offer", exact: true }).click();
  await expect(current).toHaveCount(0);
  await page.getByRole("button", { name: "Compare current needs" }).click();
  await expect(current).toBeVisible();
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cancel shopping task", exact: true }).click();
  await expect(current).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Finish decision" })).toHaveCount(0);
  await page.reload(); await expect(page.getByRole("button", { name: "Cancel shopping task" })).toBeDisabled();
  expect(first).toBeTruthy();
});
test("classic saved session is adopted with needs permissions cart and history intact", async ({ page, request }) => {
  const s = await (await request.post(`${API}/sessions`)).json();
  const result = await (await request.post(`${API}/sessions/${s.id}/messages`, { data: { text: "Find headphones under SGD200" } })).json();
  const a = result.proposals.at(-1);
  await request.post(`${API}/sessions/${s.id}/cart`, { data: { proposal_id: a.id, fingerprint: a.fingerprint } });
  await page.addInitScript(id => localStorage.setItem("beany-session", id), s.id);
  await ready(page);
  await expect(page.getByRole("link", { name: "Cart (1)", exact: true })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("beany-shop-backend-session"))).toBe(s.id);
  await page.getByRole("link", { name: "Cart (1)", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Total (1 items)" })).toBeVisible();
  await page.getByRole("button", { name: "Review checkout", exact: true }).click();
  await page.getByRole("button", { name: "Confirm simulated checkout", exact: true }).click();
  await page.getByRole("link", { name: "View receipts", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Simulated receipt", exact: true })).toHaveCount(1);
});
test("permissions invalidate current selection and apply to saved cart review", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  await page.getByRole("button", { name: "Add to cart", exact: true }).click();
  await expect(page.getByRole("link", { name: "Cart (1)", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open settings" }).click();
  await page.getByRole("checkbox", { name: "Demo Visa (fictional)", exact: true }).uncheck();
  await page.getByRole("button", { name: "Save Permissions", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Permissions saved");
  await page.goto("/cart"); await expect(page.getByRole("heading", { name: "Total (1 items)" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Review checkout", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: /^Remove / }).click();
  await expect(page.getByText("Your cart has no items to review.", { exact: true })).toBeVisible();
});
test("saved needs expose hard versus preferred controls and full merchant evidence", async ({ page }) => {
  await ready(page); await send(page, "Find headphones under SGD200");
  await page.getByRole("button", { name: "Edit spending limit: 200", exact: true }).click();
  const hard = page.getByRole("checkbox", { name: "Must have", exact: true });
  await expect(hard).toBeChecked(); await hard.uncheck();
  await page.getByRole("button", { name: "Save need", exact: true }).click();
  await page.reload(); await expect(page.getByRole("button", { name: "Edit spending limit: 200", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Edit spending limit: 200", exact: true }).click(); await expect(hard).not.toBeChecked();
  await page.getByRole("combobox", { name: "Purchase field" }).selectOption("features"); await expect(hard).not.toBeChecked();
  await page.getByRole("button", { name: "Compare current needs" }).click();
  const current = page.getByRole("article", { name: "Current recommendation" });
  await current.getByText("View comparison and sources", { exact: true }).click();
  await current.getByText(/^Review merchant details:/).click();
  await expect(current).toContainText("Verification indicator"); await expect(current).toContainText("Requested information");
});
