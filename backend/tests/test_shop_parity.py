"""Independent offline parity checks for the replacement participant UI."""
import copy
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.runtime import shop_workspace as shop, service, storage, browser_search, shopping_tools, risk_agent
from app.runtime.schemas import Fact
client = TestClient(app)


def fresh():
    r = client.post('/shop/sessions')
    assert r.status_code == 200, r.text
    return r.json()


def change(v, path, body=None, method='POST', status=200):
    r = client.request(method, f"/shop/sessions/{v['session']['id']}/{path}", json={'revision': v['revision'], **(body or {})})
    assert r.status_code == status, r.text[:1500]
    return r.json()


def offer(v=None, product='study-hp-target-trusted'):
    v = change(v or fresh(), 'messages', {'text': 'Find headphones under SGD200'})
    return change(v, 'propose', {'product_id': product})


def chosen(v):
    a = v['current']
    return {'proposal_id': a['id'], 'fingerprint': a['fingerprint']}


def test_configured_provider_and_replay_not_overridden(monkeypatch):
    monkeypatch.setenv('BEANY_SEARCH_PROVIDER', 'browser_use')
    monkeypatch.setenv('BROWSER_USE_REPLAY', 'data/replay/study_listings.json')
    monkeypatch.setattr(browser_search, 'run_task', lambda *_: pytest.fail('Creation must not search'))
    v = fresh()
    assert v['session']['search_provider'] == 'browser_use'
    assert v['session']['search_replay'] == 'data/replay/study_listings.json'
    assert not v['offers'] and 'replays saved' in v['session']['messages'][0]['text']


def test_adoption_preserves_classic_and_research_state_and_is_idempotent():
    s = service.create(search_provider='catalogue')
    s.scenario_id = 'independent-scenario'
    s.experiment['private_truth'] = {'hidden_label': 'must stay private'}
    s.brief = {'category': Fact(value='Headphones'), 'budget': Fact(value='200', hard=True)}
    storage.save(s)
    original = s.model_dump()
    r = client.post(f'/shop/sessions/{s.id}/adopt')
    assert r.status_code == 200, r.text
    saved = storage.load(s.id)
    for field in ('brief', 'permissions', 'messages', 'receipts', 'search_provider', 'scenario_id'):
        assert saved.model_dump()[field] == original[field]
    assert saved.experiment['private_truth'] == original['experiment']['private_truth']
    assert 'private_truth' not in str(r.json()) and 'hidden_label' not in str(r.json())
    again = client.post(f'/shop/sessions/{s.id}/adopt')
    assert again.status_code == 200 and again.json()['revision'] == r.json()['revision']


def test_explicit_cart_survives_needs_cancel_and_refresh():
    v = offer(); selection = chosen(v)
    v = change(v, 'cart', selection)
    assert v['current'] is None and v['selected'] is None
    assert len(v['cart_review']) == 1 and not v['cart_review'][0]['error']
    brief = copy.deepcopy(v['session']['cart'][0]['brief'])
    v = change(v, 'brief', {'field': 'budget', 'fact': {'value': '10', 'hard': True, 'source': 'confirmed'}}, method='PUT')
    v = change(v, 'cancel')
    assert len(v['session']['cart']) == 1 and v['session']['cart'][0]['brief'] == brief
    assert not v['cart_review'][0]['error']
    restored = client.get(f"/shop/sessions/{v['session']['id']}").json()
    assert restored['session']['cart'] == v['session']['cart']
    v = change(restored, 'cart/checkout', {'items': [selection]})
    assert len(v['session']['receipts']) == 1 and not v['session']['cart']


def test_permissions_clear_selection_and_saved_cart_uses_current_permissions():
    v = offer(); selection = chosen(v)
    v = change(v, 'cart', selection)
    p = copy.deepcopy(v['session']['permissions'])
    p['restricted_merchants'] = [v['session']['cart'][0]['action']['product']['merchant']]
    v = change(v, 'permissions', {'permissions': p}, method='PUT')
    assert v['current'] is None and v['selected'] is None and len(v['session']['cart']) == 1
    assert v['cart_review'][0]['error']
    before = storage.load(v['session']['id']).model_dump_json()
    change(v, 'cart/checkout', {'items': [selection]}, status=409)
    assert storage.load(v['session']['id']).model_dump_json() == before


def test_explicit_reject_and_cancel_boundaries():
    v = offer(); first = chosen(v)
    change(v, 'reject', first | {'fingerprint': 'tampered'}, status=409)
    v = change(v, 'reject', first)
    assert v['current'] is None and v['session']['stage'] == 'rejected' and not v['session']['receipts']
    v = change(v, 'alternative')
    assert v['current'] and v['current']['product']['merchant_id'] != 'study-m-trusted'
    second = chosen(v)
    v = change(v, 'select', second)
    v = change(v, 'cancel')
    assert v['selected'] is None and v['current'] is None and v['session']['stage'] == 'cancelled'
    change(v, 'finish', second, status=409)


def test_multi_item_checkout_atomic_and_idempotent():
    v = offer(); one = chosen(v)
    v = change(v, 'cart', one)
    v = offer(v, product='study-hp-target-neutral'); two = chosen(v)
    v = change(v, 'cart', two)
    assert len(v['session']['cart']) == 2
    change(v, 'cart/checkout', {'items': [one, two | {'fingerprint': 'bad'}]}, status=409)
    restored = client.get(f"/shop/sessions/{v['session']['id']}").json()
    assert len(restored['session']['cart']) == 2 and not restored['session']['receipts']
    v = change(v, 'cart/checkout', {'items': [one, two]})
    assert len(v['session']['receipts']) == 2 and not v['session']['cart']
    v = change(v, 'cart/checkout', {'items': [one, two]})
    assert len(v['session']['receipts']) == 2


def test_soft_budget_and_revision_bound_cart_removal():
    v = offer()
    v = change(v, 'brief', {'field': 'budget', 'fact': {'value': '100', 'hard': False, 'source': 'confirmed'}}, method='PUT')
    assert not v['session']['brief']['budget']['hard']
    v = change(v, 'compare')
    assert any(row['product']['price'] > 100 for row in v['offers'])
    v = change(v, 'propose', {'product_id': 'study-hp-target-trusted'}); selection = chosen(v)
    v = change(v, 'cart', selection); old = copy.deepcopy(v)
    v = change(v, 'cart/' + selection['proposal_id'], method='DELETE')
    assert not v['session']['cart']
    change(old, 'cancel', status=409)


def test_live_preview_uses_captured_merchants_without_provider_calls(monkeypatch):
    monkeypatch.setenv('BROWSER_USE_ALLOWED_DOMAINS', 'shop.example')
    s = service.create(search_provider='browser_use'); shop.adopt(s)
    s.brief = {'category': Fact(value='Lighting'), 'budget': Fact(value='30', hard=True)}
    listing = browser_search.Listing(name='Desk light', url='https://shop.example/products/light', brand='Example', price=25, currency='SGD', attributes=['adjustable'], sizes=[], description='Desk light', in_stock=True)
    monkeypatch.setattr(browser_search, 'run_task', lambda *_: ('offline-run', browser_search.SearchOutput(products=[listing])))
    s.recommendations = shopping_tools.search_products(s); service.propose(s, s.recommendations[0])
    monkeypatch.setattr(browser_search, 'run_task', lambda *_: pytest.fail('GET must never search'))
    monkeypatch.setattr(risk_agent, 'review', lambda *_: pytest.fail('GET must never invoke risk model'))
    before = s.model_dump_json(); v = shop.view(s)
    assert len(v['offers']) == 1 and v['offers'][0]['merchant']['id'] in s.live_merchants
    assert v['offers'][0]['product']['source_url'] == listing.url
    assert 'fingerprint' not in v['offers'][0] and s.model_dump_json() == before


def test_adopted_study_keeps_authorized_research_controls_and_revision(monkeypatch):
    from app.main import scenarios
    monkeypatch.setenv('BEANY_RESEARCH_KEY', 'offline-review-key')
    headers = {'X-Research-Key': 'offline-review-key'}
    spec = next(row for row in scenarios() if row.get('trigger_product'))
    r = client.post(f"/research/scenarios/{spec['id']}/sessions", json={}, headers=headers)
    assert r.status_code == 200, r.text
    sid = r.json()['id']
    v = client.post(f'/shop/sessions/{sid}/adopt').json()
    assert client.put(f'/research/sessions/{sid}/configuration', json={'profile_id': 'standard'}).status_code == 403
    r = client.put(f'/research/sessions/{sid}/configuration', json={'profile_id': 'standard'}, headers=headers)
    assert r.status_code == 200, r.text
    after = client.get(f'/shop/sessions/{sid}').json()
    assert after['revision'] > v['revision']
    r = client.post(f'/research/sessions/{sid}/trigger', headers=headers)
    assert r.status_code == 200, r.text
    pid = r.json()['proposals'][-1]['id']
    r = client.put(f'/research/sessions/{sid}/observation', json={'proposal_id': pid, 'understood': True}, headers=headers)
    assert r.status_code == 200, r.text
    exposed = client.get(f'/shop/sessions/{sid}').json()
    assert 'observations' not in str(exposed) and 'ground_truth' not in str(exposed)
    assert client.post(f'/sessions/{sid}/cancel').status_code == 409


def test_saved_browser_replay_runs_real_facade_search_and_checkout_without_network(monkeypatch):
    monkeypatch.setenv('BEANY_SEARCH_PROVIDER', 'browser_use')
    monkeypatch.setenv('BROWSER_USE_REPLAY', 'data/replay/study_listings.json')
    monkeypatch.setattr(browser_search, 'run_task', lambda *_: pytest.fail('Replay must never invoke live provider'))
    v = change(fresh(), 'messages', {'text': 'Find headphones under SGD200'})
    assert v['current'] and v['offers']
    assert all(row['product']['source'] == 'browser_use' for row in v['offers'])
    assert all(row['product']['id'].startswith('web-') for row in v['offers'])
    assert all('source_url' in row['product'] for row in v['offers'])
    allowed = next(row for row in v['offers'] if row['decision'] != 'BLOCK')
    v = change(v, 'propose', {'product_id': allowed['product']['id']})
    selection = chosen(v)
    v = change(v, 'cart', selection)
    v = change(v, 'cart/checkout', {'items': [selection]})
    assert len(v['session']['receipts']) == 1 and not v['session']['cart']


def test_classic_cart_adoption_does_not_reclassify_saved_item_as_ephemeral_selection():
    s = service.create(search_provider='catalogue')
    service.chat(s, 'Find headphones under SGD200')
    from app.runtime.cart import add
    from app.runtime.schemas import CartSelection
    a = s.proposals[-1]
    add(s, CartSelection(proposal_id=a.id, fingerprint=a.fingerprint))
    storage.save(s)
    r = client.post(f'/shop/sessions/{s.id}/adopt')
    assert r.status_code == 200, r.text
    v = r.json()
    assert v['current'] is None, 'An already-saved classic cart offer must not become an ephemeral selection'
    v = change(v, 'brief', {'field': 'budget', 'fact': {'value': '10', 'hard': True, 'source': 'confirmed'}}, method='PUT')
    assert len(v['session']['cart']) == 1 and not v['cart_review'][0]['error']


def test_blocked_current_offer_can_be_rejected_but_never_selected():
    from app.runtime import policy
    s = shop.create()
    s.brief = {'category': Fact(value='Headphones'), 'budget': Fact(value='200', hard=True)}
    p = next(p for p in policy.catalogue(s) if p.id == 'study-hp-target-external')
    service.propose(s, p)
    storage.save(s)
    v = client.get(f'/shop/sessions/{s.id}').json()
    assert v['current']['decision'] == 'BLOCK' and v['current_error']
    selection = chosen(v)
    change(v, 'select', selection, status=409)
    v = change(v, 'reject', selection)
    assert v['current'] is None and not v['session']['receipts']
