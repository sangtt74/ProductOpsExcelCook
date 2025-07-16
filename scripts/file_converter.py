# scripts/file_converter.py
import pandas as pd
import os
from pathlib import Path

def convert_file(uploaded_file, target_format, output_dir):
    """
    Chuyển đổi file được tải lên sang định dạng mục tiêu (CSV, Excel, TXT).

    Args:
        uploaded_file: Đối tượng file được tải lên từ Streamlit (File-like object).
        target_format (str): Định dạng đích ('csv', 'excel', 'txt').
        output_dir (Path): Thư mục để lưu file đầu ra.

    Returns:
        tuple: (Đường dẫn file đầu ra nếu thành công, DataFrame đã đọc).
               Trả về (None, None) nếu có lỗi.
    """
    try:
        # Bước 1: Đọc file đầu vào vào DataFrame
        file_extension = Path(uploaded_file.name).suffix.lower()
        base_name = Path(uploaded_file.name).stem

        df = None
        if file_extension == '.csv':
            df = pd.read_csv(uploaded_file)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(uploaded_file)
        elif file_extension == '.txt':
            # Đối với TXT, đọc dưới dạng CSV với dấu phân cách có thể tùy chỉnh
            # Mặc định thử đọc với tab, sau đó là space.
            # Trong ứng dụng thực tế, bạn có thể muốn hỏi người dùng dấu phân cách.
            try:
                df = pd.read_csv(uploaded_file, sep='\t', header=None) # Thử tab-separated
            except pd.errors.ParserError:
                uploaded_file.seek(0) # Reset con trỏ file
                df = pd.read_csv(uploaded_file, sep=' ', header=None) # Thử space-separated
            except Exception: # Nếu vẫn lỗi, thử đọc dưới dạng 1 cột
                uploaded_file.seek(0)
                df = pd.DataFrame([line.strip() for line in uploaded_file.readlines()], columns=['Content'])
        else:
            raise ValueError("Định dạng file đầu vào không được hỗ trợ. Vui lòng tải lên CSV, Excel hoặc TXT.")

        if df is None:
            raise ValueError("Không thể đọc file đầu vào vào DataFrame.")

        # Bước 2: Chuyển đổi và lưu file theo định dạng đích
        output_filename = f"{base_name}_converted.{target_format}"
        output_path = output_dir / output_filename

        if target_format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8')
        elif target_format == 'excel':
            df.to_excel(output_path, index=False, engine='openpyxl')
        elif target_format == 'txt':
            # Đối với TXT, lưu dưới dạng CSV tab-separated hoặc đơn giản là string
            df.to_csv(output_path, sep='\t', index=False, header=False, encoding='utf-8')
        else:
            raise ValueError("Định dạng file đầu ra không được hỗ trợ. Vui lòng chọn CSV, Excel hoặc TXT.")

        return output_path, df

    except Exception as e:
        print(f"Lỗi khi chuyển đổi file: {e}")
        return None, None