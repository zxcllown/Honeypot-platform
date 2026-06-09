import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.security import CurrentUser, get_current_user


router = APIRouter(prefix="/agent", tags=["agent"])

DB_PATH = Path(
    os.getenv(
        "HONEYPOT_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "data" / "telemetry.db"),
    )
)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class AgentSessionPayload(BaseModel):
    node_id: str = Field(min_length=3, max_length=80)
    source: str = Field(min_length=2, max_length=80)
    session: dict


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def columns(conn, table):
    return {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def insert_row(conn, table, data):
    available = columns(conn, table)
    filtered = {
        key: value
        for key, value in data.items()
        if key in available and key != "id"
    }
    if not filtered:
        return None

    keys = list(filtered)
    placeholders = ", ".join(["?"] * len(keys))
    conn.execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})",
        [filtered[key] for key in keys],
    )


def classify_session(session):
    commands = [item.get("cmd", "") for item in session.get("commands", [])]
    requests = [
        f"{item.get('method', '')} {item.get('path', '')} {item.get('payload', '')}"
        for item in session.get("requests", [])
    ]
    text = "\n".join(commands + requests).lower()
    tactics = []
    behaviors = []

    if any(token in text for token in ["wget", "curl", "/dev/tcp", "nc ", "ncat", "socket"]):
        tactics.append("command_and_control")
        behaviors.append("outbound tooling")
    if any(token in text for token in ["cat /etc/passwd", "/etc/shadow", "whoami", "id", "uname"]):
        tactics.append("discovery")
        behaviors.append("host enumeration")
    if any(token in text for token in ["wp-admin", "wp-login", "admin-ajax"]):
        tactics.append("credential_access")
        behaviors.append("web login probing")
    if any(token in text for token in ["sudo", "su ", "shadow"]):
        tactics.append("privilege_escalation")
        behaviors.append("privilege probing")

    classification = "malicious" if tactics else "mixed"
    severity = min(1.0, 0.25 + (0.18 * len(set(tactics))))

    return {
        "classification": classification,
        "confidence": 0.82 if tactics else 0.55,
        "tactics": sorted(set(tactics)) or ["unknown"],
        "behaviors": sorted(set(behaviors)) or ["interaction captured"],
        "severity_score": round(severity, 3),
    }


def ensure_owned_honeypot(conn, node_id, user_id):
    row = conn.execute(
        """
        SELECT *
        FROM honeypot_nodes
        WHERE node_id = ?
            AND user_id = ?
        """,
        (node_id, user_id),
    ).fetchone()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Honeypot not found for this user")

    return row


@router.get("/honeypots")
def list_agent_honeypots(current_user: CurrentUser = Depends(get_current_user)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                node_id,
                name,
                honeypot_type,
                host,
                port,
                status,
                version,
                updated_at
            FROM honeypot_nodes
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (current_user.id,),
        ).fetchall()

    return {
        "items": [dict(row) for row in rows],
        "count": len(rows),
    }


@router.post("/heartbeat")
def heartbeat(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "user_id": current_user.id,
        "time": iso_now(),
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def ingest_session(
    payload: AgentSessionPayload,
    current_user: CurrentUser = Depends(get_current_user),
):
    session = dict(payload.session)
    session_id = str(session.get("session_id") or uuid4())[:64]
    session["session_id"] = session_id
    session["node_id"] = payload.node_id
    session["source"] = payload.source

    classified_at = session.get("date_end") or iso_now()
    analysis = classify_session(session)
    commands = [item.get("cmd", "") for item in session.get("commands", [])]
    requests = session.get("requests", [])
    event_id = str(uuid4())
    correlation_id = str(uuid4())

    with connect() as conn:
        ensure_owned_honeypot(conn, payload.node_id, current_user.id)

        existing = conn.execute(
            """
            SELECT id
            FROM classified_sessions
            WHERE session_id = ?
                AND user_id = ?
            LIMIT 1
            """,
            (session_id, current_user.id),
        ).fetchone()

        if existing:
            return {
                "session_id": session_id,
                "stored": False,
                "duplicate": True,
            }

        insert_row(conn, "classified_sessions", {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "session_id": session_id,
            "classification": analysis["classification"],
            "confidence": analysis["confidence"],
            "tactics": dumps(analysis["tactics"]),
            "model_name": "honeyzxc-agent",
            "model_version": "v1",
            "classified_at": classified_at,
            "created_at": iso_now(),
            "user_id": current_user.id,
        })

        insert_row(conn, "risk_decisions", {
            "event_id": str(uuid4()),
            "correlation_id": correlation_id,
            "session_id": session_id,
            "risk_score": analysis["severity_score"],
            "sandbox_required": int(bool(commands)),
            "reason": dumps(analysis["behaviors"]),
            "observe_commands": dumps(commands[:10]),
            "commands_to_sandbox": dumps(commands[:5]),
            "decided_at": classified_at,
            "created_at": iso_now(),
            "user_id": current_user.id,
        })

        insert_row(conn, "telemetry_analysis", {
            "session_id": session_id,
            "sandbox_run_id": 0,
            "behaviors": dumps(analysis["behaviors"]),
            "indicators": dumps({
                "ip": session.get("ip"),
                "username": session.get("username"),
                "node_id": payload.node_id,
                "requests_total": len(requests),
                "commands_total": len(commands),
            }),
            "severity_score": analysis["severity_score"],
            "summary": f"{payload.source} session captured by {payload.node_id}",
            "syscall_summary": dumps({}),
            "file_activity": dumps({}),
            "process_activity": dumps({"commands": commands}),
            "network_activity": dumps({"requests": requests}),
            "attack_chain": dumps(analysis["tactics"]),
            "analyzed_at": iso_now(),
            "user_id": current_user.id,
        })

        conn.execute(
            """
            UPDATE honeypot_nodes
            SET sessions_total = COALESCE(sessions_total, 0) + 1,
                updated_at = ?
            WHERE node_id = ?
                AND user_id = ?
            """,
            (iso_now(), payload.node_id, current_user.id),
        )
        conn.commit()

    return {
        "session_id": session_id,
        "stored": True,
        "classification": analysis["classification"],
        "severity_score": analysis["severity_score"],
    }
