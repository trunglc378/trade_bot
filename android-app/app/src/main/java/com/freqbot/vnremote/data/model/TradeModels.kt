package com.freqbot.vnremote.data.model

import com.google.gson.annotations.SerializedName

/**
 * 1. Kết quả trả về khi đăng nhập (/api/v1/token/login)
 */
data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String? = null
)

/**
 * 2. Tổng quan lợi nhuận (/api/v1/profit)
 */
data class ProfitSummary(
    @SerializedName("profit_all_coin") val tongLaiUsdt: Double = 0.0,
    @SerializedName("profit_all_percent") val phanTramLaiTong: Double = 0.0,
    @SerializedName("profit_closed_coin") val laiDaChotUsdt: Double = 0.0,
    @SerializedName("trade_count") val tongSoLenh: Int = 0,
    @SerializedName("winning_trades") val soLenhThang: Int = 0,
    @SerializedName("losing_trades") val soLenhThua: Int = 0,
    @SerializedName("max_drawdown") val sutGiamToiDa: Double = 0.0
)

/**
 * 3. Số dư tài khoản (/api/v1/balance)
 */
data class BalanceResponse(
    @SerializedName("currencies") val danhSachTienTe: List<CoinBalance> = emptyList(),
    @SerializedName("total") val tongTaiSanUsdt: Double = 0.0,
    @SerializedName("free") val vonRanhUsdt: Double = 0.0,
    @SerializedName("used") val vonDangKetUsdt: Double = 0.0,
    @SerializedName("symbol") val kyHieuTienTe: String = "USDT"
)

data class CoinBalance(
    @SerializedName("currency") val tenCoin: String = "USDT",
    @SerializedName("free") val soDuRanh: Double = 0.0,
    @SerializedName("used") val soDuDangDung: Double = 0.0,
    @SerializedName("balance") val tongSoDu: Double = 0.0
)

/**
 * 4. Chi tiết từng lệnh đang mở (/api/v1/status)
 */
data class OpenTrade(
    @SerializedName("trade_id") val maLenh: Int,
    @SerializedName("pair") val capCoin: String,
    @SerializedName("stake_amount") val vonVaoLenh: Double,
    @SerializedName("open_rate") val giaMua: Double,
    @SerializedName("current_rate") val giaHienTai: Double,
    @SerializedName("profit_ratio") val tyLeLaiLo: Double,      // Ví dụ: 0.025 = +2.5%
    @SerializedName("profit_abs") val laiLoUsdt: Double,        // Lãi/lỗ tính bằng USDT
    @SerializedName("stop_loss_abs") val giaCatLo: Double,      // Mốc giá Stop-Loss cứng
    @SerializedName("stoploss_current_dist_ratio") val khoangCachCatLo: Double = 0.0,
    @SerializedName("open_date") val thoiGianMo: String = "",
    @SerializedName("enter_tag") val lyDoMua: String? = null
)

/**
 * 5. Trạng thái Giáp bảo vệ rủi ro (/api/v1/locks)
 */
data class ProtectionLocksResponse(
    @SerializedName("lock_count") val soKhoaDangBat: Int = 0,
    @SerializedName("locks") val danhSachKhoa: List<LockDetail> = emptyList()
)

data class LockDetail(
    @SerializedName("pair") val capBiKhoa: String,              // "*" nghĩa là khóa toàn bộ Bot
    @SerializedName("reason") val lyDoKhoa: String,             // Ví dụ: MaxDrawdown, StoplossGuard
    @SerializedName("lock_end_time") val thoiGianMoKhoa: String
)

/**
 * 6. Yêu cầu đóng lệnh khẩn cấp (/api/v1/forceexit)
 */
data class ForceExitRequest(
    @SerializedName("tradeid") val tradeId: String = "all",     // "all" hoặc ID lệnh cụ thể
    @SerializedName("ordertype") val orderType: String = "market"
)

data class StatusMsgResponse(
    @SerializedName("status") val trangThai: String
)

/**
 * 7. Cấu hình kết nối máy chủ lưu trong SharedPreferences
 */
data class ServerConfig(
    val serverUrl: String,
    val username: String,
    val password: String
)
