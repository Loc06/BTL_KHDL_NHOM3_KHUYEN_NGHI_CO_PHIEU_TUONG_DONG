"""
test_sql_connection.py
Test nhanh kết nối Python -> SQL Server.

Chạy:
    python test_sql_connection.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from db_connection import available_drivers, test_connection  # noqa: E402


if __name__ == "__main__":
    print("ODBC drivers đang có:")
    for driver in available_drivers():
        print("-", driver)

    print("\nĐang test kết nối SQL Server...")
    info = test_connection()
    print("Kết nối thành công!")
    for key, value in info.items():
        print(f"{key}: {value}")
