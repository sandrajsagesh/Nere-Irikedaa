@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Building Nere Irikedaa Setup.exe Installer
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Verify working dist application build exists
if not exist "dist\Nere Irikedaa\Nere Irikedaa.exe" (
    echo [ERROR] Working standalone build not found at dist\Nere Irikedaa\Nere Irikedaa.exe
    echo Please run build_exe.bat first!
    pause
    exit /b 1
)

REM 2. Locate Inno Setup Compiler (ISCC.exe)
set "ISCC_EXE="

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    for /f "delims=" %%I in ('where iscc 2^>nul') do set "ISCC_EXE=%%I"
)

if "%ISCC_EXE%"=="" (
    echo [ERROR] Inno Setup Compiler ISCC.exe was not found!
    echo Please install Inno Setup 6 via winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

echo Found Inno Setup Compiler:
echo "%ISCC_EXE%"
echo.

REM 3. Compile installer script
echo Compiling Nere Irikedaa Setup.exe...
"%ISCC_EXE%" "installer.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup compilation failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   INSTALLER BUILD SUCCESSFUL!
echo   Installer location:
echo   %~dp0Nere Irikedaa Setup.exe
echo ============================================================
echo.
pause
