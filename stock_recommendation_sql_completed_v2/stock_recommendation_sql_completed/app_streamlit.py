"""
app_streamlit.py
Demo Similar Stock Recommendation bằng PCA + KMeans.

Chạy đúng cách:
python -m streamlit run app_streamlit.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
CLUSTER_FILE = ROOT / "data" / "output" / "stock_clusters_final.csv"
SIMILAR_FILE = ROOT / "data" / "output" / "similar_stock_recommendations_all.csv"
CHART_KMEANS = ROOT / "charts" / "kmeans_3d_interactive.html"
CHART_HDBSCAN = ROOT / "charts" / "hdbscan_3d_interactive.html"
PC_COLUMNS = ["PC1", "PC2", "PC3"]


def normalize_ticker(ticker: str) -> str:
    ticker = str(ticker).strip().upper()
    if ticker and not ticker.endswith(".VN"):
        ticker += ".VN"
    return ticker


@st.cache_data
def load_data():
    if not CLUSTER_FILE.exists():
        return None
    return pd.read_csv(CLUSTER_FILE)


def recommend_similar_stocks(df, ticker, top_n=5, same_cluster_only=True, fill_if_not_enough=True):
    query = normalize_ticker(ticker)
    if query not in set(df["Ticker"].astype(str)):
        raise ValueError(f"Không tìm thấy mã {query} trong dữ liệu.")

    selected = df.loc[df["Ticker"].astype(str) == query].iloc[0]
    selected_vec = selected[PC_COLUMNS].to_numpy(dtype=float)
    selected_cluster = selected["KMeans_Cluster"]

    candidates = df[df["Ticker"].astype(str) != query].copy()
    X = candidates[PC_COLUMNS].to_numpy(dtype=float)
    candidates["Distance"] = np.linalg.norm(X - selected_vec, axis=1)
    candidates["Similarity"] = 1 / (1 + candidates["Distance"])
    candidates["Same_Cluster"] = candidates["KMeans_Cluster"] == selected_cluster

    if same_cluster_only:
        same = candidates[candidates["Same_Cluster"]].sort_values("Distance")
        rec = same.head(top_n).copy()
        if fill_if_not_enough and len(rec) < top_n:
            used = set(rec["Ticker"].astype(str)) | {query}
            extra = candidates[~candidates["Ticker"].astype(str).isin(used)].sort_values("Distance")
            rec = pd.concat([rec, extra.head(top_n - len(rec))], ignore_index=True)
    else:
        rec = candidates.sort_values("Distance").head(top_n).copy()

    rec = rec.reset_index(drop=True)
    rec.insert(0, "Rank", np.arange(1, len(rec) + 1))
    return rec, selected


st.set_page_config(page_title="Similar Stock Recommendation", layout="wide")
st.title("📈 Similar Stock Recommendation bằng PCA + KMeans")
st.write(
    "Nhập hoặc chọn một mã cổ phiếu mẫu. Hệ thống sẽ tìm 5 mã gần nhất trong không gian PCA 3D "
    "và ưu tiên các mã cùng cụm KMeans."
)

if not CLUSTER_FILE.exists():
    st.error("Chưa có file clustering. Hãy chạy `python run_all.py` trước.")
    st.stop()

df = load_data()
if df is None or df.empty:
    st.error("Không đọc được dữ liệu clustering.")
    st.stop()

tickers = sorted(df["Ticker"].astype(str).tolist())

st.subheader("Danh sách cổ phiếu theo từng cụm KMeans")
cluster_counts = df["KMeans_Cluster"].value_counts().sort_index()
st.write("KMeans đang chia dữ liệu thành 4 cụm: " + ", ".join([f"Cluster {int(k)}: {int(v)} mã" for k, v in cluster_counts.items()]))

with st.expander("Mở danh sách mã của từng cụm"):
    for cluster_id, group in df.sort_values(["KMeans_Cluster", "Ticker"]).groupby("KMeans_Cluster"):
        tickers_in_cluster = group["Ticker"].astype(str).tolist()
        sector_text = ""
        if "Sector" in group.columns:
            top_sectors = group["Sector"].astype(str).value_counts().head(5)
            sector_text = " | Ngành nổi bật: " + ", ".join([f"{idx} ({val})" for idx, val in top_sectors.items()])
        st.markdown(f"**Cluster {int(cluster_id)} — {len(tickers_in_cluster)} mã{sector_text}**")
        st.code(", ".join(tickers_in_cluster), language="text")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    selected_ticker = st.selectbox("Chọn mã cổ phiếu mẫu", tickers, index=tickers.index("FPT.VN") if "FPT.VN" in tickers else 0)
with col2:
    manual_ticker = st.text_input("Hoặc nhập mã thủ công, ví dụ FPT hoặc FPT.VN", value="")
with col3:
    top_n = st.number_input("Số mã gợi ý", min_value=1, max_value=20, value=5, step=1)

same_cluster_only = st.checkbox("Ưu tiên chỉ lấy mã cùng cụm KMeans", value=True)
query_ticker = normalize_ticker(manual_ticker) if manual_ticker.strip() else selected_ticker

try:
    rec, selected = recommend_similar_stocks(df, query_ticker, top_n=int(top_n), same_cluster_only=same_cluster_only)
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.subheader(f"Mã tham chiếu: {selected['Ticker']}")
summary_cols = [c for c in ["Ticker", "Sector", "KMeans_Cluster", "HDBSCAN_Cluster_ID", "Is_Outlier", "PC1", "PC2", "PC3", "RET", "VOL", "PE", "ROE", "DY", "BETA"] if c in df.columns]
st.dataframe(pd.DataFrame([selected[summary_cols]]), use_container_width=True)

st.subheader(f"Top {top_n} cổ phiếu gần {selected['Ticker']} nhất trong không gian PCA")
show_cols = [c for c in ["Rank", "Ticker", "Sector", "KMeans_Cluster", "Same_Cluster", "Distance", "Similarity", "PC1", "PC2", "PC3", "RET", "VOL", "PE", "ROE", "DY", "BETA", "Is_Outlier"] if c in rec.columns]
view = rec[show_cols].copy()
if "Distance" in view.columns:
    view["Distance"] = view["Distance"].round(6)
if "Similarity" in view.columns:
    view["Similarity"] = view["Similarity"].round(6)
st.dataframe(view, use_container_width=True)

st.subheader("Giải thích công thức")
st.markdown(
    """
- Sau PCA, mỗi cổ phiếu là một điểm 3D: **PC1, PC2, PC3**.  
- Hệ thống tính khoảng cách Euclidean giữa mã tham chiếu và các mã còn lại.  
- Công thức similarity: **Similarity = 1 / (1 + Distance)**.  
- Distance càng nhỏ thì Similarity càng cao, nghĩa là hai cổ phiếu càng giống nhau trong không gian PCA.  
- KMeans không tự đặt tên cụm; nó chỉ gom các mã gần nhau thành các cluster.
"""
)

with st.expander("Xem biểu đồ KMeans 3D"):
    if CHART_KMEANS.exists():
        st.components.v1.html(CHART_KMEANS.read_text(encoding="utf-8"), height=780, scrolling=True)
    else:
        st.warning("Chưa có biểu đồ KMeans. Hãy chạy `python run_all.py` trước.")

with st.expander("Xem biểu đồ HDBSCAN 3D"):
    if CHART_HDBSCAN.exists():
        st.components.v1.html(CHART_HDBSCAN.read_text(encoding="utf-8"), height=780, scrolling=True)
    else:
        st.warning("Chưa có biểu đồ HDBSCAN. Hãy chạy `python run_all.py` trước.")
