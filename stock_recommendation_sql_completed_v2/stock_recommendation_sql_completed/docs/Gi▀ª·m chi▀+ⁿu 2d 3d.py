import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# =====================================================
# LOAD DATA (Sửa lỗi đường dẫn file từ bước trước)
# =====================================================
try:
    # Thay "vn100" bằng file dữ liệu thật đã lưu ở các bước trước
    df = pd.read_csv("vn100.csv")
    print("✅ Đã tải file dữ liệu thành công!")
except FileNotFoundError:
    print("❌ Không tìm thấy file 'dataset_cleaned.csv'.")
    print("👉 Mẹo: Hãy đổi tên file dữ liệu VN30/VN100 của bạn thành 'dataset_cleaned.csv' hoặc sửa lại đoạn code này.")
    exit()

# =====================================================
# GIỮ TICKER (Sửa lỗi KeyError: Thay 'Stock' thành 'Ticker')
# =====================================================
# Bản dữ liệu Kaggle/Vnstock dùng cột 'Ticker' hoặc 'ticker' để lưu mã
if "Ticker" in df.columns:
    stocks = df["Ticker"]
elif "ticker" in df.columns:
    stocks = df["ticker"]
elif "Stock" in df.columns:
    stocks = df["Stock"]
else:
    # Nếu file thu gọn chỉ có mã ở cột đầu tiên
    stocks = df.iloc[:, 0]

# =====================================================
# CHỌN FEATURES NUMERIC
# =====================================================
# Loại bỏ các cột phi số như Ticker, Date trước khi đưa vào PCA
X = df.select_dtypes(include=np.number)

# Phải xử lý triệt để nếu cột dữ liệu trống hoàn toàn
X = X.dropna(how='all', axis=1)

# =====================================================
# FILL NA
# =====================================================
X = X.fillna(X.median())

# =====================================================
# STANDARDIZE (Chuẩn hóa Z-score là bắt buộc đối với PCA)
# =====================================================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# =====================================================
# PCA 2D
# =====================================================
pca_2d = PCA(n_components=2)
X_pca_2d = pca_2d.fit_transform(X_scaled)

# =====================================================
# EXPLAINED VARIANCE
# =====================================================
print("\n========== PCA 2D EXTRACTION ==========\n")
print("Explained Variance Ratio (Năng lượng giữ lại từng thành phần):", pca_2d.explained_variance_ratio_)
print("Total Explained Variance (Tổng năng lượng thông tin 2D):", f"{pca_2d.explained_variance_ratio_.sum() * 100:.2f}%")

# =====================================================
# DATAFRAME 2D
# =====================================================
pca2d_df = pd.DataFrame({
    "Ticker": stocks,
    "PC1": X_pca_2d[:, 0],
    "PC2": X_pca_2d[:, 1]
})

print("\n========== PCA 2D DATA SAMPLE ==========\n")
print(pca2d_df.head())

# =====================================================
# VISUALIZE 2D
# =====================================================
plt.figure(figsize=(12, 8))
plt.scatter(X_pca_2d[:, 0], X_pca_2d[:, 1], alpha=0.7, edgecolors='k', c='royalblue', s=60)

# Thêm nhãn chữ cho từng mã cổ phiếu (Tránh trùng chữ)
for i, stock in enumerate(stocks):
    # Loại bỏ đuôi thị trường nếu có (.VN)
    label = str(stock).replace(".VN", "")
    plt.text(
        X_pca_2d[i, 0] + 0.05, # Dịch lề phải một chút để không đè lên chấm tròn
        X_pca_2d[i, 1] + 0.05, 
        label,
        fontsize=8,
        weight='bold'
    )

plt.title("VN Market Structure - PCA 2D Projection", fontsize=14, weight='bold')
plt.xlabel("Principal Component 1 (PC1)", fontsize=11)
plt.ylabel("Principal Component 2 (PC2)", fontsize=11)
plt.grid(True, linestyle='--', alpha=0.6)

# =====================================================
# PCA 3D
# =====================================================
# Ràng buộc số chiều không vượt quá số lượng đặc trưng đầu vào ban đầu
n_feats = X_scaled.shape[1]
components_3d = min(3, n_feats)

if components_3d == 3:
    pca_3d = PCA(n_components=3)
    X_pca_3d = pca_3d.fit_transform(X_scaled)

    print("\n========== PCA 3D EXTRACTION ==========\n")
    print("Explained Variance Ratio:", pca_3d.explained_variance_ratio_)
    print("Total Explained Variance (Tổng năng lượng thông tin 3D):", f"{pca_3d.explained_variance_ratio_.sum() * 100:.2f}%")

    # DATAFRAME 3D
    pca3d_df = pd.DataFrame({
        "Ticker": stocks,
        "PC1": X_pca_3d[:, 0],
        "PC2": X_pca_3d[:, 1],
        "PC3": X_pca_3d[:, 2]
    })

    # VISUALIZE 3D (Sửa cú pháp add_subplot chuẩn mới không lo lỗi hệ thống)
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(X_pca_3d[:, 0], X_pca_3d[:, 1], X_pca_3d[:, 2], alpha=0.7, c='crimson', edgecolors='k', s=50)

    for i, stock in enumerate(stocks):
        label = str(stock).replace(".VN", "")
        ax.text(X_pca_3d[i, 0], X_pca_3d[i, 1], X_pca_3d[i, 2], label, fontsize=8)

    ax.set_title("VN Market Structure - PCA 3D Projection", fontsize=14, weight='bold')
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_zlabel("PC3")
    
    # LƯU FILE TÍCH HỢP 3D
    pca3d_df.to_csv("vn100_pca_3d.csv", index=False)
else:
    print("\n⚠️ Số lượng cột đặc trưng nhỏ hơn 3, bỏ qua tính toán ma trận không gian 3D.")

# =====================================================
# SAVE FILES
# =====================================================
pca2d_df.to_csv("vn100_pca_2d.csv", index=False)
print("\n🎉 THÀNH CÔNG! Đã xuất các file giảm chiều dữ liệu ra thư mục:")
print(" -> vn100_pca_2d.csv")
if components_3d == 3:
    print(" -> vn100_pca_3d.csv")

# Hiển thị đồ thị biểu diễn cấu trúc không gian hình học lên màn hình
plt.show()