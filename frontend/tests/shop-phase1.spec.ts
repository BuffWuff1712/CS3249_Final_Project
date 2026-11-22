import { test, expect } from "@playwright/test";

test("screened shortlist has one primary and at most two alternatives; checkout stays explicit", async ({ page }) => {
  await page.goto("/shop");
  const send = page.getByRole("button", { name: "Send", exact: true });
  await expect(send).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find wireless headphones under SGD200");
  await send.click();
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current).toBeVisible();
  const options = page.getByLabel("Compare your match with").locator("option");
  expect(await options.count()).toBeLessThanOrEqual(2);
  expect(await options.count()).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("No receipt");
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByRole("region", { name: "Conversation history" })).toContainText("Simulated checkout complete");
});
