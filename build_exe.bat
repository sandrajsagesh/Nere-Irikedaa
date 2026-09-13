@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Building Nere Irikedaa Standalone Windows Application
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Verifying PyInstaller installation...
py -3.14 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    py -3.14 -m pip install pyinstaller
)

echo [2/3] Compiling standalone package with PyInstaller...
py -3.14 -m PyInstaller --clean --noconfirm nere_irikedaa.spec
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [3/3] Synchronizing companion assets and model tasks to dist folder...
if not exist "dist\Nere Irikedaa" (
    echo [ERROR] dist\Nere Irikedaa was not found!
    pause
    exit /b 1
)

copy /y "face_landmarker.task" "dist\Nere Irikedaa\" >nul
copy /y "pose_landmarker_lite.task" "dist\Nere Irikedaa\" >nul
if exist "assets" xcopy /y /e /i "assets" "dist\Nere Irikedaa\assets" >nul

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo   Executable location:
echo   %~dp0dist\Nere Irikedaa\Nere Irikedaa.exe
echo ============================================================
echo.
pause
