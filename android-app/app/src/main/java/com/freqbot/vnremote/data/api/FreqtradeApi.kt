package com.freqbot.vnremote.data.api

import com.freqbot.vnremote.data.model.*
import retrofit2.http.*

/**
 * Interface Retrofit định nghĩa toàn bộ các lệnh gọi điều khiển Freqtrade REST API & Cố vấn AI
 */
interface FreqtradeApi {

    // 1. Đăng nhập bằng Basic Auth để lấy JWT Access Token
    @POST("api/v1/token/login")
    suspend fun dangNhap(
        @Header("Authorization") basicAuth: String
    ): TokenResponse

    // 2. Lấy thống kê tổng quan lợi nhuận
    @GET("api/v1/profit")
    suspend fun layThongKeLoiNhuan(): ProfitSummary

    // 3. Lấy số dư tài khoản (Tổng tài sản, Vốn rảnh, Vốn đang trong lệnh)
    @GET("api/v1/balance")
    suspend fun laySoDuTaiKhoan(): BalanceResponse

    // 4. Lấy danh sách các lệnh đang mở theo thời gian thực
    @GET("api/v1/status")
    suspend fun layDanhSachLenhDangMo(): List<OpenTrade>

    // 5. Kiểm tra xem Bot có đang bị khóa do chạm ngưỡng rủi ro (Protections) không
    @GET("api/v1/locks")
    suspend fun kiemTraKhoaRuiRo(): ProtectionLocksResponse

    // 6. Lấy thông tin cấu hình trạng thái vận hành hiện tại của Bot
    @GET("api/v1/show_config")
    suspend fun layCauHinhBot(): BotConfigResponse

    // 7. Lấy báo cáo Phân tích Thị trường, Khung giờ & Đề xuất Coin từ AI (ChatGPT + Gemini)
    @GET("api/v1/vn_research")
    suspend fun layBaoCaoNghienCuuAi(): VnResearchReport

    // 8. Tạm dừng mua thêm lệnh mới (chỉ canh chốt lời/cắt lỗ lệnh cũ)
    @POST("api/v1/stopbuy")
    suspend fun tamDungMuaMoi(): StatusMsgResponse

    // 9. Khởi động lại chế độ mua bán bình thường
    @POST("api/v1/reload_config")
    suspend fun khoiDongLaiBot(): StatusMsgResponse

    // 10. BÁN KHẨN CẤP (Đóng 1 lệnh hoặc toàn bộ lệnh ngay lập tức theo giá thị trường)
    @POST("api/v1/forceexit")
    suspend fun banKhanCap(
        @Body request: ForceExitRequest
    ): StatusMsgResponse
}
