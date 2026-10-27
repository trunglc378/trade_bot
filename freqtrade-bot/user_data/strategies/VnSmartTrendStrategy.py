# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""
Chiến lược Giao dịch Định lượng Tiếng Việt: VnSmartTrendStrategy
Thuộc Dự án: Hệ thống Giao dịch Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (FreqBot VN Remote)

Tính năng cốt lõi:
1. Kết hợp Đa chỉ báo: EMA (20, 50, 200) + RSI (14) + Bollinger Bands (20, 2.0) + Bộ lọc Khối lượng (Volume SMA 20).
2. Cắt lỗ cứng (-3%) kèm Cắt lỗ trượt khóa lợi nhuận (Trailing Stop).
3. Tích hợp Bộ 4 Lớp Giáp Bảo Vệ Vốn Tự Động (Protections):
   - MaxDrawdown (Khóa toàn bộ Bot 12h nếu lỗ ngày vượt 5%)
   - StoplossGuard (Khóa toàn bộ Bot 6h nếu dính 3 lệnh cắt lỗ liên tiếp trong 6h)
   - LowProfitPairs (Cách ly cặp coin hiệu suất kém trong 6h)
   - CooldownPeriod (Nghỉ 30 phút sau khi đóng lệnh trên 1 cặp coin)
4. Luồng thông báo đẩy 100% Tiếng Việt rõ ràng khi Vào lệnh (confirm_trade_entry) và Thoát lệnh (confirm_trade_exit).
"""

from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class VnSmartTrendStrategy(IStrategy):
    """
    Chiến lược giao dịch theo xu hướng thông minh kết hợp bắt nhịp hồi quá bán,
    tích hợp đầy đủ quản trị rủi ro đa tầng và báo cáo Tiếng Việt.
    """

    INTERFACE_VERSION = 3

    # Khung thời gian giao dịch chính: 5 phút
    timeframe = "5m"

    # Chỉ chạy trên chiều Mua (Spot Long)
    can_short: bool = False

    # Bảng chốt lời tối thiểu theo thời gian giữ lệnh (Minimal ROI)
    minimal_roi = {
        "0": 0.06,     # Chốt lời ngay nếu đạt +6.0%
        "30": 0.035,   # Sau 30 phút: Chốt lời nếu đạt +3.5%
        "60": 0.02,    # Sau 60 phút: Chốt lời nếu đạt +2.0%
        "180": 0.01    # Sau 180 phút: Chốt lời nếu đạt +1.0%
    }

    # Cắt lỗ cứng tối đa -3% cho mỗi vị thế (Kết hợp stoploss_on_exchange trong config.json)
    stoploss = -0.03

    # Cấu hình Cắt lỗ trượt (Trailing Stop-Loss) để khóa lợi nhuận khi giá tăng
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01          # Giữ khoảng cách cắt lỗ trượt 1.0% dưới mức đỉnh
    trailing_stop_positive_offset = 0.025  # Bắt đầu kích hoạt trượt khi lệnh lãi từ +2.5%

    # Chỉ tính toán trên nến mới để tối ưu CPU
    process_only_new_candles = True

    # Sử dụng tín hiệu thoát lệnh từ populate_exit_trend
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Số nến lịch sử cần tải khi khởi động để tính chuẩn EMA 200
    startup_candle_count: int = 200

    # Tham số có thể tối ưu hóa bằng Hyperopt
    buy_rsi_min = IntParameter(40, 55, default=45, space="buy", optimize=True)
    buy_rsi_max = IntParameter(60, 72, default=68, space="buy", optimize=True)
    oversold_rsi = IntParameter(22, 35, default=30, space="buy", optimize=True)
    sell_rsi_overbought = IntParameter(72, 85, default=78, space="sell", optimize=True)

    @property
    def protections(self):
        """
        Bộ 4 Lớp Giáp Bảo Vệ Vốn Tự Động (Circuit Breakers)
        """
        return [
            {
                # 1. Nghỉ 6 nến 5m (30 phút) sau khi đóng lệnh trên 1 cặp coin
                "method": "CooldownPeriod",
                "stop_duration_candles": 6
            },
            {
                # 2. Hạn mức lỗ ngày tối đa: Nếu lỗ vượt 5% trong 24h (288 nến 5m) -> Khóa toàn bộ Bot 12h
                "method": "MaxDrawdown",
                "lookback_period_candles": 288,
                "trade_limit": 2,
                "stop_duration_candles": 144,
                "max_allowed_drawdown": 0.05
            },
            {
                # 3. Chống sập dây chuyền: Nếu dính 3 lệnh cắt lỗ liên tiếp trong 6h (72 nến) -> Khóa Bot 6h
                "method": "StoplossGuard",
                "lookback_period_candles": 72,
                "trade_limit": 3,
                "stop_duration_candles": 72,
                "only_per_pair": False
            },
            {
                # 4. Cách ly cặp coin yếu: Nếu 1 cặp coin có >= 2 lệnh tổng lỗ <= -3% trong 12h -> Khóa cặp đó 6h
                "method": "LowProfitPairs",
                "lookback_period_candles": 144,
                "trade_limit": 2,
                "stop_duration_candles": 72,
                "required_profit": -0.03
            }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật cần thiết (EMA, RSI, Bollinger Bands, Volume SMA)
        """
        # 1. Hệ thống đường trung bình động EMA
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # 2. Chỉ báo động lượng RSI (14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # 3. Dải Bollinger Bands (20, 2.0)
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        # 4. Khối lượng trung bình 20 phiên
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Xác định tín hiệu Mua (enter_long) và gắn nhãn lý do bằng Tiếng Việt (enter_tag)
        """
        dataframe.loc[:, "enter_tag"] = ""

        # Điều kiện Mua 1: Xu hướng tăng chuẩn (Close > EMA200, EMA20 > EMA50, RSI khỏe, Volume đột biến)
        dk_xu_huong_tang = (
            (dataframe["close"] > dataframe["ema200"])
            & (dataframe["ema20"] > dataframe["ema50"])
            & (dataframe["close"] > dataframe["ema20"])
            & (dataframe["rsi"] >= self.buy_rsi_min.value)
            & (dataframe["rsi"] <= self.buy_rsi_max.value)
            & (dataframe["volume"] > dataframe["volume_mean_20"] * 1.15)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_xu_huong_tang, ["enter_long", "enter_tag"]] = (
            1,
            "XU_HUONG_TANG_EMA_RSI",
        )

        # Điều kiện Mua 2: Bắt nhịp hồi khi quá bán chạm dải dưới Bollinger trong xu hướng lớn ổn định
        dk_hoi_qua_ban = (
            (dataframe["close"] < dataframe["bb_lowerband"] * 1.003)
            & (dataframe["rsi"] < self.oversold_rsi.value)
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["volume"] > dataframe["volume_mean_20"])
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_hoi_qua_ban, ["enter_long", "enter_tag"]] = (
            1,
            "BAT_NHIP_HOI_BOLLINGER_RSI",
        )

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Xác định tín hiệu Bán (exit_long) và gắn nhãn lý do thoát lệnh (exit_tag)
        """
        dataframe.loc[:, "exit_tag"] = ""

        # Điều kiện Bán 1: Chạm vùng quá mua mạnh trên dải Bollinger trên
        dk_qua_mua = (
            (dataframe["rsi"] > self.sell_rsi_overbought.value)
            & (dataframe["close"] >= dataframe["bb_upperband"])
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_qua_mua, ["exit_long", "exit_tag"]] = (
            1,
            "CHOT_LOI_QUA_MUA_RSI_BB",
        )

        # Điều kiện Bán 2: Gãy xu hướng ngắn hạn (EMA20 cắt xuống dưới EMA50 kèm RSI suy yếu)
        dk_gay_xu_huong = (
            qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
            & (dataframe["rsi"] < 42)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_gay_xu_huong, ["exit_long", "exit_tag"]] = (
            1,
            "GAY_XU_HUONG_EMA20_50",
        )

        return dataframe

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        Gửi báo cáo Tiếng Việt rành mạch mỗi khi Bot bắt đầu mở lệnh mới
        """
        if self.dp:
            self.dp.send_msg(
                f"🟢 [VÀO LỆNH MỚI]\n"
                f"• Cặp giao dịch: {pair}\n"
                f"• Giá mua dự kiến: {rate:.4f} USDT\n"
                f"• Khối lượng: {amount:.6f}\n"
                f"• Lý do mua (Tín hiệu): {entry_tag or 'TIN_HIEU_CHINH'}\n"
                f"• Ngưỡng cắt lỗ bảo vệ: {self.stoploss * 100:.1f}%"
            )
        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs
    ) -> bool:
        """
        Gửi báo cáo Tiếng Việt mỗi khi Bot đóng lệnh (Chốt lời, Cắt lỗ hoặc Bán khẩn cấp)
        """
        if self.dp:
            profit_ratio = trade.calc_profit_ratio(rate)
            bieu_tuong = "💰 [CHỐT LỜI]" if profit_ratio >= 0 else "🛑 [CẮT LỖ / ĐÓNG LỆNH]"
            self.dp.send_msg(
                f"{bieu_tuong} {pair}\n"
                f"• Giá mua vào: {trade.open_rate:.4f} USDT\n"
                f"• Giá bán ra: {rate:.4f} USDT\n"
                f"• Tỷ lệ Lãi/Lỗ: {profit_ratio * 100:.2f}%\n"
                f"• Lý do đóng: {exit_reason}"
            )
        return True
