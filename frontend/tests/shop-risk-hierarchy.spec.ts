import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import type { Action, MerchantRisk } from "../src/lib/beany";

const API = "http://localhost:8100/shop/sessions";
const secondary = [
  { rule_id: "low_price", evidence: "The listing price is unusually low compared with captured alternatives.", weight: 1 },
  { rule_id: "missing_business", evidence: "The supplied seller page does not include complete business contact details.", weight: 1 },
  { rule_id: "pressure", evidence: "The listing urges buyers to decide before a countdown ends.", weight: 1 },
  { rule_id: "unrecognized_signal", evidence: "An additional recorded observation needs review.", weight: 1 },
];
const concrete = [
  { rule_id: "external_payment", evidence: "The seller requests payment outside the website checkout.", weight: 1 },
  { rule_id: "misleading_returns", evidence: "The advertised return promise conflicts with the supplied return terms.", weight: 1 },
];

function assessment(evidence = secondary): MerchantRisk {
  return { basis: "rules", merchant_id: "presentation-fixture", level: "MEDIUM", score: 4,
    explanation: "Review the supplied evidence before selecting.", evidence,
    recommended_decision: "REVIEW", config_version: "test", config_hash: "test" };
}

// Patch presentation only; the backend policy and persisted proposal remain intact.
async function openOffer(page: Page, request: APIRequestContext, patch: (action: Action) => void) {
  const createdResponse = await request.post(API);
  expect(createdResponse.ok()).toBeTruthy();
  const created = await createdResponse.json();
  const searchedResponse = await request.post(`${API}/${created.session.id}/messages`, {
    data: { revision: created.revision, text: "Find headphones under SGD200; no feature preference" },
  });
  expect(searchedResponse.ok()).toBeTruthy();
  const searched = await searchedResponse.json();
  expect(searched.current).toBeTruthy();
  await page.addInitScript(id => localStorage.setItem("beany-shop-backend-session", id), created.session.id);
  await page.route(`**/shop/sessions/${created.session.id}`, async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.current.decision = "REVIEW";
    body.current.rules = [{ rule_id: "approval", decision: "REVIEW", explanation: "Explicit selection is required." }];
    body.current.risk = assessment();
    patch(body.current);
    await route.fulfill({ response, json: body });
  });
  await page.goto("/");
  const current = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(current).toBeVisible();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  return current;
}

test("secondary concerns use a counted keyboard disclosure without losing evidence", async ({ page, request }) => {
  const current = await openOffer(page, request, () => {});
  const concerns = current.getByRole("region", { name: "Seller and listing concerns", exact: true });
  await expect(concerns.locator("li:visible")).toHaveCount(3);
  const extra = concerns.getByText(secondary[3].evidence, { exact: true });
  await expect(extra).toBeHidden();
  const disclosure = concerns.locator("summary");
  await expect(disclosure).toContainText("1");
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(extra).toBeVisible();
  await expect(concerns.locator("li:visible")).toHaveCount(4);
  await page.keyboard.press("Space");
  await expect(extra).toBeHidden();
  await expect(current.getByRole("button", { name: "Select this offer", exact: true })).toBeEnabled();
});

test("concrete concerns remain visible even when supplied after secondary observations", async ({ page, request }) => {
  const current = await openOffer(page, request, action => { action.risk = assessment([...secondary, ...concrete]); });
  const concerns = current.getByRole("region", { name: "Seller and listing concerns", exact: true });
  for (const item of concrete) {
    const row = concerns.getByRole("listitem").filter({ hasText: item.evidence });
    await expect(row).toBeVisible();
    await expect(row).toHaveClass(/concern-danger/);
    await expect(row.locator("svg")).toHaveCount(1);
  }
  await expect(concerns.getByRole("listitem").filter({ hasText: secondary[0].evidence })).toHaveClass(/concern-review/);
});

test("blocked offers keep every concern and policy reason visible and disable purchase actions", async ({ page, request }) => {
  const reason = "This seller is excluded by your shopping rules.";
  const current = await openOffer(page, request, action => {
    action.decision = "BLOCK";
    action.risk = assessment([...secondary, ...concrete]);
    action.rules.push({ rule_id: "restricted_merchant", decision: "BLOCK", explanation: reason });
  });
  const concerns = current.getByRole("region", { name: "Seller and listing concerns", exact: true });
  for (const item of [...secondary, ...concrete]) await expect(concerns.getByText(item.evidence, { exact: true })).toBeVisible();
  await expect(current.getByText(reason, { exact: true })).toBeVisible();
  await expect(current.getByRole("button", { name: "Select this offer", exact: true })).toBeDisabled();
  await expect(current.getByRole("button", { name: "Add to cart", exact: true })).toBeDisabled();
});

test("a merchant risk block explanation remains visible when no individual evidence was supplied", async ({ page, request }) => {
  const reason = "The merchant risk assessment exceeds your configured shopping limit.";
  const current = await openOffer(page, request, action => {
    action.decision = "BLOCK";
    action.risk = assessment([]);
    action.rules.push({ rule_id: "merchant_risk", decision: "BLOCK", explanation: reason });
  });
  await expect(current.getByText(reason, { exact: true })).toBeVisible();
  await expect(current.getByRole("button", { name: "Select this offer", exact: true })).toBeDisabled();
  await expect(current.getByRole("button", { name: "Add to cart", exact: true })).toBeDisabled();
});

test("missing assessments remain neutral and explicitly unknown", async ({ page, request }) => {
  const current = await openOffer(page, request, action => {
    action.risk = null;
    if (action.merchant_details) action.merchant_details.site = null;
  });
  const risk = current.locator(".cui-risk-badge");
  await expect(risk).toContainText("Unknown");
  await expect(risk).toHaveClass(/cui-tone-unknown/);
  await expect(current.locator(".cui-site-badge")).toHaveClass(/cui-site-unknown/);
  await expect(current.locator(".cui-policy-badge")).toHaveClass(/cui-tone-medium/);
  await expect(current.locator(".cui-policy-badge")).toContainText("Needs your approval");
  await expect(current).toContainText("risk remains unknown");
});

test("low estimated risk stays neutral rather than implying a safety certification", async ({ page, request }) => {
  const current = await openOffer(page, request, action => {
    action.risk = { ...assessment([]), level: "LOW", score: 0 };
  });
  await expect(current.locator(".cui-risk-badge")).toHaveText("Estimated merchant risk: Low");
  await expect(current.locator(".cui-risk-badge")).toHaveClass(/cui-tone-unknown/);
  await expect(current).toContainText("not proof of fraud or a safety guarantee");
});

test("Change your needs opens and focuses the existing editor", async ({ page, request }) => {
  const current = await openOffer(page, request, () => {});
  await current.getByRole("button", { name: "Change your needs", exact: true }).click();
  const editor = page.getByRole("region", { name: "Purchase needs", exact: true }).getByRole("form", { name: /^Edit / });
  await expect(editor).toBeVisible();
  await expect(editor.locator("input, select").first()).toBeFocused();
  await editor.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(editor).toHaveCount(0);
  await current.getByRole("button", { name: "Change your needs", exact: true }).click();
  await expect(editor).toBeVisible();
  await expect(editor.locator("input, select").first()).toBeFocused();
  await editor.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(editor).toHaveCount(0);
  await expect(current.getByRole("button", { name: "Select this offer", exact: true })).toBeEnabled();
});

test("long content preserves assessment-before-action order and layout at all target widths", async ({ page, request }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const current = await openOffer(page, request, action => {
    action.product.name = "E7 Active Noise Cancelling Headphones Wireless 5.0 Bluetooth Headphones with Rich Bass";
    action.risk = assessment([concrete[1]]);
    if (action.merchant_details) action.merchant_details.return_policy = "Returns accepted within thirty days, subject to the supplied packaging and condition requirements.";
  });
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const layout = await current.evaluate(card => {
      const assessment = card.querySelector<HTMLElement>('[aria-label="Merchant and website assessment"]')!;
      const actions = card.querySelector<HTMLElement>('[aria-label="Offer actions"]')!;
      const head = card.querySelector<HTMLElement>(".cui-offer-head")!;
      const riskRect = assessment.getBoundingClientRect(), actionRect = actions.getBoundingClientRect(), headRect = head.getBoundingClientRect();
      const buttons = Array.from(actions.querySelectorAll("button")).map(button => button.getBoundingClientRect());
      return {
        assessmentFirst: Boolean(assessment.compareDocumentPosition(actions) & Node.DOCUMENT_POSITION_FOLLOWING),
        headBottom: headRect.bottom, assessmentTop: riskRect.top,
        assessmentBottom: riskRect.bottom, actionsTop: actionRect.top,
        horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
        overflowElements: Array.from(document.querySelectorAll<HTMLElement>("body *")).filter(element => {
          if (element.matches(".cui-skip, .sr-only") || element.closest(".sr-only")) return false;
          const rect = element.getBoundingClientRect(), style = getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none"
            && (rect.right > innerWidth || rect.left < 0);
        }).map(element => {
          const rect = element.getBoundingClientRect();
          return { tag: element.tagName, className: element.className, text: element.textContent?.slice(0, 80), left: rect.left, right: rect.right, width: rect.width };
        }),
        buttonsOverlap: buttons.some((a, i) => buttons.slice(i + 1).some(b => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)),
      };
    });
    if (width === 320 || width === 1440 || layout.horizontalOverflow) {
      await current.scrollIntoViewIfNeeded();
      await page.screenshot({ path: testInfo.outputPath(`risk-hierarchy-${width}.png`), fullPage: true });
    }
    if (layout.horizontalOverflow) {
      await testInfo.attach(`overflow-${width}.json`, { body: JSON.stringify(layout.overflowElements, null, 2), contentType: "application/json" });
    }
    expect(layout.assessmentFirst, `reading order at ${width}px`).toBe(true);
    expect(layout.assessmentTop, `title clearance at ${width}px`).toBeGreaterThanOrEqual(layout.headBottom - 1);
    expect(layout.actionsTop, `warning clearance at ${width}px`).toBeGreaterThanOrEqual(layout.assessmentBottom - 1);
    expect(layout.horizontalOverflow, `horizontal overflow at ${width}px: ${JSON.stringify(layout.overflowElements)}`).toBe(false);
    expect(layout.buttonsOverlap, `button overlap at ${width}px`).toBe(false);
  }
  expect(errors).toEqual([]);
});
