import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from shared import event_bus, Streams, ClassifiedEvent


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS classified_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            classification TEXT,
            confidence REAL,
            tactics TEXT,
            model_name TEXT,
            model_version TEXT,
            classified_at TEXT,
            created_at TEXT
        )
        """)
        conn.commit()


def save_classification(event: ClassifiedEvent):
    clf = event.classification

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO classified_sessions (
            event_id,
            correlation_id,
            session_id,
            classification,
            confidence,
            tactics,
            model_name,
            model_version,
            classified_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.correlation_id,
            event.session_id,
            clf.classification,
            clf.confidence,
            json.dumps(clf.tactics, ensure_ascii=False),
            clf.model_name,
            clf.model_version,
            event.classified_at.isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()


def run():
    init_db()

    while True:
        events = event_bus.consume(
            Streams.CLASSIFIED,
            "classification_writer",
            "classification_1"
        )

        for msg_id, data in events:
            try:
                event = ClassifiedEvent.model_validate(data)
                save_classification(event)
                event_bus.ack(Streams.CLASSIFIED, "classification_writer", msg_id)
            except Exception as e:
                print(f"[classification_writer] error: {e}")


if __name__ == "__main__":
    run()