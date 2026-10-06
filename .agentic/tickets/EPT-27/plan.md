# EPT-27 — Backend: Platform Audit Trail

## Risk Tier: HIGH

Reasons: new database table (down migration loses all audit history), 11 existing files
instrumented, transactional commit structure changed in `claims.py`, security guard added
to a previously unguarded route.

---

## Database changes — read first

**Migration type:** additive DDL only (new table + indexes). No existing table is modified.

**Up (append to `database/init.sql`):**
```sql
CREATE TABLE audit_logs (
    id          SERIAL PRIMARY KEY,
    event_name  VARCHAR(100) NOT NULL,
    category    VARCHAR(50)  NOT NULL,
    actor_email VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   VARCHAR(100),
    severity    VARCHAR(20)  NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_created_at  ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_logs_category    ON audit_logs (category);
CREATE INDEX idx_audit_logs_severity    ON audit_logs (severity);
CREATE INDEX idx_audit_logs_actor_email ON audit_logs (actor_email);
CREATE INDEX idx_audit_logs_entity      ON audit_logs (entity_type, entity_id);
```

**Down:** `DROP TABLE audit_logs;` — **loses all audit history, not reversible.**

There is no migration framework (no Alembic). The table will be applied by rebuilding
the Docker container with the updated `init.sql`, or by running the DDL manually against
the running database.

---

## Summary

Implement the complete backend for the Platform Audit Trail:

1. Add `audit_logs` table (with required indexes) to `database/init.sql`.
2. Add `AuditLog` ORM model, three Pydantic schemas, and a `write_audit_event()` helper.
3. Instrument all 18 events from the Audit Event Catalogue across the relevant routes.
4. Add four missing trigger endpoints needed to cover the full catalogue.
5. Expose `GET /admin/audit-log` (paginated, filterable) and `GET /admin/audit-log/export`
   (CSV, capped at 1 000 rows) in `routers/admin.py`.
6. Write `ADMIN_AUDIT_LOG_EXPORTED` before the CSV stream begins.
7. Add `admin_only()` guard to the previously unguarded `PUT /claims/{id}/status` route
   (required for CLAIM_STATUS_ADMIN_CHANGED attribution to be meaningful).

---

## Detailed Steps

### Step 1 — `database/init.sql`
Append the `CREATE TABLE audit_logs` DDL and five `CREATE INDEX` statements after the
existing `adminlogs` table definition. No existing DDL is touched.

### Step 2 — `models.py`
Add `AuditLog` class after `AdminLogs`:

```python
from sqlalchemy.dialects.postgresql import JSONB

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    event_name  = Column(String(100), nullable=False)
    category    = Column(String(50),  nullable=False)
    actor_email = Column(String(255), nullable=False)
    entity_type = Column(String(50),  nullable=True)
    entity_id   = Column(String(100), nullable=True)
    severity    = Column(String(20),  nullable=False)
    metadata    = Column(JSONB,       nullable=True)
    created_at  = Column(TIMESTAMP,   server_default=func.now())
```

`entity_id` is `VARCHAR(100)` (not `INT`) so it can hold both integer IDs and any
future UUID-typed entities without schema changes.

### Step 3 — `schemas.py`
Add three schemas after `AdminLogResponse`:

```python
from typing import Optional, List

class AuditLogCreate(BaseModel):
    event_name:  str
    category:    str
    actor_email: str
    entity_type: Optional[str] = None
    entity_id:   Optional[str] = None
    severity:    str
    metadata:    Optional[dict] = None

class AuditLogResponse(BaseModel):
    id:          int
    event_name:  str
    category:    str
    actor_email: str
    entity_type: Optional[str]  = None
    entity_id:   Optional[str]  = None
    severity:    str
    metadata:    Optional[dict] = None
    created_at:  datetime

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    items:       List[AuditLogResponse]
    total_count: int
    page:        int
    page_size:   int
    total_pages: int
```

### Step 4 — `audit_helper.py` (new file)

```python
from sqlalchemy.orm import Session
from typing import Optional
import models

def write_audit_event(
    db:          Session,
    event_name:  str,
    category:    str,
    actor_email: str,
    severity:    str,
    entity_type: Optional[str] = None,
    entity_id:   Optional[str] = None,
    metadata:    Optional[dict] = None,
) -> None:
    db.add(models.AuditLog(
        event_name=event_name,
        category=category,
        actor_email=actor_email,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    ))
    # Caller must call db.commit() — this function never commits.
```

The helper never calls `db.commit()`. This is the load-bearing invariant for
transactional correctness: every audit event lives or dies with the transaction its
caller controls.

### Step 5 — Instrument `routers/login.py`

Two cases require restructuring the route to accept `db: Session`:

**USER_LOGIN_FAILURE** — two sub-cases (user not found / wrong password). Write the
audit event and commit it independently **before** raising the `HTTPException`. This
is the one legitimate case where the audit commit is not bundled with a triggering
action, because the triggering action (failed login) has no own transaction.

```python
# user not found branch
write_audit_event(db, "USER_LOGIN_FAILURE", "Authentication",
    actor_email=request.email, severity="WARNING",
    metadata={"attempted_email": request.email, "failure_reason": "user_not_found"})
db.commit()
raise HTTPException(status_code=401, ...)

# wrong password branch
write_audit_event(db, "USER_LOGIN_FAILURE", "Authentication",
    actor_email=request.email, severity="WARNING",
    metadata={"attempted_email": request.email, "failure_reason": "invalid_password"})
db.commit()
raise HTTPException(status_code=401, ...)
```

**USER_LOGIN_SUCCESS** — write after `create_access_token`, before the return.

```python
write_audit_event(db, "USER_LOGIN_SUCCESS", "Authentication",
    actor_email=user.email, severity="INFO",
    entity_type="User", entity_id=str(user.id),
    metadata={"user_id": user.id, "email": user.email})
db.commit()
return {...}
```

**POST /logout** — add a new endpoint to `routers/login.py`. JWT is stateless so
no server-side token revocation occurs; the endpoint exists solely to record the
event. Requires `get_current_user`.

```python
@router.post("/logout")
def logout(db: Session = Depends(get_db),
           current_user: models.User = Depends(get_current_user)):
    write_audit_event(db, "USER_LOGOUT", "Authentication",
        actor_email=current_user.email, severity="INFO",
        entity_type="User", entity_id=str(current_user.id),
        metadata={"user_id": current_user.id})
    db.commit()
    return {"message": "Logged out successfully"}
```

### Step 6 — Add `PUT /users/{user_id}/password` to `routers/risk_profile.py`

New endpoint (could also sit in `main.py`, but `risk_profile.py` already owns user
profile routes). Takes `{current_password: str, new_password: str}`. Verifies the
current password, hashes the new one, writes PASSWORD_CHANGED audit within the same
transaction as the password update.

```python
write_audit_event(db, "PASSWORD_CHANGED", "Authentication",
    actor_email=current_user.email, severity="WARNING",
    entity_type="User", entity_id=str(user_id),
    metadata={"user_id": user_id})
db.commit()
```

### Step 7 — Instrument `routers/claims.py`

**Commit pattern restructure** (critical for transactional correctness):

Current flow has two separate `db.commit()` calls. New flow uses `db.flush()` to get
the claim ID before the first commit, then bundles the CLAIM_SUBMITTED audit with the
first commit:

```python
db.add(new_claim)
db.flush()                          # assigns new_claim.id, stays in transaction
write_audit_event(db, "CLAIM_SUBMITTED", ...)
db.commit()                         # atomic: claim + CLAIM_SUBMITTED
db.refresh(new_claim)

fraud_flags, auto_changed = run_fraud_checks(db, new_claim)
if fraud_flags:
    write_audit_event(db, "CLAIM_FRAUD_FLAGGED", ...)
if auto_changed:
    write_audit_event(db, "CLAIM_STATUS_AUTO_CHANGED", ...)
db.commit()                         # atomic: fraud flags + status + audit events
```

`run_fraud_checks` is refactored to return `(list[tuple], bool)` — the flag list and
whether a status auto-change occurred — instead of committing internally (it currently
does not commit, just adds to the session; the return value is new).

**CLAIM_DOCUMENT_UPLOADED** — write before `db.commit()` inside `upload_claim_document`.

**CLAIM_STATUS_ADMIN_CHANGED** — add `admin_only()` dependency to
`PUT /claims/{id}/status`, capture old status before the mutation, write audit within
same `db.commit()`.

**POST /claims/{claim_id}/withdraw** (new endpoint) — user-facing, owner-only. Sets
`claim.status = "withdrawn"`. Writes CLAIM_WITHDRAWN audit within same commit.

### Step 8 — Instrument `routers/userpolicies.py`

**POLICY_DUPLICATE_ATTEMPT** — write and commit before raising the 400 in the
`existing` guard. (Same rationale as login failure: the triggering action is the
rejection, not a successful mutation.)

**POLICY_ACTIVATED** — write before `db.commit()` inside `activate_policy`.

**PUT /userpolicies/{user_policy_id}/auto-renew** (new endpoint) — owner-only.
Toggles `auto_renew`. Writes POLICY_AUTO_RENEW_TOGGLED audit within same commit.

### Step 9 — Instrument `routers/risk_profile.py`

**RISK_PROFILE_UPDATED** — write before `db.commit()` in `save_risk_profile`. Capture
old and new risk levels for the metadata:

```python
old_risk = (user.risk_profile or {}).get("risk_level")
# ... compute calculated_risk ...
write_audit_event(db, "RISK_PROFILE_UPDATED", "User Profile",
    actor_email=current_user.email, severity="INFO",
    entity_type="User", entity_id=str(user_id),
    metadata={"user_id": user_id, "old_risk_level": old_risk,
               "new_risk_level": calculated_risk, "changed_fields": list(request.model_fields)})
db.commit()
```

### Step 10 — Instrument `routers/recommendations.py`

**RECOMMENDATIONS_GENERATED** — write before `db.commit()` at the end of
`get_recommendations`. Metadata: `user_id`, `risk_level`, `count_returned`.

### Step 11 — Instrument `routers/admin.py`

**ADMIN_FRAUD_FLAGS_VIEWED** — add optional `severity_filter: str | None = None`
query param to `GET /admin/fraud-summary`. Write audit before returning.

**GET /admin/audit-log** (new) — paginated list with filters:
- Query params: `category`, `severity` (multi-value via `List[str]`), `date_from`,
  `date_to`, `actor_email`, `entity_type`, `entity_id`, `search`, `page=1`,
  `page_size=25` (server caps at 100).
- Filter logic: categories and severities use `IN`, date range uses `>=`/`<=` on
  `created_at` (UTC day boundaries), `actor_email` uses `ILIKE %value%`, `entity_type`
  uses exact match, `entity_id` uses exact match, `search` uses `OR` across
  `actor_email ILIKE` and `entity_id =`.
- Returns `AuditLogListResponse`.

**GET /admin/audit-log/export** (new) — same filter params, no pagination.
- Write ADMIN_AUDIT_LOG_EXPORTED audit event and commit **before** building the CSV.
- Query up to 1 000 rows (ordered by `created_at DESC`).
- Stream CSV as `StreamingResponse` with
  `Content-Disposition: attachment; filename=audit_log_YYYY-MM-DD.csv`.

### Step 12 — Instrument `main.py`

**USER_REGISTERED** — write before `db.commit()` in the `POST /signup` route.
Use `db.flush()` to get the new user's ID first.

---

## Files Changed

| File | Change type |
|---|---|
| `database/init.sql` | Append `audit_logs` DDL + indexes |
| `models.py` | Add `AuditLog` model |
| `schemas.py` | Add `AuditLogCreate`, `AuditLogResponse`, `AuditLogListResponse` |
| `audit_helper.py` | **New** — `write_audit_event()` |
| `main.py` | Instrument USER_REGISTERED |
| `routers/login.py` | Instrument USER_LOGIN_SUCCESS, USER_LOGIN_FAILURE; add POST /logout |
| `routers/risk_profile.py` | Instrument RISK_PROFILE_UPDATED; add PUT /users/{id}/password |
| `routers/claims.py` | Restructure commits; instrument 6 claim events; add POST /claims/{id}/withdraw; add admin_only to PUT /claims/{id}/status |
| `routers/userpolicies.py` | Instrument POLICY_ACTIVATED, POLICY_DUPLICATE_ATTEMPT; add PUT /userpolicies/{id}/auto-renew |
| `routers/recommendations.py` | Instrument RECOMMENDATIONS_GENERATED |
| `routers/admin.py` | Instrument ADMIN_FRAUD_FLAGS_VIEWED; add GET /admin/audit-log and GET /admin/audit-log/export |
| `tests/test_audit.py` | **New** — full test suite |

---

## Trade-offs and Assumptions

**`db.flush()` instead of `db.commit()` for pre-commit ID retrieval.**
This is the correct SQLAlchemy pattern for getting a sequence-assigned ID within a
transaction. It adds a round-trip but is cheaper than committing early and losing the
ability to roll back.

**`run_fraud_checks` returns a value rather than side-effecting silently.**
The function already adds to `db` but never commits (the caller does). Making it return
the flag list and `high_severity_found` boolean is a minimal change that enables the
caller to write the correct audit events without re-querying the DB.

**`entity_id` as `VARCHAR(100)` instead of `INT`.**
Integer IDs would be fine today, but the column would need to be altered if any entity
ever uses UUIDs. String coercion at write time (`str(claim.id)`) is trivial.

**POLICY_DUPLICATE_ATTEMPT and USER_LOGIN_FAILURE commit independently.**
These events have no successful triggering transaction to attach to — they record the
_failure_ of an attempted action. Committing them independently before raising the
exception is intentional and correct. The spec confirms this for USER_LOGIN_FAILURE
explicitly.

**Password change endpoint placed in `routers/risk_profile.py`.**
This router already owns the `/users/{user_id}/...` namespace. Keeping user-profile
mutations together avoids adding a new file for a single endpoint.

**`PUT /claims/{claim_id}/status` gains `admin_only()`.**
The route is currently unguarded — any authenticated user can mutate any claim's
status. Adding the admin guard is a prerequisite for the CLAIM_STATUS_ADMIN_CHANGED
event to have meaningful attribution. This is a security fix that is strictly in scope
for this ticket.

---

## Open Questions

None — the ticket and PRD are complete. All ambiguities resolved above.

---

## Out of Scope

- Customer-facing audit history.
- Real-time streaming / websocket delivery.
- Email / webhook notifications from audit events.
- Log archival, rotation, or forwarding to external systems.
- Export formats other than CSV.
- Sorting by any column other than `created_at DESC`.
- RBAC beyond the existing `ADMIN_EMAIL` mechanism.
- Bulk actions on audit log entries.
- A distinct admin login event (admin uses the same login flow; USER_LOGIN_SUCCESS covers it).
- Field-level diff for every model update column.
