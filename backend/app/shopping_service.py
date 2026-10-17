"""Learning scaffold: connect existing sessions to the shopping graph.

Not connected to HTTP routes yet. Complete start_request one TODO at a time.
"""
from threading import Lock
from typing import Literal, TypedDict
from uuid import uuid4

from .checkout import CheckoutState, ReceiptStore
from .intent import ShoppingIntent
from .models import Message, Session
from .store import record, sessions
from .workflow import build_workflow
from .review import fingerprint


class ActiveRun(TypedDict):
    """Where to find the current shopping request for a conversation."""
    thread_id: str
    proposal_id: str | None
    status: Literal['no_match', 'blocked', 'waiting_review', 'completed', 'rejected']


# Shared means these objects are created once when Python imports this module.
# Every start/resume call uses the same graph so paused runs are not forgotten.
receipt_store = ReceiptStore()
graph = build_workflow(receipt_store)
active_runs: dict[str, ActiveRun] = {}

# A lock makes simultaneous requests for the same session take turns.
# The short registry lock prevents two callers creating different session locks.
_session_locks: dict[str, Lock] = {}
_registry_lock = Lock()


def _get_session_lock(session_id: str):
    with _registry_lock:
        if session_id not in _session_locks:
            _session_locks[session_id] = Lock()
        return _session_locks[session_id]


def start_request(session_id: str, text: str, intent: ShoppingIntent) -> Session:
    """Start one shopping request and eventually return its updated Session."""
    with _get_session_lock(session_id):
        curr_sess = sessions.get(session_id)
        if curr_sess is None:
            raise LookupError(f'Session not found: {session_id}')
        clean_text = text.strip()
        if not clean_text:
            raise ValueError('Please enter a shopping request')
        if len(clean_text) > 2000:
            raise ValueError('Shopping request must not exceed 2000 characters')

        # Work on a COPY. If anything below fails, the stored session is intact.
        working_session = curr_sess.model_copy(deep=True)
        working_session.messages.append(Message(role='user', text=clean_text))

        # You already chose uuid4 correctly. Each shopping request gets a new ID.
        thread_id = str(uuid4())
        config = {'configurable': {'thread_id': thread_id}}
        initial_state: CheckoutState = {
            'intent': intent.model_copy(deep=True),
            'preferences': working_session.preferences.model_copy(deep=True),
            'candidates': [], 'proposal': None, 'violations': [], 'outcome': '',
            'decision': None, 'action_fingerprint': None,
            'receipt': None, 'checkout_error': None,
        }


        result = graph.invoke(initial_state, config=config)
        proposal = result['proposal']
        status = ''
        reply = ''

        if proposal is None:
            status = 'no_match'
            reply = result['outcome']
        elif result['violations']:
            status = 'blocked'
            reply = result['outcome']
        elif result.get('__interrupt__'):
            status = 'waiting_review'
            reply = f"Please review {proposal.product.name} and approve or reject the proposal. No checkout has occurred."
        else:
             raise RuntimeError('Unexpected graph result')


        for old_proposal in working_session.proposals:
            if old_proposal.status == 'pending':
                old_proposal.status = 'superseded'
                record(
                    working_session,
                    "superseded",
                    f"Proposal {old_proposal.id} replaced by request {thread_id}",
                )

        # proposal is the NEW graph result; old_proposal belongs only to the loop.
        if proposal is not None:
            new_proposal = proposal.model_copy(deep=True)
            new_proposal.explanation = reply
            working_session.proposals.append(new_proposal)

        working_session.messages.append(Message(role='assistant', text=reply))
        working_session.activity = [
            f"Searched the fictional catalogue: {len(result['candidates'])} matches",
        ]

        if proposal is not None:
            working_session.activity.append('Checked saved shopping permissions')
        activity_result = {
            'waiting_review': 'Waiting for your review; no checkout has occurred',
            'blocked': 'Proposal blocked by your shopping permissions',
            'no_match': 'No matching products; no proposal evaluated',
        }

        working_session.activity.append(activity_result[status])
        record(
            working_session,
            'request',
            f"Request {thread_id}: {clean_text}",
        )

        if proposal is not None:
            record(
                working_session,
                'proposal',
                f"Request {thread_id}: proposed {proposal.id} ({proposal.product.name})",
            )
            policy_detail = '; '.join(result['violations']) or 'Saved shopping permissions satisfied; awaiting user review'
            record(working_session, 'policy', f"Request {thread_id}, proposal {proposal.id}: {policy_detail}")
        else:
            record(working_session, 'policy', f"Request {thread_id}: no matches; no proposal evaluated")
       
       
        if proposal is not None:
            active_run = ActiveRun(thread_id=thread_id, proposal_id=proposal.id, status=status)
        else:
            active_run = ActiveRun(thread_id=thread_id, proposal_id=None, status=status)

        sessions[session_id] = working_session
        active_runs[session_id] = active_run

        return working_session

def respond_to_proposal(session_id: str, proposal_id: str, action: str) -> Session:
    """Resume this session's current proposal with approve or reject.

    Browser supplies only the proposal ID/action. The server supplies the thread
    ID and fingerprint. This function must not create a new graph or thread.
    """

    with _get_session_lock(session_id):
        curr_sess = sessions.get(session_id)
        if curr_sess is None: 
            raise LookupError(f'Session not found: {session_id}')
        if action not in ("approve", "reject"):
            raise ValueError(f"Action {action} is not recognised.")


        run = active_runs.get(session_id)

        if run is None or run['proposal_id'] != proposal_id:
            raise ValueError('Run not found')

        session_proposal = None
        for target in curr_sess.proposals:
            if target.id == run['proposal_id']:
                session_proposal = target
                break

        if session_proposal is None:
            raise ValueError("Proposal not found in session")

        if session_proposal.status == "superseded":
            raise ValueError("This proposal was replaced by a newer request")
        

        config = {'configurable': {'thread_id': run['thread_id']}}
        snapshot = graph.get_state(config) 
        values = snapshot.values         
        proposal = values.get('proposal')

        if proposal is None:
            raise ValueError("No proposal found in the saved workflow")
        if proposal.id != proposal_id:
            raise ValueError("Proposal does not match the saved workflow")
        if fingerprint(proposal) != fingerprint(session_proposal):
            raise ValueError("The displayed proposal differs from the saved action")

        # Detect a finished run without executing the graph a second time.
        saved_decision = values.get("decision")
        receipt = values.get("receipt")
        already_finished = False
        result = None

        completed_approval = (
            saved_decision is not None
            and saved_decision.action == 'approve'
            and proposal.status == 'approved'
            and receipt is not None
        )
        completed_rejection = (
            saved_decision is not None
            and saved_decision.action == 'reject'
            and proposal.status == 'rejected'
            and receipt is None
        )

        if completed_approval or completed_rejection:
            current_fingerprint = fingerprint(proposal)
            if (
                saved_decision.proposal_id != proposal.id
                or saved_decision.action_fingerprint != current_fingerprint
                or values.get('action_fingerprint') != current_fingerprint
            ):
                raise ValueError('Saved decision does not match this proposal')
            if action != saved_decision.action:
                raise ValueError('Cannot change a decision after the request has finished')
            if completed_approval and (
                receipt.proposal_id != proposal.id
                or receipt.action_fingerprint != current_fingerprint
            ):
                raise ValueError('Saved receipt does not match this proposal')
            if snapshot.next:
                raise RuntimeError('Workflow still has unfinished steps')

            finished_status = 'completed' if completed_approval else 'rejected'
            if run['status'] == finished_status and session_proposal.status == proposal.status:
                # A normal retry: no new graph execution, message or audit event.
                return curr_sess

            # Recovery: graph finished but the session was not saved yet.
            # TODO 7 must publish this result without resuming the graph again.
            already_finished = True
            result = values
        elif saved_decision is not None or receipt is not None or proposal.status in ('approved', 'rejected'):
            # Partial/inconsistent completion is not permission to run checkout.
            raise RuntimeError('Workflow has an incomplete or inconsistent saved decision')


        # TODO 5: For a NEW decision, verify there is actually a review to resume.
        # Put TODOs 5 AND 6 inside: if not already_finished:
        # For recovery, result was set above and must go directly to TODO 7.
        # Require run['status'] == 'waiting_review' and both proposals pending.
        # snapshot.next should contain 'human_review'. Check that at least one
        # task in snapshot.tasks has nonempty task.interrupts; otherwise raise.
        # Build resume_data with these exact keys:
        # 'proposal_id': proposal.id,
        # 'action_fingerprint': values['action_fingerprint'],
        # 'action': action.
        # The graph will validate the fingerprint/decision again. Do not auto-approve.

        # TODO 6: Supply current permissions, then resume the SAME graph/config.
        # graph.update_state(config,
        #     {'preferences': curr_sess.preferences.model_copy(deep=True)},
        #     as_node='prepare_review')
        # This schedules human_review, not search; the proposal must stay unchanged.
        # Import Command from langgraph.types, then:
        # result = graph.invoke(Command(resume=resume_data), config=config)
        # Do not catch exceptions and report success. No input() calls here.
        # Skip TODOs 5-6 entirely for the completed-run reconciliation in TODO 4.

        # TODO 7: Turn result into an updated Session, like start_request TODO 3.
        # working_session = curr_sess.model_copy(deep=True)
        # Replace the matching item in working_session.proposals with a deep copy
        # of result['proposal']; set its explanation to result['outcome'].
        # REPLACE by ID, don't append a duplicate proposal.
        # Append one assistant Message containing result['outcome']; update activity.
        # record() the user decision and final policy result with proposal/thread IDs.
        # If result['receipt'] exists, also audit its ID and simulated amount/currency.
        # Never describe a blocked/rejected outcome as a purchase.
        # Session has no receipt field yet: full receipt remains in the checkpoint;
        # a typed frontend receipt field will be a separate integration task.

        # TODO 8: Publish result and return, still inside the lock.
        # Determine new run status using result:
        # receipt exists -> 'completed'; rejected proposal -> 'rejected';
        # policy violations -> 'blocked'; unexpected combination -> RuntimeError.
        # Save working_session to sessions[session_id]. Replace active_runs entry
        # using SAME thread_id/proposal_id with the updated status. Return Session.
        # Do not add new messages/audit on a later identical completed retry.
        raise NotImplementedError('Complete respond_to_proposal TODOs 5-8')


def update_preferences(session_id, preferences):
    raise NotImplementedError('Later: synchronize saved preferences and graph state')


def reset_session(session_id):
    raise NotImplementedError('Later: clear the session, owned checkpoints and receipts')
