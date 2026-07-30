import traceback, sys

sys.stderr.write("before import\n")
sys.stderr.flush()

try:
    import app.services.crime_service as cs
    sys.stderr.write("import OK\n")
    sys.stderr.flush()
    lat, lon = cs._AREA_COORDINATES["Gandhipuram"]
    sys.stderr.write("coords OK: lat=%s lon=%s\n" % (lat, lon))
    d = cs._haversine_m(lat, lon, lat, lon)
    sys.stderr.write("haversine OK: %s\n" % d)
    df = cs.load_dataset()
    sys.stderr.write("dataset OK: %d rows\n" % len(df))
    route = [[lon, lat]]
    results = cs.get_crimes_near_route(route, radius_m=200)
    sys.stderr.write("query OK: %d results\n" % len(results))
    results2 = cs.get_crimes_near_route(route, radius_m=3000)
    sys.stderr.write("wide query OK: %d results\n" % len(results2))
    for r in results2[:5]:
        sys.stderr.write("  %s %s %sm\n" % (r.area, r.risk_level, r.distance_m))
except Exception as e:
    sys.stderr.write("EXCEPTION: " + str(e) + "\n")
    traceback.print_exc(file=sys.stderr)

sys.stderr.flush()
