"""
07_export_to_sql.py
Đẩy kết quả PCA + KMeans + Recommendation từ CSV vào SQL Server.

Chạy từ thư mục gốc project:
    python src/07_export_to_sql.py

Điều kiện trước khi chạy:
    1. Đã chạy file database/StockRecommendation_SQLServer_Final.sql trong SSMS 22.
    2. Đã chạy python run_all.py để có data/output/stock_clusters_final.csv
       và data/output/similar_stock_recommendations_all.csv.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from db_connection import available_drivers, test_connection
from sql_server_io import export_project_outputs_to_sql


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ML outputs to SQL Server")
    parser.add_argument("--report-date", default="2025-12-31", help="Ngày báo cáo cho StockFinancialMetrics, dạng YYYY-MM-DD")
    parser.add_argument("--trade-date", default="2025-12-31", help="Ngày snapshot giá cho StockPriceHistory, dạng YYYY-MM-DD")
    parser.add_argument("--cluster-file", default=None, help="Đường dẫn stock_clusters_final.csv nếu muốn override")
    parser.add_argument("--recommendation-file", default=None, help="Đường dẫn similar_stock_recommendations_all.csv nếu muốn override")
    args = parser.parse_args()

    print("=" * 80)
    print("KIỂM TRA KẾT NỐI SQL SERVER")
    print("=" * 80)
    print("ODBC drivers:", available_drivers())
    info = test_connection()
    print("Kết nối thành công:")
    for key, value in info.items():
        print(f"- {key}: {value}")

    kwargs = {
        "report_date": parse_date(args.report_date),
        "trade_date": parse_date(args.trade_date),
    }
    if args.cluster_file:
        kwargs["cluster_path"] = Path(args.cluster_file)
    if args.recommendation_file:
        kwargs["recommendation_path"] = Path(args.recommendation_file)

    print("\n" + "=" * 80)
    print("EXPORT OUTPUT PYTHON VÀO SQL SERVER")
    print("=" * 80)
    result = export_project_outputs_to_sql(**kwargs)
    print("Export thành công. Kết quả:")
    for key, value in result.items():
        print(f"- {key}: {value}")

    print("\nChạy thử trong SSMS:")
    print("EXEC dbo.usp_GetStockRecommendations @Ticker = N'FPT', @RunId = {}, @TopN = 5;".format(result["run_id"]))
    print("SELECT * FROM dbo.vw_ClusterSummary WHERE run_id = {};".format(result["run_id"]))


if __name__ == "__main__":
    main()
