import { test, expect } from "@playwright/test";

test("broad shoes clarify before searching and explicit uncertainty continues", async ({ page }) => {
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await input.fill("I need shoes");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("region", { name: "Conversation history" }).getByText("I can help narrow it down!", { exact: false })).toBeVisible();
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Compare current needs", exact: true })).toHaveCount(0);
  await input.fill("I'm unsure about those; show me some options");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("article", { name: "Current recommendation", exact: true })).toBeVisible();
});

test("only the latest progress is visible until the history arrow is expanded", async ({ page }, testInfo) => {
  // UI-only streaming fixture: backend cancellation is exercised separately in Python.
  await page.addInitScript(() => {
    const original = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      if (!String(input).endsWith("/messages/stream")) return original(input, init);
      return new Response(new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          const rows = [
            { id: "1", label: "Read your request", state: "completed", evidence: [] },
            { id: "2", label: "Prepared the product search", state: "completed", evidence: [] },
            { id: "3", label: "Comparing available offers…", state: "running", evidence: [] },
          ];
          for (const activity of rows) controller.enqueue(encoder.encode(JSON.stringify({ type: "activity", activity }) + "\n"));
          init?.signal?.addEventListener("abort", () => controller.error(new DOMException("Aborted", "AbortError")), { once: true });
        },
      }), { headers: { "Content-Type": "application/x-ndjson" } });
    };
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
  await page.getByRole("textbox", { name: "Message Beany" }).fill("Find wireless headphones under SGD200");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const progress = page.getByLabel("Backend request in progress", { exact: true });
  await expect(progress.getByText("Comparing available offers…", { exact: true })).toBeVisible();
  await expect(progress.getByText("Read your request", { exact: true })).toBeHidden();
  await expect(page.getByLabel(/^Elapsed time: [1-9]/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop", exact: true })).toBeInViewport();
  await expect(page.getByLabel("Show or hide action history", { exact: true })).toBeInViewport();
  await page.screenshot({ path: testInfo.outputPath("compact-progress.png") });
  await page.getByLabel("Show or hide action history", { exact: true }).click();
  await expect(progress.getByText("Read your request", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("expanded-progress.png") });
});
