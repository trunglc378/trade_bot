/**
 * Logic Điều Khiển Giao Diện Web Tiếng Việt Kết Nối Trực Tiếp Freqtrade REST API
 * Dự án: FreqBot VN Remote
 */

let jwtToken = "";
let timerId = null;

function layBotUrl() {
    return document.getElementById("botUrl").value.trim().replace(/\/+$/, "");
}

function dichLyDoKhoa(reason) {
    if (!reason) return "Không rõ";
    const r = reason.toLowerCase();
    if (r.includes("maxdrawdown")) return "Chạm hạn mức lỗ tối đa trong ngày (MaxDrawdown)";
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
            riskBanner.innerHTML = `🟢 <strong>TRẠNG THÁI AN TOÀN:</strong> Chưa chạm ngưỡng cắt lỗ ngày. Bộ giáp bảo vệ (MaxDrawdown, StoplossGuard) đang trực chiến.`;
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

// 3. Tạm dừng mua thêm lệnh mới (/api/v1/stopbuy)
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

// 4. Khởi động lại chế độ mua bán (/api/v1/reload_config)
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

// 5. Nút bấm Bán khẩn cấp toàn bộ danh mục (/api/v1/forceexit)
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

// 6. Đóng riêng 1 lệnh cụ thể
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

// 7. Thử nghiệm bật/tắt khóa rủi ro (trên Mock Server)
async function thuNghiemKhoaRuiRo() {
    if (!jwtToken) return alert("Vui lòng Kết nối & Đăng nhập trước!");
    await fetch(`${layBotUrl()}/mock/toggle_lock`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${jwtToken}` }
    });
    await capNhatToanBoBangDieuKhien();
}

window.addEventListener("DOMContentLoaded", () => {
    ketNoiVaDangNhap();
});
