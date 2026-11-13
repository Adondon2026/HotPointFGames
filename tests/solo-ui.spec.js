const { test, expect } = require('@playwright/test');
test('solo lobby, contextual rules and settings, add bot and play', async ({ browser }) => {
  const c = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await c.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto('/');
    await page.getByPlaceholder('你的昵称').fill('单人玩家');
    await page.locator('#joinBtn').click();
    await expect(page.locator('#liteSolo')).toBeVisible();
    await page.locator('#modeDice').click();
    await expect(page.locator('#liteGameName')).toHaveText('大话骰');
    await page.locator('#liteGameRules').click();
    await expect(page.locator('#helpModal')).toContainText('至少');
    await expect(page.locator('#helpModal')).not.toContainText('四川麻将');
    await page.locator('#helpModal [data-close]').click();
    await page.locator('#liteGameSettings').click();
    await expect(page.locator('#diceStart')).toBeVisible();
    await expect(page.locator('#drawTime')).toBeHidden();
    await page.locator('#settingsModal [data-close]').click();
    await page.locator('#liteAddBot').click();
    await expect(page.locator('#playersLobby')).toContainText('机器人小北');
    await page.locator('#liteSolo').click();
    await expect(page.locator('#diceGame')).toBeVisible();
    await page.locator('#bidBtn').click();
    await expect(page.locator('#liteTurnLabel')).not.toContainText('等待 机器人', { timeout: 10000 });
    expect(errors).toEqual([]);
  } finally { await c.close(); }
});
