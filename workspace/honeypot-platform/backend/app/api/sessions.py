import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.api.security import CurrentUser, get_current_user


router = APIRouter(prefix="/sessions", tags=["sessions"])

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


def fetch_one(query: str, params: tuple = ()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


@router.get("")
def list_sessions(
    limit: int = 50,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
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
        LIMIT ? OFFSET ?
    """, (current_user.id, limit, offset))

    items = []

    for row in rows:
        items.append({
            "session_id": row["session_id"],
            "classification": row["classification"],
            "confidence": row["confidence"],
            "tactics": safe_json_loads(row["tactics"], []),
            "severity_score": row["severity_score"],
            "behaviors": safe_json_loads(row["behaviors"], []),
            "attack_chain": safe_json_loads(row["attack_chain"], []),
            "sandbox": {
                "level": row["sandbox_level"],
                "exit_code": row["exit_code"],
            },
            "classified_at": row["classified_at"],
        })

    return {
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{session_id}")
def get_session_detail(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    classification = fetch_one("""
        SELECT *
        FROM classified_sessions
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id, current_user.id))

    if not classification:
        raise HTTPException(status_code=404, detail="Session not found")

    risk = fetch_one("""
        SELECT *
        FROM risk_decisions
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id, current_user.id))

    sandbox = fetch_one("""
        SELECT *
        FROM sandbox_runs
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id, current_user.id))

    telemetry = fetch_one("""
        SELECT *
        FROM telemetry_analysis
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id, current_user.id))

    recommendations = fetch_all("""
        SELECT *
        FROM adaptive_recommendations
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id ASC
    """, (session_id, current_user.id))

    actions = fetch_all("""
        SELECT *
        FROM adaptive_actions_log
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id ASC
    """, (session_id, current_user.id))

    return {
        "session_id": session_id,

        "classification": {
            "event_id": classification["event_id"],
            "correlation_id": classification["correlation_id"],
            "classification": classification["classification"],
            "confidence": classification["confidence"],
            "tactics": safe_json_loads(classification["tactics"], []),
            "model_name": classification["model_name"],
            "model_version": classification["model_version"],
            "classified_at": classification["classified_at"],
        },

        "risk": None if not risk else {
            "event_id": risk["event_id"],
            "correlation_id": risk["correlation_id"],
            "risk_score": risk["risk_score"],
            "sandbox_required": bool(risk["sandbox_required"]),
            "reason": safe_json_loads(risk["reason"], []),
            "observe_commands": safe_json_loads(risk["observe_commands"], []),
            "commands_to_sandbox": safe_json_loads(risk["commands_to_sandbox"], []),
            "decided_at": risk["decided_at"],
        },

        "sandbox": None if not sandbox else {
            "event_id": sandbox["event_id"],
            "correlation_id": sandbox["correlation_id"],
            "exit_code": sandbox["exit_code"],
            "sandbox_level": sandbox["sandbox_level"],
            "commands_executed": safe_json_loads(sandbox["commands_executed"], []),
            "command_results": safe_json_loads(sandbox["command_results"], []),
            "stdout": sandbox["stdout"],
            "stderr": sandbox["stderr"],
            "files_created": safe_json_loads(sandbox["files_created"], []),
            "files_modified": safe_json_loads(sandbox["files_modified"], []),
            "files_deleted": safe_json_loads(sandbox["files_deleted"], []),
            "network_connections": safe_json_loads(sandbox["network_connections"], []),
            "syscalls": safe_json_loads(sandbox["syscalls"], []),
            "executed_at": sandbox["executed_at"],
        },

        "telemetry": None if not telemetry else {
            "behaviors": safe_json_loads(telemetry["behaviors"], []),
            "indicators": safe_json_loads(telemetry["indicators"], []),
            "severity_score": telemetry["severity_score"],
            "summary": telemetry["summary"],
            "syscall_summary": safe_json_loads(telemetry["syscall_summary"], {}),
            "file_activity": safe_json_loads(telemetry["file_activity"], {}),
            "process_activity": safe_json_loads(telemetry["process_activity"], {}),
            "network_activity": safe_json_loads(telemetry["network_activity"], {}),
            "attack_chain": safe_json_loads(telemetry["attack_chain"], []),
            "analyzed_at": telemetry["analyzed_at"],
        },

        "adaptive": {
            "recommendations": [
                {
                    "id": row["id"],
                    "action_type": row["action_type"],
                    "action_name": row["action_name"],
                    "reason": row["reason"],
                    "evidence": safe_json_loads(row["evidence"], {}),
                    "priority": row["priority"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "applied_at": row["applied_at"],
                }
                for row in recommendations
            ],
            "actions_log": [
                {
                    "id": row["id"],
                    "recommendation_id": row["recommendation_id"],
                    "action_name": row["action_name"],
                    "action_type": row["action_type"],
                    "status": row["status"],
                    "details": safe_json_loads(row["details"], {}),
                    "created_at": row["created_at"],
                }
                for row in actions
            ],
        },
    }


@router.get("/{session_id}/timeline")
def get_session_timeline(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    detail = get_session_detail(session_id, current_user)

    timeline = []

    c = detail["classification"]
    timeline.append({
        "stage": "classification",
        "time": c["classified_at"],
        "title": "Session classified",
        "description": f"{c['classification']} with confidence {c['confidence']}",
        "data": c,
    })

    if detail["risk"]:
        r = detail["risk"]
        timeline.append({
            "stage": "risk",
            "time": r["decided_at"],
            "title": "Risk decision",
            "description": "Sandbox required" if r["sandbox_required"] else "Sandbox not required",
            "data": r,
        })

    if detail["sandbox"]:
        s = detail["sandbox"]
        timeline.append({
            "stage": "sandbox",
            "time": s["executed_at"],
            "title": "Sandbox executed",
            "description": f"Sandbox level={s['sandbox_level']}, exit_code={s['exit_code']}",
            "data": {
                "commands_executed": s["commands_executed"],
                "network_connections": s["network_connections"],
                "files_created": s["files_created"],
                "files_modified": s["files_modified"],
                "files_deleted": s["files_deleted"],
            },
        })

    if detail["telemetry"]:
        t = detail["telemetry"]
        timeline.append({
            "stage": "telemetry",
            "time": t["analyzed_at"],
            "title": "Telemetry analyzed",
            "description": t["summary"],
            "data": {
                "behaviors": t["behaviors"],
                "attack_chain": t["attack_chain"],
                "severity_score": t["severity_score"],
            },
        })

    for rec in detail["adaptive"]["recommendations"]:
        timeline.append({
            "stage": "adaptive_recommendation",
            "time": rec["created_at"],
            "title": rec["action_name"],
            "description": rec["reason"],
            "data": rec,
        })

    for action in detail["adaptive"]["actions_log"]:
        timeline.append({
            "stage": "adaptive_action",
            "time": action["created_at"],
            "title": action["action_name"],
            "description": f"Action {action['status']}",
            "data": action,
        })

    timeline = sorted(
        timeline,
        key=lambda x: x["time"] or ""
    )

    return {
        "session_id": session_id,
        "timeline": timeline,
        "count": len(timeline),
    }

@router.get("/{session_id}/replay")
def get_session_replay(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    sandbox = fetch_one("""
        SELECT *
        FROM sandbox_runs
        WHERE session_id = ?
            AND user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session_id, current_user.id))

    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox run not found")

    command_results = safe_json_loads(sandbox["command_results"], [])
    syscalls = safe_json_loads(sandbox["syscalls"], [])

    replay_steps = []

    for index, item in enumerate(command_results):
        command = item.get("command", "")
        exit_code = item.get("exit_code")
        stdout = item.get("stdout", "")
        stderr = item.get("stderr", "")
        network_indicators = item.get("network_indicators", [])

        related_syscalls = []

        for syscall in syscalls:
            if command.split()[0] in syscall:
                related_syscalls.append(syscall)

        replay_steps.append({
            "index": index,
            "command": command,
            "exit_code": exit_code,
            "status": "success" if exit_code == 0 else "failed",
            "stdout": stdout,
            "stderr": stderr,
            "network_indicators": network_indicators,
            "related_syscalls": related_syscalls[:20],
        })

    return {
        "session_id": session_id,
        "sandbox": {
            "event_id": sandbox["event_id"],
            "correlation_id": sandbox["correlation_id"],
            "sandbox_level": sandbox["sandbox_level"],
            "exit_code": sandbox["exit_code"],
            "executed_at": sandbox["executed_at"],
        },
        "summary": {
            "commands_total": len(replay_steps),
            "failed_commands": len([
                step for step in replay_steps
                if step["exit_code"] not in (0, None)
            ]),
            "network_indicators": safe_json_loads(sandbox["network_connections"], []),
            "files_created": safe_json_loads(sandbox["files_created"], []),
            "files_modified": safe_json_loads(sandbox["files_modified"], []),
            "files_deleted": safe_json_loads(sandbox["files_deleted"], []),
            "syscalls_total": len(syscalls),
        },
        "steps": replay_steps,
    }
