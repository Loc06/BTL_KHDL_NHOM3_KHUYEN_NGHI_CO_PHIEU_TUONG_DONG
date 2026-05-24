import numpy as np
import pandas as pd
import itertools
import os
import time
import plotly.express as px
# SỬA LỖI GIẢI QUYẾT TRIỆT ĐỂ: Dùng bộ HDBSCAN tích hợp sẵn trong thư viện gốc sklearn
from sklearn.cluster import HDBSCAN

# =====================================================================
# BƯỚC 1: KHỞI TẠO VÀ KIỂM TRA DỮ LIỆU LUỒNG PHÂN CỤM
# =====================================================================
# ĐỒNG BỘ FILE: Thống nhất dùng chung một tên file đầu vào là "vn100_pca_3d.csv"
input_filename = "pc3.csv"

if not os.path.exists(input_filename):
    raise FileNotFoundError(f"❌ Không tìm thấy file tọa độ '{input_filename}' trong cùng thư mục!")

df_pca3d = pd.read_csv(input_filename)
stocks = df_pca3d["Ticker"]
X = df_pca3d[["PC1", "PC2", "PC3"]].values
total_samples = len(X)

print(f"✅ Đã nạp tọa độ PCA 3D: {total_samples} mã cổ phiếu.")

print("\n" + "══════════════════════════════════════════════════════════════════════")
print("CHẠY TIẾN TRÌNH OPTIMIZED GRID SEARCH CHO HDBSCAN (sklearn)")
print("══════════════════════════════════════════════════════════════════════")
print(f" {'mcs':>5} {'ms':>5} {'clusters':>10} {'noise%':>10} {'noise_n':>9} {'Time(s)':>8}")
print("──────────────────────────────────────────────────────────────────────")

# Không gian tìm kiếm tham số phù hợp với kích thước tập dữ liệu VN100 (100 mẫu)
hdb_sizes = [3, 4, 5, 6, 7, 8, 10]
hdb_samples = [1, 2, 3, 4, 5]

best_params = None
best_labels = None
min_noise_ratio = 1.0  # Ưu tiên số 1: Ép tỷ lệ cổ phiếu bị coi là nhiễu xuống thấp nhất
max_clusters_for_min_noise = -1

# =====================================================================
# BƯỚC 2: GRID SEARCH MỊN CHỌN ĐIỂM NGỌT (TRÁNH GỘP SAI THÔ)
# =====================================================================
for m in hdb_samples:
    for s in hdb_sizes:
        if m > s: 
            continue  # Điều kiện bắt buộc: min_samples không được lớn hơn min_cluster_size
            
        start_time = time.time()
        
        # SỬA LỖI CÚ PHÁP: Chuyển sang gọi Class HDBSCAN chuẩn của sklearn
        model = HDBSCAN(
            min_cluster_size=s, 
            min_samples=m
        )
        labels = model.fit_predict(X)
        
        elapsed_time = time.time() - start_time
        
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = np.sum(labels == -1)
        noise_ratio = n_noise / total_samples
        
        print(f" {s:>5} {m:>5} {n_clusters:>10} {noise_ratio*100:>9.1f}% {n_noise:>9} {elapsed_time:>8.2f}")
        
        # CHIẾN LƯỢC ĐÁNH GIÁ ĐÚNG TƯ DUY CỦA BẠN:
        # 1. Tìm các bộ tham số đạt tỷ lệ nhiễu thấp nhất hệ thống để cứu vớt cổ phiếu.
        # 2. Nếu tỷ lệ nhiễu bằng nhau, ưu tiên bộ sinh ra nhiều cụm nhất (chống gộp sai các nhóm ngành).
        if noise_ratio < min_noise_ratio:
            min_noise_ratio = noise_ratio
            max_clusters_for_min_noise = n_clusters
            best_params = {'mcs': s, 'ms': m, 'clusters': n_clusters, 'noise_n': n_noise, 'noise_ratio': noise_ratio}
            best_labels = labels
        elif abs(noise_ratio - min_noise_ratio) < 1e-4:
            if n_clusters > max_clusters_for_min_noise:
                max_clusters_for_min_noise = n_clusters
                best_params = {'mcs': s, 'ms': m, 'clusters': n_clusters, 'noise_n': n_noise, 'noise_ratio': noise_ratio}
                best_labels = labels

print("──────────────────────────────────────────────────────────────────────")
print(" BÁO CÁO NGHIỆM THU THAM SỐ TỐT NHẤT HDBSCAN CHO THỊ TRƯỜNG VN100")
print("══════════════════════════════════════════════════════════════════════")
print(f" * Cấu hình tối ưu chốt hạ: min_cluster_size = {best_params['mcs']}, min_samples = {best_params['ms']}")
print(f" * Số lượng cụm tự nhiên giữ lại (chống gộp sai): {best_params['clusters']} cụm")
print(f" * Số lượng cổ phiếu biến động dị biệt bị lọc ra (Noise): {best_params['noise_n']} mã")
print(f" * TỶ LỆ DỮ LIỆU BỊ GÁN NHÃN NHIỄU (-1): {best_params['noise_ratio']*100:.2f}% (Đã tối thiểu hóa)")
print("══════════════════════════════════════════════════════════════════════")

# =====================================================================
# BƯỚC 3: XUẤT BẢNG BIỂU OUTPUT DẠNG FILE
# =====================================================================
np.save("hdbscan_stock_labels.npy", best_labels)
df_pca3d['HDBSCAN_Cluster_ID'] = best_labels
df_pca3d.to_csv("KetQua_PhanCum_Stocks_HDBSCAN.csv", index=False)

print("💾 Đã lưu mảng mã cụm vào: 'hdbscan_stock_labels.npy'")
print("💾 Đã xuất file bảng tính nghiệm thu: 'KetQua_PhanCum_Stocks_HDBSCAN.csv'")

# =====================================================================
# BƯỚC 4: TRỰC QUAN HÓA TƯƠNG TÁC HOVER BẰNG PLOTLY 3D (MÀU SẮC ĐẶC TRƯNG)
# =====================================================================
print("\nĐang khởi tạo bản đồ trực quan hóa thị trường chứng khoán tương tác 3D...")
df_vis = df_pca3d.copy()

# Định dạng nhãn chữ hiển thị cho các cụm
df_vis['Cluster_Name'] = df_vis['HDBSCAN_Cluster_ID'].apply(
    lambda x: "Noise (Dị biệt/Nhiễu)" if x == -1 else f"Cluster {x}")

# Sắp xếp để các điểm Noise (mã dị biệt) vẽ ở lớp nền, các cụm màu nổi bật đè lên trên
df_vis = df_vis.sort_values(by='HDBSCAN_Cluster_ID')

# Thiết lập bảng màu thủ công: Ép Noise làm màu đen, các cụm khác phân phối màu tương phản rõ nét
unique_clusters = df_vis['Cluster_Name'].unique()
color_map = {}
color_palette = px.colors.qualitative.Alphabet + px.colors.qualitative.Dark24
color_idx = 0

for cluster in unique_clusters:
    if "Noise" in cluster:
        color_map[cluster] = "#000000"  # Màu đen đặc trưng cho điểm nhiễu cực đoan như VIC
    else:
        color_map[cluster] = color_palette[color_idx % len(color_palette)]
        color_idx += 1

# Khởi tạo đồ thị Scatter 3D bằng Plotly giúp bạn xoay lật đa chiều tự do
fig = px.scatter_3d(
    df_vis, 
    x='PC1', 
    y='PC2',
    z='PC3',
    color='Cluster_Name',
    color_discrete_map=color_map,
    text='Ticker',  # Hiển thị trực tiếp mã cổ phiếu bên cạnh chấm tròn
    hover_data={
        'PC1': ':.4f',
        'PC2': ':.4f',
        'PC3': ':.4f',
        'Cluster_Name': True,
        'Ticker': True
    },
    title="ĐỒ THỊ PHÂN CỤM THỊ TRƯỜNG VN100 TƯƠNG TÁC (PCA 3D + HDBSCAN)")

# Tinh chỉnh kích thước marker và bổ sung viền bao quanh hạt màu
fig.update_traces(
    marker=dict(
        size=6,
        opacity=0.85,
        line=dict(width=0.5, color='black')
    ),
    textposition='top center'  # Đặt chữ Ticker nằm trên đầu điểm chấm để tránh đè màu
)

# Tinh chỉnh giao diện nền trắng, ô hover màu hồng nhạt đặc trưng giống y hệt form cũ của bạn
fig.update_layout(
    template='plotly_white',
    hoverlabel=dict(
        bgcolor="#f0718d",          # Màu hồng cánh sen đặc trưng của bạn
        font_size=13,
        font_family="Arial",
        font_color="black"
    ),
    scene=dict(
        xaxis_title="PC1",
        yaxis_title="PC2",
        zaxis_title="PC3"
    ),
    legend_title="Phân loại cấu trúc cụm",
    width=1200,
    height=750
)

# Xuất biểu đồ ra file HTML tĩnh độc lập
fig.write_html("BieuDo_3D_TuongTac_Stocks_HDBSCAN.html")
print("===> 🎉 ĐÃ HOÀN THÀNH TẤT CẢ! Hãy mở file 'BieuDo_3D_TuongTac_Stocks_HDBSCAN.html' để hưởng thụ thành quả.")

# Tự động hiển thị bản đồ ra màn hình
fig.show()