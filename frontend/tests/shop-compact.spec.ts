import { test, expect } from "@playwright/test";

test("compact facts, comparison tables and bullet answers preserve shopping controls", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1280, height: 900 });
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current).toBeVisible();
  await expect(current).toContainText("Product reviews"); await expect(current).toContainText("Seller reviews");
  await expect(current.getByText("No selectable size supplied.", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Conversation history" }).locator(".cui-chat-answer ul")).toHaveCount(1);
  await expect(page.locator(".cui-chat-answer ul")).toHaveCSS("list-style-type", "disc");
  await expect(page.getByRole("table", { name: "Listed product features; missing information is not assumed" })).toBeVisible();
  const sellers = page.getByRole("table", { name: "Compare sellers of this model", exact: true });
  await expect(sellers).toBeVisible();
  await expect(sellers.getByRole("button", { name: "Compare offer from Flash Deals", exact: true })).toBeDisabled();
  await sellers.getByRole("button", { name: "Details for Flash Deals", exact: true }).click();
  await expect(sellers).toContainText("Blocked by backend policy");
  await expect(sellers).toContainText("outside");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("compact-comparison.png"), fullPage: true });
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByRole("button", { name: "Finish decision", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByLabel("Simulated receipt", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("assistant bullet markup is rendered as text and semantic lists, never HTML", async ({ page, request }) => {
  const v = await (await request.post("http://localhost:8100/shop/sessions")).json();
  await page.route(`**/shop/sessions/${v.session.id}`, async route => {
    const response = await route.fetch(); const body = await response.json();
    body.session.messages.push({ role: "assistant", text: "Here is the offer.\n\n- **Price:** SGD35.\n- <img src=x onerror=alert(1)>\n\nReview before selecting." });
    await route.fulfill({ response, json: body });
  });
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), v.session.id);
  await page.goto("/");
  const answer = page.locator(".cui-chat-answer").last();
  await expect(answer.locator("li")).toHaveCount(2);
  await expect(answer.locator("strong")).toHaveText("Price:");
  await expect(answer.locator("img")).toHaveCount(0);
  await expect(answer).toContainText("<img src=x onerror=alert(1)>");
});

test("Lumen summary surfaces reviews, return terms and the current seller in comparison", async ({ page, request }, testInfo) => {
  const created = await (await request.post("http://localhost:8100/shop/sessions")).json();
  const searched = await (await request.post(`http://localhost:8100/shop/sessions/${created.session.id}/messages`, { data: { revision: created.revision, text: "Find headphones under SGD200" } })).json();
  const proposed = await request.post(`http://localhost:8100/shop/sessions/${created.session.id}/propose`, { data: { revision: searched.revision, product_id: "study-hp-target-lowprice" } });
  expect(proposed.ok()).toBeTruthy();
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1280, height: 900 });
  await page.goto("/");
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current).toContainText("Lumen Hush ANC");
  await expect(current).toContainText("272 g");
  await expect(current).toContainText("30-day free returns");
  await expect(current).toContainText("Stopped charging");
  await expect(page.getByRole("table", { name: "Listed product features; missing information is not assumed" })).toContainText("Noise control");
  const sellers = page.getByRole("table", { name: "Compare sellers of this model", exact: true });
  const currentSeller = sellers.getByRole("row", { name: "Seller offer Bargain Depot SG", exact: true });
  await expect(currentSeller).toContainText("Current offer");
  await expect(currentSeller.getByRole("button", { name: "Compare offer from Bargain Depot SG", exact: true })).toBeDisabled();
  await expect(sellers.getByRole("button", { name: "Compare offer from Quickpay Deals", exact: true })).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("lumen-summary-tables.png"), fullPage: true });
  await page.getByRole("heading", { name: "Compare products", exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("lumen-model-comparison.png"), fullPage: false });
});
