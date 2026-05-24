"""
06_recommendation.py
Similar Stock Recommendation dựa trên PCA + KMeans.

Ý tưởng:
- Sau PCA, mỗi cổ phiếu là một điểm trong không gian 3D: PC1, PC2, PC3.
- KMeans chia các điểm này thành các cụm cổ phiếu tương đồng.
- Khi người dùng nhập/chọn một mã cổ phiếu, hệ thống tìm các cổ phiếu gần mã đó nhất
  trong không gian PCA, ưu tiên các mã cùng cụm KMeans.

Output chính:
- data/output/similar_stock_recommendations_all.csv
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import CLUSTER_FILE, DATA_OUTPUT, SIMILAR_RECOMMENDATION_FILE

PC_COLUMNS = ["PC1", "PC2", "PC3"]


def _normalize_ticker(ticker: str) -> str:
    """Chuẩn hóa mã người dùng nhập: fpt -> FPT.VN."""
    ticker = str(ticker).strip().upper()
    if not ticker:
        return ticker
    if not ticker.endswith(".VN"):
        ticker += ".VN"
    return ticker


def load_cluster_data(path: Path = CLUSTER_FILE) -> pd.DataFrame:
    """Đọc dữ liệu đã PCA + KMeans."""
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {path}. Hãy chạy run_all.py hoặc chạy 04_clustering.py trước."
        )

    df = pd.read_csv(path)
    required = ["Ticker", *PC_COLUMNS, "KMeans_Cluster"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu các cột bắt buộc: {missing}")

    return df


def recommend_similar_stocks(
    ticker: str,
    df: Optional[pd.DataFrame] = None,
    top_n: int = 5,
    same_cluster_only: bool = True,
    fill_if_not_enough: bool = True,
) -> pd.DataFrame:
    """
    Tìm top N cổ phiếu giống một mã đầu vào nhất trong không gian PCA.

    Parameters
    ----------
    ticker:
        Mã cổ phiếu người dùng nhập, ví dụ FPT hoặc FPT.VN.
    df:
        DataFrame chứa Ticker, PC1, PC2, PC3, KMeans_Cluster.
    top_n:
        Số mã muốn recommend.
    same_cluster_only:
        Nếu True, ưu tiên chỉ lấy cổ phiếu cùng cụm KMeans.
    fill_if_not_enough:
        Nếu cùng cụm không đủ top_n, tự bổ sung bằng các mã gần nhất toàn thị trường.

    Returns
    -------
    DataFrame gồm Rank, Query_Ticker, Recommended_Ticker, Distance, Similarity.
    """
    if df is None:
        df = load_cluster_data()

    query = _normalize_ticker(ticker)
    if query not in set(df["Ticker"].astype(str)):
        available = ", ".join(sorted(df["Ticker"].astype(str).head(10).tolist()))
        raise ValueError(f"Không tìm thấy mã {query}. Ví dụ mã hợp lệ: {available}, ...")

    selected = df.loc[df["Ticker"].astype(str) == query].iloc[0]
    selected_vec = selected[PC_COLUMNS].to_numpy(dtype=float)
    selected_cluster = selected["KMeans_Cluster"]

    candidates = df[df["Ticker"].astype(str) != query].copy()

    # Tính khoảng cách Euclidean trong không gian PCA 3D.
    X = candidates[PC_COLUMNS].to_numpy(dtype=float)
    distances = np.linalg.norm(X - selected_vec, axis=1)
    candidates["Distance"] = distances
    candidates["Similarity"] = 1 / (1 + candidates["Distance"])
    candidates["Query_Ticker"] = query
    candidates["Query_Cluster"] = selected_cluster
    candidates["Same_Cluster"] = candidates["KMeans_Cluster"] == selected_cluster

    if same_cluster_only:
        same = candidates[candidates["Same_Cluster"]].sort_values("Distance")
        rec = same.head(top_n).copy()

        if fill_if_not_enough and len(rec) < top_n:
            used = set(rec["Ticker"].astype(str)) | {query}
            extra = candidates[~candidates["Ticker"].astype(str).isin(used)].sort_values("Distance")
            rec = pd.concat([rec, extra.head(top_n - len(rec))], ignore_index=True)
    else:
        rec = candidates.sort_values("Distance").head(top_n).copy()

    rec = rec.reset_index(drop=True)
    rec.insert(0, "Rank", np.arange(1, len(rec) + 1))
    rec = rec.rename(columns={"Ticker": "Recommended_Ticker", "KMeans_Cluster": "Recommended_Cluster"})

    # Cột chọn để output dễ nhìn.
    preferred_cols = [
        "Rank", "Query_Ticker", "Recommended_Ticker",
        "Query_Cluster", "Recommended_Cluster", "Same_Cluster",
        "Distance", "Similarity", "Sector",
        "PC1", "PC2", "PC3",
        "RET", "VOL", "PE", "ROE", "DY", "BETA",
        "Is_Outlier",
    ]
    cols = [c for c in preferred_cols if c in rec.columns]
    rec = rec[cols]
    rec["Distance"] = rec["Distance"].round(6)
    rec["Similarity"] = rec["Similarity"].round(6)
    return rec


def build_all_similarity_recommendations(top_n: int = 5, same_cluster_only: bool = True) -> pd.DataFrame:
    """Tạo sẵn top N mã gần nhất cho toàn bộ cổ phiếu trong dataset."""
    df = load_cluster_data()
    results = []
    for ticker in df["Ticker"].astype(str).tolist():
        rec = recommend_similar_stocks(
            ticker=ticker,
            df=df,
            top_n=top_n,
            same_cluster_only=same_cluster_only,
            fill_if_not_enough=True,
        )
        results.append(rec)
    return pd.concat(results, ignore_index=True)


def main():
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    all_rec = build_all_similarity_recommendations(top_n=5, same_cluster_only=True)
    all_rec.to_csv(SIMILAR_RECOMMENDATION_FILE, index=False)

    print("Saved:", SIMILAR_RECOMMENDATION_FILE)
    print("Ví dụ recommendation theo cổ phiếu mẫu:")
    for ticker in ["FPT.VN", "ACB.VN", "VHM.VN"]:
        try:
            print("\n" + "-" * 80)
            print(f"Mã tham chiếu: {ticker}")
            print(recommend_similar_stocks(ticker, top_n=5).to_string(index=False))
        except Exception as exc:
            print(f"Bỏ qua {ticker}: {exc}")


if __name__ == "__main__":
    main()
