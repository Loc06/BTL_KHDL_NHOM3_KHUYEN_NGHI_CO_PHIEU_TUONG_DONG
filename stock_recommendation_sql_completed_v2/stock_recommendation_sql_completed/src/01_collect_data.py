
"""
01_collect_data.py
Thu thập dữ liệu cổ phiếu bằng yfinance.

Ghi chú:
- Script này cần internet.
- Nếu không muốn crawl lại, bạn có thể dùng sẵn data/raw/vn100.csv đã được chuẩn bị trong project.
"""
import time
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise ImportError("Bạn cần cài yfinance: pip install yfinance") from exc

from config import DATA_RAW, SECTOR_MAP

VN100_STOCKS = list(SECTOR_MAP.keys())


def collect_stock_data(start="2025-01-01", end="2025-12-31", sleep_sec=1.0):
    rows = []

    for ticker in VN100_STOCKS:
        try:
            print(f"Downloading {ticker} ...")
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start, end=end)

            if hist.empty:
                print(f"No price data for {ticker}")
                continue

            info = stock.info or {}
            close = hist["Close"]

            yearly_return = close.iloc[-1] / close.iloc[0] - 1
            avg_volume = hist["Volume"].mean()
            volatility = close.pct_change().std()

            rows.append({
                "Stock": ticker,
                "Sector": SECTOR_MAP.get(ticker, "Other"),
                "CLOSE": close.iloc[-1],
                "RET": yearly_return,
                "AVG_VOL": avg_volume,
                "VOL": volatility,
                "PE": info.get("trailingPE"),
                "PB": info.get("priceToBook"),
                "FPE": info.get("forwardPE"),
                "ROE": info.get("returnOnEquity"),
                "ROA": info.get("returnOnAssets"),
                "REV_G": info.get("revenueGrowth"),
                "EPS_G": info.get("earningsGrowth"),
                "GM": info.get("grossMargins"),
                "PM": info.get("profitMargins"),
                "OM": info.get("operatingMargins"),
                "DE": info.get("debtToEquity"),
                "CR": info.get("currentRatio"),
                "QR": info.get("quickRatio"),
                "BETA": info.get("beta"),
                "MCAP": info.get("marketCap"),
                "FCF": info.get("freeCashflow"),
                "OCF": info.get("operatingCashflow"),
                "DY": info.get("dividendYield"),
            })

            time.sleep(sleep_sec)
        except Exception as exc:
            print(f"ERROR {ticker}: {exc}")

    df = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    out = DATA_RAW / "vn100.csv"
    df.to_csv(out, index=False)
    print(f"Saved: {out}")
    print(df.shape)
    return df


if __name__ == "__main__":
    collect_stock_data()
