import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from dataclasses import dataclass
from fastapi import HTTPException, status


@dataclass
class SSETicket:
    ticket_id: str
    investigation_id: str
    analyst_id: str
    role: str
    expires_at: datetime
    used: bool = False


class SSETicketService:
    """
    Process-local, concurrency-safe ephemeral single-use ticket service for SSE connections.
    Avoids transmitting long-lived JWTs in URLs or query strings.
    """
    _tickets: Dict[str, SSETicket] = {}
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def create_ticket(
        cls,
        investigation_id: str,
        analyst_id: str,
        role: str,
        ttl_seconds: int = 60
    ) -> SSETicket:
        ticket_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        ticket = SSETicket(
            ticket_id=ticket_id,
            investigation_id=investigation_id,
            analyst_id=analyst_id,
            role=role,
            expires_at=expires_at,
            used=False
        )
        cls._tickets[ticket_id] = ticket
        return ticket

    @classmethod
    async def consume_ticket(cls, ticket_id: str, expected_investigation_id: str) -> SSETicket:
        """
        Atomically validates and consumes an ephemeral ticket under an asyncio.Lock.
        - Raises 401 if missing, expired, or already consumed.
        - Raises 403 if investigation mismatch.
        - Immediately marks used = True.
        """
        async with cls._lock:
            ticket = cls._tickets.get(ticket_id)
            if not ticket:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid SSE ticket: Ticket does not exist."
                )

            now = datetime.now(timezone.utc)
            if now > ticket.expires_at:
                # Clean up expired ticket
                cls._tickets.pop(ticket_id, None)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid SSE ticket: Ticket has expired."
                )

            if ticket.used:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid SSE ticket: Ticket has already been consumed."
                )

            # Ticket is valid and unconsumed; now verify investigation scoping
            if ticket.investigation_id != expected_investigation_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: Ticket is scoped to investigation '{ticket.investigation_id}', not '{expected_investigation_id}'."
                )

            # Consume ticket atomically
            ticket.used = True
            return ticket

    @classmethod
    def clear_all(cls):
        """Testing utility to reset in-memory ticket cache."""
        cls._tickets.clear()
