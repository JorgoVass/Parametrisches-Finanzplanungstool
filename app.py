# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
import json
import plotly.graph_objs as go
import plotly.io as pio
import os
from datetime import datetime
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATEN_DATEI = os.path.join(BASE_DIR, "daten.json")
PERSONAL_DATEI = os.path.join(BASE_DIR, "personal.json")

print("starte")

# ---------- Hilfsfunktionen ----------
def convertiere_monat_to_num(monatsname):
    monate = {
        "januar": 1, "februar": 2, "märz": 3, "april": 4,
        "mai": 5, "juni": 6, "juli": 7, "august": 8,
        "september": 9, "oktober": 10, "november": 11, "dezember": 12
    }
    return monate.get(monatsname.strip().lower(), 0)

def safe_load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

# =====  Mitarbeiter =====
def _ym_to_ordinal(monat:int, jahr:int) -> int:
    """Wandelt (Monat, Jahr) in fortlaufenden Index (Jahre*12 + Monat) um."""
    return int(jahr) * 12 + int(monat)

def mitarbeiter_aktiv_im(monat: int, jahr: int, m: dict) -> bool:
    """
    Aktiv, wenn (startmonat/startjahr) <= (monat/jahr) <= (endmonat/endjahr) (falls Enddatum gesetzt).
    Rückwärtskompatibel: fehlen Jahresfelder, wird startjahr=1900, endjahr=None angenommen.
    """
    try:
        startmonat = m.get("startmonat")
        if not startmonat or not isinstance(startmonat, int):
            return False
        if not (1 <= startmonat <= 12): 
            return False
            
        startjahr = m.get("startjahr")
        startjahr = int(startjahr) if startjahr not in (None, "",) else 1900

        endmonat = m.get("endmonat")
        endmonat = int(endmonat) if (endmonat not in (None, "",)) else None
        endjahr  = m.get("endjahr")
        endjahr  = int(endjahr) if (endjahr not in (None, "",)) else None

        cur = _ym_to_ordinal(monat, jahr)
        start = _ym_to_ordinal(startmonat, startjahr)

        if endmonat is not None and endjahr is not None:
            end = _ym_to_ordinal(endmonat, endjahr)
            return start <= cur <= end
        else:
            return start <= cur
    except Exception:
        return False

def berechne_personalkosten(monat_nummer: int, jahr: int, personal_liste: list) -> float:
    return sum(float(m.get("gehalt", 0.0)) for m in personal_liste if mitarbeiter_aktiv_im(monat_nummer, jahr, m))

def speichere_monatsdaten(monat, jahr, revenue, costs, profit, extra=None, personnel_included=False):
    daten = safe_load_json(DATEN_DATEI, [])

    def _merge_extra(e, extra_dict):
        if not extra_dict:
            return
        e["components"] = {
            "units": extra_dict.get("units"),
            "price": extra_dict.get("price"),
            "fixed_costs": extra_dict.get("fixed_costs"),
            "variable_costs": extra_dict.get("variable_costs"),
        }

    ersetzt = False
    for eintrag in daten:
        if eintrag["monat"].lower() == monat.lower() and int(eintrag.get("jahr", 0)) == int(jahr):
            eintrag["revenue"] = revenue
            eintrag["costs"]   = costs
            eintrag["profit"]  = profit
            eintrag["personnel_included"] = bool(personnel_included)
            _merge_extra(eintrag, extra)
            ersetzt = True
            break

    if not ersetzt:
        neu = {
            "monat": monat,
            "jahr": int(jahr),
            "revenue": revenue,
            "costs": costs,
            "profit": profit,
            "personnel_included": bool(personnel_included)
        }
        _merge_extra(neu, extra)
        daten.append(neu)

    with open(DATEN_DATEI, "w") as f:
        json.dump(daten, f, indent=2)

# ---------- Flask ----------
app = Flask(__name__)

# --- Start ---
@app.route("/")
def home():
    return render_template("index.html", current_year=datetime.now().year)

# --- bearbeiten (monat + jahr) ---
@app.route("/bearbeiten", methods=["GET", "POST"])
def bearbeiten():
    monat = request.args.get("monat")
    jahr = request.args.get("jahr", type=int)

    daten = safe_load_json(DATEN_DATEI, [])
    eintrag = next((e for e in daten if e["monat"].lower() == str(monat).lower() and int(e.get("jahr", 0)) == int(jahr)), None)
    if not eintrag:
        return "Eintrag nicht gefunden.", 404

    if request.method == "POST":
        eintrag["revenue"] = float(request.form["revenue"])
        eintrag["costs"] = float(request.form["costs"])
        eintrag["profit"] = float(request.form["profit"])
        with open(DATEN_DATEI, "w") as f:
            json.dump(daten, f, indent=2)
        return redirect(url_for("monatsdaten"))

    return render_template("bearbeiten.html", eintrag=eintrag)

# --- monatsdaten  ---
@app.route("/monatsdaten")
def monatsdaten():
    daten = safe_load_json(DATEN_DATEI, [])
    personal = safe_load_json(PERSONAL_DATEI, [])

    # Jahre sammeln
    jahre = sorted(list({int(d.get("jahr", 0)) for d in daten if "jahr" in d}))
    if not jahre:
        jahre = [datetime.now().year]

    # Jahr-Auswahl
    jahr_auswahl = request.args.get("jahr", "alle")

    # Filtern nach Jahr
    if jahr_auswahl == "alle":
        daten_gefiltert = daten
    else:
        jahr_auswahl_int = int(jahr_auswahl)
        daten_gefiltert = [d for d in daten if int(d.get("jahr", 0)) == jahr_auswahl_int]

    daten_berechnet = []
    for d in daten_gefiltert:
        monat = d.get("monat")
        jahr  = int(d.get("jahr", 0))
        mnum  = convertiere_monat_to_num(monat)

        comps = d.get("components") or {}
        units = comps.get("units")
        price = comps.get("price")
        fixed_costs = comps.get("fixed_costs")
        variable_costs = comps.get("variable_costs")

        pers = berechne_personalkosten(mnum, jahr, personal)

        if None not in (units, price, fixed_costs, variable_costs):
            revenue_calc = float(units) * float(price)
            costs_calc   = float(fixed_costs) + float(variable_costs) * float(units) + float(pers)
            profit_calc  = revenue_calc - costs_calc
        else:
            revenue_calc = float(d.get("revenue", 0.0))
            costs_stored = float(d.get("costs", 0.0))
            if not d.get("personnel_included", False):
                costs_stored += float(pers)
            costs_calc  = costs_stored
            profit_calc = revenue_calc - costs_calc

        daten_berechnet.append({
            "monat": monat,
            "jahr": jahr,
            "revenue_calc": round(revenue_calc, 2),
            "costs_calc": round(costs_calc, 2),
            "profit_calc": round(profit_calc, 2),
        })

    # Sortierung nach Jahr und Monat
    daten_berechnet.sort(key=lambda x: (x["jahr"], convertiere_monat_to_num(x["monat"])))
    
    return render_template("monatsdaten.html", 
                         daten=daten_berechnet,
                         jahre=jahre,
                         jahr_auswahl=jahr_auswahl)

# --- personal ---
@app.route("/personal", methods=["GET", "POST"], endpoint="personal")
def personal_view():
    if not os.path.exists(PERSONAL_DATEI):
        with open(PERSONAL_DATEI, "w") as f:
            json.dump([], f)

    mitarbeiter = safe_load_json(PERSONAL_DATEI, [])

    if request.method == "POST":
        try:
            rolle = (request.form.get("rolle") or "").strip()
            gehalt_raw = (request.form.get("gehalt") or "").strip()
            startmonat_raw = (request.form.get("startmonat") or "").strip()
            startjahr_raw  = (request.form.get("startjahr") or "").strip()
            endmonat_raw   = (request.form.get("endmonat") or "").strip()
            endjahr_raw    = (request.form.get("endjahr") or "").strip()

            if not rolle:
                return "Fehler: 'Rolle' darf nicht leer sein.", 400
            if gehalt_raw == "":
                return "Fehler: 'Monatsgehalt' darf nicht leer sein.", 400
            if startmonat_raw == "":
                return "Fehler: 'Startmonat' (1–12) ist erforderlich.", 400
            if startjahr_raw == "":
                return "Fehler: 'Startjahr' ist erforderlich.", 400

            gehalt = float(gehalt_raw.replace(",", "."))
            startmonat = int(startmonat_raw)
            startjahr  = int(startjahr_raw)

            if not (1 <= startmonat <= 12):
                return "Fehler: Startmonat muss zwischen 1 und 12 liegen.", 400
            if not (1900 <= startjahr <= 2100):
                return "Fehler: Startjahr muss zwischen 1900 und 2100 liegen.", 400

            endmonat = int(endmonat_raw) if endmonat_raw != "" else None
            endjahr  = int(endjahr_raw)  if endjahr_raw  != "" else None
            if (endmonat is None) ^ (endjahr is None):
                return "Fehler: Endmonat und Endjahr bitte gemeinsam angeben oder beide leer lassen.", 400
            if endmonat is not None:
                if not (1 <= endmonat <= 12):
                    return "Fehler: Endmonat muss zwischen 1 und 12 liegen.", 400
                if endjahr is None or not (1900 <= endjahr <= 2100):
                    return "Fehler: Endjahr muss zwischen 1900 und 2100 liegen.", 400
                if _ym_to_ordinal(endmonat, endjahr) < _ym_to_ordinal(startmonat, startjahr):
                    return "Fehler: Ende liegt vor dem Beginn.", 400

            mitarbeiter.append({
                "rolle": rolle,
                "gehalt": gehalt,
                "startmonat": startmonat,
                "startjahr": startjahr,
                "endmonat": endmonat,
                "endjahr": endjahr
            })
            with open(PERSONAL_DATEI, "w") as f:
                json.dump(mitarbeiter, f, indent=2)

            return redirect(url_for("personal"))

        except ValueError as ve:
            return f"Fehlerhafte Eingabe (Zahl erwartet): {ve}", 400
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Unerwarteter Fehler beim Speichern: {e}", 500

    return render_template("personal.html", mitarbeiter=mitarbeiter)

# --- personal/loeschen ---
@app.route("/personal/loeschen/<int:index>", methods=["POST"])
def personal_loeschen(index):
    mitarbeiter = safe_load_json(PERSONAL_DATEI, [])
    if 0 <= index < len(mitarbeiter):
        del mitarbeiter[index]
        with open(PERSONAL_DATEI, "w") as f:
            json.dump(mitarbeiter, f, indent=2)
    return redirect(url_for("personal"))

# --- calculate ---
@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        month = request.form["month"]
        jahr = int(request.form["jahr"])
        units = int(request.form["units"])
        price = float(request.form["price"])
        fixed_costs = float(request.form["fixed_costs"])
        variable_costs = float(request.form["variable_costs"])

        monat_num = convertiere_monat_to_num(month)
        if monat_num == 0:
            return "Fehler: Ungültiger Monatsname."

        personal = safe_load_json(PERSONAL_DATEI, [])
        personalkosten = berechne_personalkosten(monat_num, jahr, personal)

        revenue = units * price
        costs_total = fixed_costs + (variable_costs * units) + personalkosten
        profit = revenue - costs_total

        speichere_monatsdaten(
            month, jahr,
            revenue=revenue,
            costs=costs_total,
            profit=profit,
            extra={
                "units": units,
                "price": price,
                "fixed_costs": fixed_costs,
                "variable_costs": variable_costs
            },
            personnel_included=True
        )

        return redirect(url_for("diagramm"))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Fehler in CALCULATE: {str(e)}"

# --- diagramm ---
@app.route("/diagramm")
def diagramm():
    daten = safe_load_json(DATEN_DATEI, [])
    personal = safe_load_json(PERSONAL_DATEI, [])

    jahre = sorted(list({int(d.get("jahr", 0)) for d in daten if "jahr" in d and isinstance(d.get("jahr"), int)}))
    if not jahre:
        jahre = [datetime.now().year]

    jahr_auswahl = request.args.get("jahr", str(jahre[-1]))

    if jahr_auswahl == "alle":
        daten_jahr = daten
    else:
        jahr_auswahl_int = int(jahr_auswahl)
        daten_jahr = [d for d in daten if int(d.get("jahr", 0)) == jahr_auswahl_int]

    if jahr_auswahl == "alle":
        daten_sorted = sorted(
            daten_jahr,
            key=lambda d: (int(d.get("jahr", 0)), convertiere_monat_to_num(d["monat"]))
        )
    else:
        monats_sortierung = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                             "Juli", "August", "September", "Oktober", "November", "Dezember"]
        monats_sortierung_lower = [m.lower() for m in monats_sortierung]
        daten_sorted = sorted(
            daten_jahr,
            key=lambda d: monats_sortierung_lower.index(d["monat"].strip().lower())
            if d["monat"].strip().lower() in monats_sortierung_lower else 99
        )

    monate = [f"{d['monat']} {d['jahr']}" for d in daten_sorted] if jahr_auswahl == "alle" else [d["monat"] for d in daten_sorted]

    revenues = []
    costs_liste = []
    profits = []
    personalkosten_liste = []

    for d in daten_sorted:
        j = int(d.get("jahr", jahre[-1]))
        mnum = convertiere_monat_to_num(d["monat"])

        pers = berechne_personalkosten(mnum, j, personal)
        personalkosten_liste.append(pers)

        comps = d.get("components") or {}
        units = comps.get("units")
        price = comps.get("price")
        fixed_costs = comps.get("fixed_costs")
        variable_costs = comps.get("variable_costs")

        if None not in (units, price, fixed_costs, variable_costs):
            rev  = float(units) * float(price)
            cost = float(fixed_costs) + float(variable_costs) * float(units) + float(pers)
            prof = rev - cost
            revenues.append(rev)
            costs_liste.append(cost)
            profits.append(prof)
        else:
            rev_stored   = float(d["revenue"])
            cost_stored  = float(d["costs"])
            incl_flag    = bool(d.get("personnel_included", False))
            cost_effect  = cost_stored if incl_flag else (cost_stored + float(pers))
            prof_effect  = rev_stored - cost_effect

            revenues.append(rev_stored)
            costs_liste.append(cost_effect)
            profits.append(prof_effect)

    kumulierte_gewinn = []
    s = 0.0
    break_even_monat = None
    for i, p in enumerate(profits):
        s += float(p)
        kumulierte_gewinn.append(s)
        if break_even_monat is None and s >= 0:
            break_even_monat = monate[i] if i < len(monate) else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monate, y=revenues,            mode='lines+markers', name='Umsatz'))
    fig.add_trace(go.Scatter(x=monate, y=costs_liste,         mode='lines+markers', name='Kosten'))
    fig.add_trace(go.Scatter(x=monate, y=profits,             mode='lines+markers', name='Gewinn'))
    fig.add_trace(go.Scatter(x=monate, y=personalkosten_liste,mode='lines+markers', name='Mitarbeiterkosten'))
    fig.add_trace(go.Scatter(x=monate, y=kumulierte_gewinn,   mode='lines+markers', name='Kumul. Gewinn', line=dict(dash="dash")))

    fig.update_xaxes(type="category", categoryorder="array", categoryarray=monate)

    if break_even_monat is not None:
        fig.update_layout(shapes=[
            dict(
                type="line",
                xref="x", yref="paper",
                x0=break_even_monat, x1=break_even_monat,
                y0=0, y1=1,
                line=dict(color="black", width=2, dash="dot"),
            )
        ])
        fig.add_annotation(
            x=break_even_monat, xref="x",
            y=1, yref="paper",
            text=f"Break-Even: {break_even_monat}",
            showarrow=False,
            xanchor="left", yanchor="bottom",
            bgcolor="rgba(255,255,255,0.7)"
        )

    fig.update_layout(
        xaxis_title="Monat",
        yaxis_title="Betrag in Euro",
        template="plotly_white",
        margin=dict(t=30)
    )

    plot_html = pio.to_html(fig, full_html=False)

    return render_template(
        "diagramm.html",
        plot_html=plot_html,
        break_even_monat=break_even_monat,
        jahre=jahre,
        jahr_auswahl=jahr_auswahl
    )

# ===== Kostenvergleich: OP vs. Konservativ =====
@app.route("/kostenvergleich", methods=["GET","POST"])
def kostenvergleich():
    defaults = {
        "implant_unit_cost": 2600.0, 
        "surgeon_fee": 600.0, 
        "anesthesia_fee": 300.0, 
        "monthly_supplies_cost": 120.0, 
        "monthly_care_time_cost": 50.0,
    }

    def getf(name, typ=float):
        val = request.form.get(name, "")
        if val == "": return defaults[name]
        return typ(val)

    if request.method == "POST":
        params = defaults.copy()
        params.update({
            "implant_unit_cost": getf("implant_unit_cost"),
            "surgeon_fee": getf("surgeon_fee"),
            "anesthesia_fee": getf("anesthesia_fee"),
            "monthly_supplies_cost": getf("monthly_supplies_cost"),
            "monthly_care_time_cost": getf("monthly_care_time_cost"),
        })
    else:
        params = defaults

    # --- BERECHNUNG ---
    op_year = params["implant_unit_cost"] + params["surgeon_fee"] + params["anesthesia_fee"]
    cons_monthly = params["monthly_supplies_cost"] + params["monthly_care_time_cost"]
    cons_year = cons_monthly * 12

    # Delta
    delta = op_year - cons_year

    # --- PLOTLY DIAGRAMM ---
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=["Operation"],
        y=[op_year],
        name="Operation",
        marker_color="#779FB5",  
        text=[f"{op_year:,.2f} €"],
        textposition="outside"
    ))
    
    fig.add_trace(go.Bar(
        x=["Konservativ"],
        y=[cons_year],
        name="Konservativ",
        marker_color="#FF6B6B",  
        text=[f"{cons_year:,.2f} €"],
        textposition="outside"
    ))
    
    fig.update_layout(
        xaxis_title="Szenario",
        yaxis_title="Kosten im Jahr (€)",
        template="plotly_white",
        margin=dict(t=40, b=60),
        showlegend=False,
        barmode="group"
    )
    
    # Delta
    y_max = max(op_year, cons_year)
    delta_text = f"(OP − Konservativ): {delta:+,.2f} €"
    fig.add_annotation(
        x=0.5, xref="paper",
        y=y_max * 1.1, yref="y",
        text=delta_text,
        showarrow=False,
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#002F6C",  
        borderwidth=2,
        font=dict(size=16, color="#002F6C", family="Arial Black") 
    )
    
    plot_html = pio.to_html(fig, full_html=False)
    
    # --- ERGEBNISSE ---
    results = {
        "op_year": round(op_year, 2),
        "cons_year": round(cons_year, 2),
        "cons_monthly": round(cons_monthly, 2),
        "delta": round(delta, 2),
    }
    
    return render_template("kostenvergleich.html", params=params, results=results, plot_html=plot_html)

# ===== SZENARIEN-VERGLEICH =====
@app.route("/szenarien", methods=["GET", "POST"])
def szenarien():
    """
    Vergleicht 3 Szenarien (Pessimistisch/Realistisch/Optimistisch)
    basierend auf den aktuellen Monatsdaten mit verschiedenen Faktoren.
    """
    daten = safe_load_json(DATEN_DATEI, [])
    personal = safe_load_json(PERSONAL_DATEI, [])
    
    if not daten:
        return render_template("szenarien.html", 
                             plot_html=None, 
                             no_data=True,
                             results=None)
    
    # Szenarien-Definitionen 
    szenarien_params = {
        "Pessimistisch": {
            "units_faktor": 0.7,
            "preis_faktor": 0.95,
            "fixkosten_faktor": 1.15,
            "varkosten_faktor": 1.10,
            "color": "#E57373"
        },
        "Realistisch": {
            "units_faktor": 1.0,
            "preis_faktor": 1.0,
            "fixkosten_faktor": 1.0,
            "varkosten_faktor": 1.0,
            "color": "#779FB5"
        },
        "Optimistisch": {
            "units_faktor": 1.3,
            "preis_faktor": 1.05,
            "fixkosten_faktor": 0.95,
            "varkosten_faktor": 0.90,
            "color": "#A8C7DC"
        }
    }    
    # Jahre sammeln
    jahre = sorted(list({int(d.get("jahr", 0)) for d in daten}))
    if not jahre:
        jahre = [datetime.now().year]
    
    jahr_auswahl = request.args.get("jahr", str(jahre[-1]))
    
    # Filtern nach Jahr
    if jahr_auswahl == "alle":
        daten_jahr = daten
    else:
        jahr_auswahl_int = int(jahr_auswahl)
        daten_jahr = [d for d in daten if int(d.get("jahr", 0)) == jahr_auswahl_int]
    
    # Sortierung
    if jahr_auswahl == "alle":
        daten_sorted = sorted(daten_jahr, key=lambda d: (int(d.get("jahr", 0)), convertiere_monat_to_num(d["monat"])))
    else:
        monats_sortierung_lower = ["januar", "februar", "märz", "april", "mai", "juni",
                                   "juli", "august", "september", "oktober", "november", "dezember"]
        daten_sorted = sorted(daten_jahr, key=lambda d: monats_sortierung_lower.index(d["monat"].strip().lower())
                            if d["monat"].strip().lower() in monats_sortierung_lower else 99)
    
    # X-Achsen-Labels
    monate = [f"{d['monat']} {d['jahr']}" for d in daten_sorted] if jahr_auswahl == "alle" else [d["monat"] for d in daten_sorted]
    
    # Berechnung für jedes Szenario
    szenarien_ergebnisse = {}
    
    for szenario_name, params in szenarien_params.items():
        profits = []
        
        for d in daten_sorted:
            j = int(d.get("jahr", jahre[-1]))
            mnum = convertiere_monat_to_num(d["monat"])
            pers = berechne_personalkosten(mnum, j, personal)
            
            comps = d.get("components") or {}
            units = comps.get("units")
            price = comps.get("price")
            fixed_costs = comps.get("fixed_costs")
            variable_costs = comps.get("variable_costs")
            
            if None not in (units, price, fixed_costs, variable_costs):
                # Szenario-Faktoren anwenden
                units_adj = float(units) * params["units_faktor"]
                price_adj = float(price) * params["preis_faktor"]
                fixed_adj = float(fixed_costs) * params["fixkosten_faktor"]
                var_adj = float(variable_costs) * params["varkosten_faktor"]
                
                rev = units_adj * price_adj
                cost = fixed_adj + (var_adj * units_adj) + float(pers)
                prof = rev - cost
                profits.append(prof)
            else:
                profits.append(0.0)
        
        # Kumulierte Gewinne
        kumuliert = []
        s = 0.0
        break_even_monat = None
        break_even_index = None
        
        for i, p in enumerate(profits):
            s += p
            kumuliert.append(s)
            if break_even_monat is None and s >= 0:
                break_even_monat = monate[i] if i < len(monate) else None
                break_even_index = i
        
        # Gesamt-Gewinn
        total_profit = sum(profits)
        
        szenarien_ergebnisse[szenario_name] = {
            "kumuliert": kumuliert,
            "break_even_monat": break_even_monat,
            "break_even_index": break_even_index,
            "total_profit": round(total_profit, 2),
            "color": params["color"]
        }
    
    # Plotly
    fig = go.Figure()
    
    for szenario_name, ergebnis in szenarien_ergebnisse.items():
        fig.add_trace(go.Scatter(
            x=monate,
            y=ergebnis["kumuliert"],
            mode='lines+markers',
            name=szenario_name,
            line=dict(width=3, color=ergebnis["color"]),
            marker=dict(size=8)
        ))
        
        # Break-Even Marker
        if ergebnis["break_even_index"] is not None:
            idx = ergebnis["break_even_index"]
            fig.add_trace(go.Scatter(
                x=[monate[idx]],
                y=[ergebnis["kumuliert"][idx]],
                mode='markers+text',
                marker=dict(size=15, color=ergebnis["color"], symbol='star'),
                text=[f"✓ {szenario_name}"],
                textposition="top center",
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # Null-Linie
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=monate)
    fig.update_layout(
        title="Kumulierter Gewinn: Szenarien-Vergleich",
        xaxis_title="Monat",
        yaxis_title="Kumulierter Gewinn (€)",
        template="plotly_white",
        margin=dict(t=80, b=60),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    plot_html = pio.to_html(fig, full_html=False)
    
    return render_template("szenarien.html", 
                         plot_html=plot_html,
                         results=szenarien_ergebnisse,
                         jahre=jahre,
                         jahr_auswahl=jahr_auswahl,
                         no_data=False)


# --- CSV EXPORT ---
@app.route("/export_csv")
def export_csv():
    """Exportiert Monatsdaten als CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    daten = safe_load_json(DATEN_DATEI, [])
    personal = safe_load_json(PERSONAL_DATEI, [])
    
    # Jahr-Filter
    jahr_auswahl = request.args.get("jahr", "alle")
    
    if jahr_auswahl == "alle":
        daten_gefiltert = daten
    else:
        jahr_auswahl_int = int(jahr_auswahl)
        daten_gefiltert = [d for d in daten if int(d.get("jahr", 0)) == jahr_auswahl_int]
    
    # Daten berechnen 
    daten_berechnet = []
    for d in daten_gefiltert:
        monat = d.get("monat")
        jahr = int(d.get("jahr", 0))
        mnum = convertiere_monat_to_num(monat)
        
        comps = d.get("components") or {}
        units = comps.get("units")
        price = comps.get("price")
        fixed_costs = comps.get("fixed_costs")
        variable_costs = comps.get("variable_costs")
        
        pers = berechne_personalkosten(mnum, jahr, personal)
        
        if None not in (units, price, fixed_costs, variable_costs):
            revenue_calc = float(units) * float(price)
            costs_calc = float(fixed_costs) + float(variable_costs) * float(units) + float(pers)
            profit_calc = revenue_calc - costs_calc
        else:
            revenue_calc = float(d.get("revenue", 0.0))
            costs_stored = float(d.get("costs", 0.0))
            if not d.get("personnel_included", False):
                costs_stored += float(pers)
            costs_calc = costs_stored
            profit_calc = revenue_calc - costs_calc
        
        daten_berechnet.append({
            "Jahr": jahr,
            "Monat": monat,
            "Umsatz": round(revenue_calc, 2),
            "Kosten": round(costs_calc, 2),
            "Gewinn": round(profit_calc, 2),
            "Personalkosten": round(pers, 2)
        })
    
    # Sortieren
    daten_berechnet.sort(key=lambda x: (x["Jahr"], convertiere_monat_to_num(x["Monat"])))
    
    # CSV erstellen
    si = StringIO()
    if daten_berechnet:
        fieldnames = ["Jahr", "Monat", "Umsatz", "Kosten", "Gewinn", "Personalkosten"]
        writer = csv.DictWriter(si, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(daten_berechnet)
    
    # Response erstellen
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=monatsdaten_{jahr_auswahl}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return output

if __name__ == "__main__":
    app.run(debug=True)