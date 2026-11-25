# Gemini Pro và nghiên cứu thị trường từ nhiều nguồn

Cập nhật: 27/10/2026. Bổ sung cho [đặc tả triển khai](07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md).

## 1. Tận dụng gói Google AI Pro đang có

“Google AI Pro” là gói thuê bao; tên gói không phải model ID/API key của bot. Có hai cách sử dụng:

| Cách dùng | Phù hợp | Cấu hình |
| --- | --- | --- |
| Gemini trên web, bật nghiên cứu sâu/tìm kiếm nếu tài khoản hỗ trợ | Rà soát thủ công, phân tích luận điểm và kiểm tra chéo nguồn trước phiên trade | Dùng [mẫu prompt](../freqtrade-bot/user_data/research/gemini-pro-prompt.md) cùng snapshot mới nhất; không cần bot gọi API |
| Gemini API với Google Search grounding | Tự động cập nhật nghiên cứu cho pipeline hiện tại | Cần `GEMINI_API_KEY`, project/quota/billing và model hỗ trợ tools + JSON schema |

Theo [quyền lợi Google AI Pro](https://support.google.com/googleone/answer/14534406?hl=en), gói hiện có quyền lợi Google Developer Program premium gồm Google Cloud credit 10 USD/tháng, với điều kiện tài khoản đủ điều kiện và được liên kết với Developer Profile. Kiểm tra quyền lợi đã kích hoạt, billing project nhận credit và phạm vi dịch vụ được áp dụng trong tài khoản của bạn; bot không đọc được trạng thái thuê bao hoặc credit. Xem thêm [Developer Program benefits](https://developers.google.com/profile/help/benefits).

Không mặc định API miễn phí/không giới hạn vì đã mua Pro. Token/model và Google Search có cơ chế tính phí riêng của Gemini API; xem [billing](https://ai.google.dev/gemini-api/docs/billing) và [Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search). Trong lần bổ sung này chỉ sửa mã và test offline, không bật billing hoặc gọi API trả phí.

## 2. Cấu hình Gemini đa nguồn đã bổ sung

**Cập nhật 25/11/2026:** Overlay hiện bổ sung `ai_control.enabled: false` mặc định. Cần đọc [hạn mức/circuit mới](12-DIEU-TRA-REQUEST-VA-GIOI-HAN-AI.md) trước khi bật gọi mạng. Worker vẫn lấy dữ liệu công khai mỗi 300 giây nhưng không hỏi Gemini mỗi vòng; output cap mới 1.000 token. Các đoạn bên dưới về cấu hình provider vẫn áp dụng sau khi chủ động bật control.

Overlay `freqtrade-bot/user_data/config-gemini-research.json`:

```json
{
  "vn_policy": {
    "research": {
      "mode": "advisory",
      "providers": {
        "gemini": {
          "model": "gemini-pro-latest",
          "google_search": true,
          "min_source_domains": 2,
          "source_domains": [
            "binance.com", "okx.com", "ethereum.org", "solana.com",
            "federalreserve.gov", "sec.gov", "reuters.com", "coindesk.com"
          ]
        }
      },
      "min_ai_votes": 1,
      "min_ai_confidence": 0.75
    }
  }
}
```

`gemini-pro-latest` là alias model cấu hình mẫu, khác tên gói Google AI Pro. Quyền truy cập và khả năng hỗ trợ grounding/JSON phải được kiểm tra trong project của bạn; có thể thay model ID theo [Interactions API](https://ai.google.dev/api/interactions-api). Alias có thể đổi phiên bản phía Google; khi nghiệm thu nên ghi lại model thực tế và pin model phù hợp.

Luồng mới dùng API Interactions, thêm `tools: [{"type": "google_search"}]`, yêu cầu JSON có danh sách `sources` cho từng cặp. Dạng cũ `"gemini": "model-id"` vẫn hoạt động như trước: phân tích chỉ số được đưa vào, không bật Search.

### Chạy một lần để xem kết quả

Từ thư mục gốc, đặt API key bằng môi trường cục bộ hoặc qua `.env` cho Docker. Không đưa key vào chat, mã frontend hoặc Git.

```powershell
python freqtrade-bot/user_data/research/run.py --config freqtrade-bot/user_data/config.json --config freqtrade-bot/user_data/config-gemini-research.json
```

Python riêng cần cài CCXT như hướng dẫn 07. Với Docker, từ `freqtrade-bot`:

```powershell
docker compose run --rm research --config /freqtrade/user_data/config.json --config /freqtrade/user_data/config-gemini-research.json
```

Worker ghi `latest.json` và history; dashboard chọn tệp hoặc đồng bộ từ mock để xem nhận định kèm nguồn. Bản chạy một lần không khởi động bot giao dịch và không thay cấu hình bot đang chạy.

### Áp dụng vào bot

Phải truyền overlay cho CẢ worker và Freqtrade, vì context hash bao gồm cấu hình provider. Khi chỉ thử nghiên cứu riêng mà bot vẫn dùng config gốc, snapshot mới sẽ không khớp context và bot chặn mua; đây là cơ chế bảo vệ dự kiến.

Để chạy lâu dài, thêm `--config /freqtrade/user_data/config-gemini-research.json` sau config gốc vào command của cả hai service. Nếu dùng OKX, thứ tự là config gốc → config OKX → config Gemini ở cả hai phía. Worker hỗ trợ nhiều `--config` với cách merge object tương ứng; danh sách được thay thế.

Nếu config gốc đã có `openai`, overlay merge sẽ giữ provider đó. Muốn chỉ dùng Gemini, bỏ `openai` trong cấu hình hiệu lực. Muốn hai AI đồng thuận, giữ OpenAI và Gemini, đặt `mode: required`, `min_ai_votes: 2`; cần API key hợp lệ cho cả hai. Với chỉ Gemini, required dùng `min_ai_votes: 1`.

Không coi hai hay nhiều website do Gemini đọc là hai AI độc lập. Gemini luôn chỉ có một phiếu trong quorum.

## 3. Những nguồn nào cần phân tích?

| Nhóm | Câu hỏi nghiên cứu | Ví dụ nguồn |
| --- | --- | --- |
| Sàn | Niêm yết/hủy niêm yết, bảo trì, thay quy tắc giao dịch? | Thông báo chính thức Binance, OKX |
| Dự án | Nâng cấp, sự cố mạng, exploit hoặc thay đổi kỹ thuật? | Ethereum, Solana hoặc website chính thức của coin trong universe |
| Vĩ mô/pháp lý | Lịch họp, công bố chính sách hay sự kiện mới có thể gây biến động? | Federal Reserve, SEC, cơ quan gốc liên quan |
| Báo chí | Có xác nhận độc lập hoặc thông tin phản bác luận điểm? | Reuters, CoinDesk; ưu tiên bài có tác giả và thời gian |
| Định lượng | Diễn biến giá/volume/EMA/RSI có đồng thuận với thông tin bên ngoài? | OHLCV/ticker/orderbook từ sàn qua worker |

Danh sách miền là ví dụ được phép trích dẫn, không phải cam kết website luôn đúng. Thêm domain chính thức của coin bạn quan tâm. Không dùng số lượt nhắc mạng xã hội hoặc một bài quảng bá làm lý do duy nhất để mua.

Prompt tự động yêu cầu đối chiếu thông báo gốc, tin mới, bằng chứng phản bác và thời gian sự kiện. Đây là yêu cầu đối với model, không phải bộ crawler độc lập đã xác minh từng câu hoặc từng ngày đăng.

## 4. Kiểm tra nguồn trước khi cho phiếu mua

- Chỉ chấp nhận URL HTTPS hợp lệ, không user/password, thuộc miền được cho phép hoặc subdomain của miền đó.
- URL phải xuất hiện trong `url_citation` gốc của response API và trong `sources` của cặp coin. Link model tự viết thêm không được tính.
- Tối thiểu hai miền nguồn khác nhau mặc định; hai subdomain của cùng miền cấu hình chỉ tính một. Không cho cấu hình miền cha/con chồng nhau.
- Không đủ nguồn: `consider` chuyển thành `wait` và ghi `evidence_status: insufficient_sources`. `avoid` vẫn là phiếu thận trọng; nguồn ít không tự biến nó thành quyền mua.
- Lưu URL, title, domain, trạng thái bằng chứng vào snapshot/history. Web tạo link nguồn an toàn; không render HTML từ nội dung model.
- Grounding không vượt được lịch, giới hạn vốn, dữ liệu hết hạn hoặc bộ lọc kỹ thuật. Trong advisory, AI vẫn chỉ là tham khảo và không chặn lệnh kỹ thuật; muốn AI thiếu bằng chứng chặn mua, dùng required.

Giới hạn: đa dạng domain không chứng minh các bài độc lập hoặc nội dung chính xác. Chưa fetch nội dung từng URL, kiểm tra ngày đăng tự động hay kiểm chứng claim-level. Một số response có thể thiếu annotations khi dùng JSON schema; lúc đó lời đề xuất mua bị chuyển thành wait. URL redirect Google không thuộc allowlist cũng không tự được tính; không tự truy cập để mở rộng redirect. Source nào không được thu thập hoặc không có tin mới phải được xem là thiếu dữ liệu.

Search có thể tạo nhiều truy vấn trong một request. Giới hạn 4.000 output token/response 1 MB và timeout 25 giây không phải giới hạn cứng chi phí tìm kiếm. Model reasoning + web search có thể timeout, khi đó required không mua. Nên bắt đầu chạy một lần, kiểm tra nguồn và usage thực tế trước khi bật vòng lặp 300 giây; không coi credit thuê bao là ngân sách vô hạn.

## 5. Dùng trực tiếp thuê bao Gemini Pro

Mở Gemini, chọn chế độ nghiên cứu phù hợp tài khoản, dán [mẫu prompt nghiên cứu](../freqtrade-bot/user_data/research/gemini-pro-prompt.md) rồi đính kèm snapshot thị trường mới. Chỉ cung cấp chỉ số công khai; không gửi API key hoặc dữ liệu tài khoản riêng. Thay khung thời gian và danh sách cặp đúng với lần chạy.

Kết quả thủ công là tài liệu để bạn kiểm tra và quyết định. Hiện bot chưa có importer xác thực báo cáo copy từ Gemini web, và không tự dùng cookie/phiên đăng nhập thuê bao để gọi API. Không chép báo cáo thủ công thành `latest.json` để làm như phiếu API đã qua kiểm chứng.

## 6. Kiểm thử và phạm vi

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -m unittest discover -s freqtrade-bot/tests -v
node tests/test_dashboard.js
```

Có test cho payload Search, nguồn trong native citations, link bịa/link không an toàn, nhiều subdomain cùng miền, cấu hình Gemini-only, tương thích provider dạng chuỗi và render link web. Tests dùng phản hồi giả, chưa gọi Gemini API thật hoặc kiểm tra credit của tài khoản. Không có kết luận lợi nhuận từ nghiên cứu đa nguồn.
