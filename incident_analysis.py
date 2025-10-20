
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
