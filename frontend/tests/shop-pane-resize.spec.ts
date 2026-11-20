import { test, expect } from "@playwright/test";

test("pane resizing, persistence and bounds", async ({ page, isMobile }) => {
  await page.goto("/");
  const divider = page.getByRole("separator", { name: "Resize conversation and product panes" });
  if (isMobile) {
    await expect(divider).toBeHidden();
    const left = await page.locator("#shopping-conversation").boundingBox();
    const right = await page.locator("#shopping-decision").boundingBox();
    expect(right!.y).toBeGreaterThanOrEqual(left!.y + left!.height);
    return;
  }
  await expect(divider).toBeVisible();
  await expect(page.getByRole("button", { name: "Open settings" })).toBeEnabled();
  await expect.poll(async () => Number(await divider.getAttribute("aria-valuemin"))).toBeGreaterThan(0);
  await divider.hover();
  await expect(divider).toHaveCSS("outline-style", "none");
  await expect(page.locator(".cui-disclosure")).toHaveCount(0);
  const left = page.locator("#shopping-conversation");
  const right = page.locator("#shopping-decision");
  const initial = (await left.boundingBox())!.width;
  const initialRight = (await right.boundingBox())!.width;
  const box = (await divider.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + 100);
  await page.mouse.down();
  await page.mouse.move(box.x - 80, box.y + 100);
  await page.mouse.up();
  await expect.poll(async () => (await left.boundingBox())!.width).toBeLessThan(initial);
  await expect.poll(async () => (await right.boundingBox())!.width).toBeGreaterThan(initialRight);
  const saved = await divider.getAttribute("aria-valuenow");
  await page.reload();
  await expect(divider).toHaveAttribute("aria-valuenow", saved!);
  await divider.focus();
  await page.keyboard.press("ArrowRight");
  expect(Number(await divider.getAttribute("aria-valuenow"))).toBeGreaterThan(Number(saved));
  await page.keyboard.press("Home");
  expect((await left.boundingBox())!.width).toBeGreaterThanOrEqual(319);
  await page.keyboard.press("End");
  expect((await right.boundingBox())!.width).toBeGreaterThanOrEqual(319);
  await expect(page.getByRole("button", { name: "Reset pane widths" })).toHaveCount(0);
});

test("saved Shopify title is cleaned only for display", async ({ page, request }) => {
  let view = await (await request.post("http://localhost:8100/shop/sessions")).json();
  view = await (await request.post(`http://localhost:8100/shop/sessions/${view.session.id}/messages`, {
    data: { revision: view.revision, text: "Find headphones under SGD200; no feature preference" },
  })).json();
  const title = "Nike Revolution 7 Road Running Shoes 'Black White' FB2207-001";
  view.current.product.name = `${title} · ${title}`;
  view.current.product.source = "shopify_catalog";
  await page.route("**/shop/sessions**", route => route.fulfill({ json: view }));
  await page.goto("/");
  await expect(page.locator(".cui-product-heading h3")).toHaveText(title);
  expect(view.current.product.name).toBe(`${title} · ${title}`);
});

test("marketing-heavy titles are concise with full details accessible", async ({ page, request }) => {
  let view = await (await request.post("http://localhost:8100/shop/sessions")).json();
  view = await (await request.post(`http://localhost:8100/shop/sessions/${view.session.id}/messages`, {
    data: { revision: view.revision, text: "Find headphones under SGD200; no feature preference" },
  })).json();
  const core = "Nike Pegasus Premium Women's Road Running Shoes";
  const full = `${core} | Mint Green/White | Triple-cushioning system: ZoomX + Air Zoom | Breathable mesh upper`;
  view.current.product.name = full;
  view.current.product.source = "browser_use";
  await page.route("**/shop/sessions**", route => route.fulfill({ json: view }));
  await page.goto("/");
  await expect(page.locator(".cui-product-heading h3")).toHaveText(core);
  await page.getByText("Full listing title", { exact: true }).click();
  await expect(page.locator(".cui-full-title p")).toHaveText(full);
  expect(view.current.product.name).toBe(full);
});
