from sqlalchemy.orm import Session
from typing import Optional
import models


def write_audit_event(
    db:          Session,
    event_name:  str,
    category:    str,
    actor_email: str,
    severity:    str,
    entity_type: Optional[str] = None,
    entity_id:   Optional[str] = None,
    metadata:    Optional[dict] = None,
) -> None:
    """
    Write an audit event to the audit_logs table.

    IMPORTANT: This function does NOT commit the transaction.
    The caller is responsible for calling db.commit().
    """
    db.add(models.AuditLog(
        event_name=event_name,
        category=category,
        actor_email=actor_email,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    ))
    # Caller must call db.commit() — this function never commits.
