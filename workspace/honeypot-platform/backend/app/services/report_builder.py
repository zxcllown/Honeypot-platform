import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def build_report(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM classified_sessions
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id,))
    classification = cur.fetchone()

    cur.execute("""
        SELECT *
        FROM risk_decisions
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id,))
    risk = cur.fetchone()

    cur.execute("""
        SELECT *
        FROM sandbox_runs
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id,))
    sandbox = cur.fetchone()

    conn.close()

    report = {
        "session_id": session_id
    }

    if classification:
        report["classification"] = {
            "type": classification["classification"],
            "confidence": classification["confidence"],
            "tactics": json.loads(classification["tactics"]),
            "model": classification["model_name"]
        }

    if risk:
        report["risk"] = {
            "score": risk["risk_score"],
            "sandbox_required": bool(risk["sandbox_required"]),
            "reason": json.loads(risk["reason"]),
            "observe_commands": json.loads(risk["observe_commands"]),
            "commands_to_sandbox": json.loads(risk["commands_to_sandbox"])
        }

    if sandbox:
        report["sandbox"] = {
            "exit_code": sandbox["exit_code"],
            "network_connections": json.loads(sandbox["network_connections"]),
            "stdout": sandbox["stdout"],
            "stderr": sandbox["stderr"]
        }

    return report