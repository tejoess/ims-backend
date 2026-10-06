import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schemas import LoginRequest
from models import User
from database import get_db
from hashing import Verify
from jwt_token import create_access_token

router = APIRouter()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    is_valid = Verify.verify_password(request.password, user.password)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

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