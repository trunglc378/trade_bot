# Kiểm thử trước khi tăng vốn

Các tệp ở đây dành cho nghiên cứu, không được thêm tên chiến lược ứng viên vào
Docker Compose live khi chưa có bằng chứng đạt yêu cầu. Không có script tự tăng
vốn hoặc tự triển khai chiến lược.

Đợt 01/11/2026:

- Hạn mức live vẫn **34,16 USDT/sàn**, trần stake **15,37 USDT**, tối đa **2 vị thế**.
- Đã đặt lệnh bán BTC limit theo đỉnh 7 ngày để chuẩn bị thêm khoảng 100 USDT/sàn.
  Order/journal riêng trong `user_data/*.private.json`; đây không phải lệnh của
  database Freqtrade, không nhập chúng vào thống kê lãi/lỗ bot.
- PI và coin khác giữ nguyên khi chưa chứng minh giá vốn sau phí. Bảng CSV ở
  `user_data/reports/gia-von-can-doi-soat-20261101.csv` cần đối soát, không coi
  nguồn vốn không rõ là vốn 0.

## Quy trình đã chạy

1. `prepare_workspace.py` chỉ đọc cấu hình công khai, sao chép baseline và ứng viên
   vào `user_data/reports/validation-20261101`. Workspace không có khóa API.
2. `run_validation.py` chạy bên trong container riêng trên VPS, ghim cùng image
   live. Giới hạn container 1 CPU/2 GiB RAM, không mount thư mục live.
3. Download nến 5m/1h 01/07–01/11; phát triển 01/08–15/09, giữ riêng
   15/09–29/10 UTC, phí 0,1% mỗi chiều và protections được bật.
4. So sánh baseline, lọc 1h, trailing sớm, và kết hợp hai thay đổi. Không hyperopt.
5. `check_candidates.py` thử chi phí 0,15% mỗi chiều và kiểm tra lookahead,
   recursive của ứng viên 1h. Lookahead dùng wallet lớn mặc định của công cụ,
   bỏ `available_capital` **chỉ trong cấu hình bias** để không chặn mọi tín hiệu;
   cấu hình hiệu quả và cấu hình live vẫn có vốn 34,16.
6. `summarize_validation.py` tạo báo cáo, không có thao tác sửa cấu hình live.

Chạy trình tổng hợp trên Windows sau khi tải kết quả về:

```powershell
& .\.venv\Scripts\python.exe freqtrade-bot\validation\summarize_validation.py
```

Kết quả hiện tại: **chưa đạt điều kiện tăng vốn**. Bản lọc 1h giữ riêng đạt
Binance +0,78%, OKX -0,34%; stress chi phí âm cả hai sàn. Trailing sớm xấu hơn
baseline. Không triển khai ứng viên dựa trên kết quả này.

Kết quả và nhật ký nằm trong `user_data/reports/`, bị Git bỏ qua để tránh đưa
lịch sử tài khoản lên repository. DB snapshot nhất quán nằm trong
`user_data/backups/pre-capital-20261101T092925Z/`.

Backtest không tái dựng được sổ lệnh/AI lịch sử hoặc bảo đảm khớp limit; số liệu
chỉ để bác bỏ/đánh giá giả thuyết, không hứa hẹn lợi nhuận tương lai.
