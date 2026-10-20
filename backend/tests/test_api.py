import pytest
from fastapi.testclient import TestClient
from app.legacy_main import app
from app.models import Preferences, Proposal
from app.agent import CATALOGUE
from app.policy import evaluate

client = TestClient(app)


def session():
    return client.post('/sessions').json()


def propose(s, scenario='normal'):
    return client.post(f'/sessions/{s["id"]}/messages', json={'text': 'Find headphones', 'scenario': scenario}).json()


@pytest.mark.parametrize('scenario,violation', [('normal', None), ('budget', 'Budget'), ('substitution', 'Substitution'), ('merchant', 'Merchant')])
def test_scenarios(scenario, violation):
    s = propose(session(), scenario)
    p = s['proposals'][-1]
    assert (any(violation in v for v in p['violations']) if violation else not p['violations'])
    result = client.post(f'/sessions/{s["id"]}/proposals/{p["id"]}/decision', json={'action': 'approve'})
    assert result.status_code == (409 if violation else 200)


def test_preferences_rechecked_and_duplicate_decisions_blocked():
    s = propose(session())
    p = s['proposals'][-1]
    prefs = s['preferences'] | {'budget': 50}
    updated = client.put(f'/sessions/{s["id"]}/preferences', json=prefs).json()
    assert updated['proposals'][-1]['violations']
    url = f'/sessions/{s["id"]}/proposals/{p["id"]}/decision'
    assert client.post(url, json={'action': 'approve'}).status_code == 409
    assert client.post(url, json={'action': 'reject'}).status_code == 200
    assert client.post(url, json={'action': 'approve'}).status_code == 409


def test_refine_supersede_and_reset():
    s = propose(session(), 'budget')
    pid = s['proposals'][-1]['id']
    url = f'/sessions/{s["id"]}/proposals/{pid}/decision'
    assert client.post(url, json={'action': 'refine'}).status_code == 422
    refined = client.post(url, json={'action': 'refine', 'note': 'cheaper please'}).json()
    assert refined['proposals'][-1]['status'] == 'superseded'
    assert refined['audit'][-1]['kind'] == 'decision'
    assert client.delete(f'/sessions/{s["id"]}').status_code == 204
    assert client.get(f'/sessions/{s["id"]}').status_code == 404


def test_isolation_and_superseding():
    a, b = session(), session()
    a = propose(a)
    old_pid = a['proposals'][-1]['id']
    a = propose(a, 'budget')
    assert a['proposals'][0]['status'] == 'superseded'
    assert not client.get(f'/sessions/{b["id"]}').json()['proposals']
    assert client.post(f'/sessions/{a["id"]}/proposals/{old_pid}/decision', json={'action': 'approve'}).status_code == 409


def test_currency_payment_privacy_and_validation():
    p = Proposal(id='test', product=CATALOGUE[0], shares_personal_data=True)
    reasons = evaluate(p, Preferences(currency='USD', payment_methods=[]))
    assert all(any(key in reason for reason in reasons) for key in ['Currency', 'Payment', 'Privacy'])
    s = session()
    assert client.put(f'/sessions/{s["id"]}/preferences', json=s['preferences'] | {'budget': -1}).status_code == 422
    assert client.post(f'/sessions/{s["id"]}/messages', json={'text': '   '}).status_code == 422
    assert client.post(f'/sessions/{s["id"]}/messages', json={'text': 'test', 'scenario': 'unknown'}).status_code == 422
