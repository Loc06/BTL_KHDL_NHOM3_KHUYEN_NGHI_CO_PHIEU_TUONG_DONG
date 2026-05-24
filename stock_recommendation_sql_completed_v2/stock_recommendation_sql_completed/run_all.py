"""
run_all.py
Chạy toàn bộ pipeline từ dữ liệu có sẵn:
1. Làm sạch dữ liệu
2. PCA
3. Clustering
4. Supervised Learning
5. Similar Stock Recommendation
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Cho phép các script import config.py trong thư mục src.
sys.path.insert(0, str(SRC))

steps = [
    "02_prepare_data.py",
    "03_pca.py",
    "04_clustering.py",
    "05_supervised_model.py",
    "06_recommendation.py",
]

for step in steps:
    print("\n" + "=" * 80, flush=True)
    print(f"RUNNING: {step}", flush=True)
    print("=" * 80, flush=True)
    runpy.run_path(str(SRC / step), run_name="__main__")

print("\nHOÀN TẤT PIPELINE.", flush=True)
print("Mở data/output/similar_stock_recommendations_all.csv hoặc chạy: python -m streamlit run app_streamlit.py", flush=True)
