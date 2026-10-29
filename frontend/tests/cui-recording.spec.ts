import { test, expect, type Page } from "@playwright/test";

test.use({ video: "on" });
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill(text);
  await page.getByRole("button", { name: "Send", exact: true }).click();
}

test("record both working CUI scenarios with correction and informed selection", async ({ page }, testInfo) => {
  await page.goto("/shop");
  await send(page, "Headphones for my daily train commute under SGD300, noise cancellation first");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Echo Quiet");
  await page.getByRole("article", { name: "Current recommendation" }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("headphones-recommendation.png"), fullPage: true });
  await send(page, "Actually, comfort matters more");
  await expect(page.getByLabel("What changed")).toContainText("Luma Air");
  await page.getByText("How I reached this recommendation", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Product comparison Updated", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Eligibility decisions", exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("headphones-correction.png"), fullPage: true });
  await send(page, "Find the cheapest Echo Quiet offer");
  await expect(page.getByLabel("Merchant caution", { exact: true })).toContainText("gift card");
  await expect(page.getByLabel("Merchant caution", { exact: true })).toContainText("Everyday Sound at SGD269");
  await page.getByLabel("Merchant caution", { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("headphones-caution.png"), fullPage: true });
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Decision complete");
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  await send(page, "Running shoes for daily road runs under SGD200. Cushioning and light weight are equally important.");
  await page.getByRole("button", { name: "Cushioning first", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Stride Cloud");
  await send(page, "Actually, light weight matters more");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Pace Light");
  await send(page, "Keep the product but find another seller");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("SGD149");
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await page.getByRole("button", { name: "Finish decision", exact: true }).click();
  await expect(page.getByLabel("Selected offer", { exact: true })).toContainText("Everyday Run");
  await page.getByLabel("Selected offer", { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("shoes-decision.png"), fullPage: true });
});
