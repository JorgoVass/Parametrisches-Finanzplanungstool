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

# ===== Variante A (mit Jahr): Mitarbeiter mit (rolle, gehalt, startmonat, startjahr, optional endmonat, endjahr) =====
def _ym_to_ordinal(monat:int, jahr:int) -> int:
    """Wandelt (Monat, Jahr) in fortlaufenden Index (Jahre*12 + Monat) um."""
    return int(jahr) * 12 + int(monat)

def mitarbeiter_aktiv_im(monat: int, jahr: int, m: dict) -> bool:
    """
    Aktiv, wenn (startmonat/startjahr) <= (monat/jahr) <= (endmonat/endjahr) (falls Enddatum gesetzt).
    Rückwärtskompatibel: fehlen Jahresfelder, wird startjahr=1900, endjahr=None angenommen.
    """
    try:
        startmonat = int(m.get("startmonat"))
        if not (1 <= startmonat <= 12): return False
        startjahr = m.get("startjahr")
        startjahr = int(startjahr) if startjahr not in (None, "",) else 1900  # legacy fallback

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

# --- monatsdaten (serverseitig berechnet aus components + aktuellen Personalkosten) ---
@app.route("/monatsdaten")
def monatsdaten():
    daten = safe_load_json(DATEN_DATEI, [])
    personal = safe_load_json(PERSONAL_DATEI, [])

    daten_berechnet = []
    for d in daten:
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

    daten_berechnet.sort(key=lambda x: (x["jahr"], convertiere_monat_to_num(x["monat"])))
    return render_template("monatsdaten.html", daten=daten_berechnet)

# --- personal (Endpoint explizit als 'personal') ---
@app.route("/personal", methods=["GET", "POST"], endpoint="personal")
def personal_view():
    # Datei sicherstellen
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
                # Optionales Plausibilitäts-Check Ende >= Start
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

    # Jahre sammeln
    jahre = sorted(list({int(d.get("jahr", 0)) for d in daten if "jahr" in d and isinstance(d.get("jahr"), int)}))
    if not jahre:
        jahre = [datetime.now().year]

    # Jahr-Auswahl
    jahr_auswahl = request.args.get("jahr", str(jahre[-1]))

    # Filtern nach Jahr
    if jahr_auswahl == "alle":
        daten_jahr = daten
    else:
        jahr_auswahl_int = int(jahr_auswahl)
        daten_jahr = [d for d in daten if int(d.get("jahr", 0)) == jahr_auswahl_int]

    # Sortierung
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

    # X-Achsen-Kategorien (Labels)
    monate = [f"{d['monat']} {d['jahr']}" for d in daten_sorted] if jahr_auswahl == "alle" else [d["monat"] for d in daten_sorted]

    # Dynamische Neu-Berechnung aus Komponenten (Fallback + Flag-Logik)
    revenues = []
    costs_liste = []
    profits = []
    personalkosten_liste = []

    for d in daten_sorted:
        j = int(d.get("jahr", jahre[-1]))
        mnum = convertiere_monat_to_num(d["monat"])

        # Personalkosten (mit Jahr-Logik)
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

    # Kumulierte Gewinne & Break-Even (erstes Mal >= 0)
    kumulierte_gewinn = []
    s = 0.0
    break_even_monat = None
    for i, p in enumerate(profits):
        s += float(p)
        kumulierte_gewinn.append(s)
        if break_even_monat is None and s >= 0:
            break_even_monat = monate[i] if i < len(monate) else None

    # --- Plot ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monate, y=revenues,            mode='lines+markers', name='Umsatz'))
    fig.add_trace(go.Scatter(x=monate, y=costs_liste,         mode='lines+markers', name='Kosten'))
    fig.add_trace(go.Scatter(x=monate, y=profits,             mode='lines+markers', name='Gewinn'))
    fig.add_trace(go.Scatter(x=monate, y=personalkosten_liste,mode='lines+markers', name='Mitarbeiterkosten'))
    fig.add_trace(go.Scatter(x=monate, y=kumulierte_gewinn,   mode='lines+markers', name='Kumul. Gewinn', line=dict(dash="dash")))

    # X-Achse als Kategorie in deiner Reihenfolge pinnen
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=monate)

    # Vertikale Break-Even-Linie (yref='paper' → volle Höhe)
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

# ---------- ECONOMICS (dein bestehender Block; unverändert gelassen) ----------
def _npv(series, r):
    return sum(v / ((1 + r) ** t) for t, v in enumerate(series))

def _cum(xs):
    s = 0
    out = []
    for v in xs:
        s += v
        out.append(s)
    return out

def economics_calculation(p):
    T = int(p["time_horizon_years"])
    r = float(p["discount_rate"])

    surgery_cost = (
        p["or_time_min"] * p["or_cost_per_min"]
        + p["surgeon_fee"] + p["anesthesia_fee"] + p["hospital_case_fee"]
        + p["consumables_cost"]
        + p["post_op_days"] * p["post_op_daily_cost"]
        + p["implant_unit_cost"]
        + p["complication_prob"] * p["complication_cost"]
    )

    payer_op   = p["reimb_rate_surgery"] * surgery_cost
    patient_op = surgery_cost - payer_op + p["patient_copay_flat"] * p["post_op_days"]

    followup = p["followup_per_year"] * p["followup_cost_each"]
    repl_years = set(range(p["device_lifetime_years"], T + 1, p["device_lifetime_years"]))

    impl_total   = [surgery_cost] + [0]*T
    impl_payer   = [payer_op] + [0]*T
    impl_patient = [patient_op] + [0]*T
    for t in range(1, T + 1):
        repl = p["implant_unit_cost"] if t in repl_years else 0
        extra = followup + repl
        impl_total[t]   += extra
        payer_extra     = p["reimb_rate_surgery"] * (followup + repl)
        impl_payer[t]   += payer_extra
        impl_patient[t] += extra - payer_extra

    cons_y = (12 * p["monthly_supplies_cost"] + 12 * p["monthly_care_time_cost"] + p["annual_complication_cost_conservative"])
    cons_total   = [0] + [cons_y]*T
    cons_payer   = [0] + [p["reimb_rate_conservative"] * cons_y]*T
    cons_patient = [cons_total[t] - cons_payer[t] for t in range(T+1)]

    npv_dict = {
        "implant_total":   _npv(impl_total, r),
        "conserv_total":   _npv(cons_total, r),
        "implant_payer":   _npv(impl_payer, r),
        "conserv_payer":   _npv(cons_payer, r),
        "implant_patient": _npv(impl_patient, r),
        "conserv_patient": _npv(cons_patient, r),
    }

    cum_impl = _cum(impl_total)
    cum_cons = _cum(cons_total)
    years = list(range(0, T + 1))
    breakeven_year = None
    for t in range(0, T + 1):
        if cum_impl[t] <= cum_cons[t]:
            breakeven_year = t
            break

    unit_margin = p["selling_price_implant"] - p["cogs_implant"] - p["sales_cost_per_case"]
    breakeven_units = math.ceil(max(1.0, p["overhead_per_year"] / max(1e-9, unit_margin)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=cum_impl, mode="lines+markers", name="Implantat (kumuliert)"))
    fig.add_trace(go.Scatter(x=years, y=cum_cons, mode="lines+markers", name="Konservativ (kumuliert)"))
    if breakeven_year is not None:
        y_min = min(cum_impl + cum_cons)
        y_max = max(cum_impl + cum_cons)
        fig.add_trace(go.Scatter(
            x=[breakeven_year, breakeven_year],
            y=[y_min, y_max],
            mode="lines",
            name=f"Break-Even Jahr {breakeven_year}",
            line=dict(width=2, dash="dot")
        ))
    fig.update_layout(xaxis_title="Jahr", yaxis_title="€", template="plotly_white", margin=dict(t=30))
    plot_html = pio.to_html(fig, full_html=False)

    return {
        "plot_html": plot_html,
        "breakeven_year": breakeven_year,
        "npv": npv_dict,
        "startup": {"unit_margin": unit_margin, "breakeven_units": breakeven_units}
    }

@app.route("/economics", methods=["GET", "POST"])
def economics():
    defaults = {
        "time_horizon_years": 10,
        "discount_rate": 0.03,
        "payer_type": "GKV",
        "reimb_rate_surgery": 0.90,
        "reimb_rate_conservative": 0.70,
        "patient_copay_flat": 10.0,

        "implant_unit_cost": 2600.0,
        "device_lifetime_years": 7,
        "followup_per_year": 2,
        "followup_cost_each": 80.0,
        "complication_prob": 0.05,
        "complication_cost": 600.0,

        "or_time_min": 90,
        "or_cost_per_min": 20.0,
        "surgeon_fee": 600.0,
        "anesthesia_fee": 300.0,
        "hospital_case_fee": 2500.0,
        "consumables_cost": 180.0,
        "post_op_days": 2,
        "post_op_daily_cost": 350.0,

        "monthly_supplies_cost": 120.0,
        "monthly_care_time_cost": 0.0,
        "annual_complication_cost_conservative": 150.0,

        "selling_price_implant": 4200.0,
        "cogs_implant": 1900.0,
        "sales_cost_per_case": 200.0,
        "overhead_per_year": 350000.0
    }

    if request.method == "POST":
        def getf(name, typ=float):
            val = request.form.get(name, "")
            if val == "": return defaults[name]
            return typ(val)

        params = defaults.copy()
        params.update({
            "time_horizon_years": getf("time_horizon_years", int),
            "discount_rate": getf("discount_rate"),
            "payer_type": request.form.get("payer_type", defaults["payer_type"]),
            "reimb_rate_surgery": getf("reimb_rate_surgery"),
            "reimb_rate_conservative": getf("reimb_rate_conservative"),
            "patient_copay_flat": getf("patient_copay_flat"),

            "implant_unit_cost": getf("implant_unit_cost"),
            "device_lifetime_years": getf("device_lifetime_years", int),
            "followup_per_year": getf("followup_per_year", int),
            "followup_cost_each": getf("followup_cost_each"),
            "complication_prob": getf("complication_prob"),
            "complication_cost": getf("complication_cost"),

            "or_time_min": getf("or_time_min", int),
            "or_cost_per_min": getf("or_cost_per_min"),
            "surgeon_fee": getf("surgeon_fee"),
            "anesthesia_fee": getf("anesthesia_fee"),
            "hospital_case_fee": getf("hospital_case_fee"),
            "consumables_cost": getf("consumables_cost"),
            "post_op_days": getf("post_op_days", int),
            "post_op_daily_cost": getf("post_op_daily_cost"),

            "monthly_supplies_cost": getf("monthly_supplies_cost"),
            "monthly_care_time_cost": getf("monthly_care_time_cost"),
            "annual_complication_cost_conservative": getf("annual_complication_cost_conservative"),

            "selling_price_implant": getf("selling_price_implant"),
            "cogs_implant": getf("cogs_implant"),
            "sales_cost_per_case": getf("sales_cost_per_case"),
            "overhead_per_year": getf("overhead_per_year")
        })

        result = economics_calculation(params)
        return render_template("economics.html", params=params, **result)

    return render_template("economics.html", params=defaults, plot_html=None, breakeven_year=None,
                           npv=None, startup=None)

# ===== Raster: Jährlicher Vergleich (ohne Post-OP-Tage) =====
def _calc_surgery_cost_min(params):
    return params["surgeon_fee"] + params["anesthesia_fee"] + params["consumables_cost"] + params["implant_unit_cost"]

def _monthly_conservative_min(params):
    return params["monthly_supplies_cost"] + params["monthly_care_time_cost"]

@app.route("/raster", methods=["GET","POST"])
def raster():
    defaults = {
        "implant_unit_cost": 2600.0, "surgeon_fee": 600.0, "anesthesia_fee": 300.0, "consumables_cost": 180.0,
        "monthly_supplies_cost": 120.0, "monthly_care_time_cost": 0.0, "surgery_month": 3
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
            "consumables_cost": getf("consumables_cost"),
            "monthly_supplies_cost": getf("monthly_supplies_cost"),
            "monthly_care_time_cost": getf("monthly_care_time_cost"),
            "surgery_month": getf("surgery_month", int),
        })
    else:
        params = defaults

    cons_year = 12.0 * _monthly_conservative_min(params)
    op_year   = _calc_surgery_cost_min(params)
    totals = {"cons": round(cons_year, 2), "op": round(op_year, 2), "delta": round(op_year - cons_year, 2)}

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Konservativ (Jahr)", x=["Konservativ"], y=[totals["cons"]]))
    fig.add_trace(go.Bar(name="OP (Jahr)",          x=["OP"],           y=[totals["op"]]))
    fig.update_layout(barmode="group", xaxis_title="Szenario", yaxis_title="Kosten im Jahr (€)",
                      template="plotly_white", margin=dict(t=30),
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    delta_text = f"Δ (OP − Kons.): {totals['delta']:+.2f} €"
    y_max = max(totals["cons"], totals["op"])
    x_pos = "Konservativ" if totals["cons"] >= totals["op"] else "OP"
    fig.add_annotation(x=x_pos, y=y_max, yshift=10, text=delta_text, showarrow=False, bgcolor="rgba(255,255,255,0.85)")
    plot_html = pio.to_html(fig, full_html=False)

    return render_template("raster.html", params=params, totals=totals, plot_html=plot_html)

if __name__ == "__main__":
    app.run(debug=True)
