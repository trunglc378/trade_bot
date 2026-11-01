"""Summarize backtests and reserve orders, without deploying or trading."""
import csv
import datetime as dt
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1] / 'user_data'
workspace = root / 'reports' / 'validation-20261101'
metrics = {}
for path in sorted((workspace / 'results').rglob('*.zip')):
    exchange, window = path.parent.parent.name, path.parent.name
    # The newest result in each directory wins; repeated stress checks are not independent samples.
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            if member.endswith('.json'):
                data = json.loads(archive.read(member))
                if 'strategy' not in data:
                    continue
                metrics.setdefault(exchange, {})[window] = {
                    name: {key: row.get(key) for key in ['total_trades', 'profit_total', 'profit_total_abs',
                           'profit_factor', 'max_drawdown_account', 'winrate']}
                    for name, row in data['strategy'].items()}

candidate = 'VnTrend1hCandidate'
reasons = []
bias_rows = []
bias_path = workspace / 'lookahead-binance.csv'
if bias_path.exists():
    with bias_path.open(encoding='utf-8-sig', newline='') as f:
        bias_rows = list(csv.DictReader(f))
bias_pass = any(r.get('strategy') == candidate and r.get('has_bias') in ['False', 'No']
                and int(r.get('total_signals') or 0) >= 20 for r in bias_rows)
if not bias_pass:
    reasons.append('Scoped lookahead check not verified')
for exchange in ['binance', 'okx']:
    holdout = metrics[exchange]['holdout'][candidate]
    stress = metrics[exchange]['stress'][candidate]
    if holdout['profit_total_abs'] <= 0:
        reasons.append(f'{exchange}: holdout PnL <= 0')
    if holdout['profit_factor'] < 1.2:
        reasons.append(f'{exchange}: holdout profit factor < 1.2')
    if holdout['max_drawdown_account'] > .05:
        reasons.append(f'{exchange}: holdout drawdown > 5%')
    if stress['profit_total_abs'] <= 0:
        reasons.append(f'{exchange}: higher-cost stress PnL <= 0')
reasons.append('No qualifying forward-test evidence')
plan = {'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
    'current_capital_per_exchange': 34.16, 'target_capital_per_exchange': 134.16,
    'proposed_stages': [34.16, 54.16, 84.16, 134.16],
    'max_open_trades': 2, 'stake_amount_ceiling_usdt': 15.37,
    'additional_reserve_target_per_exchange': 100,
    'automatic_capital_change_enabled': False, 'eligible_for_capital_increase': False,
    'reasons': reasons,
    'proposed_review_gates': {'holdout_profitable_both_exchanges': True, 'min_profit_factor': 1.2,
        'max_historical_drawdown': .05, 'higher_cost_stress_profitable': True,
        'forward_min_days': 7, 'forward_min_closed_trades_per_exchange': 30,
        'forward_max_drawdown': .03},
    'lookahead_scoped_pass': bias_pass, 'metrics': metrics}
(root / 'capital-review-20261101.private.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
lines = ['# Chuẩn bị vốn dự phòng và kiểm thử chiến lược — 01/11/2026', '',
    '## Trạng thái vốn', '',
    'Đã tạo hai lệnh limit post-only bán BTC theo đỉnh 7 ngày trước thời điểm chụp giá khoảng 16:25 VN ngày 01/11. Đây là mức giá cố định, không tự nâng theo đỉnh mới. Không có lịch tự động đặt lại lệnh.', '',
    '| Sàn | Giá giới hạn (USDT/BTC) | Số BTC | USDT ròng dự kiến với phí dự phòng 0,1% | Order ID |',
    '|---|---:|---:|---:|---|']
for exchange in ['binance', 'okx']:
    order = json.loads((root / f'reserve100-{exchange}-20261101.private.json').read_text(encoding='utf-8-sig'))
    lines.append(f'| {exchange.upper()} | {order["limit_price"]} | {order["quantity"]} | {order["expected_net_usdt"]} | {order["order_id"]} |')
lines += ['', 'Lúc xác minh ban đầu, cả hai lệnh đang open và filled=0: chưa có thêm 100 USDT khả dụng từ các lệnh này. Phí thực tế có thể thay đổi; số ròng là ước tính. Binance chỉ hoàn trả 0,00123 BTC từ Flexible Earn để bảo đảm lệnh, không dùng BTC thuộc vị thế bot. Không đổi available_capital=34,16 USDT mỗi sàn, stake_amount=15,37 và max_open_trades=2.', '',
    'PI và các coin khác chưa bán. Điều kiện hòa vốn sau phí cần giá vốn có chứng từ; không suy giá vốn bằng 0 từ dữ liệu thiếu. Bảng kê cần đối soát: gia-von-can-doi-soat-20261101.csv. Không tính các mã LD... đại diện Earn thêm lần nữa vào số lượng. Bảng này là snapshot trước khi đặt lệnh BTC, không phải số dư hiện tại.', '',
    'Giá bán hòa vốn tối thiểu cho lượng tài sản đã xác minh = tổng giá vốn phân bổ đã gồm phí mua / số lượng thực bán / (1 - phí bán), làm tròn tăng theo bước giá sàn. Cần xét cả phí tính bằng coin, Earn/reward, chuyển ví và các lần mua/bán trước đó. Coin hủy niêm yết hoặc dưới hạn mức giao dịch không thể mặc nhiên đổi toàn bộ bằng lệnh Spot.', '',
    '## Kiểm thử', '',
    'Image Freqtrade 2026.9 giữ nguyên digest như live. Dữ liệu nến 5m/1h từ 01/07–01/11/2026; warm-up đủ cho EMA200 1h. Giai đoạn phát triển 01/08–15/09; kiểm tra giữ riêng 15/09–29/10 UTC. Giai đoạn live gây ra yêu cầu sửa (29/10 trở đi) không dùng để chọn kết quả trong bảng.', '',
    'Cùng ví khởi đầu 34,16 USDT, tối đa 2 vị thế, trần stake 15,37, sizing/risk như live, protections được bật. Binance 7 cặp; OKX 5 cặp. Phí cơ sở 0,1% mỗi chiều cho cả hai sàn; stress 0,15% mỗi chiều để kiểm tra độ nhạy với chi phí. Không hyperopt hoặc thay ngưỡng sau khi xem giai đoạn giữ riêng.', '',
    '| Chiến lược | Binance: lợi nhuận giữ riêng | OKX: lợi nhuận giữ riêng |',
    '|---|---:|---:|']
labels = {'VnSmartTrendStrategy': 'Chiến lược live hiện tại', 'VnTrend1hCandidate': 'Thêm lọc xu hướng 1h',
          'VnEarlierTrailCandidate': 'Trailing bật +1,2%, khoảng cách 0,5%', 'VnTrendTrailCandidate': 'Lọc 1h + trailing sớm'}
for strategy, label in labels.items():
    b = metrics['binance']['holdout'][strategy]['profit_total']*100
    o = metrics['okx']['holdout'][strategy]['profit_total']*100
    lines.append(f'| {label} | {b:+.2f}% | {o:+.2f}% |')
lines += ['', 'Bộ lọc 1h giữ yêu cầu giá > EMA200, EMA50 > EMA200 và EMA50 tăng so với 3 giờ trước, ghép bằng informative() chỉ sau khi nến 1h đóng. Các biến thể là tệp nghiên cứu riêng, không thay chiến lược live.', '',
    'Ứng viên lọc 1h tuy cải thiện so với baseline nhưng chưa đạt:', '']
for exchange in ['binance', 'okx']:
    h = metrics[exchange]['holdout'][candidate]
    s = metrics[exchange]['stress'][candidate]
    lines.append(f'- {exchange.upper()}: {h["total_trades"]} lệnh giữ riêng, PF {h["profit_factor"]:.3f}, drawdown {h["max_drawdown_account"]*100:.2f}%; khi chi phí 0,15%/chiều, kết quả {s["profit_total"]*100:+.2f}%.')
lines += ['', '**Quyết định: CHƯA tăng vốn live, CHƯA triển khai các ứng viên.** Bằng chứng hiệu quả chưa đủ; quy trình không coi một backtest tốt hơn baseline là đủ để tăng tiền.', '',
    'Bậc vốn dự thảo: 34,16 → 54,16 → 84,16 → 134,16 USDT mỗi sàn. Giữ tối đa 2 vị thế và trần mỗi lệnh 15,37 cho đến lần đánh giá riêng về sizing. Các bậc là kế hoạch chờ xét, không phải lịch tự động hoặc thay đổi đã áp dụng. Mức kiểm tra đề xuất: lợi nhuận dương cả hai sàn, PF ≥ 1,2, drawdown lịch sử ≤ 5%, stress vẫn dương, kiểm tra bias đạt và forward tối thiểu 7 ngày/30 lệnh đóng mỗi sàn với drawdown ≤ 3%. Các ngưỡng là hàng rào đánh giá kỹ thuật, không bảo đảm lợi nhuận.', '',
    '## Giới hạn và bằng chứng', '',
    '- Backtest dùng OHLCV, không tái dựng sổ lệnh, trượt giá, lỗi mạng hoặc các phiếu AI lịch sử. Chế độ nghiên cứu đặt research=off, vì vậy đây là so sánh tín hiệu kỹ thuật; không giả là tái hiện chính xác giao dịch live.',
    '- Trailing trên nến 5m không tái dựng đường giá từng tick; không dùng kết quả đó để hứa hẹn mức lãi thực tế.',
    f'- Lookahead Binance của ứng viên 1h: {"đạt trên 20 tín hiệu được kiểm tra, không phát hiện bias" if bias_pass else "chưa xác minh đủ mẫu"}. Đây là kiểm tra có giới hạn, không chứng minh mọi trường hợp đều không có bias. Lần đầu vốn 34,16 không tương thích stake cố định của công cụ khiến 0 mẫu; cấu hình bias riêng đã bỏ hạn mức này rồi mới kiểm tra lại.',
    '- Recursive BTC/USDT Binance: so sánh 600/1200/2400 nến; EMA200 1h lệch khoảng 0,008% ở 600 nến trong phép thử, gần 0 ở 1200/2400. Không phát hiện nhìn trước trên các chỉ báo được kiểm tra. Log và CSV được lưu cùng báo cáo.',
    '- DB live đã được sao lưu bằng SQLite backup API và integrity_check=ok cho cả hai sàn; bản sao ở user_data/backups/pre-capital-20261101T092925Z/.',
    '- Tệp capital-review-20261101.private.json có kết quả và lý do chặn tăng vốn; không có lệnh sửa cấu hình hoặc giao dịch trong trình tổng hợp này.', '',
    'Tài liệu: https://www.freqtrade.io/en/stable/lookahead-analysis/ và https://docs.freqtrade.io/en/stable/strategy-customization/.', '']
(root / 'reports' / '2026-11-01-CHUAN-BI-VON-VA-KIEM-THU.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'eligible_for_capital_increase': False, 'reasons': reasons, 'metrics': metrics}))
