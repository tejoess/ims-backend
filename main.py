from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import SignupRequest
from hashing import Hash
from audit_helper import write_audit_event

# ✅ Import routers
from routers import (
    policies,
    login,
    risk_profile,
    recommendations,
    claims,
    userpolicies,
    admin  # ✅ NEW
)

app = FastAPI(
    title="Edme Insurance API",
    description="Insurance Comparison, Recommendation & Claim Assistant",
    version="1.0.0"
)

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include Routers
app.include_router(policies.router)
app.include_router(login.router)
app.include_router(risk_profile.router)
app.include_router(recommendations.router)
app.include_router(claims.router)
app.include_router(userpolicies.router)
app.include_router(admin.router)  # ✅ NEW


# ---------------------------------
# SIGNUP ROUTE
# ---------------------------------
@app.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        return {"message": "Email already registered"}

    hashed_password = Hash.hash_password(request.password)

    new_user = User(
        name=request.name,
        email=request.email,
        password=hashed_password,
        dob=request.dob
    )

    db.add(new_user)
    db.flush()  # Get new_user.id without committing

    # Write USER_REGISTERED audit event
    write_audit_event(
        db, "USER_REGISTERED", "User Profile",
        actor_email=new_user.email, severity="INFO",
        entity_type="User", entity_id=str(new_user.id),
        metadata={"user_id": new_user.id, "email": new_user.email}
    )
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Signup successful",
        "user_id": new_user.id,
        "email": new_user.email
    }