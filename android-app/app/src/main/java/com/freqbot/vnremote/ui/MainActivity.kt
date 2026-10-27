package com.freqbot.vnremote.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.freqbot.vnremote.R
import com.freqbot.vnremote.data.api.FreqtradeApi
import com.freqbot.vnremote.data.api.RetrofitClient
import com.freqbot.vnremote.data.model.ForceExitRequest
import com.freqbot.vnremote.data.model.OpenTrade
import com.freqbot.vnremote.worker.RiskMonitorWorker
import kotlinx.coroutines.Job
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.Locale
import java.time.Instant
import java.time.OffsetDateTime
import java.util.concurrent.TimeUnit

/**
 * Màn hình điều khiển chính 100% Tiếng Việt của ứng dụng FreqBot VN Remote:
 * - Hiển thị Tổng quan Lợi nhuận, Số dư USDT, Trạng thái Giáp bảo vệ rủi ro (Protections).
 * - Hiển thị Trạng thái Khung giờ giao dịch vàng (03:00-04:00 VN) & Đề xuất Coin từ AI (ChatGPT + Gemini).
 * - Danh sách RecyclerView các lệnh đang mở theo thời gian thực (tự động cập nhật mỗi 5 giây).
 * - Nút "Tạm dừng Mua mới", Nút "Bật lại Mua", và Nút đỏ "BÁN KHẨN CẤP TOÀN BỘ (PANIC SELL)".
 */
class MainActivity : AppCompatActivity() {

    private lateinit var tvDiaChiMayChu: TextView
    private lateinit var tvTongQuan: TextView
    private lateinit var tvSoDuTaiKhoan: TextView
    private lateinit var tvTrangThaiRuiRo: TextView
    private lateinit var tvCoVanAi: TextView
    private lateinit var tvTrongDanhSach: TextView
    private lateinit var rvDanhSachLenh: RecyclerView
    private lateinit var btnCauHinhMayChu: Button
    private lateinit var btnTamDungMua: Button
    private lateinit var btnBatLaiMua: Button
    private lateinit var btnBanKhanCap: Button

    private lateinit var openTradeAdapter: OpenTradeAdapter
    private var pollingJob: Job? = null

    private val api: FreqtradeApi
        get() {
            val config = RetrofitClient.docCauHinh(this)
            return RetrofitClient.getApi(config.serverUrl)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        anhXaGiaoDien()
        thietLapRecyclerView()
        thietLapSuKienNutBam()

        // 1. Kích hoạt WorkManager giám sát rủi ro chạy ngầm mỗi 15 phút
        kichHoatGiamSatRuiRoNgam()

        // 2. Kết nối máy chủ Bot và bắt đầu vòng lặp cập nhật mỗi 5 giây
        khoiDongKetNoiVaCapNhat()
    }

    private fun anhXaGiaoDien() {
        tvDiaChiMayChu = findViewById(R.id.tvDiaChiMayChu)
        tvTongQuan = findViewById(R.id.tvTongQuan)
        tvSoDuTaiKhoan = findViewById(R.id.tvSoDuTaiKhoan)
        tvTrangThaiRuiRo = findViewById(R.id.tvTrangThaiRuiRo)
        tvCoVanAi = findViewById(R.id.tvCoVanAi)
        tvTrongDanhSach = findViewById(R.id.tvTrongDanhSach)
        rvDanhSachLenh = findViewById(R.id.rvDanhSachLenh)
        btnCauHinhMayChu = findViewById(R.id.btnCauHinhMayChu)
        btnTamDungMua = findViewById(R.id.btnTamDungMua)
        btnBatLaiMua = findViewById(R.id.btnBatLaiMua)
        btnBanKhanCap = findViewById(R.id.btnBanKhanCap)
    }

    private fun thietLapRecyclerView() {
        openTradeAdapter = OpenTradeAdapter { lenhCanDong ->
            hienThiHopThoaiDongMotLenh(lenhCanDong)
        }
        rvDanhSachLenh.layoutManager = LinearLayoutManager(this)
        rvDanhSachLenh.adapter = openTradeAdapter
    }

    private fun thietLapSuKienNutBam() {
        btnCauHinhMayChu.setOnClickListener {
            hienThiHopThoaiCauHinhMayChu()
        }

        btnTamDungMua.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val res = api.tamDungMuaMoi()
                    Toast.makeText(
                        this@MainActivity,
                        "⏸️ Đã bật chế độ: NGỪNG MUA MỚI (${res.trangThai})",
                        Toast.LENGTH_LONG
                    ).show()
                    taiDuLieuBangDieuKhien()
                } catch (e: Exception) {
                    thongBaoLoi("Không thể gửi lệnh tạm dừng mua: ${e.message}")
                }
            }
        }

        btnBatLaiMua.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val res = api.khoiDongLaiBot()
                    Toast.makeText(
                        this@MainActivity,
                        "▶️ Đã bật lại chế độ MUA BÁN BÌNH THƯỜNG (${res.trangThai})",
                        Toast.LENGTH_LONG
                    ).show()
                    taiDuLieuBangDieuKhien()
                } catch (e: Exception) {
                    thongBaoLoi("Không thể nạp lại cấu hình: ${e.message}")
                }
            }
        }

        btnBanKhanCap.setOnClickListener {
            hienThiHopThoaiBanKhanCap()
        }
    }

    private fun khoiDongKetNoiVaCapNhat() {
        pollingJob?.cancel()
        val config = RetrofitClient.docCauHinh(this)
        tvDiaChiMayChu.text = "🌐 Máy chủ: ${config.serverUrl} (Tài khoản: ${config.username})"

        pollingJob = lifecycleScope.launch {
            try {
                val basicAuth = RetrofitClient.taoChuoiBasicAuth(config.username, config.password)
                val tokenRes = api.dangNhap(basicAuth)
                RetrofitClient.jwtToken = tokenRes.accessToken

                while (isActive) {
                    taiDuLieuBangDieuKhien()
                    delay(5000)
                }
            } catch (e: Exception) {
                tvTrangThaiRuiRo.text =
                    "🔴 MẤT KẾT NỐI MÁY CHỦ BOT (${config.serverUrl})\n" +
                    "Chi tiết: ${e.message}\n" +
                    "Hãy nhấn nút [⚙️ Máy chủ] để kiểm tra địa chỉ IP VPS / Tailscale."
                thongBaoLoi("Lỗi kết nối máy chủ Bot: ${e.message}")
            }
        }
    }

    private suspend fun taiDuLieuBangDieuKhien() {
        try {
            val loiNhuan = api.layThongKeLoiNhuan()
            val soDu = api.laySoDuTaiKhoan()
            val lenhDangMo = api.layDanhSachLenhDangMo()
            val khoaRuiRo = api.kiemTraKhoaRuiRo()

            // 1. Hiển thị thẻ Tổng quan Lợi nhuận bằng Tiếng Việt
            val tongSoDaDong = loiNhuan.soLenhThang + loiNhuan.soLenhThua
            val winRate = if (tongSoDaDong > 0) {
                (loiNhuan.soLenhThang.toDouble() / tongSoDaDong.toDouble()) * 100.0
            } else 0.0

            tvTongQuan.text = String.format(
                Locale.US,
                "📊 TỔNG QUAN HIỆU SUẤT GIAO DỊCH\n" +
                "• Tổng lợi nhuận (cả lệnh mở): %+.2f USDT (%+.2f%%)\n" +
                "• Lợi nhuận đã chốt: %+.2f USDT\n" +
                "• Thống kê lệnh: %d Thắng / %d Thua (Tỷ lệ thắng: %.1f%%)\n" +
                "• Sụt giảm tối đa (Max Drawdown): %.2f%%",
                loiNhuan.tongLaiUsdt,
                loiNhuan.phanTramLaiTong,
                loiNhuan.laiDaChotUsdt,
                loiNhuan.soLenhThang,
                loiNhuan.soLenhThua,
                winRate,
                loiNhuan.sutGiamToiDa * 100
            )

            // 2. Hiển thị thẻ Số dư Tài khoản USDT
            tvSoDuTaiKhoan.text = String.format(
                Locale.US,
                "💼 SỐ DƯ TÀI KHOẢN (%s)\n" +
                "• Tổng tài sản: %.2f USDT\n" +
                "• Vốn rảnh (Sẵn sàng mua): %.2f USDT  |  Vốn trong lệnh: %.2f USDT",
                soDu.kyHieuTienTe,
                soDu.tongTaiSanUsdt,
                soDu.vonRanhUsdt,
                soDu.vonDangKetUsdt
            )

            // 3. Dịch trạng thái Giáp bảo vệ rủi ro sang Tiếng Việt
            if (khoaRuiRo.soKhoaDangBat > 0) {
                val chiTietKhoa = khoaRuiRo.danhSachKhoa.joinToString("\n") {
                    val phamVi = if (it.capBiKhoa == "*") "TOÀN BỘ BOT" else it.capBiKhoa
                    "⚠️ Khóa [$phamVi] do: ${dichLyDoKhoa(it.lyDoKhoa)}\n   ⏳ Mở khóa lúc: ${it.thoiGianMoKhoa}"
                }
                tvTrangThaiRuiRo.text = "🛡️ GIÁP BẢO VỆ RỦI RO ĐANG KÍCH HOẠT:\n$chiTietKhoa"
            } else {
                tvTrangThaiRuiRo.text =
                    "🟢 TRẠNG THÁI AN TOÀN: Không có khóa rủi ro nào kích hoạt. Chưa chạm hạn mức cắt lỗ ngày."
            }

            // 4. Cập nhật danh sách lệnh đang mở lên RecyclerView
            openTradeAdapter.capNhatDuLieu(lenhDangMo)
            if (lenhDangMo.isEmpty()) {
                tvTrongDanhSach.visibility = View.VISIBLE
                rvDanhSachLenh.visibility = View.GONE
                tvTrongDanhSach.text =
                    "Hiện không có lệnh nào đang mở (100% vốn đang ở trạng thái USDT an toàn)."
            } else {
                tvTrongDanhSach.visibility = View.GONE
                rvDanhSachLenh.visibility = View.VISIBLE
            }

            // 5. Đồng bộ Báo cáo Phân tích Thị trường & Đề xuất Coin từ AI (nếu máy chủ hỗ trợ)
            try {
                val baoCaoAi = api.layBaoCaoNghienCuuAi()
                val conHan = runCatching {
                    val now = Instant.now()
                    baoCaoAi.phienBan == 1 &&
                        !now.isBefore(OffsetDateTime.parse(baoCaoAi.thoiDiemTao).toInstant()) &&
                        now.isBefore(OffsetDateTime.parse(baoCaoAi.thoiDiemHetHan).toInstant())
                }.getOrDefault(false)
                val trangThaiGio = if (baoCaoAi.dangTrongKhungGioMua) {
                    "Trong khung mua cấu hình tại thời điểm lấy báo cáo"
                } else {
                    "Ngoài khung mua tại thời điểm lấy báo cáo; vẫn canh thoát 24/7"
                }
                val topCoins = baoCaoAi.danhSachCoin.take(3).joinToString("\n") { c ->
                    val bieuTuong = if (!baoCaoAi.duLieuGiaLap && conHan && c.duDieuKienMua) "✅" else "⛔"
                    val nhanDinh = c.phieuBauAi.entries.joinToString(", ") { (nguon, phieu) ->
                        "${nguon.uppercase()}: ${phieu.hanhDong} (${(phieu.doTuTin * 100).toInt()}%)"
                    }
                    String.format(
                        Locale.US,
                        "%s %s (Điểm: %.1f/100 | RSI: %.1f | %s)\n   💡 AI: %s",
                        bieuTuong,
                        c.capCoin,
                        c.diemKyThuat,
                        c.rsi14,
                        c.trangThaiThiTruong,
                        nhanDinh.ifEmpty { "Đang phân tích" }
                    )
                }
                tvCoVanAi.text =
                    "NGHIÊN CỨU AI (${baoCaoAi.sanGiaoDich.uppercase()})\n" +
                    (if (baoCaoAi.duLieuGiaLap) "DỮ LIỆU GIẢ LẬP — không phải nhận định AI thật\n" else "") +
                    (if (conHan) "Báo cáo còn hạn\n" else "Báo cáo hết hạn hoặc không hợp lệ\n") +
                    "• $trangThaiGio\n" +
                    topCoins + "\nĐiểm/confidence không phải xác suất sinh lời."
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                tvCoVanAi.text = "Chưa lấy được báo cáo nghiên cứu. Endpoint AI hiện chỉ có ở mock; Freqtrade gốc không cung cấp endpoint này."
            }
        } catch (e: Exception) {
            // Bỏ qua lỗi mạng thoáng qua trong vòng lặp 5 giây
        }
    }

    private fun dichLyDoKhoa(reason: String): String {
        return when {
            reason.contains("MaxDrawdown", true) -> "Chạm hạn mức lỗ tối đa trong ngày (MaxDrawdown)"
            reason.contains("StoplossGuard", true) -> "Dính chuỗi lệnh cắt lỗ liên tiếp (StoplossGuard)"
            reason.contains("CooldownPeriod", true) -> "Đang nghỉ ngơi sau khi đóng lệnh (CooldownPeriod)"
            reason.contains("LowProfitPairs", true) -> "Cách ly cặp coin hiệu suất kém (LowProfitPairs)"
            else -> reason
        }
    }

    private fun hienThiHopThoaiBanKhanCap() {
        AlertDialog.Builder(this)
            .setTitle("🚨 XÁC NHẬN BÁN KHẨN CẤP TOÀN BỘ")
            .setMessage(
                "CẢNH BÁO: Bạn có chắc chắn muốn đóng TOÀN BỘ các lệnh đang mở theo giá thị trường (Market) " +
                "và thu hồi toàn bộ vốn về USDT ngay lập tức không?"
            )
            .setPositiveButton("ĐỒNG Ý BÁN HẾT") { _, _ ->
                lifecycleScope.launch {
                    try {
                        val res = api.banKhanCap(ForceExitRequest(tradeId = "all", orderType = "market"))
                        Toast.makeText(
                            this@MainActivity,
                            "🚨 ${res.trangThai}",
                            Toast.LENGTH_LONG
                        ).show()
                        taiDuLieuBangDieuKhien()
                    } catch (e: Exception) {
                        thongBaoLoi("Lỗi khi thực thi bán khẩn cấp: ${e.message}")
                    }
                }
            }
            .setNegativeButton("Hủy bỏ", null)
            .show()
    }

    private fun hienThiHopThoaiDongMotLenh(lenh: OpenTrade) {
        AlertDialog.Builder(this)
            .setTitle("⚠️ Đóng Lệnh [#${lenh.maLenh}] ${lenh.capCoin}")
            .setMessage(
                String.format(
                    Locale.US,
                    "Bạn có muốn bán ngay lệnh %s (Lãi/Lỗ hiện tại: %+.2f%% / %+.2f USDT) theo giá thị trường không?",
                    lenh.capCoin,
                    lenh.tyLeLaiLo * 100,
                    lenh.laiLoUsdt
                )
            )
            .setPositiveButton("Bán Lệnh Này") { _, _ ->
                lifecycleScope.launch {
                    try {
                        val res = api.banKhanCap(
                            ForceExitRequest(
                                tradeId = lenh.maLenh.toString(),
                                orderType = "market"
                            )
                        )
                        Toast.makeText(this@MainActivity, res.trangThai, Toast.LENGTH_LONG).show()
                        taiDuLieuBangDieuKhien()
                    } catch (e: Exception) {
                        thongBaoLoi("Không thể đóng lệnh #${lenh.maLenh}: ${e.message}")
                    }
                }
            }
            .setNegativeButton("Giữ Lệnh", null)
            .show()
    }

    private fun hienThiHopThoaiCauHinhMayChu() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_server_config, null)
        val edtServerUrl = dialogView.findViewById<EditText>(R.id.edtServerUrl)
        val edtUsername = dialogView.findViewById<EditText>(R.id.edtUsername)
        val edtPassword = dialogView.findViewById<EditText>(R.id.edtPassword)

        val currentConfig = RetrofitClient.docCauHinh(this)
        edtServerUrl.setText(currentConfig.serverUrl)
        edtUsername.setText(currentConfig.username)
        edtPassword.setText(currentConfig.password)

        AlertDialog.Builder(this)
            .setTitle("⚙️ Cấu Hình Kết Nối Máy Chủ Freqtrade")
            .setView(dialogView)
            .setPositiveButton("Lưu & Kết Nối Lại") { _, _ ->
                RetrofitClient.luuCauHinh(
                    this,
                    edtServerUrl.text.toString(),
                    edtUsername.text.toString(),
                    edtPassword.text.toString()
                )
                RetrofitClient.jwtToken = null
                khoiDongKetNoiVaCapNhat()
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun kichHoatGiamSatRuiRoNgam() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val workRequest = PeriodicWorkRequestBuilder<RiskMonitorWorker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "FreqBotVnRiskMonitor",
            ExistingPeriodicWorkPolicy.KEEP,
            workRequest
        )
    }

    private fun thongBaoLoi(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }
}
