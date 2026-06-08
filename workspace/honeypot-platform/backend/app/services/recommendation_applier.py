import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS adaptive_actions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            action_name TEXT NOT NULL,
            action_type TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT
        )
        """)
        conn.commit()


def safe_json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def simulate_action(row: sqlite3.Row) -> dict:
    action_name = row["action_name"]
    evidence = safe_json_loads(row["evidence"], {})

    if action_name == "deploy_c2_decoy_listener":
        return {
            "result": "simulated",
            "message": "C2 decoy listener would be deployed.",
            "ports": [9001, 4444],
            "evidence": evidence,
        }

    if action_name == "deploy_fake_credentials":
        return {
            "result": "simulated",
            "message": "Fake credential decoys would be added.",
            "decoys": ["fake_id_rsa", "fake_db_passwords.txt"],
            "evidence": evidence,
        }

    if action_name == "enable_fake_sudo_responses":
        return {
            "result": "simulated",
            "message": "Fake sudo responses would be enabled.",
            "policy": "sudo deception mode",
            "evidence": evidence,
        }

    if action_name == "increase_network_telemetry_level":
        return {
            "result": "simulated",
            "message": "Network telemetry level would be increased.",
            "level": "high",
            "evidence": evidence,
        }

    if action_name == "notify_analyst_high_severity":
        return {
            "result": "simulated",
            "message": "High severity analyst alert would be sent.",
            "channel": "console",
            "evidence": evidence,
        }

    return {
        "result": "simulated",
        "message": f"No real applier implemented for {action_name}.",
        "evidence": evidence,
    }


def mark_applied(conn, recommendation_id: int):
    conn.execute("""
        UPDATE adaptive_recommendations
        SET status = 'applied',
            applied_at = ?
        WHERE id = ?
    """, (
        datetime.now(timezone.utc).isoformat(),
        recommendation_id,
    ))


def log_action(conn, row: sqlite3.Row, details: dict):
    conn.execute("""
        INSERT INTO adaptive_actions_log (
            recommendation_id,
            session_id,
            action_name,
            action_type,
            status,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        row["id"],
        row["session_id"],
        row["action_name"],
        row["action_type"],
        "applied",
        json.dumps(details, ensure_ascii=False),
        datetime.now(timezone.utc).isoformat(),
    ))


def apply_pending_recommendations():
    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM adaptive_recommendations
            WHERE status = 'pending'
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                id ASC
        """)

        rows = cur.fetchall()

        for row in rows:
            details = simulate_action(row)
            mark_applied(conn, row["id"])
            log_action(conn, row, details)

            print(
                f"[recommendation_applier] applied "
                f"id={row['id']} "
                f"session={row['session_id']} "
                f"action={row['action_name']}"
            )

        conn.commit()

    print(f"[recommendation_applier] done applied={len(rows)}")


if __name__ == "__main__":
    apply_pending_recommendations()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("""
                    SELECT id, session_id, action_name, priority, status, applied_at
                    FROM adaptive_recommendations;
                    """)

        cur.execute("""
                    SELECT recommendation_id, session_id, action_name, status, details
                    FROM adaptive_actions_log;
                    """)