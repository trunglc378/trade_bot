const vn = 'Asia/Ho_Chi_Minh';
const dateKey = new Intl.DateTimeFormat('en-CA', { timeZone: vn, year: 'numeric', month: '2-digit', day: '2-digit' });

export function localDay(iso) {
  return dateKey.format(new Date(iso));
}

export function summarize(rows) {
  const values = { pnl: 0, wins: 0, losses: 0, flat: 0, closed: 0 };
  for (const row of rows) {
    values.pnl += row.pnl;
    values.wins += row.wins;
    values.losses += row.losses;
    values.flat += row.flat;
  }
  values.closed = values.wins + values.losses + values.flat;
  return values;
}

export function dashboardData(snapshot, exchange, window) {
  const end = localDay(snapshot.capturedAt);
  const start = window === 'all' ? '' :
    new Date(Date.parse(end) - (Number(window) - 1) * 86_400_000).toISOString().slice(0, 10);
  const inWindow = date => start <= date && date <= end;
  const exchanges = snapshot.exchanges.filter(row => exchange === 'all' || exchange === row.name);
  const rows = exchanges.flatMap(row => row.daily.filter(item => inWindow(item.date)));
  const totals = summarize(rows);
  const ordered = new Map();
  for (const row of rows) ordered.set(row.date, (ordered.get(row.date) ?? 0) + row.pnl);
  const sorted = [...ordered.entries()].sort(([a], [b]) => a.localeCompare(b));
  let cumulative = 0;
  const points = sorted.map(([date, pnl]) => ({ date, pnl: cumulative += pnl }));
  const recent = exchanges.flatMap(row => row.recent.map(trade => ({ ...trade, exchange: row.name })))
    .filter(row => inWindow(localDay(row.closedAt))).sort((a, b) => Date.parse(b.closedAt) - Date.parse(a.closedAt));

  return {
    totals, points, recent,
    exchanges: exchanges.map(row => ({ ...summarize(row.daily.filter(item => inWindow(item.date))),
      name: row.name, capital: row.capital })),
    openCount: exchanges.reduce((sum, row) => sum + row.openCount, 0),
    unrealized: exchanges.some(row => row.unrealized === null) ? null :
      exchanges.reduce((sum, row) => sum + row.unrealized, 0),
  };
}
