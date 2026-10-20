import pytest
pytest.importorskip('langgraph', reason='Optional legacy learning exercises')

from app.run_workflow import main


@pytest.mark.parametrize('action,status', [('approve', 'approved'), ('reject', 'rejected')])
def test_runner_records_decision(monkeypatch, capsys, action, status):
    monkeypatch.setattr('builtins.input', lambda _: action)
    main(['--allow-market-lane'])
    output = capsys.readouterr().out
    assert f'Proposal status: {status}' in output
    if action == 'approve':
        assert '"status": "simulated"' in output
        assert '"amount": 79.0' in output
    else:
        assert 'Receipt: None' in output


@pytest.mark.parametrize('args,message', [([], 'is blocked:'), (['--maximum-price', '50'], 'No matching products found.')])
def test_runner_finishes_without_prompt_when_blocked_or_empty(monkeypatch, capsys, args, message):
    def unexpected_prompt(_):
        pytest.fail('Blocked or empty search must not request approval')
    monkeypatch.setattr('builtins.input', unexpected_prompt)
    main(args)
    assert message in capsys.readouterr().out


def test_runner_retries_invalid_input_and_normalizes_answer(monkeypatch, capsys):
    answers = iter(['invalid', ' APPROVE '])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    main(['--allow-market-lane'])
    output = capsys.readouterr().out
    assert 'Please type approve or reject.' in output
    assert 'Proposal status: approved' in output


@pytest.mark.parametrize('exception', [EOFError, KeyboardInterrupt])
def test_runner_cancellation_does_not_checkout(monkeypatch, capsys, exception):
    def cancel(_):
        raise exception
    monkeypatch.setattr('builtins.input', cancel)
    main(['--allow-market-lane'])
    output = capsys.readouterr().out
    assert 'Cancelled.' in output
    assert 'Simulated checkout completed' not in output


def test_runner_rejects_negative_maximum_price():
    with pytest.raises(SystemExit) as error:
        main(['--maximum-price', '-1'])
    assert error.value.code == 2
