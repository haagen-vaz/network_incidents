import csv

with open ('network_incidents.csv', encoding='utf-8', newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

def to_int_safe(value, default=0):
    """Konvertera text till int, klarar svenska tal med komma."""
    s = (value or "").strip()
    if s == "":
        return default
    s = s.replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return default
    
    
severity_sum = {}   # lagrar totalt antal minuter per severity
severity_cnt = {}   # lagrar hur många incidenter av varje typ

for row in rows:                                     # loopar varje incident
    sev = (row["severity"] or "").strip().lower()    # hämtar t.ex. "critical"
    mins = to_int_safe(row["resolution_minutes"], 0) # konverterar till int

    if sev not in severity_sum:                      # initiera om första gången
        severity_sum[sev] = 0
        severity_cnt[sev] = 0

    severity_sum[sev] += mins                        # addera minuter
    severity_cnt[sev] += 1                           # räkna incidenten

# Räkna ut snitt och skriv ut både antal och genomsnitt 
print("Antal och genomsnittlig resolution per severity:")
for sev in severity_cnt:                             
    count = severity_cnt[sev]
    total = severity_sum[sev]
    avg = total / count if count else 0              
    print(f" - {sev:<8} : {count:>2} st, snitt {avg:.1f} min")



