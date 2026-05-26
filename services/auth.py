"""
Auth service — Supabase GoTrue for production, in-memory fallback for dev.

Three roles:
  - admin    — NEST team. Full access.
  - client   — bond/position holders. Access to their own deals.
  - investor — LPs. Access to gated marketplace endpoints.

The `require_auth` decorator works with both backends — it verifies JWTs
regardless of whether they were issued by Supabase or the in-memory service.
"""
from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import httpx
import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config


VALID_ROLES = {"admin", "client", "investor"}


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    role: str
    name: str
    client_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def public(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "client_id": self.client_id,
            "created_at": self.created_at,
        }


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


class AuthService:
    """Dual-mode auth: Supabase GoTrue when configured, in-memory fallback."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._supabase_url = os.getenv("SUPABASE_URL", "")
        self._supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._use_supabase = bool(self._supabase_url and self._supabase_key)
        self._seed()

    def _seed(self) -> None:
        seeds = [
            ("admin@nest.local",    "Admin123!",    "admin",    "NEST Admin",      None),
            ("client@nest.local",   "Client123!",   "client",   "Demo Client",     "demo"),
            ("investor@nest.local", "Investor123!", "investor", "Redwood Family",  None),
        ]
        for email, pw, role, name, client_id in seeds:
            self._create_local(email=email, password=pw, role=role, name=name, client_id=client_id)

    # ---------- local (in-memory) ----------

    def _create_local(self, *, email: str, password: str, role: str, name: str,
                      client_id: Optional[str] = None) -> User:
        email = email.strip().lower()
        if role not in VALID_ROLES:
            raise AuthError(f"invalid role: {role}", status=400)
        if not email or "@" not in email:
            raise AuthError("invalid email", status=400)
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters", status=400)
        with self._lock:
            if email in self._users_by_email:
                raise AuthError("email already registered", status=409)
            user = User(
                id=f"usr_{uuid.uuid4().hex[:10]}",
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                name=name.strip() or email.split("@")[0],
                client_id=client_id,
            )
            self._users_by_id[user.id] = user
            self._users_by_email[user.email] = user
            return user

    # ---------- Supabase GoTrue ----------

    def _gotrue_headers(self):
        return {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
        }

    def _supabase_signup(self, email: str, password: str, name: str, role: str) -> dict:
        """Create user via Supabase GoTrue admin API."""
        try:
            r = httpx.post(
                f"{self._supabase_url}/auth/v1/admin/users",
                headers=self._gotrue_headers(),
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"name": name, "role": role},
                },
                timeout=10,
            )
            if r.status_code in (200, 201):
                data = r.json()
                return {
                    "id": data["id"],
                    "email": data["email"],
                    "role": data.get("user_metadata", {}).get("role", "client"),
                    "name": data.get("user_metadata", {}).get("name", ""),
                    "created_at": data.get("created_at", ""),
                }
            elif r.status_code == 422:
                raise AuthError("email already registered", status=409)
            else:
                raise AuthError(f"signup failed: {r.text}", status=r.status_code)
        except httpx.HTTPError as e:
            raise AuthError(f"auth service unavailable: {e}", status=503)

    def _supabase_login(self, email: str, password: str) -> dict:
        """Authenticate via Supabase GoTrue."""
        try:
            r = httpx.post(
                f"{self._supabase_url}/auth/v1/token?grant_type=password",
                headers={"apikey": self._supabase_key, "Content-Type": "application/json"},
                json={"email": email, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                user_meta = data.get("user", {}).get("user_metadata", {})
                return {
                    "token": data["access_token"],
                    "refresh_token": data.get("refresh_token"),
                    "expires_at": datetime.fromtimestamp(
                        data.get("expires_at", 0), tz=timezone.utc
                    ).isoformat() if data.get("expires_at") else None,
                    "user": {
                        "id": data["user"]["id"],
                        "email": data["user"]["email"],
                        "role": user_meta.get("role", "client"),
                        "name": user_meta.get("name", ""),
                    },
                }
            else:
                raise AuthError("invalid email or password", status=401)
        except httpx.HTTPError as e:
            raise AuthError(f"auth service unavailable: {e}", status=503)

    # ---------- public API ----------

    def register(self, *, email: str, password: str, name: str,
                 role: str = "client", client_id: Optional[str] = None) -> User:
        if role != "client":
            raise AuthError("only client accounts can self-register", status=403)
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise AuthError("invalid email", status=400)
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters", status=400)

        if self._use_supabase:
            try:
                data = self._supabase_signup(email, password, name, role)
                # Also cache locally for token verification
                user = User(
                    id=data["id"], email=email,
                    password_hash=generate_password_hash(password),
                    role=role, name=name.strip() or email.split("@")[0],
                    client_id=client_id,
                )
                with self._lock:
                    self._users_by_id[user.id] = user
                    self._users_by_email[user.email] = user
                return user
            except AuthError:
                raise
            except Exception:
                pass  # Fall through to local

        return self._create_local(email=email, password=password, role=role,
                                  name=name, client_id=client_id)

    def authenticate(self, email: str, password: str) -> User:
        email = (email or "").strip().lower()

        if self._use_supabase:
            try:
                result = self._supabase_login(email, password)
                # Return a token dict directly — caller handles it
                user_data = result["user"]
                user = User(
                    id=user_data["id"], email=user_data["email"],
                    password_hash="", role=user_data.get("role", "client"),
                    name=user_data.get("name", ""),
                )
                with self._lock:
                    self._users_by_id[user.id] = user
                    self._users_by_email[user.email] = user
                user._supabase_token = result  # Attach for route handler
                return user
            except AuthError:
                raise
            except Exception:
                pass  # Fall through to local

        with self._lock:
            user = self._users_by_email.get(email)
        if user is None or not check_password_hash(user.password_hash, password or ""):
            raise AuthError("invalid email or password", status=401)
        return user

    def change_password(self, user: User, current: str, new: str) -> None:
        if not check_password_hash(user.password_hash, current or ""):
            raise AuthError("current password is incorrect", status=401)
        if len(new) < 8:
            raise AuthError("new password must be at least 8 characters", status=400)
        with self._lock:
            user.password_hash = generate_password_hash(new)

    def get_user(self, user_id: str) -> Optional[User]:
        with self._lock:
            return self._users_by_id.get(user_id)

    # ---------- JWT ----------

    def issue_token(self, user: User) -> dict:
        # If Supabase auth returned a token, use it
        if hasattr(user, "_supabase_token"):
            return user._supabase_token

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=Config.JWT_TTL_HOURS)
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "client_id": user.client_id,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
        return {"token": token, "expires_at": exp.isoformat(), "user": user.public()}

    def verify_token(self, token: str) -> User:
        if not token:
            raise AuthError("missing token", status=401)

        # Try local JWT first
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user = self.get_user(payload.get("sub", ""))
            if user:
                return user
        except jwt.InvalidTokenError:
            pass

        # Try Supabase JWT (different secret — uses Supabase JWT secret)
        if self._use_supabase:
            try:
                r = httpx.get(
                    f"{self._supabase_url}/auth/v1/user",
                    headers={
                        "apikey": self._supabase_key,
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    meta = data.get("user_metadata", {})
                    user = User(
                        id=data["id"], email=data.get("email", ""),
                        password_hash="",
                        role=meta.get("role", "client"),
                        name=meta.get("name", ""),
                    )
                    with self._lock:
                        self._users_by_id[user.id] = user
                        self._users_by_email[user.email] = user
                    return user
            except Exception:
                pass

        raise AuthError("invalid token", status=401)


# ---------- Flask plumbing ----------

def _service() -> AuthService:
    return current_app.config["AUTH"]


def _bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.args.get("token")


def require_auth(*roles: str):
    """
    Decorator: enforce a valid token and (optionally) one of the given roles.

    Usage:
        @bp.get("/thing")
        @require_auth()              # any authenticated user
        def thing(): ...

        @bp.post("/admin-thing")
        @require_auth("admin")       # admin only
        def admin_thing(): ...
    """
    allowed = set(roles)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Demo bypass — allows unauthenticated access when NEST_DEMO_MODE=1
            if os.environ.get("NEST_DEMO_MODE") == "1":
                g.current_user = User(
                    id="demo-admin", email="sean@nestadvisors.com",
                    password_hash="", role="admin", name="Sean Gilmore (Demo)",
                )
                return fn(*args, **kwargs)
            try:
                user = _service().verify_token(_bearer_token() or "")
            except AuthError as e:
                return jsonify({"error": str(e)}), e.status
            if allowed and user.role not in allowed:
                return jsonify({"error": "forbidden", "required_roles": sorted(allowed)}), 403
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user() -> Optional[User]:
    return getattr(g, "current_user", None)
