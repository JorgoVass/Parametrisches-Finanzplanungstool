#!/bin/bash

echo "========================================"
echo "  Finanzplanungs-Tool wird gestartet..."
echo "========================================"
echo ""

# Prüfen ob Python installiert ist
if ! command -v python3 &> /dev/null
then
    echo "[FEHLER] Python3 ist nicht installiert!"
    echo "Bitte fuehre zuerst './setup.sh' aus."
    echo ""
    read -p "Druecke Enter zum Beenden..."
    exit 1
fi

echo "[INFO] Starte Flask-Server..."
echo ""
echo "Die App laeuft unter: http://localhost:5000"
echo ""
echo "[WICHTIG] Schliesse dieses Terminal NICHT!"
echo "          Druecke STRG+C zum Beenden."
echo ""
echo "========================================"
echo ""

# Browser öffnen (macOS)
open http://localhost:5000 2>/dev/null

python3 app.py
```