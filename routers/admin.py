import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, or_
from fastapi.responses import StreamingResponse
from datetime import date, datetime, timezone
from typing import List, Optional
import csv
import io
import math

import models
import schemas
from database import get_db
from oauth2 import get_current_user
from audit_helper import write_audit_event

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

# -------------------------------------------------
# ADMIN ACCESS CHECK
# -------------------------------------------------
def admin_only(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# -------------------------------------------------
# GET ALL CLAIMS (WITH DOCUMENTS + FRAUD FLAGS)
# -------------------------------------------------
@router.get("/claims")
def get_all_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):

    claims = db.query(models.Claims).all()
    result = []

    for claim in claims:

        # Get documents
        documents = db.query(models.ClaimDocuments).filter(
            models.ClaimDocuments.claim_id == claim.id
        ).all()

        doc_list = [
            {
                "id": doc.id,
                "file_url": doc.file_url,
                "doc_type": doc.doc_type
            }
            for doc in documents
        ]

        # Get fraud flags
        fraud_flags = db.query(models.FraudFlags).filter(
            models.FraudFlags.claim_id == claim.id
        ).all()

        fraud_list = [
            {
                "rule_code": flag.rule_code,
                "severity": flag.severity,
                "details": flag.details
            }
            for flag in fraud_flags
        ]

        result.append({
            "id": claim.id,
            "claim_number": claim.claim_number,
            "amount_claimed": float(claim.amount_claimed),
            "status": claim.status,
            "created_at": claim.created_at,
            "documents": doc_list,
            "fraud_flags": fraud_list  # ✅ Added fraud flags
        })

    return result


# -------------------------------------------------
# DASHBOARD SUMMARY
# -------------------------------------------------
@router.get("/dashboard-summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):

    total_users = db.query(models.User).count()
    total_claims = db.query(models.Claims).count()
    total_policies = db.query(models.UserPolicies).count()
    total_fraud_flags = db.query(models.FraudFlags).count()

    total_premium = db.query(
        func.sum(models.UserPolicies.premium)
    ).scalar() or 0

    total_claim_amount = db.query(
        func.sum(models.Claims.amount_claimed)
    ).scalar() or 0

    return {
        "total_users": total_users,
        "total_claims": total_claims,
        "total_policies_sold": total_policies,
        "total_fraud_flags": total_fraud_flags,
        "total_premium_collected": float(total_premium),
        "total_claims_amount": float(total_claim_amount)
    }


# -------------------------------------------------
# FRAUD SUMMARY (Grouped by Rule)
# -------------------------------------------------
@router.get("/fraud-summary")
def fraud_summary(
    severity_filter: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    q = db.query(
        models.FraudFlags.rule_code,
        func.count(models.FraudFlags.id)
    )

    if severity_filter:
        q = q.filter(models.FraudFlags.severity == severity_filter)

    fraud_counts = q.group_by(models.FraudFlags.rule_code).all()

    # Write audit event
    write_audit_event(
        db, "ADMIN_FRAUD_FLAGS_VIEWED", "Admin Actions",
        actor_email=current_user.email, severity="INFO",
        metadata={"severity_filter": severity_filter} if severity_filter else {}
    )
    db.commit()

    return [
        {"rule_code": rule, "count": count}
        for rule, count in fraud_counts
    ]


# -------------------------------------------------
# MONTHLY CLAIM ANALYTICS
# -------------------------------------------------
@router.get("/monthly-claims")
def monthly_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):

    monthly = db.query(
        extract('month', models.Claims.created_at).label("month"),
        func.count(models.Claims.id)
    ).group_by("month").all()

    return [
        {"month": int(month), "total_claims": count}
        for month, count in monthly
    ]


# -------------------------------------------------
# EXPORT CLAIMS CSV
# -------------------------------------------------
@router.get("/export-claims")
def export_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):

    claims = db.query(models.Claims).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Claim Number",
        "Amount",
        "Status",
        "Created At"
    ])

    for claim in claims:
        writer.writerow([
            claim.claim_number,
            float(claim.amount_claimed),
            claim.status,
            claim.created_at
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=claims_export.csv"
        }
    )


# -------------------------------------------------
# AUDIT LOG LIST WITH FILTERS
# -------------------------------------------------
@router.get("/audit-log", response_model=schemas.AuditLogListResponse)
def list_audit_log(
    category:     Optional[List[str]] = Query(default=None),
    severity:     Optional[List[str]] = Query(default=None),
    date_from:    Optional[date]      = Query(default=None),
    date_to:      Optional[date]      = Query(default=None),
    actor_email:  Optional[str]       = Query(default=None),
    entity_type:  Optional[str]       = Query(default=None),
    entity_id:    Optional[str]       = Query(default=None),
    search:       Optional[str]       = Query(default=None),
    page:         int                 = Query(default=1, ge=1),
    page_size:    int                 = Query(default=25, ge=1, le=100),
    db:           Session             = Depends(get_db),
    current_user: models.User        = Depends(admin_only),
):
    q = db.query(models.AuditLog)

    if category:
        q = q.filter(models.AuditLog.category.in_(category))
    if severity:
        q = q.filter(models.AuditLog.severity.in_(severity))
    if date_from:
        dt_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0, tzinfo=timezone.utc)
        q = q.filter(models.AuditLog.created_at >= dt_from)
    if date_to:
        dt_to = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        q = q.filter(models.AuditLog.created_at <= dt_to)
    if actor_email:
        q = q.filter(models.AuditLog.actor_email.ilike(f"%{actor_email}%"))
    if entity_type:
        q = q.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(models.AuditLog.entity_id == entity_id)
    if search:
        q = q.filter(or_(
            models.AuditLog.actor_email.ilike(f"%{search}%"),
            models.AuditLog.entity_id == search,
        ))

    total_count = q.count()
    items = (q.order_by(models.AuditLog.created_at.desc())
              .offset((page - 1) * page_size)
              .limit(page_size)
              .all())

    total_pages = max(1, math.ceil(total_count / page_size))

    return schemas.AuditLogListResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------
# AUDIT LOG EXPORT CSV
# -------------------------------------------------
@router.get("/audit-log/export")
def export_audit_log(
    category:    Optional[List[str]] = Query(default=None),
    severity:    Optional[List[str]] = Query(default=None),
    date_from:   Optional[date]      = Query(default=None),
    date_to:     Optional[date]      = Query(default=None),
    actor_email: Optional[str]       = Query(default=None),
    entity_type: Optional[str]       = Query(default=None),
    entity_id:   Optional[str]       = Query(default=None),
    search:      Optional[str]       = Query(default=None),
    db:          Session             = Depends(get_db),
    current_user: models.User       = Depends(admin_only),
):
    from datetime import date as date_type
    today = date_type.today().strftime("%Y-%m-%d")

    # Build same query as list endpoint
    q = db.query(models.AuditLog)
    active_filters = {}

    if category:
        q = q.filter(models.AuditLog.category.in_(category))
        active_filters["category"] = category
    if severity:
        q = q.filter(models.AuditLog.severity.in_(severity))
        active_filters["severity"] = severity
    if date_from:
        dt_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0, tzinfo=timezone.utc)
        q = q.filter(models.AuditLog.created_at >= dt_from)
        active_filters["date_from"] = str(date_from)
    if date_to:
        dt_to = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        q = q.filter(models.AuditLog.created_at <= dt_to)
        active_filters["date_to"] = str(date_to)
    if actor_email:
        q = q.filter(models.AuditLog.actor_email.ilike(f"%{actor_email}%"))
        active_filters["actor_email"] = actor_email
    if entity_type:
        q = q.filter(models.AuditLog.entity_type == entity_type)
        active_filters["entity_type"] = entity_type
    if entity_id:
        q = q.filter(models.AuditLog.entity_id == entity_id)
        active_filters["entity_id"] = entity_id
    if search:
        q = q.filter(or_(
            models.AuditLog.actor_email.ilike(f"%{search}%"),
            models.AuditLog.entity_id == search,
        ))
        active_filters["search"] = search

    rows = q.order_by(models.AuditLog.created_at.desc()).limit(1000).all()
    row_count = len(rows)

    # Write ADMIN_AUDIT_LOG_EXPORTED BEFORE building the CSV stream
    write_audit_event(
        db, "ADMIN_AUDIT_LOG_EXPORTED", "Admin Actions",
        actor_email=current_user.email, severity="INFO",
        metadata={
            "active_filters": active_filters,
            "row_count": row_count
        }
    )
    db.commit()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "event_name", "category", "actor_email", "entity_type",
                     "entity_id", "severity", "metadata", "created_at"])
    for r in rows:
        writer.writerow([r.id, r.event_name, r.category, r.actor_email,
                         r.entity_type, r.entity_id, r.severity,
                         str(r.metadata), r.created_at])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_log_{today}.csv"}
    )