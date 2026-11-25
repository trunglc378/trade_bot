const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const out = process.env.TEST_ARTIFACT_DIR || path.join(root, 'test-results', 'system');
fs.mkdirSync(out, { recursive: true });
const executablePath = process.env.TEST_BROWSER_PATH || [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
].find(p => fs.existsSync(p));
const results = [];
let browser, service, url;
async function check(name, action) {
  const started = Date.now();
  let context;
  try {
    await fetch(url + '/__test__/reset', {method: 'POST'});
    context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === url ? route.continue() : route.abort());
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(url + '/dashboard');
    await page.locator('#botUrl').fill(url + '/api/v1');
    await action(page);
    assert.deepEqual(errors, [], 'Browser JavaScript errors');
    results.push({id: name, status: 'PASS', duration_ms: Date.now() - started});
  } catch (error) {
    results.push({id: name, status: 'FAIL', duration_ms: Date.now() - started, error: error.stack});
    if (context?.pages()[0]) await context.pages()[0].screenshot({path: path.join(out, name + '-failure.png'), fullPage: true}).catch(() => {});
  } finally { await context?.close(); }
}
async function login(page) {
  await page.getByRole('button', {name: /Kết Nối & Đăng Nhập/}).click();
  await page.waitForFunction(() => document.getElementById('connStatus').textContent.includes('Đã kết nối'));
  await page.waitForFunction(() => document.querySelectorAll('#bangLenhDangMo button').length > 0);
}
async function api(page, endpoint) {
  return page.evaluate(async endpoint => (await fetch(layBotUrl() + endpoint, {headers: {Authorization: 'Bearer ' + jwtToken}})).json(), endpoint);
}
(async () => {
  const started_at = new Date().toISOString();
  try {
    if (!executablePath) throw new Error('Set TEST_BROWSER_PATH to an installed Chromium/Edge/Chrome executable');
    service = spawn(process.env.TEST_PYTHON || 'python', [path.join(__dirname, 'mock_service.py')], {cwd: root, stdio: ['ignore', 'pipe', 'pipe']});
    const startup = await Promise.race([once(service.stdout, 'data'), new Promise((_, reject) => setTimeout(() => reject(new Error('Mock startup timeout')), 10000).unref())]);
    url = JSON.parse(startup[0].toString().trim()).url;
    browser = await chromium.launch({executablePath, headless: true});
    await check('SYS-01-login-dashboard', async page => {
      await login(page);
      assert.match(await page.locator('#tongTaiSanUsdt').innerText(), /USDT/);
      assert.equal((await api(page, '/status')).length, await page.locator('#bangLenhDangMo button').count());
      await page.screenshot({path: path.join(out, 'desktop.png'), fullPage: true});
    });
    await check('SYS-02-invalid-login', async page => {
      await page.locator('#password').fill('wrong');
      page.once('dialog', dialog => dialog.accept());
      await page.getByRole('button', {name: /Kết Nối & Đăng Nhập/}).click();
      await page.waitForFunction(() => document.getElementById('connStatus').textContent.includes('Lỗi'));
      const response = await page.request.get(url + '/api/v1/status');
      assert.equal(response.status(), 401);
    });
    await check('SYS-03-stop-and-resume', async page => {
      await login(page);
      const before = (await api(page, '/status')).length;
      page.once('dialog', d => d.accept());
      await page.getByRole('button', {name: /Tạm Dừng Mua Mới/}).click();
      assert.equal((await api(page, '/show_config')).stopbuy_active, true);
      assert.equal((await api(page, '/status')).length, before);
      page.once('dialog', d => d.accept());
      await page.getByRole('button', {name: /Bật Lại Mua/}).click();
      assert.equal((await api(page, '/show_config')).stopbuy_active, false);
    });
    await check('SYS-04-panic-confirmation', async page => {
      await login(page);
      const before = (await api(page, '/status')).length;
      page.once('dialog', d => d.dismiss());
      await page.getByRole('button', {name: /PANIC SELL/}).click();
      assert.equal((await api(page, '/status')).length, before);
      page.on('dialog', d => d.accept());
      await page.getByRole('button', {name: /PANIC SELL/}).click();
      await page.waitForFunction(async () => (await (await fetch(layBotUrl() + '/status', {headers:{Authorization:'Bearer '+jwtToken}})).json()).length === 0);
      assert.equal((await api(page, '/status')).length, 0);
    });
    await check('SYS-05-close-single-trade', async page => {
      await login(page);
      const before = (await api(page, '/status')).length;
      page.on('dialog', d => d.accept());
      await page.locator('#bangLenhDangMo button').first().click();
      await page.waitForFunction(n => document.querySelectorAll('#bangLenhDangMo button').length === n, before - 1);
      assert.equal((await api(page, '/status')).length, before - 1);
    });
    await check('SYS-06-risk-lock', async page => {
      await login(page);
      await page.getByRole('button', {name: /Thử Nghiệm Bật/}).click();
      await page.waitForFunction(() => document.getElementById('riskBanner').textContent.includes('CẢNH BÁO'));
      assert.equal((await api(page, '/locks')).lock_count, 1);
    });
    await check('SYS-07-research-grounding-mobile', async page => {
      await login(page);
      await page.getByRole('button', {name: /Đồng bộ báo cáo từ mock/}).click();
      await page.waitForFunction(() => document.getElementById('researchStatus').textContent.includes('DỮ LIỆU GIẢ LẬP'));
      assert.equal(await page.locator('#researchRows a').getAttribute('href'), 'https://reuters.com/markets');
      await page.setViewportSize({width: 390, height: 844});
      assert.equal(await page.locator('#researchTitle').isVisible(), true);
      await page.screenshot({path: path.join(out, 'mobile.png'), fullPage: true});
    });
    await check('SYS-08-file-stale-xss-and-invalid-json', async page => {
      const report = {schema_version: 1, exchange: 'binance', mode: 'required', errors: [], generated_at:'2020-01-01T00:00:00Z', expires_at:'2020-01-01T00:15:00Z', candidates:[{pair:'BTC/USDT', score:90, spread:.001, hour_change:.01, eligible:true, ai_votes:{gemini:{action:'consider', confidence:.9, reason:'<img src=x onerror="window.XSS=true">', sources:[{url:'javascript:window.XSS=true',title:'unsafe'}]}}}]};
      await page.locator('#researchFile').setInputFiles({name:'stale.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(report))});
      await page.waitForFunction(() => document.getElementById('researchStatus').textContent.includes('Hết hạn'));
      assert.match(await page.locator('#researchRows').innerText(), /hết hạn/);
      assert.equal(await page.locator('#researchRows img').count(), 0);
      assert.equal(await page.locator('#researchRows a').count(), 0);
      assert.equal(await page.evaluate(() => window.XSS === true), false);
      await page.locator('#researchFile').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{bad')});
      await page.waitForFunction(() => document.getElementById('researchStatus').textContent.includes('Không đọc được'));
      assert.equal(await page.locator('#researchRows tr').count(), 0);
    });
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({started_at, completed_at:new Date().toISOString(), browser:await browser.version(), executablePath, scope:'Real browser + isolated mock HTTP service; no exchange/provider calls', results}, null, 2));
    console.log(JSON.stringify(results, null, 2));
    process.exitCode = results.some(r => r.status === 'FAIL') ? 1 : 0;
  } catch (error) { console.error(error); process.exitCode = 1; }
  finally { await browser?.close(); service?.kill(); }
})();
