/**
 * Logic Điều Khiển Giao Diện Web Tiếng Việt Kết Nối Trực Tiếp Freqtrade REST API & Cố Vấn Đa Nguồn AI
 * Dự án: FreqBot VN Remote v2.0
 */

let jwtToken = "";
let timerId = null;
let researchSnapshot = null;

function layBotUrl() {
    return document.getElementById("botUrl").value.trim().replace(/\/+$/, "");
}

function dichLyDoKhoa(reason) {
    if (!reason) return "Không rõ";
    const r = reason.toLowerCase();
    if (r.includes("maxdrawdown")) return "Sụt giảm trên lịch sử lệnh đóng (MaxDrawdown)";
    if (r.includes("stoplossguard")) return "Dính chuỗi lệnh cắt lỗ liên tiếp (StoplossGuard)";
    if (r.includes("cooldown")) return "Đang nghỉ ngơi sau khi đóng lệnh (CooldownPeriod)";
    if (r.includes("lowprofit")) return "Cách ly cặp coin hiệu suất kém (LowProfitPairs)";
    return reason;
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
            throw new Error(`Đăng nhập thất bại (HTTP ${res.status})`);
        }

        const data = await res.json();
        jwtToken = data.access_token;
        connBadge.textContent = "🟢 Đã kết nối Bot (Đang đồng bộ 5s/lần)";

        await capNhatToanBoBangDieuKhien();
        await dongBoNghienCuuTuServer();
        if (timerId) clearInterval(timerId);
        timerId = setInterval(capNhatToanBoBangDieuKhien, 5000);
    } catch (err) {
        connBadge.textContent = "🔴 Lỗi kết nối";
        alert("Không thể kết nối hoặc đăng nhập vào máy chủ Freqtrade:\n" + err.message);
    }
}

// 2. Lấy toàn bộ số liệu Lợi nhuận, Số dư, Lệnh đang mở & Giáp bảo vệ rủi ro
async function capNhatToanBoBangDieuKhien() {
    if (!jwtToken) return;
    const botUrl = layBotUrl();
    const headers = { "Authorization": `Bearer ${jwtToken}` };

    try {
        const [profitRes, balanceRes, statusRes, locksRes] = await Promise.all([
            fetch(`${botUrl}/profit`, { headers }),
            fetch(`${botUrl}/balance`, { headers }),
            fetch(`${botUrl}/status`, { headers }),
            fetch(`${botUrl}/locks`, { headers })
        ]);
        if ([profitRes, balanceRes, statusRes, locksRes].some(r => !r.ok)) {
            throw new Error("Không tải được dữ liệu xác thực từ bot");
        }

        const loiNhuan = await profitRes.json();
        const soDu = await balanceRes.json();
        const danhSachLenh = await statusRes.json();
        const khoaRuiRo = await locksRes.json();

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
            `Thắng/Thua: ${win}/${loss} (Tỷ lệ thắng: ${winRate}%) | Sụt giảm tối đa: ${maxDd}%`;

        // Cập nhật thẻ Số dư
        document.getElementById("tongTaiSanUsdt").textContent = `${Number(soDu.total || 0).toFixed(2)} USDT`;
        document.getElementById("chiTietSoDu").textContent =
            `Vốn rảnh: ${Number(soDu.free || 0).toFixed(2)} USDT | Vốn trong lệnh: ${Number(soDu.used || 0).toFixed(2)} USDT`;

        // Cập nhật trạng thái Giáp bảo vệ rủi ro
        const riskBanner = document.getElementById("riskBanner");
        if (khoaRuiRo.lock_count > 0) {
            riskBanner.className = "card risk-banner danger";
            const chiTiet = khoaRuiRo.locks.map(l =>
                `⚠️ Khóa [${l.pair === "*" ? "TOÀN BỘ BOT" : l.pair}] do: ${dichLyDoKhoa(l.reason)} (Mở khóa lúc: ${l.lock_end_time})`
            ).join("<br>");
            riskBanner.innerHTML = `🛡️ <strong>CẢNH BÁO RỦI RO ĐANG KÍCH HOẠT:</strong><br>${chiTiet}`;
        } else {
            riskBanner.className = "card risk-banner";
            riskBanner.textContent = "🟢 Không có khóa mua mới đang hoạt động. MaxDrawdown xét lệnh đã đóng, kết hợp Hard Stop-Loss (-3%) trên sàn cho lệnh đang mở.";
        }

        // Cập nhật bảng Lệnh đang mở
        const tbody = document.getElementById("bangLenhDangMo");
        if (!Array.isArray(danhSachLenh) || danhSachLenh.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="empty-row">Hiện không có lệnh nào đang mở.</td></tr>`;
        } else {
            tbody.innerHTML = danhSachLenh.map(lenh => {
                const pnlPct = (Number(lenh.profit_ratio || 0) * 100).toFixed(2);
                const pnlUsdt = Number(lenh.profit_abs || 0).toFixed(2);
                const dangLai = Number(lenh.profit_abs || 0) >= 0;
                const slDist = (Number(lenh.stoploss_current_dist_ratio || 0) * 100).toFixed(2);
                return `
                    <tr>
                        <td><strong>#${lenh.trade_id}</strong></td>
                        <td><strong>${lenh.pair}</strong></td>
                        <td>${Number(lenh.stake_amount).toFixed(2)} USDT</td>
                        <td>${Number(lenh.open_rate).toFixed(4)}</td>
                        <td>${Number(lenh.current_rate).toFixed(4)}</td>
                        <td class="${dangLai ? 'text-green' : 'text-red'}">
                            <strong>${dangLai ? '🟢 +' : '🔴 '}${pnlPct}% (${dangLai ? '+' : ''}${pnlUsdt} USDT)</strong>
                        </td>
                        <td>${Number(lenh.stop_loss_abs).toFixed(4)} (${slDist}%)</td>
                        <td>${lenh.enter_tag || 'TIN_HIEU_CHINH'}</td>
                        <td>
                            <button class="btn btn-sm-danger" onclick="dongMotLenh('${lenh.trade_id}', '${lenh.pair}')">
                                Đóng lệnh
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
            if (res.status === 404) document.getElementById("researchStatus").textContent = "Máy chủ không cung cấp báo cáo AI; hãy chọn tệp latest.json. Endpoint đồng bộ chỉ có trên mock.";
            return;
        }
        const report = await res.json();
        if (report && report.schema_version === 1 && Array.isArray(report.candidates)) {
            researchSnapshot = report;
            hienThiNghienCuu();
        }
    } catch (err) {
        // Nếu kết nối trực tiếp Freqtrade container chưa mở endpoint /vn_research thì dùng nút tải file latest.json
    }
}

function trangThaiPhien(report, now = new Date()) {
    if (typeof report.schedule_enabled !== "boolean") return "Chưa có lịch trong báo cáo";
    if (!report.schedule_enabled) return "Lịch mua 24/7";
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
    return `${opened ? "Trong" : "Ngoài"} khung mua (${labels} VN); vẫn canh thoát 24/7`;
}

function hienThiNghienCuu() {
    if (!researchSnapshot) return;
    const report = researchSnapshot;
    const fresh = Date.parse(report.generated_at) <= Date.now() && Date.now() < Date.parse(report.expires_at);
    const status = document.getElementById("researchStatus");
    const sessionBadge = trangThaiPhien(report);
    status.textContent = `${report.is_mock ? "DỮ LIỆU GIẢ LẬP — không phải nhận định AI thật | " : ""}${sessionBadge} | Báo cáo: ${fresh ? "Còn hạn" : "Hết hạn"} | Sàn: ${(report.exchange || "").toUpperCase()} | Chế độ AI: ${report.mode} | Cập nhật: ${new Date(report.generated_at).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"})} (VN) | Lỗi nguồn: ${report.errors.length}. Điểm/confidence không phải xác suất sinh lời.`;

    const tbody = document.getElementById("researchRows");
    tbody.replaceChildren();
    for (const row of report.candidates) {
        const tr = document.createElement("tr");
        const opinions = Object.entries(row.ai_votes || {}).map(([provider, vote]) => {
            const label = provider === "openai" ? "ChatGPT" : provider === "gemini" ? "Gemini" : provider;
            const icon = vote.action === "consider" ? "🟢 NÊN XEM XÉT MUA" : vote.action === "avoid" ? "🔴 TRÁNH GIAO DỊCH" : "🟡 CHỜ ĐỢI";
            return `[${label}: ${icon} (${(Number(vote.confidence) * 100).toFixed(0)}%)] ${vote.reason}`;
        }).join(" | ");
        const rsiText = row.rsi_14 !== undefined ? `RSI: ${Number(row.rsi_14).toFixed(1)} (${row.regime || "N/A"})` : (row.regime || "N/A");
        const values = [
            row.pair,
            `${Number(row.score).toFixed(1)} / 100`,
            rsiText,
            `${(Number(row.spread) * 100).toFixed(3)}%`,
            `${(Number(row.hour_change) * 100).toFixed(2)}%`,
            report.is_mock ? "Giả lập để thử giao diện" : fresh && row.eligible === true ? "Qua bộ lọc; chờ lịch, tín hiệu & rủi ro" : "Không đủ điều kiện / hết hạn",
            [opinions, (row.reasons || []).join("; ")].filter(Boolean).join(" | ") || "Chưa có nhận định AI"
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
        if (file.size > 1000000) throw new Error("Tệp quá lớn (tối đa 1 MB)");
        const report = JSON.parse(await file.text());
        if (report.schema_version !== 1 || !Array.isArray(report.candidates) || report.candidates.length > 200
            || !Array.isArray(report.errors) || !Number.isFinite(Date.parse(report.generated_at))
            || !Number.isFinite(Date.parse(report.expires_at))) throw new Error("Sai định dạng báo cáo");
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
    if (!jwtToken) return alert("Vui lòng Kết nối & Đăng nhập trước!");
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
    if (!jwtToken) return alert("Vui lòng Kết nối & Đăng nhập trước!");
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
    if (!jwtToken) return alert("Vui lòng Kết nối & Đăng nhập trước!");
    if (!confirm("🚨 CẢNH BÁO: Bạn có chắc chắn muốn BÁN KHẨN CẤP toàn bộ các lệnh đang mở theo giá thị trường (Market) và thu hồi về USDT ngay lập tức?")) {
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
    if (!confirm(`Bạn có chắc chắn muốn bán đóng lệnh #${tradeId} (${pair}) theo giá thị trường ngay lập tức?`)) {
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
    alert(data.status || `Đã đóng lệnh #${tradeId}`);
    await capNhatToanBoBangDieuKhien();
}

// 8. Thử nghiệm bật/tắt khóa rủi ro (trên Mock Server)
async function thuNghiemKhoaRuiRo() {
    if (!jwtToken) return alert("Vui lòng Kết nối & Đăng nhập trước!");
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
