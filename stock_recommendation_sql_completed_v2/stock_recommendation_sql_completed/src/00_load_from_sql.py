"""
00_load_from_sql.py
Tùy chọn: đọc feature từ SQL Server và xuất thành CSV raw để pipeline Python dùng.

Chạy:
    python src/00_load_from_sql.py

Output:
    data/raw/vn100_from_sql.csv

Muốn dùng file này thay cho data/raw/vn100.csv thì có 2 cách:
    Cách 1: đổi RAW_FILE trong src/config.py thành DATA_RAW / "vn100_from_sql.csv"
    Cách 2: copy/rename vn100_from_sql.csv thành vn100.csv
"""
from sql_server_io import export_sql_features_to_raw_csv, load_latest_features_from_sql


if __name__ == "__main__":
    df = load_latest_features_from_sql()
    print("Đọc dữ liệu từ SQL thành công. Shape:", df.shape)
    print(df.head().to_string(index=False))

    out = export_sql_features_to_raw_csv()
    print("Đã xuất CSV raw từ SQL:", out)
