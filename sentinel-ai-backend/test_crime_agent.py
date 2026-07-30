import sys
from app.agents.crime_agent import analyze_crime

# Route through central Coimbatore: Gandhipuram -> Town Hall -> RS Puram
route = [
    [76.9558, 11.0168],  # Gandhipuram
    [76.9650, 11.0100],  # Town Hall
    [76.9550, 11.0050],  # RS Puram
]

result = analyze_crime(route)
sys.stderr.write("crime_risk=%s\n" % result.crime_risk)
sys.stderr.write("nearby_crimes=%d\n" % result.nearby_crimes)
sys.stderr.write("score_contribution=%d\n" % result.score_contribution)
sys.stderr.write("is_live=%s\n" % result.is_live)
sys.stderr.write("locations:\n")
for loc in result.crime_locations:
    sys.stderr.write("  %s | %s | index=%d | dist=%sm\n" % (
        loc.area, loc.risk_level, loc.crime_index, loc.distance_m
    ))

# Test fallback with empty coords
fallback = analyze_crime([])
sys.stderr.write("\nFallback (empty route): risk=%s score=%d is_live=%s\n" % (
    fallback.crime_risk, fallback.score_contribution, fallback.is_live
))
sys.stderr.flush()
