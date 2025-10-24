import csv
import os
import datetime
from collections import defaultdict

# --- Läser in CSV med incidenter ---
with open("network_incidents.csv", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))  # varje rad blir en dict

# --- hjälpfunktioner
def parse_float(v, default=0.0):
    # text -> float, tar bort mellanslag och byter komma till punkt
    s = (v or "").strip().replace("\u202f", " ").replace(" ", "").replace(",", ".")
    if s == "":
        return default
    try:
        return float(s)
    except ValueError:
        return default

def to_int_safe(v, default=0):
    # text -> int (via float), tål t.ex. "135,0"
    f = parse_float(v, None)
    return int(f) if f is not None else default

def users_int_safe(v, default=0):
    # antal användare som int
    return to_int_safe(v, default)

def sek_fmt(n):
    # 12345.67 -> "12 345,67" (för utskrift i text)
    s = f"{n:,.2f}"
    return s.replace(",", " ").replace(".", ",")

def write_csv(path, fieldnames, rows_iter):
    # enkel CSV-skrivare
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_iter)

# --- För utdatafiler ---
OUT_DIR = "out"
os.makedirs(OUT_DIR, exist_ok=True)

# --- En loop: samla all severity-statistik (antal, minuter, kostnad) ---
severity_stats = defaultdict(lambda: {"count": 0, "sum_min": 0, "sum_cost": 0.0})
for r in rows:
    sev = (r.get("severity") or "").strip().lower()
    severity_stats[sev]["count"] += 1
    severity_stats[sev]["sum_min"] += to_int_safe(r.get("resolution_minutes"), 0)
    severity_stats[sev]["sum_cost"] += parse_float(r.get("cost_sek"), 0.0)

# för enkel åtkomst i utskrift
severity_cnt  = {k: v["count"] for k, v in severity_stats.items()}
severity_sum  = {k: v["sum_min"] for k, v in severity_stats.items()}
severity_cost = {k: v["sum_cost"] for k, v in severity_stats.items()}

# --- Statistik incidents_by_site.csv
site_stats = {}
for r in rows:
    site = (r.get("site") or "").strip()
    sev  = (r.get("severity") or "").strip().lower()
    mins = to_int_safe(r.get("resolution_minutes"), 0)
    cost = parse_float(r.get("cost_sek"), 0.0)

    if site not in site_stats:
        site_stats[site] = {
            "total_incidents": 0, "critical_incidents": 0, "high_incidents": 0,
            "medium_incidents": 0, "low_incidents": 0,
            "sum_resolution": 0, "total_cost_sek": 0.0,
        }

    site_stats[site]["total_incidents"] += 1
    key = f"{sev}_incidents"
    if key in site_stats[site]:
        site_stats[site][key] += 1
    site_stats[site]["sum_resolution"] += mins
    site_stats[site]["total_cost_sek"] += cost

# räkna fram snitt per site och skriv CSV
inc_site_csv = os.path.join(OUT_DIR, "incidents_by_site.csv")
site_rows = []
for site, d in sorted(site_stats.items()):
    avg_res = (d["sum_resolution"] / d["total_incidents"]) if d["total_incidents"] else 0.0
    site_rows.append({
        "site": site,
        "total_incidents": d["total_incidents"],
        "critical_incidents": d["critical_incidents"],
        "high_incidents": d["high_incidents"],
        "medium_incidents": d["medium_incidents"],
        "low_incidents": d["low_incidents"],
        "avg_resolution_minutes": round(avg_res, 2),
        "total_cost_sek": f'{d["total_cost_sek"]:.2f}',
    })
write_csv(inc_site_csv,
          ["site","total_incidents","critical_incidents","high_incidents",
           "medium_incidents","low_incidents","avg_resolution_minutes","total_cost_sek"],
          site_rows)
print(f"[OK] Skrev {inc_site_csv}")

# --- Problem devices
severity_score = {"low": 1, "medium": 2, "high": 3, "critical": 4}
dev_stats = {}
for r in rows:
    host = (r.get("device_hostname") or "").strip()
    if not host:
        continue
    site = (r.get("site") or "").strip()
    sev  = (r.get("severity") or "").strip().lower()
    cost = parse_float(r.get("cost_sek"), 0.0)
    users = users_int_safe(r.get("affected_users"), 0)

    if host not in dev_stats:
        # device_type = prefix före första "-" (ex "SW" i "SW-DC-TOR-02")
        dev_stats[host] = {
            "device_hostname": host, "site": site,
            "device_type": host.split("-")[0].lower() if "-" in host else "",
            "incident_count": 0, "sum_sev_score": 0.0, "total_cost": 0.0, "sum_users": 0
        }

    dev_stats[host]["incident_count"] += 1
    dev_stats[host]["sum_sev_score"] += severity_score.get(sev, 0)
    dev_stats[host]["total_cost"] += cost
    dev_stats[host]["sum_users"] += users

problem_rows = []
for d in dev_stats.values():
    cnt = d["incident_count"]
    problem_rows.append({
        "device_hostname": d["device_hostname"],
        "site": d["site"],
        "device_type": d["device_type"],
        "incident_count": cnt,
        "avg_severity_score": f'{(d["sum_sev_score"]/cnt if cnt else 0.0):.2f}',
        "total_cost_sek": f'{d["total_cost"]:.2f}',
        "avg_affected_users": f'{(d["sum_users"]/cnt if cnt else 0.0):.2f}',
    })


# sortera: flest incidents först, sedan dyrast
problem_rows.sort(key=lambda r: (-int(r["incident_count"]), -parse_float(r["total_cost_sek"], 0.0)))

problem_csv = os.path.join(OUT_DIR, "problem_devices.csv")
write_csv(
    problem_csv,
    [
        "device_hostname","site","device_type",
        "incident_count","avg_severity_score",
        "total_cost_sek","avg_affected_users"
    ],
    problem_rows
)
print(f"[OK] Skrev {problem_csv}")

# --- Kostnad per vecka + impact (cost_analysis.csv)
week_stats = defaultdict(lambda: {"total_cost": 0.0, "count": 0, "impact_sum": 0.0})
for r in rows:
    w = to_int_safe(r.get("week_number"), 0)
    week_stats[w]["total_cost"] += parse_float(r.get("cost_sek"), 0.0)
    week_stats[w]["count"] += 1
    week_stats[w]["impact_sum"] += parse_float(r.get("impact_score"), 0.0)

weekly_rows = []
for w in sorted(k for k in week_stats.keys() if k):
    total_cost = week_stats[w]["total_cost"]
    c = week_stats[w]["count"]
    avg_impact = (week_stats[w]["impact_sum"]/c) if c else 0.0
    weekly_rows.append({
        "week_number": w,
        "total_incidents": c,
        "total_cost_sek": f"{total_cost:.2f}",
        "avg_impact_score": round(avg_impact, 2),
    })

cost_csv = os.path.join(OUT_DIR, "cost_analysis.csv")
write_csv(cost_csv, ["week_number","total_incidents","total_cost_sek","avg_impact_score"], weekly_rows)
print(f"[OK] Skrev {cost_csv}")

# --- Impact per kategori (impact_by_category.csv)
cat_stats = defaultdict(lambda: {"sum": 0.0, "count": 0})
for r in rows:
    cat = (r.get("category") or "").strip().lower()
    cat_stats[cat]["sum"] += parse_float(r.get("impact_score"), 0.0)
    cat_stats[cat]["count"] += 1

cat_rows = []
for cat, vals in cat_stats.items():
    c = vals["count"]
    avg = (vals["sum"]/c) if c else 0.0
    cat_rows.append({"category": cat, "avg_impact_score": f"{avg:.2f}", "incident_count": c})
cat_rows.sort(key=lambda x: -parse_float(x["avg_impact_score"], 0.0))

impact_cat_csv = os.path.join(OUT_DIR, "impact_by_category.csv")
write_csv(impact_cat_csv, ["category","avg_impact_score","incident_count"], cat_rows)
print(f"[OK] Skrev {impact_cat_csv}")

# --- Text-rapport 
total_incidents = len(rows)
total_cost = sum(parse_float(r.get("cost_sek"), 0.0) for r in rows)
weeks = [to_int_safe(r.get("week_number"), 0) for r in rows if r.get("week_number")]
min_w, max_w = (min(weeks), max(weeks)) if weeks else (None, None)

lines = []
lines.append("=" * 80)
lines.append(" " * 22 + "INCIDENT ANALYSIS - SENASTE PERIODEN")
lines.append("=" * 80)
lines.append(f"Rapport genererad: {datetime.date.today().strftime('%Y-%m-%d')}")
if min_w and max_w:
    lines.append(f"Analysperiod (veckor): {min_w} till {max_w}")
lines.append(f"Total incidents: {total_incidents} st")
lines.append(f"Total kostnad: {sek_fmt(total_cost)} SEK")
lines.append("")

# Executive summary (kort överblick)
top_site = max(site_stats.items(), key=lambda kv: kv[1]["total_incidents"])[0] if site_stats else "-"
recurrent = [r for r in problem_rows if int(r["incident_count"]) >= 3]
lines.append("EXECUTIVE SUMMARY")
lines.append("-" * 25)
lines.append(f"• Mest belastade site: {top_site}")
lines.append(f"• Enheter med ≥3 incidenter: {len(recurrent)} st")
lines.append("")

# Incidents per severity
lines.append("INCIDENTS PER SEVERITY")
lines.append("-" * 80)
for sev in ["critical", "high", "medium", "low"]:
    cnt = severity_cnt.get(sev, 0)
    tot_min = severity_sum.get(sev, 0)
    avg_min = (tot_min / cnt) if cnt else 0
    tot_cost = severity_cost.get(sev, 0.0)
    avg_cost = (tot_cost / cnt) if cnt else 0.0
    pct = (cnt / total_incidents * 100) if total_incidents else 0
    lines.append(f"{sev.capitalize():<10}: {cnt:>3} st ({pct:>2.0f}%) - Genomsnitt: {avg_min:>4.0f} min, {sek_fmt(avg_cost)} SEK/incident")
lines.append("")

# Största påverkan (>100 användare)
big_impact = [r for r in rows if users_int_safe(r.get("affected_users"), 0) > 100]
lines.append("STÖRSTA PÅVERKAN (>100 användare)")
lines.append("-" * 80)
if big_impact:
    lines.append(f"{'ticket':<12} {'site':<14} {'device':<18} {'users':>5} {'sev':<8} {'kostnad':>14}  {'category'}")
    lines.append("-" * 80)
    for r in big_impact:
        tid  = (r.get('ticket_id') or '')
        site = (r.get('site') or '')
        dev  = (r.get('device_hostname') or '')
        sev  = (r.get('severity') or '').strip().lower()
        users = users_int_safe(r.get('affected_users'), 0)
        cost  = f"{sek_fmt(parse_float(r.get('cost_sek'), 0.0))} SEK"
        cat   = (r.get('category') or '')
        lines.append(f"{tid:<12} {site:<14} {dev:<18} {users:>5} {sev:<8} {cost:>14}  {cat}")
else:
    lines.append("- (inga händelser över 100 användare)")
lines.append("")

# Topp 5 dyraste
top5 = sorted(rows, key=lambda r: parse_float(r.get("cost_sek"), 0.0), reverse=True)[:5]
lines.append("TOPP 5 DYRASTE INCIDENTS")
lines.append("-" * 80)
if top5:
    lines.append(f"{'ticket':<12} {'device':<18} {'site':<14} {'sev':<8} {'kostnad':>14}  {'category'}")
    lines.append("-" * 80)
    for r in top5:
        lines.append(f"{(r.get('ticket_id') or ''):<12} {(r.get('device_hostname') or ''):<18} {(r.get('site') or ''):<14} {(r.get('severity') or '').strip().lower():<8} {sek_fmt(parse_float(r.get('cost_sek'),0.0)):>14}  {(r.get('category') or '')}")
else:
    lines.append("- (inga data)")
lines.append("")

# Rekommenderad åtgärdsplan
lines.append("REKOMMENDERAD ÅTGÄRDSPLAN")
lines.append("-" * 25)
if recurrent:
    for d in sorted(recurrent, key=lambda x: (-int(x["incident_count"]), -parse_float(x["avg_severity_score"]))):
        name, site = d["device_hostname"], d["site"]
        avg = parse_float(d["avg_severity_score"], 0.0)
        if avg >= 3.5:
            action = "Byt ut eller gör hårdvarugenomgång."
        elif avg >= 2.5:
            action = "Planera förebyggande underhåll/uppdatering."
        else:
            action = "Övervaka och följ upp nästa period."
        lines.append(f"- {name} ({site}): {d['incident_count']} incidenter → {action}")
else:
    lines.append("Inga enheter över tröskeln (≥3 incidenter).")
lines.append("")

# skriv rapport
report_path = os.path.join(OUT_DIR, "incident_analysis.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"[OK] Skrev {report_path}")
