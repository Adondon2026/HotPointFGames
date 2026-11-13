const { test, expect } = require('@playwright/test');

test('three players can see cards, bid points and bid history without render errors', async ({ browser }) => {
  const names = ['房主', '朋友甲', '朋友乙'];
  const contexts = [];
  const pages = [];
  const consoleErrors = [];

  try {
    for (const name of names) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page = await context.newPage();
      page.on('pageerror', error => consoleErrors.push(`${name}: ${error.message}`));
      contexts.push(context);
      pages.push(page);
      await page.goto('/');
      await page.getByPlaceholder('你的昵称').fill(name);
      await page.getByRole('button', { name: '游客进入', exact: true }).click();
      await expect(page.locator('#liteSolo').or(page.getByRole('button', { name: '准备', exact: true }))).toBeVisible();
    }

    await pages[0].getByText('斗地主', { exact: true }).click();
    for (const page of pages) {
      await expect(page.locator('#liteRoomHint')).toContainText('自动补足三家');
      await page.getByRole('button', { name: '准备', exact: true }).click();
    }

    const start = pages[0].getByRole('button', { name: '开始游戏', exact: true });
    await expect(start).toBeEnabled();
    await start.click();

    for (const page of pages) {
      await expect(page.locator('#ddzGame')).toBeVisible();
      await expect(page.locator('#ddzHand .ddz-card')).toHaveCount(17);
      await expect(page.getByRole('button', { name: '1 分', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: '2 分', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: '3 分', exact: true })).toBeVisible();
    }

    let bidderIndex = -1;
    await expect.poll(async () => {
      for (let index = 0; index < pages.length; index += 1) {
        if (await pages[index].getByRole('button', { name: '1 分', exact: true }).isEnabled()) {
          bidderIndex = index;
          return index;
        }
      }
      return -1;
    }).not.toBe(-1);

    await pages[bidderIndex].getByRole('button', { name: '1 分', exact: true }).click();
    for (const page of pages) {
      await page.locator('#ddzHistoryToggle').click();
      await expect(page.locator('#ddzHistoryList')).toContainText(`${names[bidderIndex]} 叫 1 分`);
      await page.locator('#ddzHistoryClose').click();
      await expect(page.locator('#ddzLastPlay')).toContainText('当前 1 分');
    }
    expect(consoleErrors).toEqual([]);
  } finally {
    for (const context of contexts) await context.close();
  }
});
