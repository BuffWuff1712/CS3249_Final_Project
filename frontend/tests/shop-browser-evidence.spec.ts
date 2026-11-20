import { test, expect } from "@playwright/test";

test("Browser Use ratings, excerpts, returns and delivery warnings reach the card", async ({ page, request }) => {
  let view = await (await request.post("http://localhost:8100/shop/sessions")).json();
  view = await (await request.post(`http://localhost:8100/shop/sessions/${view.session.id}/messages`, {
    data: { revision: view.revision, text: "Find wireless headphones under SGD200" },
  })).json();
  Object.assign(view.current.product, {
    source: "browser_use", attributes: ["25L capacity", "Water-resistant ripstop nylon"],
    specifications: { Brand: "ZITIZER", Capacity: "25L", Weight: "230 g" },
    rating: 4.7, rating_count: 15, product_rating_text: "4.7 out of 5 stars (15)",
    seller_rating_text: "99% positive feedback", reviews: [],
    review_excerpts: ["5 out of 5 stars — Water beads off in the rain."],
    availability_note: "In stock. Cannot be shipped to the selected location; displayed location was United States.",
    web_evidence: { ...view.current.product.web_evidence, return_policy: "Eligible for change-of-mind returns until Jan 31, 2027." },
    policy_links: { refund_policy: "https://www.amazon.sg/gp/help/customer/display.html?nodeId=201819200" },
  });
  await page.route("**/shop/sessions**", route => route.fulfill({ json: view }));
  await page.goto("/");
  const offer = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(offer.getByText("4.7/5", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText("15 aggregate ratings", { exact: true }).first()).toBeVisible();
  await expect(offer.getByText("99% positive feedback", { exact: true })).toBeVisible();
  await expect(offer.getByLabel("Availability and delivery notice")).toContainText("United States");
  await expect(offer).toContainText("Water-resistant ripstop nylon");
  await expect(offer.getByText("Eligible for change-of-mind returns until Jan 31, 2027.", { exact: true }).first()).toBeVisible();
  await offer.getByText("Read captured review excerpts", { exact: true }).click();
  await expect(offer.getByText("5 out of 5 stars — Water beads off in the rain.", { exact: true }).first()).toBeVisible();
  await offer.getByText("Product description and specifications", { exact: true }).click();
  await expect(offer.getByText("ZITIZER", { exact: true }).first()).toBeVisible();
});
