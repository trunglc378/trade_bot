package com.freqbot.vnremote.worker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.freqbot.vnremote.data.api.RetrofitClient
import java.util.Locale

/**
 * WorkManager CoroutineWorker chạy ngầm định kỳ mỗi 15 phút:
 * - Tự động kiểm tra trạng thái các lệnh đang mở và trạng thái khóa rủi ro (Protections).
 * - Nếu có lệnh đang lỗ vượt ngưỡng -3% hoặc Bot vừa kích hoạt giáp bảo vệ, hoặc mất kết nối VPS,
 *   lập tức đẩy thông báo Tiếng Việt lên màn hình khóa điện thoại.
 */
class RiskMonitorWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        private const val CHANNEL_ID = "freqbot_vn_risk_alerts"
        private const val CHANNEL_NAME = "Cảnh Báo Rủi Ro Giao Dịch"
    }

    override suspend fun doWork(): Result {
        val config = RetrofitClient.docCauHinh(applicationContext)
        return try {
            val api = RetrofitClient.getApi(config.serverUrl)
            val basicAuth = RetrofitClient.taoChuoiBasicAuth(config.username, config.password)
            RetrofitClient.jwtToken = api.dangNhap(basicAuth).accessToken

            val dsLenh = api.layDanhSachLenhDangMo()
            val khoaRuiRo = api.kiemTraKhoaRuiRo()

            // Kiểm tra nếu có lệnh nào đang lỗ quá -3% (-0.03)
            val lenhLoSau = dsLenh.filter { it.tyLeLaiLo <= -0.03 }

            if (lenhLoSau.isNotEmpty() || khoaRuiRo.soKhoaDangBat > 0) {
                val chiTietCanhBao = buildString {
                    if (lenhLoSau.isNotEmpty()) {
                        val dsCap = lenhLoSau.joinToString(", ") {
                            String.format(Locale.US, "%s (%.2f%%)", it.capCoin, it.tyLeLaiLo * 100)
                        }
                        append("⚠️ Lệnh đang lỗ sâu: $dsCap. ")
                    }
                    if (khoaRuiRo.soKhoaDangBat > 0) {
                        val lyDo = khoaRuiRo.danhSachKhoa.joinToString(", ") { it.lyDoKhoa }
                        append("🛡️ Giáp bảo vệ đang bật: $lyDo.")
                    }
                }
                phatThongBaoTiengViet(
                    tieuDe = "🚨 Cảnh Báo Rủi Ro FreqBot VN",
                    noiDung = chiTietCanhBao,
                    notificationId = 1001
                )
            }
            Result.success()
        } catch (e: Exception) {
            phatThongBaoTiengViet(
                tieuDe = "⚠️ Mất Kết Nối Máy Chủ Bot",
                noiDung = "Không thể kết nối tới VPS (${config.serverUrl}). Vui lòng kiểm tra mạng hoặc trạng thái Bot!",
                notificationId = 1002
            )
            Result.retry()
        }
    }

    private fun phatThongBaoTiengViet(tieuDe: String, noiDung: String, notificationId: Int) {
        val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Thông báo khẩn cấp khi lệnh chạm ngưỡng lỗ hoặc kích hoạt khóa rủi ro"
            }
            manager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(tieuDe)
            .setContentText(noiDung)
            .setStyle(NotificationCompat.BigTextStyle().bigText(noiDung))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        manager.notify(notificationId, notification)
    }
}
