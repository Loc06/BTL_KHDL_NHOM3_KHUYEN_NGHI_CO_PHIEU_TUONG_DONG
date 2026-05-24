# HƯỚNG DẪN NỐI PYTHON VỚI SQL SERVER CHO PROJECT CỔ PHIẾU

Tài liệu này dành cho project **Stock Similarity Recommendation using PCA + KMeans/HDBSCAN**.  
Mục tiêu là nối được luồng:

```text
SQL Server / CSV dữ liệu
        ↓
Python xử lý ML: clean data → PCA 3D → KMeans/HDBSCAN → recommendation
        ↓
Python ghi kết quả vào SQL Server
        ↓
SSMS / Streamlit SQL đọc kết quả để demo
```

---

## 1. Các file đã thêm vào project

```text
stock_recommendation_sql_completed/
│
├── database/
│   └── StockRecommendation_SQLServer_Final.sql
│
├── src/
│   ├── db_connection.py          # Kết nối Python với SQL Server
│   ├── sql_server_io.py          # Hàm đọc/ghi dữ liệu giữa Python và SQL
│   ├── 00_load_from_sql.py       # Tùy chọn: đọc feature từ SQL ra CSV raw
│   └── 07_export_to_sql.py       # Đẩy kết quả ML từ CSV vào SQL Server
│
├── test_sql_connection.py        # Test kết nối SQL Server
├── run_all_with_sql.py           # Chạy toàn bộ ML rồi export vào SQL
├── app_streamlit_sql.py          # Streamlit đọc trực tiếp từ SQL Server
└── requirements.txt              # Đã thêm pyodbc và SQLAlchemy
```

---

## 2. Chạy database trong SSMS 22

Mở SQL Server Management Studio 22, sau đó:

1. Bấm **New Query**.
2. Mở file:

```text
database/StockRecommendation_SQLServer_Final.sql
```

3. Bấm **Execute** hoặc nhấn **F5**.

Sau khi chạy thành công, trong Object Explorer sẽ có database:

```text
StockSimilarityRecommendationDB
```

Các bảng chính:

```text
dbo.Stocks
dbo.StockFinancialMetrics
dbo.FeatureSets
dbo.MLModelRuns
dbo.ClusterDefinitions
dbo.StockClusterResults
dbo.Recommendations
```

Các view/procedure để demo:

```text
dbo.vw_ClusterSummary
dbo.vw_ClusterMembers
dbo.vw_RecommendationDetails
dbo.usp_GetStockRecommendations
dbo.usp_GetStocksByCluster
```

---

## 3. Cài thư viện Python

Mở terminal ở thư mục project rồi chạy:

```bash
pip install -r requirements.txt
```

Nếu muốn cài riêng phần SQL:

```bash
pip install pyodbc SQLAlchemy
```

Máy Windows cần có **ODBC Driver for SQL Server**. Nên dùng một trong hai driver:

```text
ODBC Driver 18 for SQL Server
ODBC Driver 17 for SQL Server
```

---

## 4. Test kết nối Python → SQL Server

Chạy:

```bash
python test_sql_connection.py
```

Nếu thành công, terminal sẽ hiện gần như sau:

```text
ODBC drivers đang có:
- ODBC Driver 18 for SQL Server

Đang test kết nối SQL Server...
Kết nối thành công!
server_name: ...
database_name: StockSimilarityRecommendationDB
login_name: ...
product_version: ...
```

---

## 5. Nếu server của bạn không phải .\SQLEXPRESS

Mặc định file `src/db_connection.py` dùng:

```python
DEFAULT_SERVER = r".\SQLEXPRESS"
DEFAULT_DATABASE = "StockSimilarityRecommendationDB"
```

Nếu trong SSMS bạn connect bằng tên khác, ví dụ:

```text
localhost
DESKTOP-ABC\SQLEXPRESS
(localdb)\MSSQLLocalDB
```

thì có 2 cách sửa.

### Cách 1: sửa trực tiếp trong `src/db_connection.py`

```python
DEFAULT_SERVER = r"localhost"
```

hoặc:

```python
DEFAULT_SERVER = r"DESKTOP-ABC\SQLEXPRESS"
```

### Cách 2: dùng biến môi trường, không cần sửa code

PowerShell:

```powershell
$env:SQL_SERVER=".\SQLEXPRESS"
$env:SQL_DATABASE="StockSimilarityRecommendationDB"
python test_sql_connection.py
```

CMD:

```cmd
set SQL_SERVER=.\SQLEXPRESS
set SQL_DATABASE=StockSimilarityRecommendationDB
python test_sql_connection.py
```

---

## 6. Chạy pipeline rồi export vào SQL Server

Có 2 cách.

### Cách nhanh nhất

Chạy toàn bộ từ đầu đến cuối:

```bash
python run_all_with_sql.py
```

File này sẽ chạy lần lượt:

```text
02_prepare_data.py
03_pca.py
04_clustering.py
05_supervised_model.py
06_recommendation.py
07_export_to_sql.py
```

### Cách tách riêng cho dễ kiểm soát

Chạy Machine Learning trước:

```bash
python run_all.py
```

Sau đó export vào SQL:

```bash
python src/07_export_to_sql.py
```

Khi export thành công, terminal sẽ hiện kiểu:

```text
Export thành công. Kết quả:
- run_id: 2
- metric_rows_upserted: 89
- cluster_results_inserted: 89
- recommendations_inserted: 445
```

Ý nghĩa:

```text
89 cổ phiếu được lưu feature + PCA + cluster vào SQL
445 recommendation = 89 mã * top 5 gợi ý mỗi mã
```

---

## 7. Query kiểm tra trong SSMS

### Xem model run mới nhất

```sql
SELECT TOP 10 *
FROM dbo.MLModelRuns
ORDER BY run_id DESC;
```

### Xem tóm tắt các cụm

```sql
SELECT *
FROM dbo.vw_ClusterSummary
ORDER BY run_id DESC, cluster_id;
```

### Xem cổ phiếu trong từng cụm

```sql
SELECT *
FROM dbo.vw_ClusterMembers
ORDER BY run_id DESC, cluster_id, ticker;
```

### Gợi ý cổ phiếu giống FPT

```sql
EXEC dbo.usp_GetStockRecommendations @Ticker = N'FPT', @TopN = 5;
```

Nếu muốn lấy đúng run mới nhất vừa export:

```sql
DECLARE @LatestRunId INT;

SELECT TOP 1 @LatestRunId = run_id
FROM dbo.MLModelRuns
ORDER BY run_id DESC;

EXEC dbo.usp_GetStockRecommendations
    @Ticker = N'FPT',
    @RunId = @LatestRunId,
    @TopN = 5;
```

### Xem recommendation đã lưu từ Python

```sql
SELECT *
FROM dbo.vw_RecommendationDetails
ORDER BY run_id DESC, selected_ticker, rank_order;
```

---

## 8. Chạy Streamlit đọc trực tiếp SQL Server

App cũ đọc CSV:

```bash
python -m streamlit run app_streamlit.py
```

App mới đọc SQL Server:

```bash
python -m streamlit run app_streamlit_sql.py
```

App SQL sẽ đọc:

```text
dbo.vw_ClusterSummary
dbo.vw_ClusterMembers
dbo.usp_GetStockRecommendations
```

---

## 9. Python đang ghi gì vào từng bảng?

### `dbo.Stocks`

Lưu danh mục cổ phiếu. Python chuyển ticker:

```text
FPT.VN → FPT
ACB.VN → ACB
```

Vì SQL demo đang dùng mã không có `.VN`.

### `dbo.StockFinancialMetrics`

Mapping từ file `stock_clusters_final.csv`:

```text
PE      → pe_ratio
PB      → pb_ratio
ROE     → roe
ROA     → roa
REV_G   → revenue_growth
EPS_G   → profit_growth
DE      → debt_to_equity
MCAP    → market_cap_billion, chia cho 1 tỷ
DY      → dividend_yield
BETA    → beta
AVG_VOL → avg_volume
VOL     → volatility_30d
RET     → return_1y
```

### `dbo.StockClusterResults`

Mapping:

```text
KMeans_Cluster → cluster_id
PC1            → pca_1
PC2            → pca_2
PC3            → pca_3
Is_Outlier     → is_noise
```

`distance_to_centroid` được Python tự tính lại từ tâm cụm KMeans.

### `dbo.Recommendations`

Mapping từ `similar_stock_recommendations_all.csv`:

```text
Query_Ticker        → input_stock_id
Recommended_Ticker  → recommended_stock_id
Rank                → rank_order
Distance            → distance
Similarity          → similarity_score
Same_Cluster        → same_cluster
```

---

## 10. Lỗi thường gặp và cách sửa

### Lỗi 1: Không tìm thấy ODBC Driver

Lỗi có dạng:

```text
Không tìm thấy ODBC Driver cho SQL Server
```

Cách sửa:

- Cài Microsoft ODBC Driver 17 hoặc 18 for SQL Server.
- Sau đó chạy lại:

```bash
python test_sql_connection.py
```

### Lỗi 2: Login failed

Có thể bạn đang dùng SQL Authentication nhưng code mặc định là Windows Authentication.

Nếu dùng Windows Authentication thì giữ nguyên.

Nếu dùng user/password, set biến môi trường:

PowerShell:

```powershell
$env:SQL_TRUSTED_CONNECTION="no"
$env:SQL_USERNAME="sa"
$env:SQL_PASSWORD="your_password"
python test_sql_connection.py
```

### Lỗi 3: Cannot open database

Có thể bạn chưa chạy file SQL tạo database.

Cách sửa:

1. Mở SSMS.
2. Chạy file `database/StockRecommendation_SQLServer_Final.sql`.
3. Chạy lại:

```bash
python test_sql_connection.py
```

### Lỗi 4: Không tìm thấy `stock_clusters_final.csv`

Cách sửa:

```bash
python run_all.py
python src/07_export_to_sql.py
```

---

## 11. Câu thuyết trình phần SQL + Python

Bạn có thể nói:

> Trong project này, Python chịu trách nhiệm xử lý Machine Learning gồm làm sạch dữ liệu, chuẩn hóa feature, giảm chiều PCA 3D, phân cụm KMeans/HDBSCAN và tính khoảng cách giữa các cổ phiếu. SQL Server được dùng để lưu dữ liệu cổ phiếu, feature tài chính, kết quả PCA, kết quả phân cụm và bảng recommendation. Sau khi Python chạy xong, file `07_export_to_sql.py` sẽ đẩy toàn bộ output vào SQL Server. Nhờ vậy nhóm có thể dùng SSMS hoặc Streamlit để truy vấn nhanh một mã thuộc cụm nào, cụm gồm những mã nào, và khi chọn mã FPT thì hệ thống đề xuất các mã gần nhất theo khoảng cách Euclidean trong không gian PCA 3D.

