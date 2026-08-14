import { expect, test } from '@playwright/test';

test('runs the full lunch lookup flow through the backend only', async ({ page }) => {
  const browserRequests: string[] = [];
  page.on('request', (request) => {
    browserRequests.push(request.url());
  });

  await page.goto('/');
  await page.getByLabel('학교 이름').fill('한국중학교');
  await page.getByRole('button', { name: '검색' }).click();
  await page.locator('.school-list button').nth(1).click();
  await page.getByLabel('시작일').fill('2026-08-01');
  await page.getByLabel('종료일').fill('2026-08-02');
  await page.getByRole('button', { name: '중식 조회' }).click();

  await expect(page.getByRole('heading', { level: 4, name: '2026-08-01' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 4, name: '2026-08-02' })).toBeVisible();
  await expect(page.getByText('잡곡밥 (5.6.)')).toBeVisible();

  await page.getByLabel('시작일').fill('2026-08-02');
  await page.getByLabel('종료일').fill('2026-08-02');
  await page.getByRole('button', { name: '중식 조회' }).click();

  await expect(page.getByRole('heading', { level: 4, name: '2026-08-01' })).toHaveCount(0);
  await expect(page.getByRole('heading', { level: 4, name: '2026-08-02' })).toBeVisible();
  expect(browserRequests.some((url) => url.includes(':8081') || url.includes('/hub/'))).toBeFalsy();
});

test('renders empty states for missing schools and missing meals', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('학교 이름').fill('없는학교');
  await page.getByRole('button', { name: '검색' }).click();
  await expect(page.getByRole('status')).toContainText('해당하는 학교가 없습니다');

  await page.getByLabel('학교 이름').fill('빈급식학교');
  await page.getByRole('button', { name: '검색' }).click();
  await page.locator('.school-list button').first().click();
  await page.getByLabel('시작일').fill('2026-08-01');
  await page.getByLabel('종료일').fill('2026-08-02');
  await page.getByRole('button', { name: '중식 조회' }).click();

  await expect(page.getByRole('status')).toContainText('표시할 중식 정보가 없습니다');
});

test('shows a retryable backend error state for upstream failures', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('학교 이름').fill('장애학교');
  await page.getByRole('button', { name: '검색' }).click();
  await page.locator('.school-list button').first().click();
  await page.getByLabel('시작일').fill('2026-08-01');
  await page.getByLabel('종료일').fill('2026-08-02');
  await page.getByRole('button', { name: '중식 조회' }).click();

  await expect(page.getByRole('alert')).toContainText('서버 오류입니다.');
  await expect(page.getByRole('button', { name: '다시 시도' })).toBeVisible();
});
