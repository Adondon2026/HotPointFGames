const { test, expect } = require('@playwright/test');

function isAction(response, type) {
  if (!response.url().endsWith('/api/action') || response.request().method() !== 'POST') return false;
  try {
    return response.request().postDataJSON().type === type;
  } catch {
    return false;
  }
}

test('refresh, draw clear, end game and leave work on a phone viewport', async ({ browser }) => {
  const contexts = [];
  const pages = [];
  const errors = [];
  const names = ['房主', '朋友'];

  try {
    for (const name of names) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page = await context.newPage();
      page.on('pageerror', error => {
        errors.push(`${name}: ${error.message}`);
        console.log(`PAGE ERROR ${name}: ${error.message}`);
      });
      page.on('console', message => {
        if (message.type() === 'error') console.log(`CONSOLE ERROR ${name}: ${message.text()}`);
      });
      contexts.push(context);
      pages.push(page);
      await page.goto('/');
      expect(await page.locator('#joinBtn').evaluate(element => typeof element.onclick)).toBe('function');
      await page.getByPlaceholder('你的昵称').fill(name);
      const joinResponse = page.waitForResponse(response => response.url().endsWith('/api/join'));
      await page.getByRole('button', { name: '游客进入', exact: true }).click();
      expect((await (await joinResponse).json()).ok).toBe(true);
      await expect(page.getByRole('button', { name: '准备', exact: true })).toBeVisible();
    }

    await pages[0].getByText('你画我猜', { exact: true }).click();
    for (const page of pages) {
      await page.getByRole('button', { name: '准备', exact: true }).click();
    }
    const start = pages[0].getByRole('button', { name: '开始游戏', exact: true });
    await expect(start).toBeEnabled();
    await start.click();

    let drawerIndex = -1;
    await expect.poll(async () => {
      for (let index = 0; index < pages.length; index += 1) {
        if (await pages[index].locator('.word-choice').count()) {
          drawerIndex = index;
          return index;
        }
      }
      return -1;
    }).not.toBe(-1);

    const drawer = pages[drawerIndex];
    await drawer.locator('.word-choice').first().click();
    const canvas = drawer.locator('#drawCanvas');
    await expect(canvas).toBeVisible();
    await expect(drawer.getByRole('button', { name: '清空', exact: true })).toBeVisible();

    const strokeResponse = drawer.waitForResponse(response => isAction(response, 'draw_stroke'));
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();
    await drawer.mouse.move(box.x + 40, box.y + 40);
    await drawer.mouse.down();
    await drawer.mouse.move(box.x + 150, box.y + 100, { steps: 6 });
    await drawer.mouse.up();
    expect((await (await strokeResponse).json()).ok).toBe(true);

    drawer.once('dialog', dialog => dialog.accept());
    const clearResponse = drawer.waitForResponse(response => isAction(response, 'draw_clear'));
    await drawer.getByRole('button', { name: '清空', exact: true }).click();
    expect((await (await clearResponse).json()).ok).toBe(true);
    await expect(drawer.locator('#canvasEmpty')).toBeVisible();

    await pages[0].locator('#liteMenuBtn').click();
    await pages[0].getByRole('button', { name: '刷新连接', exact: true }).click();
    await expect(pages[0].locator('#toast')).toHaveText('已刷新最新状态');

    pages[0].once('dialog', dialog => dialog.accept());
    const resetResponse = pages[0].waitForResponse(response => isAction(response, 'reset'));
    await pages[0].locator('#liteMenuBtn').click();
    await pages[0].getByRole('button', { name: '结束本局', exact: true }).click();
    expect((await (await resetResponse).json()).ok).toBe(true);
    for (const page of pages) {
      await expect(page.locator('#lobbyCard')).toBeVisible();
      await expect(page.getByRole('button', { name: '取消准备', exact: true })).toBeVisible();
    }

    pages[1].once('dialog', dialog => dialog.accept());
    await pages[1].locator('#liteMenuBtn').click();
    await pages[1].getByRole('button', { name: '退出房间', exact: true }).click();
    await expect(pages[1].getByRole('button', { name: '游客进入', exact: true })).toBeVisible();

    pages[0].once('dialog', dialog => dialog.accept());
    await pages[0].locator('#liteMenuBtn').click();
    await pages[0].getByRole('button', { name: '退出房间', exact: true }).click();
    await expect(pages[0].getByRole('button', { name: '游客进入', exact: true })).toBeVisible();
    expect(errors).toEqual([]);
  } finally {
    for (const context of contexts) await context.close();
  }
});
