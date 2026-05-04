#!/bin/bash
# build_linux.sh – sestaví PDFStamper binary
# Spusť z adresáře projektu s aktivním venv: source venv/bin/activate

set -e

echo "==> Kontrola venv..."
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "CHYBA: Aktivuj venv: source venv/bin/activate"
    exit 1
fi

echo "==> Systémové závislosti (vyžaduje sudo)..."
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev \
         libffi-dev shared-mime-info python3-dev
elif command -v dnf &>/dev/null; then
    sudo dnf install -y cairo-devel pango-devel gdk-pixbuf2-devel libffi-devel
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm cairo pango gdk-pixbuf2 libffi
fi

echo "==> Instalace Python závislostí..."
pip install pyinstaller pymupdf PyQt6 cairosvg pillow reportlab \
    cryptography pyhanko pyhanko-certvalidator --quiet

echo "==> Čištění..."
rm -rf build dist

echo "==> Sestavení binary..."
pyinstaller pdfstamper.spec

echo ""
echo "✓ Hotovo! Binary je v: dist/PDFStamper"
echo "Spuštění: ./dist/PDFStamper"

# Volitelně: zabalit do AppImage pro distribuci bez závislostí
if command -v appimagetool &>/dev/null; then
    echo ""
    echo "==> Vytváření AppImage..."
    mkdir -p PDFStamper.AppDir/usr/bin
    cp dist/PDFStamper PDFStamper.AppDir/usr/bin/
    cat > PDFStamper.AppDir/PDFStamper.desktop << EOF
[Desktop Entry]
Name=PDF Signature Stamper
Exec=PDFStamper
Type=Application
Categories=Office;
EOF
    appimagetool PDFStamper.AppDir dist/PDFStamper.AppImage
    echo "✓ AppImage: dist/PDFStamper.AppImage"
fi
