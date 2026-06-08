import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from shared import event_bus, Streams, SandboxResultEvent


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sandbox_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            exit_code INTEGER,
            sandbox_level TEXT,
            commands_executed TEXT,
            command_results TEXT,
            stdout TEXT,
            stderr TEXT,
            files_created TEXT,
            files_modified TEXT,
            files_deleted TEXT,
            network_connections TEXT,
            syscalls TEXT,
            executed_at TEXT,
            created_at TEXT
        )
        """)
        conn.commit()


def save_sandbox_result(event: SandboxResultEvent):
    result = event.result

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO sandbox_runs (
            event_id,
            correlation_id,
            session_id,
            exit_code,
            sandbox_level,
            commands_executed,
            command_results,
            stdout,
            stderr,
            files_created,
            files_modified,
            files_deleted,
            network_connections,
            syscalls,
            executed_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.correlation_id,
            event.session_id,
            result.exit_code,
            result.sandbox_level,
            json.dumps(result.commands_executed, ensure_ascii=False),
            json.dumps([r.model_dump(mode="json") for r in result.command_results], ensure_ascii=False),
            result.stdout,
            result.stderr,
            json.dumps(result.files_created, ensure_ascii=False),
            json.dumps(result.files_modified, ensure_ascii=False),
            json.dumps(result.files_deleted, ensure_ascii=False),
            json.dumps(result.network_connections, ensure_ascii=False),
            json.dumps(result.syscalls, ensure_ascii=False),
            event.executed_at.isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()


def run():
    init_db()

    while True:
        events = event_bus.consume(
            Streams.TELEMETRY,
            "telemetry_writer",
            "telemetry_1"
        )

        for msg_id, data in events:
            try:
                event = SandboxResultEvent.model_validate(data)
                save_sandbox_result(event)
                event_bus.ack(Streams.TELEMETRY, "telemetry_writer", msg_id)
            except Exception as e:
                print(f"[telemetry_writer] error: {e}")


if __name__ == "__main__":
    run()