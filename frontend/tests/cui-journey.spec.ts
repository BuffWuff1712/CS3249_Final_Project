import { test, expect, type Page } from "@playwright/test";

const commute = "Headphones for my daily train commute, under SGD300. Noise cancellation matters more than weight.";
async function send(page: Page, message: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(message);
  await page.getByRole("button", { name: "Send", exact: true }).click();
}

test("priority correction updates the choice and explains the change", async ({ page }) => {
  await page.goto("/shop");
  await send(page, commute);
  await send(page, "Actually, comfort matters more");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Luma Air");
  await expect(page.getByLabel("What changed")).toContainText("Echo Quiet");
  await expect(page.getByLabel("What changed")).toContainText("Luma Air");
  await expect(page.getByLabel("Purchase needs")).toContainText("300");
});

test("an impossible budget explains the conflict and recovers without relaxing it", async ({ page }) => {
  await page.goto("/shop");
  await send(page, commute);
  await send(page, "My budget is now SGD180");
  await expect(page.getByLabel("No matching offer")).toContainText("SGD180");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
  await expect(page.getByLabel("Purchase needs")).toContainText("180");
  await send(page, "Raise my budget to SGD300");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("SGD289");
});

test("seller revision preserves the product and selection needs no evidence opening", async ({ page }) => {
  const mutations: string[] = [];
  page.on("request", request => { if (!["GET", "HEAD"].includes(request.method())) mutations.push(request.url()); });
  await page.goto("/shop");
  await send(page, commute);
  await send(page, "Keep the product but find another seller");
  const result = page.getByRole("article", { name: "Current recommendation" });
  await expect(result.getByRole("heading", { name: "Echo Quiet", exact: true })).toBeVisible();
  await expect(result).toContainText("Everyday Sound");
  await expect(result).toContainText("SGD269");
  await expect(page.getByLabel("Comparison and sources")).toBeHidden();
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer")).toContainText("Everyday Sound");
  await page.reload();
  await expect(page.getByLabel("Selected offer")).toContainText("SGD269");
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Decision complete");
  expect(mutations).toEqual([]);
});

test("the cheapest request explains the concrete payment concern and suggests a clean discount", async ({ page }) => {
  await page.goto("/shop");
  await send(page, commute);
  await send(page, "Find the cheapest Echo Quiet offer");
  await expect(page.getByLabel("Merchant caution")).toContainText("gift card");
  const result = page.getByRole("article", { name: "Current recommendation" });
  await expect(result).toContainText("Everyday Sound");
  await expect(result).toContainText("SGD269");
  await expect(page.getByLabel("Merchant caution")).toContainText("SoundRush Deals");
});

test("running shoes negotiate conflicting priorities and reuse the same completion path", async ({ page }) => {
  await page.goto("/shop");
  await send(page, "Running shoes for daily road runs, under SGD200. Cushioning and light weight are equally important.");
  await expect(page.getByLabel("Purchase clarification")).toContainText("priority");
  await page.getByRole("button", { name: "Cushioning first", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Stride Cloud");
  await send(page, "Actually, light weight matters more");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Pace Light");
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer")).toContainText("Pace Light");
});

test("an unchanged winner has a concrete explanation after a genuine priority correction", async ({ page }) => {
  await page.goto("/shop");
  await send(page, "Headphones for commuting under SGD260, noise cancellation first");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Luma Air");
  await send(page, "Actually, comfort matters more");
  await expect(page.getByLabel("What changed")).toContainText("Luma Air still wins");
  await expect(page.getByLabel("What changed")).toContainText("SGD260");
  expect((await page.getByLabel("What changed").innerText()).split(/\s+/).length).toBeLessThanOrEqual(40);
});

test("editing clears a selection and a stale offer cannot be selected", async ({ page }) => {
  await page.goto("/shop");
  await send(page, commute);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await page.getByRole("button", { name: "Revise needs", exact: true }).click();
  await page.getByLabel("Purchase field").selectOption("budget");
  await page.getByLabel("Preference value").fill("180");
  await page.getByRole("button", { name: "Save need", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("article", { name: "Previous recommendation" })).toBeVisible();
  await expect(page.getByRole("status")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Select this offer", exact: true })).toBeDisabled();
  await page.reload();
  await expect(page.getByLabel("Selected offer", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Compare current needs", exact: true }).click();
  await expect(page.getByLabel("No matching offer")).toContainText("SGD180");
});

test("unsupported inputs preserve needs and USD clarification does not silently convert", async ({ page }) => {
  await page.goto("/shop");
  await send(page, "Headphones for commuting under USD300, comfort first");
  await expect(page.getByLabel("Purchase clarification")).toContainText("No conversion");
  await expect(page.getByLabel("Purchase needs")).toContainText("USD");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
  await page.getByRole("button", { name: "Use SGD", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Luma Air");
  await send(page, "Find a laptop instead");
  await expect(page.getByLabel("Purchase clarification")).toContainText("supports headphones and running shoes");
  await expect(page.getByLabel("Purchase needs")).toContainText("300");
  await expect(page.getByLabel("Purchase needs")).toContainText("comfort");
});

test("keyboard controls, evidence focus and narrow layouts work without console errors", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/shop");
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1024, height: 900 });
  const message = page.getByRole("textbox", { name: "Message Beany" });
  await message.fill(commute);
  await message.press("Tab");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  const trace = page.getByText("How I reached this recommendation", { exact: true });
  await trace.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Inspect product comparison", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Product evidence for Echo Quiet", { exact: true })).toBeFocused();
  const activity = page.getByText(/^Compared 2 models · Checked 3 sellers · Excluded 1$/);
  await activity.click();
  await expect(page.getByText(/Compared 2 fictional product records/)).toBeVisible();
  await expect(page.getByText(/Reviewed 3 seller records/)).toBeVisible();
  await expect(page.getByText(/Some return, payment or product-review evidence is unavailable/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("headphones-evidence.png"), fullPage: true });
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  await send(page, "Running shoes for daily road runs under SGD200, cushioning first");
  await page.getByRole("button", { name: "Select this offer", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Stride Cloud");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("shoes-selection.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("unavailable browser storage is visible and does not prevent a decision", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, "getItem", { value: () => { throw new Error("Storage disabled"); } });
    Object.defineProperty(Storage.prototype, "setItem", { value: () => { throw new Error("Storage disabled"); } });
  });
  await page.goto("/shop");
  await expect(page.getByText(/Browser storage is unavailable/)).toBeVisible();
  await send(page, commute);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Decision complete");
});
