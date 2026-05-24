
"""
02_prepare_data.py
Làm sạch dữ liệu, xử lý missing/outlier, thêm Sector và các cờ missing.
"""
import numpy as np
import pandas as pd
from config import RAW_FILE, CLEAN_FILE, FEATURE_COLUMNS, SECTOR_MAP, DATA_PROCESSED


def find_ticker_col(df: pd.DataFrame) -> str:
    for col in ["Ticker", "ticker", "Stock", "stock", "Symbol", "symbol"]:
        if col in df.columns:
            return col
    return df.columns[0]


def winsorize_series(s: pd.Series, lower=0.01, upper=0.99) -> pd.Series:
    """Cắt cực trị nhẹ để outlier không phá PCA/ML."""
    if s.dropna().empty:
        return s
    lo = s.quantile(lower)
    hi = s.quantile(upper)
    return s.clip(lo, hi)


def prepare_data(input_path=RAW_FILE, output_path=CLEAN_FILE):
    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file raw: {input_path}")

    df = pd.read_csv(input_path)
    ticker_col = find_ticker_col(df)
    df = df.rename(columns={ticker_col: "Ticker"})
    df["Ticker"] = df["Ticker"].astype(str).str.strip()

    if "Sector" not in df.columns:
        df["Sector"] = df["Ticker"].map(SECTOR_MAP).fillna("Other")
    else:
        df["Sector"] = df["Sector"].fillna(df["Ticker"].map(SECTOR_MAP)).fillna("Other")

    # Chuẩn hóa dữ liệu vô hạn thành missing.
    df = df.replace([np.inf, -np.inf], np.nan)

    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    for col in available_features:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Cờ missing để report/thuyết trình: mã nào bị API thiếu nhiều dữ liệu.
    for col in available_features:
        df[f"{col}_missing"] = df[col].isna().astype(int)

    df["Missing_Ratio"] = df[[f"{c}_missing" for c in available_features]].mean(axis=1)

    # Winsorize trước impute để giảm tác động PE/DE/FCF cực trị.
    for col in available_features:
        df[col] = winsorize_series(df[col])

    # Fill missing bằng median từng cột.
    for col in available_features:
        median = df[col].median()
        if pd.isna(median):
            median = 0
        df[col] = df[col].fillna(median)

    # Loại trùng mã nếu có.
    df = df.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved cleaned data: {output_path}")
    print("Shape:", df.shape)
    print("Features used:", available_features)
    return df


if __name__ == "__main__":
    prepare_data()
