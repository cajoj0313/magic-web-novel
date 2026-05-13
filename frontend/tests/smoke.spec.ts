import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';

test.describe('WebNovel App Smoke Tests', () => {
  test('home page loads and shows project list', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await expect(page).toHaveTitle(/frontend/);
    // Sidebar menu items
    await expect(page.getByRole('menuitem', { name: '概览' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '章节管理' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '模型配置' })).toBeVisible();
    // Project list card header
    await expect(page.getByText('项目列表')).toBeVisible();
  });

  test('project creation flow', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    // Click create button
    await page.getByRole('button', { name: '新建项目' }).click();
    // Wait for dialog to appear
    await page.waitForSelector('.el-dialog__header', { state: 'visible' });
    // Fill form - label is "项目根目录"
    await page.getByLabel('项目根目录').fill('/tmp/test-e2e-project');
    // Genre select - el-select uses custom rendering
    await page.locator('.el-select').first().click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item span').filter({ hasText: '都市' }).click();
    // Click submit
    await page.getByRole('button', { name: '创建' }).click();
    // Should see success or error message
    await page.waitForTimeout(1000);
  });

  test('chapter list page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/chapters`);
    await expect(page.getByRole('menuitem', { name: '章节管理' })).toHaveClass(/is-active/);
    await expect(page.getByText('章节列表')).toBeVisible();
  });

  test('LLM config page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/llm-configs`);
    await expect(page.getByRole('menuitem', { name: '模型配置' })).toHaveClass(/is-active/);
    await expect(page.getByRole('main').getByText('模型配置')).toBeVisible();
  });

  test('settings page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/settings`);
    await expect(page.getByRole('menuitem', { name: '设定集' })).toHaveClass(/is-active/);
    await expect(page.getByRole('main').getByText('设定集')).toBeVisible();
  });

  test('query page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/query`);
    await expect(page.getByRole('menuitem', { name: '查询' })).toHaveClass(/is-active/);
    await expect(page.getByText('设定查询')).toBeVisible();
  });

  test('learn page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/learn`);
    await expect(page.getByRole('menuitem', { name: '学习模式' })).toHaveClass(/is-active/);
    await expect(page.getByText('模式学习')).toBeVisible();
  });

  test('plan page loads', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/plan`);
    await expect(page.getByRole('menuitem', { name: '大纲规划' })).toHaveClass(/is-active/);
    await expect(page.getByRole('main').getByText('大纲规划')).toBeVisible();
  });
});
