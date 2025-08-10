import streamlit as st
from PIL import Image
import io
import os
import zipfile
import tempfile
import shutil
from pathlib import Path

# --- UI Config ---
st.set_page_config(page_title="Advanced Image Compressor", layout="centered")

# --- Style Toggle ---
theme = st.selectbox("Choose Theme", ["Light", "Dark"])
if theme == "Dark":
    st.markdown("""
        <style>
            body, .stApp {
                background-color: #111;
                color: #EEE;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Constants ---
DEFAULT_MAX_KB = 500

# --- Compression Function ---
def compress_image(img, format, target_size_kb):
    quality = 95
    img_bytes = io.BytesIO()
    original_size = img.size

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    while quality > 5:
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
        size_kb = img_bytes.tell() / 1024
        if size_kb <= target_size_kb:
            break
        quality -= 5

    if size_kb > target_size_kb:
        width, height = img.size
        while size_kb > target_size_kb and width > 200 and height > 200:
            width = int(width * 0.9)
            height = int(height * 0.9)
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
            size_kb = img_bytes.tell() / 1024

    img_bytes.seek(0)
    return img_bytes, size_kb, img.size, original_size

# --- Single Image ---
def process_single_image(uploaded_file, target_size_kb):
    image = Image.open(uploaded_file)
    format = image.format
    compressed_bytes, compressed_size, compressed_dims, original_dims = compress_image(image, format, target_size_kb)
    return {
        "filename": uploaded_file.name,
        "data": compressed_bytes,
        "original_size": uploaded_file.size / 1024,
        "compressed_size": compressed_size,
        "original_dims": original_dims,
        "compressed_dims": compressed_dims
    }

# --- ZIP Image Folder ---
def process_zip(uploaded_zip, target_size_kb):
    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    individual_files = []

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "uploaded.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        output_dir = os.path.join(temp_dir, "compressed")
        os.makedirs(output_dir, exist_ok=True)

        all_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    all_files.append(os.path.join(root, file))

        progress = st.progress(0)
        for i, full_path in enumerate(all_files):
            try:
                relative_path = os.path.relpath(full_path, temp_dir)
                out_path = os.path.join(output_dir, relative_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                img = Image.open(full_path)
                format = img.format
                compressed, size_kb, comp_dims, orig_dims = compress_image(img, format, target_size_kb)

                with open(out_path, "wb") as f:
                    f.write(compressed.read())

                individual_files.append({
                    "name": Path(relative_path).name,
                    "data": compressed,
                    "compressed_size": size_kb,
                    "original_size": os.path.getsize(full_path) / 1024,
                    "original_dims": orig_dims,
                    "compressed_dims": comp_dims
                })

            except Exception as e:
                print(f"Error compressing {full_path}: {e}")

            progress.progress((i + 1) / len(all_files))

        shutil.make_archive(temp_zip_file.name.replace(".zip", ""), 'zip', output_dir)
        return temp_zip_file.name, individual_files

# --- UI ---
st.title("📸 Advanced Image Compressor - Under Custom KB")
upload_type = st.selectbox("Upload Type", ["Single Image", "ZIP Folder"])
target_kb = st.slider("Target Image Size (KB)", 20, 1000, DEFAULT_MAX_KB)

uploaded_file = st.file_uploader("Upload File", type=['jpg', 'jpeg', 'png', 'zip'], label_visibility="visible")

# --- Processing ---
if uploaded_file:
    if upload_type == "Single Image":
        result = process_single_image(uploaded_file, target_kb)
        st.success(f"✅ Compressed: {result['filename']}")
        st.write(f"📏 **Dimensions**: {result['original_dims']} → {result['compressed_dims']}")
        st.write(f"📦 **Size**: {result['original_size']:.1f} KB → {result['compressed_size']:.1f} KB")
        st.download_button("Download Compressed Image", data=result['data'], file_name=result['filename'])
    else:
        zip_path, files_info = process_zip(uploaded_file, target_kb)
        st.success(f"✅ {len(files_info)} images compressed")

        with open(zip_path, "rb") as f:
            st.download_button("Download All as ZIP", data=f, file_name="compressed_images.zip")

        with st.expander("📂 Download Individual Files"):
            for img in files_info:
                st.write(f"📸 `{img['name']}` — {img['original_size']:.1f} KB → {img['compressed_size']:.1f} KB")
                st.download_button(f"Download {img['name']}", data=img['data'], file_name=img['name'])