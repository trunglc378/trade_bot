package com.freqbot.vnremote.ui

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.freqbot.vnremote.R
import com.freqbot.vnremote.data.model.OpenTrade
import java.util.Locale

/**
 * RecyclerView Adapter hiển thị danh sách các lệnh đang mở 100% bằng Tiếng Việt
 * kèm nút "Đóng lệnh này" (Force Exit từng lệnh đơn lẻ).
 */
class OpenTradeAdapter(
    private val onForceExitSingleTrade: (OpenTrade) -> Unit
) : RecyclerView.Adapter<OpenTradeAdapter.TradeViewHolder>() {

    private val danhSachLenh = mutableListOf<OpenTrade>()

    fun capNhatDuLieu(dsMoi: List<OpenTrade>) {
        danhSachLenh.clear()
        danhSachLenh.addAll(dsMoi)
        notifyDataSetChanged()
    }

    private fun dichTinHieuMua(tag: String?): String {
        val raw = tag?.trim().orEmpty()
        return when (raw) {
            "XU_HUONG_TANG_EMA_RSI" -> "Xu hướng tăng (EMA 20/50/200 + RSI)"
            "BAT_NHIP_HOI_BOLLINGER_RSI" -> "Bắt nhịp hồi quá bán (Bollinger + RSI)"
            "TIN_HIEU_CHINH", "" -> "Tín hiệu kỹ thuật chính"
            else -> raw
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TradeViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_open_trade, parent, false)
        return TradeViewHolder(view)
    }

    override fun onBindViewHolder(holder: TradeViewHolder, position: Int) {
        holder.bind(danhSachLenh[position])
    }

    override fun getItemCount(): Int = danhSachLenh.size

    inner class TradeViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvCapCoinVaMa: TextView = itemView.findViewById(R.id.tvCapCoinVaMa)
        private val tvBadgeLaiLo: TextView = itemView.findViewById(R.id.tvBadgeLaiLo)
        private val tvChiTietGia: TextView = itemView.findViewById(R.id.tvChiTietGia)
        private val tvMocCatLoVaTag: TextView = itemView.findViewById(R.id.tvMocCatLoVaTag)
        private val btnDongLenhDon: Button = itemView.findViewById(R.id.btnDongLenhDon)

        fun bind(lenh: OpenTrade) {
            tvCapCoinVaMa.text = String.format(
                Locale.US,
                "[#%d] %s  •  Vốn: %.1f USDT",
                lenh.maLenh,
                lenh.capCoin,
                lenh.vonVaoLenh
            )

            val dangLai = lenh.laiLoUsdt >= 0
            val nhanLaiLo = if (dangLai) "🟢 ĐANG LÃI" else "🔴 ĐANG LỖ"
            tvBadgeLaiLo.text = String.format(
                Locale.US,
                "%s: %+.2f%% (%+.2f USDT)",
                nhanLaiLo,
                lenh.tyLeLaiLo * 100,
                lenh.laiLoUsdt
            )
            tvBadgeLaiLo.setTextColor(
                if (dangLai) Color.parseColor("#10B981") else Color.parseColor("#EF4444")
            )

            tvChiTietGia.text = String.format(
                Locale.US,
                "• Giá mua vào: %.4f USDT  |  Giá hiện tại: %.4f USDT",
                lenh.giaMua,
                lenh.giaHienTai
            )

            val tagHienThi = dichTinHieuMua(lenh.lyDoMua)
            tvMocCatLoVaTag.text = String.format(
                Locale.US,
                "• Mốc cắt lỗ cứng (Stop-Loss): %.4f USDT (Cách giá hiện tại: %+.2f%%)\n• Lý do mua: %s\n• Thời điểm mở lệnh: %s",
                lenh.giaCatLo,
                lenh.khoangCachCatLo * 100,
                tagHienThi,
                lenh.thoiGianMo
            )

            btnDongLenhDon.setOnClickListener {
                onForceExitSingleTrade(lenh)
            }
        }
    }
}
