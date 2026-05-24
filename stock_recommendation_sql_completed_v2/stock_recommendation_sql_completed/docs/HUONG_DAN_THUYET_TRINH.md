
# Kịch bản thuyết trình BTL: Hệ thống Recommendation cổ phiếu

## 1. Mở đầu

Đề tài của nhóm em là xây dựng hệ thống recommendation cổ phiếu dựa trên khẩu vị đầu tư của người dùng. Người dùng có thể chọn một trong bốn nhóm: phòng thủ, tăng trưởng, aggressive và cân bằng. Hệ thống sẽ phân tích dữ liệu tài chính, phân cụm cổ phiếu, dùng supervised learning và đưa ra danh sách cổ phiếu phù hợp.

## 2. Dữ liệu

Dữ liệu gồm các nhóm chỉ số:

- Nhóm giá và thanh khoản: CLOSE, RET, AVG_VOL, VOL
- Nhóm định giá: PE, PB, FPE
- Nhóm chất lượng: ROE, ROA
- Nhóm tăng trưởng: REV_G, EPS_G
- Nhóm biên lợi nhuận: GM, PM, OM
- Nhóm sức khỏe tài chính: DE, CR, QR
- Nhóm rủi ro: BETA
- Nhóm dòng tiền và cổ tức: FCF, OCF, DY

## 3. Làm sạch dữ liệu

Nhóm xử lý các giá trị vô hạn, missing values và outliers. Với missing values, nhóm dùng median imputation vì median ít bị ảnh hưởng bởi outlier hơn mean. Với outlier, nhóm dùng winsorization để cắt các giá trị quá cực đoan ở ngưỡng 1% và 99%.

## 4. Chuẩn hóa và PCA

Do các feature có thang đo rất khác nhau, ví dụ volume có thể hàng triệu, PE khoảng vài chục, ROE là tỷ lệ phần trăm, nên nhóm dùng StandardScaler để chuẩn hóa dữ liệu về cùng thang đo. Sau đó nhóm dùng PCA để giảm chiều dữ liệu xuống 2D/3D, giúp trực quan hóa và phân cụm dễ hơn.

## 5. Clustering

Nhóm dùng hai thuật toán clustering:

- KMeans: chia cổ phiếu thành 4 cụm chính phục vụ recommendation.
- HDBSCAN: phát hiện các mã cổ phiếu dị biệt hoặc outlier.

KMeans phù hợp vì bài toán có 4 khẩu vị đầu tư. HDBSCAN phù hợp để phát hiện các mã có đặc điểm khác biệt, không nên gộp cứng vào cụm.

## 6. Supervised Learning

Nhóm tạo nhãn đơn giản:

- Label = 1 nếu RET lớn hơn median RET
- Label = 0 nếu RET nhỏ hơn hoặc bằng median RET

Sau đó train RandomForest và GradientBoosting để dự đoán xác suất một mã thuộc nhóm sinh lời tốt. Xác suất này được gọi là ML_Probability.

## 7. Recommendation Engine

Điểm cuối cùng được tính bằng công thức:

```text
Final_Score = 0.70 × Rule_Based_Score + 0.25 × ML_Probability - 0.05 × Is_Outlier
```

Trong đó:

- Rule_Based_Score phụ thuộc vào khẩu vị đầu tư.
- ML_Probability là xác suất từ mô hình supervised learning.
- Is_Outlier là cờ phát hiện mã dị biệt từ HDBSCAN.

## 8. Kết luận

Hệ thống đã hoàn thiện pipeline từ dữ liệu đầu vào đến recommendation cuối cùng. Điểm mạnh là có kết hợp preprocessing, PCA, clustering, supervised learning, rule-based recommendation và dashboard trực quan.
