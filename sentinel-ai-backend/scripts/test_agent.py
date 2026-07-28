import asyncio
from app.agents.risk_assessment_agent import RiskAssessmentAgent

result = asyncio.run(RiskAssessmentAgent("Hyderabad", "Gachibowli").run())
print(result.model_dump_json(indent=2))
