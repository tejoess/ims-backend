from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import random
import string
import os

import models
import schemas
from database import get_db
from oauth2 import get_current_user
from audit_helper import write_audit_event

router = APIRouter(
    prefix="/claims",
    tags=["Claims"]
)

UPLOAD_DIR = "uploaded_claim_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------
# GENERATE CLAIM NUMBER
# -----------------------------
def generate_claim_number():
    return "CLM-" + ''.join(random.choices(string.digits, k=6))


# -----------------------------
# FRAUD RULES ENGINE
# -----------------------------
def run_fraud_checks(db: Session, claim: models.Claims):
    """
    Run fraud detection rules on a claim.
    Returns (fraud_flags, auto_changed) where:
    - fraud_flags: list of (rule_code, severity, details) tuples
    - auto_changed: True if status was automatically changed to under_review
    """
    fraud_flags = []
    high_severity_found = False

    # Rule 1: Large Amount
    if float(claim.amount_claimed) > 100000:
        fraud_flags.append(("HIGH_AMOUNT", "high", "Claim amount exceeds 100000"))
        high_severity_found = True

    # Rule 2: Suspicious Timing
    user_policy = db.query(models.UserPolicies).filter(
        models.UserPolicies.id == claim.user_policy_id
    ).first()

    if user_policy:
        days_difference = (claim.incident_date - user_policy.start_date).days
        if days_difference <= 7:
            fraud_flags.append(("SUSPICIOUS_TIMING", "medium",
                                "Claim filed within 7 days of policy start"))

    # Rule 3: Duplicate Claim Amount
    duplicate_claim = db.query(models.Claims).filter(
        models.Claims.user_policy_id == claim.user_policy_id,
        models.Claims.amount_claimed == claim.amount_claimed,
        models.Claims.id != claim.id
    ).first()

    if duplicate_claim:
        fraud_flags.append(("DUPLICATE_AMOUNT", "medium",
                            "Duplicate claim amount detected"))

    # Rule 4: Multiple Claims in 3 Days
    three_days_ago = datetime.utcnow() - timedelta(days=3)

    recent_claims = db.query(models.Claims).filter(
        models.Claims.user_policy_id == claim.user_policy_id,
        models.Claims.created_at >= three_days_ago,
        models.Claims.id != claim.id
    ).count()

    if recent_claims >= 2:
        fraud_flags.append(("MULTIPLE_RECENT_CLAIMS", "high",
                            "Multiple claims filed within 3 days"))
        high_severity_found = True

    # Add fraud flags to DB
    for rule_code, severity, details in fraud_flags:
        db.add(models.FraudFlags(
            claim_id=claim.id,
            rule_code=rule_code,
            severity=severity,
            details=details
        ))

    # Auto-change status if high severity found
    if high_severity_found:
        claim.status = "under_review"

    return fraud_flags, high_severity_found


# -----------------------------
# CREATE CLAIM
# -----------------------------
@router.post("/")
def create_claim(
    request: schemas.ClaimCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    user_policy = (
        db.query(models.UserPolicies)
        .filter(
            models.UserPolicies.id == request.user_policy_id,
            models.UserPolicies.user_id == current_user.id
        )
        .first()
    )

    if not user_policy:
        raise HTTPException(status_code=403, detail="Invalid user policy")

    new_claim = models.Claims(
        user_policy_id=request.user_policy_id,
        claim_number=generate_claim_number(),
        claim_type=request.claim_type,
        incident_date=request.incident_date,
        amount_claimed=request.amount_claimed,
        status="submitted"
    )

    db.add(new_claim)
    db.flush()  # Get new_claim.id without committing

    # Write CLAIM_SUBMITTED audit event
    write_audit_event(
        db, "CLAIM_SUBMITTED", "Claims",
        actor_email=current_user.email, severity="INFO",
        entity_type="Claim", entity_id=str(new_claim.id),
        metadata={
            "claim_id": new_claim.id,
            "claim_number": new_claim.claim_number,
            "user_policy_id": request.user_policy_id,
            "amount": str(request.amount_claimed)
        }
    )
    db.commit()  # Atomic: claim + CLAIM_SUBMITTED
    db.refresh(new_claim)

    # Run fraud checks
    fraud_flags, auto_changed = run_fraud_checks(db, new_claim)

    # Write fraud audit events if needed
    if fraud_flags:
        write_audit_event(
            db, "CLAIM_FRAUD_FLAGGED", "Claims",
            actor_email="system@fraud-engine", severity="WARNING",
            entity_type="Claim", entity_id=str(new_claim.id),
            metadata={
                "claim_id": new_claim.id,
                "flag_types": [f[0] for f in fraud_flags],
                "severities": [f[1] for f in fraud_flags]
            }
        )

    if auto_changed:
        write_audit_event(
            db, "CLAIM_STATUS_AUTO_CHANGED", "Claims",
            actor_email="system@fraud-engine", severity="WARNING",
            entity_type="Claim", entity_id=str(new_claim.id),
            metadata={
                "claim_id": new_claim.id,
                "old_status": "submitted",
                "new_status": "under_review",
                "triggered_by": "fraud_engine"
            }
        )

    db.commit()  # Atomic: fraud flags + audit events

    return {
        "id": new_claim.id,
        "claim_number": new_claim.claim_number,
        "status": new_claim.status
    }


# -----------------------------
# GET CLAIMS FOR USER
# -----------------------------
@router.get("/")
def get_user_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    claims = (
        db.query(models.Claims)
        .join(models.UserPolicies)
        .filter(models.UserPolicies.user_id == current_user.id)
        .all()
    )

    return [
        {
            "id": claim.id,
            "claim_number": claim.claim_number,
            "amount_claimed": float(claim.amount_claimed),
            "incident_date": claim.incident_date,
            "status": claim.status,
            "created_at": claim.created_at
        }
        for claim in claims
    ]


# -----------------------------
# UPLOAD CLAIM DOCUMENT (FIXED VERSION)
# -----------------------------
@router.post("/{claim_id}/upload")
def upload_claim_document(
    claim_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    claim = (
        db.query(models.Claims)
        .join(models.UserPolicies)
        .filter(
            models.Claims.id == claim_id,
            models.UserPolicies.user_id == current_user.id
        )
        .first()
    )

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    try:
        file_bytes = file.file.read()

        safe_filename = f"{claim_id}_{file.filename.replace(' ', '_')}"
        file_location = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_location, "wb") as buffer:
            buffer.write(file_bytes)

        # Stored locally (Google Drive upload disabled for this setup)
        file_url = f"/{file_location}"

        new_doc = models.ClaimDocuments(
            claim_id=claim_id,
            file_url=file_url,
            doc_type="general"
        )

        db.add(new_doc)

        # Write audit event before commit
        write_audit_event(
            db, "CLAIM_DOCUMENT_UPLOADED", "Claims",
            actor_email=current_user.email, severity="INFO",
            entity_type="Claim", entity_id=str(claim_id),
            metadata={
                "claim_id": claim_id,
                "filename": file.filename,
                "size_bytes": len(file_bytes)
            }
        )
        db.commit()

        return {
            "message": "File uploaded successfully",
            "file_url": file_url
        }

    except Exception as e:
        db.rollback()
        print("UPLOAD ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# UPDATE CLAIM STATUS (ADMIN)
# -----------------------------
class ClaimStatusUpdate(BaseModel):
    status: str
    admin_comment: Optional[str] = None


# Admin email check for claims router
ADMIN_EMAIL_CLAIMS = os.getenv("ADMIN_EMAIL")


@router.put("/{claim_id}/status")
def update_claim_status(
    claim_id: int,
    request: ClaimStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Admin access check
    if current_user.email != ADMIN_EMAIL_CLAIMS:
        raise HTTPException(status_code=403, detail="Admin access required")

    claim = db.query(models.Claims).filter(
        models.Claims.id == claim_id
    ).first()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    old_status = claim.status
    claim.status = request.status

    # Write audit event
    write_audit_event(
        db, "CLAIM_STATUS_ADMIN_CHANGED", "Claims",
        actor_email=current_user.email, severity="CRITICAL",
        entity_type="Claim", entity_id=str(claim_id),
        metadata={
            "claim_id": claim_id,
            "old_status": old_status,
            "new_status": request.status,
            "admin_comment": request.admin_comment
        }
    )
    db.commit()

    # Status-update email notification disabled (Celery/SMTP not used in this setup)

    return {
        "message": "Claim status updated successfully",
        "claim_id": claim.id,
        "new_status": claim.status
    }


# -----------------------------
# WITHDRAW CLAIM
# -----------------------------
@router.post("/{claim_id}/withdraw")
def withdraw_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify ownership
    claim = (
        db.query(models.Claims)
        .join(models.UserPolicies)
        .filter(
            models.Claims.id == claim_id,
            models.UserPolicies.user_id == current_user.id
        )
        .first()
    )

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.status = "withdrawn"

    write_audit_event(
        db, "CLAIM_WITHDRAWN", "Claims",
        actor_email=current_user.email, severity="INFO",
        entity_type="Claim", entity_id=str(claim_id),
        metadata={
            "claim_id": claim_id,
            "claim_number": claim.claim_number
        }
    )
    db.commit()

    return {"message": "Claim withdrawn successfully"}