
"""
04_clustering.py
Chạy KMeans và HDBSCAN.
- KMeans: chia 4 nhóm để phục vụ 4 khẩu vị đầu tư.
- HDBSCAN: phát hiện cổ phiếu dị biệt/outlier.
"""
import json
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from config import PCA_3D_FILE, CLUSTER_FILE, CHARTS, DATA_OUTPUT, RANDOM_STATE

try:
    from sklearn.cluster import HDBSCAN
    HAS_HDBSCAN = True
except Exception:
    HAS_HDBSCAN = False


def run_kmeans(df: pd.DataFrame, n_clusters=4):
    X = df[["PC1", "PC2", "PC3"]].values
    model = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=20)
    labels = model.fit_predict(X)
    score = silhouette_score(X, labels) if len(set(labels)) > 1 else np.nan
    return labels, score


def run_hdbscan_grid(df: pd.DataFrame):
    X = df[["PC1", "PC2", "PC3"]].values
    total = len(df)

    if not HAS_HDBSCAN:
        print("sklearn.cluster.HDBSCAN không khả dụng, bỏ qua HDBSCAN.")
        return np.zeros(total, dtype=int), {"available": False}

    # Grid nhỏ để pipeline chạy nhanh khi thuyết trình.
    # Có thể mở rộng nếu muốn nghiên cứu kỹ hơn.
    candidate_params = [(3, 1), (4, 1), (5, 2), (6, 3), (8, 4), (10, 5)]
    best = None
    best_labels = None
    logs = []

    for min_cluster_size, min_samples in candidate_params:
        if min_samples > min_cluster_size:
            continue
        model = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            copy=True,
            n_jobs=1,
        )
        labels = model.fit_predict(X)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        noise_ratio = n_noise / total
        logs.append({
            "min_cluster_size": min_cluster_size,
            "min_samples": min_samples,
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "noise_ratio": noise_ratio,
        })

        # Tiêu chí mới cân bằng hơn bản cũ:
        # - Không muốn quá nhiều noise.
        # - Không muốn chỉ có 1 cụm khổng lồ.
        # - Ưu tiên có từ 2 cụm trở lên.
        cluster_bonus = min(n_clusters, 5) / 10
        penalty_noise = noise_ratio
        objective = cluster_bonus - penalty_noise

        if best is None or objective > best["objective"]:
            best = {
                "available": True,
                "objective": objective,
                "min_cluster_size": min_cluster_size,
                "min_samples": min_samples,
                "n_clusters": n_clusters,
                "n_noise": n_noise,
                "noise_ratio": noise_ratio,
            }
            best_labels = labels

    best["grid_search_log"] = logs
    return best_labels, best


def save_cluster_members(df: pd.DataFrame):
    """Lưu và in danh sách mã cổ phiếu trong từng cụm KMeans."""
    rows = []
    for cluster_id, group in df.groupby("KMeans_Cluster"):
        tickers = sorted(group["Ticker"].astype(str).tolist())
        sectors = (
            group["Sector"].astype(str).value_counts().head(5).index.tolist()
            if "Sector" in group.columns else []
        )
        rows.append({
            "KMeans_Cluster": int(cluster_id),
            "Count": len(tickers),
            "Top_Sectors": ", ".join(sectors),
            "Tickers": ", ".join(tickers),
        })

    members_df = pd.DataFrame(rows).sort_values("KMeans_Cluster")
    out_csv = DATA_OUTPUT / "kmeans_cluster_members.csv"
    out_json = DATA_OUTPUT / "kmeans_cluster_members.json"

    members_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_json.write_text(
        members_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nDANH SÁCH CỔ PHIẾU THEO TỪNG CỤM KMEANS")
    print("-" * 80)
    for _, row in members_df.iterrows():
        print(f"Cluster {row['KMeans_Cluster']} ({row['Count']} mã): {row['Tickers']}")
    print("-" * 80)
    print("Saved cluster members:", out_csv)

    return members_df


def plot_3d(df: pd.DataFrame, color_col: str, title: str, filename: str):
    fig = px.scatter_3d(
        df,
        x="PC1", y="PC2", z="PC3",
        color=color_col,
        text="Ticker",
        hover_data=["Ticker", "Sector", "RET", "VOL", "PE", "ROE", "DY"],
        title=title,
    )
    fig.update_traces(marker=dict(size=6, opacity=0.85, line=dict(width=0.5, color="black")), textposition="top center")
    fig.update_layout(template="plotly_white", width=1200, height=760, legend_title=color_col)
    out = CHARTS / filename
    fig.write_html(out)
    return out


def run_clustering(input_path=PCA_3D_FILE):
    df = pd.read_csv(input_path)
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)

    kmeans_labels, sil = run_kmeans(df, n_clusters=4)
    df["KMeans_Cluster"] = kmeans_labels

    hdb_labels, hdb_report = run_hdbscan_grid(df)
    df["HDBSCAN_Cluster_ID"] = hdb_labels
    df["Is_Outlier"] = (df["HDBSCAN_Cluster_ID"] == -1).astype(int)

    # Tạo nhãn giải thích sơ bộ cho KMeans dựa trên đặc điểm trung bình cụm.
    cluster_summary = df.groupby("KMeans_Cluster")[["RET", "VOL", "BETA", "ROE", "DY", "PE"]].mean(numeric_only=True)
    cluster_summary.to_csv(DATA_OUTPUT / "cluster_summary.csv")

    # Xuất danh sách mã cổ phiếu của từng cụm để dễ đưa vào báo cáo/thuyết trình.
    cluster_members = save_cluster_members(df)

    metrics = {
        "kmeans_n_clusters": 4,
        "kmeans_silhouette_score": None if np.isnan(sil) else float(sil),
        "hdbscan": hdb_report,
        "kmeans_cluster_counts": df["KMeans_Cluster"].value_counts().sort_index().to_dict(),
        "hdbscan_cluster_counts": df["HDBSCAN_Cluster_ID"].value_counts().sort_index().to_dict(),
    }
    (DATA_OUTPUT / "clustering_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    df.to_csv(CLUSTER_FILE, index=False)
    plot_3d(df, "KMeans_Cluster", "VN Stocks - PCA 3D + KMeans 4 nhóm", "kmeans_3d_interactive.html")
    plot_3d(df, "HDBSCAN_Cluster_ID", "VN Stocks - PCA 3D + HDBSCAN outlier detection", "hdbscan_3d_interactive.html")

    print("Saved:", CLUSTER_FILE)
    print("KMeans silhouette:", sil)
    if hdb_report.get("available"):
        print("HDBSCAN best:", {k: hdb_report[k] for k in ["min_cluster_size", "min_samples", "n_clusters", "n_noise", "noise_ratio"]})
    else:
        print("HDBSCAN skipped")
    return df


if __name__ == "__main__":
    run_clustering()
