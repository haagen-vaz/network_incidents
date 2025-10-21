
import csv   # För att läsa CSV-filer
import os    # För att kunna skapa mappar och hantera filvägar


# Läs in CSV-filen till en lista av dictionaries
with open('network_incidents.csv', encoding='utf-8', newline="") as f:
    reader = csv.DictReader(f)   # Gör varje rad till en dictionary baserad på rubriker
    rows = list(reader)          # Lägg alla rader i en lista så vi kan loopa flera gånger


# Hjälpfunktion: gör text till heltal (t.ex. "135" eller "135,0" -> 135)
def to_int_safe(value, default=0):
    """Konvertera text till int, klarar svenska tal med komma."""
    s = (value or "").strip()      # Gör None till "" och ta bort mellanslag
    if s == "":                    # Om värdet är tomt, returnera 0
        return default
    s = s.replace(",", ".")        # Byt ut komma mot punkt så float() fungerar
    try:
        return int(float(s))       # Försök konvertera till float först, sen int
    except ValueError:
        return default             # Om värdet inte går att läsa som tal, returnera default (0)


# Hjälpfunktion: konvertera svensk kostnad ("12 345,67") till float
def parse_cost_sek(value, default=0.0):
    """Parsea svensk kostnad '12 345,67' -> 12345.67 (float)."""
    s = (value or "").strip()              # Trimma texten
    if s == "":                            # Tomt fält = 0.0
        return default
    s = s.replace("\u202f", " ")           # Ersätt smalt mellanslag (från Excel) med vanligt
    s = s.replace(" ", "")                 # Ta bort tusentalsavgränsare
    s = s.replace(",", ".")                # Byt komma till punkt
    try:
        return float(s)                    # Konvertera till float
    except ValueError:
        return default                     # Felaktigt värde → 0.0


# Hjälpfunktion: formatera tal till svenskt format (12345.67 -> "12 345,67")
def sek_fmt(n):
    """Formatera 12345.67 -> '12 345,67' för snygg utskrift."""
    s = f"{n:,.2f}"                        # Gör till sträng med två decimaler
    return s.replace(",", " ").replace(".", ",")  # Byt till svenska formatet


# Beräkna resolution-tider per severity (antal + snitt)
severity_sum = {}   # Totala minuter per severity
severity_cnt = {}   # Antal incidenter per severity

for row in rows:                                     # Gå igenom varje incident
    sev = (row["severity"] or "").strip().lower()    # Hämta severity, t.ex. "critical"
    mins = to_int_safe(row["resolution_minutes"], 0) # Gör om till int
    cost = parse_cost_sek(row["cost_sek"], 0.0)      # Läs in kostnad (kan användas senare)
    site = (row["site"] or "").strip()               # Läs in plats (site)

    # Om vi inte sett denna severity förut, skapa startvärden
    if sev not in severity_sum:
        severity_sum[sev] = 0
        severity_cnt[sev] = 0

    # Addera värden
    severity_sum[sev] += mins
    severity_cnt[sev] += 1


# Skriv ut resultat: antal och snitt-resolution per severity
print("Antal och genomsnittlig resolution per severity:")
for sev in severity_cnt:                             
    count = severity_cnt[sev]              # antal incidenter
    total = severity_sum[sev]              # totala minuter
    avg = total / count if count else 0    # snittminuter (skydd mot division med 0)
    print(f" - {sev:<8} : {count:>2} st, snitt {avg:.1f} min")


# Beräkna totalkostnad och snittkostnad per severity
severity_cost = {}    # total kostnad per severity
severity_count = {}   # antal incidenter per severity (igen, för snitt)

for row in rows:
    sev = (row["severity"] or "").strip().lower()   # severity
    cost = parse_cost_sek(row["cost_sek"], 0.0)     # kostnad

    if sev not in severity_cost:                    # initiera nycklar
        severity_cost[sev] = 0.0
        severity_count[sev] = 0

    severity_cost[sev] += cost                      # addera kostnaden
    severity_count[sev] += 1                        # öka räknare


# Skriv ut total och genomsnittlig kostnad per severity
print("\nTotalkostnad per severity:")
for sev in severity_cost:
    total = severity_cost[sev]
    avg   = total / severity_count[sev] if severity_count[sev] else 0.0
    print(f" - {sev:<8}: {sek_fmt(total)} SEK  (snitt {sek_fmt(avg)} SEK/incident)")


# Samla statistik per site i en ordbok
site_stats = {}  # {"Huvudkontor": {...}, "Datacenter": {...}, ...}

for row in rows:
    site = (row["site"] or "").strip()
    sev  = (row["severity"] or "").strip().lower()
    mins = to_int_safe(row["resolution_minutes"], 0)
    cost = parse_cost_sek(row["cost_sek"], 0.0)

    if site not in site_stats:
        site_stats[site] = {
            "total_incidents": 0,
            "critical_incidents": 0,
            "high_incidents": 0,
            "medium_incidents": 0,
            "low_incidents": 0,
            "sum_resolution": 0,
            "total_cost_sek": 0.0,
        }

    site_stats[site]["total_incidents"] += 1
    key = f"{sev}_incidents"          # bygger t.ex. "high_incidents"
    if key in site_stats[site]:
        site_stats[site][key] += 1
    site_stats[site]["sum_resolution"] += mins
    site_stats[site]["total_cost_sek"] += cost

# Räkna ut genomsnittlig resolution-tid per site
for site_name, data in site_stats.items():
    count = data["total_incidents"]
    avg = (data["sum_resolution"] / count) if count else 0.0
    data["avg_resolution_minutes"] = round(avg, 2)
    data["total_cost_sek"] = round(data["total_cost_sek"], 2)

# Skriv CSV med sammanfattning per site
OUT_DIR = "out"
os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "incidents_by_site.csv")

fieldnames = [
    "site",
    "total_incidents",
    "critical_incidents",
    "high_incidents",
    "medium_incidents",
    "low_incidents",
    "avg_resolution_minutes",
    "total_cost_sek",
]

with open(out_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for site in sorted(site_stats.keys()):
        d = site_stats[site]
        writer.writerow({
            "site": site,
            "total_incidents": d["total_incidents"],
            "critical_incidents": d["critical_incidents"],
            "high_incidents": d["high_incidents"],
            "medium_incidents": d["medium_incidents"],
            "low_incidents": d["low_incidents"],
            "avg_resolution_minutes": d["avg_resolution_minutes"],
            # punkt som decimal funkar fint i Excel
            "total_cost_sek": f'{d["total_cost_sek"]:.2f}',
        })

print(f"[OK] Skrev {out_path}")


# --- Problem devices: gruppera per enhet och skriv CSV ---

# Omvandla severity till ett numeriskt "allvarlighetsvärde" för snittberäkning
severity_score = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Samla statistik per device
dev_stats = {}  # t.ex. {"SW-DC-TOR-02": {...}, ...}

for row in rows:
    host = (row["device_hostname"] or "").strip()
    site = (row["site"] or "").strip()
    sev  = (row["severity"] or "").strip().lower()
    cost = parse_cost_sek(row["cost_sek"], 0.0)
    users = to_int_safe(row.get("affected_users"), 0)

    if host not in dev_stats:
        dev_stats[host] = {
            "device_hostname": host,
            "site": site,
            # device_type = prefix före första "-" (ex: "SW" i "SW-DC-TOR-02")
            "device_type": host.split("-")[0].lower() if "-" in host else "",
            "incident_count": 0,
            "sum_sev_score": 0.0,
            "total_cost": 0.0,
            "sum_users": 0,
        }

    dev_stats[host]["incident_count"] += 1
    dev_stats[host]["sum_sev_score"] += severity_score.get(sev, 0)
    dev_stats[host]["total_cost"] += cost
    dev_stats[host]["sum_users"] += users

# Gör en lista med färdiga rader och räkna snitt
problem_rows = []
for d in dev_stats.values():
    cnt = d["incident_count"]
    avg_sev = (d["sum_sev_score"] / cnt) if cnt else 0.0
    avg_usr = (d["sum_users"] / cnt) if cnt else 0.0
    problem_rows.append({
        "device_hostname": d["device_hostname"],
        "site": d["site"],
        "device_type": d["device_type"],
        "incident_count": cnt,
        "avg_severity_score": round(avg_sev, 2),
        "total_cost_sek": round(d["total_cost"], 2),
        "avg_affected_users": round(avg_usr, 2),
        # Vi har inte förra veckans lista i denna uppgift, så markera som okänt
        "in_last_weeks_warnings": "no_data",
    })

# Sortera: flest incidents först, sedan högst total kostnad
problem_rows.sort(key=lambda r: (-r["incident_count"], -r["total_cost_sek"]))

# Skriv CSV
out_path_pd = os.path.join(OUT_DIR, "problem_devices.csv")
with open(out_path_pd, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "device_hostname","site","device_type",
        "incident_count","avg_severity_score",
        "total_cost_sek","avg_affected_users","in_last_weeks_warnings"
    ])
    writer.writeheader()
    for r in problem_rows:
        # se till att kostnaden skrivs med punkt som decimal i CSV
        r_out = dict(r)
        r_out["total_cost_sek"] = f'{r["total_cost_sek"]:.2f}'
        writer.writerow(r_out)

print(f"[OK] Skrev {out_path_pd}")



#  cost_analysis.csv 

# Liten hjälpare: säkert float-parsning (tål svenska komma och mellanslag)
def to_float_safe(value, default=0.0):
    s = (value or "").strip()
    if s == "":
        return default
    # ta bort ev. smalt/vanligt mellanslag som tusentalsavgränsare
    s = s.replace("\u202f", " ").replace(" ", "")
    # byt komma till punkt så Python kan läsa decimaler
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default

# Samla statistik per vecka i en ordbok
# Exempelstruktur: {36: {"total_cost": 0.0, "count": 0, "impact_sum": 0.0}}
week_stats = {}

for row in rows:
    # Hämta veckonummer som int (tål "36", "36.0", "36,0")
    week = to_int_safe(row.get("week_number"), 0)
    # Kostnad i SEK som float (svensk parsing)
    cost = parse_cost_sek(row.get("cost_sek"), 0.0)
    # Impact score (kan vara tom sträng → 0.0)
    impact = to_float_safe(row.get("impact_score"), 0.0)

    if week not in week_stats:
        week_stats[week] = {"total_cost": 0.0, "count": 0, "impact_sum": 0.0}

    week_stats[week]["total_cost"] += cost      # summera kostnaden för veckan
    week_stats[week]["count"] += 1              # räkna incidenter i veckan
    week_stats[week]["impact_sum"] += impact    # summera impact för snitt senare

# Gör rader klara för CSV 
weekly_rows = []
for week in sorted(week_stats.keys()):
    total_cost = round(week_stats[week]["total_cost"], 2)
    count = week_stats[week]["count"]
    avg_impact = round(
        (week_stats[week]["impact_sum"] / count) if count else 0.0, 2
    )

    weekly_rows.append({
        "week_number": week,
        "total_incidents": count,
        # skriv ut med punkt som decimal så Excel/Sheets läser talet
        "total_cost_sek": f"{total_cost:.2f}",
        "avg_impact_score": avg_impact,
    })

# Skriv CSV till out/cost_analysis.csv
os.makedirs(OUT_DIR, exist_ok=True)
out_path_cost = os.path.join(OUT_DIR, "cost_analysis.csv")

with open(out_path_cost, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["week_number", "total_incidents", "total_cost_sek", "avg_impact_score"]
    )
    writer.writeheader()
    for r in weekly_rows:
        writer.writerow(r)

print(f"[OK] Skrev {out_path_cost}")





# Textrapport


# Hämta heltal säkert för affected_users i listningen nedan
def users_int_safe(v, default=0):
    s = (v or "").strip()
    if s == "":
        return default
    try:
        return int(float(s.replace(",", ".")))
    except ValueError:
        return default

# Sammanställ grunddata till rapporten
total_incidents = len(rows)  # hur många rader totalt
total_cost = sum(parse_cost_sek(r.get("cost_sek"), 0.0) for r in rows)  # summera kostnader

# period (min/max vecka)
all_weeks = [to_int_safe(r.get("week_number"), 0) for r in rows if r.get("week_number") is not None]
min_week = min(all_weeks) if all_weeks else None
max_week = max(all_weeks) if all_weeks else None

# genomsnittlig resolution per severity
def avg_res_min(sev):
    cnt = severity_cnt.get(sev, 0)
    tot = severity_sum.get(sev, 0)
    return (tot / cnt) if cnt else 0.0

# genomsnittlig kostnad per severity
from collections import defaultdict
sev_costs = defaultdict(float)
sev_counts = defaultdict(int)
for r in rows:
    sev = (r.get("severity") or "").strip().lower()
    c = parse_cost_sek(r.get("cost_sek"), 0.0)
    sev_costs[sev] += c
    sev_counts[sev] += 1
def avg_cost_sek(sev):
    cnt = sev_counts.get(sev, 0)
    return (sev_costs.get(sev, 0.0) / cnt) if cnt else 0.0

# incidents som påverkat fler än 100 användare
big_impact = [r for r in rows if users_int_safe(r.get("affected_users"), 0) > 100]

# topp 5 dyraste incidents
top5_costly = sorted(
    rows,
    key=lambda r: parse_cost_sek(r.get("cost_sek"), 0.0),
    reverse=True
)[:5]

# lista alla sites och hitta de som saknar critical
sites = sorted({ (r.get("site") or "").strip() for r in rows })
site_crit = { s: 0 for s in sites }
for r in rows:
    s = (r.get("site") or "").strip()
    sev = (r.get("severity") or "").strip().lower()
    if sev == "critical":
        site_crit[s] += 1
sites_no_critical = [s for s in sites if site_crit.get(s, 0) == 0]

# bygg rad för rad i rapporten
lines = []
lines.append("=" * 80)
lines.append(" " * 22 + "INCIDENT ANALYSIS - SENASTE PERIODEN")
lines.append("=" * 80)
if min_week is not None and max_week is not None:
    lines.append(f"Analysperiod (veckor): {min_week} till {max_week}")
lines.append(f"Total incidents: {total_incidents} st")
lines.append(f"Total kostnad: {sek_fmt(total_cost)} SEK")
lines.append("")

# executive summary
lines.append("EXECUTIVE SUMMARY")
lines.append("-" * 25)
if sites_no_critical:
    lines.append(f"✓ POSITIVT: Inga critical incidents på {', '.join(sites_no_critical)}.")
if top5_costly:
    t0 = top5_costly[0]
    lines.append(
        f"⚠ KOSTNAD: Dyraste incident: {sek_fmt(parse_cost_sek(t0.get('cost_sek'), 0.0))} SEK "
        f"({t0.get('device_hostname')} {t0.get('category')})."
    )
lines.append("")

# incidents per severity
lines.append("INCIDENTS PER SEVERITY")
lines.append("-" * 25)
for sev in ["critical", "high", "medium", "low"]:
    cnt = severity_cnt.get(sev, 0)
    pct = (cnt / total_incidents * 100) if total_incidents else 0
    avg_min = avg_res_min(sev)
    avg_cost = avg_cost_sek(sev)
    lines.append(
        f"{sev.capitalize():<10}: {cnt:>3} st ({pct:>2.0f}%) - "
        f"Genomsnitt: {avg_min:>4.0f} min resolution, {sek_fmt(avg_cost)} SEK/incident"
    )
lines.append("")

# största påverkan
lines.append("STÖRSTA PÅVERKAN (>100 användare)")
lines.append("-" * 25)
if big_impact:
    for r in big_impact:
        users = users_int_safe(r.get("affected_users"), 0)
        cost = sek_fmt(parse_cost_sek(r.get("cost_sek"), 0.0))
        lines.append(
            f"- {r.get('ticket_id')} {(r.get('site') or ''):<12} {(r.get('device_hostname') or ''):<15}  "
            f"users={users:<3}  sev={(r.get('severity') or '').strip().lower():<8}  "
            f"kostnad= {cost}  SEK  {r.get('category')}"
        )
else:
    lines.append("- (inga händelser över 100 användare)")
lines.append("")

# topp 5 dyraste
lines.append("TOPP 5 DYRASTE INCIDENTS")
lines.append("-" * 25)
for r in top5_costly:
    cost = sek_fmt(parse_cost_sek(r.get("cost_sek"), 0.0))
    lines.append(
        f"- {r.get('ticket_id')} {(r.get('device_hostname') or ''):<15}  {(r.get('site') or ''):<14}  "
        f"{(r.get('severity') or '').strip().lower():<8}  {cost} SEK  ({r.get('category')})"
    )

# skriv filen
os.makedirs(OUT_DIR, exist_ok=True)
txt_path = os.path.join(OUT_DIR, "incident_analysis.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"[OK] Skrev {txt_path}")
