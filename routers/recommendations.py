from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, Policy, Recommendation
from oauth2 import get_current_user
from audit_helper import write_audit_event

router = APIRouter()


@router.get("/users/{user_id}/recommendations")
def get_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # ✅ FIXED TYPE
):

    # 1️⃣ Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2️⃣ Auth check (FIXED)
    if user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # 3️⃣ Risk profile check
    if not user.risk_profile:
        raise HTTPException(status_code=400, detail="Risk profile not set")

    risk = user.risk_profile
    annual_income = risk.get("annual_income", 0)
    dependents = risk.get("dependents", 0)
    age = risk.get("age", 0)
    health_condition = risk.get("health_condition", "normal")

    # 🔥 AUTO CALCULATE RISK LEVEL
    if age > 50 or dependents >= 3 or health_condition.lower() == "critical":
        risk_level = "high"
    else:
        risk_level = "low"

    # 5️⃣ Fetch all policies
    policies = db.query(Policy).all()

    # Delete old recommendations
    db.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).delete()

    recommendations = []

    for policy in policies:
        score = 0
        reasons = []

        # Affordability
        if policy.premium <= annual_income * 0.05:
            score += 25
            reasons.append("Affordable based on your income")

        # Risk logic
        if risk_level == "high" and policy.deductible < 5000:
            score += 20
            reasons.append("Low deductible suits high risk profile")

        if risk_level == "low" and policy.deductible >= 5000:
            score += 15
            reasons.append("Higher deductible suits low risk profile")

        # Dependents
        if dependents >= 2:
            score += 10
            reasons.append("Suitable for family coverage")

        # Bonus
        if policy.deductible < 3000:
            score += 5
            reasons.append("Low deductible bonus")

        premium_score = max(0, 40 - int(policy.premium / 1000))
        score += premium_score

        reason_text = ", ".join(reasons) if reasons else "Basic eligibility match"

        new_recommendation = Recommendation(
            user_id=user_id,
            policy_id=policy.id,
            score=score,
            reason=reason_text,
            created_at=datetime.utcnow()
        )

        db.add(new_recommendation)

        recommendations.append({
            "id": policy.id,
            "title": policy.title,
            "policy_type": policy.policy_type,
            "premium": policy.premium,
            "deductible": policy.deductible,
            "score": score,
            "reason": reason_text
        })

    # Sort recommendations before writing audit event
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    # Write audit event before commit
    write_audit_event(
        db, "RECOMMENDATIONS_GENERATED", "Recommendations",
        actor_email=current_user.email, severity="INFO",
        entity_type="User", entity_id=str(user_id),
        metadata={
            "user_id": user_id,
            "risk_level": risk_level,
            "count_returned": len(recommendations[:5])
        }
    )
    db.commit()

    return {
        "risk_level": risk_level,
        "annual_income": annual_income,
        "top_recommendations": recommendations[:5]
    }