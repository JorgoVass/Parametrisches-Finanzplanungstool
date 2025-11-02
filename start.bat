@echo off
chcp 65001 > nul
color 0B
echo ========================================
echo   Finanzplanungs-Tool wird gestartet...
echo ========================================
echo.

REM Pruefen ob Python installiert ist
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FEHLER] Python ist nicht installiert!
    echo Bitte fuehre zuerst "setup.bat" aus.
    echo.
    pause
    exit /b 1
)

echo [INFO] Starte Flask-Server...
echo.
echo Die App wird im Browser geoeffnet unter:
echo http://localhost:5000
echo.
echo [WICHTIG] Schliesse dieses Fenster NICHT!
echo           Druecke STRG+C zum Beenden.
echo.
echo ========================================
echo.

start http://localhost:5000

python app.py

pause
```

6. **Speichern** → **Schließen**