import logging
from threading import Event
import pytest
from app.runtime.timing import timed
from app.runtime.progress import cancellable_call, cancellation, RequestStopped


def test_nested_spans_and_thread_context_are_correlated(caplog):
    caplog.set_level(logging.INFO, logger='uvicorn.error')
    with timed('request.test'), cancellation(Event()):
        def work():
            with timed('provider.test'):
                return 42
        assert cancellable_call(work) == 42
    starts = [r.getMessage() for r in caplog.records if r.getMessage().startswith('timing_start')]
    traces = {line.split('trace=')[1].split()[0] for line in starts}
    assert len(traces) == 1 and len(starts) == 2
    summary = [r.getMessage() for r in caplog.records if r.getMessage().startswith('timing_summary')]
    assert len(summary) == 1 and 'provider.test' in summary[0] and '"calls": 1' in summary[0]
    with timed('request.second'):
        pass
    assert len([r for r in caplog.records if r.getMessage().startswith('timing_summary')]) == 2


@pytest.mark.parametrize('error,status', [(ValueError('SECRET_PROMPT'), 'error'), (RequestStopped('SECRET_PROMPT'), 'cancelled')])
def test_failure_metadata_without_exception_body(caplog, error, status):
    caplog.set_level(logging.INFO, logger='uvicorn.error')
    with pytest.raises(type(error)), timed('request.test'):
        raise error
    assert f'status={status}' in caplog.text
    assert 'SECRET_PROMPT' not in caplog.text
    assert 'elapsed_s=' in caplog.text


def test_monotonic_duration_and_sorted_summary(monkeypatch, caplog):
    from app.runtime import timing
    ticks = iter([0, 1, 3, 4, 9, 10])
    monkeypatch.setattr(timing, 'perf_counter', lambda: next(ticks))
    caplog.set_level(logging.INFO, logger='uvicorn.error')
    with timed('request.test'):
        with timed('short'):
            pass
        with timed('long'):
            pass
    summary = next(r.getMessage() for r in caplog.records if r.getMessage().startswith('timing_summary'))
    assert 'total_s=10.000' in summary
    assert summary.index('long') < summary.index('short')


def test_product_cache_diagnostics_explain_repeated_work(caplog):
    from app.runtime import relevance, risk_agent, shopify_catalog
    from app.runtime.schemas import Session, Fact
    from app.runtime.timing import product_ref
    from test_shopify_catalog import row
    caplog.set_level(logging.INFO, logger='uvicorn.error')
    product, merchant = shopify_catalog.normalize(row())[0]
    product.name = 'PRIVATE_LISTING_TEXT'
    session = Session(mode='mock', search_provider='hybrid')
    with timed('request.test'):
        relevance.inspect(session, product)
        relevance.inspect(session, product)
        session.brief['category'] = Fact(value='PRIVATE_USER_REQUEST')
        relevance.inspect(session, product)
        risk_agent.review(session, product, merchant)
        risk_agent.review(session, product, merchant)
        product.price += 1
        risk_agent.review(session, product, merchant)
    assert 'no_cached_assessment' in caplog.text
    assert 'request_or_product_changed' in caplog.text
    assert 'no_cached_review' in caplog.text and 'product_changed' in caplog.text
    assert '"cache": "hit"' in caplog.text
    assert product_ref(product.id) in caplog.text
    assert 'PRIVATE_LISTING_TEXT' not in caplog.text
    assert 'PRIVATE_USER_REQUEST' not in caplog.text


def test_workflow_diagnostics_include_action_sequence(caplog):
    from app.runtime.shopping_workflow import run_shopping
    from app.runtime.schemas import Session
    caplog.set_level(logging.INFO, logger='uvicorn.error')
    run_shopping(Session(mode='mock', search_provider='catalogue'))
    messages = [r.getMessage() for r in caplog.records]
    assert not any('event=workflow.chosen ' in line for line in messages)
    assert any('event=shortlist.start ' in line for line in messages)
    assert any('event=shortlist.result ' in line for line in messages)
    assert any('"planner_calls": 0' in line for line in messages)
