import json
import httpx
import pytest
from app.runtime import browser_search as browser, service, shopping_tools, cart
from app.runtime.schemas import Session, Fact, CartSelection, CartCheckout
from app.runtime.gateway import LLMError

RUN = "12345678-1234-1234-1234-123456789abc"


def listing(**changes):
    return {"name": "Desk light", "url": "https://shop.example/products/light", "brand": "Example",
            "price": 25, "currency": "SGD", "attributes": ["adjustable"], "sizes": [],
            "description": "Adjustable desk lamp", "in_stock": True, **changes}


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("BROWSER_USE_API_KEY", "test-secret")
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", "shop.example")
    monkeypatch.setenv("BEANY_SEARCH_PROVIDER", "catalogue")
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")


def test_rest_contract_and_no_payment_capabilities(config):
    calls = []
    def handler(req):
        calls.append(req)
        if req.method == "POST":
            return httpx.Response(200, json={"id": RUN})
        return httpx.Response(200, json={"status": "completed", "output": {"products": [listing()]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, result = browser.run_task({"category": "Lighting"}, "", client=client)
    assert result.products[0].price == 25
    body = json.loads(calls[0].content)
    assert set(body) == {"task", "outputSchema", "maxCostUsd", "keepAlive", "agentmail", "browserSettings"}
    assert calls[0].headers["X-Browser-Use-API-Key"] == "test-secret"
    assert str(calls[0].url).endswith("/api/v4/runs")


@pytest.mark.parametrize("url", ["http://shop.example/x", "https://evil.example/x", "https://shop.example@evil.example/x", "https://shop.example:444/x", "javascript:alert(1)"])
def test_source_url_validation(config, url):
    with pytest.raises(ValueError): browser.allowed_url(url, browser.domains())


def test_timeout_requests_cancellation(config, monkeypatch):
    monkeypatch.setenv("BROWSER_USE_TIMEOUT_SECONDS", "10")
    calls = []
    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, json={"id": RUN, "status": "running"})
    times = iter([0, 11])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMError, match="timed out"):
            browser.run_task({}, "", client=client, clock=lambda: next(times))
    assert calls[-1].endswith(f"/{RUN}/cancel")


def test_errors_sanitized_no_retry(config):
    def handler(req): return httpx.Response(401, json={"detail": "test-secret"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMError, match="HTTP 401") as exc:
            browser.run_task({}, "", client=client)
    assert "test-secret" not in str(exc.value)


def test_live_results_use_existing_policy_and_simulated_cart(config, monkeypatch):
    monkeypatch.setattr(browser, "run_task", lambda *_: (RUN, browser.SearchOutput(products=[browser.Listing(**listing())])))
    s = Session(search_provider="browser_use", brief={"category": Fact(value="Lighting"), "budget": Fact(value="30", hard=True)})
    found = shopping_tools.search_products(s)
    assert len(found) == 1 and found[0].source == "browser_use"
    service.propose(s, found[0])
    a = s.proposals[-1]
    assert a.decision == "REVIEW" and a.risk.level == "LOW" and not s.receipts
    chosen = CartSelection(proposal_id=a.id, fingerprint=a.fingerprint)
    cart.add(s, chosen)
    cart.checkout(s, CartCheckout(items=[chosen]))
    assert s.receipts[0].status == "simulated"
    s.brief["budget"] = Fact(value="10", hard=True)
    assert not shopping_tools.search_products(s)


def test_snapshot_expiry_blocks(config, monkeypatch):
    monkeypatch.setattr(browser, "run_task", lambda *_: (RUN, browser.SearchOutput(products=[browser.Listing(**listing())])))
    s = Session(search_provider="browser_use", brief={"category": Fact(value="Lighting")})
    p = shopping_tools.search_products(s)[0]
    p.observed_at = "2000-01-01T00:00:00+00:00"
    service.propose(s, p)
    assert s.proposals[-1].decision == "BLOCK"


def test_default_off_and_research_stays_catalogue(config, monkeypatch):
    assert service.create().search_provider == "catalogue"
    monkeypatch.setenv("BEANY_SEARCH_PROVIDER", "browser_use")
    assert service.create().search_provider == "browser_use"
    assert service.create(search_provider="catalogue").search_provider == "catalogue"


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
    with pytest.raises(LLMError, match="BROWSER_USE_API_KEY"):
        browser.run_task({}, "")


AMAZON = {"url": "https://www.amazon.sg/Brooks-Adrenaline-Supportive-Running-Shoes/dp/B0DM3S2J3J",
          "name": "Brooks Men's Adrenaline GTS 25", "brand": "Brooks", "price": 178.08, "currency": "S",
          "attributes": ["Sole material: Rubber"], "sizes": ["9 US"], "description": "Supportive running shoe.",
          "in_stock": True, "evidence": {
              "seller": {"name": "Amazon US", "page_url": "https://www.amazon.sg/sp?seller=ARPIJN329XQ0D",
                         "business_name": "Amazon Export Sales LLC", "badges": [], "rating": ""},
              "urgency_claims": ["Only 1 left in stock."], "payment_methods": [],
              "return_policy_url": "https://www.amazon.sg/gp/help/customer/display.html/?nodeId=GV38326YW5JX9V9X"}}


def completed(products, monkeypatch, domains="amazon.sg"):
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", domains)
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"id": RUN})
        return httpx.Response(200, json={"status": "completed", "output": {"products": products}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return browser.run_task({"category": "Running shoes"}, "", client=client)[1]


@pytest.mark.parametrize("raw,code", [("S", "SGD"), ("S$", "SGD"), (" sgd ", "SGD"), ("US$", "USD")])
def test_currency_symbols_normalised(raw, code):
    assert browser.Listing.model_validate(listing(currency=raw)).currency == code


def test_bare_dollar_stays_ambiguous():
    assert browser.Listing.model_validate(listing(currency="$")).currency == "$"


def test_real_amazon_output_is_accepted(config, monkeypatch):
    out = completed([AMAZON], monkeypatch)
    row = out.products[0]
    assert row.currency == "SGD" and row.evidence.seller.business_name == "Amazon Export Sales LLC"


def test_invalid_rows_are_skipped_not_fatal(config, monkeypatch):
    bad_currency = {**AMAZON, "currency": "$"}
    off_list = {**AMAZON, "url": "https://evil.example/x"}
    no_price = {**AMAZON, "price": 0}
    out = completed([bad_currency, off_list, no_price, AMAZON], monkeypatch)
    assert len(out.products) == 1 and out.products[0].url == AMAZON["url"]


def test_all_rows_invalid_reports_why(config, monkeypatch):
    with pytest.raises(LLMError, match="none had an SGD/USD price"):
        completed([{**AMAZON, "currency": "JPY"}], monkeypatch)


def test_empty_result_is_not_an_error(config, monkeypatch):
    assert completed([], monkeypatch).products == []


def test_prompt_requests_iso_currency(config, monkeypatch):
    calls = []
    def handler(req):
        calls.append(req)
        if req.method == "POST":
            return httpx.Response(200, json={"id": RUN})
        return httpx.Response(200, json={"status": "completed", "output": {"products": []}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        browser.run_task({}, "", client=client)
    assert "ISO code SGD or USD" in json.loads(calls[0].content)["task"]
