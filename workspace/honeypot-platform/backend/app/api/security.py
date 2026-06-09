import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"
PBKDF2_ITERATIONS = 260_000
TOKEN_TTL_HOURS = 12
ACCESS_TOKEN_COOKIE = "honeypot_access_token"


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    username: str
    role: str
    token_hash: str


def utcnow():
    return datetime.now(timezone.utc)


def iso_now():
    return utcnow().isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def token_hash(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_security_schema():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                last_used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        owned_tables = [
            "honeypot_nodes",
            "classified_sessions",
            "risk_decisions",
            "sandbox_runs",
            "telemetry_analysis",
            "adaptive_recommendations",
            "adaptive_actions_log",
        ]

        existing_tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        for table in owned_tables:
            if table not in existing_tables:
                continue

            column_names = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if "user_id" not in column_names:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")

        conn.commit()


def users_count():
    ensure_security_schema()
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def claim_unowned_data(user_id: int):
    with connect() as conn:
        for table in [
            "honeypot_nodes",
            "classified_sessions",
            "risk_decisions",
            "sandbox_runs",
            "telemetry_analysis",
            "adaptive_recommendations",
            "adaptive_actions_log",
        ]:
            column_names = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if "user_id" in column_names:
                conn.execute(
                    f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL",
                    (user_id,),
                )
        conn.commit()


def create_access_token(user_id: int):
    raw_token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    hashed = token_hash(raw_token)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO api_tokens (user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, hashed, iso_now(), expires_at.isoformat()),
        )
        conn.commit()

    return raw_token, expires_at.isoformat()


def parse_access_token(authorization: str | None, cookie_token: str | None):
    if cookie_token:
        return cookie_token

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    cookie_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
):
    ensure_security_schema()
    token = parse_access_token(authorization, cookie_token)
    hashed = token_hash(token)

    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.username,
                u.role,
                u.is_active,
                t.token_hash,
                t.expires_at,
                t.revoked_at
            FROM api_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (hashed,),
        ).fetchone()

        if not row or row["revoked_at"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is disabled",
            )

        conn.execute(
            "UPDATE api_tokens SET last_used_at = ? WHERE token_hash = ?",
            (iso_now(), hashed),
        )
        conn.commit()

    return CurrentUser(
        id=row["id"],
        email=row["email"],
        username=row["username"],
        role=row["role"],
        token_hash=row["token_hash"],
    )


def require_admin(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def is_valid_email(value: str):
    return "@" in value and "." in value.rsplit("@", 1)[-1]


def password_policy_error(password: str):
    if len(password) < 12:
        return "Password must be at least 12 characters"
    if not any(char.islower() for char in password):
        return "Password must include a lowercase letter"
    if not any(char.isupper() for char in password):
        return "Password must include an uppercase letter"
    if not any(char.isdigit() for char in password):
        return "Password must include a digit"
    return None
