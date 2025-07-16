# scripts/batch_processor.py (Đã sửa đổi hàm split_file_by_rows để hỗ trợ nhiều định dạng)
import pandas as pd
import os
import shutil
from pathlib import Path
from io import BytesIO

def split_file_by_rows(uploaded_file_stream, lines_to_keep, output_dir, original_filename, suffix="(1)"):
    """
    Splits a file (TXT, CSV, Excel) into two parts based on a specified row/line number.

    The first part retains the original filename (without suffix), and the second part
    is saved with a new filename containing a suffix.

    Args:
        uploaded_file_stream: Streamlit UploadedFile object (BytesIO stream).
        lines_to_keep (int): The number of lines/rows to keep in the first part.
        output_dir (Path): The directory to save the split files.
        original_filename (str): The original name of the uploaded file.
        suffix (str): The suffix to add to the new split file's name (e.g., "(1)").

    Returns:
        tuple: (path_to_original_part_file, path_to_split_part_file) if successful, else (None, None).
    """
    try:
        uploaded_file_stream.seek(0) # Ensure cursor is at the beginning
        file_extension = Path(original_filename).suffix.lower()

        df = None
        # Read file based on its extension
        if file_extension == '.txt':
            lines = [line.decode('utf-8').strip() for line in uploaded_file_stream.readlines()]
            lines = [line for line in lines if line] # Remove empty strings
            if not lines:
                raise ValueError("File trống hoặc không có dòng dữ liệu hợp lệ để tách.")

            total_rows = len(lines)
            if lines_to_keep >= total_rows or lines_to_keep <= 0:
                raise ValueError(f"Số dòng cần giữ ({lines_to_keep}) không hợp lệ. Phải lớn hơn 0 và nhỏ hơn tổng số dòng ({total_rows}).")

            original_content = '\n'.join(lines[:lines_to_keep])
            split_content = '\n'.join(lines[lines_to_keep:])

        elif file_extension == '.csv':
            df = pd.read_csv(uploaded_file_stream)
            total_rows = len(df)
            if lines_to_keep >= total_rows or lines_to_keep <= 0:
                raise ValueError(f"Số hàng cần giữ ({lines_to_keep}) không hợp lệ. Phải lớn hơn 0 và nhỏ hơn tổng số hàng ({total_rows}).")

            df_original = df.iloc[:lines_to_keep]
            df_split = df.iloc[lines_to_keep:]

        elif file_extension in ['.xlsx', '.xls']:
            # Read only the first sheet for simplicity. If multiple sheets need splitting,
            # this logic would become more complex (e.g., looping through sheets).
            df = pd.read_excel(uploaded_file_stream, engine='openpyxl')
            total_rows = len(df)
            if lines_to_keep >= total_rows or lines_to_keep <= 0:
                raise ValueError(f"Số hàng cần giữ ({lines_to_keep}) không hợp lệ. Phải lớn hơn 0 và nhỏ hơn tổng số hàng ({total_rows}).")

            df_original = df.iloc[:lines_to_keep]
            df_split = df.iloc[lines_to_keep:]

        else:
            raise ValueError(f"Định dạng file '{file_extension}' không được hỗ trợ để tách.")

        # Construct output file paths
        base_name, ext = os.path.splitext(original_filename)
        original_part_path = output_dir / f"{base_name}{ext}" # Retains original name
        split_part_path = output_dir / f"{base_name} {suffix}{ext}" # Adds suffix

        # Save the split parts back to files
        if file_extension == '.txt':
            with open(original_part_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            with open(split_part_path, 'w', encoding='utf-8') as f:
                f.write(split_content)
        elif file_extension == '.csv':
            df_original.to_csv(original_part_path, index=False, encoding='utf-8')
            df_split.to_csv(split_part_path, index=False, encoding='utf-8')
        elif file_extension in ['.xlsx', '.xls']:
            df_original.to_excel(original_part_path, index=False, engine='openpyxl')
            df_split.to_excel(split_part_path, index=False, engine='openpyxl')

        return original_part_path, split_part_path

    except ValueError as ve:
        print(f"Lỗi logic khi tách file '{original_filename}': {ve}")
        return None, None
    except Exception as e:
        print(f"Đã xảy ra lỗi khi tách file '{original_filename}': {e}")
        return None, None

# Giữ nguyên các hàm convert_single_file và create_zip_archive
def convert_single_file(uploaded_file_stream, input_format, output_format, output_dir, original_filename):
    # ... (Nội dung hàm này giữ nguyên như trước) ...
    df = None
    try:
        uploaded_file_stream.seek(0) # Reset stream position

        # Read input file into DataFrame
        if input_format == 'csv':
            df = pd.read_csv(uploaded_file_stream)
        elif input_format in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file_stream, engine='openpyxl')
        elif input_format == 'txt':
            # Attempt to read TXT assuming tab-separated, then space-separated, then single column
            try:
                df = pd.read_csv(uploaded_file_stream, sep='\t', header=None, encoding='utf-8')
            except pd.errors.ParserError:
                uploaded_file_stream.seek(0)
                try:
                    df = pd.read_csv(uploaded_file_stream, sep=' ', header=None, encoding='utf-8')
                except pd.errors.ParserError:
                    uploaded_file_stream.seek(0)
                    df = pd.DataFrame([line.decode('utf-8').strip() for line in uploaded_file_stream.readlines()], columns=['Content'])
            except Exception: # Fallback for other issues, read as single column
                uploaded_file_stream.seek(0)
                df = pd.DataFrame([line.decode('utf-8').strip() for line in uploaded_file_stream.readlines()], columns=['Content'])
        else:
            raise ValueError(f"Định dạng đầu vào '{input_format}' không được hỗ trợ.")

        if df is None:
            raise ValueError("Không thể đọc file đầu vào vào DataFrame.")

        # Prepare output path
        base_name = Path(original_filename).stem
        output_filepath = output_dir / f"{base_name}_converted.{output_format}"

        # Write DataFrame to output format
        if output_format == 'csv':
            df.to_csv(output_filepath, index=False, encoding='utf-8')
        elif output_format == 'xlsx':
            df.to_excel(output_filepath, index=False, engine='openpyxl')
        elif output_format == 'txt':
            # For TXT output, write as tab-separated without header/index
            df.to_csv(output_filepath, sep='\t', index=False, header=False, encoding='utf-8')
        else:
            raise ValueError(f"Định dạng đầu ra '{output_format}' không được hỗ trợ.")

        return output_filepath, df

    except Exception as e:
        print(f"Lỗi khi chuyển đổi file '{original_filename}': {e}")
        return None, None

def create_zip_archive(source_dir, output_zip_path_without_ext):
    # ... (Nội dung hàm này giữ nguyên như trước) ...
    try:
        shutil.make_archive(output_zip_path_without_ext, 'zip', source_dir)
        return Path(str(output_zip_path_without_ext) + '.zip')
    except Exception as e:
        print(f"Lỗi khi tạo file zip từ '{source_dir}': {e}")
        return None