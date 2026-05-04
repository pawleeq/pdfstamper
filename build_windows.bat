@echo off
REM build_windows.bat – sestaví PDFStamper.exe
REM Spusť z adresáře projektu s aktivním venv

echo =^> Kontrola venv...
if "%VIRTUAL_ENV%"=="" (
    echo CHYBA: Aktivuj venv: venv\Scripts\activate
    exit /b 1
)

echo =^> Instalace závislostí...
pip install pyinstaller pymupdf PyQt6 cairosvg pillow reportlab cryptography pyhanko pyhanko-certvalidator --quiet

echo =^> Instalace GTK/Cairo pro Windows...
pip install cairocffi --quiet
REM Poznámka: na Windows cairo musí být dostupné přes GTK runtime nebo vcpkg
REM Stáhnout GTK3 runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

echo =^> Čištění...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo =^> Sestavení .exe...
pyinstaller pdfstamper.spec

echo.
echo Hotovo! Spustitelny soubor: dist\PDFStamper.exe
echo.
echo Poznamka: Pokud se neotevira, chybi GTK runtime.
echo Stahnout: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
pause
