import { test, expect } from "@playwright/test";
test("conversation, specific approval and simulated receipt", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("MOCK LLM MODE", { exact: false })).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message Beany" })
    .fill("Find headphones under $150");
  await page.getByRole("button", { name: "Send ↗", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Approve simulated checkout" })
    .click();
  await expect(
    page.getByText("Simulated receipt", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Simulated receipt", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
test("vague request, repair and cancellation", async ({ page }) => {
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await expect(input).toBeEnabled();
  await input.fill("I need some shoes");
  await page.getByRole("button", { name: "Send ↗", exact: true }).click();
  await expect(
    page.getByText("Will you use them for running or everyday wear?", {
      exact: true,
    }),
  ).toBeVisible();
  await input.fill("Find running shoes under $150");
  await page.getByRole("button", { name: "Send ↗", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toBeVisible();
  await input.fill("cancel");
  await page.getByRole("button", { name: "Send ↗", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toHaveCount(0);
});
test("study hard block and CSV export", async ({ page, request }) => {
  const headers = { "X-Research-Key": "e2e-key" };
  const res = await request.post(
    "http://localhost:8100/research/scenarios/budget/sessions",
    { headers },
  );
  const session = await res.json();
  await request.post(
    `http://localhost:8100/research/sessions/${session.id}/trigger`,
    { headers },
  );
  await page.goto("/");
  await page.evaluate(
    (id) => localStorage.setItem("beany-session", id),
    session.id,
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toBeDisabled();
  await expect(
    page.getByText("Blocked by your boundaries", { exact: true }),
  ).toBeVisible();
  const csv = await request.get(
    `http://localhost:8100/research/sessions/${session.id}/export`,
    { headers },
  );
  expect(await csv.text()).toContain("intervention");
});

test("keyboard submission and recoverable network errors", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Message Beany" });
  await expect(input).toBeEnabled();
  await page.route("**/sessions/*/messages", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "OpenAI temporarily unavailable. Retry your message.",
      }),
    }),
  );
  await input.fill("Find headphones under $150");
  await input.press("Tab");
  await expect(
    page.getByRole("button", { name: "Send ↗", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "OpenAI temporarily unavailable" }),
  ).toContainText("OpenAI temporarily unavailable");
  await expect(input).toHaveValue("Find headphones under $150");
  await page.unroute("**/sessions/*/messages");
  await page.getByRole("button", { name: "Send ↗", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toBeEnabled();
  await page.screenshot({
    path: testInfo.outputPath("beany-review.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Cancel shopping task", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Approve simulated checkout" }),
  ).toHaveCount(0);
});

test("merchant evidence is public but hidden truth is research-only", async ({
  page,
  request,
}) => {
  const headers = { "X-Research-Key": "e2e-key" };
  const created = await request.post(
    "http://localhost:8100/research/scenarios/risk-h/sessions",
    { headers },
  );
  const session = await created.json();
  await request.post(
    `http://localhost:8100/research/sessions/${session.id}/trigger`,
    { headers },
  );
  const publicResponse = await request.get(
    `http://localhost:8100/sessions/${session.id}`,
  );
  const state = await publicResponse.json();
  expect(state.experiment).toBeUndefined();
  expect(JSON.stringify(state)).not.toContain("MALICIOUS");
  await page.goto("/");
  await expect(
    page.getByRole("textbox", { name: "Message Beany" }),
  ).toBeEnabled();
  await page.evaluate(
    (id) => localStorage.setItem("beany-session", id),
    session.id,
  );
  await page.reload();
  await page
    .getByText("Review merchant details: City Goods", { exact: true })
    .click();
  await expect(
    page.getByText("https://city-goods.test", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText("MALICIOUS", { exact: true })).toHaveCount(0);
  const denied = await request.get(
    `http://localhost:8100/research/sessions/${session.id}/risk-report`,
  );
  expect(denied.status()).toBe(403);
  const report = await request.get(
    `http://localhost:8100/research/sessions/${session.id}/risk-report`,
    { headers },
  );
  expect((await report.json()).metrics.fn).toBe(1);
});

test("risky offer can be replaced with another merchant without losing brief", async ({
  page,
  request,
}) => {
  const headers = { "X-Research-Key": "e2e-key" };
  const created = await request.post(
    "http://localhost:8100/research/scenarios/risk-i/sessions",
    { headers },
  );
  const s = await created.json();
  await request.post(
    `http://localhost:8100/research/sessions/${s.id}/trigger`,
    { headers },
  );
  await page.goto("/");
  await expect(
    page.getByRole("textbox", { name: "Message Beany" }),
  ).toBeEnabled();
  await page.evaluate((id) => localStorage.setItem("beany-session", id), s.id);
  await page.reload();
  await expect(
    page.getByText("Merchant assessment · high predicted risk", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Find another merchant", exact: true })
    .click();
  await expect(
    page.getByText("Review merchant details: Demo Store", { exact: true }),
  ).toBeVisible();
  const response = await request.get(`http://localhost:8100/sessions/${s.id}`);
  const result = await response.json();
  expect(result.brief.budget.value).toBe("150");
});
