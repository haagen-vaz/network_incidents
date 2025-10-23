import csv
import os
import datetime
from collections import defaultdict
import json

# Läs in CSV-filen
with open("network_incidents.csv", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

import json

def load_last_week_warnings(path="network.devices.json"):
    try:
        with open(path, encoding="utf-8") as jf:
            data = json.load(jf)
    except FileNotFoundError:
        return set()

    warn = set()
    # Walk locations -> devices and collect warning/offline devices
    for loc in data.get("locations", []):
        for d in loc.get("devices", []):
            name = (d.get("hostname") or "").strip().upper()
            status = (d.get("status") or "").strip().lower()
            if name and status in {"warning", "offline", "down", "degraded"}:
                warn.add(name)

    # Optional: if your JSON also had a simple list like {"warnings": ["SW-..."]}
    for name in data.get("warnings", []):
        if isinstance(name, str) and name.strip():
            warn.add(name.strip().upper())

    return warn

last_week_warnings = load_last_week_warnings()
print(f"[Info] Found {len(last_week_warnings)} last-week warning devices")



# text till heltal
def to_int_safe(value, default=0):
    s = (value or "").strip()
    if s == "":
        return default
    s = s.replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return default

#  text till flyttal
def to_float_safe(value, default=0.0):
    s = (value or "").strip()
    if s == "":
        return default
    s = s.replace("\u202f", " ").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default

# svensk kostnad till float
def parse_cost_sek(value, default=0.0):
    s = (value or "").strip()
    if s == "":
        return default
    s = s.replace("\u202f", " ").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default

# formatera SEK till svensk stil
def sek_fmt(n):
    s = f"{n:,.2f}"
    return s.replace(",", " ").replace(".", ",")

# heltal för användare
def users_int_safe(v, default=0):
    s = (v or "").strip()
    if s == "":
        return default
    try:
        return int(float(s.replace(",", ".")))
    except ValueError:
        return default


# Beräkna resolution-tider per severity
severity_sum = {}
severity_cnt = {}

for row in rows:
    sev = (row["severity"] or "").strip().lower()
    mins = to_int_safe(row["resolution_minutes"], 0)
    if sev not in severity_sum:
        severity_sum[sev] = 0
        severity_cnt[sev] = 0
    severity_sum[sev] += mins
    severity_cnt[sev] += 1

print("Antal och genomsnittlig resolution per severity:")
for sev in ["critical", "high", "medium", "low"]:
    if sev in severity_cnt:
        count = severity_cnt[sev]
        total = severity_sum[sev]
        avg = total / count if count else 0
        print(f" - {sev:<8} : {count:>2} st, snitt {avg:.1f} min")


# Beräkna kostnad per severity
severity_cost = {}
severity_count = {}

for row in rows:
    sev = (row["severity"] or "").strip().lower()
    cost = parse_cost_sek(row["cost_sek"], 0.0)
    if sev not in severity_cost:
        severity_cost[sev] = 0.0
        severity_count[sev] = 0
    severity_cost[sev] += cost
    severity_count[sev] += 1

print("\nTotalkostnad per severity:")
for sev in ["critical", "high", "medium", "low"]:
    if sev in severity_cost:
        total = severity_cost[sev]
        avg   = total / severity_count[sev] if severity_count[sev] else 0.0
        print(f" - {sev:<8}: {sek_fmt(total)} SEK  (snitt {sek_fmt(avg)} SEK/incident)")


# Statistik per site 
OUT_DIR = "out"
os.makedirs(OUT_DIR, exist_ok=True)

site_stats = {}

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
    key = f"{sev}_incidents"
    if key in site_stats[site]:
        site_stats[site][key] += 1
    site_stats[site]["sum_resolution"] += mins
    site_stats[site]["total_cost_sek"] += cost

for _, data in site_stats.items():
    count = data["total_incidents"]
    avg = (data["sum_resolution"] / count) if count else 0.0
    data["avg_resolution_minutes"] = round(avg, 2)
    data["total_cost_sek"] = round(data["total_cost_sek"], 2)

# Skriv incidents_by_site.csv 
out_path = os.path.join(OUT_DIR, "incidents_by_site.csv")
with open(out_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "site",
        "total_incidents",
        "critical_incidents",
        "high_incidents",
        "medium_incidents",
        "low_incidents",
        "avg_resolution_minutes",
        "total_cost_sek",
    ])
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
            "total_cost_sek": f'{d["total_cost_sek"]:.2f}',
        })
print(f"[OK] Skrev {out_path}")


# Problem devices
severity_score = {"low": 1, "medium": 2, "high": 3, "critical": 4}
dev_stats = {}

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
        "in_last_weeks_warnings": "yes" if d["device_hostname"].strip().upper() in last_week_warnings else "no",


    })

problem_rows.sort(key=lambda r: (-r["incident_count"], -r["total_cost_sek"]))

# Skriv problem_devices.csv
out_path_pd = os.path.join(OUT_DIR, "problem_devices.csv")
with open(out_path_pd, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "device_hostname","site","device_type",
        "incident_count","avg_severity_score",
        "total_cost_sek","avg_affected_users","in_last_weeks_warnings"
    ])
    writer.writeheader()
    for r in problem_rows:
        writer.writerow({
            "device_hostname": r["device_hostname"],
            "site": r["site"],
            "device_type": r["device_type"],
            "incident_count": r["incident_count"],
            "avg_severity_score": f'{r["avg_severity_score"]:.2f}',
            "total_cost_sek": f'{r["total_cost_sek"]:.2f}',
            "avg_affected_users": f'{r["avg_affected_users"]:.2f}',
            "in_last_weeks_warnings": r["in_last_weeks_warnings"],
        })
print(f"[OK] Skrev {out_path_pd}")


# Kostnad per vecka
week_stats = {}
for row in rows:
    week = to_int_safe(row.get("week_number"), 0)
    cost = parse_cost_sek(row.get("cost_sek"), 0.0)
    impact = to_float_safe(row.get("impact_score"), 0.0)
    if week not in week_stats:
        week_stats[week] = {"total_cost": 0.0, "count": 0, "impact_sum": 0.0}
    week_stats[week]["total_cost"] += cost
    week_stats[week]["count"] += 1
    week_stats[week]["impact_sum"] += impact

weekly_rows = []
for week in sorted(k for k in week_stats.keys() if k):
    total_cost = round(week_stats[week]["total_cost"], 2)
    count = week_stats[week]["count"]
    avg_impact = round((week_stats[week]["impact_sum"] / count) if count else 0.0, 2)
    weekly_rows.append({
        "week_number": week,
        "total_incidents": count,
        "total_cost_sek": f"{total_cost:.2f}",
        "avg_impact_score": avg_impact,
    })

# --- Skriv cost_analysis.csv ---
out_path_cost = os.path.join(OUT_DIR, "cost_analysis.csv")
with open(out_path_cost, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "week_number", "total_incidents", "total_cost_sek", "avg_impact_score"
    ])
    writer.writeheader()
    for r in weekly_rows:
        writer.writerow(r)
print(f"[OK] Skrev {out_path_cost}")


# Impact score per kategori
category_stats = {}
for row in rows:
    category = (row.get("category") or "").strip().lower()
    impact = to_float_safe(row.get("impact_score"), 0.0)
    if category not in category_stats:
        category_stats[category] = {"sum": 0.0, "count": 0}
    category_stats[category]["sum"] += impact
    category_stats[category]["count"] += 1

category_avg = []
for cat, vals in category_stats.items():
    count = vals["count"]
    avg = vals["sum"] / count if count else 0.0
    category_avg.append((cat, round(avg, 2), count))
category_avg.sort(key=lambda x: -x[1])

# Skriv impact_by_category.csv
out_path_cat = os.path.join(OUT_DIR, "impact_by_category.csv")
with open(out_path_cat, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "avg_impact_score", "incident_count"])
    for cat, avg, count in category_avg:
        writer.writerow([cat, f"{avg:.2f}", count])
print(f"[OK] Skrev {out_path_cat}")


# Skapa textrapport
total_incidents = len(rows)
total_cost = sum(parse_cost_sek(r.get("cost_sek"), 0.0) for r in rows)
all_weeks = [to_int_safe(r.get("week_number"), 0) for r in rows if r.get("week_number") is not None]
min_week = min(all_weeks) if all_weeks else None
max_week = max(all_weeks) if all_weeks else None

def avg_res_min(sev):
    cnt = severity_cnt.get(sev, 0)
    tot = severity_sum.get(sev, 0)
    return (tot / cnt) if cnt else 0.0

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

big_impact = [r for r in rows if users_int_safe(r.get("affected_users"), 0) > 100]
top5_costly = sorted(rows, key=lambda r: parse_cost_sek(r.get("cost_sek"), 0.0), reverse=True)[:5]
sites = sorted({ (r.get("site") or "").strip() for r in rows })
site_crit = { s: 0 for s in sites }
for r in rows:
    s = (r.get("site") or "").strip()
    sev = (r.get("severity") or "").strip().lower()
    if sev == "critical":
        site_crit[s] += 1
sites_no_critical = [s for s in sites if site_crit.get(s, 0) == 0]

lines = []
lines.append("=" * 80)
lines.append(" " * 22 + "INCIDENT ANALYSIS - SENASTE PERIODEN")
lines.append("=" * 80)
today = datetime.date.today()
lines.append(f"Rapport genererad: {today.strftime('%Y-%m-%d')}")
if min_week is not None and max_week is not None:
    lines.append(f"Analysperiod (veckor): {min_week} till {max_week}")
lines.append(f"Total incidents: {total_incidents} st")
lines.append(f"Total kostnad: {sek_fmt(total_cost)} SEK")
lines.append("")

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

lines.append("INCIDENTS PER SEVERITY")
lines.append("-" * 25)
for sev in ["critical", "high", "medium", "low"]:
    cnt = severity_cnt.get(sev, 0)
    pct = (cnt / total_incidents * 100) if total_incidents else 0
    avg_min = avg_res_min(sev)
    avg_cst = avg_cost_sek(sev)
    lines.append(
        f"{sev.capitalize():<10}: {cnt:>3} st ({pct:>2.0f}%) - "
        f"Genomsnitt: {avg_min:>4.0f} min resolution, {sek_fmt(avg_cst)} SEK/incident"
    )
lines.append("")

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
        cost_sw = f"{sek_fmt(parse_cost_sek(r.get('cost_sek'), 0.0))} SEK"
        cat  = (r.get('category') or '')
        lines.append(f"{tid:<12} {site:<14} {dev:<18} {users:>5} {sev:<8} {cost_sw:>14}  {cat}")
else:
    lines.append("- (inga händelser över 100 användare)")
lines.append("")

lines.append("TOPP 5 DYRASTE INCIDENTS")
lines.append("-" * 80)
if top5_costly:
    lines.append(f"{'ticket':<12} {'device':<18} {'site':<14} {'sev':<8} {'kostnad':>14}  {'category'}")
    lines.append("-" * 80)
    for r in top5_costly:
        tid  = (r.get('ticket_id') or '')
        dev  = (r.get('device_hostname') or '')
        site = (r.get('site') or '')
        sev  = (r.get('severity') or '').strip().lower()
        cost_sw = f"{sek_fmt(parse_cost_sek(r.get('cost_sek'), 0.0))} SEK"
        cat  = (r.get('category') or '')
        lines.append(f"{tid:<12} {dev:<18} {site:<14} {sev:<8} {cost_sw:>14}  {cat}")
else:
    lines.append("- (inga data)")
lines.append("")

lines.append("REKOMMENDERAD ÅTGÄRDSPLAN")
lines.append
