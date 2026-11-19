import { test, expect } from "@playwright/test";

for (const broken of [false, true]) test(`product image placement and ${broken ? "failed image fallback" : "loading"}`, async ({ page, request }) => {
  const created = await request.post("http://localhost:8100/shop/sessions");
  let view = await created.json();
  const searched = await request.post(`http://localhost:8100/shop/sessions/${view.session.id}/messages`, {
    data: { revision: view.revision, text: "Find headphones under SGD200; no feature preference" },
  });
  view = await searched.json();
  expect(view.current).toBeTruthy();
  view.current.product.image_url = "https://images.example.com/product.svg";
  view.current.product.image_alt = "Headphones product photo";
  await page.route("https://images.example.com/**", route => broken ? route.abort() : route.fulfill({
    contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240"><rect width="320" height="240" fill="#dbeafe"/><circle cx="160" cy="120" r="70" fill="#2563eb"/></svg>',
  }));
  await page.route("**/shop/sessions**", route => route.fulfill({ json: view }));
  await page.goto("/");
  const offer = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(offer).toBeVisible();
  const photo = offer.getByLabel("Product image", { exact: true });
  if (broken) await expect(photo).toContainText("Product image unavailable");
  else {
    const img = photo.getByRole("img", { name: "Headphones product photo" });
    await expect(img).toBeVisible();
    await expect.poll(() => img.evaluate((node: HTMLImageElement) => node.naturalWidth)).toBeGreaterThan(0);
  }
  const heading = await offer.locator(".cui-product-heading").boundingBox();
  const image = await photo.boundingBox();
  const needs = await offer.getByText("How this matches your needs", { exact: true }).boundingBox();
  expect(image!.y).toBeGreaterThanOrEqual(heading!.y + heading!.height);
  expect(image!.y + image!.height).toBeLessThanOrEqual(needs!.y);
});
