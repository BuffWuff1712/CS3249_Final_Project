"""Validated edits; conversation is evidence, never permission."""
LIST_FIELDS = {"features", "preferred_brands", "excluded_brands", "merchants"}


def task_start(session):
    if session.task_start_message is not None:
        return session.task_start_message
    # Legacy sessions with resets have no reliable message boundary: do not guess.
    return len(session.messages) if any(e.kind == "brief_reset" for e in session.events) else 0


def grounded_change(session, change, text, allow_history=True):
    evidence = change.evidence.strip()
    if not evidence:
        return False
    if change.evidence_message_index is None:
        return evidence.casefold() in text.casefold()
    index = change.evidence_message_index
    return bool(allow_history and change.field == "category" and "category" not in session.brief
                and task_start(session) <= index < len(session.messages)
                and session.messages[index].role == "user"
                and evidence.casefold() in session.messages[index].text.casefold())


def apply_change(old, change, fact):
    if change.operation == "set":
        return fact
    if change.field not in LIST_FIELDS:
        raise ValueError("Add/remove operations require a list preference")
    if change.source != "confirmed":
        return old  # Suggested edits cannot remove or extend confirmed requirements.
    parts = lambda value: [v.strip() for v in value.split(",") if v.strip()]
    existing = parts(old.value) if old else []
    incoming = parts(change.value or "")
    if change.operation == "remove":
        values = [v for v in existing if v.casefold() not in {x.casefold() for x in incoming}]
    else:
        values = list(existing)
        for v in incoming:
            if v.casefold() not in {x.casefold() for x in values}:
                values.append(v)
    if not values:
        return None
    from .schemas import Fact
    return Fact(value=", ".join(values), source="confirmed", hard=change.hard or bool(old and old.hard))
