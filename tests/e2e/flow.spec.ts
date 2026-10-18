import { expect, test, type Page } from '@playwright/test';

const password = 'Demo123!';

async function loginUI(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('用户名').fill(username);
  await page.getByLabel('密码').fill(password);
  await page.getByRole('button', { name: '登录工作台' }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
}

test('outpatient flow is traceable from login through audit', async ({ page }) => {
  // Every business transition below is a browser interaction. Direct API
  // calls are deliberately not used to bypass an unfinished page.
  await loginUI(page, 'cashier.demo');

  await page.goto('/schedules');
  await page.getByLabel('就诊日期').fill('2099-01-01');
  await page.getByLabel('科室 ID').fill('1');
  await page.getByRole('button', { name: '查询排班' }).click();
  const scheduleRow = page.getByRole('row').filter({ hasText: '演示医生' });
  await expect(scheduleRow).toBeVisible();
  await expect(scheduleRow.getByRole('cell').nth(6)).toHaveText('2');

  await page.goto('/registrations');
  await page.getByLabel('患者 ID').fill('1');
  await page.getByLabel('排班 ID').fill('1');
  await page.getByRole('button', { name: '确认挂号' }).click();
  await expect(page.getByText('挂号已由服务端创建')).toBeVisible();
  await expect(page.getByText('排队号').locator('..').getByRole('strong')).toHaveText('1');

  await page.getByRole('button', { name: '退出登录' }).click();
  await loginUI(page, 'doctor.demo');
  await page.goto('/prescriptions');
  await page.getByLabel('挂号单 ID').fill('1');
  await page.getByLabel('诊断编码').fill('J06.9');
  await page.getByLabel('诊断名称').fill('急性上呼吸道感染');
  await page.getByLabel('药品 ID').fill('1');
  await page.getByLabel('数量').fill('2');
  await page.getByRole('button', { name: '创建草稿处方' }).click();
  await page.getByRole('button', { name: '提交为待收费' }).click();
  await expect(page.getByText('待收费', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '退出登录' }).click();
  await loginUI(page, 'cashier.demo');
  await page.goto('/billing');
  await page.getByLabel('收费处方 ID').fill('1');
  await page.getByRole('button', { name: '收费台' }).click();
  await expect(page.getByText('¥ 25.00', { exact: true })).toBeVisible();
  await expect(page.getByText('completed', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '退出登录' }).click();
  await loginUI(page, 'pharmacist.demo');
  await page.goto('/dispensing');
  await page.getByLabel('已收费处方 ID').fill('1');
  await page.getByRole('button', { name: '药房发药' }).click();
  await expect(page.getByText('completed', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '退出登录' }).click();
  await loginUI(page, 'admin.demo');
  await page.goto('/audit-logs');
  await page.getByRole('button', { name: '刷新日志' }).click();
  await expect(page.getByText('registration.create', { exact: true })).toBeVisible();
  await expect(page.getByText('prescription.charge', { exact: true })).toBeVisible();
  await expect(page.getByText('prescription.dispense', { exact: true })).toBeVisible();
});

