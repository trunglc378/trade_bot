import { dashboardData } from './metrics.js';

const id = key => document.getElementById(key);
const number = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 4 });
const profit = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 4, signDisplay: 'exceptZero' });
const date = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'short', timeStyle: 'short' });
const reasons = {
  roi: 'Chốt theo mục tiêu', stoploss_on_exchange: 'Stop-loss trên sàn',
  GAY_XU_HUONG_EMA20_50: 'Xu hướng EMA suy yếu',
  CHOT_LOI_QUA_MUA_RSI_BB: 'Chốt khi quá mua',
  trailing_stop_loss: 'Trailing stop', force_exit: 'Thoát thủ công',
};
let code = '';
let snapshot;
let pending;
let points = [];

function status(message = '', error = false) {
  id('status').textContent = message;
  id('status').dataset.state = error ? 'error' : '';
}

function money(value) {
  return value === null ? 'Chưa có giá' : profit.format(value) + ' USDT';
}

function pnlCell(element, value) {
  element.textContent = money(value);
  element.classList.toggle('positive', value > 0);
  element.classList.toggle('negative', value < 0);
}

function rate(row) {
  return row.closed ? number.format(100 * row.wins / row.closed) + '%' : '—';
}

function table(target, rows, columnCount) {
  const tbody = id(target);
  tbody.replaceChildren();
  if (!rows.length) {
    const cell = tbody.insertRow().insertCell();
    cell.colSpan = columnCount;
    cell.textContent = 'Không có giao dịch trong khoảng đã chọn.';
    return;
  }
  for (const { fields, pnl } of rows) {
    const row = tbody.insertRow();
    for (const field of fields) row.insertCell().textContent = field;
    pnlCell(row.insertCell(), pnl);
  }
}

function draw() {
  const canvas = id('chart');
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const density = window.devicePixelRatio || 1;
  canvas.width = width * density;
  canvas.height = height * density;
  const ctx = canvas.getContext('2d');
  ctx.scale(density, density);
  ctx.font = '12px system-ui';
  ctx.fillStyle = '#a5b2c2';
  if (!points.length) {
    ctx.fillText('Không có lệnh đã đóng', 20, 36);
    id('chart-value').textContent = '—';
    return;
  }
  const pad = { top: 15, bottom: 30, left: 56, right: 20 };
  const min = Math.min(0, ...points.map(point => point.pnl));
  const max = Math.max(0, ...points.map(point => point.pnl));
  const spread = max - min || 1;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const start = Date.parse(points[0].date);
  const end = Date.parse(points.at(-1).date);
  const x = p => pad.left + (end === start ? .5 : (Date.parse(p.date) - start) / (end - start)) * plotW;
  const y = v => pad.top + (max - v) / spread * plotH;
  for (let i = 0; i <= 3; i++) {
    const value = max - spread * i / 3;
    const lineY = y(value);
    ctx.beginPath();
    ctx.moveTo(pad.left, lineY);
    ctx.lineTo(width - pad.right, lineY);
    ctx.strokeStyle = '#35414d';
    ctx.stroke();
    ctx.fillText(number.format(value), 8, lineY + 4);
  }
  ctx.beginPath();
  points.forEach((p, i) => i ? ctx.lineTo(x(p), y(p.pnl)) : ctx.moveTo(x(p), y(p.pnl)));
  ctx.strokeStyle = '#6be4cf';
  ctx.lineWidth = 2.5;
  ctx.stroke();
  const active = points[Number(id('chart-day').value)] ?? points.at(-1);
  ctx.beginPath();
  ctx.arc(x(active), y(active.pnl), 5, 0, Math.PI * 2);
  ctx.fillStyle = '#6be4cf';
  ctx.fill();
  id('chart-value').textContent = active.date.split('-').reverse().join('/') + ' · ' + money(active.pnl);
}

function render() {
  if (!snapshot) return;
  const data = dashboardData(snapshot, id('exchange').value, id('range').value);
  const { totals } = data;
  const captured = new Date(snapshot.capturedAt);
  id('updated').dateTime = snapshot.capturedAt;
  id('updated').textContent = 'Dữ liệu ' + date.format(captured);
  pnlCell(id('pnl'), totals.pnl);
  id('winrate').textContent = rate(totals);
  id('winloss').textContent = `${totals.wins} thắng · ${totals.losses} thua`;
  id('closed').textContent = number.format(totals.closed);
  id('flat').textContent = `${totals.flat} hòa vốn`;
  pnlCell(id('open-pnl'), data.unrealized);
  id('open-count').textContent = `${data.openCount} vị thế tại lần cập nhật`;
  table('exchange-rows', data.exchanges.map(row => ({
    fields: [row.name, number.format(row.capital) + ' USDT', number.format(row.closed), rate(row)], pnl: row.pnl,
  })), 5);
  table('trade-rows', data.recent.map(trade => ({
    fields: [date.format(new Date(trade.closedAt)), trade.exchange, trade.pair, reasons[trade.reason] ?? (trade.reason || '—')],
    pnl: trade.pnl,
  })), 5);
  points = data.points;
  const last = Math.max(0, points.length - 1);
  id('chart-day').max = String(last);
  id('chart-day').value = String(last);
  id('chart-day').disabled = points.length < 2;
  draw();
}

function lock(focus = false) {
  pending?.abort();
  pending = undefined;
  code = '';
  snapshot = undefined;
  points = [];
  id('dashboard').hidden = id('refresh').hidden = id('lock').hidden = true;
  id('access').hidden = false;
  id('unlock').disabled = id('refresh').disabled = false;
  id('code').value = '';
  status();
  if (focus) id('code').focus();
}

async function refresh() {
  if (!code || pending) return;
  const request = new AbortController();
  pending = request;
  id('unlock').disabled = id('refresh').disabled = true;
  status('Đang tải số liệu…');
  try {
    const response = await fetch('/api/snapshot', {
      headers: { Authorization: 'Bearer ' + code }, cache: 'no-store', signal: request.signal,
    });
    if (pending !== request) return;
    if (response.status === 401) {
      lock(true);
      status('Mã truy cập không hợp lệ.', true);
      return;
    }
    if (response.status === 404) {
      status('Đang chờ lần đồng bộ đầu tiên từ VPS.', true);
      return;
    }
    if (!response.ok) throw new Error('fetch');
    const received = await response.json();
    if (pending !== request) return;
    snapshot = received;
    id('access').hidden = true;
    id('dashboard').hidden = id('refresh').hidden = id('lock').hidden = false;
    status(Date.now() - Date.parse(snapshot.capturedAt) > 65 * 60_000 ?
      'VPS chưa gửi bản cập nhật trong 65 phút qua.' : '');
    render();
  } catch {
    if (pending === request) status('Không tải được dữ liệu. Vui lòng thử lại.', true);
  } finally {
    if (pending === request) {
      pending = undefined;
      id('unlock').disabled = id('refresh').disabled = false;
    }
  }
}

id('login').addEventListener('submit', event => {
  event.preventDefault();
  code = id('code').value.trim();
  id('code').value = '';
  refresh();
});
id('refresh').addEventListener('click', refresh);
id('lock').addEventListener('click', () => lock(true));
id('exchange').addEventListener('change', render);
id('range').addEventListener('change', render);
id('chart-day').addEventListener('input', draw);
new ResizeObserver(draw).observe(id('chart'));
window.setInterval(() => {
  if (!document.hidden && snapshot) refresh();
}, 5 * 60_000);
