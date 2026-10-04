"""
V.O.I.D. Brand Asset Generator
Generates all SVG and high-resolution PNG/ICO assets for:
- Web (Favicon, Logo, Brandmark, App Icons)
- Flutter (Web icons, Favicon, Android mipmap launcher icons)
- Electron (App icon, Splash screen assets)
- Desktop / PWA Manifest
"""

import os
import sys
import subprocess
import tempfile
from PIL import Image

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
FLUTTER_WEB_DIR = os.path.join(PROJECT_ROOT, "void_flutter", "web")
FLUTTER_RES_DIR = os.path.join(PROJECT_ROOT, "void_flutter", "android", "app", "src", "main", "res")
ELECTRON_DIR = os.path.join(PROJECT_ROOT, "void_electron")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(FLUTTER_WEB_DIR, exist_ok=True)
os.makedirs(os.path.join(FLUTTER_WEB_DIR, "icons"), exist_ok=True)
os.makedirs(ELECTRON_DIR, exist_ok=True)

# 1. STANDALONE SYMBOL SVG (Dark Background Squircle)
ICON_SVG_SQUIRCLE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <radialGradient id="bgGrad" cx="50%" cy="40%" r="65%">
      <stop offset="0%" stop-color="#1c1d22"/>
      <stop offset="60%" stop-color="#121316"/>
      <stop offset="100%" stop-color="#0a0a0c"/>
    </radialGradient>
    <linearGradient id="orangeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF701A"/>
      <stop offset="50%" stop-color="#FF5500"/>
      <stop offset="100%" stop-color="#E64500"/>
    </linearGradient>
    <linearGradient id="goldRing" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#D49010" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#FFD54F" stop-opacity="1"/>
      <stop offset="100%" stop-color="#E5A823" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="innerOrange" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF8A3D"/>
      <stop offset="100%" stop-color="#FF5500"/>
    </linearGradient>
    <filter id="subtleGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Background Squircle -->
  <rect x="16" y="16" width="480" height="480" rx="108" fill="url(#bgGrad)" stroke="#272832" stroke-width="2.5"/>

  <!-- Orbital Halo Ring (Back Arc) -->
  <path d="M 96 260 A 166 52 0 0 1 416 260" fill="none" stroke="url(#goldRing)" stroke-width="12" stroke-linecap="round" opacity="0.85"/>

  <!-- Inner Inverted Triangle -->
  <polygon points="184,212 328,212 256,334" fill="none" stroke="url(#innerOrange)" stroke-width="13" stroke-linejoin="miter" stroke-miterlimit="4"/>
  <!-- Inner Triangle Upper Gold Highlight Arc/Line -->
  <path d="M 200 224 A 60 14 0 0 1 312 224" fill="none" stroke="#FFD54F" stroke-width="5" stroke-linecap="round" opacity="0.95"/>

  <!-- Outer Inverted Triangle (Main Orange Body) -->
  <path d="M 126 150 L 324 150 M 356 182 L 256 396 L 126 150" fill="none" stroke="url(#orangeGrad)" stroke-width="24" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>

  <!-- Outer Triangle Top-Right White Geometric Accent -->
  <path d="M 324 150 L 386 150 L 356 182" fill="none" stroke="#FFFFFF" stroke-width="24" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>

  <!-- Orbital Halo Ring (Front Arc highlights on outer sides) -->
  <path d="M 86 262 A 172 52 0 0 0 134 294" fill="none" stroke="url(#goldRing)" stroke-width="12" stroke-linecap="round"/>
  <path d="M 378 294 A 172 52 0 0 0 426 262" fill="none" stroke="url(#goldRing)" stroke-width="12" stroke-linecap="round"/>
</svg>'''

# 2. TRANSPARENT STANDALONE SYMBOL SVG (For UI Headers & Avatars)
VOID_SYMBOL_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="orangeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF701A"/>
      <stop offset="50%" stop-color="#FF5500"/>
      <stop offset="100%" stop-color="#E64500"/>
    </linearGradient>
    <linearGradient id="goldRing" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#D49010" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#FFD54F" stop-opacity="1"/>
      <stop offset="100%" stop-color="#E5A823" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="innerOrange" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF8A3D"/>
      <stop offset="100%" stop-color="#FF5500"/>
    </linearGradient>
  </defs>

  <!-- Orbital Halo Ring (Back Arc) -->
  <path d="M 96 260 A 166 52 0 0 1 416 260" fill="none" stroke="url(#goldRing)" stroke-width="14" stroke-linecap="round" opacity="0.85"/>

  <!-- Inner Inverted Triangle -->
  <polygon points="184,212 328,212 256,334" fill="none" stroke="url(#innerOrange)" stroke-width="14" stroke-linejoin="miter" stroke-miterlimit="4"/>
  <!-- Inner Triangle Upper Gold Highlight -->
  <path d="M 200 224 A 60 14 0 0 1 312 224" fill="none" stroke="#FFD54F" stroke-width="6" stroke-linecap="round" opacity="0.95"/>

  <!-- Outer Inverted Triangle (Main Orange Body) -->
  <path d="M 126 150 L 324 150 M 356 182 L 256 396 L 126 150" fill="none" stroke="url(#orangeGrad)" stroke-width="26" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>

  <!-- Outer Triangle Top-Right White Geometric Accent -->
  <path d="M 324 150 L 386 150 L 356 182" fill="none" stroke="#FFFFFF" stroke-width="26" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>

  <!-- Orbital Halo Ring (Front Arc highlights on outer sides) -->
  <path d="M 86 262 A 172 52 0 0 0 134 294" fill="none" stroke="url(#goldRing)" stroke-width="14" stroke-linecap="round"/>
  <path d="M 378 294 A 172 52 0 0 0 426 262" fill="none" stroke="url(#goldRing)" stroke-width="14" stroke-linecap="round"/>
</svg>'''

# 3. FULL HORIZONTAL BRANDMARK SVG (Symbol + Wordmark + Tagline)
VOID_BRANDMARK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 320" width="1000" height="320">
  <defs>
    <linearGradient id="bmOrange" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF751A"/>
      <stop offset="50%" stop-color="#FF5500"/>
      <stop offset="100%" stop-color="#E64500"/>
    </linearGradient>
    <linearGradient id="bmGold" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#D49010"/>
      <stop offset="50%" stop-color="#FFD54F"/>
      <stop offset="100%" stop-color="#E5A823"/>
    </linearGradient>
  </defs>

  <!-- Left Icon Symbol (Scaled 0.52 and placed at x=40, y=20) -->
  <g transform="translate(30, 20) scale(0.52)">
    <!-- Orbital Halo Ring (Back Arc) -->
    <path d="M 96 260 A 166 52 0 0 1 416 260" fill="none" stroke="url(#bmGold)" stroke-width="15" stroke-linecap="round" opacity="0.85"/>

    <!-- Inner Inverted Triangle -->
    <polygon points="184,212 328,212 256,334" fill="none" stroke="#FF5500" stroke-width="15" stroke-linejoin="miter" stroke-miterlimit="4"/>
    <path d="M 200 224 A 60 14 0 0 1 312 224" fill="none" stroke="#FFD54F" stroke-width="6" stroke-linecap="round"/>

    <!-- Outer Inverted Triangle -->
    <path d="M 126 150 L 324 150 M 356 182 L 256 396 L 126 150" fill="none" stroke="url(#bmOrange)" stroke-width="26" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>
    <path d="M 324 150 L 386 150 L 356 182" fill="none" stroke="#FFFFFF" stroke-width="26" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>

    <!-- Orbital Halo Ring (Front Flanks) -->
    <path d="M 86 262 A 172 52 0 0 0 134 294" fill="none" stroke="url(#bmGold)" stroke-width="15" stroke-linecap="round"/>
    <path d="M 378 294 A 172 52 0 0 0 426 262" fill="none" stroke="url(#bmGold)" stroke-width="15" stroke-linecap="round"/>
  </g>

  <!-- Stylized Wordmark: V.O.I.D. -->
  <g transform="translate(320, 45)">
    <!-- Letter V (Stylized with detached top-left accent) -->
    <!-- Top-left detached diagonal pill/dash -->
    <polygon points="10,25 32,25 24,42 2,42" fill="#FF5500"/>
    <!-- Left diagonal bar (shortened) -->
    <polygon points="18,52 38,52 70,116 50,116" fill="#FF5500"/>
    <!-- Right diagonal bar (full) -->
    <polygon points="106,25 128,25 68,126 48,126" fill="#FF5500"/>

    <!-- Dot after V -->
    <circle cx="146" cy="116" r="8" fill="#FF5500"/>

    <!-- Letter O -->
    <path d="M 210,25 L 255,25 Q 285,25 285,55 L 285,95 Q 285,125 255,125 L 210,125 Q 180,125 180,95 L 180,55 Q 180,25 210,25 Z M 216,47 Q 202,47 202,62 L 202,88 Q 202,103 216,103 L 249,103 Q 263,103 263,88 L 263,62 Q 263,47 249,47 Z" fill="#FF5500"/>

    <!-- Dot after O -->
    <circle cx="307" cy="116" r="8" fill="#FF5500"/>

    <!-- Letter I -->
    <rect x="336" y="25" width="22" height="100" rx="3" fill="#FF5500"/>

    <!-- Dot after I -->
    <circle cx="380" cy="116" r="8" fill="#FF5500"/>

    <!-- Letter D -->
    <path d="M 410,25 L 452,25 Q 495,25 495,75 Q 495,125 452,125 L 410,125 Z M 432,47 L 432,103 L 450,103 Q 473,103 473,75 Q 473,47 450,47 Z" fill="#FF5500"/>

    <!-- Dot after D -->
    <circle cx="517" cy="116" r="8" fill="#FF5500"/>

    <!-- Subtitle / Tagline -->
    <text x="5" y="172" font-family="'Inter', 'Segoe UI', system-ui, sans-serif" font-size="19" font-weight="500" letter-spacing="4.5" fill="#B0B0A8">
      VIRTUAL OPERATOR OF INFORMATION &amp; DEVELOPMENT
    </text>
  </g>
</svg>'''

# 4. LIGHT THEME BRANDMARK
VOID_BRANDMARK_LIGHT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 320" width="1000" height="320">
  <!-- Left Icon Symbol (Pure Crisp Black Geometry for Light/B&W) -->
  <g transform="translate(30, 20) scale(0.52)">
    <path d="M 96 260 A 166 52 0 0 1 416 260" fill="none" stroke="#111111" stroke-width="15" stroke-linecap="round"/>
    <polygon points="184,212 328,212 256,334" fill="none" stroke="#111111" stroke-width="15" stroke-linejoin="miter" stroke-miterlimit="4"/>
    <path d="M 200 224 A 60 14 0 0 1 312 224" fill="none" stroke="#111111" stroke-width="6" stroke-linecap="round"/>
    <polygon points="126,150 386,150 256,396" fill="none" stroke="#111111" stroke-width="26" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="4"/>
    <path d="M 86 262 A 172 52 0 0 0 134 294" fill="none" stroke="#111111" stroke-width="15" stroke-linecap="round"/>
    <path d="M 378 294 A 172 52 0 0 0 426 262" fill="none" stroke="#111111" stroke-width="15" stroke-linecap="round"/>
  </g>

  <!-- Stylized Wordmark: V.O.I.D. (Black) -->
  <g transform="translate(320, 45)">
    <polygon points="10,25 32,25 24,42 2,42" fill="#111111"/>
    <polygon points="18,52 38,52 70,116 50,116" fill="#111111"/>
    <polygon points="106,25 128,25 68,126 48,126" fill="#111111"/>
    <circle cx="146" cy="116" r="8" fill="#111111"/>
    <path d="M 210,25 L 255,25 Q 285,25 285,55 L 285,95 Q 285,125 255,125 L 210,125 Q 180,125 180,95 L 180,55 Q 180,25 210,25 Z M 216,47 Q 202,47 202,62 L 202,88 Q 202,103 216,103 L 249,103 Q 263,103 263,88 L 263,62 Q 263,47 249,47 Z" fill="#111111"/>
    <circle cx="307" cy="116" r="8" fill="#111111"/>
    <rect x="336" y="25" width="22" height="100" rx="3" fill="#111111"/>
    <circle cx="380" cy="116" r="8" fill="#111111"/>
    <path d="M 410,25 L 452,25 Q 495,25 495,75 Q 495,125 452,125 L 410,125 Z M 432,47 L 432,103 L 450,103 Q 473,103 473,75 Q 473,47 450,47 Z" fill="#111111"/>
    <circle cx="517" cy="116" r="8" fill="#111111"/>

    <text x="5" y="172" font-family="'Inter', 'Segoe UI', system-ui, sans-serif" font-size="19" font-weight="600" letter-spacing="4.5" fill="#333333">
      VIRTUAL OPERATOR OF INFORMATION &amp; DEVELOPMENT
    </text>
  </g>
</svg>'''

# 5. CRISP HIGH-CONTRAST FAVICON SVG
FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="14" fill="#121316"/>
  <!-- Halo Ring -->
  <ellipse cx="32" cy="33" rx="23" ry="8" fill="none" stroke="#FFD54F" stroke-width="2" opacity="0.9"/>
  <!-- Inner Triangle -->
  <polygon points="23,26 41,26 32,42" fill="none" stroke="#FF5500" stroke-width="2"/>
  <!-- Outer Triangle -->
  <path d="M 16 18 L 40 18 M 44 22 L 32 50 L 16 18" fill="none" stroke="#FF5500" stroke-width="3.5" stroke-linecap="square"/>
  <path d="M 40 18 L 48 18 L 44 22" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="square"/>
</svg>'''


def write_svg_files():
    print("Writing SVG brand files...")
    files = {
        os.path.join(STATIC_DIR, "icon.svg"): ICON_SVG_SQUIRCLE,
        os.path.join(STATIC_DIR, "void-symbol.svg"): VOID_SYMBOL_SVG,
        os.path.join(STATIC_DIR, "void-brandmark.svg"): VOID_BRANDMARK_SVG,
        os.path.join(STATIC_DIR, "void-brandmark-light.svg"): VOID_BRANDMARK_LIGHT_SVG,
        os.path.join(STATIC_DIR, "favicon.svg"): FAVICON_SVG,
    }
    for path, content in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  -> {os.path.relpath(path, PROJECT_ROOT)}")


def rasterize_svg_with_edge(svg_path, output_png_path, width=1024, height=1024):
    """Renders an SVG to PNG using Edge headless screenshot for crisp vector rasterization."""
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    browser_exe = next((p for p in edge_candidates if os.path.isfile(p)), None)
    if not browser_exe:
        raise RuntimeError("No Chromium browser found for headless SVG rendering.")

    # Create a small HTML wrapper to render SVG at full canvas with no margins
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: transparent; width: {width}px; height: {height}px; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
  img {{ width: {width}px; height: {height}px; display: block; }}
</style>
</head>
<body>
  <img src="file:///{svg_path.replace(os.sep, '/')}" />
</body>
</html>"""

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp_html:
        tmp_html.write(html_content)
        tmp_html_path = tmp_html.name

    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={output_png_path}",
        f"file:///{tmp_html_path.replace(os.sep, '/')}",
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    try:
        os.remove(tmp_html_path)
    except Exception:
        pass


def generate_png_and_ico_assets():
    print("Rasterizing master high-res icons...")
    master_icon_svg = os.path.join(STATIC_DIR, "icon.svg")
    master_png_512 = os.path.join(STATIC_DIR, "icon.png")

    rasterize_svg_with_edge(master_icon_svg, master_png_512, width=1024, height=1024)

    # Open with Pillow for downsampling with high-quality Lanczos resampling
    img = Image.open(master_png_512)
    # Save standard 512x512
    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save(master_png_512, format="PNG")
    print(f"  -> Generated {os.path.relpath(master_png_512, PROJECT_ROOT)} (512x512)")

    # Static Web Assets
    pwa_192 = os.path.join(STATIC_DIR, "icon-192.png")
    pwa_512 = os.path.join(STATIC_DIR, "icon-512.png")
    fav_png = os.path.join(STATIC_DIR, "favicon.png")
    fav_ico = os.path.join(STATIC_DIR, "favicon.ico")

    img_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
    img_192.save(pwa_192, format="PNG")
    img_512.save(pwa_512, format="PNG")

    img_64 = img.resize((64, 64), Image.Resampling.LANCZOS)
    img_64.save(fav_png, format="PNG")

    img.save(fav_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"  -> Generated favicon.ico, favicon.png, icon-192.png, icon-512.png in static/")

    # Flutter Web Assets
    flutter_fav = os.path.join(FLUTTER_WEB_DIR, "favicon.png")
    flutter_192 = os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-192.png")
    flutter_512 = os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-512.png")
    flutter_mask_192 = os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-maskable-192.png")
    flutter_mask_512 = os.path.join(FLUTTER_WEB_DIR, "icons", "Icon-maskable-512.png")

    img_64.save(flutter_fav, format="PNG")
    img_192.save(flutter_192, format="PNG")
    img_512.save(flutter_512, format="PNG")
    img_192.save(flutter_mask_192, format="PNG")
    img_512.save(flutter_mask_512, format="PNG")
    print(f"  -> Generated Flutter Web icons & favicon")

    # Flutter Android Launcher Mipmaps
    mipmap_targets = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, size in mipmap_targets.items():
        folder_path = os.path.join(FLUTTER_RES_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        out_path = os.path.join(folder_path, "ic_launcher.png")
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_path, format="PNG")
        print(f"  -> Android {folder}/ic_launcher.png ({size}x{size})")

    # Electron Desktop Asset
    electron_icon = os.path.join(ELECTRON_DIR, "icon.png")
    img_512.save(electron_icon, format="PNG")
    electron_ico = os.path.join(ELECTRON_DIR, "icon.ico")
    img.save(electron_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"  -> Generated Electron icon.png and icon.ico")

    # Also render horizontal brandmark to PNG for quick reference or headers
    brandmark_svg = os.path.join(STATIC_DIR, "void-brandmark.svg")
    brandmark_png = os.path.join(STATIC_DIR, "void-brandmark.png")
    rasterize_svg_with_edge(brandmark_svg, brandmark_png, width=1000, height=320)
    print(f"  -> Generated {os.path.relpath(brandmark_png, PROJECT_ROOT)} (1000x320)")


if __name__ == "__main__":
    from generate_brand_assets import generate_all_assets
    generate_all_assets()

