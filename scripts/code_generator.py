# scripts/code_generator.py
import random
import string
import csv
import os
import pandas as pd # Cần Pandas nếu hàm nào đó dùng nó (ví dụ: tạo DataFrame)
from pathlib import Path

def load_existing_codes(directory_to_check, prefix_to_match):
    """
    Loads all existing codes from CSV files in the specified directory
    that match the given prefix.
    """
    existing_codes = set()

    if not os.path.isdir(directory_to_check):
        # Trong môi trường script, bạn có thể in ra hoặc raise lỗi.
        # Với Streamlit, thông báo lỗi sẽ được xử lý ở main_app.py
        print(f"Warning: Directory not found: {directory_to_check}. Skipping existing code loading.")
        return existing_codes

    for filename in os.listdir(directory_to_check):
        if filename.endswith(".csv") and filename.upper().startswith(prefix_to_match.upper()):
            filepath = os.path.join(directory_to_check, filename)
            try:
                with open(filepath, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    header = next(reader, None) # Skip header if exists
                    for row in reader:
                        if row:
                            existing_codes.add(row[0])
            except Exception as e:
                print(f"Warning: Could not read existing codes from '{filename}': {e}")
    return existing_codes

def generate_random_code(prefix, num_codes, existing_codes_set, progress_callback=None):
    """
    Generates a list of unique codes with a given prefix, ensuring they are
    not present in the existing_codes_set.
    The total length of each code will be 16 characters.
    'progress_callback' is a function (e.g., from Streamlit) to update UI progress.
    """
    if not (3 <= len(prefix) <= 8):
        raise ValueError("Prefix must be between 3 and 8 characters long.")

    random_part_length = 16 - len(prefix)
    if random_part_length < 0:
        raise ValueError("Calculated random part length is negative. Prefix too long?")

    generated_codes_current_run = set()

    attempts = 0
    max_attempts = num_codes * 10 

    while len(generated_codes_current_run) < num_codes and attempts < max_attempts:
        rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random_part_length))
        full_code = prefix + rand_part

        if full_code not in existing_codes_set and full_code not in generated_codes_current_run:
            generated_codes_current_run.add(full_code)
        attempts += 1

        if progress_callback:
            progress = min(1.0, len(generated_codes_current_run) / num_codes)
            status_text = f"Generating codes: {len(generated_codes_current_run)} / {num_codes} (Attempts: {attempts})"
            progress_callback(progress, status_text)

    if len(generated_codes_current_run) < num_codes:
        print(f"Warning: Could only generate {len(generated_codes_current_run)} unique codes for prefix '{prefix}' after {max_attempts} attempts. "
              "This might indicate a high density of existing codes or too many requested codes for the available unique space.")

    return [[code] for code in list(generated_codes_current_run)]

def get_unique_filename(prefix, output_dir):
    """
    Generates a unique CSV filename based on the prefix within the specified output_dir.
    If 'prefix.csv' exists, it tries 'prefix_1.csv', 'prefix_2.csv', etc.
    """
    base_filename = f"{prefix}.csv"
    counter = 0
    filename = base_filename

    full_path = Path(output_dir) / filename

    while full_path.exists():
        counter += 1
        filename = f"{prefix}_{counter}.csv"
        full_path = Path(output_dir) / filename
    return full_path

# Bạn có thể thêm các hàm khác liên quan đến việc tạo mã ở đây