# Stock Similarity Recommendation + SQL Server

Bản này đã được thêm phần nối **Python ↔ SQL Server / SSMS 22**.

## Chạy nhanh

```bash
pip install -r requirements.txt
python test_sql_connection.py
python run_all_with_sql.py
python -m streamlit run app_streamlit_sql.py
```

## Trước đó cần chạy trong SSMS

Mở file này và Execute:

```text
database/StockRecommendation_SQLServer_Final.sql
```

## File quan trọng

```text
src/db_connection.py        Kết nối SQL Server
src/sql_server_io.py        Đọc/ghi dữ liệu SQL
src/07_export_to_sql.py     Export kết quả PCA/KMeans/recommendation vào SQL
test_sql_connection.py      Test kết nối
run_all_with_sql.py         Chạy pipeline + export SQL
app_streamlit_sql.py        Demo Streamlit đọc SQL Server
```

## Query demo trong SSMS

```sql
SELECT * FROM dbo.vw_ClusterSummary ORDER BY run_id DESC, cluster_id;
EXEC dbo.usp_GetStockRecommendations @Ticker = N'FPT', @TopN = 5;
SELECT * FROM dbo.vw_RecommendationDetails ORDER BY run_id DESC, selected_ticker, rank_order;
```

Xem hướng dẫn chi tiết ở:

```text
docs/HUONG_DAN_NOI_SQL_SERVER.md
```
