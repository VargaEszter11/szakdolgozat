import csv
import json
import os

# Input CSV file from OurAirports
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(script_dir, "airports.csv")
json_file = os.path.join(script_dir, "airports_europe.json")

airports = []

with open(csv_file, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Only European airports with scheduled flights
        if row["continent"] == "EU" and row["scheduled_service"] == "yes" and row["type"] in ("medium_airport", "large_airport"):
            airport = {
                "name": row["name"],
                "city": row["municipality"],
                "country": row["iso_country"],
                "iata": row["iata_code"],
                "icao": row["ident"],
                "lat": float(row["latitude_deg"]),
                "lon": float(row["longitude_deg"]),
                "type": row["type"].replace("_airport", ""),
                "scheduled": True
            }
            airports.append(airport)

# Save JSON
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(airports, f, indent=2, ensure_ascii=False)

print(f"Saved {len(airports)} European airports to {json_file}")
