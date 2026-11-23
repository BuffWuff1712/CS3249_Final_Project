"""Track questions separately from shopping facts; uncertainty is not permission."""
FIELDS = {"product_type": "category", "budget": "budget", "features": "features"}


# INNOVATION: One-shot validation feedback for ungrounded extractions. Instead of
# silently accepting a hallucinated preference (as other chat agents do), Beany sends
# the extraction back to the model once with the grounding issue stated; if it still
# cannot cite the user, the preference is discarded, never saved as confirmed.
def extraction_issues(session, result, text):
    if result.intent not in ("search", "new_task", "clarify", "alternative"):
        return []
    issues = []
    available = set() if result.intent == "new_task" else set(session.brief)
    for change in result.changes:
        from .preferences import grounded_change
        grounded = grounded_change(session, change, text, allow_history=result.intent != "new_task")
        if change.source == "confirmed" and not grounded:
            issues.append(f"{change.field}: evidence is not a literal quote from the latest message.")
        elif change.value is not None:
            available.add(change.field)
    if "category" not in available:
        issues.append("Extract the stated product family as category even when asking about its subtype. Recover from an indexed current-task user message if needed.")
    for answer in result.clarification_answers:
        if answer.status == "provided" and FIELDS[answer.field] not in available:
            issues.append(f"{answer.field}: marked provided but the corresponding preference was not saved or extracted.")
    return issues


def resume_uncertainty(session, result, text):
    """A short answer to a pending question is not unrelated small talk."""
    import re
    from .schemas import ClarificationAnswer
    if not session.search_requested or session.stage != "clarifying" or result.intent not in ("respond", "clarify", "search"):
        return
    if re.fullmatch(r"\s*(?:(?:i['’]?m|i am)\s+)?(?:unsure|not sure|(?:i\s+)?don['’]?t know|no preference)[.!?\s]*", text, re.I):
        missing = [f for f in session.clarification_asked if session.clarification_answers.get(f) not in ("provided", "unknown")]
        if missing:
            result.intent = "search"
            from .preferences import grounded_change
            # A repaired missing family may survive; uncertainty cannot erase requirements.
            result.changes = [c for c in result.changes if c.field == "category"
                              and "category" not in session.brief and c.value is not None
                              and grounded_change(session, c, text)]
            result.clarification_answers = [ClarificationAnswer(field=f, status="unknown", evidence=text) for f in missing]


# INNOVATION: Conversation is evidence, not permission. Other chat agents search as
# soon as the brief looks complete and treat any "not sure" as answering something.
# Beany tracks asked/answered state separately from the brief: a search runs only on
# explicit user request with the asked fields resolved, and "not sure" only clears
# a question that was actually asked.
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
    # The type is asked once. A reply that still names none ("any shoes") searches the stated
    # family; the narrower catalogue category stays suggested, never confirmed.
    elif session.clarification_answers.get("product_type") == "missing" and "product_type" in session.clarification_asked:
        session.clarification_answers["product_type"] = "unknown"
    missing = [field for field in FIELDS if session.clarification_answers.get(field) not in ("provided", "unknown")]
    if not missing:
        return None
    session.clarification_asked = list(dict.fromkeys([*session.clarification_asked, *missing]))
    questions = {
        "product_type": "what type of " + session.brief["category"].value + " you want" if "category" in session.brief else "what type of product you want",
        "budget": "your budget",
        "features": "any features that matter to you",
    }
    # One grouped clarification lets users answer all three or explicitly skip any.
    return "I can help narrow it down! Tell me " + ", ".join(questions[f] for f in missing) + ". It's fine to say you're unsure or have no preference for any of these."
