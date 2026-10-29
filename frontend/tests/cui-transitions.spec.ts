import { test, expect, type Page } from "@playwright/test";

const request = "Headphones for my train commute, under SGD300. Noise cancellation first.";
async function open(page: Page) {
  await page.goto("/shop");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.clock.install();
  const now = await page.evaluate(() => Date.now());
  await page.clock.pauseAt(new Date(now + 100));
}
async function send(page: Page, value = request) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(value);
  await page.getByRole("button", { name: "Send", exact: true }).click();
}

test("comparison stages reveal in order while the composer and frame stay steady", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 390 : 1487, height: 1058 });
  await open(page);
  const composer = page.getByLabel("Describe your purchase", { exact: true });
  const panel = page.getByLabel("Current decision", { exact: true });
  const before = await composer.boundingBox(); const panelBefore = await panel.boundingBox();
  const needsBefore = await page.getByLabel("Purchase needs", { exact: true }).boundingBox();
  await send(page);
  const history = page.getByRole("region", { name: "Conversation history" });
  const progress = page.getByLabel("Preparing comparison", { exact: true });
  await expect(history).toContainText(request);
  await expect(progress).toContainText("Preparing your local comparison");
  await expect(history.getByText(/^I compared 2/)).toHaveCount(0);
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
  await page.clock.runFor(399);
  await expect(page.getByLabel("Purchase needs", { exact: true })).not.toContainText("SGD300");
  await page.clock.runFor(1);
  await expect(page.getByLabel("Purchase needs", { exact: true })).toContainText("SGD300");
  await page.clock.runFor(600);
  await expect(progress).toContainText("Compared 2 fictional product records");
  await page.clock.runFor(600);
  await expect(progress).toContainText("Reviewed 3 seller records");
  await page.screenshot({ path: testInfo.outputPath("comparison-1600ms.png") });
  await page.clock.runFor(399);
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
  await page.clock.runFor(1);
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Echo Quiet");
  await expect(progress).toHaveCount(0);
  const after = await composer.boundingBox(); const panelAfter = await panel.boundingBox();
  const needsAfter = await page.getByLabel("Purchase needs", { exact: true }).boundingBox();
  expect(Math.abs(needsAfter!.width - needsBefore!.width)).toBeLessThanOrEqual(2);
  expect(Math.abs(after!.y - before!.y)).toBeLessThanOrEqual(2);
  expect(Math.abs(after!.height - before!.height)).toBeLessThanOrEqual(2);
  expect(Math.abs(panelAfter!.y - panelBefore!.y)).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("reset at every phase cancels the old reveal and permits a new request", async ({ page }) => {
  await open(page);
  for (const phase of [0, 400, 1000, 1600]) {
    await send(page);
    if (phase) await page.clock.runFor(phase);
    await page.getByRole("button", { name: "Start fresh", exact: true }).click();
    await page.clock.runFor(2500);
    await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Conversation history" })).not.toContainText(request);
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  }
  await send(page, "Running shoes for road runs under SGD200, cushioning first");
  await page.clock.runFor(2000);
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Stride Cloud");
});

test("updates invalidate selection immediately, block action controls and retain typed drafts", async ({ page }) => {
  await open(page);
  await send(page); await page.clock.runFor(2000);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await send(page, "Actually, comfort matters more");
  await expect(page.getByLabel("Selected offer", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Select this offer", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Find another seller", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeDisabled();
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await input.fill("Why this seller?");
  await page.clock.runFor(2000);
  await expect(input).toHaveValue("Why this seller?");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Luma Air");
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  const before = await page.evaluate(() => JSON.parse(localStorage.getItem("beany-cui-needs")!));
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("Preparing reply", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Preparing comparison", { exact: true })).toHaveCount(0);
  await page.clock.runFor(299);
  await expect(page.getByLabel("Preparing reply", { exact: true })).toBeVisible();
  await page.clock.runFor(1);
  await expect(page.getByLabel("Preparing reply", { exact: true })).toHaveCount(0);
  const after = await page.evaluate(() => JSON.parse(localStorage.getItem("beany-cui-needs")!));
  for (const key of ["revision", "needs", "choice", "selectedOfferId", "finished"]) expect(after[key]).toEqual(before[key]);
});

test("refresh during presentation restores the computed result without replay", async ({ page }) => {
  await open(page); await send(page); await page.clock.runFor(400);
  await page.reload();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Echo Quiet");
  await expect(page.getByLabel("Preparing comparison", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
});

test("clarification and no-match present only applicable steps", async ({ page }) => {
  await open(page); await send(page, "Headphones");
  await expect(page.getByLabel("Preparing reply", { exact: true })).toBeVisible();
  await page.clock.runFor(300);
  await expect(page.getByLabel("Purchase clarification")).toContainText("mainly use");
  await expect(page.getByLabel("Comparison activity", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  await send(page, "Headphones for commuting under SGD1, comfort first");
  await page.clock.runFor(1600);
  await expect(page.getByLabel("Preparing comparison", { exact: true })).toContainText("0 models");
  await expect(page.getByLabel("Preparing comparison", { exact: true })).not.toContainText("Reviewed 3 seller");
  await page.clock.runFor(400);
  await expect(page.getByLabel("No matching offer", { exact: true })).toContainText("SGD1");
});

test("reduced motion and keyboard submission retain status updates without animation", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await input.fill(request); await input.press("Tab");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Preparing your local comparison");
  expect(await page.locator(".cui-typing").evaluate(element => getComputedStyle(element).animationName)).toBe("none");
  await page.clock.runFor(2000);
  await expect(page.getByRole("status")).toContainText("I compared");
  expect(await page.locator(".cui-recommendation").evaluate(element => getComputedStyle(element).animationName)).toBe("none");
  expect(errors).toEqual([]);
});


test("expanded needs on a short desktop retain a usable chat and composer", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 600 });
  await open(page); await send(page); await page.clock.runFor(2000);
  await page.getByRole("button", { name: "Edit spending limit" }).click();
  const chat = await page.getByRole("region", { name: "Conversation history" }).boundingBox();
  expect(chat!.height).toBeGreaterThan(250);
  const composer = page.getByRole("textbox", { name: "Message Beany" });
  await composer.scrollIntoViewIfNeeded();
  await expect(composer).toBeInViewport();
  await composer.fill("Why this seller?");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});


test("follow-up answer starts inside the chat viewport above older comparison activity", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page); await send(page); await page.clock.runFor(2000);
  await send(page, "What do reviews say?"); await page.clock.runFor(300);
  const history = page.getByRole("region", { name: "Conversation history" });
  await expect(history).toContainText("supplied review excerpt");
  const geometry = await history.evaluate(element => {
    const reply = element.querySelector(".cui-conversation-history .cui-turn:last-child")!.getBoundingClientRect();
    const bounds = element.getBoundingClientRect();
    return { top: reply.top - bounds.top, bottom: reply.bottom - bounds.top, height: bounds.height };
  });
  expect(geometry.top).toBeGreaterThanOrEqual(-2);
  expect(geometry.top).toBeLessThan(geometry.height);
  expect(geometry.bottom).toBeGreaterThan(0);
});
