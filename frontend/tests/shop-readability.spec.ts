import { test, expect } from "@playwright/test";
const API = "http://localhost:8100/shop/sessions";

test("priorities, fractional ratings, unique evidence and compact seller controls preserve the offer", async ({ page, request }, testInfo) => {
  const created = await (await request.post(API)).json();
  const searched = await (await request.post(`${API}/${created.session.id}/messages`, { data: { revision: created.revision, text: "Find headphones under SGD200; no feature preference" } })).json();
  const edited = await (await request.put(`${API}/${created.session.id}/brief`, { data: { revision: searched.revision, field: "features", fact: { value: "wireless, noise cancellation, long battery", source: "confirmed", hard: false } } })).json();
  const compared = await (await request.post(`${API}/${created.session.id}/compare`, { data: { revision: edited.revision } })).json();
  const lion = compared.offers.find((offer: { product: { id: string } }) => offer.product.id === "study-hp-target-inconsistent");
  expect(lion).toBeTruthy();
  const proposed = await request.post(`${API}/${created.session.id}/propose`, { data: { revision: compared.revision, product_id: lion.product.id } });
  expect(proposed.ok()).toBeTruthy();
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
  await page.setViewportSize({ width: testInfo.project.name === "mobile" ? 320 : 1280, height: 900 });
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  const matches = current.getByRole("region", { name: "Priority matches", exact: true });
  await expect(matches.locator("li")).toHaveText(["Within your SGD200 budget (currency assumed)", "wireless", "noise cancellation"]);
  await expect(matches).toContainText(/Not established from listed features: long[- ]battery/);
  await expect(current.getByRole("img", { name: "4.6 out of 5 stars", exact: true })).toBeVisible();
  await expect(current.getByRole("img", { name: "4 out of 5 stars", exact: true })).toBeVisible();
  await expect(current).toContainText("2,310 aggregate ratings");
  await expect(current).toContainText("133 aggregate ratings");
  const fractional = await current.locator(".cui-stars").first().locator(".cui-star-fill").last().evaluate(element => element.getBoundingClientRect().width);
  expect(fractional).toBeCloseTo(8.4, 1);
  await expect(current.locator(".cui-key-spec")).toHaveText("Up to 40 hours");
  await expect(current.getByText("Merchant and product information is inconsistent in the fixture.", { exact: true })).toHaveCount(1);
  await expect(current.getByRole("region", { name: "Seller and listing concerns", exact: true })).toContainText("Conflicting information");
  await expect(current.getByText("Conflicting information", { exact: true })).toBeVisible();
  await expect(current.getByRole("region", { name: "Seller and listing concerns", exact: true }).locator("details")).toHaveCount(0);
  await expect(current).toContainText("not proof of fraud or a safety guarantee");
  const sellers = page.getByRole("table", { name: "Compare sellers of this model", exact: true });
  const selected = sellers.getByRole("row", { name: "Seller offer Lion City Sports Hub", exact: true });
  await expect(selected.getByRole("button", { name: "Compare offer from Lion City Sports Hub", exact: true })).toHaveText("Current offer");
  const blocked = sellers.getByRole("row", { name: "Seller offer Everyday Value Co", exact: true });
  await expect(blocked.getByRole("button", { name: "Compare offer from Everyday Value Co", exact: true })).toBeDisabled();
  await expect(blocked).toContainText("Website reputation: Good");
  await expect(blocked).toContainText("Seller risk: high estimate");
  await expect(blocked.getByRole("button", { name: "Compare offer from Everyday Value Co", exact: true })).toHaveText("Blocked");
  await expect(blocked).not.toContainText("not proof of fraud");
  const amountsFit = await sellers.locator(".cui-money-amount").evaluateAll(elements => elements.every(element => { const range = document.createRange(); range.selectNodeContents(element); const rects = [...range.getClientRects()]; return rects.length === 1 && rects[0].right <= element.closest("td")!.getBoundingClientRect().right; }));
  expect(amountsFit).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await sellers.getByRole("button", { name: "Compare offer from Bargain Depot SG", exact: true }).click();
  await expect(current).toContainText("Bargain Depot SG");
  await page.getByRole("button", { name: "Select this offer", exact: true }).click();
  await expect(page.getByRole("button", { name: "Finish decision", exact: true })).toBeEnabled();
  expect(errors).toEqual([]);
});

test("missing ratings and assessments remain unknown rather than reassuring", async ({ page, request }) => {
  const created = await (await request.post(API)).json();
  const searched = await (await request.post(`${API}/${created.session.id}/messages`, { data: { revision: created.revision, text: "Find headphones under SGD200; no feature preference" } })).json();
  const unknown = searched.offers.find((offer: { product: { rating: number | null }; decision: string }) => offer.product.rating == null && offer.decision !== "BLOCK");
  expect(unknown).toBeTruthy();
  await request.post(`${API}/${created.session.id}/propose`, { data: { revision: searched.revision, product_id: unknown.product.id } });
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
  await page.route(`**/shop/sessions/${created.session.id}`, async route => { const response = await route.fetch(); const body = await response.json(); body.current.risk = null; body.current.merchant_details.site = null; body.current.merchant_details.review_rating = null; await route.fulfill({ response, json: body }); });
  await page.goto("/");
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current.getByText("Rating not supplied", { exact: true })).toHaveCount(2);
  await expect(current.getByRole("img", { name: /out of 5 stars/ })).toHaveCount(0);
  await expect(current).toContainText("Merchant risk: Unknown");
  await expect(current).toContainText("Website reputation: Unknown");
});

test("budget-only matches respect limits, targets, currency and missing values", async ({ page, request }) => {
  const created = await (await request.post(API)).json();
  const view = await (await request.post(`${API}/${created.session.id}/messages`, { data: { revision: created.revision, text: "Find headphones under SGD200; no feature preference" } })).json();
  expect(view.current).toBeTruthy();
  const price = view.current.product.price;
  let brief: Record<string, { value: string; source: string; hard: boolean }> = {};
  // Only replace saved-brief presentation to exercise impossible and unknown UI states;
  // the backend's actual budget/approval policy is unchanged.
  await page.route(`**/shop/sessions/${created.session.id}`, async route => {
    const response = await route.fetch(); const body = await response.json();
    body.session.brief = brief;
    await route.fulfill({ response, json: body });
  });
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
  const budget = (value: string, hard = true, source = "confirmed") => ({ value, hard, source });
  const currency = (value: string) => budget(value, false);
  const cases = [
    { brief: { budget: budget("200"), currency: currency("SGD") }, chip: "Within your SGD200 budget", note: "" },
    { brief: { budget: budget(String(price)), currency: currency("SGD") }, chip: `Within your SGD${price} budget`, note: "" },
    { brief: { budget: budget("200", false), currency: currency("SGD") }, chip: "Within your SGD200 target budget", note: "" },
    { brief: { budget: budget(String(price - 1)), currency: currency("SGD") }, chip: "", note: `Above your SGD${price - 1} budget` },
    { brief: { budget: budget("200"), currency: currency("USD") }, chip: "", note: "Budget match unconfirmed" },
    { brief: { budget: budget("200") }, chip: "Within your SGD200 budget (currency assumed)", note: "" },
    { brief: { budget: budget("200", true, "suggested"), currency: currency("SGD") }, chip: "", note: "" },
    { brief: { budget: budget("not a number"), currency: currency("SGD") }, chip: "", note: "" },
    { brief: {}, chip: "", note: "" },
  ];
  for (const scenario of cases) {
    brief = scenario.brief as typeof brief;
    await page.goto("/");
    const current = page.getByRole("article", { name: "Current recommendation", exact: true });
    await expect(current).toBeVisible();
    const matches = current.getByRole("region", { name: "Priority matches", exact: true });
    if (scenario.chip) await expect(matches.locator("li")).toHaveText([scenario.chip]);
    else await expect(matches.locator("li")).toHaveCount(0);
    if (scenario.note) await expect(matches).toContainText(scenario.note);
    if (!scenario.chip && !scenario.note) await expect(matches).toHaveCount(0);
  }
});
