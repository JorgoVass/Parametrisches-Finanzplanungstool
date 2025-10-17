# Parametrisches-Finanzplanungstool
  FINANZPLANUNGS-TOOL - ANLEITUNG
_________________________________________________________________

VORAUSSETZUNG (EINMALIG):
Python 3.8 oder höher muss installiert sein

Prüfen: Terminal/CMD öffnen und eingeben: python --version
Falls "nicht gefunden": Python installieren von:
  -> Windows: https://www.python.org/downloads/
     WICHTIG: Haken setzen bei === "Add Python to PATH" ===
  -> Mac: Terminal: brew install python3
  -> Linux: Terminal: sudo apt-get install python3 python3-pip
_________________________________________________________________

WINDOWS:
1. "setup.bat" doppelklicken (nur beim ersten Mal)
   -> Prüft Python und installiert Flask + Plotly
   -> Dauert ca. 1-2 Minuten

2. "start.bat" doppelklicken
   -> Browser öffnet sich automatisch
   -> App läuft unter: http://localhost:5000
   -> CMD-Fenster NICHT schließen während der Nutzung!

Beenden: CMD-Fenster schließen oder STRG+C
_________________________________________________________________

MAC / LINUX:
1. Terminal öffnen und zum Ordner navigieren:
   cd /Pfad/zum/Ordner

2. Setup ausführen (nur beim ersten Mal):
   chmod +x setup.sh start.sh
   ./setup.sh

3. App starten:
   ./start.sh
_________________________________________________________________

FUNKTIONEN:

- Monatliche Finanzplanung mit automatischer Gewinn-/Verlustrechnung
- Personalkosten-Management (Mitarbeiter mit Zeiträumen)
- Interaktive Diagramme (Umsatz, Kosten, Gewinn)
- Automatische Break-Even-Berechnung
- Szenarienvergleich (Pessimistisch/Realistisch/Optimistisch)
- Kostenvergleich: Operation vs. Konservative Behandlung
- CSV-Export für Excel/LibreOffice
_________________________________________________________________

BEI PROBLEMEN:
"Python ist nicht installiert":
  -> Python installieren (siehe Voraussetzung oben)
  -> setup.bat / setup.sh erneut ausführen

Browser öffnet sich nicht:
  -> Manuell öffnen: http://localhost:5000
_________________________________________________________________

KONTAKT:
Jorgo Vassiliadis
FAU Erlangen-Nürnberg
