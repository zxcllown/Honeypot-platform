import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from shared import event_bus, Streams, RiskDecisionEvent


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            risk_score REAL,
            sandbox_required INTEGER,
            reason TEXT,
            observe_commands TEXT,
            commands_to_sandbox TEXT,
            decided_at TEXT,
            created_at TEXT
        )
        """)
        conn.commit()


def save_risk_decision(event: RiskDecisionEvent):
    decision = event.decision

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO risk_decisions (
            event_id,
            correlation_id,
            session_id,
            risk_score,
            sandbox_required,
            reason,
            observe_commands,
            commands_to_sandbox,
            decided_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.correlation_id,
            event.session_id,
            decision.risk_score,
            int(decision.sandbox_required),
            json.dumps(decision.reason, ensure_ascii=False),
            json.dumps(decision.observe_commands, ensure_ascii=False),
            json.dumps(decision.commands_to_sandbox, ensure_ascii=False),
            event.decided_at.isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()


def run():
    init_db()

    while True:
        events = event_bus.consume(
            Streams.SANDBOX,
            "risk_writer",
            "risk_writer_1"
        )

        for msg_id, data in events:
            try:
                event = RiskDecisionEvent.model_validate(data)
                save_risk_decision(event)
                event_bus.ack(Streams.SANDBOX, "risk_writer", msg_id)
            except Exception as e:
                print(f"[risk_writer] error: {e}")


if __name__ == "__main__":
    run()