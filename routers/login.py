import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schemas import LoginRequest
from models import User
from database import get_db
from hashing import Verify
from jwt_token import create_access_token
from oauth2 import get_current_user
import models
from audit_helper import write_audit_event

router = APIRouter()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Write audit event and commit BEFORE raising exception
        write_audit_event(
            db, "USER_LOGIN_FAILURE", "Authentication",
            actor_email=request.email, severity="WARNING",
            metadata={
                "attempted_email": request.email,
                "failure_reason": "user_not_found"
            }
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    is_valid = Verify.verify_password(request.password, user.password)

    if not is_valid:
        # Write audit event and commit BEFORE raising exception
        write_audit_event(
            db, "USER_LOGIN_FAILURE", "Authentication",
            actor_email=request.email, severity="WARNING",
            metadata={
                "attempted_email": request.email,
                "failure_reason": "invalid_password"
            }
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Write success audit event before returning
    write_audit_event(
        db, "USER_LOGIN_SUCCESS", "Authentication",
        actor_email=user.email, severity="INFO",
        entity_type="User", entity_id=str(user.id),
        metadata={"user_id": user.id, "email": user.email}
    )
    db.commit()

    access_token = create_access_token(data={"sub": user.email})

    # ✅ Role flag without changing DB schema
    is_admin = user.email == ADMIN_EMAIL

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "is_admin": is_admin
    }


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    write_audit_event(
        db, "USER_LOGOUT", "Authentication",
        actor_email=current_user.email, severity="INFO",
        entity_type="User", entity_id=str(current_user.id),
        metadata={"user_id": current_user.id}
    )
    db.commit()
    return {"message": "Logged out successfully"}