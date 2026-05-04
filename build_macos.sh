#!/bin/zsh
# build_macos.sh – sestaví PDFStamper.app
# Spusť z adresáře projektu s aktivním venv: source venv/bin/activate

set -e

echo "==> Kontrola venv..."
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "CHYBA: Aktivuj venv: source venv/bin/activate"
    exit 1
fi

echo "==> Instalace PyInstaller..."
pip install pyinstaller --quiet

echo "==> Čištění předchozích buildů..."
rm -rf build dist

echo "==> Sestavení .app..."
pyinstaller pdfstamper.spec

echo ""
echo "✓ Hotovo! Aplikace je v: dist/PDFStamper.app"
echo ""
echo "Poznámka: aplikace není code-signed. macOS ji může blokovat."
echo "Při prvním spuštění: pravý klik → Otevřít → Otevřít"
echo ""
echo "Pro distribuci podepsat:"
echo "  codesign --deep --force --sign '-' dist/PDFStamper.app"
