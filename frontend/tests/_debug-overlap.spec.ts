import { test, expect, type Page } from "@playwright/test";

test("debug: dump rect layout of recommendation card", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find headphones under SGD200; no feature preference");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const card = page.getByRole("article", { name: "Current recommendation", exact: true });
  await expect(card).toBeVisible();

  const styleOnly = await page.evaluate(() => {
    const el = document.querySelector("header.cui-offer-anchor") as HTMLElement | null;
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out: Record<string, string> = {};
    for (const prop of ["height", "min-height", "max-height", "display", "flex-direction", "align-items", "justify-content", "padding", "overflow"]) out[prop] = cs.getPropertyValue(prop);
    return out;
  });
  console.log("ANCHOR_STYLE_OUT=" + JSON.stringify(styleOnly));
  const info = await page.evaluate(() => {
    const anchor = document.querySelector("header.cui-offer-anchor") as HTMLElement | null;
    if (anchor) {
      const cs = getComputedStyle(anchor);
      (window as any).__ANCHOR_STYLE__ = { height: cs.height, minHeight: cs.minHeight, maxHeight: cs.maxHeight, display: cs.display, flexDirection: cs.flexDirection, alignItems: cs.alignItems, justifyContent: cs.justifyContent, overflow: cs.overflow, boxSizing: cs.boxSizing };
      console.log("ANCHOR STYLE:", JSON.stringify((window as any).__ANCHOR_STYLE__));
    }
    const article = document.querySelector("article.cui-recommendation") as HTMLElement | null;
    if (!article) return { error: "no article" };
    const walk = (el: HTMLElement, depth = 0): any[] => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const out: any[] = [{
        tag: el.tagName.toLowerCase(),
        cls: el.className,
        depth,
        top: Math.round(r.top),
        left: Math.round(r.left),
        w: Math.round(r.width),
        h: Math.round(r.height),
        display: cs.display,
        position: cs.position,
        flex: cs.flexDirection,
        gridCol: cs.gridColumn,
        gridRow: cs.gridRow,
        margin: cs.margin,
        transform: cs.transform,
      }];
      if (depth < 5) {
        for (const child of Array.from(el.children)) {
          out.push(...walk(child as HTMLElement, depth + 1));
        }
      }
      return out;
    };
    return walk(article);
  });
  console.log(JSON.stringify(info, null, 2));
  await page.screenshot({ path: "test-results/_overlap-debug.png", fullPage: true });
});
