import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
const MID = { domain: "dealbazaar.test", name: "DealBazaar", kind: "marketplace", tier: "mid", label: "Loosely regulated marketplace", summary: "Loosely regulated sellers; product quality varies; refunds are inconvenient." };

// Component rendering cases use a saved cart and a labelled response patch, not live evidence.
async function openWithMerchant(page: Page, request: APIRequestContext, patch: Record<string, unknown>) {
  const s = await (await request.post("http://localhost:8100/sessions")).json();
  const found = await (await request.post(`http://localhost:8100/sessions/${s.id}/messages`, { data: { text: "Find headphones under SGD150" } })).json();
  const a = found.proposals.at(-1);
  expect((await request.post(`http://localhost:8100/sessions/${s.id}/cart`, { data: { proposal_id: a.id, fingerprint: a.fingerprint } })).ok()).toBeTruthy();
  await page.route(`**/shop/sessions/${s.id}/adopt`, async route => {
    const response = await route.fetch(); const body = await response.json();
    Object.assign(body.cart_review[0].action.merchant_details, patch);
    await route.fulfill({ response, json: body });
  });
  await page.addInitScript(id => localStorage.setItem("beany-session", id), s.id);
  await page.goto("/cart");
  await page.getByText(/^Review merchant details/).first().click();
  return page.locator(".merchant-details").first();
}

test("merchant details show the website reputation meter", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, { website: "https://dealbazaar.test/store/harbour-deals", site: MID });
  await expect(details).toContainText("Simulated website: dealbazaar.test");
  await expect(details).toContainText("Website reputation: Mid");
  await expect(details).toContainText("Loosely regulated marketplace");
  await expect(details).not.toContainText("harbour-deals");
  const meter = details.locator('.site-meter[aria-hidden="true"]');
  await expect(meter).toHaveCount(1); await expect(meter.locator("span")).toHaveCount(3); await expect(meter.locator(".filled")).toHaveCount(2);
});
test("merchant without a registered site shows no reputation", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, { site: null });
  await expect(details).toContainText("Simulated website:"); await expect(details).not.toContainText("Website reputation"); await expect(details.locator(".site-meter")).toHaveCount(0);
});
test("an unparseable website is shown as written", async ({ page, request }) => {
  const details = await openWithMerchant(page, request, { website: "not a url", site: null });
  await expect(details).toContainText("Simulated website: not a url");
});
