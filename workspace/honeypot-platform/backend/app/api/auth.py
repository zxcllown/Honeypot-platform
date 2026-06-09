from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.security import (
    CurrentUser,
    claim_unowned_data,
    connect,
    create_access_token,
    get_current_user,
    hash_password,
    is_valid_email,
    iso_now,
    password_policy_error,
    require_admin,
    token_hash,
    users_count,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    role: str = "analyst"


class UpdateUserRequest(BaseModel):
    username: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    password: str


def public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def validate_user_payload(email: str, username: str, password: str):
    email = email.strip().lower()
    username = username.strip()

    if not is_valid_email(email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email")
    if len(username) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Username is too short")

    password_error = password_policy_error(password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, password_error)

    return email, username


@router.get("/bootstrap-status")
def bootstrap_status():
    return {
        "bootstrap_required": users_count() == 0,
    }


@router.post("/bootstrap")
def bootstrap_owner(payload: BootstrapRequest):
    if users_count() > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bootstrap is already completed",
        )

    email, username = validate_user_payload(
        payload.email,
        payload.username,
        payload.password,
    )
    created_at = iso_now()

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (
                email,
                username,
                password_hash,
                role,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'admin', 1, ?, ?)
            """,
            (email, username, hash_password(payload.password), created_at, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid

    claim_unowned_data(user_id)
    access_token, expires_at = create_access_token(user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": {
            "id": user_id,
            "email": email,
            "username": username,
            "role": "admin",
            "is_active": True,
            "created_at": created_at,
            "updated_at": created_at,
        },
    }


@router.post("/login")
def login(payload: LoginRequest):
    email = payload.email.strip().lower()

    with connect() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if (
        not user
        or not user["is_active"]
        or not verify_password(payload.password, user["password_hash"])
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_at = create_access_token(user["id"])

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": public_user(user),
    }


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
    }


@router.post("/logout")
def logout(current_user: CurrentUser = Depends(get_current_user)):
    with connect() as conn:
        conn.execute(
            "UPDATE api_tokens SET revoked_at = ? WHERE token_hash = ?",
            (iso_now(), current_user.token_hash),
        )
        conn.commit()

    return {"status": "ok"}


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
):
    if payload.role not in ("admin", "analyst"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid role")

    email, username = validate_user_payload(
        payload.email,
        payload.username,
        payload.password,
    )
    created_at = iso_now()

    try:
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    email,
                    username,
                    password_hash,
                    role,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    email,
                    username,
                    hash_password(payload.password),
                    payload.role,
                    created_at,
                    created_at,
                ),
            )
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        raise

    return public_user(user)


@router.get("/users")
def list_users(_admin: CurrentUser = Depends(require_admin)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                email,
                username,
                role,
                is_active,
                created_at,
                updated_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()

    return {
        "items": [public_user(row) for row in rows],
        "count": len(rows),
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    admin: CurrentUser = Depends(require_admin),
):
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        with connect() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return public_user(user)

    if "role" in updates and updates["role"] not in ("admin", "analyst"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid role")

    if "username" in updates:
        username = updates["username"].strip()
        if len(username) < 2:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Username is too short")
        updates["username"] = username

    if admin.id == user_id:
        if updates.get("is_active") is False:
            raise HTTPException(status.HTTP_409_CONFLICT, "You cannot disable your own account")
        if updates.get("role") == "analyst":
            raise HTTPException(status.HTTP_409_CONFLICT, "You cannot demote your own account")

    updates["updated_at"] = iso_now()
    assignments = ", ".join(f"{key} = ?" for key in updates)

    with connect() as conn:
        current = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not current:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        conn.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            list(updates.values()) + [user_id],
        )

        if updates.get("is_active") is False:
            conn.execute(
                "UPDATE api_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (iso_now(), user_id),
            )

        conn.commit()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return public_user(user)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    _admin: CurrentUser = Depends(require_admin),
):
    password_error = password_policy_error(payload.password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, password_error)

    with connect() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        conn.execute(
            """
            UPDATE users
            SET password_hash = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (hash_password(payload.password), iso_now(), user_id),
        )
        conn.execute(
            "UPDATE api_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (iso_now(), user_id),
        )
        conn.commit()

    return {
        "user_id": user_id,
        "password_reset": True,
        "sessions_revoked": True,
    }
