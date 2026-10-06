# EPT-27 — Test Plan

## Acceptance Criteria → Test Case Traceability

| AC-id | Acceptance Criterion (from ticket) | TC-ids |
|---|---|---|
| AC-01 | audit_logs table created with correct columns, indexes, constraints | TC-001 |
| AC-02 | Every catalogue event produces an audit_logs row on trigger | TC-002 – TC-018 |
| AC-03 | USER_LOGIN_FAILURE captured without authenticated session | TC-019 |
| AC-04 | All audit writes transactional — rollback leaves no orphan row | TC-020 |
| AC-05 | GET /admin/audit-log: paginated + all filters work | TC-021 – TC-028 |
| AC-06 | GET /admin/audit-log/export: CSV download, capped at 1 000, writes ADMIN_AUDIT_LOG_EXPORTED | TC-029, TC-030 |
| AC-07 | Audit endpoints protected by admin_only() → 403 for non-admin | TC-031 |
| AC-08 | No PUT/PATCH/DELETE on /admin/audit-log → 404 or 405 | TC-032 |
| AC-09 | ADMIN_AUDIT_LOG_EXPORTED written before CSV streamed | TC-033 |

---

## Test Cases

### Infrastructure

**TC-001** (AC-01) — Table schema and indexes
- Connect directly to the PostgreSQL database after applying updated `init.sql`.
- Verify `audit_logs` table exists with columns: `id`, `event_name`, `category`,
  `actor_email`, `entity_type`, `entity_id`, `severity`, `metadata`, `created_at`.
- Verify five indexes: `idx_audit_logs_created_at`, `idx_audit_logs_category`,
  `idx_audit_logs_severity`, `idx_audit_logs_actor_email`, `idx_audit_logs_entity`.
- Verify `event_name`, `category`, `actor_email`, `severity`, `created_at` are NOT NULL.
- Verify `metadata` column is JSONB.

---

### Audit Event Catalogue — one TC per event

**TC-002** (AC-02) — USER_LOGIN_SUCCESS
- POST /login with valid credentials.
- Assert one `audit_logs` row: `event_name=USER_LOGIN_SUCCESS`, `category=Authentication`,
  `severity=INFO`, `actor_email=<user_email>`, `entity_type=User`,
  `entity_id=str(user.id)`, `metadata` contains `user_id` and `email`.

**TC-003** (AC-02, AC-03) — USER_LOGIN_FAILURE (user not found)
- POST /login with an email that does not exist.
- Assert one `audit_logs` row: `event_name=USER_LOGIN_FAILURE`, `severity=WARNING`,
  `actor_email=<attempted_email>`, `entity_type=None`,
  `metadata.failure_reason=user_not_found`.
- Assert response is 401 (the audit write does not swallow the error).

**TC-004** (AC-02, AC-03) — USER_LOGIN_FAILURE (wrong password)
- POST /login with a registered email but wrong password.
- Assert row: same shape as TC-003, `metadata.failure_reason=invalid_password`.

**TC-005** (AC-02) — USER_LOGOUT
- POST /logout with a valid Bearer token.
- Assert one `audit_logs` row: `event_name=USER_LOGOUT`, `category=Authentication`,
  `severity=INFO`, `actor_email=<user_email>`, `entity_type=User`.

**TC-006** (AC-02) — PASSWORD_CHANGED
- PUT /users/{id}/password with correct `current_password` and new `new_password`.
- Assert one row: `event_name=PASSWORD_CHANGED`, `severity=WARNING`, `entity_type=User`.

**TC-007** (AC-02) — CLAIM_SUBMITTED
- POST /claims/ with a valid `user_policy_id`.
- Assert one row: `event_name=CLAIM_SUBMITTED`, `category=Claims`, `severity=INFO`,
  `entity_type=Claim`, `entity_id=str(new_claim.id)`,
  `metadata` contains `claim_id`, `claim_number`, `user_policy_id`, `amount`.

**TC-008** (AC-02) — CLAIM_FRAUD_FLAGGED
- POST /claims/ with `amount_claimed > 100 000` (triggers HIGH_AMOUNT rule).
- Assert one `CLAIM_FRAUD_FLAGGED` row: `severity=WARNING`, `entity_type=Claim`,
  `metadata` contains `flag_types` list and `severities` list.

**TC-009** (AC-02) — CLAIM_STATUS_AUTO_CHANGED
- POST /claims/ with `amount_claimed > 100 000` (which sets status to `under_review`).
- Assert one `CLAIM_STATUS_AUTO_CHANGED` row: `severity=WARNING`, `entity_type=Claim`,
  `metadata` contains `old_status`, `new_status`, `triggered_by`.

**TC-010** (AC-02) — CLAIM_STATUS_ADMIN_CHANGED
- PUT /claims/{id}/status as admin with a status change.
- Assert one `CLAIM_STATUS_ADMIN_CHANGED` row: `severity=CRITICAL`, `entity_type=Claim`,
  `metadata` contains `claim_id`, `old_status`, `new_status`, `admin_comment`.
- Assert the same call as a non-admin returns 403 and writes NO audit row.

**TC-011** (AC-02) — CLAIM_DOCUMENT_UPLOADED
- POST /claims/{id}/upload a file.
- Assert one row: `event_name=CLAIM_DOCUMENT_UPLOADED`, `category=Claims`,
  `severity=INFO`, `metadata` contains `claim_id`, `filename`, `size_bytes`.

**TC-012** (AC-02) — CLAIM_WITHDRAWN
- POST /claims/{id}/withdraw as the claim's owner.
- Assert one row: `event_name=CLAIM_WITHDRAWN`, `category=Claims`, `severity=INFO`,
  `metadata` contains `claim_id`, `claim_number`.
- Assert claim `status` is now `withdrawn`.

**TC-013** (AC-02) — POLICY_ACTIVATED
- POST /userpolicies/{policy_id} to activate a new policy.
- Assert one row: `event_name=POLICY_ACTIVATED`, `category=Policies`, `severity=INFO`,
  `entity_type=UserPolicy`, `metadata` contains `user_policy_id`, `policy_id`,
  `policy_number`, `premium`.

**TC-014** (AC-02) — POLICY_DUPLICATE_ATTEMPT
- POST /userpolicies/{policy_id} for a policy the user already holds.
- Assert one row: `event_name=POLICY_DUPLICATE_ATTEMPT`, `severity=WARNING`,
  `metadata` contains `policy_id`, `existing_user_policy_id`.
- Assert response is 400.

**TC-015** (AC-02) — POLICY_AUTO_RENEW_TOGGLED
- PUT /userpolicies/{id}/auto-renew with `{"auto_renew": false}`.
- Assert one row: `event_name=POLICY_AUTO_RENEW_TOGGLED`, `severity=INFO`,
  `metadata` contains `user_policy_id`, `old_value`, `new_value`.

**TC-016** (AC-02) — USER_REGISTERED
- POST /signup with a unique email.
- Assert one row: `event_name=USER_REGISTERED`, `category=User Profile`,
  `severity=INFO`, `entity_type=User`, `metadata` contains `user_id`, `email`.

**TC-017** (AC-02) — RISK_PROFILE_UPDATED
- POST /users/{id}/risk-profile.
- Assert one row: `event_name=RISK_PROFILE_UPDATED`, `severity=INFO`,
  `metadata` contains `user_id`, `old_risk_level`, `new_risk_level`, `changed_fields`.

**TC-018** (AC-02) — RECOMMENDATIONS_GENERATED
- GET /users/{id}/recommendations (user must have a risk profile set).
- Assert one row: `event_name=RECOMMENDATIONS_GENERATED`, `category=Recommendations`,
  `severity=INFO`, `metadata` contains `user_id`, `risk_level`, `count_returned`.

---

### Transactional Correctness

**TC-019** (AC-03) — USER_LOGIN_FAILURE does not require a session
- Run TC-003 or TC-004 without any Bearer token in the request.
- Assert the audit row exists.
- Assert the login response is 401.

**TC-020** (AC-04) — Rolled-back claim leaves no orphan CLAIM_SUBMITTED row
- Force a DB error after `db.flush()` but before `db.commit()` in the claim creation
  path (e.g., by inserting a duplicate claim_number via a test fixture).
- Assert no `CLAIM_SUBMITTED` row exists for that failed attempt.
- Note: this test may require a test-specific route override or transaction rollback
  fixture depending on test setup. Mark as integration test.

---

### Admin List Endpoint

**TC-021** (AC-05) — Unfiltered paginated list
- Seed 30 audit_logs rows. GET /admin/audit-log with no params.
- Assert: `total_count=30`, `page=1`, `page_size=25`, `total_pages=2`,
  `len(items)=25`, results ordered by `created_at DESC`.

**TC-022** (AC-05) — category filter (single)
- Seed rows for Authentication and Claims categories. GET /admin/audit-log?category=Claims.
- Assert: only Claims rows returned.

**TC-023** (AC-05) — severity filter (multi-value)
- Seed INFO and WARNING rows. GET /admin/audit-log?severity=INFO&severity=WARNING.
- Assert: both INFO and WARNING rows returned; no CRITICAL rows if any exist.

**TC-024** (AC-05) — date_from / date_to filter
- Seed rows across multiple dates. GET /admin/audit-log?date_from=2026-01-01&date_to=2026-01-31.
- Assert: only rows with `created_at` in January 2026 returned.

**TC-025** (AC-05) — actor_email partial match
- Seed rows for `alice@example.com` and `bob@example.com`.
  GET /admin/audit-log?actor_email=alice.
- Assert: only alice rows returned (case-insensitive partial match).

**TC-026** (AC-05) — entity_type filter
- Seed Claim and User entity type rows. GET /admin/audit-log?entity_type=Claim.
- Assert: only Claim rows returned.

**TC-027** (AC-05) — combined filters (AND logic)
- GET /admin/audit-log?category=Claims&severity=WARNING.
- Assert: only rows where category=Claims AND severity=WARNING.

**TC-028** (AC-05) — empty result
- GET /admin/audit-log?category=NonExistentCategory.
- Assert: `total_count=0`, `items=[]`, response 200 (not 404).

---

### CSV Export Endpoint

**TC-029** (AC-06) — CSV structure and row cap
- Seed 1 200 audit_logs rows. GET /admin/audit-log/export.
- Assert: response is `text/csv`, `Content-Disposition` header contains
  `audit_log_YYYY-MM-DD.csv`.
- Parse CSV body: assert exactly 1 000 data rows (plus header row).
- Assert rows are ordered by `created_at DESC` (most recent 1 000).

**TC-030** (AC-06) — ADMIN_AUDIT_LOG_EXPORTED event written on export
- GET /admin/audit-log/export.
- Assert one `ADMIN_AUDIT_LOG_EXPORTED` row exists after the request completes,
  with `metadata` containing `active_filters` and `row_count`.

**TC-033** (AC-09) — ADMIN_AUDIT_LOG_EXPORTED written before the stream
- GET /admin/audit-log/export.
- Before the response body is consumed, query the DB for `ADMIN_AUDIT_LOG_EXPORTED`.
- Assert the row exists (write precedes streaming). Implementation: the route commits
  the audit event before constructing the `StreamingResponse`.

---

### Access Control

**TC-031** (AC-07) — Non-admin receives 403 on both audit endpoints
- GET /admin/audit-log with a non-admin Bearer token → 403.
- GET /admin/audit-log/export with a non-admin Bearer token → 403.

**TC-032** (AC-08) — No modification endpoints exposed
- PUT /admin/audit-log → 405 or 404.
- PATCH /admin/audit-log/{id} → 405 or 404.
- DELETE /admin/audit-log/{id} → 405 or 404.

---

## Test Infrastructure Notes

- All test cases above are backend unit/integration tests. No frontend component
  is tested here (EPT-26 covers frontend).
- Tests run against the real PostgreSQL instance (no mocking of the DB layer per
  project conventions).
- Each test function must run in a transaction that is rolled back on teardown, OR
  use isolated test-specific data with cleanup, to avoid cross-test pollution.
- TC-020 (rollback test) may need a pytest fixture that patches `db.commit` to raise
  after `flush`.
