import { test, expect } from "@playwright/test";

// A refused action (the backend raises before saving) must explain itself and leave every
// control usable; only an uncertain failure should pause the workspace until it is reloaded.
test("a refused action keeps the workspace usable", async ({ page }) => {
  await page.goto("/shop");
  const send = page.getByRole("button", { name: "Send", exact: true });
  await expect(send).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200; no feature preference");
  await send.click();
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toBeVisible();
  await expect(send).toBeEnabled();

  await page.route(/\/seller\/stream$/, route => route.fulfill({
    status: 200, contentType: "application/x-ndjson",
    body: JSON.stringify({ type: "error", message: "No other eligible seller for this exact model and variant fits your needs. Your current choice is unchanged.", rejected: true }) + "\n",
  }));
  await page.getByRole("button", { name: /Find another seller/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "No other eligible seller" })).toBeVisible();
  await expect(page.getByText("Selection and checkout are paused")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Find another product/ })).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("hello");
  await expect(send).toBeEnabled();
  await page.unroute(/\/seller\/stream$/);
});

test("an uncertain failure still pauses the workspace until it is reloaded", async ({ page }) => {
  await page.goto("/shop");
  const send = page.getByRole("button", { name: "Send", exact: true });
  await expect(send).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200; no feature preference");
  await send.click();
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toBeVisible();
  await page.route(/\/seller\/stream$/, route => route.fulfill({
    status: 200, contentType: "application/x-ndjson",
    body: JSON.stringify({ type: "error", message: "The request could not finish." }) + "\n",
  }));
  await page.getByRole("button", { name: /Find another seller/ }).click();
  await expect(page.getByText("Selection and checkout are paused")).toBeVisible();
  await page.unroute(/\/seller\/stream$/);
  await page.getByRole("button", { name: "Reload workspace" }).click();
  await expect(send).toBeEnabled();
});
