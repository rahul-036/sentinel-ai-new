import sys, traceback

sys.stderr.write("Testing schema imports...\n")
try:
    from app.schemas.risk import (
        CrimeLocationDetail, LiveCrimeAnalysis, RiskAnalysisResponse,
        RiskLevel, CrimeAnalysis, WeatherAnalysis, RouteAnalysis,
        LiveInfrastructureAnalysis, EmergencyServicesAnalysis,
    )
    sys.stderr.write("  schemas OK\n")
except Exception as e:
    sys.stderr.write("  FAIL: %s\n" % e)
    traceback.print_exc(file=sys.stderr)

sys.stderr.write("Testing crime_agent import...\n")
try:
    from app.agents.crime_agent import analyze_crime
    sys.stderr.write("  crime_agent OK\n")
except Exception as e:
    sys.stderr.write("  FAIL: %s\n" % e)
    traceback.print_exc(file=sys.stderr)

sys.stderr.write("Testing risk_assessment_agent import...\n")
try:
    from app.agents.risk_assessment_agent import RiskAssessmentAgent
    sys.stderr.write("  risk_assessment_agent OK\n")
except Exception as e:
    sys.stderr.write("  FAIL: %s\n" % e)
    traceback.print_exc(file=sys.stderr)

sys.stderr.write("Testing CrimeLocationDetail schema...\n")
try:
    from app.schemas.risk import CrimeLocationDetail
    loc = CrimeLocationDetail(
        area="Gandhipuram",
        crime_index=72,
        risk_level="High",
        latitude=11.0168,
        longitude=76.9558,
        dominant_crime_type="Theft",
        distance_m=0.0,
    )
    sys.stderr.write("  CrimeLocationDetail OK: %s\n" % loc.model_dump())
except Exception as e:
    sys.stderr.write("  FAIL: %s\n" % e)
    traceback.print_exc(file=sys.stderr)

sys.stderr.flush()
