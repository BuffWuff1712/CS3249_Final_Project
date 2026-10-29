import { test, expect, type Page } from "@playwright/test";

const MID = {
  domain: "dealbazaar.test",
  name: "DealBazaar",
  kind: "marketplace",
  tier: "mid",
  label: "Loosely regulated marketplace",
  summary: "Loosely regulated sellers; product quality varies; refunds are inconvenient.",
};

// Open the proposal with its merchant details rewritten, so each case is deterministic.
async function openWithMerchant(page: Page, request: import("@playwright/test").APIRequestContext, patch: Record<string, unknown>) {
  const session = await (await request.post("http://localhost:8100/sessions")).json();
  await request.post(`http://localhost:8100/sessions/${session.id}/messages`, { data: { text: "Find headphones under $150" } });
  await page.route(`**/sessions/${session.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const body = await response.json();
    Object.assign(body.proposals[0].merchant_details, patch);
    await route.fulfill({ response, json: body });
  });
  await page.addInitScript((id) => localStorage.setItem("beany-session", id), session.id);
  await page.goto("/");
  await page.getByText(/^Review merchant details/).first().click();
  return page.locator(".merchant-details").first();
}

test("merchant details show the website reputation meter", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, {
    website: "https://dealbazaar.test/store/harbour-deals",
    site: MID,
  });
  await expect(details).toContainText("Simulated website: dealbazaar.test");
  await expect(details).toContainText("Website reputation: Mid");
  await expect(details).toContainText("Loosely regulated marketplace");
  await expect(details).not.toContainText("harbour-deals");
  const meter = details.locator('.site-meter[aria-hidden="true"]');
  await expect(meter).toHaveCount(1);
  await expect(meter.locator("span")).toHaveCount(3);
  await expect(meter.locator(".filled")).toHaveCount(2);
});

test("merchant without a registered site shows no reputation", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, { site: null });
  await expect(details).toContainText("Simulated website:");
  await expect(details).not.toContainText("Website reputation");
  await expect(details.locator(".site-meter")).toHaveCount(0);
});

test("an unparseable website is shown as written", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, { website: "not a url", site: null });
  await expect(details).toContainText("Simulated website: not a url");
});
