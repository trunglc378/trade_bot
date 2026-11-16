import { get, put } from '@vercel/blob';
import { createHash, timingSafeEqual } from 'node:crypto';

const path = 'freqbot-pnl-v1.json';
const exchanges = ['Binance', 'OKX'];
const hash = value => createHash('sha256').update(value).digest();

function authorized(value, secret) {
  return Boolean(secret && secret.length >= 32 && typeof value === 'string' &&
    timingSafeEqual(hash(value), hash('Bearer ' + secret)));
}

const amount = value => typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 1e9;
const count = value => Number.isInteger(value) && value >= 0 && value <= 1e7;
const day = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const stamp = value => typeof value === 'string' && value.length <= 35 && Number.isFinite(Date.parse(value));
const pair = value => typeof value === 'string' && /^[A-Z0-9]{1,20}\/USDT$/.test(value);

export function sanitizeSnapshot(input) {
  if (input?.version !== 1 || !stamp(input.capturedAt) ||
      Math.abs(Date.parse(input.capturedAt) - Date.now()) > 300_000 ||
      !Array.isArray(input.exchanges) || input.exchanges.length !== exchanges.length) throw new Error('snapshot');
  const clean = exchanges.map(name => {
    const s = input.exchanges.find(value => value?.name === name);
    if (!s || !amount(s.capital) || s.capital <= 0 || !count(s.openCount) ||
        !(s.unrealized === null || amount(s.unrealized)) ||
        !Array.isArray(s.daily) || s.daily.length > 15_000 ||
        !Array.isArray(s.recent) || s.recent.length > 35) throw new Error('exchange');
    const daily = s.daily.map(row => {
      if (!day(row?.date) || !pair(row.pair) || !amount(row.pnl) || !count(row.wins) ||
          !count(row.losses) || !count(row.flat) || !amount(row.gains) || row.gains < 0 ||
          !amount(row.lossAbs) || row.lossAbs < 0) throw new Error('daily');
      return { date: row.date, pair: row.pair, pnl: row.pnl, wins: row.wins, losses: row.losses,
        flat: row.flat, gains: row.gains, lossAbs: row.lossAbs };
    });
    const recent = s.recent.map(row => {
      if (!stamp(row?.closedAt) || !pair(row.pair) || !amount(row.pnl) ||
          typeof row.reason !== 'string' || !/^\w{0,80}$/.test(row.reason)) throw new Error('recent');
      return { closedAt: row.closedAt, pair: row.pair, pnl: row.pnl, reason: row.reason };
    });
    return { name, capital: s.capital, openCount: s.openCount, unrealized: s.unrealized, daily, recent };
  });
  return { version: 1, capturedAt: input.capturedAt, exchanges: clean };
}

export function makeHandler(storage) {
  return async (req, res) => {
    res.setHeader('Cache-Control', 'private, no-store');
    const method = req.method;
    if (method !== 'GET' && method !== 'POST') {
      res.setHeader('Allow', 'GET, POST');
      return res.status(405).json({ error: 'method_not_allowed' });
    }
    const secret = method === 'GET' ? process.env.DASHBOARD_ACCESS_CODE : process.env.SNAPSHOT_PUBLISH_TOKEN;
    if (!authorized(req.headers.authorization, secret)) return res.status(401).json({ error: 'unauthorized' });
    if (method === 'POST') {
      let snapshot;
      try {
        const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
        snapshot = sanitizeSnapshot(body);
        if (Buffer.byteLength(JSON.stringify(snapshot)) > 2_000_000) throw new Error('size');
      } catch {
        return res.status(400).json({ error: 'invalid_snapshot' });
      }
      try {
        await storage.write(snapshot);
        return res.status(200).json({ capturedAt: snapshot.capturedAt });
      } catch {
        return res.status(503).json({ error: 'storage_unavailable' });
      }
    }
    try {
      const snapshot = await storage.read();
      if (!snapshot) return res.status(404).json({ error: 'awaiting_first_snapshot' });
      return res.status(200).json(snapshot);
    } catch {
      return res.status(503).json({ error: 'storage_unavailable' });
    }
  };
}

export default makeHandler({
  async read() {
    const blob = await get(path, { access: 'private', useCache: false });
    return blob?.statusCode === 200 ? new Response(blob.stream).json() : null;
  },
  async write(snapshot) {
    await put(path, JSON.stringify(snapshot), {
      access: 'private', allowOverwrite: true, addRandomSuffix: false,
      contentType: 'application/json', cacheControlMaxAge: 60,
    });
  },
});
