from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
from pydantic import BaseModel
import random

import models
import schemas
from database import get_db
from oauth2 import get_current_user
from audit_helper import write_audit_event

router = APIRouter(
    prefix="/userpolicies",
    tags=["User Policies"]
)

# ===========================
# ACTIVATE POLICY (BUY)
# ===========================
@router.post("/{policy_id}")
def activate_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if policy exists
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Check if already activated
    existing = db.query(models.UserPolicies).filter(
        models.UserPolicies.user_id == current_user.id,
        models.UserPolicies.policy_id == policy_id
    ).first()

    if existing:
        # Write audit event and commit BEFORE raising exception
        write_audit_event(
            db, "POLICY_DUPLICATE_ATTEMPT", "Policies",
            actor_email=current_user.email, severity="WARNING",
            entity_type="UserPolicy",
            metadata={
                "policy_id": policy_id,
                "existing_user_policy_id": existing.id
            }
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Policy already activated")

    policy_number = f"POL-{random.randint(10000,99999)}"

    new_user_policy = models.UserPolicies(
        user_id=current_user.id,
        policy_id=policy_id,
        policy_number=policy_number,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        premium=policy.premium,
        status="active",
        auto_renew=True
    )

    db.add(new_user_policy)
    db.flush()  # Get new_user_policy.id without committing

    # Write POLICY_ACTIVATED audit event
    write_audit_event(
        db, "POLICY_ACTIVATED", "Policies",
        actor_email=current_user.email, severity="INFO",
        entity_type="UserPolicy", entity_id=str(new_user_policy.id),
        metadata={
            "user_policy_id": new_user_policy.id,
            "policy_id": policy_id,
            "policy_number": new_user_policy.policy_number,
            "premium": str(new_user_policy.premium)
        }
    )
    db.commit()
    db.refresh(new_user_policy)

    return {"message": "Policy activated successfully"}


# ===========================
# GET USER POLICIES
# ===========================
@router.get("/", response_model=List[schemas.UserPolicyResponse])
def get_user_policies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    rows = (
        db.query(models.UserPolicies, models.Policy)
        .join(models.Policy, models.UserPolicies.policy_id == models.Policy.id)
        .filter(models.UserPolicies.user_id == current_user.id)
        .all()
    )

    return [
        schemas.UserPolicyResponse(
            id=user_policy.id,
            policy_id=user_policy.policy_id,
            policy_number=user_policy.policy_number,
            start_date=user_policy.start_date,
            end_date=user_policy.end_date,
            premium=user_policy.premium,
            status=user_policy.status,
            auto_renew=user_policy.auto_renew,
            title=policy.title,
            policy_type=policy.policy_type,
            coverage=policy.coverage,
        )
        for user_policy, policy in rows
    ]


# ===========================
# AUTO-RENEW TOGGLE
# ===========================
class AutoRenewRequest(BaseModel):
    auto_renew: bool


@router.put("/{user_policy_id}/auto-renew")
def toggle_auto_renew(
    user_policy_id: int,
    request: AutoRenewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    up = db.query(models.UserPolicies).filter(
        models.UserPolicies.id == user_policy_id,
        models.UserPolicies.user_id == current_user.id
    ).first()

    if not up:
        raise HTTPException(status_code=404, detail="User policy not found")

    old_value = up.auto_renew
    up.auto_renew = request.auto_renew

    write_audit_event(
        db, "POLICY_AUTO_RENEW_TOGGLED", "Policies",
        actor_email=current_user.email, severity="INFO",
        entity_type="UserPolicy", entity_id=str(user_policy_id),
        metadata={
            "user_policy_id": user_policy_id,
            "old_value": old_value,
            "new_value": request.auto_renew
        }
    )
    db.commit()

    return {"message": "Auto-renew updated", "auto_renew": request.auto_renew}