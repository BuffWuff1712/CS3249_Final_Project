import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .agent import MockShoppingAgent
from .explanations import explain
from .models import ChatRequest, DecisionRequest, Message, Preferences, Proposal, Session
from .policy import evaluate
from .store import sessions, record

app = FastAPI(title='Beany Shopping Prototype', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:3000')], allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])
agent = MockShoppingAgent()


def get_session(sid: str) -> Session:
    if sid not in sessions:
        raise HTTPException(404, 'Session not found. Start a new demo.')
    return sessions[sid]


def recheck(s: Session, p: Proposal) -> None:
    p.violations = evaluate(p, s.preferences)
    p.explanation = explain(p)


@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'fictional-demo'}


@app.post('/sessions', response_model=Session)
def create_session():
    s = Session(id=str(uuid4()), messages=[Message(role='assistant', text='Hi, I’m Beany, your shopping copilot. This demo compares fictional headphones. Tell me what matters to you, set your boundaries, then choose a scenario to explore. What are you shopping for?')])
    sessions[s.id] = s
    record(s, 'session', 'Demo session created. No real shopping services connected.')
    return s


@app.get('/sessions/{sid}', response_model=Session)
def read_session(sid: str):
    return get_session(sid)


@app.put('/sessions/{sid}/preferences', response_model=Session)
def update_preferences(sid: str, preferences: Preferences):
    s = get_session(sid)
    old = s.preferences.model_dump()
    s.preferences = preferences
    record(s, 'preferences', f'Boundaries updated: {old} → {preferences.model_dump()}')
    for p in s.proposals:
        if p.status == 'pending':
            recheck(s, p)
            record(s, 'policy', f'{p.id}: re-evaluated after boundary update: {p.violations or "within boundaries"}')
    return s


@app.post('/sessions/{sid}/messages', response_model=Session)
def chat(sid: str, request: ChatRequest):
    s = get_session(sid)
    if not request.text.strip():
        raise HTTPException(422, 'Please enter a message.')
    s.messages.append(Message(role='user', text=request.text.strip()))
    for previous in s.proposals:
        if previous.status == 'pending':
            previous.status = 'superseded'
            record(s, 'proposal', f'{previous.id}: superseded by a new request')
    p = Proposal(id=str(uuid4()), product=agent.propose(request.scenario))
    recheck(s, p)
    s.proposals.append(p)
    s.activity = ['Searched 4 fictional catalogue products', 'Compared price, merchant and product type', 'Checked your current permissions', 'Waiting for your review']
    record(s, 'proposal', f'{p.id}: proposed {p.product.name} using scenario {request.scenario}')
    record(s, 'policy', '; '.join(p.violations) or 'All current boundaries satisfied')
    s.messages.append(Message(role='assistant', text=f'For the {request.scenario} demo scenario, I selected {p.product.name}. ' + p.explanation + ' Your message is recorded for this conversation; this scripted demo does not interpret arbitrary shopping requests.'))
    return s


@app.post('/sessions/{sid}/proposals/{pid}/decision', response_model=Session)
def decide(sid: str, pid: str, request: DecisionRequest):
    s = get_session(sid)
    p = next((p for p in s.proposals if p.id == pid), None)
    if p is None:
        raise HTTPException(404, 'Proposal not found')
    if p.status != 'pending':
        raise HTTPException(409, 'This proposal has already been resolved or superseded.')
    recheck(s, p)
    if request.action == 'approve' and p.violations:
        record(s, 'blocked', 'Approval blocked by current policy')
        raise HTTPException(409, 'Update your boundaries or refine this proposal before approving.')
    if request.action == 'refine':
        if not request.note.strip():
            raise HTTPException(422, 'Tell the agent what to refine.')
        p.status = 'superseded'
        s.messages.append(Message(role='user', text='Refine: ' + request.note.strip()))
        s.messages.append(Message(role='assistant', text='Refinement recorded. Update your boundaries or choose another demo scenario and send a new request. The scripted agent does not interpret free-text refinements.'))
    else:
        p.status = 'approved' if request.action == 'approve' else 'rejected'
        s.messages.append(Message(role='assistant', text='Simulated approval recorded. No order or payment was created.' if request.action == 'approve' else 'Proposal rejected. Choose another scenario or refine your request.'))
    record(s, 'decision', f'{pid}: {request.action}. {request.note}')
    s.activity = ['Review response recorded', 'No real checkout or transaction performed']
    return s


@app.delete('/sessions/{sid}', status_code=204)
def reset(sid: str):
    get_session(sid)
    del sessions[sid]
