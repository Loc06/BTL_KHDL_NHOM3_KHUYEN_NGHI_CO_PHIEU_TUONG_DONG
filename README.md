<h1 align="center">📈 Hệ Thống Khuyến Nghị Cổ Phiếu Tương Đồng</h1>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white" alt="Scikit-learn">
  <img src="https://img.shields.io/badge/Jupyter-F37626.svg?&style=flat&logo=Jupyter&logoColor=white" alt="Jupyter Notebook">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>
## 📖 Giới thiệu Tổng quan (Introduction)
Chào mừng bạn đến với dự án **Hệ thống Khuyến nghị Cổ phiếu Tương đồng (Stock Similarity Recommendation)**. Đây là bài tập lớn thuộc môn học **Khoa học Dữ liệu (Data Science)**.
Thị trường chứng khoán luôn biến động và chứa đựng lượng dữ liệu khổng lồ. Việc tìm kiếm các mã cổ phiếu có tiềm năng hoặc có hành vi giá tương tự nhau để đa dạng hóa danh mục đầu tư là một thách thức lớn đối với các nhà đầu tư. Dự án này cung cấp một giải pháp dựa trên dữ liệu bằng cách ứng dụng các kỹ thuật **Học máy Không giám sát (Unsupervised Machine Learning)**. Thông qua việc phân tích các chỉ số tài chính và lịch sử giao dịch, hệ thống sẽ tự động phân cụm và đề xuất các nhóm cổ phiếu có đặc tính tương đồng, giúp hỗ trợ quá trình ra quyết định đầu tư một cách trực quan và khoa học.
## ✨ Các Tính năng Chính (Key Features)
- **Tiền xử lý Dữ liệu Chuẩn xác:** Tự động làm sạch dữ liệu, xử lý các giá trị khuyết thiếu và chuẩn hóa các chỉ số tài chính của cổ phiếu.
- **Giảm chiều Dữ liệu (Dimensionality Reduction):** Giữ lại các đặc trưng quan trọng nhất của tập dữ liệu khổng lồ nhằm tối ưu hóa quá trình tính toán và trực quan hóa.
- **Phân cụm Thông minh (Clustering):** Gom nhóm các mã cổ phiếu có hành vi tương đồng trên thị trường dựa trên các thuật toán học máy.
- **Trực quan hóa Sinh động:** Cung cấp các biểu đồ biểu diễn không gian phân cụm, giúp người dùng dễ dàng theo dõi và đánh giá kết quả.
- **Khuyến nghị Tự động:** Đề xuất danh sách các cổ phiếu tương đồng khi người dùng truy vấn một mã cổ phiếu bất kỳ.
## 🧠 Kiến trúc Thuật toán (Methodology)
Hệ thống được xây dựng dựa trên sự kết hợp của hai kỹ thuật cốt lõi trong phân tích dữ liệu:
1. **Phân tích Thành phần Chính (PCA - Principal Component Analysis):**
   Do dữ liệu chứng khoán thường có số chiều lớn (nhiều chỉ số tài chính, kỹ thuật khác nhau), thuật toán PCA được áp dụng để giảm số lượng đặc trưng mà vẫn bảo toàn tối đa lượng thông tin (phương sai) của dữ liệu gốc. Bước này giúp loại bỏ hiện tượng đa cộng tuyến, giảm nhiễu và tăng tốc độ cho thuật toán phân cụm phía sau.
2. **Phân cụm K-Means (K-Means Clustering):**
   Sau khi dữ liệu được giảm chiều, thuật toán K-Means được sử dụng để phân chia các cổ phiếu thành $K$ cụm khác biệt. Các cổ phiếu trong cùng một cụm sẽ có khoảng cách tới tâm cụm (centroid) gần nhất, đồng nghĩa với việc chúng có mức độ tương đồng cao về các chỉ số tài chính hoặc biến động giá. Số lượng cụm $K$ tối ưu có thể được xác định thông qua phương pháp Elbow (Elbow Method) hoặc hệ số Silhouette (Silhouette Score).
## 💻 Công nghệ và Thư viện Sử dụng
- **Ngôn ngữ:** Python
- **Thao tác Dữ liệu:** Pandas, NumPy
- **Học máy:** Scikit-learn
- **Trực quan hóa:** Matplotlib, Seaborn
- **Môi trường Phát triển:** Jupyter Notebook
## ⚙️ Cài đặt Môi trường (Installation)
Để triển khai dự án trên máy tính cá nhân, vui lòng thực hiện các bước sau:
1. **Clone repository về máy:**
   ```bash
   git clone https://github.com/your-username/stock-similarity-recommendation.git
   cd stock-similarity-recommendation
   ```
2. **Tạo môi trường ảo (Khuyến nghị):**
   ```bash
   # Sử dụng venv
   python -m venv venv
   
   # Kích hoạt môi trường ảo
   # Trên Windows:
   venv\Scripts\activate
   # Trên macOS/Linux:
   source venv/bin/activate
   ```
3. **Cài đặt các thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```
## 🚀 Hướng dẫn Sử dụng (Usage)
Sau khi cài đặt xong môi trường, bạn có thể chạy dự án theo cách sau:
- **Chạy bằng Jupyter Notebook:**
  Mở terminal tại thư mục gốc của dự án và khởi động Jupyter Notebook:
  ```bash
  jupyter notebook
  ```
  Truy cập vào file `notebooks/analysis.ipynb` (hoặc tên file notebook tương ứng của bạn) và chạy tuần tự các cell để xem quá trình phân tích và kết quả.
- **Chạy bằng Python Script (Nếu có):**
  ```bash
  python main.py
  ```
## 📂 Cấu trúc Thư mục (Directory Structure)
```text
stock-similarity-recommendation/
│
├── data/                   # Thư mục chứa dữ liệu thô và dữ liệu đã qua xử lý
│   ├── raw/                # Dữ liệu gốc
│   └── processed/          # Dữ liệu sau tiền xử lý
│
├── notebooks/              # Các file Jupyter Notebook để EDA và thử nghiệm
│   └── analysis.ipynb
│
├── src/                    # Mã nguồn chính của dự án
│   ├── data_loader.py      # Script tải và đọc dữ liệu
│   ├── preprocessing.py    # Script làm sạch và chuẩn hóa dữ liệu
│   ├── model.py            # Định nghĩa mô hình PCA và K-Means
│   └── visualization.py    # Các hàm vẽ biểu đồ
│
├── requirements.txt        # Danh sách các thư viện cần thiết
├── README.md               # Tài liệu mô tả dự án
└── main.py                 # Script thực thi toàn bộ luồng chương trình
```
## 📊 Kết quả Đạt được (Results/Visualizations)
*(Placeholder: Hình ảnh hoặc bảng kết quả sẽ được cập nhật tại đây)*
**1. Biểu đồ xác định số cụm tối ưu (Elbow Method):**
<!-- Thay thế bằng link ảnh thực tế -->
> `![Biểu đồ Elbow](link_to_image)`
**2. Không gian phân cụm cổ phiếu (PCA 2D/3D Scatter Plot):**
<!-- Thay thế bằng link ảnh thực tế -->
> `![Biểu đồ phân cụm](link_to_image)`
**3. Ví dụ danh sách cổ phiếu tương đồng:**
> *Khi truy vấn mã ABC, hệ thống khuyến nghị các mã cùng cụm: XYZ, MNP...*
