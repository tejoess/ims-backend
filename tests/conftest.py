"""
Test fixtures for EPT-27 — Backend: Platform Audit Trail.

Provides TestClient, admin/user tokens, and per-test audit log cleanup.
Tests hit the real PostgreSQL database (no mocking per project convention).
"""
import os
import pytest

# Let the app's own load_dotenv() (in database.py) handle DATABASE_URL from .env.
# Only override vars that may not be in .env in CI/test environments.
os.environ.setdefault("SECRET_KEY", "testsecretkey_epm27")

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal, engine
import models


# ---------------------------------------------------------------------------
# DB session fixture — each test rolls back to a clean state via direct
# audit_log row cleanup rather than outer-transaction nesting (psycopg2 compat)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


def _cleanup_audit(db: Session, actor_email: str = None, event_names: list = None):
    """Delete audit log rows matching actor_email or event_names."""
    q = db.query(models.AuditLog)
    if actor_email:
        q = q.filter(models.AuditLog.actor_email == actor_email)
    if event_names:
        q = q.filter(models.AuditLog.event_name.in_(event_names))
    q.delete(synchronize_session=False)
    db.commit()


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test user fixtures
# ---------------------------------------------------------------------------

TEST_USER_EMAIL = "testuser_ept27@example.com"
TEST_USER_PASSWORD = "testpass123"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass123"


@pytest.fixture(scope="session")
def test_user(client):
    """Create a test user once per session; delete on teardown."""
    resp = client.post("/signup", json={
        "name": "Test User EPT27",
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "dob": "1990-01-01",
    })
    # 200 = created; 200 with "already registered" = exists from prior run
    user_id = resp.json().get("user_id")
    if not user_id:
        # Already exists — fetch via login
        login = client.post("/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
        user_id = login.json()["user_id"]
    yield {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "id": user_id}
    # Teardown: remove user and all cascade data
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == TEST_USER_EMAIL).first()
        if user:
            db.query(models.AuditLog).filter(models.AuditLog.actor_email == TEST_USER_EMAIL).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


@pytest.fixture(scope="function")
def user_token(client, test_user):
    resp = client.post("/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def admin_token(client):
    resp = client.post("/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    data = resp.json()
    if "access_token" not in data:
        pytest.skip("Admin user not configured — set ADMIN_EMAIL/ADMIN_PASSWORD and ensure admin exists")
    return data["access_token"]


@pytest.fixture(scope="function")
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------------------------------------------------------------------
# Seed a policy + user_policy for claim-related tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def user_policy(client, test_user, auth_headers, db):
    """Return a user_policy_id the test user can file claims against."""
    # Pick the first available policy
    policies = client.get("/policies", headers=auth_headers).json()
    if not policies:
        pytest.skip("No policies seeded — run init.sql first")
    policy_id = policies[0]["id"]

    # Activate (ignore 400 if already active from previous test run)
    activate = client.post(f"/userpolicies/{policy_id}", headers=auth_headers)
    if activate.status_code not in (200, 400):
        activate.raise_for_status()

    # Fetch user policies to get the id
    up_list = client.get("/userpolicies/", headers=auth_headers).json()
    user_policy_id = next(
        (up["id"] for up in up_list if up["policy_id"] == policy_id), None
    )
    if not user_policy_id:
        pytest.skip("Could not resolve user_policy_id")
    return {"user_policy_id": user_policy_id, "policy_id": policy_id}
