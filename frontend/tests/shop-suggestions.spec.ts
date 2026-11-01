import { test, expect } from "@playwright/test";
const API = "http://localhost:8100/shop/sessions";

for (const suggestion of ["Show me some options", "Find an alternative", "Cancel this task"]) {
  test(`${suggestion} gives a relevant response and preserves safeguards`, async ({ page, request }, testInfo) => {
    const created = await (await request.post(API)).json();
    const baseline = await (await request.post(`${API}/${created.session.id}/messages`, { data: { revision: created.revision, text: "Find wireless noise-cancelling headphones under SGD200 for my commute." } })).json();
    expect(baseline.current).toBeTruthy();
    await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
    await page.goto("/");
    const current = page.getByRole("article", { name: "Current recommendation", exact: true });
    await expect(current).toContainText(baseline.current.product.name);
    await page.getByRole("button", { name: "Select this offer", exact: true }).click();
    await expect(page.getByRole("button", { name: "Finish decision", exact: true })).toBeEnabled();
    await page.getByRole("button", { name: suggestion, exact: true }).click();
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
    const response = page.locator(".cui-chat-answer").last();
    const saved = await (await request.get(`${API}/${created.session.id}`)).json();
    expect(saved.session.messages.filter((m: { role: string; text: string }) => m.role === "user" && m.text === suggestion)).toHaveLength(1);
    expect(saved.session.brief).toEqual(baseline.session.brief);
    expect(saved.session.receipts).toHaveLength(0);
    if (suggestion === "Show me some options") {
      await expect(response).toContainText("Here are matching models");
      const table = response.getByRole("table", { name: "Matching model options" });
      await expect(table).toBeVisible();
      expect(await table.locator("tbody tr").count()).toBeGreaterThan(1);
      await expect(table.getByRole("columnheader")).toHaveText(["Model / seller", "Price", "Listed features", "Returns"]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(saved.current.id).toBe(baseline.current.id);
      expect(saved.selected).toBeTruthy();
      await expect(page.getByRole("button", { name: "Finish decision", exact: true })).toBeEnabled();
    } else if (suggestion === "Find an alternative") {
      await expect(response).toContainText("A different model to review:");
      await expect(response).toContainText(`Previously: ${baseline.current.product.name}`);
      expect(saved.current.product.name).not.toBe(baseline.current.product.name);
      expect(saved.current.decision).not.toBe("BLOCK");
      expect(saved.current.product.price).toBeLessThanOrEqual(200);
      expect(saved.selected).toBeNull();
      await expect(response).toContainText("Any previous selection was cleared");
    } else {
      await expect(response).toContainText("Shopping task cancelled. Nothing was purchased.");
      expect(saved.session.stage).toBe("cancelled");
      expect(saved.current).toBeNull();
      expect(saved.selected).toBeNull();
      expect(saved.session.suggestions).toEqual([]);
      await expect(page.getByRole("button", { name: "Select this offer", exact: true })).toHaveCount(0);
      await expect(page.getByRole("button", { name: suggestion, exact: true })).toHaveCount(0);
    }
    await page.screenshot({ path: testInfo.outputPath("suggestion-result.png") });
  });
}
