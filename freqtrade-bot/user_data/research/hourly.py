"""Compare VN entry hours using realized, net-of-fees trade results (not forecasts)."""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies"))
from vn_support import aware, number, VN


def summarize(rows, min_trades=30):
    groups = {hour: [] for hour in range(24)}
    for row in rows:
        groups[aware(row["open_date"]).astimezone(VN).hour].append(number(row["profit_abs"]))
    results = []
    for hour, profits in groups.items():
        gain, loss = sum(p for p in profits if p > 0), -sum(p for p in profits if p < 0)
        results.append({"hour_vn": hour, "trades": len(profits),
                        "net_profit": sum(profits), "mean_profit": sum(profits) / len(profits) if profits else None,
                        "win_rate": sum(p > 0 for p in profits) / len(profits) if profits else None,
                        "profit_factor": gain / loss if loss else None,
                        "enough_samples": len(profits) >= min_trades})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="UTF-8 CSV: open_date (ISO timezone), profit_abs (net fees/slippage)")
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()
    if args.min_trades < 1:
        parser.error("--min-trades must be positive")
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        print(json.dumps(summarize(csv.DictReader(f), args.min_trades), ensure_ascii=False, indent=2, allow_nan=False))
