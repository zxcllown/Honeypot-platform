import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def safe_json_loads(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS adaptive_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            telemetry_analysis_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_name TEXT NOT NULL,
            reason TEXT,
            evidence TEXT,
            priority TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            applied_at TEXT
        )
        """)
        conn.commit()


def recommendation_exists(conn, telemetry_analysis_id: int, action_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("""
        SELECT 1
        FROM adaptive_recommendations
        WHERE telemetry_analysis_id = ?
        AND action_name = ?
        LIMIT 1
    """, (telemetry_analysis_id, action_name))

    return cur.fetchone() is not None


def make_recommendations(row: sqlite3.Row) -> list[dict]:
    behaviors = safe_json_loads(row["behaviors"], [])
    indicators = safe_json_loads(row["indicators"], [])
    attack_chain = safe_json_loads(row["attack_chain"], [])
    severity_score = row["severity_score"] or 0.0

    recommendations = []

    def add(action_type, action_name, reason, evidence=None, priority="medium"):
        recommendations.append({
            "session_id": row["session_id"],
            "telemetry_analysis_id": row["id"],
            "action_type": action_type,
            "action_name": action_name,
            "reason": reason,
            "evidence": evidence or {},
            "priority": priority,
        })

    if "reverse_shell_attempt" in behaviors:
        add(
            action_type="decoy",
            action_name="deploy_c2_decoy_listener",
            reason="Reverse shell behavior was detected.",
            evidence={
                "behaviors": behaviors,
                "indicators": indicators,
            },
            priority="high",
        )

    if "payload_download_attempt" in behaviors:
        add(
            action_type="decoy",
            action_name="deploy_fake_writable_payload_directory",
            reason="Payload download attempt was detected.",
            evidence={
                "behaviors": behaviors,
                "indicators": indicators,
            },
            priority="high",
        )

    if "sensitive_file_access" in behaviors:
        add(
            action_type="decoy",
            action_name="deploy_fake_credentials",
            reason="Access to sensitive-looking files was detected.",
            evidence={
                "behaviors": behaviors,
                "indicators": indicators,
            },
            priority="medium",
        )

    if "privilege_escalation_attempt" in behaviors:
        add(
            action_type="deception_policy",
            action_name="enable_fake_sudo_responses",
            reason="Privilege escalation behavior was detected.",
            evidence={
                "behaviors": behaviors,
                "attack_chain": attack_chain,
            },
            priority="high",
        )

    if "persistence_attempt" in behaviors:
        add(
            action_type="decoy",
            action_name="deploy_fake_cron_and_systemd_units",
            reason="Persistence-related behavior was detected.",
            evidence={
                "behaviors": behaviors,
                "attack_chain": attack_chain,
            },
            priority="high",
        )

    if "syscall_network_connect" in behaviors:
        add(
            action_type="monitoring",
            action_name="increase_network_telemetry_level",
            reason="Network connect syscall was observed.",
            evidence={
                "indicators": indicators,
            },
            priority="medium",
        )

    if severity_score >= 0.8:
        add(
            action_type="alert",
            action_name="notify_analyst_high_severity",
            reason="High severity sandbox behavior was detected.",
            evidence={
                "severity_score": severity_score,
                "behaviors": behaviors,
            },
            priority="critical",
        )

    return recommendations


def save_recommendations(recommendations: list[dict]):
    with sqlite3.connect(DB_PATH) as conn:
        for rec in recommendations:
            if recommendation_exists(
                conn,
                rec["telemetry_analysis_id"],
                rec["action_name"]
            ):
                continue

            conn.execute("""
                INSERT INTO adaptive_recommendations (
                    session_id,
                    telemetry_analysis_id,
                    action_type,
                    action_name,
                    reason,
                    evidence,
                    priority,
                    status,
                    created_at,
                    applied_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["session_id"],
                rec["telemetry_analysis_id"],
                rec["action_type"],
                rec["action_name"],
                rec["reason"],
                json.dumps(rec["evidence"], ensure_ascii=False),
                rec["priority"],
                "pending",
                datetime.now(timezone.utc).isoformat(),
                None,
            ))

        conn.commit()


def run_once():
    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM telemetry_analysis
            ORDER BY id ASC
        """)

        rows = cur.fetchall()

    total = 0

    for row in rows:
        recommendations = make_recommendations(row)
        save_recommendations(recommendations)
        total += len(recommendations)

        if recommendations:
            print(
                f"[adaptive_agent] session={row['session_id']} "
                f"recommendations={len(recommendations)}"
            )

    print(f"[adaptive_agent] done total_recommendations={total}")


if __name__ == "__main__":
    run_once()
    import sqlite3

    conn = sqlite3.connect("../../data/telemetry.db")
    cur = conn.cursor()

    cur.execute("""
                SELECT session_id,
                       action_type,
                       action_name,
                       priority,
                       status,
                       reason
                FROM adaptive_recommendations
                """)

    for row in cur.fetchall():
        print(row)

    conn.close()