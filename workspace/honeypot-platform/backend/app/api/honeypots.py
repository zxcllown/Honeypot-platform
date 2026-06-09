import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.security import CurrentUser, get_current_user


router = APIRouter(prefix="/honeypots", tags=["honeypots"])

DB_PATH = Path(
    os.getenv(
        "HONEYPOT_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "data" / "telemetry.db"),
    )
)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
HoneypotStatus = Literal["running", "stopped", "maintenance"]


class HoneypotCreate(BaseModel):
    node_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    honeypot_type: str = Field(min_length=2, max_length=40)
    host: str = Field(min_length=2, max_length=120)
    port: int = Field(ge=1, le=65535)
    version: str | None = Field(default=None, max_length=80)
    status: HoneypotStatus = "stopped"


class HoneypotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    honeypot_type: str | None = Field(default=None, min_length=2, max_length=40)
    host: str | None = Field(default=None, min_length=2, max_length=120)
    port: int | None = Field(default=None, ge=1, le=65535)
    version: str | None = Field(default=None, max_length=80)
    status: HoneypotStatus | None = None


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row)


def ensure_honeypot(node_id: str, user_id: int):
    with connect() as conn:
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Honeypot not found")

    return row


@router.get("")
def list_honeypots(current_user: CurrentUser = Depends(get_current_user)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM honeypot_nodes
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (current_user.id,),
        ).fetchall()

    items = [row_to_dict(row) for row in rows]

    return {
        "items": items,
        "count": len(items),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_honeypot(
    payload: HoneypotCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    created_at = iso_now()

    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO honeypot_nodes (
                    node_id,
                    name,
                    honeypot_type,
                    host,
                    port,
                    status,
                    version,
                    sessions_total,
                    created_at,
                    updated_at,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    payload.node_id,
                    payload.name,
                    payload.honeypot_type,
                    payload.host,
                    payload.port,
                    payload.status,
                    payload.version,
                    created_at,
                    created_at,
                    current_user.id,
                ),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Honeypot node_id already exists",
        )

    return row_to_dict(ensure_honeypot(payload.node_id, current_user.id))


@router.get("/{node_id}")
def get_honeypot(
    node_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    return row_to_dict(ensure_honeypot(node_id, current_user.id))


@router.patch("/{node_id}")
def update_honeypot(
    node_id: str,
    payload: HoneypotUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_honeypot(node_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        return row_to_dict(ensure_honeypot(node_id, current_user.id))

    updates["updated_at"] = iso_now()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [node_id, current_user.id]

    with connect() as conn:
        conn.execute(
            f"""
            UPDATE honeypot_nodes
            SET {assignments}
            WHERE node_id = ?
                AND user_id = ?
            """,
            values,
        )
        conn.commit()

    return row_to_dict(ensure_honeypot(node_id, current_user.id))


@router.delete("/{node_id}")
def delete_honeypot(
    node_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_honeypot(node_id, current_user.id)

    with connect() as conn:
        conn.execute(
            """
            DELETE FROM honeypot_nodes
            WHERE node_id = ?
                AND user_id = ?
            """,
            (node_id, current_user.id),
        )
        conn.commit()

    return {
        "node_id": node_id,
        "deleted": True,
    }


def set_status(node_id: str, user_id: int, status_value: HoneypotStatus):
    ensure_honeypot(node_id, user_id)
    updated_at = iso_now()

    with connect() as conn:
        conn.execute(
            """
            UPDATE honeypot_nodes
            SET status = ?,
                updated_at = ?
            WHERE node_id = ?
                AND user_id = ?
            """,
            (status_value, updated_at, node_id, user_id),
        )
        conn.commit()

    return row_to_dict(ensure_honeypot(node_id, user_id))


@router.post("/{node_id}/enable")
def enable_honeypot(
    node_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    node = set_status(node_id, current_user.id, "running")
    return {
        "node_id": node_id,
        "action": "enable",
        "status": node["status"],
        "node": node,
    }


@router.post("/{node_id}/disable")
def disable_honeypot(
    node_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    node = set_status(node_id, current_user.id, "stopped")
    return {
        "node_id": node_id,
        "action": "disable",
        "status": node["status"],
        "node": node,
    }
