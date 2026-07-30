import os
import re
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
from rembg import remove

# Resolve directory paths relative to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "Upload your Photos (File responses)-20260723T063106Z-1-001", "Upload your Photos (File responses)")
DST_DIR = os.path.join(PROJECT_ROOT, "known_faces")

os.makedirs(DST_DIR, exist_ok=True)

def parse_name(filename):
    base, ext = os.path.splitext(filename)
    if " - " in base:
        parts = base.split(" - ")
        name = parts[-1].strip()
    else:
        name = base.strip()
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name, ext.lower()

def extract_image_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            if image_list:
                xref = image_list[0][0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                return Image.open(BytesIO(image_bytes))
        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        return Image.open(BytesIO(img_data))
    except Exception as e:
        print(f"Error extracting image from PDF {pdf_path}: {e}")
        return None

def process_files():
    files = sorted(os.listdir(SRC_DIR))
    print(f"Found {len(files)} files to analyze.")
    
    name_counts = {}
    
    for filename in files:
        file_path = os.path.join(SRC_DIR, filename)
        if not os.path.isfile(file_path):
            continue
            
        name, ext = parse_name(filename)
        if not name:
            continue
            
        # Determine unique target name
        if name not in name_counts:
            name_counts[name] = 1
            target_name = name
        else:
            name_counts[name] += 1
            target_name = f"{name}_{name_counts[name]}"
            
        target_path = os.path.join(DST_DIR, f"{target_name}.png")
        print(f"Processing '{filename}' -> Saving to: '{target_name}.png'...")
        
        img = None
        if ext == ".pdf":
            img = extract_image_from_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png"]:
            try:
                img = Image.open(file_path)
            except Exception as e:
                print(f"Error opening image {filename}: {e}")
        
        if img is None:
            print(f"Failed to load image for {filename}")
            continue
            
        try:
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Remove background
            output_img = remove(img)
            output_img.save(target_path, format="PNG")
            print(f"Saved: {target_path}")
        except Exception as e:
            print(f"Error processing {target_name}: {e}")

if __name__ == "__main__":
    process_files()
    print("Done processing all photos.")
