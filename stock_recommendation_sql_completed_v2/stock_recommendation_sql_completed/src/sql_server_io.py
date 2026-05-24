"""
sql_server_io.py
Hàm đọc/ghi dữ liệu giữa project PCA + KMeans và SQL Server.

Luồng nên dùng khi demo:
    1) Chạy file database/StockRecommendation_SQLServer_Final.sql trong SSMS 22 để tạo DB/bảng.
    2) Chạy python run_all.py để tạo CSV output.
    3) Chạy python src/07_export_to_sql.py để đẩy kết quả thật vào SQL Server.

Các bảng được ghi:
    - dbo.Stocks
    - dbo.StockPriceHistory
    - dbo.StockFinancialMetrics
    - dbo.FeatureSets
    - dbo.MLModelRuns
    - dbo.ClusterDefinitions
    - dbo.StockClusterResults
    - dbo.Recommendations
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

from config import (
    CLUSTER_FILE,
    DATA_OUTPUT,
    FEATURE_COLUMNS,
    RAW_FILE,
    SIMILAR_RECOMMENDATION_FILE,
)
from db_connection import sql_connection


PC_COLUMNS = ["PC1", "PC2", "PC3"]
DEFAULT_REPORT_DATE = date(2025, 12, 31)
DEFAULT_TRADE_DATE = date(2025, 12, 31)


# -----------------------------------------------------------------------------
# Helpers chung
# -----------------------------------------------------------------------------


def normalize_ticker_for_sql(ticker: Any) -> str:
    """FPT.VN -> FPT, fpt -> FPT. SQL đang lưu ticker không có đuôi .VN."""
    value = str(ticker).strip().upper()
    if value.endswith(".VN"):
        value = value[:-3]
    return value


def normalize_ticker_for_python(ticker: Any) -> str:
    """FPT -> FPT.VN, FPT.VN -> FPT.VN. Python project đang dùng đuôi .VN."""
    value = str(ticker).strip().upper()
    if value and not value.endswith(".VN"):
        value += ".VN"
    return value


def clean_scalar(value: Any) -> Any:
    """Đổi NaN/inf/numpy scalar thành kiểu Python an toàn cho pyodbc."""
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.date()
    if pd.isna(value):
        return None
    return value


def clean_row(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(clean_scalar(v) for v in values)


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ensure_database_objects_exist(conn) -> None:
    """Kiểm tra nhanh các bảng quan trọng đã có chưa."""
    required_tables = [
        "Stocks",
        "StockFinancialMetrics",
        "FeatureSets",
        "MLModelRuns",
        "ClusterDefinitions",
        "StockClusterResults",
        "Recommendations",
    ]
    cursor = conn.cursor()
    missing: list[str] = []
    for table in required_tables:
        cursor.execute(
            "SELECT 1 FROM sys.tables WHERE name = ? AND schema_id = SCHEMA_ID('dbo');",
            table,
        )
        if cursor.fetchone() is None:
            missing.append(f"dbo.{table}")
    if missing:
        raise RuntimeError(
            "Database chưa đủ bảng: " + ", ".join(missing) + "\n"
            "Hãy mở SSMS 22 và chạy file database/StockRecommendation_SQLServer_Final.sql trước."
        )


# -----------------------------------------------------------------------------
# ĐỌC DỮ LIỆU TỪ SQL SERVER RA PYTHON
# -----------------------------------------------------------------------------


def load_latest_features_from_sql() -> pd.DataFrame:
    """
    Đọc feature mới nhất từ dbo.vw_LatestStockFeatures.
    Kết quả đang theo schema SQL, dùng cho kiểm tra/truy vấn.
    """
    query = """
    SELECT
        ticker, company_name, sector, industry, exchange_name, report_date,
        pe_ratio, pb_ratio, roe, roa, eps, revenue_growth, profit_growth,
        debt_to_equity, market_cap_billion, dividend_yield, beta, avg_volume,
        volatility_30d, return_1m, return_3m, return_6m, return_1y
    FROM dbo.vw_LatestStockFeatures
    ORDER BY ticker;
    """
    with sql_connection() as conn:
        return pd.read_sql(query, conn)


def export_sql_features_to_raw_csv(output_path: Optional[Path] = None) -> Path:
    """
    Tùy chọn: lấy dữ liệu feature từ SQL Server và xuất thành CSV dạng gần giống data/raw/vn100.csv.

    Lưu ý:
    - Bài hiện tại đã có sẵn data/raw/vn100.csv đầy đủ hơn.
    - Hàm này hữu ích nếu thầy hỏi: Python có đọc được từ SQL không?
    - Một số feature gốc không có trong SQL demo sẽ để trống, 02_prepare_data.py sẽ tự xử lý missing.
    """
    df_sql = load_latest_features_from_sql()
    if df_sql.empty:
        raise RuntimeError("dbo.vw_LatestStockFeatures không có dữ liệu.")

    out = pd.DataFrame()
    out["Stock"] = df_sql["ticker"].map(normalize_ticker_for_python)
    out["CLOSE"] = np.nan
    out["RET"] = df_sql.get("return_1y")
    out["AVG_VOL"] = df_sql.get("avg_volume")
    out["VOL"] = df_sql.get("volatility_30d")
    out["PE"] = df_sql.get("pe_ratio")
    out["PB"] = df_sql.get("pb_ratio")
    out["FPE"] = np.nan
    out["ROE"] = df_sql.get("roe")
    out["ROA"] = df_sql.get("roa")
    out["REV_G"] = df_sql.get("revenue_growth")
    out["EPS_G"] = df_sql.get("profit_growth")
    out["GM"] = np.nan
    out["PM"] = np.nan
    out["OM"] = np.nan
    out["DE"] = df_sql.get("debt_to_equity")
    out["CR"] = np.nan
    out["QR"] = np.nan
    out["BETA"] = df_sql.get("beta")
    out["MCAP"] = df_sql.get("market_cap_billion") * 1_000_000_000
    out["FCF"] = np.nan
    out["OCF"] = np.nan
    out["DY"] = df_sql.get("dividend_yield")

    if output_path is None:
        output_path = RAW_FILE.parent / "vn100_from_sql.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


# -----------------------------------------------------------------------------
# GHI DỮ LIỆU TỪ PYTHON/CSV VÀO SQL SERVER
# -----------------------------------------------------------------------------


def upsert_stocks(conn, cluster_df: pd.DataFrame) -> dict[str, int]:
    """Upsert danh mục cổ phiếu vào dbo.Stocks và trả về map ticker_sql -> stock_id."""
    cursor = conn.cursor()
    rows = []
    for _, row in cluster_df.drop_duplicates(subset=["Ticker"]).iterrows():
        ticker_sql = normalize_ticker_for_sql(row["Ticker"])
        sector = clean_scalar(row.get("Sector", "Other")) or "Other"
        company_name = ticker_sql  # Dataset chưa có tên công ty, dùng ticker làm tên tạm.
        rows.append((ticker_sql, company_name, sector, sector, "VN", f"Vietnam stock {ticker_sql}"))

    merge_sql = """
    MERGE dbo.Stocks AS target
    USING (SELECT ? AS ticker, ? AS company_name, ? AS sector, ? AS industry, ? AS exchange_name, ? AS description) AS source
    ON UPPER(target.ticker) = UPPER(source.ticker)
    WHEN MATCHED THEN
        UPDATE SET
            -- Dataset Python chưa có tên công ty đầy đủ, nên không ghi đè company_name cũ nếu đã có.
            company_name = COALESCE(NULLIF(target.company_name, N''), source.company_name),
            sector = source.sector,
            industry = source.industry,
            exchange_name = source.exchange_name,
            description = source.description,
            updated_at = SYSDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (ticker, company_name, sector, industry, exchange_name, description)
        VALUES (source.ticker, source.company_name, source.sector, source.industry, source.exchange_name, source.description);
    """
    for row in rows:
        cursor.execute(merge_sql, clean_row(row))

    cursor.execute("SELECT stock_id, ticker FROM dbo.Stocks;")
    return {normalize_ticker_for_sql(row.ticker): int(row.stock_id) for row in cursor.fetchall()}


def upsert_stock_price_history(conn, cluster_df: pd.DataFrame, stock_id_map: dict[str, int], trade_date: date = DEFAULT_TRADE_DATE) -> int:
    """Lưu snapshot giá CLOSE/AVG_VOL vào dbo.StockPriceHistory nếu có."""
    if "CLOSE" not in cluster_df.columns:
        return 0

    cursor = conn.cursor()
    count = 0
    sql = """
    MERGE dbo.StockPriceHistory AS target
    USING (
        SELECT ? AS stock_id, ? AS trade_date, ? AS close_price, ? AS adjusted_close, ? AS volume
    ) AS source
    ON target.stock_id = source.stock_id AND target.trade_date = source.trade_date
    WHEN MATCHED THEN
        UPDATE SET close_price = source.close_price, adjusted_close = source.adjusted_close, volume = source.volume
    WHEN NOT MATCHED THEN
        INSERT (stock_id, trade_date, close_price, adjusted_close, volume)
        VALUES (source.stock_id, source.trade_date, source.close_price, source.adjusted_close, source.volume);
    """
    for _, row in cluster_df.iterrows():
        ticker_sql = normalize_ticker_for_sql(row["Ticker"])
        stock_id = stock_id_map.get(ticker_sql)
        if stock_id is None:
            continue
        close_price = clean_scalar(row.get("CLOSE"))
        avg_volume = clean_scalar(row.get("AVG_VOL"))
        volume = int(avg_volume) if avg_volume is not None else None
        cursor.execute(sql, (stock_id, trade_date, close_price, close_price, volume))
        count += 1
    return count


def upsert_financial_metrics(
    conn,
    cluster_df: pd.DataFrame,
    stock_id_map: dict[str, int],
    report_date: date = DEFAULT_REPORT_DATE,
) -> int:
    """Upsert feature đầu vào vào dbo.StockFinancialMetrics."""
    cursor = conn.cursor()
    sql = """
    MERGE dbo.StockFinancialMetrics AS target
    USING (
        SELECT
            ? AS stock_id, ? AS report_date, ? AS pe_ratio, ? AS pb_ratio,
            ? AS roe, ? AS roa, ? AS eps, ? AS revenue_growth, ? AS profit_growth,
            ? AS debt_to_equity, ? AS market_cap_billion, ? AS dividend_yield,
            ? AS beta, ? AS avg_volume, ? AS volatility_30d, ? AS return_1m,
            ? AS return_3m, ? AS return_6m, ? AS return_1y, ? AS data_source
    ) AS source
    ON target.stock_id = source.stock_id AND target.report_date = source.report_date
    WHEN MATCHED THEN
        UPDATE SET
            pe_ratio = source.pe_ratio,
            pb_ratio = source.pb_ratio,
            roe = source.roe,
            roa = source.roa,
            eps = source.eps,
            revenue_growth = source.revenue_growth,
            profit_growth = source.profit_growth,
            debt_to_equity = source.debt_to_equity,
            market_cap_billion = source.market_cap_billion,
            dividend_yield = source.dividend_yield,
            beta = source.beta,
            avg_volume = source.avg_volume,
            volatility_30d = source.volatility_30d,
            return_1m = source.return_1m,
            return_3m = source.return_3m,
            return_6m = source.return_6m,
            return_1y = source.return_1y,
            data_source = source.data_source
    WHEN NOT MATCHED THEN
        INSERT (
            stock_id, report_date, pe_ratio, pb_ratio, roe, roa, eps,
            revenue_growth, profit_growth, debt_to_equity, market_cap_billion,
            dividend_yield, beta, avg_volume, volatility_30d,
            return_1m, return_3m, return_6m, return_1y, data_source
        )
        VALUES (
            source.stock_id, source.report_date, source.pe_ratio, source.pb_ratio,
            source.roe, source.roa, source.eps, source.revenue_growth, source.profit_growth,
            source.debt_to_equity, source.market_cap_billion, source.dividend_yield,
            source.beta, source.avg_volume, source.volatility_30d,
            source.return_1m, source.return_3m, source.return_6m, source.return_1y, source.data_source
        );
    """

    count = 0
    for _, row in cluster_df.iterrows():
        ticker_sql = normalize_ticker_for_sql(row["Ticker"])
        stock_id = stock_id_map.get(ticker_sql)
        if stock_id is None:
            continue

        mcap = clean_scalar(row.get("MCAP"))
        market_cap_billion = float(mcap) / 1_000_000_000 if mcap is not None else None
        avg_volume = clean_scalar(row.get("AVG_VOL"))
        avg_volume = int(avg_volume) if avg_volume is not None else None

        values = (
            stock_id,
            report_date,
            row.get("PE"),
            row.get("PB"),
            row.get("ROE"),
            row.get("ROA"),
            None,  # Dataset chưa có EPS tuyệt đối, chỉ có EPS_G.
            row.get("REV_G"),
            row.get("EPS_G"),
            row.get("DE"),
            market_cap_billion,
            row.get("DY"),
            row.get("BETA"),
            avg_volume,
            row.get("VOL"),
            None,
            None,
            None,
            row.get("RET"),
            "Python pipeline output",
        )
        cursor.execute(sql, clean_row(values))
        count += 1
    return count


def upsert_feature_set(conn) -> int:
    """Tạo/lấy FeatureSets cho đúng bộ feature đang dùng trong config.py."""
    cursor = conn.cursor()
    name = "Python PCA/KMeans Feature Set"
    description = "Bộ feature dùng trong project Python: giá, return, volume, định giá, sinh lời, tăng trưởng, nợ, beta, vốn hóa, dòng tiền, cổ tức."
    features_json = json.dumps({"features": FEATURE_COLUMNS}, ensure_ascii=False)

    cursor.execute("SELECT feature_set_id FROM dbo.FeatureSets WHERE feature_set_name = ?;", name)
    row = cursor.fetchone()
    if row:
        feature_set_id = int(row.feature_set_id)
        cursor.execute(
            "UPDATE dbo.FeatureSets SET description = ?, features_json = ? WHERE feature_set_id = ?;",
            description,
            features_json,
            feature_set_id,
        )
        return feature_set_id

    cursor.execute(
        """
        INSERT INTO dbo.FeatureSets (feature_set_name, description, features_json)
        OUTPUT INSERTED.feature_set_id
        VALUES (?, ?, ?);
        """,
        name,
        description,
        features_json,
    )
    return int(cursor.fetchone().feature_set_id)


def create_model_run(conn, feature_set_id: int, metrics: dict[str, Any]) -> int:
    """Thêm một dòng MLModelRuns cho lần export hiện tại."""
    cursor = conn.cursor()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name = f"Python KMeans PCA 3D k=4 - {now_text}"

    hdbscan_info = metrics.get("hdbscan", {}) if isinstance(metrics.get("hdbscan"), dict) else {}
    parameters = {
        "kmeans_n_clusters": metrics.get("kmeans_n_clusters", 4),
        "pca_components": 3,
        "random_state": 42,
        "recommendation_distance": "euclidean_on_PC1_PC2_PC3",
        "hdbscan": hdbscan_info,
    }

    silhouette = metrics.get("kmeans_silhouette_score")
    cursor.execute(
        """
        INSERT INTO dbo.MLModelRuns (
            feature_set_id, run_name, algorithm, scaler, dimensionality_reduction,
            pca_components, n_clusters, parameters_json, silhouette_score, note
        )
        OUTPUT INSERTED.run_id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        feature_set_id,
        run_name,
        "KMeans",
        "StandardScaler",
        "PCA",
        3,
        int(metrics.get("kmeans_n_clusters", 4) or 4),
        json.dumps(parameters, ensure_ascii=False),
        clean_scalar(silhouette),
        "Kết quả thật export từ Python pipeline của nhóm.",
    )
    return int(cursor.fetchone().run_id)


def build_cluster_definition_rows(cluster_df: pd.DataFrame, run_id: int) -> list[tuple[Any, ...]]:
    """Tạo tên/mô tả cụm tự động dựa trên ngành nổi bật và thống kê trung bình."""
    definitions = []
    for cluster_id, group in cluster_df.groupby("KMeans_Cluster"):
        cluster_id_int = int(cluster_id)
        top_sectors = group["Sector"].astype(str).value_counts().head(5)
        sector_text = ", ".join([f"{sector} ({count})" for sector, count in top_sectors.items()])
        tickers = ", ".join(sorted(group["Ticker"].astype(str).map(normalize_ticker_for_sql).tolist())[:15])

        avg_ret = group["RET"].mean() if "RET" in group.columns else np.nan
        avg_vol = group["VOL"].mean() if "VOL" in group.columns else np.nan
        avg_roe = group["ROE"].mean() if "ROE" in group.columns else np.nan
        avg_pe = group["PE"].mean() if "PE" in group.columns else np.nan

        if cluster_id_int == 0:
            cluster_name = "Cụm 0 - Ngân hàng/Tài chính và vốn hóa lớn"
            strategy = "Tài chính / ổn định tương đối"
            risk = "Trung bình"
        elif cluster_id_int == 1:
            cluster_name = "Cụm 1 - Chất lượng/phòng thủ/tăng trưởng ổn định"
            strategy = "Cân bằng / phòng thủ"
            risk = "Thấp - Trung bình"
        elif cluster_id_int == 2:
            cluster_name = "Cụm 2 - Bất động sản vốn hóa rất lớn"
            strategy = "Vốn hóa lớn / đặc thù ngành"
            risk = "Trung bình - Cao"
        elif cluster_id_int == 3:
            cluster_name = "Cụm 3 - Midcap/chu kỳ/biến động cao"
            strategy = "Chu kỳ / tăng trưởng rủi ro cao"
            risk = "Cao"
        else:
            cluster_name = f"Cụm {cluster_id_int}"
            strategy = "Chưa gán"
            risk = "Chưa đánh giá"

        description = (
            f"Cụm có {len(group)} mã. Ngành nổi bật: {sector_text}. "
            f"Một số mã: {tickers}."
        )
        characteristics = (
            f"RET TB={avg_ret:.4f} nếu có; VOL TB={avg_vol:.4f} nếu có; "
            f"ROE TB={avg_roe:.4f} nếu có; PE TB={avg_pe:.4f} nếu có."
        )
        definitions.append((run_id, cluster_id_int, cluster_name, description, characteristics, risk, strategy))
    return definitions


def insert_cluster_definitions(conn, cluster_df: pd.DataFrame, run_id: int) -> int:
    cursor = conn.cursor()
    rows = build_cluster_definition_rows(cluster_df, run_id)
    sql = """
    INSERT INTO dbo.ClusterDefinitions (
        run_id, cluster_id, cluster_name, cluster_description,
        typical_characteristics, risk_level, strategy_type
    )
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    cursor.fast_executemany = True
    cursor.executemany(sql, [clean_row(row) for row in rows])
    return len(rows)


def compute_distance_to_centroid(cluster_df: pd.DataFrame) -> pd.Series:
    """Tính distance_to_centroid cho từng mã theo cụm KMeans."""
    df = cluster_df.copy()
    centroids = df.groupby("KMeans_Cluster")[PC_COLUMNS].transform("mean")
    distances = np.sqrt(((df[PC_COLUMNS] - centroids) ** 2).sum(axis=1))
    return distances


def insert_stock_cluster_results(conn, cluster_df: pd.DataFrame, stock_id_map: dict[str, int], run_id: int) -> int:
    cursor = conn.cursor()
    df = cluster_df.copy()
    df["distance_to_centroid"] = compute_distance_to_centroid(df)

    rows = []
    for _, row in df.iterrows():
        ticker_sql = normalize_ticker_for_sql(row["Ticker"])
        stock_id = stock_id_map.get(ticker_sql)
        if stock_id is None:
            continue
        rows.append(
            (
                run_id,
                stock_id,
                int(row["KMeans_Cluster"]),
                row["PC1"],
                row["PC2"],
                row["PC3"],
                row["distance_to_centroid"],
                bool(int(row.get("Is_Outlier", 0) or 0)),
            )
        )

    sql = """
    INSERT INTO dbo.StockClusterResults (
        run_id, stock_id, cluster_id, pca_1, pca_2, pca_3,
        distance_to_centroid, is_noise
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    cursor.fast_executemany = True
    cursor.executemany(sql, [clean_row(row) for row in rows])
    return len(rows)


def insert_recommendations(conn, recommendation_df: pd.DataFrame, stock_id_map: dict[str, int], run_id: int) -> int:
    """Lưu bảng similar_stock_recommendations_all.csv vào dbo.Recommendations."""
    if recommendation_df.empty:
        return 0

    cursor = conn.cursor()
    rows = []
    for _, row in recommendation_df.iterrows():
        input_ticker = normalize_ticker_for_sql(row["Query_Ticker"])
        rec_ticker = normalize_ticker_for_sql(row["Recommended_Ticker"])
        input_id = stock_id_map.get(input_ticker)
        rec_id = stock_id_map.get(rec_ticker)
        if input_id is None or rec_id is None or input_id == rec_id:
            continue
        rows.append(
            (
                run_id,
                input_id,
                rec_id,
                int(row["Rank"]),
                row["Distance"],
                row["Similarity"],
                bool(row.get("Same_Cluster", False)),
                "Python Euclidean distance on PCA 3D",
            )
        )

    sql = """
    INSERT INTO dbo.Recommendations (
        run_id, input_stock_id, recommended_stock_id, rank_order,
        distance, similarity_score, same_cluster, recommendation_method
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    cursor.fast_executemany = True
    cursor.executemany(sql, [clean_row(row) for row in rows])
    return len(rows)


def export_project_outputs_to_sql(
    cluster_path: Path = CLUSTER_FILE,
    recommendation_path: Path = SIMILAR_RECOMMENDATION_FILE,
    metrics_path: Path = DATA_OUTPUT / "clustering_metrics.json",
    report_date: date = DEFAULT_REPORT_DATE,
    trade_date: date = DEFAULT_TRADE_DATE,
) -> dict[str, Any]:
    """Hàm chính: đẩy toàn bộ output của project vào SQL Server."""
    if not cluster_path.exists():
        raise FileNotFoundError(f"Không tìm thấy cluster file: {cluster_path}. Hãy chạy python run_all.py trước.")

    cluster_df = pd.read_csv(cluster_path)
    required = ["Ticker", "Sector", "KMeans_Cluster", *PC_COLUMNS]
    missing = [c for c in required if c not in cluster_df.columns]
    if missing:
        raise ValueError(f"File cluster thiếu cột: {missing}")

    if recommendation_path.exists():
        rec_df = pd.read_csv(recommendation_path)
    else:
        rec_df = pd.DataFrame()

    metrics = read_json_file(metrics_path)

    with sql_connection() as conn:
        ensure_database_objects_exist(conn)
        try:
            stock_id_map = upsert_stocks(conn, cluster_df)
            price_count = upsert_stock_price_history(conn, cluster_df, stock_id_map, trade_date=trade_date)
            metric_count = upsert_financial_metrics(conn, cluster_df, stock_id_map, report_date=report_date)
            feature_set_id = upsert_feature_set(conn)
            run_id = create_model_run(conn, feature_set_id, metrics)
            cluster_definition_count = insert_cluster_definitions(conn, cluster_df, run_id)
            cluster_result_count = insert_stock_cluster_results(conn, cluster_df, stock_id_map, run_id)
            recommendation_count = insert_recommendations(conn, rec_df, stock_id_map, run_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "run_id": run_id,
        "stocks_total_in_map": len(stock_id_map),
        "price_rows_upserted": price_count,
        "metric_rows_upserted": metric_count,
        "feature_set_id": feature_set_id,
        "cluster_definitions_inserted": cluster_definition_count,
        "cluster_results_inserted": cluster_result_count,
        "recommendations_inserted": recommendation_count,
    }


def get_recommendations_from_sql(ticker: str, top_n: int = 5) -> pd.DataFrame:
    """Gọi stored procedure dbo.usp_GetStockRecommendations từ Python."""
    ticker_sql = normalize_ticker_for_sql(ticker)
    query = "EXEC dbo.usp_GetStockRecommendations @Ticker = ?, @TopN = ?;"
    with sql_connection() as conn:
        return pd.read_sql(query, conn, params=[ticker_sql, int(top_n)])


def get_cluster_summary_from_sql() -> pd.DataFrame:
    query = "SELECT * FROM dbo.vw_ClusterSummary ORDER BY run_id DESC, cluster_id;"
    with sql_connection() as conn:
        return pd.read_sql(query, conn)


def get_cluster_members_from_sql() -> pd.DataFrame:
    query = "SELECT * FROM dbo.vw_ClusterMembers ORDER BY run_id DESC, cluster_id, ticker;"
    with sql_connection() as conn:
        return pd.read_sql(query, conn)
