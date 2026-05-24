
"""
03_pca.py
Chuẩn hóa dữ liệu bằng StandardScaler và giảm chiều bằng PCA 2D/3D.
Điểm sửa quan trọng so với bản cũ: file PCA vẫn giữ lại feature gốc để recommendation dùng tiếp.
"""
import json
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from config import CLEAN_FILE, PCA_2D_FILE, PCA_3D_FILE, FEATURE_COLUMNS, CHARTS, DATA_PROCESSED, RANDOM_STATE


def run_pca(input_path=CLEAN_FILE):
    df = pd.read_csv(input_path)
    features = [c for c in FEATURE_COLUMNS if c in df.columns]
    if len(features) < 3:
        raise ValueError("Cần ít nhất 3 feature số để chạy PCA 3D.")

    X = df[features].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca2 = PCA(n_components=2, random_state=RANDOM_STATE)
    X2 = pca2.fit_transform(X_scaled)

    pca3 = PCA(n_components=3, random_state=RANDOM_STATE)
    X3 = pca3.fit_transform(X_scaled)

    pca2_df = df.copy()
    pca2_df["PC1"] = X2[:, 0]
    pca2_df["PC2"] = X2[:, 1]

    pca3_df = df.copy()
    pca3_df["PC1"] = X3[:, 0]
    pca3_df["PC2"] = X3[:, 1]
    pca3_df["PC3"] = X3[:, 2]

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    pca2_df.to_csv(PCA_2D_FILE, index=False)
    pca3_df.to_csv(PCA_3D_FILE, index=False)

    # Lưu variance để đưa vào báo cáo.
    explained = {
        "pca_2d_explained_variance_ratio": pca2.explained_variance_ratio_.tolist(),
        "pca_2d_total": float(pca2.explained_variance_ratio_.sum()),
        "pca_3d_explained_variance_ratio": pca3.explained_variance_ratio_.tolist(),
        "pca_3d_total": float(pca3.explained_variance_ratio_.sum()),
        "features": features,
    }
    (DATA_PROCESSED / "pca_explained_variance.json").write_text(
        json.dumps(explained, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Component loadings: feature nào đóng góp nhiều cho PC1/PC2/PC3.
    loadings = pd.DataFrame(
        pca3.components_.T,
        index=features,
        columns=["PC1_loading", "PC2_loading", "PC3_loading"],
    ).reset_index().rename(columns={"index": "Feature"})
    loadings.to_csv(DATA_PROCESSED / "pca_component_loadings.csv", index=False)

    # Chart 2D cơ bản.
    plt.figure(figsize=(12, 8))
    plt.scatter(pca2_df["PC1"], pca2_df["PC2"], alpha=0.75, edgecolors="k", s=55)
    for _, row in pca2_df.iterrows():
        plt.text(row["PC1"] + 0.03, row["PC2"] + 0.03, str(row["Ticker"]).replace(".VN", ""), fontsize=7)
    plt.title("VN Stocks - PCA 2D Projection")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(CHARTS / "pca_2d_projection.png", dpi=160)
    plt.close()

    print("Saved:", PCA_2D_FILE)
    print("Saved:", PCA_3D_FILE)
    print("PCA 3D total explained variance:", round(explained["pca_3d_total"] * 100, 2), "%")
    return pca3_df


if __name__ == "__main__":
    run_pca()
