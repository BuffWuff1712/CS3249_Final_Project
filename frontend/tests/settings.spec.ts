import { test, expect } from "@playwright/test";

test("gear opens session permissions and saves them across navigation", async ({ page, request }) => {
  await page.goto("/");
  const gear = page.getByRole("button", { name: "Open settings" });
  await expect(gear).toBeEnabled();
  const id = await page.evaluate(() => localStorage.getItem("beany-session"));
  await expect(page.getByRole("heading", { name: "Permissions", exact: true })).toHaveCount(0);
  await gear.click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("checkbox", { name: "require approval" })).toBeChecked();
  await page.getByRole("checkbox", { name: "substitutions", exact: true }).check();
  await page.getByLabel("Restricted merchants (comma separated)").fill("Shop A, Shop B");
  await page.getByRole("button", { name: "Save permissions" }).click();
  await expect(page.getByRole("status")).toContainText("Permissions saved");
  const saved = await (await request.get(`http://localhost:8100/sessions/${id}`)).json();
  expect(saved.permissions.substitutions).toBe(true);
  expect(saved.permissions.restricted_merchants).toEqual(["Shop A", "Shop B"]);
  await page.getByRole("button", { name: "Back to shopping" }).click();
  await expect(gear).toBeEnabled();
  expect(await page.evaluate(() => localStorage.getItem("beany-session"))).toBe(id);
  await gear.click();
  await expect(page.getByRole("checkbox", { name: "substitutions", exact: true })).toBeChecked();
  await expect(page.getByLabel("Restricted merchants (comma separated)")).toHaveValue("Shop A, Shop B");
});

test("settings without a session explains how to start", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("alert")).toContainText("Start a shopping session");
  await expect(page.getByRole("button", { name: "Save permissions" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Back to shopping" })).toBeEnabled();
});
