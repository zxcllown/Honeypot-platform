import json
import sqlite3
from pathlib import Path
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.security import CurrentUser, get_current_user, require_admin


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def safe_json_loads(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def fetch_all(query: str, params: tuple = ()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()


@router.get("/overview")
def get_overview(current_user: CurrentUser = Depends(get_current_user)):
    classified = fetch_all(
        "SELECT * FROM classified_sessions WHERE user_id = ?",
        (current_user.id,),
    )
    telemetry = fetch_all(
        "SELECT * FROM telemetry_analysis WHERE user_id = ?",
        (current_user.id,),
    )
    recommendations = fetch_all(
        "SELECT * FROM adaptive_recommendations WHERE user_id = ?",
        (current_user.id,),
    )

    classification_counter = Counter()
    tactic_counter = Counter()
    behavior_counter = Counter()
    attack_chain_counter = Counter()
    recommendation_status_counter = Counter()
    recommendation_priority_counter = Counter()

    severity_values = []

    for row in classified:
        classification_counter[row["classification"]] += 1
        tactics = safe_json_loads(row["tactics"], [])
        tactic_counter.update(tactics)

    for row in telemetry:
        behaviors = safe_json_loads(row["behaviors"], [])
        attack_chain = safe_json_loads(row["attack_chain"], [])

        behavior_counter.update(behaviors)

        if attack_chain:
            attack_chain_counter.update([" -> ".join(attack_chain)])

        if row["severity_score"] is not None:
            severity_values.append(float(row["severity_score"]))

    for row in recommendations:
        recommendation_status_counter[row["status"]] += 1
        recommendation_priority_counter[row["priority"]] += 1

    avg_severity = (
        round(sum(severity_values) / len(severity_values), 3)
        if severity_values else 0.0
    )

    max_severity = max(severity_values) if severity_values else 0.0

    return {
        "sessions": {
            "classified_total": len(classified),
            "telemetry_analyzed_total": len(telemetry),
            "by_classification": dict(classification_counter),
        },
        "severity": {
            "avg": avg_severity,
            "max": max_severity,
        },
        "top_tactics": tactic_counter.most_common(10),
        "top_behaviors": behavior_counter.most_common(10),
        "top_attack_chains": attack_chain_counter.most_common(10),
        "adaptive": {
            "recommendations_total": len(recommendations),
            "by_status": dict(recommendation_status_counter),
            "by_priority": dict(recommendation_priority_counter),
        },
    }


@router.get("/recent-sessions")
def get_recent_sessions(
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
):
    limit = max(1, min(limit, 100))
    rows = fetch_all("""
        SELECT
            c.session_id,
            c.classification,
            c.confidence,
            c.tactics,
            c.classified_at,
            t.severity_score,
            t.behaviors,
            t.attack_chain,
            s.sandbox_level,
            s.exit_code
        FROM classified_sessions c
        LEFT JOIN telemetry_analysis t
            ON c.session_id = t.session_id
        LEFT JOIN sandbox_runs s
            ON c.session_id = s.session_id
        WHERE c.user_id = ?
        ORDER BY c.id DESC
        LIMIT ?
    """, (current_user.id, limit))

    result = []

    for row in rows:
        result.append({
            "session_id": row["session_id"],
            "classification": row["classification"],
            "confidence": row["confidence"],
            "tactics": safe_json_loads(row["tactics"], []),
            "severity_score": row["severity_score"],
            "behaviors": safe_json_loads(row["behaviors"], []),
            "attack_chain": safe_json_loads(row["attack_chain"], []),
            "sandbox_level": row["sandbox_level"],
            "sandbox_exit_code": row["exit_code"],
            "classified_at": row["classified_at"],
        })

    return {
        "items": result,
        "count": len(result),
    }


@router.get("/global-threat-view")
def get_global_threat_view(_admin: CurrentUser = Depends(require_admin)):
    path = DB_PATH.parent / "global_threat_view.json"

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="global_threat_view.json not found",
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "available": True,
        "data": data,
    }
