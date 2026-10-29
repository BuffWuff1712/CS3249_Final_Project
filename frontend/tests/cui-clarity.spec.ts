import { test, expect, type Page } from "@playwright/test";

async function requestHeadphones(page: Page) {
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Headphones for my train commute, under SGD300. Noise cancellation first.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
}

test("purchase intent and the reasons for the model and seller are explicitly labelled", async ({ page }) => {
  await requestHeadphones(page);
  const intent = page.getByLabel("Purchase needs", { exact: true });
  await expect(intent.getByRole("heading", { name: "Your purchase intent" })).toBeVisible();
  for (const label of ["Buying", "For", "Spending limit", "Most important"]) await expect(intent.getByRole("term").filter({ hasText: new RegExp(`^${label}$`) })).toBeVisible();
  const reasoning = page.getByLabel("Why I recommend this for you", { exact: true });
  for (const label of ["Your intent", "Model choice", "Seller choice", "Trade-off"]) await expect(reasoning.getByText(label, { exact: true })).toBeVisible();
});

test("a blocked seller has a prominent red flag, exact offer, evidence and actionable alternative", async ({ page }, testInfo) => {
  await requestHeadphones(page);
  const flag = page.getByLabel("Merchant caution", { exact: true });
  await expect(flag).toBeVisible();
  await expect(flag).toHaveAttribute("data-severity", "blocked");
  await expect(flag).toContainText("Possible scam risk");
  await expect(flag).toContainText("SoundRush Deals");
  await expect(flag).toContainText("SGD209");
  await expect(flag).toContainText("gift card");
  await expect(flag).toContainText("offer is blocked");
  expect(await flag.evaluate(element => getComputedStyle(element).borderLeftColor)).toBe("rgb(180, 35, 24)");
  await flag.screenshot({ path: testInfo.outputPath("red-risk-flag.png") });
  await page.getByLabel("Purchase needs", { exact: true }).screenshot({ path: testInfo.outputPath("purchase-intent.png") });
  await flag.getByRole("button", { name: "Use Northline Audio · SGD289", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Northline Audio");
  await expect(page.getByLabel("Selected offer", { exact: true })).not.toContainText("SoundRush Deals");
});

test("budget conflicts are red and offer a concrete recovery action", async ({ page }) => {
  await requestHeadphones(page);
  await page.getByRole("textbox", { name: "Message Beany" }).fill("My budget is now SGD180");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const conflict = page.getByLabel("No matching offer", { exact: true });
  await expect(conflict).toHaveAttribute("data-severity", "error");
  await expect(conflict).toContainText("SGD180");
  await conflict.getByRole("button", { name: "Change spending limit", exact: true }).click();
  await expect(page.getByLabel("Purchase field")).toHaveValue("budget");
  await expect(page.getByLabel("Preference value")).toBeFocused();
});

test("trying an example makes the intended purchase request editable before sending", async ({ page }) => {
  await page.goto("/shop");
  await page.getByRole("button", { name: "Try headphones", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Message Beany" })).toHaveValue(/Headphones.*SGD300/);
  await expect(page.getByRole("textbox", { name: "Message Beany" })).toBeFocused();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
});
