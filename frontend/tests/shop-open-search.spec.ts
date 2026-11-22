import { test, expect } from "@playwright/test";

for (const provider of ["browser_use", "shopify_catalog", "hybrid"]) test(`${provider} category editor accepts a product outside the demo list`, async ({ page }) => {
  // Offline UI contract fixture: change only provider metadata, keep real session/edit routes.
  await page.route("**/shop/sessions**", async route => {
    const response = await route.fetch();
    if (!response.headers()["content-type"]?.includes("application/json")) return route.fulfill({ response });
    const data = await response.json();
    if (data.session) { data.session.search_provider = provider; data.session.search_replay = ""; }
    await route.fulfill({ response, json: data });
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Edit buying: not set" }).click();
  await page.getByRole("textbox", { name: "Product category" }).fill("Coffee machine");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit buying: Coffee machine" })).toBeVisible();
});

test("catalogue editor still offers catalogue categories", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Edit buying: not set" }).click();
  await expect(page.getByRole("combobox", { name: "Category", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Category", exact: true }).selectOption("Headphones");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit buying: Headphones" })).toBeVisible();
});
