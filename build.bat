@echo off
echo ========================================
echo  Payment Management System - Build
echo ========================================

echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
  --name "PaymentManagementSystem" ^
  --add-data "." ^
  --hidden-import customtkinter ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import openpyxl ^
  --hidden-import reportlab ^
  --hidden-import reportlab.graphics.barcode.code93 ^
  --hidden-import reportlab.graphics.barcode.common ^
  --hidden-import reportlab.graphics.barcode.ecc200datamatrix ^
  --hidden-import reportlab.graphics.barcode.lto ^
  --hidden-import reportlab.graphics.barcode.qr ^
  --hidden-import reportlab.graphics.barcode.usps ^
  --hidden-import reportlab.graphics.barcode.usps4s ^
  --hidden-import reportlab.graphics.barcode.widgets ^
  --collect-data customtkinter ^
  main.py

echo.
echo [3/3] Done!
echo Your EXE is in the "dist" folder: dist\PaymentManagementSystem.exe
echo.
pause
