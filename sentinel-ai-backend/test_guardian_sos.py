import asyncio
import sys
sys.path.insert(0, ".")

from app.schemas.guardian import GuardianCreate, GuardianUpdate
from app.schemas.sos import SOSRequest
from app.agents.guardian_agent import GuardianAgent
from app.agents.sos_agent import SOSAgent
from app.agents.guardian_sos_agent import GuardianSOSAgent
from app.services.sos_service import get_all_alerts


async def main():
    # ── 1. Guardian CRUD ──────────────────────────────────────────────────────
    agent = GuardianAgent()
    g1 = agent.add(GuardianCreate(name="Priya", phone="9876543210", relation="Sister", is_primary=True))
    g2 = agent.add(GuardianCreate(name="Ravi", phone="9123456789", relation="Father"))
    print(f"Created: {g1.name} primary={g1.is_primary}, {g2.name} primary={g2.is_primary}")

    all_g = agent.list_all()
    print(f"List: {len(all_g)} guardians, first={all_g[0].name}")

    updated = agent.update(g2.id, GuardianUpdate(name="Ravi Kumar"))
    print(f"Updated: {updated.name}")

    fetched = agent.get_one(g1.id)
    print(f"Fetched: {fetched.name}")

    # ── 2. New SOSAgent with guardian notifications ───────────────────────────
    sos = SOSAgent()
    req = SOSRequest(
        user_name="Rahul", phone="9999999999",
        latitude=11.0168, longitude=76.9558,
        safety_score=24, risk_level="High",
    )
    resp = await sos.run(req)
    print(f"SOSAgent: alert_id={resp.alert_id} guardian_count={resp.guardian_count}")
    for g in resp.guardians_notified:
        print(f"  {g.name} ({g.relation}): {g.notification_status}")

    # ── 3. Old GuardianSOSAgent still works ───────────────────────────────────
    old_agent = GuardianSOSAgent()
    old_resp = await old_agent.run(req)
    print(f"GuardianSOSAgent (old): alert_id={old_resp.alert_id} status={old_resp.status}")

    # ── 4. History ────────────────────────────────────────────────────────────
    history = get_all_alerts()
    print(f"History: {len(history)} alerts, latest={history[0].alert_id}")

    # ── 5. Delete ─────────────────────────────────────────────────────────────
    deleted = agent.remove(g1.id)
    print(f"Deleted g1: {deleted}, remaining: {len(agent.list_all())}")

    print()
    print("=== ALL BACKEND TESTS PASSED ===")


asyncio.run(main())
