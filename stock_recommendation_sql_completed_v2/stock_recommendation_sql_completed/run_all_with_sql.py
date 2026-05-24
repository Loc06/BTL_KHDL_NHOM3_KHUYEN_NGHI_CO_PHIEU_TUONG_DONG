"""
run_all_with_sql.py
Chạy toàn bộ pipeline rồi tự export kết quả vào SQL Server.

Chạy:
    python run_all_with_sql.py

Nếu chỉ muốn chạy ML không đẩy SQL:
    python run_all.py
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

steps = [
    "02_prepare_data.py",
    "03_pca.py",
    "04_clustering.py",
    "05_supervised_model.py",
    "06_recommendation.py",
    "07_export_to_sql.py",
]

for step in steps:
    print("\n" + "=" * 80, flush=True)
    print(f"RUNNING: {step}", flush=True)
    print("=" * 80, flush=True)
    runpy.run_path(str(SRC / step), run_name="__main__")

print("\nHOÀN TẤT PIPELINE + EXPORT SQL.", flush=True)
print("Mở SSMS và chạy: EXEC dbo.usp_GetStockRecommendations @Ticker = N'FPT', @TopN = 5;", flush=True)
