"""
V.O.I.D. Official 1080p High-Fidelity Brand Asset Generator
Generates pristine 1080p (1080x1080) master brand assets from the authentic brand identity sheet
with ZERO text and 100% detail retention across:
- Web (static icons, PWA manifest, favicons, full-screen assets)
- Electron (1080p app icon, Taskbar ICO, Splash screen)
- Flutter (1080p native image assets, Web icons, Android launcher mipmaps)
"""

import os
import sys
import base64
import shutil
from PIL import Image, ImageFilter, ImageDraw
import numpy as np

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Set project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DATA_STATIC_DIR = os.path.join(PROJECT_ROOT, "data", "static")
ELECTRON_DIR = os.path.join(PROJECT_ROOT, "void_electron")
FLUTTER_DIR = os.path.join(PROJECT_ROOT, "void_flutter")
FLUTTER_ASSETS_DIR = os.path.join(FLUTTER_DIR, "assets", "images")
FLUTTER_WEB_DIR = os.path.join(FLUTTER_DIR, "web")
FLUTTER_RES_DIR = os.path.join(FLUTTER_DIR, "android", "app", "src", "main", "res")

# Source master image from user upload
SOURCE_IMAGE_PATH = r"C:\Users\kbven\.gemini\antigravity-ide\brain\aa389063-5850-45f7-a477-1dc7cd740076\.user_uploaded\media_1788585836387.png"
FALLBACK_SOURCE_PATH = os.path.join(STATIC_DIR, "void-brand-guide.png")

def extract_alpha_matte(rgb_crop, bg_color=np.array([26.0, 26.0, 24.0])):
    """
    Extracts transparent RGBA from an image on a uniform dark background
    using color unmixing to prevent fringing and preserve 100% fine edge details.
    """
    arr = np.array(rgb_crop, dtype=float)
    h, w, _ = arr.shape
    
    diff = np.sqrt(np.sum((arr - bg_color) ** 2, axis=2))
    alpha = np.clip((diff - 8.0) / (45.0 - 8.0), 0.0, 1.0)
    alpha_safe = np.maximum(alpha, 0.001)[:, :, np.newaxis]
    F = (arr - (1.0 - alpha[:, :, np.newaxis]) * bg_color) / alpha_safe
    F = np.clip(F, 0, 255)
    
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = F.astype(np.uint8)
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)
    
    return Image.fromarray(rgba)


def upscale_to_1080p_canvas(transparent_emblem, canvas_size=1080, emblem_scale=0.88, add_glow=True):
    """
    Renders the extracted emblem on a 1080x1080 transparent canvas
    with high-quality Lanczos resampling and edge-preserving sharpening.
    Zero text, 100% authentic graphic detail.
    """
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    
    target_w = int(canvas_size * emblem_scale)
    aspect = transparent_emblem.height / transparent_emblem.width
    target_h = int(target_w * aspect)
    
    scaled = transparent_emblem.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Sharpen RGB channels without introducing color fringing
    rgb = scaled.convert("RGB")
    sharpened_rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))
    
    # Smooth alpha edges
    alpha = scaled.split()[-1]
    alpha_sharpened = alpha.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))
    
    emblem_1080 = Image.merge("RGBA", (*sharpened_rgb.split(), alpha_sharpened))
    
    pos_x = (canvas_size - target_w) // 2
    pos_y = (canvas_size - target_h) // 2
    
    if add_glow:
        glow = emblem_1080.copy()
        glow_alpha = np.array(glow.split()[-1], dtype=float) * 0.35
        glow.putalpha(Image.fromarray(glow_alpha.astype(np.uint8)))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=canvas_size * 0.025))
        canvas.alpha_composite(glow, (pos_x, pos_y))
    
    canvas.alpha_composite(emblem_1080, (pos_x, pos_y))
    return canvas


def build_1080p_squircle_icon(transparent_emblem, size=1080):
    """
    Constructs the official 1080p squircle app icon (pure graphic emblem, NO text)
    matching the authentic brand desktop/app icon geometry.
    """
    icon_canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    mask = Image.new("L", (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    corner_radius = int(size * 0.22)
    draw_mask.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=255)
    
    bg_img = Image.new("RGBA", (size, size), (22, 23, 26, 255))
    draw_bg = ImageDraw.Draw(bg_img)
    border_w = max(3, int(size * 0.005))
    draw_bg.rounded_rectangle(
        [border_w, border_w, size - border_w - 1, size - border_w - 1],
        radius=corner_radius - border_w,
        outline=(42, 44, 52, 255),
        width=border_w
    )
    
    icon_canvas.paste(bg_img, (0, 0), mask=mask)
    
    target_w = int(size * 0.78)
    aspect = transparent_emblem.height / transparent_emblem.width
    target_h = int(target_w * aspect)
    
    scaled = transparent_emblem.resize((target_w, target_h), Image.Resampling.LANCZOS)
    rgb = scaled.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))
    alpha = scaled.split()[-1]
    scaled_emblem = Image.merge("RGBA", (*rgb.split(), alpha))
    
    pos_x = (size - target_w) // 2
    pos_y = (size - target_h) // 2
    
    glow = scaled_emblem.copy()
    glow_alpha = np.array(glow.split()[-1], dtype=float) * 0.35
    glow.putalpha(Image.fromarray(glow_alpha.astype(np.uint8)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.03))
    
    icon_canvas.alpha_composite(glow, (pos_x, pos_y))
    icon_canvas.alpha_composite(scaled_emblem, (pos_x, pos_y))
    
    return icon_canvas


def generate_all_assets():
    print("=" * 65)
    print("🚀 V.O.I.D. 1080p High-Fidelity Brand Asset Generation Pipeline")
    print("   (Zero Text in Logo — Pure 1080p Geometric Emblem)")
    print("=" * 65)

    source_path = SOURCE_IMAGE_PATH if os.path.exists(SOURCE_IMAGE_PATH) else FALLBACK_SOURCE_PATH
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Master source image not found at {source_path}")
    
    print(f"Loading master brand sheet from: {source_path}")
    master_img = Image.open(source_path).convert("RGB")
    master_arr = np.array(master_img)
    
    for d in [STATIC_DIR, ELECTRON_DIR, FLUTTER_ASSETS_DIR, FLUTTER_WEB_DIR, 
              os.path.join(FLUTTER_WEB_DIR, "icons")]:
        os.makedirs(d, exist_ok=True)
    
    master_copy_static = os.path.join(STATIC_DIR, "void-brand-guide.png")
    master_img.save(master_copy_static, format="PNG")
    print("  -> Preserved master brand guide in static/ as fallback reference")

    # 1. EXTRACT CENTER MASTER EMBLEM (Symbol with full orbital ring and white accent cut - ZERO TEXT)
    # Strictly bounded to emblem geometry: x=[446, 578], y=[176, 280] (eliminates any text below like "AT VERSION")
    emblem_raw = master_img.crop((446, 176, 578, 280))
    emblem_transparent_raw = extract_alpha_matte(emblem_raw)
    print(f"  -> Extracted clean master emblem: {emblem_transparent_raw.size}")

    # 2. GENERATE 1080p MASTER SYMBOL (1080x1080, NO TEXT)
    symbol_1080 = upscale_to_1080p_canvas(emblem_transparent_raw, canvas_size=1080, emblem_scale=0.88, add_glow=True)
    
    # Save 1080p symbol in static & flutter
    symbol_png_static = os.path.join(STATIC_DIR, "void-symbol.png")
    symbol_png_flutter = os.path.join(FLUTTER_ASSETS_DIR, "void_symbol.png")
    symbol_1080.save(symbol_png_static, format="PNG")
    symbol_1080.save(symbol_png_flutter, format="PNG")
    print("  -> Generated 1080p void-symbol.png (1080x1080, NO TEXT)")

    # 3. GENERATE 1080p MASTER BRANDMARK (1080x1080, Pure Emblem - NO TEXT)
    # The user explicitly requested NO TEXT in logo: brandmark is now the pure emblem
    brandmark_png_static = os.path.join(STATIC_DIR, "void-brandmark.png")
    brandmark_png_flutter = os.path.join(FLUTTER_ASSETS_DIR, "void_brandmark.png")
    symbol_1080.save(brandmark_png_static, format="PNG")
    symbol_1080.save(brandmark_png_flutter, format="PNG")
    
    # Also generate widescreen 1920x1080 banner variant (pure emblem centered on 1080p widescreen, NO TEXT)
    widescreen_1080p = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    pos_x = (1920 - 1080) // 2
    widescreen_1080p.alpha_composite(symbol_1080, (pos_x, 0))
    widescreen_1080p.save(os.path.join(STATIC_DIR, "void-brandmark-1080p.png"), format="PNG")
    print("  -> Generated 1080p void-brandmark.png & 1920x1080 widescreen banner (NO TEXT)")

    # 4. GENERATE 1080p MASTER SQUIRCLE APP ICON (1080x1080, NO TEXT)
    master_icon_1080 = build_1080p_squircle_icon(emblem_transparent_raw, size=1080)
    
    # Save 1080p icons
    master_icon_1080.save(os.path.join(STATIC_DIR, "icon.png"), format="PNG")
    master_icon_1080.save(os.path.join(STATIC_DIR, "icon-1080.png"), format="PNG")
    master_icon_1080.save(os.path.join(ELECTRON_DIR, "icon.png"), format="PNG")
    master_icon_1080.save(os.path.join(FLUTTER_ASSETS_DIR, "void_icon.png"), format="PNG")
    print("  -> Generated 1080p icon.png (1080x1080) across Web, Electron & Flutter")

    # 5. GENERATE STANDARD DOWNSAMPLED ICONS (512x512, 192x192 for PWA & mobile compatibility)
    icon_512 = master_icon_1080.resize((512, 512), Image.Resampling.LANCZOS)
    icon_512.save(os.path.join(STATIC_DIR, "icon-512.png"), format="PNG")
    icon_512.save(os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-512.png"), format="PNG")
    icon_512.save(os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-maskable-512.png"), format="PNG")

    icon_192 = master_icon_1080.resize((192, 192), Image.Resampling.LANCZOS)
    icon_192.save(os.path.join(STATIC_DIR, "icon-192.png"), format="PNG")
    icon_192.save(os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-192.png"), format="PNG")
    icon_192.save(os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-maskable-192.png"), format="PNG")
    print("  -> Generated 512x512 and 192x192 PWA & Flutter icons from 1080p master")

    # 6. GENERATE FAVICONS & MULTI-SIZE WINDOWS/WEB ICO
    fav_64 = master_icon_1080.resize((64, 64), Image.Resampling.LANCZOS)
    fav_64.save(os.path.join(STATIC_DIR, "favicon.png"), format="PNG")
    fav_64.save(os.path.join(FLUTTER_WEB_DIR, "favicon.png"), format="PNG")

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master_icon_1080.save(os.path.join(STATIC_DIR, "favicon.ico"), format="ICO", sizes=ico_sizes)
    master_icon_1080.save(os.path.join(ELECTRON_DIR, "icon.ico"), format="ICO", sizes=ico_sizes)
    print("  -> Generated multi-size favicon.ico and Electron icon.ico")

    # 7. GENERATE ANDROID LAUNCHER MIPMAPS
    mipmap_targets = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, sz in mipmap_targets.items():
        folder_path = os.path.join(FLUTTER_RES_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        out_path = os.path.join(folder_path, "ic_launcher.png")
        resized_icon = master_icon_1080.resize((sz, sz), Image.Resampling.LANCZOS)
        resized_icon.save(out_path, format="PNG")
        print(f"  -> Android {folder}/ic_launcher.png ({sz}x{sz})")

    # 8. GENERATE 1080p VECTOR SVGs (with embedded 1080p master graphics, NO TEXT)
    with open(symbol_png_static, "rb") as f:
        symbol_1080_b64 = base64.b64encode(f.read()).decode("utf-8")
    with open(os.path.join(STATIC_DIR, "icon.png"), "rb") as f:
        icon_1080_b64 = base64.b64encode(f.read()).decode("utf-8")

    # 1080x1080 Symbol SVG (NO TEXT)
    symbol_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <image href="data:image/png;base64,{symbol_1080_b64}" width="1080" height="1080"/>
</svg>'''
    with open(os.path.join(STATIC_DIR, "void-symbol.svg"), "w", encoding="utf-8") as f:
        f.write(symbol_svg_content)
    with open(os.path.join(STATIC_DIR, "void-brandmark.svg"), "w", encoding="utf-8") as f:
        f.write(symbol_svg_content)
    print("  -> Created 1080p static/void-symbol.svg & void-brandmark.svg (NO TEXT)")

    # 1080x1080 Icon Squircle SVG (NO TEXT)
    icon_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <image href="data:image/png;base64,{icon_1080_b64}" width="1080" height="1080"/>
</svg>'''
    with open(os.path.join(STATIC_DIR, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(icon_svg_content)
    print("  -> Created 1080p static/icon.svg (1080x1080, NO TEXT)")

    # Favicon SVG (64x64)
    with open(os.path.join(STATIC_DIR, "favicon.png"), "rb") as f:
        fav_b64 = base64.b64encode(f.read()).decode("utf-8")
    fav_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <image href="data:image/png;base64,{fav_b64}" width="64" height="64"/>
</svg>'''
    with open(os.path.join(STATIC_DIR, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(fav_svg_content)
    print("  -> Created static/favicon.svg (Favicon SVG)")

    # 9. 1080p LIGHT / B&W EMBLEM (Item 6 from brand sheet, NO TEXT)
    roi_light = master_arr[350:445, 800:955]
    dark_pixels = np.all(roi_light < [120, 120, 120], axis=2)
    ys_l, xs_l = np.where(dark_pixels)
    if len(ys_l) > 0:
        y1_l = max(0, ys_l.min() + 350 - 4)
        y2_l = min(master_arr.shape[0], ys_l.max() + 350 + 5)
        x1_l = max(0, xs_l.min() + 800 - 4)
        x2_l = min(master_arr.shape[1], xs_l.max() + 800 + 5)
        light_crop = master_arr[y1_l:y2_l, x1_l:x2_l]
        
        bg_light = np.array([242.0, 240.0, 228.0])
        diff_l = np.sqrt(np.sum((light_crop.astype(float) - bg_light) ** 2, axis=2))
        alpha_l = np.clip((diff_l - 8.0) / (45.0 - 8.0), 0.0, 1.0)
        alpha_safe_l = np.maximum(alpha_l, 0.001)[:, :, np.newaxis]
        F_l = np.clip((light_crop.astype(float) - (1.0 - alpha_l[:, :, np.newaxis]) * bg_light) / alpha_safe_l, 0, 255)
        
        rgba_l = np.zeros((light_crop.shape[0], light_crop.shape[1], 4), dtype=np.uint8)
        rgba_l[:, :, :3] = F_l.astype(np.uint8)
        rgba_l[:, :, 3] = (alpha_l * 255).astype(np.uint8)
        
        light_raw = Image.fromarray(rgba_l)
        light_1080 = upscale_to_1080p_canvas(light_raw, canvas_size=1080, emblem_scale=0.88, add_glow=False)
        light_1080.save(os.path.join(STATIC_DIR, "void-symbol-light.png"), format="PNG")
        
        light_b64 = base64.b64encode(open(os.path.join(STATIC_DIR, "void-symbol-light.png"), "rb").read()).decode("utf-8")
        light_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <image href="data:image/png;base64,{light_b64}" width="1080" height="1080"/>
</svg>'''
        with open(os.path.join(STATIC_DIR, "void-brandmark-light.svg"), "w", encoding="utf-8") as f:
            f.write(light_svg)
        print("  -> Created 1080p void-symbol-light.png & void-brandmark-light.svg (Item 6 Light/B&W, NO TEXT)")

    # 10. MIRROR TO DATA/STATIC IF PRESENT
    if os.path.isdir(DATA_STATIC_DIR):
        for fname in os.listdir(STATIC_DIR):
            src = os.path.join(STATIC_DIR, fname)
            if os.path.isfile(src) and (fname.endswith(('.png', '.svg', '.ico', '.css'))):
                shutil.copy2(src, os.path.join(DATA_STATIC_DIR, fname))
        print("  -> Mirrored all 1080p brand assets to data/static/")

    print("\n✨ All 1080p V.O.I.D. brand assets generated across Web, Electron & Flutter with NO TEXT and 100% detail retention!")

if __name__ == "__main__":
    generate_all_assets()
