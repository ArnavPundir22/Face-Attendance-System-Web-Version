import os
import math
from PIL import Image, ImageDraw, ImageFilter

def create_biosecure_icon(size=512, maskable=False):
    # Canvas setup
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Dimensions & Radii
    bg_color = (11, 19, 38, 255) # #0b1326
    corner_radius = size * 0.22 if not maskable else 0
    
    # Outer Background Card
    if maskable:
        draw.rectangle([0, 0, size, size], fill=bg_color)
    else:
        draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=bg_color)
        
        # Subtle glowing border
        border_glow = (59, 130, 246, 60) # #3b82f6 with opacity
        border_width = max(2, int(size * 0.015))
        draw.rounded_rectangle(
            [border_width, border_width, size - border_width, size - border_width],
            radius=corner_radius * 0.9,
            outline=border_glow,
            width=border_width
        )

    # Face Recognition Graphic elements
    center_x, center_y = size / 2, size / 2
    icon_scale = size * (0.55 if maskable else 0.6)
    half_scale = icon_scale / 2
    
    # Glowing scan frame corners
    corner_length = icon_scale * 0.25
    line_w = max(3, int(size * 0.035))
    accent_color = (6, 182, 212, 255)  # #06b6d4 Cyan
    primary_color = (59, 130, 246, 255) # #3b82f6 Blue
    
    left = center_x - half_scale
    top = center_y - half_scale
    right = center_x + half_scale
    bottom = center_y + half_scale
    
    # Top-Left Bracket
    draw.line([(left, top + corner_length), (left, top), (left + corner_length, top)], fill=accent_color, width=line_w)
    # Top-Right Bracket
    draw.line([(right - corner_length, top), (right, top), (right, top + corner_length)], fill=accent_color, width=line_w)
    # Bottom-Left Bracket
    draw.line([(left, bottom - corner_length), (left, bottom), (left + corner_length, bottom)], fill=accent_color, width=line_w)
    # Bottom-Right Bracket
    draw.line([(right - corner_length, bottom), (right, bottom), (right, bottom - corner_length)], fill=accent_color, width=line_w)
    
    # Stylized Face / Shield Silhouette inside
    # Head outline (oval)
    head_w = icon_scale * 0.48
    head_h = icon_scale * 0.60
    head_left = center_x - head_w / 2
    head_top = center_y - head_h / 2 - size * 0.02
    head_right = center_x + head_w / 2
    head_bottom = head_top + head_h
    
    draw.ellipse([head_left, head_top, head_right, head_bottom], outline=(255, 255, 255, 200), width=max(2, int(line_w * 0.75)))
    
    # Facial Scan Mesh Dots (eyes, nose, mouth points)
    dot_r = max(2, int(size * 0.018))
    
    # Eyes
    eye_y = center_y - size * 0.04
    left_eye_x = center_x - head_w * 0.22
    right_eye_x = center_x + head_w * 0.22
    
    draw.ellipse([left_eye_x - dot_r, eye_y - dot_r, left_eye_x + dot_r, eye_y + dot_r], fill=accent_color)
    draw.ellipse([right_eye_x - dot_r, eye_y - dot_r, right_eye_x + dot_r, eye_y + dot_r], fill=accent_color)
    
    # Connecting eye line (laser scan line)
    laser_w = max(1, int(size * 0.01))
    draw.line([(left - size * 0.04, eye_y), (right + size * 0.04, eye_y)], fill=(6, 182, 212, 140), width=laser_w)
    
    # Nose & Mouth Points
    nose_y = center_y + size * 0.02
    mouth_y = center_y + size * 0.08
    
    draw.ellipse([center_x - dot_r*0.8, nose_y - dot_r*0.8, center_x + dot_r*0.8, nose_y + dot_r*0.8], fill=primary_color)
    draw.ellipse([center_x - head_w * 0.15 - dot_r*0.8, mouth_y - dot_r*0.8, center_x - head_w * 0.15 + dot_r*0.8, mouth_y + dot_r*0.8], fill=accent_color)
    draw.ellipse([center_x + head_w * 0.15 - dot_r*0.8, mouth_y - dot_r*0.8, center_x + head_w * 0.15 + dot_r*0.8, mouth_y + dot_r*0.8], fill=accent_color)

    # Facial triangulation lines
    mesh_line_w = max(1, int(size * 0.006))
    mesh_color = (59, 130, 246, 100)
    draw.line([(left_eye_x, eye_y), (center_x, nose_y)], fill=mesh_color, width=mesh_line_w)
    draw.line([(right_eye_x, eye_y), (center_x, nose_y)], fill=mesh_color, width=mesh_line_w)
    draw.line([(center_x, nose_y), (center_x - head_w * 0.15, mouth_y)], fill=mesh_color, width=mesh_line_w)
    draw.line([(center_x, nose_y), (center_x + head_w * 0.15, mouth_y)], fill=mesh_color, width=mesh_line_w)
    draw.line([(left_eye_x, eye_y), (right_eye_x, eye_y)], fill=mesh_color, width=mesh_line_w)
    
    return img

def generate_all_icons():
    output_dir = os.path.join(os.path.dirname(__file__), "src", "static", "icons")
    os.makedirs(output_dir, exist_ok=True)
    
    standard_sizes = [16, 32, 72, 96, 128, 144, 152, 180, 192, 384, 512]
    
    for sz in standard_sizes:
        icon = create_biosecure_icon(size=sz, maskable=False)
        if sz == 180:
            filename = "apple-touch-icon.png"
        elif sz == 32:
            filename = "favicon-32x32.png"
        elif sz == 16:
            filename = "favicon-16x16.png"
        else:
            filename = f"icon-{sz}.png"
            
        path = os.path.join(output_dir, filename)
        icon.save(path, "PNG")
        print(f"Generated {filename} ({sz}x{sz})")
        
    # Maskable icons
    for sz in [192, 512]:
        maskable_icon = create_biosecure_icon(size=sz, maskable=True)
        filename = f"maskable-icon-{sz}.png"
        path = os.path.join(output_dir, filename)
        maskable_icon.save(path, "PNG")
        print(f"Generated {filename} (maskable {sz}x{sz})")

if __name__ == "__main__":
    generate_all_icons()
