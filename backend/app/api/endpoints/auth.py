from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    analyst_id: str


@router.post("/token", response_model=TokenResponse)
def login_for_access_token(credentials: LoginRequest):
    # SIH Demo mock authentication
    if credentials.username in ["analyst", "lead_auditor", "ntro_evaluator"] and credentials.password in ["tracex2026", "admin", "analyst"]:
        analyst_id = f"ANALYST-{credentials.username.upper()[:4]}-01"
        token = create_access_token(subject=analyst_id)
        role = "LEAD_AUDITOR" if "auditor" in credentials.username else "CTI_ANALYST"
        return TokenResponse(access_token=token, role=role, analyst_id=analyst_id)
        
    # Default fallback for demo simplicity
    token = create_access_token(subject="ANALYST-DEMO-01")
    return TokenResponse(access_token=token, role="CTI_ANALYST", analyst_id="ANALYST-DEMO-01")
