from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
import random

import models
import schemas
from database import get_db
from oauth2 import get_current_user

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