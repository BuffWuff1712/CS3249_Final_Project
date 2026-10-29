import { test, expect, type Page } from "@playwright/test";

const request = "Headphones for my train commute, under SGD300. Noise cancellation first.";
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(text);
  await page.getByRole("button", { name: "Send", exact: true }).click();
}

test("conversation and source answers survive refresh without altering a selected offer", async ({ page }) => {
  await page.goto("/shop");
  await send(page, request);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  const before = await page.evaluate(() => JSON.parse(localStorage.getItem("beany-cui-needs")!));
  await send(page, "What do the negative product reviews say?");
  const history = page.getByRole("region", { name: "Conversation history" });
  await expect(history).toContainText(request);
  await expect(history).toContainText("1 supplied review excerpt");
  await expect(history).toContainText("does not mean I read all those reviews");
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Echo Quiet");
  await expect(page.getByRole("status")).toContainText("1 supplied review excerpt");
  const after = await page.evaluate(() => JSON.parse(localStorage.getItem("beany-cui-needs")!));
  for (const key of ["needs", "revision", "selectedOfferId", "choice", "finished"]) expect(after[key]).toEqual(before[key]);
  await send(page, "Why this one, what do the negative reviews say, and can I return it?");
  await expect(history).toContainText("30-day returns");
  await expect(history.getByRole("button", { name: "View Northline Audio evidence", exact: true })).toBeVisible();
  await history.getByRole("button", { name: "View Echo Quiet evidence", exact: true }).click();
  await expect(page.getByLabel("Product evidence for Echo Quiet", { exact: true })).toBeFocused();
  await page.reload();
  await expect(history).toContainText("1 supplied review excerpt");
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Northline Audio");
});

test("seller preference and direct priority edits are consequential and remain within budget", async ({ page }) => {
  await page.goto("/shop");
  await send(page, request);
  await page.getByRole("button", { name: "Prefer lowest price", exact: true }).click();
  const decision = page.getByRole("article", { name: "Current recommendation" });
  await expect(decision).toContainText("SGD269");
  await expect(decision).toContainText("Everyday Sound");
  await expect(page.getByLabel("What changed")).toContainText("Changed seller");
  await page.getByRole("button", { name: "Prioritise comfort", exact: true }).click();
  await expect(decision).toContainText("Luma Air");
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("SGD300");
  await expect(page.getByRole("region", { name: "Conversation history" })).toContainText("Prefer lowest price");
  await page.getByRole("button", { name: "Edit spending limit: 300", exact: true }).click();
  await expect(page.getByLabel("Preference value")).toBeFocused();
  await page.getByLabel("Preference value").fill("180");
  await page.getByRole("button", { name: "Save need", exact: true }).click();
  await page.getByRole("button", { name: "Compare current needs", exact: true }).click();
  await expect(page.getByLabel("No matching offer", { exact: true })).toContainText("SGD180");
});

test("desktop exposes the decision beside the conversation and narrow layouts offer working jump links", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1487, height: 1058 });
  await page.goto("/shop");
  await send(page, request);
  const conversation = page.getByLabel("Shopping conversation", { exact: true });
  const result = page.getByRole("article", { name: "Current recommendation" });
  if (testInfo.project.name === "desktop") {
    const left = await conversation.boundingBox(); const right = await result.boundingBox();
    expect(right!.x).toBeGreaterThan(left!.x + left!.width);
    const select = await page.getByRole("button", { name: "Select this offer", exact: true }).boundingBox();
    expect(select!.y + select!.height).toBeLessThan(1058);
  } else {
    await page.getByRole("link", { name: "Current decision", exact: true }).click();
    await expect(page).toHaveURL(/#shopping-decision$/);
    await page.getByRole("link", { name: "Conversation", exact: true }).click();
    await expect(page).toHaveURL(/#shopping-conversation$/);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test("a capped conversation still scrolls to the newest answer", async ({ page }) => {
  await page.goto("/shop");
  await send(page, request);
  for (let turn = 0; turn < 30; turn++) await send(page, "Why this one?");
  await send(page, "What do the product reviews say?");
  const history = page.getByRole("region", { name: "Conversation history" });
  await expect(history).toContainText("1 supplied review excerpt");
  await expect.poll(() => history.evaluate(element => {
    const reply = element.querySelector(".cui-conversation-history .cui-turn:last-child")!;
    return Math.abs(reply.getBoundingClientRect().top - element.getBoundingClientRect().top);
  })).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem("beany-cui-needs")!).messages.length)).toBe(60);
});

test("seller preference toggles keep an explicitly fixed model", async ({ page }) => {
  await page.goto("/shop");
  await send(page, "Headphones for commuting under SGD300, comfort first");
  await send(page, "Find the cheapest Echo Quiet offer");
  const decision = page.getByRole("article", { name: "Current recommendation" });
  await expect(decision.getByRole("heading", { name: "Echo Quiet", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Prefer longer returns", exact: true }).click();
  await expect(decision.getByRole("heading", { name: "Echo Quiet", exact: true })).toBeVisible();
  await expect(decision).toContainText("Northline Audio");
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("comfort");
  await send(page, "Longer returns first");
  await expect(decision.getByRole("heading", { name: "Echo Quiet", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Preference value").fill("lowest price");
  await page.getByRole("button", { name: "Save need", exact: true }).click();
  await page.getByRole("button", { name: "Compare current needs", exact: true }).click();
  await expect(decision.getByRole("heading", { name: "Echo Quiet", exact: true })).toBeVisible();
  await expect(decision).toContainText("Everyday Sound");
});
