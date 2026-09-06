from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

ALGORITHM = "HS256"
security_scheme = HTTPBearer(auto_error=False)

# Pre-hashed credentials for NTRO / SIH demonstration
# analyst: tracex2026
# lead_auditor: auditor2026
# ntro_evaluator: ntro2026
DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "analyst": {
        "username": "analyst",
        "password_hash": "$2b$10$aU8rJcRo6OmcV/CvlNbdputEFZGcDTOAEMlK.NU8YBk0jio6WZJRW",
        "role": "CTI_ANALYST",
        "analyst_id": "ANALYST-001",
        "full_name": "Senior CTI Analyst"
    },
    "lead_auditor": {
        "username": "lead_auditor",
        "password_hash": "$2b$10$KcPkMkA1PIDwjmkNGAI3b.gSVyOF09MdYZ6vYRClnVHdlE.NUYRpK",
        "role": "LEAD_AUDITOR",
        "analyst_id": "AUDITOR-001",
        "full_name": "Lead Audit Supervisor"
    },
    "ntro_evaluator": {
        "username": "ntro_evaluator",
        "password_hash": "$2b$10$.KxOrK4vCgdMfkJEiZDfLeiPTfbvZ9xIU/1vZ8T9nnUvo7xCDZfk.",
        "role": "LEAD_AUDITOR",
        "analyst_id": "NTRO-EVAL-01",
        "full_name": "NTRO Technical Evaluator"
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")


def create_access_token(
    subject: str,
    role: str = "CTI_ANALYST",
    analyst_id: str = "ANALYST-001",
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "analyst_id": analyst_id
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def require_role(*allowed_roles: str):
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "CTI_ANALYST")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {allowed_roles} (current role: {user_role})"
            )
        return current_user
    return role_checker


def authorize_investigation_access(
    investigation_id: str,
    current_user: Dict[str, Any],
    db: Any
) -> Any:
    """
    Enforces investigation-scoped authorization:
    - 404 if investigation does not exist.
    - LEAD_AUDITOR is authorized for all investigations.
    - CTI_ANALYST is authorized if assigned_analyst_id matches their analyst_id (or if unassigned/default).
    - 403 Forbidden if analyst is not assigned to the investigation.
    """
    from app.models.database import InvestigationModel
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found."
        )

    user_role = current_user.get("role", "CTI_ANALYST")
    analyst_id = current_user.get("analyst_id")

    if user_role == "LEAD_AUDITOR":
        return inv

    if user_role == "CTI_ANALYST":
        if inv.assigned_analyst_id and inv.assigned_analyst_id != analyst_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Analyst '{analyst_id}' is not authorized for investigation '{investigation_id}'."
            )
        return inv

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: Insufficient investigation permissions."
    )
