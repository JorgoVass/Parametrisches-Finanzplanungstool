#!/bin/bash

echo "========================================"
echo "  Finanzplanungs-Tool Setup"
echo "========================================"
echo ""

# Prüfen ob Python installiert ist
if ! command -v python3 &> /dev/null
then
    echo "[FEHLER] Python3 ist nicht installiert!"
    echo ""
    echo "Bitte installiere Python3:"
    echo "  macOS: brew install python3"
    echo "  oder von: https://www.python.org/downloads/"
    echo ""
    read -p "Druecke Enter zum Beenden..."
    exit 1
fi

echo "[OK] Python gefunden"
python3 --version
echo ""

echo "[INFO] Installiere benoetigte Pakete..."
echo ""

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "[FEHLER] Installation fehlgeschlagen!"
    read -p "Druecke Enter zum Beenden..."
    exit 1
fi

echo ""
echo "========================================"
echo "  Installation erfolgreich!"
echo "========================================"
echo ""
echo "Starte jetzt './start.sh' um die App zu starten."
echo ""
read -p "Druecke Enter zum Beenden..."