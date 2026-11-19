@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set "APP_NAME=Rapihin Aja"
set "PKG_NAME=rapihin-aja"
set "PYINSTALLER_BIN="

if exist ".venv\Scripts\pyinstaller.exe" (
    set "PYINSTALLER_BIN=.venv\Scripts\pyinstaller.exe"
) else (
    where pyinstaller >nul 2>nul
    if %errorlevel%==0 (
        set "PYINSTALLER_BIN=pyinstaller"
    )
)

if "%PYINSTALLER_BIN%"=="" (
    echo [ERROR] PyInstaller tidak ditemukan di .venv\Scripts\pyinstaller.exe maupun PATH.
    echo Silakan instal terlebih dahulu: .venv\Scripts\pip install pyinstaller
    exit /b 1
)

echo === Memulai build %APP_NAME% untuk Windows ===

if exist "dist\%PKG_NAME%" rmdir /s /q "dist\%PKG_NAME%"

"%PYINSTALLER_BIN%" ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --noconsole ^
    --name "%PKG_NAME%" ^
    --icon=assets\icon.ico ^
    --add-data "data;data" ^
    --add-data "ui\styles.qss;ui" ^
    --add-data "assets;assets" ^
    main.py

if errorlevel 1 (
    echo [ERROR] Build PyInstaller gagal.
    exit /b 1
)

if not exist "dist\%PKG_NAME%\%PKG_NAME%.exe" (
    echo [ERROR] File executable tidak ditemukan di dist\%PKG_NAME%\%PKG_NAME%.exe
    exit /b 1
)

echo === Build selesai: dist\%PKG_NAME%\%PKG_NAME%.exe ===
endlocal
