import streamlit as st
from PIL import Image
import io
import os
import zipfile
import tempfile
import shutil

MAX_SIZE_KB = 100

def compress_image(img, format, target_size_kb=100):
    quality = 95
    img_bytes = io.BytesIO()

    # Convert to RGB if image is in P or RGBA mode (JPEG can't handle these)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Try to reduce quality and size iteratively
    while quality > 5:
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
        size_kb = img_bytes.tell() / 1024
        if size_kb <= target_size_kb:
            break
        quality -= 5

    # If still too large, try resizing
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
    return img_bytes

def process_single_image(uploaded_file):
    image = Image.open(uploaded_file)
    format = image.format
    compressed_bytes = compress_image(image, format)
    return compressed_bytes, uploaded_file.name

def process_zip(uploaded_zip):
    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "uploaded.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        output_dir = os.path.join(temp_dir, "compressed")
        os.makedirs(output_dir, exist_ok=True)

        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    full_path = os.path.join(root, file)
                    try:
                        img = Image.open(full_path)
                        format = img.format
                        compressed = compress_image(img, format)
                        with open(os.path.join(output_dir, file), "wb") as f:
                            f.write(compressed.read())
                    except:
                        continue

        # Create ZIP file outside the temporary folder so it doesn't get deleted
        shutil.make_archive(temp_zip_file.name.replace(".zip", ""), 'zip', output_dir)

    return temp_zip_file.name

# Streamlit UI
st.title("📸 Image Compressor - Under 100KB")

upload_type = st.selectbox("Upload Type", ["Single Image", "ZIP Folder"])

uploaded_file = st.file_uploader("Upload File", type=['jpg', 'jpeg', 'png', 'zip'])

if uploaded_file:
    if upload_type == "Single Image":
        compressed_img, filename = process_single_image(uploaded_file)
        st.success(f"✅ Compressed: {filename}")
        st.download_button("Download Compressed Image", data=compressed_img, file_name=filename)
    elif upload_type == "ZIP Folder":
        zip_path = process_zip(uploaded_file)
        with open(zip_path, "rb") as f:
            st.download_button("Download Compressed ZIP", data=f, file_name="compressed_images.zip")