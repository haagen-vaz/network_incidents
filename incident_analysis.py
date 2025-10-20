import csv

with open ('network_incidents.csv', encoding='utf-8', newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

severity_counts = {}                # ⑤ tom ordbok för att samla antal

for row in rows:                    # ⑥ gå igenom varje incident
    sev = row["severity"].strip().lower()   # ⑦ hämta texten och gör den småbokstav
    if sev not in severity_counts:          # ⑧ finns den inte än?
        severity_counts[sev] = 0            # ⑨ skapa ny nyckel med värdet 0
    severity_counts[sev] += 1               # ⑩ öka räknaren med 1

print("Antal incidenter per severity:")     # ⑪ rubrik
for level, antal in severity_counts.items():# ⑫ loopa igenom ordboken
    print(f" - {level}: {antal}")           # ⑬ skriv ut fint



