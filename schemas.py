from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


# -----------------------------
# SIGNUP
# -----------------------------
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    dob: date


# -----------------------------
# LOGIN
# -----------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


# -----------------------------
# RISK PROFILE
# -----------------------------
class RiskProfileRequest(BaseModel):
    age: int
    annual_income: int
    dependents: int
    health_condition: str


# -----------------------------
# CLAIM CREATE
# -----------------------------
class ClaimCreate(BaseModel):
    user_policy_id: int
    claim_type: str
    incident_date: date
    amount_claimed: Decimal


# -----------------------------
# CLAIM RESPONSE
# -----------------------------
class ClaimResponse(BaseModel):
    id: int
    claim_number: str
    claim_type: str
    incident_date: date
    amount_claimed: Decimal
    status: str

    class Config:
        from_attributes = True


# -----------------------------
# MY POLICIES (USER POLICY + POLICY DETAILS)
# -----------------------------
class UserPolicyResponse(BaseModel):
    id: int
    policy_id: int
    policy_number: str
    start_date: date
    end_date: date
    premium: Decimal
    status: str
    auto_renew: bool
    title: str | None = None
    policy_type: str | None = None
    coverage: dict | None = None

    class Config:
        from_attributes = True


# -----------------------------
# ADMIN LOG RESPONSE
# -----------------------------
class AdminLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# -----------------------------
# AUDIT LOG
# -----------------------------
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