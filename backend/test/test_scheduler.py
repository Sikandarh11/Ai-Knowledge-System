from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.scheduling_agent import SchedulingAgent
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Real test target date: tomorrow (UTC).
# ---------------------------------------------------------------------------
_tomorrow_date = (datetime.now(tz=timezone.utc) + timedelta(days=1)).date().isoformat()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_case(
    label: str,
    query: str,
    agent: SchedulingAgent | None = None,
) -> dict:
    print("\n" + "=" * 60)
    print(f"TEST: {label}")
    print(f"QUERY: {query!r}")
    print(f"TARGET DATE (tomorrow): {_tomorrow_date}")
    print("-" * 60)
    _agent = agent or SchedulingAgent()
    result = _agent.run(query)
    print(f"success          : {result['success']}")
    print(f"intent           : {result['intent']}")
    print(f"conflict_detected: {result['conflict_detected']}")
    print(f"created_event    : {result['created_event']}")
    print(f"alternatives     : {len(result['alternatives'])} slot(s)")
    print(f"free_slots       : {len(result['free_slots'])} slot(s)")
    print(f"error            : {result['error']}")
    print()
    print("MESSAGE:")
    print(result["message"])
    print("=" * 60)
    return result


def _to_ampm(hour: int, minute: int) -> str:
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12
    if minute == 0:
        return f"{hour12}{suffix}"
    return f"{hour12}:{minute:02d}{suffix}"


def main() -> None:
    # Reuse one real agent instance for the whole run.
    agent = SchedulingAgent()

    # ------------------------------------------------------------------
    # CASE 1 — Happy path: CREATE at a genuinely free time (1pm)
    # 1pm is outside both busy blocks → event must be booked
    # ------------------------------------------------------------------
    created = run_case(
        label="CREATE — free slot at 1pm, should book successfully",
        query=f"schedule a meeting on {_tomorrow_date} at 1pm for 30 minutes",
        agent=agent,
    )

    # ------------------------------------------------------------------
    # CASE 2 — Conflict on CREATE: 10am is blocked by Team standup
    # Conflict detected → agent must decline and suggest alternatives
    # ------------------------------------------------------------------
    run_case(
        label="CREATE — conflicting slot at 1pm, expect alternatives",
        query=f"book a standup on {_tomorrow_date} at 1pm for 1 hour",
        agent=agent,
    )

    # ------------------------------------------------------------------
    # CASE 3 — CHECK: 9am is free (before any busy block)
    # Expect green-light confirmation
    # ------------------------------------------------------------------
    run_case(
        label="CHECK — free time at 9am, expect green light",
        query=f"am I free on {_tomorrow_date} at 9am?",
        agent=agent,
    )

    # ------------------------------------------------------------------
    # CASE 4 — CHECK: 2pm overlaps the 14:00-15:00 busy block
    # Expect conflict flag + alternative suggestions
    # ------------------------------------------------------------------
    busy_query = f"do I have anything on {_tomorrow_date} at 1pm?"
    created_event = created.get("created_event")
    if created.get("success") and created_event and created_event.get("start"):
        start_dt = datetime.fromisoformat(created_event["start"].replace("Z", "+00:00"))
        busy_query = (
            f"do I have anything on {start_dt.date().isoformat()} "
            f"at {_to_ampm(start_dt.hour, start_dt.minute)}?"
        )

    run_case(
        label="CHECK — busy at created time, expect conflict + alternatives",
        query=busy_query,
        agent=agent,
    )

    # ------------------------------------------------------------------
    # CASE 5 — SUGGEST: list all free slots for tomorrow
    # Expect 18 slots minus the 2 busy hours = 14 free 30-min slots
    # ------------------------------------------------------------------
    run_case(
        label="SUGGEST — list all free slots tomorrow",
        query=f"suggest available times on {_tomorrow_date}",
        agent=agent,
    )

    # ------------------------------------------------------------------
    # CASE 6 — Bad input: no date at all
    # Expect graceful error, no crash
    # ------------------------------------------------------------------
    run_case(
        label="BAD INPUT — missing date, expect graceful error",
        query="book a meeting at 10am for 1 hour",
        agent=agent,
    )


if __name__ == "__main__":
    main()