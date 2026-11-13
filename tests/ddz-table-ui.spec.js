const { test, expect } = require('@playwright/test');

test('solo DDZ table, bottom cards, history and viewport rotation', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await page.locator('#nameInput').fill('牌桌测试');
  await page.locator('#joinBtn').click();
  await page.locator('#modeDdz').click();
  await page.locator('#liteSolo').click();
  await expect(page.locator('#ddzGame')).toBeVisible();
  await expect.poll(async()=>{
    if(await page.locator('#ddzPlayPanel').isVisible())return true;
    for(const score of [3,2,1,0]){const b=page.locator(`[data-ddz-bid="${score}"]`);if(await b.isVisible()&&await b.isEnabled()){await b.click();break;}}
    return false;
  },{timeout:20000}).toBe(true);
  await expect(page.locator('#ddzBottomToggle')).toBeVisible();
  await expect(page.locator('#ddzBottom')).toBeHidden();
  await page.locator('#ddzBottomToggle').click();
  await expect(page.locator('#ddzBottom .ddz-mini')).toHaveCount(3);
  await page.locator('#ddzBottomToggle').click();
  await page.locator('#ddzHistoryToggle').click();
  await expect(page.locator('#ddzHistoryList')).toContainText('成为地主');
  await page.locator('#ddzHistoryClose').click();
  for(const [width,height] of [[320,568],[390,844],[844,390],[1024,768],[1440,900]]){
    await page.setViewportSize({width,height});
    if(width<height){
      await expect(page.locator('#ddzHand')).toHaveClass(/ddz-two-rows/);
      const fit=await page.locator('#ddzHand').evaluate(h=>{const r=h.getBoundingClientRect();return [...h.querySelectorAll('.ddz-card')].every(c=>{const b=c.getBoundingClientRect();return b.left>=r.left-1&&b.right<=r.right+1})&&h.scrollWidth<=h.clientWidth+1});
      expect(fit).toBe(true);
      const rows=await page.locator('#ddzHand .ddz-hand-row').evaluateAll(els=>els.map(r=>[...r.querySelectorAll('.rank')].map(x=>x.textContent)));
      expect(rows).toHaveLength(2);
      expect(rows[0].at(-1)).not.toBe(rows[1][0]);
    } else await expect(page.locator('#ddzHand .ddz-hand-row')).toHaveCount(1);
    const panel=await page.locator('#ddzPlayPanel').boundingBox();
    expect(panel.y+panel.height).toBeLessThanOrEqual(height+2);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
});
