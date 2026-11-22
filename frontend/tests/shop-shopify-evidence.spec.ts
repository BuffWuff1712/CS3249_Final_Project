import { test, expect } from "@playwright/test";

test("Shopify evidence is visible without inventing reviews or confirming inferred features", async ({ page, request }) => {
  const created = await request.post("http://localhost:8100/shop/sessions");
  let view = await created.json();
  const searched = await request.post(`http://localhost:8100/shop/sessions/${view.session.id}/messages`, {
    data: { revision: view.revision, text: "Find wireless headphones under SGD200" },
  });
  view = await searched.json();
  expect(view.current).toBeTruthy();
  Object.assign(view.current.product, {
    source: "shopify_catalog", attributes: [], inferred_attributes: ["Wireless connectivity", "Active noise cancellation"],
    selling_points: ["Lightweight for travel"], rating: 4.8, rating_count: 483, rating_scope: "product", reviews: [],
    description: "Black edition & carrying case\n50 hours battery life", specifications: { Color: "Black", Condition: "new" },
    stock: true, list_price: 100, policy_links: {
      refund_policy: "https://checkout.shopify.com/10/policies/123.html", shipping_policy: "https://merchant.example/policies/shipping",
      privacy_policy: "javascript:alert(1)",
    },
  });
  // The fabricated product replaces the one the backend checked, so its feature verdicts no longer apply.
  view.current.feature_fit = [{ feature: "wireless", status: "unknown", quote: "" }];
  await page.route("**/shop/sessions**", route => route.fulfill({ json: view }));
  await page.goto("/");
  const offer = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(offer.getByRole("heading", { name: "Catalogue highlights" }).first()).toBeVisible();
  await expect(offer.getByText("Wireless connectivity", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText("4.8/5", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText("483 aggregate ratings", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText(/Product-wide rating; not specific/)).toBeVisible();
  await expect(offer.getByRole("link", { name: /Read return policy/ }).first()).toHaveAttribute("href", "https://checkout.shopify.com/10/policies/123.html");
  await expect(offer.getByRole("link", { name: /Read privacy policy/ })).toHaveCount(0);
  await offer.getByText("Product description and specifications", { exact: true }).click();
  await expect(offer.getByText("Black edition & carrying case", { exact: false }).first()).toBeVisible();
  await expect(offer.getByText("Condition", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText("Listed features: Not supplied", { exact: false })).toHaveCount(0);
  await expect(offer).toContainText("wireless: not established");
});
