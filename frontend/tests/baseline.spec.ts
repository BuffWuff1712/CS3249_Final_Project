import { test, expect } from '@playwright/test';

test('baseline exposes raw records without personalised assistance and permits manual choice', async ({ page, request }) => {
  const response = await request.get('/api/study/catalogue');
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.products).toHaveLength(4);
  expect(data.offers).toHaveLength(12);
  for (const key of ['scores', 'advantages', 'compromise', 'reasons', 'concerns', 'ground_truth']) expect(JSON.stringify(data)).not.toContain(`"${key}"`);
  await page.goto('/compare');
  await page.getByLabel('Category').selectOption('Headphones');
  await page.getByLabel('Maximum price (SGD)').fill('300');
  await expect(page.getByRole('heading', { name: 'Echo Quiet', exact: true })).toBeVisible();
  await expect(page.getByLabel('Offer echo-quiet-soundrush', { exact: true }).getByText('Pay by gift card outside checkout', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose Echo Quiet from Everyday Sound', exact: true }).click();
  await expect(page.getByLabel('Selected offer', { exact: true })).toContainText('SGD269');
  await page.getByLabel('Maximum price (SGD)').fill('180');
  await expect(page.getByLabel('Selected offer', { exact: true })).toHaveCount(0);
  await expect(page.getByText('No offers match these filters.')).toBeVisible();
});
