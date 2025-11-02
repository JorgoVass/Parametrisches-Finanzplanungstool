@echo off
chcp 65001 > nul
color 0A
echo ========================================
echo   Finanzplanungs-Tool Setup
echo ========================================
echo.

REM Pruefen ob Python installiert ist
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FEHLER] Python ist nicht installiert!
    echo.
    echo Bitte installiere Python von: https://www.python.org/downloads/
    echo Wichtig: Haken bei "Add Python to PATH" setzen!
    echo.
    pause
    exit /b 1
)

echo [OK] Python gefunden
python --version
echo.

echo [INFO] Installiere benoetigte Pakete...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [FEHLER] Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation erfolgreich!
echo ========================================
echo.
echo Starte jetzt "start.bat" um die App zu starten.
echo.
pause