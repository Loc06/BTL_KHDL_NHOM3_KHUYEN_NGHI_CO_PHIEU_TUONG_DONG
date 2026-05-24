# Hướng dẫn thuyết trình: Similar Stock Recommendation bằng PCA + KMeans

## 1. Ý tưởng chính

Project không chấm điểm thủ công cổ phiếu theo từng chỉ số tài chính riêng lẻ. Thay vào đó:

```text
Dữ liệu cổ phiếu nhiều chiều
→ Chuẩn hóa dữ liệu
→ PCA giảm chiều thành PC1, PC2, PC3
→ KMeans phân cụm trong không gian PCA
→ Người dùng chọn một mã cổ phiếu mẫu
→ Hệ thống tìm các mã gần nhất trong cùng không gian PCA
```

Ví dụ người dùng chọn `FPT.VN`, hệ thống tìm các mã có vị trí gần `FPT.VN` nhất trong không gian PCA 3D.

## 2. Vì sao PCA?

Ban đầu mỗi cổ phiếu có nhiều feature như RET, VOL, PE, PB, ROE, BETA, DY, REV_G, EPS_G,... Các feature này khó biểu diễn trực quan vì có nhiều chiều.

PCA giúp nén các feature ban đầu thành ba thành phần chính:

```text
PC1, PC2, PC3
```

Mỗi cổ phiếu sau PCA là một điểm trong không gian 3D.

## 3. KMeans dùng để làm gì?

KMeans chia các điểm PCA thành 4 cụm. Thuật toán không tự hiểu cụm nào là phòng thủ hay tăng trưởng. Nó chỉ gom các cổ phiếu có tọa độ gần nhau vào cùng một cụm.

Trong project này, KMeans được dùng để:

- tìm nhóm cổ phiếu có cấu trúc dữ liệu gần nhau;
- hỗ trợ lọc recommendation trong cùng cluster;
- trực quan hóa cụm cổ phiếu trên biểu đồ 3D.

## 4. Công thức tìm cổ phiếu giống nhau

Với hai cổ phiếu A và B:

```text
Distance(A, B) = sqrt((PC1_A - PC1_B)^2 + (PC2_A - PC2_B)^2 + (PC3_A - PC3_B)^2)
```

Khoảng cách càng nhỏ thì hai cổ phiếu càng giống nhau trong không gian PCA.

Similarity score:

```text
Similarity = 1 / (1 + Distance)
```

Distance càng nhỏ thì Similarity càng gần 1.

## 5. Output hệ thống

Khi nhập một mã cổ phiếu, ví dụ `FPT.VN`, hệ thống trả về:

| Rank | Recommended Stock | Cluster | Distance | Similarity |
|---:|---|---:|---:|---:|
| 1 | Mã gần nhất | cùng cụm hoặc gần nhất | nhỏ nhất | cao nhất |
| 2 | Mã gần thứ hai | ... | ... | ... |

## 6. Câu nói thuyết trình

“Trong project này, nhóm em xây dựng hệ thống similar stock recommendation. Mỗi cổ phiếu ban đầu có nhiều đặc trưng tài chính. Sau khi chuẩn hóa, nhóm em dùng PCA để giảm dữ liệu về ba thành phần chính PC1, PC2, PC3. KMeans được dùng để phân cụm các cổ phiếu trong không gian PCA. Khi người dùng chọn một mã cổ phiếu mẫu, hệ thống tính khoảng cách Euclidean từ mã đó đến các mã còn lại, sau đó gợi ý các mã có khoảng cách nhỏ nhất, tức là giống nhất trong không gian PCA.”
