import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Gate the real backend stream after its first activity line, not a fabricated step.
  await page.addInitScript(() => {
    const original = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const response = await original(input, init);
      if (!String(input).endsWith("/messages/stream") || !response.ok || !response.body) return response;
      const reader = response.body.getReader();
      let release!: () => void;
      const gate = new Promise<void>(resolve => { release = resolve; });
      (window as unknown as { releaseProgress: () => void }).releaseProgress = release;
      return new Response(new ReadableStream({
        async start(controller) {
          try {
            let pending = new Uint8Array(0), first = true;
            while (true) {
              const { value, done } = await reader.read();
              if (done) break;
              if (!first) { controller.enqueue(value); continue; }
              const combined = new Uint8Array(pending.length + value.length);
              combined.set(pending); combined.set(value, pending.length); pending = combined;
              const newline = pending.indexOf(10);
              if (newline < 0) continue;
              controller.enqueue(pending.slice(0, newline + 1));
              first = false; await gate;
              if (pending.length > newline + 1) controller.enqueue(pending.slice(newline + 1));
            }
            controller.close();
          } catch (error) { controller.error(error); }
        },
        cancel() { release(); return reader.cancel(); },
      }), { status: response.status, headers: response.headers });
    };
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
});

async function begin(page: import("@playwright/test").Page) {
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find wireless headphones under $200");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("Backend request in progress", { exact: true })).toContainText("Reading your request");
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toHaveCount(0);
}

test("actual progress appears before the result and finishes with readable evidence", async ({ page }, testInfo) => {
  await begin(page);
  await page.screenshot({ path: testInfo.outputPath("live-activity.png") });
  await page.evaluate(() => (window as unknown as { releaseProgress: () => void }).releaseProgress());
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toBeVisible();
  const activity = page.getByLabel("Comparison activity", { exact: true });
  await expect(activity).toContainText("Found 4 matching offers");
  await activity.locator("summary").click();
  await expect(activity).toContainText("Needs your approval");
  await expect(activity).not.toContainText("Records:");
  await expect(activity).not.toContainText("offer-");
  await expect(activity).not.toContainText("REVIEW");
  await page.screenshot({ path: testInfo.outputPath("completed-activity.png") });
});

test("reset ignores the remainder of an old progress stream", async ({ page }) => {
  await begin(page);
  await page.getByRole("button", { name: "Start fresh", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.evaluate(() => (window as unknown as { releaseProgress: () => void }).releaseProgress());
  await expect(page.getByLabel("Comparison activity", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toHaveCount(0);
});

test("elapsed timer and Stop stay available while waiting", async ({ page }) => {
  await begin(page);
  await expect(page.getByRole("button", { name: "Stop", exact: true })).toBeEnabled();
  await expect(page.getByLabel(/^Elapsed time: [1-9]/)).toBeVisible({ timeout: 5000 });
  await page.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(page.getByText("Stopped waiting for this request.", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Stop", exact: true })).toHaveCount(0);
});
