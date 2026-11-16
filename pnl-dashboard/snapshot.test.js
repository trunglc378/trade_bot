import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHandler, sanitizeSnapshot } from './api/snapshot.js';
import { dashboardData, localDay } from './metrics.js';

const capturedAt = new Date().toISOString();
const day = localDay(capturedAt);
const trade = (pnl, wins, losses) => ({
  date: day, pair: 'BTC/USDT', pnl, wins, losses, flat: 0,
  gains: Math.max(0, pnl), lossAbs: Math.max(0, -pnl),
});
const fixture = {
  version: 1, capturedAt, excludedField: 'discard',
  exchanges: [
    { name: 'Binance', capital: 34.16, openCount: 1, unrealized: -.5, daily: [trade(1, 1, 0)], recent: [] },
    { name: 'OKX', capital: 34.16, openCount: 0, unrealized: 0, daily: [trade(-2, 0, 1)], recent: [] },
  ],
};

test('filter by Vietnamese close date and exchange', () => {
  assert.equal(localDay('2026-11-16T17:00:00Z'), '2026-11-17');
  const data = dashboardData(fixture, 'all', '7');
  assert.deepEqual(data.totals, { pnl: -1, wins: 1, losses: 1, flat: 0, closed: 2 });
  assert.equal(data.points.at(-1).pnl, -1);
  assert.equal(dashboardData(fixture, 'Binance', 'all').unrealized, -.5);
});

test('snapshot retains only dashboard fields and rejects stale uploads', () => {
  assert.equal(sanitizeSnapshot(fixture).excludedField, undefined);
  assert.throws(() => sanitizeSnapshot({ ...fixture, capturedAt: '2020-01-01T00:00:00Z' }));
});

test('viewer cannot publish and publisher cannot read', async () => {
  const viewer = 'v'.repeat(48);
  const publisher = 'p'.repeat(48);
  process.env.DASHBOARD_ACCESS_CODE = viewer;
  process.env.SNAPSHOT_PUBLISH_TOKEN = publisher;
  let snapshot;
  const handler = makeHandler({ read: async () => snapshot, write: async value => { snapshot = value; } });
  async function send(method, token, body) {
    const res = { setHeader() {}, status(code) { this.code = code; return this; }, json(value) { this.payload = value; } };
    await handler({ method, headers: { authorization: token ? 'Bearer ' + token : '' }, body }, res);
    return res;
  }
  assert.equal((await send('GET')).code, 401);
  assert.equal((await send('GET', viewer)).code, 404);
  assert.equal((await send('POST', viewer, fixture)).code, 401);
  assert.equal((await send('POST', publisher, fixture)).code, 200);
  assert.equal((await send('GET', publisher)).code, 401);
  assert.deepEqual((await send('GET', viewer)).payload, sanitizeSnapshot(fixture));
});
