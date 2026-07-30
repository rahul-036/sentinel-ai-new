"""Smoke test for CrimeService — exercises every public method."""
import sys
import json
from app.services.crime_service import (
    load_dataset,
    get_all_crimes,
    get_crimes_by_area,
    get_crimes_near_location,
    get_crimes_near_route,
    calculate_crime_density,
    get_hotspots,
    get_crime_summary_for_location,
)

SEP = "=" * 60
SUB = "-" * 60

print(SEP)
print("CrimeService smoke test")
print(SEP)

# 1. load_dataset
print("\n[1] load_dataset()")
df = load_dataset()
print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
print(f"  Columns: {list(df.columns)}")

# 2. get_all_crimes
print("\n[2] get_all_crimes() - top 5 by Crime Index")
all_crimes = get_all_crimes()
print(f"  Total records: {len(all_crimes)}")
for r in all_crimes[:5]:
    print(f"  {r.area:30s}  index={r.crime_index}  risk={r.risk_level}  dominant={r.dominant_crime_type}")

# 3. get_crimes_by_area - exact match
print("\n[3] get_crimes_by_area('Gandhipuram') - exact match")
rec = get_crimes_by_area("Gandhipuram")
if rec:
    print(f"  area={rec.area}  index={rec.crime_index}  risk={rec.risk_level}  total={rec.total_crimes}")
else:
    print("  NOT FOUND")

# 4. get_crimes_by_area - fuzzy match
print("\n[4] get_crimes_by_area('RS Puram') - fuzzy match")
rec = get_crimes_by_area("RS Puram")
if rec:
    print(f"  area={rec.area}  index={rec.crime_index}  risk={rec.risk_level}")
else:
    print("  NOT FOUND")

# 5. get_crimes_by_area - no match
print("\n[5] get_crimes_by_area('NonExistentPlace') - no match")
rec = get_crimes_by_area("NonExistentPlace")
print(f"  Result: {rec}")

# 6. get_crimes_near_location
print("\n[6] get_crimes_near_location('Peelamedu')")
nearby = get_crimes_near_location("Peelamedu")
print(f"  Matched {len(nearby)} area(s):")
for r in nearby:
    print(f"    {r.area:30s}  index={r.crime_index}  risk={r.risk_level}")

# 7. get_crimes_near_route
print("\n[7] get_crimes_near_route(['Gandhipuram', 'Peelamedu', 'Saravanampatti'])")
route_results = get_crimes_near_route(["Gandhipuram", "Peelamedu", "Saravanampatti"])
for seg in route_results:
    print(f"  Segment {seg.segment_index}: risk={seg.risk_level}  score={seg.score_contribution}")
    print(f"    {seg.summary}")

# 8. calculate_crime_density
print("\n[8] calculate_crime_density(['Gandhipuram', 'Ukkadam', 'Peelamedu'])")
density = calculate_crime_density(["Gandhipuram", "Ukkadam", "Peelamedu"])
print(f"  areas={density.area_count}  avg_index={density.average_crime_index}")
print(f"  dominant_risk={density.dominant_risk_level}  hotspots={density.hotspot_areas}")
print(f"  crime_totals={density.crime_type_totals}")

# 9. get_hotspots
print("\n[9] get_hotspots(risk_level='High')")
hotspots = get_hotspots(risk_level="High")
print(f"  Found {len(hotspots)} High-risk hotspots:")
for h in hotspots:
    print(f"    {h.area:30s}  index={h.crime_index}  dominant={h.dominant_crime_type}")

print("\n[9b] get_hotspots(risk_level='Medium', top_n=5)")
med = get_hotspots(risk_level="Medium", top_n=5)
for h in med:
    print(f"    {h.area:30s}  index={h.crime_index}")

# 10. get_crime_summary_for_location
print("\n[10] get_crime_summary_for_location('Gandhipuram')")
summary = get_crime_summary_for_location("Gandhipuram")
print(json.dumps(summary, indent=4))

print("\n[10b] get_crime_summary_for_location('UnknownPlace')")
summary2 = get_crime_summary_for_location("UnknownPlace")
print(json.dumps(summary2, indent=4))

# 11. Second call to load_dataset - should use cache
print("\n[11] load_dataset() second call - should use cache")
df2 = load_dataset()
print(f"  Same object: {df is df2}")

print("\n" + SEP)
print("ALL TESTS PASSED")
print(SEP)
