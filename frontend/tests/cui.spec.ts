import { test, expect } from "@playwright/test";

const request = "Headphones for my daily train commute, under SGD300. Noise cancellation matters more than weight.";

test("expanded reasoning links five decision steps to evidence and editable priorities", async ({ page }) => {
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill(request);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const control = page.getByText("How I reached this recommendation", { exact: true });
  await expect(control).toBeVisible();
  await control.click();
  await expect(page.getByRole("list", { name: "Decision steps" }).getByRole("listitem")).toHaveCount(5);
  await page.getByRole("button", { name: "Inspect product comparison" }).click();
  await expect(page.getByLabel("Comparison and sources")).toBeVisible();
  await page.getByRole("button", { name: "Change this priority" }).click();
  await expect(page.getByLabel("Purchase field")).toHaveValue("priority");
  await expect(page.getByLabel("Preference value")).toBeFocused();
});

test("source evidence is optional and separates product reviews from seller reputation", async ({ page }) => {
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill(request);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("Comparison and sources")).toBeHidden();
  await page.getByText("View comparison and sources", { exact: true }).click();
  const evidence = page.getByLabel("Comparison and sources");
  await expect(evidence).toContainText("730 product reviews");
  await expect(evidence).toContainText("2,140 seller reviews");
  await expect(evidence).toContainText("Unknown; not supplied");
  await expect(evidence).toContainText("echo-quiet-northline");
});

test("clarification asks one useful question and permits browsing without an invented limit", async ({ page }) => {
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill("headphones");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("Purchase clarification")).toContainText("mainly use");
  await expect(page.getByRole("article", { name: "Current recommendation" })).toHaveCount(0);
  await page.getByRole("button", { name: "Commuting", exact: true }).click();
  await expect(page.getByLabel("Purchase clarification")).toContainText("spending");
  await page.getByRole("button", { name: "Show options", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toBeVisible();
  await expect(page.getByLabel("Purchase needs")).not.toContainText("300");
  await expect(page.getByLabel("Why I recommend this for you")).toContainText("No spending limit is confirmed");
});

test("purchase needs can be edited without inheriting a constraint and survive refresh", async ({ page }) => {
  await page.goto("/shop");
  await page.getByRole("textbox", { name: "Message Beany" }).fill(request);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toBeVisible();
  await page.getByText("Edit purchase needs", { exact: true }).click();
  await page.getByLabel("Purchase field").selectOption("budget");
  await page.getByLabel("Preference value").fill("280");
  await page.getByRole("button", { name: "Save need" }).click();
  await expect(page.getByRole("article", { name: "Previous recommendation" })).toBeVisible();
  await page.getByRole("button", { name: "Compare current needs" }).click();
  await expect(page.getByRole("article", { name: "Current recommendation" })).toContainText("Everyday Sound");
  await page.reload();
  await expect(page.getByLabel("Purchase needs")).toContainText("280");
  await page.getByText("Edit purchase needs", { exact: true }).click();
  await page.getByLabel("Purchase field").selectOption("priority");
  await expect(page.getByRole("checkbox", { name: "Must have" })).not.toBeChecked();
  await page.getByLabel("Preference value").fill("battery life");
  await page.getByRole("button", { name: "Save need" }).click();
  await expect(page.getByLabel("Purchase needs").getByRole("alert")).toContainText("Choose comfort or noise cancellation");
});

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
  await expect(page.getByText(/^Fictional catalogue ·/)).toBeVisible();
  expect(paidCalls).toEqual([]);
});
