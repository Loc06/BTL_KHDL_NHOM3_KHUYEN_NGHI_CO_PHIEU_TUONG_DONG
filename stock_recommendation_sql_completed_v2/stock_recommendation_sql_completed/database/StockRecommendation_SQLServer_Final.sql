/*
    Project: Stock Similarity Recommendation using PCA + Clustering
    DBMS   : Microsoft SQL Server / SQL Server Management Studio 22
    Author : Your Group

    Mục đích:
    - Lưu thông tin mã cổ phiếu
    - Lưu feature đầu vào cho Machine Learning
    - Lưu kết quả PCA 3D
    - Lưu kết quả phân cụm KMeans/HDBSCAN
    - Lưu tên/mô tả cụm
    - Truy vấn gợi ý cổ phiếu tương tự theo mã mẫu, ví dụ FPT -> CMG, ELC,...

    Lưu ý:
    - Đây là script chuẩn T-SQL cho SQL Server, KHÔNG phải MySQL.
    - Script này có phần DROP TABLE/VIEW/PROCEDURE để chạy lại từ đầu cho bài demo.
    - Nếu đã có dữ liệu thật quan trọng, hãy backup trước khi chạy lại.
*/

/* =========================================================
   1. TẠO DATABASE
   ========================================================= */
USE master;
GO

IF DB_ID(N'StockSimilarityRecommendationDB') IS NULL
BEGIN
    CREATE DATABASE StockSimilarityRecommendationDB;
END;
GO

USE StockSimilarityRecommendationDB;
GO

/* =========================================================
   2. XÓA OBJECT CŨ ĐỂ CHẠY LẠI SCRIPT DEMO
   ========================================================= */
DROP PROCEDURE IF EXISTS dbo.usp_GetStockRecommendations;
DROP PROCEDURE IF EXISTS dbo.usp_SaveStockRecommendations;
DROP PROCEDURE IF EXISTS dbo.usp_GetStocksByCluster;
GO

DROP VIEW IF EXISTS dbo.vw_RecommendationDetails;
DROP VIEW IF EXISTS dbo.vw_ClusterSummary;
DROP VIEW IF EXISTS dbo.vw_ClusterMembers;
DROP VIEW IF EXISTS dbo.vw_LatestStockFeatures;
GO

DROP TABLE IF EXISTS dbo.Recommendations;
DROP TABLE IF EXISTS dbo.StockClusterResults;
DROP TABLE IF EXISTS dbo.ClusterDefinitions;
DROP TABLE IF EXISTS dbo.MLModelRuns;
DROP TABLE IF EXISTS dbo.FeatureSets;
DROP TABLE IF EXISTS dbo.StockFinancialMetrics;
DROP TABLE IF EXISTS dbo.StockPriceHistory;
DROP TABLE IF EXISTS dbo.Stocks;
DROP TABLE IF EXISTS dbo.Staging_StockFeatures;
DROP TABLE IF EXISTS dbo.Staging_StockClusterResults;
GO

/* =========================================================
   3. TẠO BẢNG CHÍNH
   ========================================================= */

/*
    Bảng Stocks:
    Lưu danh mục mã cổ phiếu.
*/
CREATE TABLE dbo.Stocks (
    stock_id        INT IDENTITY(1,1) NOT NULL,
    ticker          NVARCHAR(20) NOT NULL,
    company_name    NVARCHAR(255) NOT NULL,
    sector          NVARCHAR(100) NULL,
    industry        NVARCHAR(150) NULL,
    exchange_name   NVARCHAR(50) NULL,
    description     NVARCHAR(1000) NULL,
    created_at      DATETIME2(0) NOT NULL CONSTRAINT DF_Stocks_created_at DEFAULT SYSDATETIME(),
    updated_at      DATETIME2(0) NULL,

    CONSTRAINT PK_Stocks PRIMARY KEY (stock_id),
    CONSTRAINT UQ_Stocks_ticker UNIQUE (ticker)
);
GO

/*
    Bảng StockPriceHistory:
    Lưu dữ liệu giá lịch sử nếu nhóm muốn import OHLCV từ CSV/API.
    Bảng này không bắt buộc cho recommendation nếu feature đã được tính sẵn bằng Python.
*/
CREATE TABLE dbo.StockPriceHistory (
    price_id        BIGINT IDENTITY(1,1) NOT NULL,
    stock_id        INT NOT NULL,
    trade_date      DATE NOT NULL,
    open_price      DECIMAL(18,4) NULL,
    high_price      DECIMAL(18,4) NULL,
    low_price       DECIMAL(18,4) NULL,
    close_price     DECIMAL(18,4) NULL,
    adjusted_close  DECIMAL(18,4) NULL,
    volume          BIGINT NULL,
    created_at      DATETIME2(0) NOT NULL CONSTRAINT DF_StockPriceHistory_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_StockPriceHistory PRIMARY KEY (price_id),
    CONSTRAINT FK_StockPriceHistory_Stocks FOREIGN KEY (stock_id) REFERENCES dbo.Stocks(stock_id),
    CONSTRAINT UQ_StockPriceHistory_stock_date UNIQUE (stock_id, trade_date),
    CONSTRAINT CK_StockPriceHistory_price_nonnegative CHECK (
        (open_price IS NULL OR open_price >= 0) AND
        (high_price IS NULL OR high_price >= 0) AND
        (low_price IS NULL OR low_price >= 0) AND
        (close_price IS NULL OR close_price >= 0) AND
        (adjusted_close IS NULL OR adjusted_close >= 0)
    )
);
GO

/*
    Bảng StockFinancialMetrics:
    Lưu các đặc trưng đầu vào để đưa vào StandardScaler/PCA/KMeans/HDBSCAN.
    Mỗi stock có thể có nhiều dòng theo report_date.
*/
CREATE TABLE dbo.StockFinancialMetrics (
    metric_id          BIGINT IDENTITY(1,1) NOT NULL,
    stock_id           INT NOT NULL,
    report_date        DATE NOT NULL,

    pe_ratio           DECIMAL(18,4) NULL,
    pb_ratio           DECIMAL(18,4) NULL,
    roe                DECIMAL(18,4) NULL,
    roa                DECIMAL(18,4) NULL,
    eps                DECIMAL(18,4) NULL,
    revenue_growth     DECIMAL(18,4) NULL,
    profit_growth      DECIMAL(18,4) NULL,
    debt_to_equity     DECIMAL(18,4) NULL,
    market_cap_billion DECIMAL(18,4) NULL,
    dividend_yield     DECIMAL(18,4) NULL,
    beta               DECIMAL(18,4) NULL,
    avg_volume         BIGINT NULL,
    volatility_30d     DECIMAL(18,4) NULL,
    return_1m          DECIMAL(18,4) NULL,
    return_3m          DECIMAL(18,4) NULL,
    return_6m          DECIMAL(18,4) NULL,
    return_1y          DECIMAL(18,4) NULL,

    data_source        NVARCHAR(100) NULL,
    created_at         DATETIME2(0) NOT NULL CONSTRAINT DF_StockFinancialMetrics_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_StockFinancialMetrics PRIMARY KEY (metric_id),
    CONSTRAINT FK_StockFinancialMetrics_Stocks FOREIGN KEY (stock_id) REFERENCES dbo.Stocks(stock_id),
    CONSTRAINT UQ_StockFinancialMetrics_stock_report UNIQUE (stock_id, report_date),
    CONSTRAINT CK_StockFinancialMetrics_marketcap CHECK (market_cap_billion IS NULL OR market_cap_billion >= 0),
    CONSTRAINT CK_StockFinancialMetrics_avg_volume CHECK (avg_volume IS NULL OR avg_volume >= 0)
);
GO

/*
    Bảng FeatureSets:
    Ghi lại nhóm feature nào được sử dụng trong mô hình.
    Cực hữu ích khi thuyết trình: mô hình không chạy mơ hồ, mà có feature set rõ ràng.
*/
CREATE TABLE dbo.FeatureSets (
    feature_set_id INT IDENTITY(1,1) NOT NULL,
    feature_set_name NVARCHAR(150) NOT NULL,
    description NVARCHAR(1000) NULL,
    features_json NVARCHAR(MAX) NOT NULL,
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_FeatureSets_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_FeatureSets PRIMARY KEY (feature_set_id),
    CONSTRAINT UQ_FeatureSets_name UNIQUE (feature_set_name),
    CONSTRAINT CK_FeatureSets_json CHECK (ISJSON(features_json) = 1)
);
GO

/*
    Bảng MLModelRuns:
    Lưu từng lần chạy mô hình.
    Ví dụ: KMeans k=4 PCA=3, hoặc HDBSCAN min_cluster_size=5.
*/
CREATE TABLE dbo.MLModelRuns (
    run_id                  INT IDENTITY(1,1) NOT NULL,
    feature_set_id           INT NULL,
    run_name                 NVARCHAR(150) NOT NULL,
    algorithm                NVARCHAR(50) NOT NULL,
    scaler                   NVARCHAR(50) NULL,
    dimensionality_reduction NVARCHAR(50) NULL,
    pca_components           INT NULL,
    n_clusters               INT NULL,
    parameters_json          NVARCHAR(MAX) NULL,

    silhouette_score         DECIMAL(18,6) NULL,
    davies_bouldin_score     DECIMAL(18,6) NULL,
    calinski_harabasz_score  DECIMAL(18,6) NULL,

    trained_at               DATETIME2(0) NOT NULL CONSTRAINT DF_MLModelRuns_trained_at DEFAULT SYSDATETIME(),
    note                     NVARCHAR(1000) NULL,

    CONSTRAINT PK_MLModelRuns PRIMARY KEY (run_id),
    CONSTRAINT FK_MLModelRuns_FeatureSets FOREIGN KEY (feature_set_id) REFERENCES dbo.FeatureSets(feature_set_id),
    CONSTRAINT CK_MLModelRuns_pca_components CHECK (pca_components IS NULL OR pca_components > 0),
    CONSTRAINT CK_MLModelRuns_n_clusters CHECK (n_clusters IS NULL OR n_clusters >= -1),
    CONSTRAINT CK_MLModelRuns_parameters_json CHECK (parameters_json IS NULL OR ISJSON(parameters_json) = 1)
);
GO

/*
    Bảng ClusterDefinitions:
    Lưu ý nghĩa từng cụm.
    Với HDBSCAN, cluster_id = -1 thường là nhiễu/noise.
*/
CREATE TABLE dbo.ClusterDefinitions (
    run_id                  INT NOT NULL,
    cluster_id              INT NOT NULL,
    cluster_name            NVARCHAR(200) NOT NULL,
    cluster_description     NVARCHAR(1500) NULL,
    typical_characteristics NVARCHAR(1500) NULL,
    risk_level              NVARCHAR(50) NULL,
    strategy_type           NVARCHAR(100) NULL,
    created_at              DATETIME2(0) NOT NULL CONSTRAINT DF_ClusterDefinitions_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_ClusterDefinitions PRIMARY KEY (run_id, cluster_id),
    CONSTRAINT FK_ClusterDefinitions_MLModelRuns FOREIGN KEY (run_id) REFERENCES dbo.MLModelRuns(run_id)
);
GO

/*
    Bảng StockClusterResults:
    Lưu kết quả PCA 3D và cụm của từng cổ phiếu.
    Đây là bảng chính để vẽ biểu đồ 3D.
*/
CREATE TABLE dbo.StockClusterResults (
    result_id            BIGINT IDENTITY(1,1) NOT NULL,
    run_id               INT NOT NULL,
    stock_id             INT NOT NULL,
    cluster_id           INT NOT NULL,

    pca_1                FLOAT NOT NULL,
    pca_2                FLOAT NOT NULL,
    pca_3                FLOAT NOT NULL,

    distance_to_centroid FLOAT NULL,
    is_noise             BIT NOT NULL CONSTRAINT DF_StockClusterResults_is_noise DEFAULT 0,
    created_at           DATETIME2(0) NOT NULL CONSTRAINT DF_StockClusterResults_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_StockClusterResults PRIMARY KEY (result_id),
    CONSTRAINT FK_StockClusterResults_MLModelRuns FOREIGN KEY (run_id) REFERENCES dbo.MLModelRuns(run_id),
    CONSTRAINT FK_StockClusterResults_Stocks FOREIGN KEY (stock_id) REFERENCES dbo.Stocks(stock_id),
    CONSTRAINT FK_StockClusterResults_ClusterDefinitions FOREIGN KEY (run_id, cluster_id) REFERENCES dbo.ClusterDefinitions(run_id, cluster_id),
    CONSTRAINT UQ_StockClusterResults_run_stock UNIQUE (run_id, stock_id)
);
GO

/*
    Bảng Recommendations:
    Lưu kết quả recommend đã tính sẵn.
    Có thể dùng procedure usp_SaveStockRecommendations để tự động ghi vào bảng này.
*/
CREATE TABLE dbo.Recommendations (
    recommendation_id    BIGINT IDENTITY(1,1) NOT NULL,
    run_id               INT NOT NULL,
    input_stock_id       INT NOT NULL,
    recommended_stock_id INT NOT NULL,
    rank_order           INT NOT NULL,
    distance             FLOAT NOT NULL,
    similarity_score     DECIMAL(18,6) NOT NULL,
    same_cluster         BIT NOT NULL,
    recommendation_method NVARCHAR(200) NOT NULL CONSTRAINT DF_Recommendations_method DEFAULT N'Euclidean distance on PCA 3D',
    created_at           DATETIME2(0) NOT NULL CONSTRAINT DF_Recommendations_created_at DEFAULT SYSDATETIME(),

    CONSTRAINT PK_Recommendations PRIMARY KEY (recommendation_id),
    CONSTRAINT FK_Recommendations_MLModelRuns FOREIGN KEY (run_id) REFERENCES dbo.MLModelRuns(run_id),
    CONSTRAINT FK_Recommendations_InputStock FOREIGN KEY (input_stock_id) REFERENCES dbo.Stocks(stock_id),
    CONSTRAINT FK_Recommendations_RecommendedStock FOREIGN KEY (recommended_stock_id) REFERENCES dbo.Stocks(stock_id),
    CONSTRAINT CK_Recommendations_not_self CHECK (input_stock_id <> recommended_stock_id),
    CONSTRAINT CK_Recommendations_rank CHECK (rank_order > 0),
    CONSTRAINT CK_Recommendations_similarity CHECK (similarity_score >= 0 AND similarity_score <= 1),
    CONSTRAINT UQ_Recommendations_run_input_rank UNIQUE (run_id, input_stock_id, rank_order)
);
GO

/* =========================================================
   4. INDEX ĐỂ QUERY NHANH HƠN
   ========================================================= */
CREATE INDEX IX_Stocks_sector ON dbo.Stocks(sector);
CREATE INDEX IX_StockFinancialMetrics_stock_date ON dbo.StockFinancialMetrics(stock_id, report_date DESC);
CREATE INDEX IX_StockClusterResults_run_cluster ON dbo.StockClusterResults(run_id, cluster_id);
CREATE INDEX IX_Recommendations_input ON dbo.Recommendations(run_id, input_stock_id, rank_order);
GO

/* =========================================================
   5. BẢNG STAGING ĐỂ IMPORT CSV TỪ PYTHON/EXCEL
   ========================================================= */

/*
    Nếu Python xuất file stock_features.csv, có thể import tạm vào bảng này trước,
    rồi INSERT/MERGE sang bảng Stocks và StockFinancialMetrics.
*/
CREATE TABLE dbo.Staging_StockFeatures (
    ticker              NVARCHAR(20) NULL,
    company_name         NVARCHAR(255) NULL,
    sector               NVARCHAR(100) NULL,
    industry             NVARCHAR(150) NULL,
    exchange_name        NVARCHAR(50) NULL,
    report_date          DATE NULL,
    pe_ratio             DECIMAL(18,4) NULL,
    pb_ratio             DECIMAL(18,4) NULL,
    roe                  DECIMAL(18,4) NULL,
    roa                  DECIMAL(18,4) NULL,
    eps                  DECIMAL(18,4) NULL,
    revenue_growth       DECIMAL(18,4) NULL,
    profit_growth        DECIMAL(18,4) NULL,
    debt_to_equity       DECIMAL(18,4) NULL,
    market_cap_billion   DECIMAL(18,4) NULL,
    dividend_yield       DECIMAL(18,4) NULL,
    beta                 DECIMAL(18,4) NULL,
    avg_volume           BIGINT NULL,
    volatility_30d       DECIMAL(18,4) NULL,
    return_1m            DECIMAL(18,4) NULL,
    return_3m            DECIMAL(18,4) NULL,
    return_6m            DECIMAL(18,4) NULL,
    return_1y            DECIMAL(18,4) NULL
);
GO

/*
    Nếu Python xuất file cluster_results.csv, import vào bảng này trước.
*/
CREATE TABLE dbo.Staging_StockClusterResults (
    ticker               NVARCHAR(20) NULL,
    cluster_id           INT NULL,
    pca_1                FLOAT NULL,
    pca_2                FLOAT NULL,
    pca_3                FLOAT NULL,
    distance_to_centroid FLOAT NULL,
    is_noise             BIT NULL
);
GO

/* =========================================================
   6. DỮ LIỆU MẪU MINH HỌA
   =========================================================
   Lưu ý: Đây là dữ liệu demo để chạy được database.
   Khi làm bài thật, nhóm nên thay bằng dữ liệu đã crawl/lấy từ file CSV.
*/

INSERT INTO dbo.Stocks (ticker, company_name, sector, industry, exchange_name, description)
VALUES
(N'FPT', N'FPT Corporation', N'Công nghệ', N'Công nghệ thông tin', N'HOSE', N'Doanh nghiệp công nghệ lớn, thiên về tăng trưởng'),
(N'CMG', N'CMC Corporation', N'Công nghệ', N'Công nghệ thông tin', N'HOSE', N'Doanh nghiệp công nghệ, gần nhóm FPT'),
(N'ELC', N'ELCOM Corporation', N'Công nghệ', N'Giải pháp công nghệ', N'HOSE', N'Công ty công nghệ quy mô vừa'),
(N'VCB', N'Vietcombank', N'Ngân hàng', N'Ngân hàng thương mại', N'HOSE', N'Ngân hàng vốn hóa lớn'),
(N'BID', N'BIDV', N'Ngân hàng', N'Ngân hàng thương mại', N'HOSE', N'Ngân hàng vốn hóa lớn'),
(N'CTG', N'VietinBank', N'Ngân hàng', N'Ngân hàng thương mại', N'HOSE', N'Ngân hàng vốn hóa lớn'),
(N'TCB', N'Techcombank', N'Ngân hàng', N'Ngân hàng thương mại', N'HOSE', N'Ngân hàng tư nhân lớn'),
(N'ACB', N'Asia Commercial Bank', N'Ngân hàng', N'Ngân hàng thương mại', N'HOSE', N'Ngân hàng tư nhân'),
(N'VNM', N'Vinamilk', N'Tiêu dùng', N'Thực phẩm đồ uống', N'HOSE', N'Cổ phiếu tiêu dùng phòng thủ'),
(N'MSN', N'Masan Group', N'Tiêu dùng', N'Tiêu dùng đa ngành', N'HOSE', N'Tập đoàn tiêu dùng'),
(N'MWG', N'Mobile World', N'Bán lẻ', N'Bán lẻ', N'HOSE', N'Doanh nghiệp bán lẻ'),
(N'FRT', N'FPT Retail', N'Bán lẻ', N'Bán lẻ', N'HOSE', N'Doanh nghiệp bán lẻ'),
(N'HPG', N'Hoa Phat Group', N'Công nghiệp', N'Thép', N'HOSE', N'Doanh nghiệp thép vốn hóa lớn'),
(N'HSG', N'Hoa Sen Group', N'Công nghiệp', N'Thép', N'HOSE', N'Doanh nghiệp thép'),
(N'GAS', N'PV Gas', N'Năng lượng', N'Dầu khí', N'HOSE', N'Doanh nghiệp khí vốn hóa lớn'),
(N'PLX', N'Petrolimex', N'Năng lượng', N'Xăng dầu', N'HOSE', N'Doanh nghiệp xăng dầu'),
(N'VHM', N'Vinhomes', N'Bất động sản', N'Bất động sản', N'HOSE', N'Doanh nghiệp bất động sản vốn hóa lớn'),
(N'VIC', N'Vingroup', N'Bất động sản', N'Tập đoàn đa ngành', N'HOSE', N'Tập đoàn đa ngành'),
(N'SSI', N'SSI Securities', N'Tài chính', N'Chứng khoán', N'HOSE', N'Công ty chứng khoán lớn'),
(N'VND', N'VNDirect Securities', N'Tài chính', N'Chứng khoán', N'HOSE', N'Công ty chứng khoán');
GO

DECLARE @FeatureSetId INT;

INSERT INTO dbo.FeatureSets (feature_set_name, description, features_json)
VALUES (
    N'Fundamental + Price Features v1',
    N'Bộ feature gồm định giá, hiệu quả sinh lời, tăng trưởng, nợ, vốn hóa, thanh khoản, biến động và lợi suất.',
    N'{
        "features": [
            "pe_ratio", "pb_ratio", "roe", "roa", "eps",
            "revenue_growth", "profit_growth", "debt_to_equity",
            "market_cap_billion", "dividend_yield", "beta", "avg_volume",
            "volatility_30d", "return_1m", "return_3m", "return_6m", "return_1y"
        ]
    }'
);

SET @FeatureSetId = SCOPE_IDENTITY();

DECLARE @DemoMetrics TABLE (
    ticker NVARCHAR(20), report_date DATE,
    pe_ratio DECIMAL(18,4), pb_ratio DECIMAL(18,4), roe DECIMAL(18,4), roa DECIMAL(18,4), eps DECIMAL(18,4),
    revenue_growth DECIMAL(18,4), profit_growth DECIMAL(18,4), debt_to_equity DECIMAL(18,4), market_cap_billion DECIMAL(18,4),
    dividend_yield DECIMAL(18,4), beta DECIMAL(18,4), avg_volume BIGINT, volatility_30d DECIMAL(18,4),
    return_1m DECIMAL(18,4), return_3m DECIMAL(18,4), return_6m DECIMAL(18,4), return_1y DECIMAL(18,4)
);

INSERT INTO @DemoMetrics
VALUES
(N'FPT','2025-12-31',24.50,5.80,25.20,10.40,5300,18.20,20.10,0.42,165000,1.80,1.05,5200000,18.50,3.20,8.50,18.60,31.20),
(N'CMG','2025-12-31',22.10,4.70,21.50,8.90,3100,19.50,23.40,0.50,26000,0.90,1.12,1700000,21.20,4.10,9.70,19.80,35.50),
(N'ELC','2025-12-31',20.40,3.90,18.70,7.10,2100,17.30,18.60,0.47,6500,0.70,1.18,800000,24.30,2.80,7.60,17.40,29.10),
(N'VCB','2025-12-31',14.20,2.90,20.30,1.90,6100,10.50,11.20,8.20,520000,1.50,0.82,3600000,12.80,1.70,4.90,9.10,18.40),
(N'BID','2025-12-31',13.80,2.20,18.10,1.20,4200,9.80,10.50,9.10,290000,1.30,0.86,4100000,13.90,1.40,4.20,8.70,16.80),
(N'CTG','2025-12-31',12.70,1.90,17.40,1.10,3900,8.70,9.60,8.80,230000,1.20,0.88,3900000,14.40,1.20,3.80,8.10,15.50),
(N'TCB','2025-12-31',11.90,1.70,18.90,1.70,5100,12.30,12.90,7.90,210000,0.80,0.93,4500000,15.10,2.10,5.40,10.20,20.60),
(N'ACB','2025-12-31',10.80,1.60,19.20,1.60,3500,10.80,11.40,7.20,120000,1.10,0.90,3100000,13.60,1.90,5.20,9.50,17.90),
(N'VNM','2025-12-31',17.40,4.20,24.00,16.30,4600,4.80,3.90,0.25,190000,4.20,0.65,2800000,10.20,0.80,2.40,4.10,8.20),
(N'MSN','2025-12-31',31.20,3.40,10.20,3.20,1800,8.10,6.30,1.40,115000,0.70,1.10,2400000,19.80,2.30,6.10,11.80,16.20),
(N'MWG','2025-12-31',18.90,3.00,15.60,5.40,2800,11.70,13.40,0.80,98000,1.00,1.15,4200000,22.40,3.50,7.20,13.30,23.00),
(N'FRT','2025-12-31',28.70,5.10,16.90,4.60,2300,21.40,24.20,1.10,42000,0.40,1.28,1900000,28.10,4.80,12.20,25.50,41.00),
(N'HPG','2025-12-31',16.40,1.80,13.80,7.20,2900,12.00,15.80,0.60,180000,1.60,1.20,5800000,25.60,2.90,8.00,15.40,27.70),
(N'HSG','2025-12-31',13.20,1.30,11.70,5.90,1700,9.40,12.10,0.70,22000,1.90,1.30,2600000,30.20,3.10,9.40,18.20,31.80),
(N'GAS','2025-12-31',15.80,2.60,18.50,11.20,5700,7.20,8.10,0.30,180000,3.10,0.72,1600000,11.90,0.90,2.80,5.60,10.90),
(N'PLX','2025-12-31',19.30,2.10,12.60,5.80,3200,6.60,7.20,0.55,72000,2.60,0.78,1400000,13.20,1.10,3.10,6.40,12.30),
(N'VHM','2025-12-31',9.80,1.40,15.20,6.70,5400,5.30,4.80,0.90,170000,0.00,1.05,3500000,21.50,1.70,5.80,9.70,13.90),
(N'VIC','2025-12-31',35.00,2.50,6.40,2.10,1200,4.20,-5.60,1.80,150000,0.00,1.25,3900000,29.40,-1.20,2.10,5.40,9.60),
(N'SSI','2025-12-31',18.70,2.30,14.80,6.10,2600,14.20,18.70,0.75,65000,1.20,1.35,3700000,32.10,5.20,13.50,22.30,38.40),
(N'VND','2025-12-31',17.60,2.10,13.90,5.80,2100,13.60,17.50,0.80,42000,1.00,1.40,3300000,34.30,5.00,12.80,21.40,36.20);

INSERT INTO dbo.StockFinancialMetrics (
    stock_id, report_date, pe_ratio, pb_ratio, roe, roa, eps, revenue_growth, profit_growth,
    debt_to_equity, market_cap_billion, dividend_yield, beta, avg_volume, volatility_30d,
    return_1m, return_3m, return_6m, return_1y, data_source
)
SELECT
    s.stock_id, m.report_date, m.pe_ratio, m.pb_ratio, m.roe, m.roa, m.eps, m.revenue_growth, m.profit_growth,
    m.debt_to_equity, m.market_cap_billion, m.dividend_yield, m.beta, m.avg_volume, m.volatility_30d,
    m.return_1m, m.return_3m, m.return_6m, m.return_1y, N'Demo data - replace with real data'
FROM @DemoMetrics m
JOIN dbo.Stocks s ON s.ticker = m.ticker;
GO

DECLARE @FeatureSetId2 INT;
SELECT @FeatureSetId2 = feature_set_id
FROM dbo.FeatureSets
WHERE feature_set_name = N'Fundamental + Price Features v1';

INSERT INTO dbo.MLModelRuns (
    feature_set_id, run_name, algorithm, scaler, dimensionality_reduction,
    pca_components, n_clusters, parameters_json,
    silhouette_score, davies_bouldin_score, calinski_harabasz_score, note
)
VALUES (
    @FeatureSetId2,
    N'KMeans PCA 3D k=4 demo',
    N'KMeans',
    N'StandardScaler',
    N'PCA',
    3,
    4,
    N'{"k": 4, "random_state": 42, "n_init": 10, "distance_metric": "euclidean"}',
    0.420000,
    0.880000,
    36.500000,
    N'Demo run. Thay bằng kết quả thật sau khi chạy Python.'
);
GO

DECLARE @RunId INT;
SELECT @RunId = run_id FROM dbo.MLModelRuns WHERE run_name = N'KMeans PCA 3D k=4 demo';

INSERT INTO dbo.ClusterDefinitions (
    run_id, cluster_id, cluster_name, cluster_description, typical_characteristics, risk_level, strategy_type
)
VALUES
(@RunId, 0, N'Cụm công nghệ tăng trưởng',
 N'Nhóm cổ phiếu công nghệ, có tăng trưởng doanh thu/lợi nhuận tốt, định giá thường cao hơn mặt bằng chung.',
 N'PE/PB tương đối cao, ROE tốt, tăng trưởng mạnh, biến động vừa đến cao.',
 N'Trung bình - Cao', N'Tăng trưởng'),
(@RunId, 1, N'Cụm ngân hàng - tài chính',
 N'Nhóm ngân hàng và chứng khoán, có đặc trưng tài chính riêng, vốn hóa và thanh khoản thường cao.',
 N'PB thấp hơn công nghệ, hệ số nợ đặc thù ngành ngân hàng, beta và thanh khoản khá cao.',
 N'Trung bình', N'Chu kỳ tài chính'),
(@RunId, 2, N'Cụm tiêu dùng - bán lẻ',
 N'Nhóm tiêu dùng/bán lẻ, có tính phòng thủ hoặc tăng trưởng tùy doanh nghiệp.',
 N'Doanh thu ổn định, ROE tốt, một số mã có cổ tức, biến động trung bình.',
 N'Thấp - Trung bình', N'Cân bằng'),
(@RunId, 3, N'Cụm công nghiệp - năng lượng - bất động sản',
 N'Nhóm ngành tài sản nặng/vốn hóa lớn như thép, dầu khí, bất động sản.',
 N'Chu kỳ ngành rõ, phụ thuộc giá hàng hóa hoặc thị trường bất động sản, biến động có thể cao.',
 N'Trung bình - Cao', N'Chu kỳ/vốn hóa lớn');
GO

DECLARE @RunId2 INT;
SELECT @RunId2 = run_id FROM dbo.MLModelRuns WHERE run_name = N'KMeans PCA 3D k=4 demo';

DECLARE @DemoPCA TABLE (
    ticker NVARCHAR(20), cluster_id INT, pca_1 FLOAT, pca_2 FLOAT, pca_3 FLOAT, distance_to_centroid FLOAT, is_noise BIT
);

INSERT INTO @DemoPCA
VALUES
(N'FPT', 0,  2.10,  1.20,  0.45, 0.18, 0),
(N'CMG', 0,  2.35,  1.05,  0.52, 0.26, 0),
(N'ELC', 0,  1.88,  0.92,  0.38, 0.33, 0),
(N'VCB', 1, -1.20,  1.55, -0.30, 0.21, 0),
(N'BID', 1, -1.45,  1.40, -0.25, 0.19, 0),
(N'CTG', 1, -1.55,  1.28, -0.20, 0.23, 0),
(N'TCB', 1, -1.05,  1.18, -0.15, 0.30, 0),
(N'ACB', 1, -1.18,  1.08, -0.10, 0.34, 0),
(N'SSI', 1, -0.70,  1.85,  0.35, 0.48, 0),
(N'VND', 1, -0.62,  1.92,  0.40, 0.52, 0),
(N'VNM', 2,  0.40, -1.25, -0.60, 0.24, 0),
(N'MSN', 2,  0.72, -0.95, -0.42, 0.38, 0),
(N'MWG', 2,  0.95, -0.72, -0.20, 0.45, 0),
(N'FRT', 2,  1.20, -0.55, -0.05, 0.62, 0),
(N'HPG', 3, -0.20, -1.80,  0.88, 0.31, 0),
(N'HSG', 3, -0.05, -2.05,  1.02, 0.44, 0),
(N'GAS', 3, -0.55, -1.42,  0.65, 0.29, 0),
(N'PLX', 3, -0.65, -1.30,  0.58, 0.35, 0),
(N'VHM', 3, -0.95, -0.90,  1.10, 0.51, 0),
(N'VIC', 3, -1.15, -0.75,  1.25, 0.67, 0);

INSERT INTO dbo.StockClusterResults (
    run_id, stock_id, cluster_id, pca_1, pca_2, pca_3, distance_to_centroid, is_noise
)
SELECT
    @RunId2, s.stock_id, p.cluster_id, p.pca_1, p.pca_2, p.pca_3, p.distance_to_centroid, p.is_noise
FROM @DemoPCA p
JOIN dbo.Stocks s ON s.ticker = p.ticker;
GO

/* =========================================================
   7. VIEW PHỤC VỤ DEMO/TRÌNH BÀY
   ========================================================= */

CREATE VIEW dbo.vw_LatestStockFeatures AS
WITH RankedMetrics AS (
    SELECT
        m.*,
        ROW_NUMBER() OVER (PARTITION BY m.stock_id ORDER BY m.report_date DESC, m.metric_id DESC) AS rn
    FROM dbo.StockFinancialMetrics m
)
SELECT
    s.stock_id,
    s.ticker,
    s.company_name,
    s.sector,
    s.industry,
    s.exchange_name,
    m.report_date,
    m.pe_ratio,
    m.pb_ratio,
    m.roe,
    m.roa,
    m.eps,
    m.revenue_growth,
    m.profit_growth,
    m.debt_to_equity,
    m.market_cap_billion,
    m.dividend_yield,
    m.beta,
    m.avg_volume,
    m.volatility_30d,
    m.return_1m,
    m.return_3m,
    m.return_6m,
    m.return_1y
FROM RankedMetrics m
JOIN dbo.Stocks s ON s.stock_id = m.stock_id
WHERE m.rn = 1;
GO

CREATE VIEW dbo.vw_ClusterMembers AS
SELECT
    r.run_id,
    r.run_name,
    r.algorithm,
    r.n_clusters,
    cd.cluster_id,
    cd.cluster_name,
    cd.cluster_description,
    cd.risk_level,
    cd.strategy_type,
    s.stock_id,
    s.ticker,
    s.company_name,
    s.sector,
    scr.pca_1,
    scr.pca_2,
    scr.pca_3,
    scr.distance_to_centroid,
    scr.is_noise
FROM dbo.StockClusterResults scr
JOIN dbo.MLModelRuns r ON r.run_id = scr.run_id
JOIN dbo.ClusterDefinitions cd ON cd.run_id = scr.run_id AND cd.cluster_id = scr.cluster_id
JOIN dbo.Stocks s ON s.stock_id = scr.stock_id;
GO

CREATE VIEW dbo.vw_ClusterSummary AS
SELECT
    cm.run_id,
    cm.run_name,
    cm.algorithm,
    cm.cluster_id,
    cm.cluster_name,
    cm.risk_level,
    cm.strategy_type,
    COUNT(*) AS total_stocks,
    STRING_AGG(cm.ticker, N', ') WITHIN GROUP (ORDER BY cm.ticker) AS tickers,
    AVG(cm.pca_1) AS avg_pca_1,
    AVG(cm.pca_2) AS avg_pca_2,
    AVG(cm.pca_3) AS avg_pca_3
FROM dbo.vw_ClusterMembers cm
GROUP BY
    cm.run_id,
    cm.run_name,
    cm.algorithm,
    cm.cluster_id,
    cm.cluster_name,
    cm.risk_level,
    cm.strategy_type;
GO

CREATE VIEW dbo.vw_RecommendationDetails AS
SELECT
    rec.recommendation_id,
    rec.created_at,
    rec.run_id,
    run.run_name,
    input_s.ticker AS selected_ticker,
    input_s.company_name AS selected_company,
    output_s.ticker AS recommended_ticker,
    output_s.company_name AS recommended_company,
    output_s.sector AS recommended_sector,
    rec.rank_order,
    rec.distance,
    rec.similarity_score,
    rec.same_cluster,
    rec.recommendation_method
FROM dbo.Recommendations rec
JOIN dbo.MLModelRuns run ON run.run_id = rec.run_id
JOIN dbo.Stocks input_s ON input_s.stock_id = rec.input_stock_id
JOIN dbo.Stocks output_s ON output_s.stock_id = rec.recommended_stock_id;
GO

/* =========================================================
   8. STORED PROCEDURE: GỢI Ý CỔ PHIẾU TƯƠNG TỰ
   ========================================================= */

CREATE OR ALTER PROCEDURE dbo.usp_GetStockRecommendations
    @Ticker NVARCHAR(20),
    @RunId INT = NULL,
    @TopN INT = 5
AS
BEGIN
    SET NOCOUNT ON;

    IF @TopN IS NULL OR @TopN <= 0
    BEGIN
        THROW 50000, N'@TopN phải lớn hơn 0.', 1;
    END;

    IF @RunId IS NULL
    BEGIN
        SELECT TOP 1 @RunId = run_id
        FROM dbo.MLModelRuns
        ORDER BY trained_at DESC, run_id DESC;
    END;

    IF @RunId IS NULL
    BEGIN
        THROW 50001, N'Chưa có model run nào trong bảng MLModelRuns.', 1;
    END;

    DECLARE @InputStockId INT;

    SELECT @InputStockId = stock_id
    FROM dbo.Stocks
    WHERE UPPER(ticker) = UPPER(@Ticker);

    IF @InputStockId IS NULL
    BEGIN
        THROW 50002, N'Không tìm thấy ticker trong bảng Stocks.', 1;
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM dbo.StockClusterResults
        WHERE run_id = @RunId AND stock_id = @InputStockId
    )
    BEGIN
        THROW 50003, N'Ticker này chưa có kết quả PCA/Cluster trong run đã chọn.', 1;
    END;

    ;WITH TargetStock AS (
        SELECT
            scr.run_id,
            scr.stock_id,
            scr.cluster_id,
            scr.pca_1,
            scr.pca_2,
            scr.pca_3
        FROM dbo.StockClusterResults scr
        WHERE scr.run_id = @RunId
          AND scr.stock_id = @InputStockId
    ),
    Distances AS (
        SELECT
            candidate.stock_id AS recommended_stock_id,
            candidate.cluster_id AS recommended_cluster_id,
            target.cluster_id AS input_cluster_id,
            SQRT(
                POWER(candidate.pca_1 - target.pca_1, 2) +
                POWER(candidate.pca_2 - target.pca_2, 2) +
                POWER(candidate.pca_3 - target.pca_3, 2)
            ) AS distance,
            CASE WHEN candidate.cluster_id = target.cluster_id THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS same_cluster
        FROM dbo.StockClusterResults candidate
        CROSS JOIN TargetStock target
        WHERE candidate.run_id = target.run_id
          AND candidate.stock_id <> target.stock_id
          AND candidate.is_noise = 0
    )
    SELECT TOP (@TopN)
        ROW_NUMBER() OVER (ORDER BY d.distance ASC, s.ticker ASC) AS rank_order,
        input_s.ticker AS selected_ticker,
        input_s.company_name AS selected_company,
        input_cluster.cluster_name AS selected_cluster,
        s.ticker AS recommended_ticker,
        s.company_name AS recommended_company,
        s.sector AS recommended_sector,
        rec_cluster.cluster_name AS recommended_cluster,
        d.distance,
        CAST(1.0 / (1.0 + d.distance) AS DECIMAL(18,6)) AS similarity_score,
        d.same_cluster
    FROM Distances d
    JOIN dbo.Stocks s ON s.stock_id = d.recommended_stock_id
    JOIN dbo.Stocks input_s ON input_s.stock_id = @InputStockId
    JOIN dbo.ClusterDefinitions input_cluster ON input_cluster.run_id = @RunId AND input_cluster.cluster_id = d.input_cluster_id
    JOIN dbo.ClusterDefinitions rec_cluster ON rec_cluster.run_id = @RunId AND rec_cluster.cluster_id = d.recommended_cluster_id
    ORDER BY d.distance ASC, s.ticker ASC;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SaveStockRecommendations
    @Ticker NVARCHAR(20),
    @RunId INT = NULL,
    @TopN INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @TopN IS NULL OR @TopN <= 0
    BEGIN
        THROW 50100, N'@TopN phải lớn hơn 0.', 1;
    END;

    IF @RunId IS NULL
    BEGIN
        SELECT TOP 1 @RunId = run_id
        FROM dbo.MLModelRuns
        ORDER BY trained_at DESC, run_id DESC;
    END;

    IF @RunId IS NULL
    BEGIN
        THROW 50101, N'Chưa có model run nào trong bảng MLModelRuns.', 1;
    END;

    DECLARE @InputStockId INT;

    SELECT @InputStockId = stock_id
    FROM dbo.Stocks
    WHERE UPPER(ticker) = UPPER(@Ticker);

    IF @InputStockId IS NULL
    BEGIN
        THROW 50102, N'Không tìm thấy ticker trong bảng Stocks.', 1;
    END;

    BEGIN TRANSACTION;

    DELETE FROM dbo.Recommendations
    WHERE run_id = @RunId
      AND input_stock_id = @InputStockId;

    ;WITH TargetStock AS (
        SELECT
            scr.run_id,
            scr.stock_id,
            scr.cluster_id,
            scr.pca_1,
            scr.pca_2,
            scr.pca_3
        FROM dbo.StockClusterResults scr
        WHERE scr.run_id = @RunId
          AND scr.stock_id = @InputStockId
    ),
    Distances AS (
        SELECT
            candidate.stock_id AS recommended_stock_id,
            candidate.cluster_id AS recommended_cluster_id,
            target.cluster_id AS input_cluster_id,
            SQRT(
                POWER(candidate.pca_1 - target.pca_1, 2) +
                POWER(candidate.pca_2 - target.pca_2, 2) +
                POWER(candidate.pca_3 - target.pca_3, 2)
            ) AS distance,
            CASE WHEN candidate.cluster_id = target.cluster_id THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS same_cluster
        FROM dbo.StockClusterResults candidate
        CROSS JOIN TargetStock target
        WHERE candidate.run_id = target.run_id
          AND candidate.stock_id <> target.stock_id
          AND candidate.is_noise = 0
    ),
    Ranked AS (
        SELECT TOP (@TopN)
            @RunId AS run_id,
            @InputStockId AS input_stock_id,
            d.recommended_stock_id,
            ROW_NUMBER() OVER (ORDER BY d.distance ASC, s.ticker ASC) AS rank_order,
            d.distance,
            CAST(1.0 / (1.0 + d.distance) AS DECIMAL(18,6)) AS similarity_score,
            d.same_cluster
        FROM Distances d
        JOIN dbo.Stocks s ON s.stock_id = d.recommended_stock_id
        ORDER BY d.distance ASC, s.ticker ASC
    )
    INSERT INTO dbo.Recommendations (
        run_id, input_stock_id, recommended_stock_id, rank_order,
        distance, similarity_score, same_cluster, recommendation_method
    )
    SELECT
        run_id, input_stock_id, recommended_stock_id, rank_order,
        distance, similarity_score, same_cluster,
        N'Euclidean distance on PCA 3D'
    FROM Ranked;

    COMMIT TRANSACTION;

    SELECT *
    FROM dbo.vw_RecommendationDetails
    WHERE run_id = @RunId
      AND selected_ticker = @Ticker
    ORDER BY rank_order;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_GetStocksByCluster
    @ClusterId INT,
    @RunId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @RunId IS NULL
    BEGIN
        SELECT TOP 1 @RunId = run_id
        FROM dbo.MLModelRuns
        ORDER BY trained_at DESC, run_id DESC;
    END;

    SELECT
        cluster_id,
        cluster_name,
        ticker,
        company_name,
        sector,
        pca_1,
        pca_2,
        pca_3,
        distance_to_centroid
    FROM dbo.vw_ClusterMembers
    WHERE run_id = @RunId
      AND cluster_id = @ClusterId
    ORDER BY distance_to_centroid ASC, ticker ASC;
END;
GO

/* =========================================================
   9. LƯU SẴN RECOMMENDATION DEMO CHO FPT
   ========================================================= */
EXEC dbo.usp_SaveStockRecommendations @Ticker = N'FPT', @TopN = 5;
GO

/* =========================================================
   10. QUERY DEMO KHI THUYẾT TRÌNH
   ========================================================= */

-- 10.1. Xem toàn bộ danh sách cổ phiếu
SELECT *
FROM dbo.Stocks
ORDER BY ticker;

-- 10.2. Xem feature mới nhất của từng cổ phiếu
SELECT *
FROM dbo.vw_LatestStockFeatures
ORDER BY ticker;

-- 10.3. Xem kết quả chia cụm và tọa độ PCA 3D
SELECT *
FROM dbo.vw_ClusterMembers
ORDER BY cluster_id, ticker;

-- 10.4. Tóm tắt mỗi cụm có những mã nào
SELECT *
FROM dbo.vw_ClusterSummary
ORDER BY cluster_id;

-- 10.5. Xem các cổ phiếu thuộc cụm 0, ví dụ cụm công nghệ tăng trưởng
EXEC dbo.usp_GetStocksByCluster @ClusterId = 0;

-- 10.6. Gợi ý cổ phiếu tương tự FPT, tính trực tiếp từ PCA 3D
EXEC dbo.usp_GetStockRecommendations @Ticker = N'FPT', @TopN = 5;

-- 10.7. Xem recommendation đã lưu sẵn trong bảng Recommendations
SELECT *
FROM dbo.vw_RecommendationDetails
WHERE selected_ticker = N'FPT'
ORDER BY rank_order;
GO

/* =========================================================
   11. TEMPLATE IMPORT CSV TRONG SQL SERVER
   =========================================================

   Cách đơn giản nhất trong SSMS 22:
   1) Chuột phải database StockSimilarityRecommendationDB
   2) Tasks
   3) Import Flat File...
   4) Chọn file CSV
   5) Import vào bảng staging, ví dụ dbo.Staging_StockFeatures
   6) Sau đó dùng INSERT/MERGE để đẩy sang bảng chính.

   Ví dụ BULK INSERT, chỉ chạy sau khi sửa đúng đường dẫn file:

   BULK INSERT dbo.Staging_StockFeatures
   FROM 'C:\Data\stock_features.csv'
   WITH (
       FIRSTROW = 2,
       FIELDTERMINATOR = ',',
       ROWTERMINATOR = '0x0a',
       CODEPAGE = '65001',
       TABLOCK
   );

   BULK INSERT dbo.Staging_StockClusterResults
   FROM 'C:\Data\cluster_results.csv'
   WITH (
       FIRSTROW = 2,
       FIELDTERMINATOR = ',',
       ROWTERMINATOR = '0x0a',
       CODEPAGE = '65001',
       TABLOCK
   );

*/
