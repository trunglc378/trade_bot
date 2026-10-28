/**
 * Logic Điều Khiển Giao Diện Web Tiếng Việt Kết Nối Trực Tiếp Freqtrade REST API & Cố Vấn Đa Nguồn AI
 * Dự án: FreqBot VN Remote v2.0 (Chuẩn hóa 100% Giao diện Tiếng Việt)
 */

let jwtToken = "";
let timerId = null;
let researchSnapshot = null;

function layBotUrl() {
    return document.getElementById("botUrl").value.trim().replace(/\/+$/, "");
}

function dichLyDoKhoa(reason) {
    if (!reason) return "Không rõ nguyên nhân";
    const r = reason.toLowerCase();
    if (r.includes("maxdrawdown")) return "Chạm hạn mức sụt giảm trên lịch sử lệnh đóng (MaxDrawdown)";
    if (r.includes("stoplossguard")) return "Chạm giới hạn số lệnh cắt lỗ trong kỳ (StoplossGuard)";
    if (r.includes("cooldown")) return "Đang nghỉ ngơi sau khi đóng lệnh (CooldownPeriod)";
    if (r.includes("lowprofit")) return "Cách ly cặp coin hiệu suất kém (LowProfitPairs)";
    return reason;
}

function dichTinHieuMua(tag) {
    if (!tag) return "Tín hiệu kỹ thuật chính";
    const map = {
        "XU_HUONG_TANG_EMA_RSI": "Xu hướng tăng (EMA 20/50/200 + RSI)",
        "BAT_NHIP_HOI_BOLLINGER_RSI": "Bắt nhịp hồi quá bán (Bollinger + RSI)",
        "TIN_HIEU_CHINH": "Tín hiệu kỹ thuật chính"
    };
    return map[tag] || tag;
}

function dichTrangThaiThiTruong(regime) {
    if (!regime) return "Chưa xác định";
    const map = {
        "TĂNG_MẠNH": "Xu hướng tăng mạnh",
        "TĂNG_ỔN_ĐỊNH": "Xu hướng tăng ổn định",
        "XU_HƯỚNG_YẾU": "Xu hướng yếu / Đi ngang",
        "THANH_KHOẢN_THẤP": "Thanh khoản thấp / Spread rộng",
        "BIẾN_ĐỘNG_CAO": "Biến động mạnh bất thường"
    };
    return map[regime] || regime;
}

function dichCheDoAi(mode) {
    const map = {
        "off": "Tắt AI (Chỉ lọc kỹ thuật)",
        "advisory": "Tham khảo (Advisory)",
        "required": "Bắt buộc đồng thuận AI (Required)"
    };
    return map[mode] || mode || "Tham khảo";
}

// 1. Đăng nhập lấy JWT Token điều khiển (/api/v1/token/login)
async function ketNoiVaDangNhap() {
    const botUrl = layBotUrl();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const connBadge = document.getElementById("connStatus");

    try {
        const basicAuth = btoa(`${username}:${password}`);
        const res = await fetch(`${botUrl}/token/login`, {
            method: "POST",
            headers: { "Authorization": `Basic ${basicAuth}` }
        });

        if (!res.ok) {
            throw new Error(`Đăng nhập thất bại (Mã lỗi HTTP ${res.status})`);
        }

        const data = await res.json();
        jwtToken = data.access_token;
        connBadge.textContent = "🟢 Đã kết nối Bot (Đang đồng bộ 5 giây/lần)";

        await capNhatToanBoBangDieuKhien();
        await dongBoNghienCuuTuServer();
        if (timerId) clearInterval(timerId);
        timerId = setInterval(capNhatToanBoBangDieuKhien, 5000);
    } catch (err) {
        connBadge.textContent = "🔴 Lỗi kết nối máy chủ Bot";
        alert("Không thể kết nối hoặc đăng nhập vào máy chủ Freqtrade:\n" + err.message);
    }
}

// 2. Lấy toàn bộ số liệu Lợi nhuận, Số dư, Lệnh đang mở, Cấu hình & Giáp bảo vệ rủi ro
async function capNhatToanBoBangDieuKhien() {
    if (!jwtToken) return;
    const botUrl = layBotUrl();
    const headers = { "Authorization": `Bearer ${jwtToken}` };

    try {
        const [profitRes, balanceRes, statusRes, locksRes, configRes] = await Promise.all([
            fetch(`${botUrl}/profit`, { headers }),
            fetch(`${botUrl}/balance`, { headers }),
            fetch(`${botUrl}/status`, { headers }),
            fetch(`${botUrl}/locks`, { headers }),
            fetch(`${botUrl}/show_config`, { headers }).catch(() => null)
        ]);
        if ([profitRes, balanceRes, statusRes, locksRes].some(r => !r.ok)) {
            throw new Error("Không tải được dữ liệu xác thực từ máy chủ Bot");
        }

        const loiNhuan = await profitRes.json();
        const soDu = await balanceRes.json();
        const danhSachLenh = await statusRes.json();
        const khoaRuiRo = await locksRes.json();

        // Cập nhật trạng thái kết nối & chế độ mua mới từ /show_config (nếu có)
        if (configRes && configRes.ok) {
            const cfg = await configRes.json();
            const connBadge = document.getElementById("connStatus");
            const cheDoChay = cfg.dry_run ? "Chạy thử (Dry-Run)" : "Tiền thật (Live)";
            if (cfg.max_open_trades === 0 || cfg.stopbuy_active) {
                connBadge.textContent = `⏸️ Đang tạm dừng Mua mới | ${cheDoChay}`;
            } else {
                connBadge.textContent = `🟢 Đang hoạt động (${cheDoChay} • Tối đa ${cfg.max_open_trades} lệnh)`;
            }
        }

        // Cập nhật thẻ Lợi nhuận
        const elProfit = document.getElementById("tongLaiUsdt");
        const laiUsdt = Number(loiNhuan.profit_all_coin || 0);
        const laiPct = Number(loiNhuan.profit_all_percent || 0);
        elProfit.textContent = `${laiUsdt >= 0 ? "+" : ""}${laiUsdt.toFixed(2)} USDT (${laiPct >= 0 ? "+" : ""}${laiPct.toFixed(2)}%)`;
        elProfit.className = "metric-big " + (laiUsdt >= 0 ? "text-green" : "text-red");

        const win = Number(loiNhuan.winning_trades || 0);
        const loss = Number(loiNhuan.losing_trades || 0);
        const winRate = (win + loss) > 0 ? ((win / (win + loss)) * 100).toFixed(1) : "0.0";
        const maxDd = (Number(loiNhuan.max_drawdown || 0) * 100).toFixed(2);
        document.getElementById("chiTietLoiNhuan").textContent =
            `Thắng/Thua: ${win}/${loss} lệnh (Tỷ lệ thắng: ${winRate}%) | Sụt giảm tối đa: ${maxDd}%`;

        // Cập nhật thẻ Số dư
        document.getElementById("tongTaiSanUsdt").textContent = `${Number(soDu.total || 0).toFixed(2)} USDT`;
        document.getElementById("chiTietSoDu").textContent =
            `Vốn rảnh sẵn sàng mua: ${Number(soDu.free || 0).toFixed(2)} USDT | Vốn đang mở lệnh: ${Number(soDu.used || 0).toFixed(2)} USDT`;

        // Cập nhật trạng thái Giáp bảo vệ rủi ro
        const riskBanner = document.getElementById("riskBanner");
        if (khoaRuiRo.lock_count > 0) {
            riskBanner.className = "card risk-banner danger";
            const chiTiet = khoaRuiRo.locks.map(l =>
                `⚠️ Đang khóa [${l.pair === "*" ? "TOÀN BỘ BOT" : l.pair}] do: ${dichLyDoKhoa(l.reason)} (Mở khóa lúc: ${l.lock_end_time})`
            ).join("<br>");
            riskBanner.innerHTML = `🛡️ <strong>CẢNH BÁO RỦI RO ĐANG KÍCH HOẠT:</strong><br>${chiTiet}`;
        } else {
            riskBanner.className = "card risk-banner";
            riskBanner.textContent = "🟢 Trạng thái an toàn: Không có khóa mua mới nào đang kích hoạt. Bộ giáp bảo vệ (MaxDrawdown, StoplossGuard, CooldownPeriod) và Cắt lỗ cứng (-3%) trên sàn đang trực chiến.";
        }

        // Cập nhật bảng Lệnh đang mở
        const tbody = document.getElementById("bangLenhDangMo");
        if (!Array.isArray(danhSachLenh) || danhSachLenh.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="empty-row">Hiện không có lệnh nào đang mở (100% vốn đang ở trạng thái USDT an toàn).</td></tr>`;
        } else {
            tbody.innerHTML = danhSachLenh.map(lenh => {
                const pnlPct = (Number(lenh.profit_ratio || 0) * 100).toFixed(2);
                const pnlUsdt = Number(lenh.profit_abs || 0).toFixed(2);
                const dangLai = Number(lenh.profit_abs || 0) >= 0;
                const slDist = (Number(lenh.stoploss_current_dist_ratio || 0) * 100).toFixed(2);
                const nhanMua = dichTinHieuMua(lenh.enter_tag);
                return `
                    <tr>
                        <td><strong>#${lenh.trade_id}</strong></td>
                        <td><strong>${lenh.pair}</strong></td>
                        <td>${Number(lenh.stake_amount).toFixed(2)} USDT</td>
                        <td>${Number(lenh.open_rate).toFixed(4)}</td>
                        <td>${Number(lenh.current_rate).toFixed(4)}</td>
                        <td class="${dangLai ? 'text-green' : 'text-red'}">
                            <strong>${dangLai ? '🟢 Đang lãi +' : '🔴 Đang lỗ '}${pnlPct}% (${dangLai ? '+' : ''}${pnlUsdt} USDT)</strong>
                        </td>
                        <td>${Number(lenh.stop_loss_abs).toFixed(4)} (${slDist}%)</td>
                        <td>${nhanMua}</td>
                        <td>
                            <button class="btn btn-sm-danger" onclick="dongMotLenh('${lenh.trade_id}', '${lenh.pair}')">
                                Đóng lệnh này
                            </button>
                        </td>
                    </tr>
                `;
            }).join("");
        }
    } catch (err) {
        console.error("Lỗi đồng bộ dữ liệu:", err);
    }
}

// 3. Đồng bộ báo cáo Nghiên cứu Thị trường & Đề xuất Coin AI từ Máy chủ (/api/v1/vn_research)
async function dongBoNghienCuuTuServer() {
    if (!jwtToken) return;
    try {
        const res = await fetch(`${layBotUrl()}/vn_research`, {
            headers: { "Authorization": `Bearer ${jwtToken}` }
        });
        if (!res.ok) {
            if (res.status === 404) {
                document.getElementById("researchStatus").textContent =
                    "Máy chủ Freqtrade gốc không mở endpoint /vn_research; vui lòng nhấn nút '📂 Chọn Tệp latest.json' để xem báo cáo AI.";
            }
            return;
        }
        const report = await res.json();
        if (report && report.schema_version === 1 && Array.isArray(report.candidates)) {
            researchSnapshot = report;
            hienThiNghienCuu();
        }
    } catch (err) {
        // Khi kết nối tới Freqtrade container không có endpoint /vn_research thì người dùng chọn tệp latest.json
    }
}

function trangThaiPhien(report, now = new Date()) {
    if (typeof report.schedule_enabled !== "boolean") return "Chưa có lịch giao dịch trong báo cáo";
    if (!report.schedule_enabled) return "Lịch mua mới mở 24/7";
    const local = new Date(now.getTime() + 7 * 3600000);
    const weekday = (local.getUTCDay() + 6) % 7;
    const current = local.getUTCHours() * 60 + local.getUTCMinutes();
    const windows = report.schedule_windows || [];
    const opened = windows.some(w => {
        const toMinute = s => {const [h, m] = s.split(":").map(Number); return h * 60 + m;};
        const start = toMinute(w.start), end = toMinute(w.end);
        return start < end ? w.weekdays.includes(weekday) && start <= current && current < end
            : start > end && ((current >= start && w.weekdays.includes(weekday))
                || (current < end && w.weekdays.includes((weekday + 6) % 7)));
    });
    const labels = windows.map(w => `${w.start}–${w.end}`).join(", ");
    return `${opened ? "Trong" : "Ngoài"} khung giờ mua (${labels} giờ VN); vẫn canh chốt lời/cắt lỗ 24/7`;
}

function hienThiNghienCuu() {
    if (!researchSnapshot) return;
    const report = researchSnapshot;
    const fresh = Date.parse(report.generated_at) <= Date.now() && Date.now() < Date.parse(report.expires_at);
    const status = document.getElementById("researchStatus");
    const sessionBadge = trangThaiPhien(report);
    const cheDoHienThi = dichCheDoAi(report.mode);
    status.textContent = `${report.is_mock ? "DỮ LIỆU GIẢ LẬP — không phải nhận định AI thật | " : ""}${sessionBadge} | Báo cáo: ${fresh ? "Còn hạn" : "Đã hết hạn"} | Sàn: ${(report.exchange || "").toUpperCase()} | Chế độ AI: ${cheDoHienThi} | Cập nhật lúc: ${new Date(report.generated_at).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"})} (VN) | Lỗi nguồn dữ liệu: ${report.errors.length}. Lưu ý: Điểm số và độ tự tin không phải cam kết xác suất sinh lời.`;

    const tbody = document.getElementById("researchRows");
    tbody.replaceChildren();
    for (const row of report.candidates) {
        const tr = document.createElement("tr");
        const opinions = Object.entries(row.ai_votes || {}).map(([provider, vote]) => {
            const label = provider === "openai" ? "ChatGPT" : provider === "gemini" ? "Gemini" : provider;
            const icon = vote.action === "consider" ? "🟢 NÊN XEM XÉT MUA" : vote.action === "avoid" ? "🔴 TRÁNH GIAO DỊCH" : "🟡 CHỜ ĐỢI THÊM";
            return `[${label}: ${icon} (Độ tự tin ${(Number(vote.confidence) * 100).toFixed(0)}%)] ${vote.reason}`;
        }).join(" | ");
        const regimeVi = dichTrangThaiThiTruong(row.regime);
        const rsiText = row.rsi_14 !== undefined ? `RSI: ${Number(row.rsi_14).toFixed(1)} (${regimeVi})` : regimeVi;
        const values = [
            row.pair,
            `${Number(row.score).toFixed(1)} / 100`,
            rsiText,
            `${(Number(row.spread) * 100).toFixed(3)}%`,
            `${(Number(row.hour_change) * 100).toFixed(2)}%`,
            report.is_mock ? "Dữ liệu giả lập để thử giao diện" : fresh && row.eligible === true ? "Qua bộ lọc; chờ lịch, tín hiệu & kiểm duyệt rủi ro" : "Không đủ điều kiện / báo cáo hết hạn",
            [opinions, (row.reasons || []).join("; ")].filter(Boolean).join(" | ") || "Chưa có nhận định từ AI"
        ];
        for (const value of values) {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    }
}

async function taiBaoCaoNghienCuu(event) {
    const file = event.target.files[0];
    if (!file) return;
    try {
        if (file.size > 1000000) throw new Error("Tệp vượt quá dung lượng cho phép (tối đa 1 MB)");
        const report = JSON.parse(await file.text());
        if (report.schema_version !== 1 || !Array.isArray(report.candidates) || report.candidates.length > 200
            || !Array.isArray(report.errors) || !Number.isFinite(Date.parse(report.generated_at))
            || !Number.isFinite(Date.parse(report.expires_at))) throw new Error("Cấu trúc tệp JSON không đúng định dạng báo cáo nghiên cứu");
        researchSnapshot = report;
        hienThiNghienCuu();
    } catch (error) {
        researchSnapshot = null;
        document.getElementById("researchRows").replaceChildren();
        document.getElementById("researchStatus").textContent = `Không đọc được báo cáo: ${error.message}`;
    }
}

// 4. Tạm dừng mua thêm lệnh mới (/api/v1/stopbuy)
async function tamDungMuaMoi() {
    if (!jwtToken) return alert("Vui lòng nhấn 'Kết Nối & Đăng Nhập' trước khi điều khiển Bot!");
    const res = await fetch(`${layBotUrl()}/stopbuy`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${jwtToken}` }
    });
    const data = await res.json();
    alert("⏸️ " + (data.status || "Đã bật chế độ Tạm dừng mua mới!"));
    await capNhatToanBoBangDieuKhien();
}

// 5. Khởi động lại chế độ mua bán (/api/v1/reload_config)
async function khoiDongLaiMua() {
    if (!jwtToken) return alert("Vui lòng nhấn 'Kết Nối & Đăng Nhập' trước khi điều khiển Bot!");
    const res = await fetch(`${layBotUrl()}/reload_config`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${jwtToken}` }
    });
    const data = await res.json();
    alert("▶️ " + (data.status || "Đã bật lại chế độ mua bán bình thường!"));
    await capNhatToanBoBangDieuKhien();
}

// 6. Nút bấm Bán khẩn cấp toàn bộ danh mục (/api/v1/forceexit)
async function banKhanCapToanBo() {
    if (!jwtToken) return alert("Vui lòng nhấn 'Kết Nối & Đăng Nhập' trước khi điều khiển Bot!");
    if (!confirm("🚨 XÁC NHẬN BÁN KHẨN CẤP TOÀN BỘ:\nBạn có chắc chắn muốn đóng TOÀN BỘ các lệnh đang mở theo giá thị trường (Market) và thu hồi toàn bộ vốn về USDT ngay lập tức không?")) {
        return;
    }
    const res = await fetch(`${layBotUrl()}/forceexit`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${jwtToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ tradeid: "all", ordertype: "market" })
    });
    const data = await res.json();
    alert("🚨 " + (data.status || "Đã gửi lệnh bán khẩn cấp toàn bộ danh mục!"));
    await capNhatToanBoBangDieuKhien();
}

// 7. Đóng riêng 1 lệnh cụ thể
async function dongMotLenh(tradeId, pair) {
    if (!jwtToken) return;
    if (!confirm(`⚠️ XÁC NHẬN ĐÓNG LỆNH:\nBạn có chắc chắn muốn bán đóng lệnh #${tradeId} (${pair}) theo giá thị trường ngay lập tức không?`)) {
        return;
    }
    const res = await fetch(`${layBotUrl()}/forceexit`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${jwtToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ tradeid: String(tradeId), ordertype: "market" })
    });
    const data = await res.json();
    alert(data.status || `Đã đóng lệnh #${tradeId} (${pair})`);
    await capNhatToanBoBangDieuKhien();
}

// 8. Thử nghiệm bật/tắt khóa rủi ro (trên Mock Server)
async function thuNghiemKhoaRuiRo() {
    if (!jwtToken) return alert("Vui lòng nhấn 'Kết Nối & Đăng Nhập' trước!");
    await fetch(`${layBotUrl()}/mock/toggle_lock`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${jwtToken}` }
    });
    await capNhatToanBoBangDieuKhien();
}

window.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("researchFile");
    if (fileInput) {
        fileInput.addEventListener("change", taiBaoCaoNghienCuu);
    }
});

setInterval(hienThiNghienCuu, 30000);
