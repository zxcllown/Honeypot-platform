import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/honeypots",
    tags=["honeypots"]
)

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def fetch_all(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.execute(query, params)

        return cur.fetchall()


def execute(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute(query, params)

        conn.commit()

@router.get("")
def list_honeypots():

    rows = fetch_all("""
        SELECT *
        FROM honeypot_nodes
        ORDER BY id ASC
    """)

    result = []

    for row in rows:
        result.append(dict(row))

    return {
        "items": result,
        "count": len(result)
    }

@router.get("/{node_id}")
def get_honeypot(node_id: str):

    rows = fetch_all("""
        SELECT *
        FROM honeypot_nodes
        WHERE node_id = ?
    """, (node_id,))

    if not rows:
        raise HTTPException(404, "Honeypot not found")

    return dict(rows[0])

@router.post("/{node_id}/disable")
def disable_honeypot(node_id: str):

    execute("""
        UPDATE honeypot_nodes
        SET
            status = 'stopped',
            updated_at = ?
        WHERE node_id = ?
    """, (
        datetime.now(timezone.utc).isoformat(),
        node_id
    ))

    return {
        "node_id": node_id,
        "action": "disable",
        "status": "stopped"
    }

@router.post("/{node_id}/enable")
def enable_honeypot(node_id: str):

    execute("""
        UPDATE honeypot_nodes
        SET
            status = 'running',
            updated_at = ?
        WHERE node_id = ?
    """, (
        datetime.now(timezone.utc).isoformat(),
        node_id
    ))

    return {
        "node_id": node_id,
        "action": "enable",
        "status": "running"
    }

@router.post("/{node_id}/restart")
def restart_honeypot(node_id: str):

    execute("""
        UPDATE honeypot_nodes
        SET
            updated_at = ?
        WHERE node_id = ?
    """, (
        datetime.now(timezone.utc).isoformat(),
        node_id
    ))

    return {
        "node_id": node_id,
        "action": "restart",
        "status": "running"
    }