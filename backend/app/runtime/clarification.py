"""Track questions separately from shopping facts; uncertainty is not permission."""
FIELDS = {"product_type": "category", "budget": "budget", "features": "features"}


def extraction_issues(session, result, text):
    if result.intent not in ("search", "new_task", "clarify", "alternative"):
        return []
    issues = []
    available = set() if result.intent == "new_task" else set(session.brief)
    for change in result.changes:
        grounded = bool(change.evidence.strip()) and change.evidence.casefold() in text.casefold()
        if change.source == "confirmed" and not grounded:
            issues.append(f"{change.field}: evidence is not a literal quote from the latest message.")
        elif change.value is not None:
            available.add(change.field)
    for answer in result.clarification_answers:
        if answer.status == "provided" and FIELDS[answer.field] not in available:
            issues.append(f"{answer.field}: marked provided but the corresponding preference was not saved or extracted.")
    return issues


def resume_uncertainty(session, result, text):
    """A short answer to a pending question is not unrelated small talk."""
    import re
    from .schemas import ClarificationAnswer
    if session.stage != "clarifying" or result.intent not in ("respond", "clarify", "search"):
        return
    if re.fullmatch(r"\s*(?:(?:i['’]?m|i am)\s+)?(?:unsure|not sure|(?:i\s+)?don['’]?t know|no preference)[.!?\s]*", text, re.I):
        missing = [f for f in session.clarification_asked if session.clarification_answers.get(f) not in ("provided", "unknown")]
        if missing:
            result.intent = "search"
            result.changes = []  # Uncertainty cannot erase a stated requirement.
            result.clarification_answers = [ClarificationAnswer(field=f, status="unknown", evidence=text) for f in missing]


def clarify_before_search(session, result, text):
    for field, brief_key in FIELDS.items():
        fact = session.brief.get(brief_key)
        if not fact and session.clarification_answers.get(field) == "provided":
            session.clarification_answers.pop(field, None)
        if fact and fact.source == "confirmed" and session.clarification_answers.get(field) != "missing":
            session.clarification_answers[field] = "provided"
    for answer in result.clarification_answers:
        if answer.status == "missing":
            # Missing is significant for a broad category inferred from 'shoes'.
            if answer.field == "product_type" and answer.field not in session.clarification_asked:
                session.clarification_answers[answer.field] = "missing"
            continue
        if not answer.evidence.strip() or answer.evidence.casefold() not in text.casefold():
            continue
        explicit_opt_out = any(phrase in answer.evidence.casefold() for phrase in ("no preference", "no feature preference", "no budget", "no particular features"))
        if answer.status == "provided" and not session.brief.get(FIELDS[answer.field]):
            continue
        if answer.status == "provided" or answer.field in session.clarification_asked or explicit_opt_out:
            session.clarification_answers[answer.field] = answer.status
    # An answer flag is not a usable search category, especially in older saved sessions.
    if not session.brief.get("category"):
        session.clarification_answers.pop("product_type", None)
    missing = [field for field in FIELDS if session.clarification_answers.get(field) not in ("provided", "unknown")]
    if not missing:
        return None
    session.clarification_asked = list(dict.fromkeys([*session.clarification_asked, *missing]))
    questions = {
        "product_type": "what type of product you want (for example, running or hiking shoes if you're looking for shoes)",
        "budget": "your budget",
        "features": "any features that matter to you",
    }
    # One grouped clarification lets users answer all three or explicitly skip any.
    return "I can help narrow it down! Tell me " + ", ".join(questions[f] for f in missing) + ". It's fine to say you're unsure or have no preference for any of these."
