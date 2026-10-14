"""In-memory session/audit boundary; replace with SQLite persistence later."""
from datetime import datetime, timezone
from uuid import uuid4
from .models import AuditEvent, Session

sessions: dict[str, Session] = {}


def record(session: Session, kind: str, detail: str) -> None:
    session.audit.append(AuditEvent(id=str(uuid4()), timestamp=datetime.now(timezone.utc).isoformat(), kind=kind, detail=detail))
