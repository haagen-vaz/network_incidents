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


    # parsea svensk kostnad "12 345,67" -> 12345.67 (float)
def parse_cost_sek(value, default=0.0):
    s = (value or "").strip()                 #  None -> "", trim
    if s == "":                               #  tomt => default
        return default
    s = s.replace("\u202f", " ")              #  ersätt hårt mellanslag (smalt) med vanligt
    s = s.replace(" ", "")                    #  ta bort tusentalsmellanslag: "12 345" -> "12345"
    s = s.replace(",", ".")                   # svenskt komma -> punkt: "12345,67" -> "12345.67"
    try:
        return float(s)                       #  konvertera till flyttal
    except ValueError:
        return default                        # trasigt värde => 0.0

# utskrift i svenskt format: 12345.67 -> "12 345,67"
def sek_fmt(n):
    s = f"{n:,.2f}"                                 #  "12,345.67" (US)
    return s.replace(",", " ").replace(".", ",")    # -> "12 345,67"

# 3) Behållare för kostnader per severity
severity_cost = {}                            # t.ex. {"critical": 123456.75, ...}
severity_count = {}                           # för att kunna räkna snittkostnad

# 4) Loopa raderna och summera kostnaden per severity
for row in rows:
    sev = (row["severity"] or "").strip().lower()   #  normalisera nyckel
    cost = parse_cost_sek(row["cost_sek"], 0.0)     #  säkert float-värde

    if sev not in severity_cost:                    #  initiera första gången vi ser 'sev'
        severity_cost[sev] = 0.0
        severity_count[sev] = 0

    severity_cost[sev] += cost                      #  addera kostnad
    severity_count[sev] += 1                        #  räkna incidenter

# 5) Skriv ut total kostnad
print("Totalkostnad per severity:")
for sev in severity_cost:
    total = severity_cost[sev]
    avg   = total / severity_count[sev] if severity_count[sev] else 0.0
    print(f" - {sev:<8}: {sek_fmt(total)} SEK  (snitt {sek_fmt(avg)} SEK/incident)")




