from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User
from schemas import RiskProfileRequest
from oauth2 import get_current_user
from audit_helper import write_audit_event

router = APIRouter()


@router.post("/users/{user_id}/risk-profile")
def save_risk_profile(
    user_id: int,
    request: RiskProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # ✅ FIXED TYPE
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🔐 ACCESS CHECK (FIXED)
    if user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this profile"
        )

    # Capture old risk level before update
    old_risk = (user.risk_profile or {}).get("risk_level")

    # 🔥 AUTO CALCULATE RISK LEVEL
    if (
        request.age > 50 or
        request.dependents >= 3 or
        request.health_condition.lower() == "critical"
    ):
        calculated_risk = "high"
    else:
        calculated_risk = "low"

    # Save everything including calculated risk
    user.risk_profile = {
        "age": request.age,
        "annual_income": request.annual_income,
        "dependents": request.dependents,
        "health_condition": request.health_condition,
        "risk_level": calculated_risk
    }

    # Write audit event before commit
    write_audit_event(
        db, "RISK_PROFILE_UPDATED", "User Profile",
        actor_email=current_user.email, severity="INFO",
        entity_type="User", entity_id=str(user_id),
        metadata={
            "user_id": user_id,
            "old_risk_level": old_risk,
            "new_risk_level": calculated_risk,
            "changed_fields": list(request.model_fields.keys())
        }
    )
    db.commit()

    return {
        "message": "Risk profile saved successfully",
        "calculated_risk": calculated_risk
    }


@router.get("/users/{user_id}/risk-profile")
def get_risk_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # ✅ FIXED TYPE
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🔐 ACCESS CHECK (FIXED)
    if user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this profile"
        )

    return {
        "risk_profile": user.risk_profile
    }


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.put("/users/{user_id}/password")
def change_password(
    user_id: int,
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized")

    from hashing import Verify, Hash
    if not Verify.verify_password(request.current_password, user.password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    user.password = Hash.hash_password(request.new_password)

    write_audit_event(
        db, "PASSWORD_CHANGED", "Authentication",
        actor_email=current_user.email, severity="WARNING",
        entity_type="User", entity_id=str(user_id),
        metadata={"user_id": user_id}
    )
    db.commit()

    return {"message": "Password changed successfully"}