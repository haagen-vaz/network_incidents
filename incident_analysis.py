import csv

with open ('network_incidents.csv', encoding='utf-8', newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:                                                         
    print(row["ticket_id"], row["site"], row["severity"])
