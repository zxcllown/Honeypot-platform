import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"
EXPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "node_summary.json"

NODE_ID = "local-node-1"
NODE_REGION = "local-lab"
MODEL_VERSION = "v1.0"


def safe_json_loads(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def fetch_telemetry_rows():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM telemetry_analysis
            ORDER BY id ASC
        """)

        return cur.fetchall()


def fetch_recommendation_rows():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM adaptive_recommendations
            ORDER BY id ASC
        """)

        return cur.fetchall()


def build_node_summary():
    telemetry_rows = fetch_telemetry_rows()
    recommendation_rows = fetch_recommendation_rows()

    behavior_counter = Counter()
    indicator_counter = Counter()
    attack_chain_counter = Counter()
    severity_values = []

    for row in telemetry_rows:
        behaviors = safe_json_loads(row["behaviors"], [])
        indicators = safe_json_loads(row["indicators"], [])
        attack_chain = safe_json_loads(row["attack_chain"], [])

        severity = row["severity_score"]
        if severity is not None:
            severity_values.append(float(severity))

        behavior_counter.update(behaviors)
        indicator_counter.update(indicators)

        if attack_chain:
            attack_chain_counter.update([" -> ".join(attack_chain)])

    recommendation_status_counter = Counter()
    recommendation_action_counter = Counter()
    recommendation_priority_counter = Counter()

    for row in recommendation_rows:
        recommendation_status_counter.update([row["status"]])
        recommendation_action_counter.update([row["action_name"]])
        recommendation_priority_counter.update([row["priority"]])

    avg_severity = (
        round(sum(severity_values) / len(severity_values), 3)
        if severity_values else 0.0
    )

    max_severity = max(severity_values) if severity_values else 0.0

    summary = {
        "node_id": NODE_ID,
        "node_region": NODE_REGION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "privacy_mode": "aggregated_only_no_raw_logs",
        "telemetry": {
            "sessions_analyzed": len(telemetry_rows),
            "avg_severity": avg_severity,
            "max_severity": max_severity,
            "top_behaviors": behavior_counter.most_common(10),
            "top_indicators": indicator_counter.most_common(10),
            "top_attack_chains": attack_chain_counter.most_common(10),
        },
        "adaptive": {
            "recommendations_total": len(recommendation_rows),
            "by_status": dict(recommendation_status_counter),
            "by_priority": dict(recommendation_priority_counter),
            "top_actions": recommendation_action_counter.most_common(10),
        },
    }

    return summary


def export_summary():
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary = build_node_summary()

    with open(EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[federated_exporter] exported {EXPORT_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    export_summary()