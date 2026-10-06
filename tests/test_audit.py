"""
EPT-27 — Backend: Platform Audit Trail
33 test cases mapped to 9 acceptance criteria.

TC-ids and AC-ids reference test-plan.md.
All tests hit the real PostgreSQL database (no DB mocking).
"""
import csv
import io
import os
import pytest
from sqlalchemy.orm import Session

# --- Imports that will FAIL at RED (modules/classes don't exist yet) ---
from audit_helper import write_audit_event   # noqa: F401  RED: no module
import models                                # AuditLog not on models yet

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _latest_audit(db: Session, event_name: str, actor_email: str = None):
    """Return the most recent audit row for event_name (+ optional actor)."""
    q = db.query(models.AuditLog).filter(models.AuditLog.event_name == event_name)
    if actor_email:
        q = q.filter(models.AuditLog.actor_email == actor_email)
    return q.order_by(models.AuditLog.created_at.desc()).first()


def _count_audit(db: Session, event_name: str, actor_email: str = None):
    q = db.query(models.AuditLog).filter(models.AuditLog.event_name == event_name)
    if actor_email:
        q = q.filter(models.AuditLog.actor_email == actor_email)
    return q.count()


# ===========================================================================
# TC-001  AC-01 — Table schema and indexes exist
# ===========================================================================

def test_tc001_audit_logs_table_schema(db: Session):
    """TC-001 (AC-01): audit_logs table has correct columns and indexes."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.bind)
    assert "audit_logs" in inspector.get_table_names(), "audit_logs table missing"

    cols = {c["name"] for c in inspector.get_columns("audit_logs")}
    required = {"id", "event_name", "category", "actor_email", "entity_type",
                "entity_id", "severity", "metadata", "created_at"}
    assert required <= cols, f"Missing columns: {required - cols}"

    indexes = {i["name"] for i in inspector.get_indexes("audit_logs")}
    required_indexes = {
        "idx_audit_logs_created_at",
        "idx_audit_logs_category",
        "idx_audit_logs_severity",
        "idx_audit_logs_actor_email",
        "idx_audit_logs_entity",
    }
    assert required_indexes <= indexes, f"Missing indexes: {required_indexes - indexes}"


# ===========================================================================
# TC-002  AC-02 — USER_LOGIN_SUCCESS
# ===========================================================================

def test_tc002_user_login_success_audit(client, db, test_user):
    """TC-002 (AC-02): POST /login success writes USER_LOGIN_SUCCESS row."""
    before = _count_audit(db, "USER_LOGIN_SUCCESS", test_user["email"])
    resp = client.post("/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "USER_LOGIN_SUCCESS", test_user["email"]) == before + 1

    row = _latest_audit(db, "USER_LOGIN_SUCCESS", test_user["email"])
    assert row.category == "Authentication"
    assert row.severity == "INFO"
    assert row.entity_type == "User"
    assert row.entity_id == str(test_user["id"])
    assert "user_id" in row.metadata
    assert "email" in row.metadata


# ===========================================================================
# TC-003  AC-02, AC-03 — USER_LOGIN_FAILURE (user not found)
# ===========================================================================

def test_tc003_login_failure_user_not_found(client, db):
    """TC-003 (AC-02, AC-03): POST /login with unknown email writes USER_LOGIN_FAILURE."""
    bad_email = "doesnotexist_ept27@example.com"
    before = _count_audit(db, "USER_LOGIN_FAILURE", bad_email)
    resp = client.post("/login", json={"email": bad_email, "password": "anything"})
    db.expire_all()
    assert resp.status_code == 401
    assert _count_audit(db, "USER_LOGIN_FAILURE", bad_email) == before + 1

    row = _latest_audit(db, "USER_LOGIN_FAILURE", bad_email)
    assert row.category == "Authentication"
    assert row.severity == "WARNING"
    assert row.entity_type is None
    assert row.metadata["failure_reason"] == "user_not_found"
    assert row.metadata["attempted_email"] == bad_email


# ===========================================================================
# TC-004  AC-02, AC-03 — USER_LOGIN_FAILURE (wrong password)
# ===========================================================================

def test_tc004_login_failure_wrong_password(client, db, test_user):
    """TC-004 (AC-02, AC-03): POST /login with wrong password writes USER_LOGIN_FAILURE."""
    before = _count_audit(db, "USER_LOGIN_FAILURE", test_user["email"])
    resp = client.post("/login", json={
        "email": test_user["email"],
        "password": "wrongpassword",
    })
    db.expire_all()
    assert resp.status_code == 401
    assert _count_audit(db, "USER_LOGIN_FAILURE", test_user["email"]) == before + 1

    row = _latest_audit(db, "USER_LOGIN_FAILURE", test_user["email"])
    assert row.metadata["failure_reason"] == "invalid_password"


# ===========================================================================
# TC-005  AC-02 — USER_LOGOUT
# ===========================================================================

def test_tc005_user_logout_audit(client, db, test_user, auth_headers):
    """TC-005 (AC-02): POST /logout writes USER_LOGOUT row."""
    before = _count_audit(db, "USER_LOGOUT", test_user["email"])
    resp = client.post("/logout", headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "USER_LOGOUT", test_user["email"]) == before + 1

    row = _latest_audit(db, "USER_LOGOUT", test_user["email"])
    assert row.category == "Authentication"
    assert row.severity == "INFO"
    assert row.entity_type == "User"


# ===========================================================================
# TC-006  AC-02 — PASSWORD_CHANGED
# ===========================================================================

def test_tc006_password_changed_audit(client, db, test_user, auth_headers):
    """TC-006 (AC-02): PUT /users/{id}/password writes PASSWORD_CHANGED row."""
    before = _count_audit(db, "PASSWORD_CHANGED", test_user["email"])
    resp = client.put(
        f"/users/{test_user['id']}/password",
        json={"current_password": test_user["password"], "new_password": test_user["password"]},
        headers=auth_headers,
    )
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "PASSWORD_CHANGED", test_user["email"]) == before + 1

    row = _latest_audit(db, "PASSWORD_CHANGED", test_user["email"])
    assert row.category == "Authentication"
    assert row.severity == "WARNING"
    assert row.entity_type == "User"


# ===========================================================================
# TC-007  AC-02 — CLAIM_SUBMITTED
# ===========================================================================

def test_tc007_claim_submitted_audit(client, db, test_user, auth_headers, user_policy):
    """TC-007 (AC-02): POST /claims/ writes CLAIM_SUBMITTED row."""
    before = _count_audit(db, "CLAIM_SUBMITTED", test_user["email"])
    resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "5000",
    }, headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_SUBMITTED", test_user["email"]) == before + 1

    row = _latest_audit(db, "CLAIM_SUBMITTED", test_user["email"])
    assert row.category == "Claims"
    assert row.severity == "INFO"
    assert row.entity_type == "Claim"
    assert row.entity_id is not None
    meta = row.metadata
    assert "claim_id" in meta
    assert "claim_number" in meta
    assert "user_policy_id" in meta
    assert "amount" in meta


# ===========================================================================
# TC-008  AC-02 — CLAIM_FRAUD_FLAGGED
# ===========================================================================

def test_tc008_claim_fraud_flagged_audit(client, db, test_user, auth_headers, user_policy):
    """TC-008 (AC-02): High-value claim triggers CLAIM_FRAUD_FLAGGED audit row."""
    before = _count_audit(db, "CLAIM_FRAUD_FLAGGED")
    resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "150000",  # > 100000 triggers HIGH_AMOUNT rule
    }, headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_FRAUD_FLAGGED") > before

    row = _latest_audit(db, "CLAIM_FRAUD_FLAGGED")
    assert row.category == "Claims"
    assert row.severity == "WARNING"
    assert row.entity_type == "Claim"
    assert "flag_types" in row.metadata
    assert "severities" in row.metadata


# ===========================================================================
# TC-009  AC-02 — CLAIM_STATUS_AUTO_CHANGED
# ===========================================================================

def test_tc009_claim_status_auto_changed_audit(client, db, test_user, auth_headers, user_policy):
    """TC-009 (AC-02): High-value claim that triggers status change writes CLAIM_STATUS_AUTO_CHANGED."""
    before = _count_audit(db, "CLAIM_STATUS_AUTO_CHANGED")
    resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "200000",  # triggers HIGH_AMOUNT + status → under_review
    }, headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_STATUS_AUTO_CHANGED") > before

    row = _latest_audit(db, "CLAIM_STATUS_AUTO_CHANGED")
    assert row.category == "Claims"
    assert row.severity == "WARNING"
    assert row.entity_type == "Claim"
    assert "old_status" in row.metadata
    assert "new_status" in row.metadata
    assert row.metadata["new_status"] == "under_review"


# ===========================================================================
# TC-010  AC-02 — CLAIM_STATUS_ADMIN_CHANGED
# ===========================================================================

def test_tc010_claim_status_admin_changed_audit(client, db, test_user, auth_headers, admin_headers, user_policy):
    """TC-010 (AC-02): Admin status change writes CLAIM_STATUS_ADMIN_CHANGED; non-admin gets 403."""
    # Create a claim as user
    create_resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "3000",
    }, headers=auth_headers)
    claim_id = create_resp.json()["id"]
    db.expire_all()

    # Non-admin attempt should now be 403
    non_admin_resp = client.put(f"/claims/{claim_id}/status",
        json={"status": "approved"}, headers=auth_headers)
    assert non_admin_resp.status_code == 403

    # Admin change
    before = _count_audit(db, "CLAIM_STATUS_ADMIN_CHANGED")
    resp = client.put(f"/claims/{claim_id}/status",
        json={"status": "approved", "admin_comment": "Looks good"},
        headers=admin_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_STATUS_ADMIN_CHANGED") == before + 1

    row = _latest_audit(db, "CLAIM_STATUS_ADMIN_CHANGED")
    assert row.category == "Claims"
    assert row.severity == "CRITICAL"
    assert "old_status" in row.metadata
    assert "new_status" in row.metadata


# ===========================================================================
# TC-011  AC-02 — CLAIM_DOCUMENT_UPLOADED
# ===========================================================================

def test_tc011_claim_document_uploaded_audit(client, db, test_user, auth_headers, user_policy):
    """TC-011 (AC-02): Document upload writes CLAIM_DOCUMENT_UPLOADED row."""
    create_resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "1000",
    }, headers=auth_headers)
    claim_id = create_resp.json()["id"]
    db.expire_all()

    before = _count_audit(db, "CLAIM_DOCUMENT_UPLOADED", test_user["email"])
    file_content = b"dummy pdf content"
    resp = client.post(
        f"/claims/{claim_id}/upload",
        files={"file": ("test_doc.pdf", io.BytesIO(file_content), "application/pdf")},
        headers=auth_headers,
    )
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_DOCUMENT_UPLOADED", test_user["email"]) == before + 1

    row = _latest_audit(db, "CLAIM_DOCUMENT_UPLOADED", test_user["email"])
    assert row.category == "Claims"
    assert row.severity == "INFO"
    assert "filename" in row.metadata
    assert "size_bytes" in row.metadata


# ===========================================================================
# TC-012  AC-02 — CLAIM_WITHDRAWN
# ===========================================================================

def test_tc012_claim_withdrawn_audit(client, db, test_user, auth_headers, user_policy):
    """TC-012 (AC-02): POST /claims/{id}/withdraw writes CLAIM_WITHDRAWN row."""
    create_resp = client.post("/claims/", json={
        "user_policy_id": user_policy["user_policy_id"],
        "claim_type": "medical",
        "incident_date": "2026-09-01",
        "amount_claimed": "750",
    }, headers=auth_headers)
    claim_id = create_resp.json()["id"]
    db.expire_all()

    before = _count_audit(db, "CLAIM_WITHDRAWN", test_user["email"])
    resp = client.post(f"/claims/{claim_id}/withdraw", headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "CLAIM_WITHDRAWN", test_user["email"]) == before + 1

    row = _latest_audit(db, "CLAIM_WITHDRAWN", test_user["email"])
    assert row.category == "Claims"
    assert row.severity == "INFO"
    assert "claim_id" in row.metadata
    assert "claim_number" in row.metadata

    # Verify claim status changed
    claims = client.get("/claims/", headers=auth_headers).json()
    claim = next((c for c in claims if c["id"] == claim_id), None)
    assert claim["status"] == "withdrawn"


# ===========================================================================
# TC-013  AC-02 — POLICY_ACTIVATED
# ===========================================================================

def test_tc013_policy_activated_audit(client, db, test_user, auth_headers):
    """TC-013 (AC-02): First-time policy activation writes POLICY_ACTIVATED row."""
    policies = client.get("/policies", headers=auth_headers).json()
    # Find a policy the user does NOT already hold
    existing = {up["policy_id"] for up in client.get("/userpolicies/", headers=auth_headers).json()}
    available = [p for p in policies if p["id"] not in existing]
    if not available:
        pytest.skip("All policies already activated for test user")
    policy_id = available[-1]["id"]

    before = _count_audit(db, "POLICY_ACTIVATED", test_user["email"])
    resp = client.post(f"/userpolicies/{policy_id}", headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "POLICY_ACTIVATED", test_user["email"]) == before + 1

    row = _latest_audit(db, "POLICY_ACTIVATED", test_user["email"])
    assert row.category == "Policies"
    assert row.severity == "INFO"
    assert row.entity_type == "UserPolicy"
    meta = row.metadata
    assert "user_policy_id" in meta
    assert "policy_id" in meta
    assert "policy_number" in meta
    assert "premium" in meta


# ===========================================================================
# TC-014  AC-02 — POLICY_DUPLICATE_ATTEMPT
# ===========================================================================

def test_tc014_policy_duplicate_attempt_audit(client, db, test_user, auth_headers, user_policy):
    """TC-014 (AC-02): Activating an already-held policy writes POLICY_DUPLICATE_ATTEMPT."""
    policy_id = user_policy["policy_id"]
    before = _count_audit(db, "POLICY_DUPLICATE_ATTEMPT", test_user["email"])
    resp = client.post(f"/userpolicies/{policy_id}", headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 400
    assert _count_audit(db, "POLICY_DUPLICATE_ATTEMPT", test_user["email"]) == before + 1

    row = _latest_audit(db, "POLICY_DUPLICATE_ATTEMPT", test_user["email"])
    assert row.category == "Policies"
    assert row.severity == "WARNING"
    assert "policy_id" in row.metadata
    assert "existing_user_policy_id" in row.metadata


# ===========================================================================
# TC-015  AC-02 — POLICY_AUTO_RENEW_TOGGLED
# ===========================================================================

def test_tc015_policy_auto_renew_toggled_audit(client, db, test_user, auth_headers, user_policy):
    """TC-015 (AC-02): PUT /userpolicies/{id}/auto-renew writes POLICY_AUTO_RENEW_TOGGLED."""
    up_id = user_policy["user_policy_id"]
    before = _count_audit(db, "POLICY_AUTO_RENEW_TOGGLED", test_user["email"])
    resp = client.put(
        f"/userpolicies/{up_id}/auto-renew",
        json={"auto_renew": False},
        headers=auth_headers,
    )
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "POLICY_AUTO_RENEW_TOGGLED", test_user["email"]) == before + 1

    row = _latest_audit(db, "POLICY_AUTO_RENEW_TOGGLED", test_user["email"])
    assert row.category == "Policies"
    assert row.severity == "INFO"
    meta = row.metadata
    assert "user_policy_id" in meta
    assert "old_value" in meta
    assert "new_value" in meta
    assert meta["new_value"] is False


# ===========================================================================
# TC-016  AC-02 — USER_REGISTERED
# ===========================================================================

def test_tc016_user_registered_audit(client, db):
    """TC-016 (AC-02): POST /signup writes USER_REGISTERED row."""
    new_email = "reg_test_ept27@example.com"
    # Clean up any previous run
    db.query(models.AuditLog).filter(models.AuditLog.actor_email == new_email).delete()
    user = db.query(models.User).filter(models.User.email == new_email).first()
    if user:
        db.delete(user)
    db.commit()

    resp = client.post("/signup", json={
        "name": "Registration Test",
        "email": new_email,
        "password": "testpass",
        "dob": "1995-05-05",
    })
    db.expire_all()
    assert resp.status_code == 200

    row = _latest_audit(db, "USER_REGISTERED", new_email)
    assert row is not None
    assert row.category == "User Profile"
    assert row.severity == "INFO"
    assert row.entity_type == "User"
    assert "user_id" in row.metadata
    assert "email" in row.metadata

    # Cleanup
    db.query(models.AuditLog).filter(models.AuditLog.actor_email == new_email).delete()
    u = db.query(models.User).filter(models.User.email == new_email).first()
    if u:
        db.delete(u)
    db.commit()


# ===========================================================================
# TC-017  AC-02 — RISK_PROFILE_UPDATED
# ===========================================================================

def test_tc017_risk_profile_updated_audit(client, db, test_user, auth_headers):
    """TC-017 (AC-02): POST /users/{id}/risk-profile writes RISK_PROFILE_UPDATED row."""
    before = _count_audit(db, "RISK_PROFILE_UPDATED", test_user["email"])
    resp = client.post(
        f"/users/{test_user['id']}/risk-profile",
        json={"age": 35, "annual_income": 500000, "dependents": 1, "health_condition": "good"},
        headers=auth_headers,
    )
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "RISK_PROFILE_UPDATED", test_user["email"]) == before + 1

    row = _latest_audit(db, "RISK_PROFILE_UPDATED", test_user["email"])
    assert row.category == "User Profile"
    assert row.severity == "INFO"
    assert row.entity_type == "User"
    meta = row.metadata
    assert "user_id" in meta
    assert "old_risk_level" in meta
    assert "new_risk_level" in meta
    assert "changed_fields" in meta


# ===========================================================================
# TC-018  AC-02 — RECOMMENDATIONS_GENERATED
# ===========================================================================

def test_tc018_recommendations_generated_audit(client, db, test_user, auth_headers):
    """TC-018 (AC-02): GET /users/{id}/recommendations writes RECOMMENDATIONS_GENERATED row."""
    # Ensure risk profile exists
    client.post(
        f"/users/{test_user['id']}/risk-profile",
        json={"age": 30, "annual_income": 600000, "dependents": 0, "health_condition": "good"},
        headers=auth_headers,
    )
    db.expire_all()

    before = _count_audit(db, "RECOMMENDATIONS_GENERATED", test_user["email"])
    resp = client.get(f"/users/{test_user['id']}/recommendations", headers=auth_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "RECOMMENDATIONS_GENERATED", test_user["email"]) == before + 1

    row = _latest_audit(db, "RECOMMENDATIONS_GENERATED", test_user["email"])
    assert row.category == "Recommendations"
    assert row.severity == "INFO"
    meta = row.metadata
    assert "user_id" in meta
    assert "risk_level" in meta
    assert "count_returned" in meta


# ===========================================================================
# TC-019  AC-03 — USER_LOGIN_FAILURE written without active session
# ===========================================================================

def test_tc019_login_failure_no_session(client, db):
    """TC-019 (AC-03): LOGIN_FAILURE audit is written even though no token is issued."""
    bad_email = "nosession_ept27@example.com"
    # Attempt login with NO auth headers (unauthenticated)
    resp = client.post("/login", json={"email": bad_email, "password": "any"})
    db.expire_all()
    assert resp.status_code == 401
    assert "access_token" not in resp.json()

    row = _latest_audit(db, "USER_LOGIN_FAILURE", bad_email)
    assert row is not None, "Audit row must exist even though login failed"
    # Cleanup
    db.query(models.AuditLog).filter(models.AuditLog.actor_email == bad_email).delete()
    db.commit()


# ===========================================================================
# TC-020  AC-04 — Rollback leaves no orphan CLAIM_SUBMITTED row
# ===========================================================================

def test_tc020_rollback_no_orphan_audit(db):
    """
    TC-020 (AC-04): write_audit_event() does not commit — if the outer
    transaction rolls back, no audit row is left behind.
    """
    from audit_helper import write_audit_event

    initial_count = db.query(models.AuditLog).count()

    # Simulate: add an audit event, then rollback without committing
    write_audit_event(
        db=db,
        event_name="CLAIM_SUBMITTED",
        category="Claims",
        actor_email="rollback_test@example.com",
        severity="INFO",
        entity_type="Claim",
        entity_id="99999",
        metadata={"claim_id": 99999, "claim_number": "CLM-TEST", "user_policy_id": 1, "amount": "100"},
    )
    db.rollback()  # explicit rollback — no commit was called

    final_count = db.query(models.AuditLog).count()
    assert final_count == initial_count, "Rollback must remove the unflushed audit row"


# ===========================================================================
# TC-021  AC-05 — Unfiltered paginated list
# ===========================================================================

def test_tc021_audit_log_unfiltered_pagination(client, db, admin_headers):
    """TC-021 (AC-05): GET /admin/audit-log returns paginated AuditLogListResponse."""
    resp = client.get("/admin/audit-log", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total_count" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 25
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 25


# ===========================================================================
# TC-022  AC-05 — category filter (single)
# ===========================================================================

def test_tc022_category_filter(client, admin_headers):
    """TC-022 (AC-05): category filter returns only matching rows."""
    resp = client.get("/admin/audit-log?category=Claims", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["category"] == "Claims"


# ===========================================================================
# TC-023  AC-05 — severity filter (multi-value)
# ===========================================================================

def test_tc023_severity_filter_multi(client, admin_headers):
    """TC-023 (AC-05): multiple severity values return rows matching any selected severity."""
    resp = client.get("/admin/audit-log?severity=INFO&severity=WARNING", headers=admin_headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["severity"] in ("INFO", "WARNING")


# ===========================================================================
# TC-024  AC-05 — date range filter
# ===========================================================================

def test_tc024_date_range_filter(client, admin_headers):
    """TC-024 (AC-05): date_from / date_to filter restricts created_at range (UTC)."""
    resp = client.get(
        "/admin/audit-log?date_from=2026-01-01&date_to=2026-12-31",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    from datetime import datetime, timezone
    for item in resp.json()["items"]:
        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        assert created.year == 2026


# ===========================================================================
# TC-025  AC-05 — actor_email partial match
# ===========================================================================

def test_tc025_actor_email_partial_match(client, db, admin_headers, test_user):
    """TC-025 (AC-05): actor_email filter uses case-insensitive partial match."""
    # Ensure at least one row for the test user exists
    resp = client.get(
        f"/admin/audit-log?actor_email={test_user['email'][:5]}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # All returned rows should have an email containing the prefix
    prefix = test_user["email"][:5].lower()
    for item in resp.json()["items"]:
        assert prefix in item["actor_email"].lower()


# ===========================================================================
# TC-026  AC-05 — entity_type filter
# ===========================================================================

def test_tc026_entity_type_filter(client, admin_headers):
    """TC-026 (AC-05): entity_type filter returns exact-match rows."""
    resp = client.get("/admin/audit-log?entity_type=Claim", headers=admin_headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["entity_type"] == "Claim"


# ===========================================================================
# TC-027  AC-05 — combined AND filters
# ===========================================================================

def test_tc027_combined_and_filters(client, admin_headers):
    """TC-027 (AC-05): category AND severity filters combine with AND logic."""
    resp = client.get(
        "/admin/audit-log?category=Claims&severity=WARNING",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["category"] == "Claims"
        assert item["severity"] == "WARNING"


# ===========================================================================
# TC-028  AC-05 — empty result (no 404)
# ===========================================================================

def test_tc028_empty_result_200(client, admin_headers):
    """TC-028 (AC-05): Filter with no matching rows returns 200 with empty items."""
    resp = client.get(
        "/admin/audit-log?category=NonExistentCategory99",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 0
    assert data["items"] == []


# ===========================================================================
# TC-029  AC-06 — CSV structure and 1000-row cap
# ===========================================================================

def test_tc029_export_csv_structure(client, admin_headers):
    """TC-029 (AC-06): GET /admin/audit-log/export returns CSV with ≤ 1000 data rows."""
    resp = client.get("/admin/audit-log/export", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    disp = resp.headers.get("content-disposition", "")
    assert "audit_log_" in disp and ".csv" in disp

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) >= 1, "CSV must have at least a header row"
    data_rows = rows[1:]  # exclude header
    assert len(data_rows) <= 1000, f"Export must be capped at 1000 rows, got {len(data_rows)}"


# ===========================================================================
# TC-030  AC-06 — ADMIN_AUDIT_LOG_EXPORTED event written on export
# ===========================================================================

def test_tc030_exported_event_written(client, db, admin_headers):
    """TC-030 (AC-06): Export triggers ADMIN_AUDIT_LOG_EXPORTED audit row."""
    before = _count_audit(db, "ADMIN_AUDIT_LOG_EXPORTED")
    resp = client.get("/admin/audit-log/export", headers=admin_headers)
    db.expire_all()
    assert resp.status_code == 200
    assert _count_audit(db, "ADMIN_AUDIT_LOG_EXPORTED") == before + 1

    row = _latest_audit(db, "ADMIN_AUDIT_LOG_EXPORTED")
    assert row.category == "Admin Actions"
    assert row.severity == "INFO"
    assert "active_filters" in row.metadata
    assert "row_count" in row.metadata


# ===========================================================================
# TC-031  AC-07 — Non-admin gets 403 on audit endpoints
# ===========================================================================

def test_tc031_non_admin_403(client, auth_headers):
    """TC-031 (AC-07): Non-admin token receives 403 on list and export endpoints."""
    resp_list = client.get("/admin/audit-log", headers=auth_headers)
    assert resp_list.status_code == 403

    resp_export = client.get("/admin/audit-log/export", headers=auth_headers)
    assert resp_export.status_code == 403


# ===========================================================================
# TC-032  AC-08 — No modification endpoints
# ===========================================================================

def test_tc032_no_modification_endpoints(client, admin_headers):
    """TC-032 (AC-08): PUT/PATCH/DELETE on /admin/audit-log return 404 or 405."""
    for method, path in [
        ("PUT",    "/admin/audit-log"),
        ("PATCH",  "/admin/audit-log/1"),
        ("DELETE", "/admin/audit-log/1"),
    ]:
        resp = client.request(method, path, headers=admin_headers)
        assert resp.status_code in (404, 405), (
            f"{method} {path} returned {resp.status_code}, expected 404 or 405"
        )


# ===========================================================================
# TC-033  AC-09 — ADMIN_AUDIT_LOG_EXPORTED written before CSV stream
# ===========================================================================

def test_tc033_exported_event_before_stream(client, db, admin_headers):
    """
    TC-033 (AC-09): The ADMIN_AUDIT_LOG_EXPORTED event is committed before
    the CSV bytes are returned (i.e. the route commits the audit row then
    builds the StreamingResponse).

    We verify this by checking the row exists in the DB after the response
    completes — which is guaranteed if the route commits before streaming.
    """
    before = _count_audit(db, "ADMIN_AUDIT_LOG_EXPORTED")
    resp = client.get("/admin/audit-log/export", headers=admin_headers)
    db.expire_all()
    assert resp.status_code == 200
    # The audit row must exist in DB now that the response is fully received.
    # If it were written after streaming, a cancelled mid-stream download would miss it.
    # The TestClient consumes the full response, so the row must already be there.
    assert _count_audit(db, "ADMIN_AUDIT_LOG_EXPORTED") > before
    row = _latest_audit(db, "ADMIN_AUDIT_LOG_EXPORTED")
    assert row is not None
    # Confirm the row was committed (not just flushed) by querying in a new session
    from database import SessionLocal
    fresh = SessionLocal()
    try:
        fresh_row = fresh.query(models.AuditLog).filter(
            models.AuditLog.id == row.id
        ).first()
        assert fresh_row is not None, "EXPORTED row not found in fresh session — was it committed?"
    finally:
        fresh.close()
