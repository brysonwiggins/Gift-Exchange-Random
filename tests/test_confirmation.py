import importlib.util
import os
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def santa(tmp_path, monkeypatch):
    """Loads santa-helper-program.py with Gmail sending stubbed out."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(ROOT)
    spec = importlib.util.spec_from_file_location('santa_program', os.path.join(ROOT, 'santa-helper-program.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    (tmp_path / 'list.txt').write_text('Alice, a@x.com\r\nBob, b@x.com\r\nCarol, c@x.com')
    (tmp_path / 'history.csv').write_text('2025,Alice,Bob\n')
    module.listFile = 'list.txt'
    module.historyFile = 'history.csv'
    module.siteUrl = 'https://santa.example.com'
    module.dbFile = str(tmp_path / 'santa.db')

    sent = []
    monkeypatch.setattr(module.Mail, 'get_credentials', lambda self: None)
    monkeypatch.setattr(module.Mail, 'send', lambda self, email, body, subject=None: sent.append((email, subject, body)))
    yield module, sent, tmp_path
    module.debug.close()


def run(module, monkeypatch, command, answer):
    module.confirmation = True
    # The script keeps the list in module globals and normally runs once per process
    module.names.clear()
    module.emails.clear()
    monkeypatch.setattr('builtins.input', lambda prompt: answer)
    module.main(SimpleNamespace(command=command))


def test_draw_abort_sends_nothing_and_keeps_history(santa, monkeypatch, capsys):
    module, sent, tmp_path = santa
    run(module, monkeypatch, 'draw', 'n')
    assert sent == []
    assert (tmp_path / 'history.csv').read_text() == '2025,Alice,Bob\n'
    out = capsys.readouterr().out
    assert 'Draw results:' in out
    assert 'Aborted' in out


def test_draw_confirm_sends_what_was_shown_and_records_history(santa, monkeypatch, capsys):
    module, sent, tmp_path = santa
    run(module, monkeypatch, 'draw', 'y')
    out = capsys.readouterr().out
    assert len(sent) == 3
    for email, subject, body in sent:
        assert body in out
        assert 'https://santa.example.com/ideas/' in body
    history = (tmp_path / 'history.csv').read_text().splitlines()
    assert len(history) == 4


def test_invite_abort_and_confirm(santa, monkeypatch):
    module, sent, tmp_path = santa
    run(module, monkeypatch, 'invite', '')
    assert sent == []
    run(module, monkeypatch, 'invite', 'yes')
    assert [email for email, subject, body in sent] == ['a@x.com', 'b@x.com', 'c@x.com']
    assert all('/edit/' in body for email, subject, body in sent)


def test_without_confirmation_sends_immediately(santa, monkeypatch):
    module, sent, tmp_path = santa
    module.confirmation = False
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('should not prompt'))
    module.main(SimpleNamespace(command='draw'))
    assert len(sent) == 3
