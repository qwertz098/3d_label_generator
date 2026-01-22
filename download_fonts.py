"""
Font Downloader for 3D Label Generator
Downloads required sans-serif fonts from Google Fonts
"""

import os
import urllib.request
import zipfile
import shutil
from pathlib import Path

FONTS_DIR = Path(__file__).parent / "fonts"

# Google Fonts to download (name, Google Fonts family name)
GOOGLE_FONTS = [
    ("Overpass", "Overpass"),
    ("Roboto", "Roboto"),
    ("Open Sans", "Open+Sans"),
    ("Lato", "Lato"),
    ("Montserrat", "Montserrat"),
    ("Source Sans Pro", "Source+Sans+Pro"),
    ("Nunito", "Nunito"),
    ("Poppins", "Poppins"),
]

# Direct download URLs - using verified working sources
DIRECT_FONTS = {
    # 1. Osifont
    "osifont": "https://github.com/hikikomori82/osifont/raw/master/osifont.ttf",
    
    # 2. Overpass (from RedHat official repo)
    "Overpass-Regular": "https://github.com/RedHatOfficial/Overpass/raw/master/fonts/ttf/Overpass-Regular.ttf",
    "Overpass-Bold": "https://github.com/RedHatOfficial/Overpass/raw/master/fonts/ttf/Overpass-Bold.ttf",
    "Overpass-Italic": "https://github.com/RedHatOfficial/Overpass/raw/master/fonts/ttf/Overpass-Italic.ttf",
    
    # 3. Roboto (from googlefonts repo)
    "Roboto-Regular": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "Roboto-Bold": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "Roboto-Italic": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Italic.ttf",
    
    # 4. Open Sans (from googlefonts repo)
    "OpenSans-Regular": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Regular.ttf",
    "OpenSans-Bold": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf",
    "OpenSans-Italic": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Italic.ttf",
    
    # 5. Lato (works from google/fonts)
    "Lato-Regular": "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf",
    "Lato-Bold": "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Bold.ttf",
    "Lato-Italic": "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Italic.ttf",
    
    # 6. Montserrat (from official repo)
    "Montserrat-Regular": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf",
    "Montserrat-Bold": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
    "Montserrat-Italic": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Italic.ttf",
    
    # 7. Source Sans 3 (from adobe repo)
    "SourceSans3-Regular": "https://github.com/adobe-fonts/source-sans/raw/release/TTF/SourceSans3-Regular.ttf",
    "SourceSans3-Bold": "https://github.com/adobe-fonts/source-sans/raw/release/TTF/SourceSans3-Bold.ttf",
    "SourceSans3-Italic": "https://github.com/adobe-fonts/source-sans/raw/release/TTF/SourceSans3-It.ttf",
    
    # 8. Nunito (from fontsource CDN - more reliable)
    "Nunito-Regular": "https://cdn.jsdelivr.net/fontsource/fonts/nunito@latest/latin-400-normal.ttf",
    "Nunito-Bold": "https://cdn.jsdelivr.net/fontsource/fonts/nunito@latest/latin-700-normal.ttf",
    "Nunito-Italic": "https://cdn.jsdelivr.net/fontsource/fonts/nunito@latest/latin-400-italic.ttf",
    
    # 9. Poppins (works from google/fonts)
    "Poppins-Regular": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf",
    "Poppins-Bold": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-Italic": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Italic.ttf",
}

# Font families for counting (not counting bold/italic separately)
FONT_FAMILIES = [
    "Osifont", "Overpass", "Roboto", "Open Sans", "Lato", 
    "Montserrat", "Source Sans 3", "Nunito", "Poppins"
]


def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"  Downloading: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def download_google_font(family_name, display_name):
    """Download a font family from Google Fonts."""
    print(f"\nDownloading {display_name}...")
    
    # Google Fonts API URL for downloading
    url = f"https://fonts.google.com/download?family={family_name}"
    zip_path = FONTS_DIR / f"{display_name}.zip"
    
    try:
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract the zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract only .ttf files
            for file_info in zip_ref.namelist():
                if file_info.endswith('.ttf'):
                    # Extract to fonts directory with simple name
                    filename = os.path.basename(file_info)
                    source = zip_ref.open(file_info)
                    target = open(FONTS_DIR / filename, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print(f"  Extracted: {filename}")
        
        # Remove zip file
        zip_path.unlink()
        return True
        
    except Exception as e:
        print(f"  Error downloading {display_name}: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False


def main():
    print("=" * 50)
    print("3D Label Generator - Font Downloader")
    print("=" * 50)
    
    # Create fonts directory
    FONTS_DIR.mkdir(exist_ok=True)
    print(f"\nFonts directory: {FONTS_DIR}")
    
    # Download all fonts directly from GitHub
    print(f"\n--- Downloading {len(FONT_FAMILIES)} Font Families ---")
    print("(each with Regular, Bold, Italic variants)\n")
    
    file_success = 0
    file_fail = 0
    
    for name, url in DIRECT_FONTS.items():
        # Determine file extension from URL
        ext = ".otf" if url.endswith(".otf") else ".ttf"
        dest = FONTS_DIR / f"{name}{ext}"
        if dest.exists():
            print(f"[OK] {name} (exists)")
            file_success += 1
        else:
            print(f"Downloading {name}...", end=" ", flush=True)
            if download_file(url, dest):
                print("[OK]")
                file_success += 1
            else:
                print("[FAILED]")
                file_fail += 1
    
    # Count font families
    family_count = 0
    for family in FONT_FAMILIES:
        # Check if at least Regular variant exists (ttf or otf)
        base = family.replace(" ", "")
        if family == "Osifont":
            if (FONTS_DIR / "osifont.ttf").exists():
                family_count += 1
        elif family == "Source Sans 3":
            if (FONTS_DIR / "SourceSans3-Regular.ttf").exists():
                family_count += 1
        elif family == "Overpass":
            if (FONTS_DIR / "Overpass-Regular.otf").exists():
                family_count += 1
        else:
            if (FONTS_DIR / f"{base}-Regular.ttf").exists():
                family_count += 1
    
    # List downloaded fonts
    print("\n" + "=" * 50)
    print("Downloaded fonts:")
    print("=" * 50)
    for font_file in sorted(list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))):
        size_kb = font_file.stat().st_size / 1024
        print(f"  - {font_file.name} ({size_kb:.1f} KB)")
    
    print("\n" + "=" * 50)
    print(f"Result: {family_count}/{len(FONT_FAMILIES)} font families available")
    print(f"        {file_success} files OK, {file_fail} failed")
    print("\nNote: Arial Rounded requires manual installation")
    print("      (it's a commercial font)")
    print("=" * 50)


if __name__ == "__main__":
    main()
