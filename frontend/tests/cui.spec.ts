import { test, expect } from "@playwright/test";

const request = "Headphones for my daily train commute, under SGD300. Noise cancellation matters more than weight.";

test("a specific request receives one short personalised recommendation", async ({ page }) => {
  const paidCalls: string[] = [];
  page.on("request", r => { if (/openai|browser-use/.test(r.url())) paidCalls.push(r.url()); });
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill(request);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const result = page.getByRole("article", { name: "Current recommendation" });
  await expect(result.getByRole("heading", { name: "Echo Quiet" })).toBeVisible();
  await expect(result).toContainText("Northline Audio");
  await expect(result).toContainText("SGD289");
  await expect(result).toContainText("Luma Air");
  await expect(result).toContainText("45g");
  const rationale = result.getByLabel("Why I recommend this for you");
  expect((await rationale.innerText()).split(/\s+/).length).toBeLessThanOrEqual(120);
  await expect(page.getByText("Fictional catalogue", { exact: false })).toBeVisible();
  expect(paidCalls).toEqual([]);
});
