r"""
db_connection.py
Kết nối Python với Microsoft SQL Server / SQL Server Management Studio 22.

Mặc định dành cho máy cá nhân dùng SQL Server Express:
    SERVER   = .\SQLEXPRESS
    DATABASE = StockSimilarityRecommendationDB
    Login    = Windows Authentication

Có thể override bằng biến môi trường:
    SQL_SERVER=.\SQLEXPRESS
    SQL_DATABASE=StockSimilarityRecommendationDB
    SQL_DRIVER=ODBC Driver 18 for SQL Server
    SQL_TRUSTED_CONNECTION=yes
    SQL_USERNAME=sa
    SQL_PASSWORD=your_password
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional
from urllib.parse import quote_plus


DEFAULT_SERVER = r".\SQLEXPRESS"
DEFAULT_DATABASE = "StockSimilarityRecommendationDB"


@dataclass(frozen=True)
class SQLServerConfig:
    server: str = DEFAULT_SERVER
    database: str = DEFAULT_DATABASE
    driver: Optional[str] = None
    trusted_connection: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    trust_server_certificate: bool = True
    encrypt: Optional[str] = None


def _load_pyodbc():
    """Import pyodbc đúng lúc cần dùng để lỗi dễ hiểu hơn."""
    try:
        import pyodbc  # type: ignore
        return pyodbc
    except ImportError as exc:
        raise ImportError(
            "Chưa cài pyodbc. Hãy chạy: pip install pyodbc\n"
            "Nếu lỗi driver ODBC, hãy cài thêm Microsoft ODBC Driver 17 hoặc 18 for SQL Server."
        ) from exc


def available_drivers() -> list[str]:
    """Trả về danh sách ODBC drivers đang có trên máy."""
    pyodbc = _load_pyodbc()
    return list(pyodbc.drivers())


def pick_sql_driver(preferred: Optional[str] = None) -> str:
    """
    Tự chọn driver SQL Server.
    Ưu tiên ODBC Driver 18, sau đó 17, sau đó SQL Server Native Client/SQL Server.
    """
    drivers = available_drivers()

    if preferred:
        if preferred in drivers:
            return preferred
        raise RuntimeError(
            f"Không tìm thấy driver '{preferred}'. Driver hiện có: {drivers}.\n"
            "Cách sửa: đổi SQL_DRIVER trong môi trường hoặc cài Microsoft ODBC Driver 17/18."
        )

    candidates = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]
    for driver in candidates:
        if driver in drivers:
            return driver

    raise RuntimeError(
        "Không tìm thấy ODBC Driver cho SQL Server.\n"
        f"Driver hiện có: {drivers}\n"
        "Cách sửa: cài Microsoft ODBC Driver 17 hoặc 18 for SQL Server."
    )


def load_config_from_env() -> SQLServerConfig:
    """Đọc cấu hình kết nối từ biến môi trường, nếu không có thì dùng mặc định."""
    trusted_raw = os.getenv("SQL_TRUSTED_CONNECTION", "yes").strip().lower()
    trusted = trusted_raw in {"yes", "true", "1", "y"}

    return SQLServerConfig(
        server=os.getenv("SQL_SERVER", DEFAULT_SERVER),
        database=os.getenv("SQL_DATABASE", DEFAULT_DATABASE),
        driver=os.getenv("SQL_DRIVER") or None,
        trusted_connection=trusted,
        username=os.getenv("SQL_USERNAME") or None,
        password=os.getenv("SQL_PASSWORD") or None,
        trust_server_certificate=os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "yes").strip().lower() in {"yes", "true", "1", "y"},
        encrypt=os.getenv("SQL_ENCRYPT") or None,
    )


def build_connection_string(config: Optional[SQLServerConfig] = None, database: Optional[str] = None) -> str:
    """Tạo chuỗi kết nối pyodbc."""
    if config is None:
        config = load_config_from_env()

    driver = pick_sql_driver(config.driver)
    db_name = database or config.database

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={config.server}",
        f"DATABASE={db_name}",
    ]

    if config.trusted_connection:
        parts.append("Trusted_Connection=yes")
    else:
        if not config.username or not config.password:
            raise ValueError(
                "Bạn đang tắt Trusted_Connection nhưng chưa có SQL_USERNAME hoặc SQL_PASSWORD."
            )
        parts.append(f"UID={config.username}")
        parts.append(f"PWD={config.password}")

    if config.trust_server_certificate:
        parts.append("TrustServerCertificate=yes")
    if config.encrypt:
        parts.append(f"Encrypt={config.encrypt}")

    return ";".join(parts) + ";"


def get_connection(config: Optional[SQLServerConfig] = None, autocommit: bool = False, database: Optional[str] = None):
    """
    Mở kết nối pyodbc tới SQL Server.

    Ví dụ:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM dbo.Stocks", conn)
    """
    pyodbc = _load_pyodbc()
    conn_str = build_connection_string(config=config, database=database)
    return pyodbc.connect(conn_str, autocommit=autocommit)


@contextmanager
def sql_connection(config: Optional[SQLServerConfig] = None, autocommit: bool = False, database: Optional[str] = None) -> Iterator:
    """Context manager để tự đóng connection."""
    conn = get_connection(config=config, autocommit=autocommit, database=database)
    try:
        yield conn
    finally:
        conn.close()


def get_sqlalchemy_engine(config: Optional[SQLServerConfig] = None, database: Optional[str] = None):
    """
    Tạo SQLAlchemy engine, tiện cho pandas.to_sql/read_sql.
    File export chính dùng pyodbc trực tiếp, nhưng hàm này vẫn hữu ích khi bạn cần.
    """
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise ImportError("Chưa cài sqlalchemy. Hãy chạy: pip install sqlalchemy") from exc

    conn_str = build_connection_string(config=config, database=database)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(conn_str)}", fast_executemany=True)


def test_connection(config: Optional[SQLServerConfig] = None) -> dict:
    """Test kết nối và trả về thông tin database/server."""
    with sql_connection(config=config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                @@SERVERNAME AS server_name,
                DB_NAME() AS database_name,
                SUSER_SNAME() AS login_name,
                CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(100)) AS product_version;
            """
        )
        row = cursor.fetchone()
        return {
            "server_name": row.server_name,
            "database_name": row.database_name,
            "login_name": row.login_name,
            "product_version": row.product_version,
        }
