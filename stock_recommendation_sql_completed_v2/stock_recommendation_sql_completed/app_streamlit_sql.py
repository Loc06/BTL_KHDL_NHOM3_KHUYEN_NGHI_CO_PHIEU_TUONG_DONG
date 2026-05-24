"""
app_streamlit_sql.py
Streamlit demo đọc dữ liệu trực tiếp từ SQL Server.

Chạy:
    python -m streamlit run app_streamlit_sql.py

Điều kiện:
    1) Đã chạy database/StockRecommendation_SQLServer_Final.sql trong SSMS.
    2) Đã chạy python src/07_export_to_sql.py hoặc python run_all_with_sql.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CHART_KMEANS = ROOT / "charts" / "kmeans_3d_interactive.html"
CHART_HDBSCAN = ROOT / "charts" / "hdbscan_3d_interactive.html"
sys.path.insert(0, str(SRC))

from db_connection import test_connection  # noqa: E402
from sql_server_io import (  # noqa: E402
    get_cluster_members_from_sql,
    get_cluster_summary_from_sql,
    get_recommendations_from_sql,
    normalize_ticker_for_sql,
)


@st.cache_data(ttl=60)
def cached_connection_info() -> dict:
    return test_connection()


@st.cache_data(ttl=60)
def cached_cluster_summary() -> pd.DataFrame:
    return get_cluster_summary_from_sql()


@st.cache_data(ttl=60)
def cached_cluster_members() -> pd.DataFrame:
    return get_cluster_members_from_sql()


st.set_page_config(page_title="Stock Recommendation SQL Server", layout="wide")
st.title("📈 Similar Stock Recommendation + SQL Server")
st.write(
    "Stocks, StockClusterResults, ClusterDefinitions, Recommendations và stored procedure."
)

try:
    info = cached_connection_info()
except Exception as exc:
    st.error("Chưa kết nối được SQL Server.")
    st.code(str(exc), language="text")
    st.stop()

with st.expander("Thông tin kết nối SQL Server", expanded=False):
    st.json(info)

try:
    summary = cached_cluster_summary()
    members = cached_cluster_members()
except Exception as exc:
    st.error("Kết nối được SQL Server nhưng chưa đọc được view. Có thể bạn chưa chạy SQL schema hoặc chưa export dữ liệu Python vào SQL.")
    st.code(str(exc), language="text")
    st.stop()

if summary.empty or members.empty:
    st.warning("SQL Server chưa có dữ liệu cluster. Hãy chạy: python src/07_export_to_sql.py")
    st.stop()

# Lấy run mới nhất để hiển thị mặc định.
latest_run_id = int(members["run_id"].max())
latest_members = members[members["run_id"] == latest_run_id].copy()
latest_summary = summary[summary["run_id"] == latest_run_id].copy()

st.subheader(f"Model run mới nhất: run_id = {latest_run_id}")
st.dataframe(
    latest_summary[[
        "run_id", "run_name", "algorithm", "cluster_id", "cluster_name",
        "risk_level", "strategy_type", "total_stocks", "tickers"
    ]],
    use_container_width=True,
)

with st.expander("Danh sách cổ phiếu theo từng cụm"):
    for cluster_id, group in latest_members.sort_values(["cluster_id", "ticker"]).groupby("cluster_id"):
        cluster_name = group["cluster_name"].iloc[0]
        st.markdown(f"**Cluster {int(cluster_id)} — {cluster_name} — {len(group)} mã**")
        st.code(", ".join(group["ticker"].astype(str).tolist()),
                language="text")

st.subheader("Biểu đồ PCA 3D: KMeans và HDBSCAN")
st.write(
    "Hai biểu đồ này là file HTML tương tác được tạo từ pipeline Python. "
    "SQL Server lưu kết quả PCA/cluster, còn file HTML dùng để xoay, zoom và trình bày trực quan."
)

tab_kmeans, tab_hdbscan = st.tabs(["KMeans 3D", "HDBSCAN 3D"])

with tab_kmeans:
    if CHART_KMEANS.exists():
        components.html(CHART_KMEANS.read_text(encoding="utf-8"), height=780, scrolling=True)
    else:
        st.warning("Chưa thấy charts/kmeans_3d_interactive.html. Hãy chạy `python run_all.py` trước.")

with tab_hdbscan:
    if CHART_HDBSCAN.exists():
        components.html(CHART_HDBSCAN.read_text(encoding="utf-8"), height=780, scrolling=True)
    else:
        st.warning("Chưa thấy charts/hdbscan_3d_interactive.html. Hãy chạy `python run_all.py` trước.")

tickers = sorted(latest_members["ticker"].astype(str).unique().tolist())

col1, col2 = st.columns([2, 1])
with col1:
    selected = st.selectbox("Chọn mã cổ phiếu", tickers, index=tickers.index("FPT") if "FPT" in tickers else 0)
with col2:
    top_n = st.number_input("Số mã gợi ý", min_value=1, max_value=20, value=5, step=1)

manual = st.text_input("Hoặc nhập mã thủ công, ví dụ FPT hoặc FPT.VN", value="")
query_ticker = normalize_ticker_for_sql(manual) if manual.strip() else selected

st.subheader(f"Top {top_n} mã gần {query_ticker} nhất")
try:
    rec = get_recommendations_from_sql(query_ticker, top_n=int(top_n))
except Exception as exc:
    st.error("Không lấy được recommendation từ stored procedure dbo.usp_GetStockRecommendations.")
    st.code(str(exc), language="text")
    st.stop()

if rec.empty:
    st.warning("Không có recommendation.")
else:
    show_cols = [
        "rank_order", "selected_ticker", "selected_company", "selected_cluster",
        "recommended_ticker", "recommended_company", "recommended_sector", "recommended_cluster",
        "distance", "similarity_score", "same_cluster",
    ]
    show_cols = [c for c in show_cols if c in rec.columns]
    st.dataframe(rec[show_cols], use_container_width=True)

st.subheader("Tọa độ PCA 3D và cụm trong SQL")
show_member_cols = [
    "run_id", "cluster_id", "cluster_name", "ticker", "company_name", "sector",
    "pca_1", "pca_2", "pca_3", "distance_to_centroid", "is_noise"
]
st.dataframe(latest_members[[c for c in show_member_cols if c in latest_members.columns]], use_container_width=True)
