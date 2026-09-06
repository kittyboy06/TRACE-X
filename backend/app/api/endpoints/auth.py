from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any

from app.core.security import (
    DEMO_USERS,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    analyst_id: str
    username: str


@router.post("/token", response_model=TokenResponse)
def login_for_access_token(credentials: LoginRequest):
    """
    Authenticates threat intelligence analysts against verified credentials.
    Rejects invalid username or password with 401 Unauthorized (no universal fallback).
    """
    user_record = DEMO_USERS.get(credentials.username.strip())
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user_record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user_record["username"],
        role=user_record["role"],
        analyst_id=user_record["analyst_id"]
    )
    return TokenResponse(
        access_token=token,
        role=user_record["role"],
        analyst_id=user_record["analyst_id"],
        username=user_record["username"]
    )


@router.get("/me")
def read_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the authenticated analyst profile and active permissions.
    """
    return {
        "status": "AUTHENTICATED",
        "username": current_user.get("sub"),
        "role": current_user.get("role"),
        "analyst_id": current_user.get("analyst_id")
    }


class SSETicketRequest(BaseModel):
    investigation_id: str


class SSETicketResponse(BaseModel):
    ticket: str
    expires_in: int = 60
    investigation_id: str


@router.post("/sse-ticket", response_model=SSETicketResponse)
def request_sse_ticket(
    req: SSETicketRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Any = Depends(lambda: next(__import__("app.models.database", fromlist=["get_db"]).get_db()))
):
    """
    Issues an ephemeral single-use ticket (60-second TTL) for streaming pipeline progress.
    Avoids transmitting long-lived JWTs in EventSource URLs or access logs.
    """
    from app.core.security import authorize_investigation_access
    from app.services.sse_ticket_service import SSETicketService

    # Enforce investigation authorization (404 if missing, 403 if unauthorized)
    authorize_investigation_access(req.investigation_id, current_user, db)

    ticket = SSETicketService.create_ticket(
        investigation_id=req.investigation_id,
        analyst_id=current_user.get("analyst_id", "ANALYST-001"),
        role=current_user.get("role", "CTI_ANALYST"),
        ttl_seconds=60
    )

    return SSETicketResponse(
        ticket=ticket.ticket_id,
        expires_in=60,
        investigation_id=req.investigation_id
    )
