import streamlit as st
import pandas as pd
import os
import csv
from pathlib import Path
from io import BytesIO
import shutil # Import shutil for cleaning up temporary directories

# --- Import các hàm từ thư mục scripts ---
from scripts.code_generator import load_existing_codes, generate_random_code, get_unique_filename
from scripts.excel_processor import process_excel_for_codes
from scripts.file_converter import convert_file
from scripts.batch_processor import split_file_by_rows, convert_single_file, create_zip_archive

# --- Cấu hình trang Streamlit ---
st.set_page_config(
    page_title="Công cụ Xử lý Dữ liệu Tổng hợp",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Công cụ Xử lý Dữ liệu Tổng hợp")
st.write("Chào mừng bạn đến với công cụ mạnh mẽ để tạo sinh và xử lý file CSV/Excel/TXT của bạn!")

# --- Thiết lập thư mục đầu ra ---
OUTPUT_DIR = Path("processed_files_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Giao diện người dùng Streamlit ---

st.sidebar.header("Tùy chọn chung")

st.sidebar.markdown("**Thư mục để kiểm tra mã hiện có (cho chức năng tạo mã):**")
st.sidebar.info("Vui lòng dán đường dẫn tuyệt đối của thư mục chứa các file CSV có mã hiện có.")
directory_to_check = st.sidebar.text_input("Đường dẫn thư mục", value=os.getcwd(), help="Ví dụ: C:\\MyCodes hoặc /home/user/codes")

if st.sidebar.button("Kiểm tra thư mục"):
    if os.path.isdir(directory_to_check):
        st.sidebar.success(f"Thư mục đã chọn: `{directory_to_check}`")
    else:
        st.sidebar.error(f"Đường dẫn thư mục không hợp lệ: `{directory_to_check}`. Vui lòng kiểm tra lại.")

st.sidebar.markdown("---")
st.sidebar.header("Chọn chức năng")
function_choice = st.sidebar.radio(
    "Chọn một tác vụ:",
    [
        "Tạo Mã Thủ công",
        "Tạo Mã từ File Excel",
        "Đếm Dòng File",
        "Chuyển đổi Định dạng File",
        "Xử lý File Hàng loạt",
        "Thông tin"
    ]
)

# --- Chức năng Tạo Mã Thủ công ---
if function_choice == "Tạo Mã Thủ công":
    st.header("✨ Tạo Mã Thủ công")
    st.write("Nhập tiền tố và số lượng mã bạn muốn tạo.")

    prefix_manual = st.text_input("Nhập tiền tố (3-8 ký tự, chữ cái và số):").strip().upper()
    num_codes_manual = st.number_input("Số lượng mã cần tạo:", min_value=1, value=100, step=1)

    if st.button("Tạo Mã"):
        if not (3 <= len(prefix_manual) <= 8):
            st.error("Lỗi: Tiền tố phải dài từ 3 đến 8 ký tự.")
        elif num_codes_manual <= 0:
            st.error("Lỗi: Số lượng mã phải lớn hơn 0.")
        else:
            try:
                st.info(f"Đang tải mã hiện có từ `{directory_to_check}`...")
                existing_codes_set = load_existing_codes(directory_to_check, prefix_manual)
                st.info(f"Tìm thấy {len(existing_codes_set)} mã hiện có trong thư mục đã chọn cho tiền tố '{prefix_manual}'.")
                
                # Tạo thanh tiến trình và status text cho hàm generate_random_code
                progress_bar = st.progress(0)
                status_text = st.empty()
                def update_progress(progress, text):
                    progress_bar.progress(progress)
                    status_text.text(text)

                codes_to_write = generate_random_code(prefix_manual, num_codes_manual, existing_codes_set, update_progress)

                if codes_to_write:
                    output_file_path = get_unique_filename(prefix_manual, OUTPUT_DIR)
                    
                    with open(output_file_path, mode="w", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        writer.writerow(["code"])
                        writer.writerows(codes_to_write)
                    
                    st.success(f"Đã tạo {len(codes_to_write)} mã mới và lưu vào: `{output_file_path.name}` trong thư mục `{OUTPUT_DIR}`.")
                    st.write(f"Ví dụ mã: **{codes_to_write[0][0]}** (Độ dài: {len(codes_to_write[0][0])})")

                    generated_df = pd.DataFrame(codes_to_write, columns=["code"])
                    st.dataframe(generated_df.head(10))

                    st.download_button(
                        label=f"Tải xuống {output_file_path.name}",
                        data=generated_df.to_csv(index=False).encode('utf-8'),
                        file_name=output_file_path.name,
                        mime="text/csv"
                    )
                else:
                    st.warning("Không thể tạo thêm mã duy nhất nào dựa trên yêu cầu và các mã hiện có.")
            except ValueError as e:
                st.error(f"Lỗi: {e}")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi không mong muốn: {e}")

# --- Chức năng Tạo Mã từ File Excel ---
elif function_choice == "Tạo Mã từ File Excel":
    st.header("📝 Tạo Mã từ File Excel")
    st.write("Tải lên một file Excel (dạng .xlsx hoặc .xls) có cấu trúc:")
    st.markdown("- **Cột A**: Tiền tố (Prefix, 3-8 ký tự)")
    st.markdown("- **Cột B**: Số lượng mã cần tạo (Quantity)")

    uploaded_excel_file = st.file_uploader("Tải lên file Excel của bạn", type=["xlsx", "xls"])

    if uploaded_excel_file is not None:
        if st.button("Tạo Mã từ Excel"):
            try:
                excel_progress_bar = st.progress(0)
                excel_status_text = st.empty()
                def update_excel_progress(progress, text):
                    excel_progress_bar.progress(progress)
                    excel_status_text.text(text)

                generated_file_paths, rows_processed = process_excel_for_codes(
                    uploaded_excel_file,
                    directory_to_check,
                    OUTPUT_DIR,
                    update_excel_progress
                )
                
                excel_progress_bar.empty()
                excel_status_text.empty()

                if rows_processed > 0:
                    st.success(f"\n✅ Đã xử lý thành công {rows_processed} hàng từ file Excel '{uploaded_excel_file.name}'.")
                    st.write("Các file đã tạo:")
                    for fname_path in generated_file_paths:
                        st.markdown(f"- `{fname_path.name}`")
                    
                    st.write(f"Tất cả các file đã tạo được lưu trong thư mục: `{OUTPUT_DIR}`")
                else:
                    st.warning("Không có hàng hợp lệ nào được xử lý từ file Excel. Vui lòng kiểm tra dữ liệu đầu vào của bạn.")

            except Exception as e:
                st.error(f"Lỗi khi tải hoặc xử lý file Excel: {e}. Đảm bảo đây là file Excel hợp lệ.")
    else:
        st.info("Vui lòng tải lên một file Excel để bắt đầu.")

# --- Chức năng Đếm Dòng File ---
elif function_choice == "Đếm Dòng File":
    st.header("🔢 Đếm Dòng File CSV/Excel")
    st.write("Tải lên một file CSV hoặc Excel để đếm tổng số dòng dữ liệu.")

    uploaded_file_to_count = st.file_uploader("Tải lên file của bạn", type=["csv", "xlsx", "xls"])

    if uploaded_file_to_count is not None:
        if st.button("Đếm Dòng"):
            st.info(f"Đang đếm dòng cho file: {uploaded_file_to_count.name}...")
            try:
                file_extension = Path(uploaded_file_to_count.name).suffix.lower()

                if file_extension == '.csv':
                    df = pd.read_csv(uploaded_file_to_count)
                elif file_extension in ['.xlsx', '.xls']:
                    df = pd.read_excel(uploaded_file_to_count)
                else:
                    st.error("Loại file không được hỗ trợ. Chỉ chấp nhận CSV và Excel.")
                    st.stop()

                num_rows = len(df)
                st.success(f"File '{uploaded_file_to_count.name}' có **{num_rows}** dòng dữ liệu (không bao gồm tiêu đề nếu có).")
                st.write("5 dòng đầu tiên:")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Lỗi khi đếm dòng hoặc đọc file '{uploaded_file_to_count.name}': {e}")
    else:
        st.info("Vui lòng tải lên một file CSV hoặc Excel.")

# --- Chức năng Chuyển đổi Định dạng File ---
elif function_choice == "Chuyển đổi Định dạng File":
    st.header("🔄 Chuyển đổi Định dạng File")
    st.write("Chuyển đổi file của bạn giữa các định dạng CSV, Excel (.xlsx) và TXT.")

    uploaded_file_convert = st.file_uploader("Tải lên file cần chuyển đổi (.csv, .xlsx, .xls, .txt)", type=["csv", "xlsx", "xls", "txt"])

    if uploaded_file_convert is not None:
        st.write("Chọn định dạng đầu ra:")
        target_format = st.radio(
            "Chuyển đổi sang:",
            ('csv', 'excel', 'txt'),
            key="target_format_radio"
        )

        if st.button("Chuyển đổi"):
            with st.spinner(f"Đang chuyển đổi '{uploaded_file_convert.name}' sang {target_format.upper()}..."):
                output_path, result_df = convert_file(uploaded_file_convert, target_format, OUTPUT_DIR)

                if output_path and result_df is not None:
                    st.success(f"Đã chuyển đổi thành công! File đã lưu tại: `{output_path.name}` trong thư mục `{OUTPUT_DIR}`.")
                    st.write("Xem trước 5 dòng đầu tiên của file đã chuyển đổi:")
                    st.dataframe(result_df.head())

                    # Chuẩn bị dữ liệu cho nút tải xuống dựa trên định dạng đích
                    download_data = None
                    mime_type = ""
                    if target_format == 'csv':
                        download_data = result_df.to_csv(index=False, encoding='utf-8').encode('utf-8')
                        mime_type = "text/csv"
                    elif target_format == 'excel':
                        # Dùng BytesIO để tạo file Excel trong bộ nhớ
                        excel_buffer = BytesIO()
                        result_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                        download_data = excel_buffer.getvalue()
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    elif target_format == 'txt':
                        download_data = result_df.to_csv(sep='\t', index=False, header=False, encoding='utf-8').encode('utf-8')
                        mime_type = "text/plain"

                    if download_data:
                        st.download_button(
                            label=f"Tải xuống {output_path.name}",
                            data=download_data,
                            file_name=output_path.name,
                            mime=mime_type,
                        )
                else:
                    st.error("Không thể hoàn tất quá trình chuyển đổi. Vui lòng kiểm tra file đầu vào và định dạng.")
    else:
        st.info("Vui lòng tải lên một file để bắt đầu chuyển đổi.")

# --- Chức năng Xử lý File Hàng loạt ---
elif function_choice == "Xử lý File Hàng loạt":
    st.header("📦 Xử lý File Hàng loạt (Batch File Processor)")
    st.write("Chọn các file đầu vào, định dạng chuyển đổi, và các tùy chọn xử lý.")

    # Tạo thư mục tạm thời cho các file đã upload và đã xử lý trong phiên này
    temp_upload_dir = OUTPUT_DIR / "temp_uploads"
    temp_processed_dir = OUTPUT_DIR / "temp_processed"
    temp_upload_dir.mkdir(exist_ok=True)
    temp_processed_dir.mkdir(exist_ok=True)

    st.subheader("1. Tải lên File Đầu vào")
    uploaded_files = st.file_uploader(
        "Chọn các file (.txt, .csv, .xlsx, .xls) bạn muốn xử lý:",
        type=["txt", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Bạn có thể chọn nhiều file cùng lúc."
    )

    st.subheader("2. Cấu hình Chuyển đổi và Xử lý")
    col1, col2 = st.columns(2)
    with col1:
        input_format_select = st.selectbox(
            "Định dạng của file đầu vào (tất cả file tải lên phải cùng định dạng này):",
            ("txt", "csv", "xlsx"),
            help="Chọn định dạng chung của các file bạn đã tải lên."
        )
    with col2:
        output_format_select = st.selectbox(
            "Chuyển đổi sang định dạng:",
            ("csv", "xlsx", "txt"),
            help="Chọn định dạng mà bạn muốn chuyển đổi các file sang."
        )

    st.markdown("---")
    st.subheader("3. Tùy chọn Tách File (Nếu có)")
    
    # Dictionary to store split configurations for each uploaded file
    if 'split_configs' not in st.session_state:
        st.session_state.split_configs = {}

    if uploaded_files:
        st.info("Để tách file, hãy chọn file và nhập số dòng/hàng cần giữ cùng hậu tố tùy chỉnh.")
        
        for uploaded_file in uploaded_files:
            file_key = f"split_config_{uploaded_file.name}"
            
            with st.expander(f"Cấu hình tách cho file: **{uploaded_file.name}** ({Path(uploaded_file.name).suffix.upper()})"):
                if file_key not in st.session_state.split_configs:
                    st.session_state.split_configs[file_key] = {
                        'do_split': False,
                        'lines_to_keep': 100,
                        'suffix': "(1)"
                    }
                
                current_config = st.session_state.split_configs[file_key]

                do_split = st.checkbox(
                    f"Kích hoạt tách cho '{uploaded_file.name}'",
                    value=current_config['do_split'],
                    key=f"checkbox_{file_key}"
                )
                st.session_state.split_configs[file_key]['do_split'] = do_split

                if do_split:
                    lines_to_keep = st.number_input(
                        f"Số dòng/hàng để giữ trong '{uploaded_file.name}' (phần gốc):",
                        min_value=1,
                        value=current_config['lines_to_keep'],
                        key=f"lines_{file_key}"
                    )
                    st.session_state.split_configs[file_key]['lines_to_keep'] = lines_to_keep
                    
                    suffix_input = st.text_input(
                        f"Hậu tố cho file tách mới của '{uploaded_file.name}' (vd: (1)):",
                        value=current_config['suffix'],
                        key=f"suffix_{file_key}"
                    )
                    st.session_state.split_configs[file_key]['suffix'] = suffix_input
                else:
                    st.session_state.split_configs[file_key]['lines_to_keep'] = 100
                    st.session_state.split_configs[file_key]['suffix'] = "(1)"
    else:
        st.info("Vui lòng tải lên file để cấu hình tùy chọn tách.")

    st.markdown("---")
    st.subheader("4. Bắt đầu Xử lý")

    if st.button("Bắt đầu Xử lý File Hàng loạt", key="start_batch_process"):
        if not uploaded_files:
            st.warning("Vui lòng tải lên ít nhất một file để bắt đầu xử lý.")
        else:
            processed_files_info = []
            total_files = len(uploaded_files)
            current_file_idx = 0

            # Clear previous temporary files from these session-specific directories
            if temp_upload_dir.exists():
                for f in temp_upload_dir.iterdir(): os.remove(f)
            if temp_processed_dir.exists():
                for f in temp_processed_dir.iterdir(): os.remove(f)

            process_progress_bar = st.progress(0)
            process_status_text = st.empty()

            for uploaded_file in uploaded_files:
                current_file_idx += 1
                process_progress_bar.progress(current_file_idx / total_files)
                process_status_text.text(f"Đang xử lý file: {uploaded_file.name} ({current_file_idx}/{total_files})")

                # Get the split configuration for this specific file
                file_key = f"split_config_{uploaded_file.name}"
                config_for_this_file = st.session_state.split_configs.get(file_key, {})
                do_split_this_file = config_for_this_file.get('do_split', False)
                lines_to_keep_this_file = config_for_this_file.get('lines_to_keep', 100)
                suffix_this_file = config_for_this_file.get('suffix', "(1)")

                # Write uploaded file to a temporary location to be able to read multiple times if needed
                temp_input_file_path = temp_upload_dir / uploaded_file.name
                with open(temp_input_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                files_after_split = []

                # --- Step A: Split file if requested ---
                if do_split_this_file:
                    st.info(f"Đang tách file: {uploaded_file.name} với {lines_to_keep_this_file} dòng/hàng và hậu tố '{suffix_this_file}'...")
                    
                    with open(temp_input_file_path, "rb") as f_temp_read:
                        split_original_part, split_new_part = split_file_by_rows(
                            BytesIO(f_temp_read.read()),
                            lines_to_keep_this_file,
                            temp_processed_dir,
                            uploaded_file.name,
                            suffix_this_file
                        )
                    if split_original_part and split_new_part:
                        st.success(f"Đã tách '{uploaded_file.name}'. Phần gốc: {split_original_part.name}, Phần mới: {split_new_part.name}")
                        files_after_split.append(split_original_part)
                        files_after_split.append(split_new_part)
                    else:
                        st.error(f"Không thể tách file '{uploaded_file.name}'. Bỏ qua chuyển đổi cho file này.")
                else:
                    files_after_split = [temp_input_file_path] 

                # --- Step B: Convert each (or split) file ---
                for file_for_conversion_path in files_after_split:
                    if not file_for_conversion_path.exists():
                        st.warning(f"File {file_for_conversion_path.name} không tồn tại sau khi tách/tải lên. Bỏ qua.")
                        continue

                    # Determine actual input format based on file extension for conversion
                    actual_input_format = Path(file_for_conversion_path.name).suffix.lower().replace('.', '')
                    if actual_input_format == 'xls':
                        actual_input_format = 'xlsx'

                    st.info(f"Đang chuyển đổi '{file_for_conversion_path.name}' từ .{actual_input_format} sang .{output_format_select}...")
                    
                    with open(file_for_conversion_path, "rb") as f_read_for_convert:
                        converted_filepath, converted_df = convert_single_file(
                            BytesIO(f_read_for_convert.read()),
                            actual_input_format,
                            output_format_select,
                            temp_processed_dir,
                            file_for_conversion_path.name
                        )

                    if converted_filepath:
                        st.success(f"Đã chuyển đổi thành công '{file_for_conversion_path.name}' sang '{converted_filepath.name}'.")
                        processed_files_info.append(converted_filepath)
                    else:
                        st.error(f"Không thể chuyển đổi '{file_for_conversion_path.name}'.")

            process_progress_bar.empty()
            process_status_text.empty()

            if processed_files_info:
                st.subheader("5. Hoàn tất & Tải xuống")
                st.success(f"Đã xử lý xong {len(processed_files_info)} file. Các file đầu ra được lưu tạm thời.")
                
                st.write("Các file đã tạo:")
                for p_file in processed_files_info:
                    st.markdown(f"- `{p_file.name}`")

                # Tạo file ZIP của tất cả các file đã xử lý
                zip_file_name = f"processed_files_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
                zip_output_path = OUTPUT_DIR / zip_file_name
                
                st.info("Đang nén các file đầu ra thành một file ZIP...")
                final_zip_path = create_zip_archive(temp_processed_dir, zip_output_path)

                if final_zip_path:
                    st.success(f"Đã tạo file ZIP thành công: `{final_zip_path.name}`.")
                    with open(final_zip_path, "rb") as f:
                        st.download_button(
                            label="Tải xuống tất cả file (ZIP)",
                            data=f.read(),
                            file_name=final_zip_path.name,
                            mime="application/zip",
                            help="Tải xuống một file ZIP chứa tất cả các file đã xử lý."
                        )
                else:
                    st.error("Không thể tạo file ZIP chứa các file đã xử lý.")
            else:
                st.warning("Không có file nào được xử lý thành công.")

            # Cleanup temporary directories after processing
            if temp_upload_dir.exists():
                shutil.rmtree(temp_upload_dir)
            if temp_processed_dir.exists():
                shutil.rmtree(temp_processed_dir)

# --- Chức năng Thông tin ---
elif function_choice == "Thông tin":
    st.header("ℹ️ Thông tin Ứng dụng")
    st.write("""
    Đây là một công cụ giúp bạn **tạo Code Riêng** với prefix tùy chỉnh,
    **đếm dòng** trong file, **chuyển đổi định dạng** giữa CSV, Excel, TXT,
    và thực hiện **xử lý file hàng loạt** bao gồm **tách file theo dòng/hàng** và nén file.
    """)
    st.write("Ứng dụng này được tổ chức với các module logic trong thư mục `scripts/` để dễ dàng bảo trì và mở rộng.")

st.markdown("---")
st.markdown("Phát triển bởi Gemini & SangTT6 với Streamlit & Pandas. Ngày: " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))