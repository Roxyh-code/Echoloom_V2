import time
from copy import deepcopy

import pytest

from echoloom.db import RehearsalOperation, sessions
from echoloom.providers import ProviderError
from echoloom import rehearsal_service as service
from test_rehearsal import create, quick, command, wait


def live(setup):
    c, text, *_ = setup
    s = create(c, False, character_ids=[quick(c, 'Lin'), quick(c, 'Xu')])
    return c, text, s


def settled(c, jid):
    for _ in range(250):
        if jid not in c.app.state.rehearsal_running:
            return
        time.sleep(.01)
    pytest.fail('Worker did not exit')


def count(text):
    return sum(kind == 'rehearsal' for kind, _ in text.calls)


def retry(c, jid):
    r = c.post('/api/rehearsal/jobs/' + jid + '/retry', json={})
    assert r.status_code == 200, r.text
    return wait(c, r.json())


def test_resume_pending_generation(setup):
    c, text, s = live(setup)
    text.fail = True
    failed = wait(c, command(c, s, 'continue'))
    assert failed['status'] == 'failed'
    settled(c, failed['id'])
    text.fail = False
    done = retry(c, failed['id'])
    assert done['status'] == 'completed'
    assert count(text) == 2
    with sessions(setup[-1])() as db:
        old = db.get(RehearsalOperation, failed['id'])
        new = db.get(RehearsalOperation, done['id'])
        assert old.result['checkpoint_thread_id'] == new.result['checkpoint_thread_id']
        assert new.result['checkpoint_mode'] == 'resumed'


def fail_after_graph(monkeypatch):
    original = service.validate_performance
    calls = 0
    def validate(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderError('Simulated failure after graph completed')
        return original(*args)
    monkeypatch.setattr(service, 'validate_performance', validate)


def test_completed_checkpoint_does_not_call_model_again(setup, monkeypatch):
    c, text, s = live(setup)
    fail_after_graph(monkeypatch)
    failed = wait(c, command(c, s, 'continue'))
    assert failed['status'] == 'failed'
    settled(c, failed['id'])
    done = retry(c, failed['id'])
    assert done['status'] == 'completed'
    assert count(text) == 1
    assert len(done['scene']['document']['nodes']) == 1
    again = c.post('/api/rehearsal/jobs/' + failed['id'] + '/retry', json={})
    assert again.json()['job_id'] == done['id']


def test_changed_scene_does_not_reuse_old_output(setup, monkeypatch):
    c, text, s = live(setup)
    fail_after_graph(monkeypatch)
    failed = wait(c, command(c, s, 'continue'))
    settled(c, failed['id'])
    current = failed['scene']
    new_setup = deepcopy(current['document']['setup'])
    new_setup['goal'] = 'The actors must leave separately.'
    command(c, current, 'setup', setup=new_setup)
    done = retry(c, failed['id'])
    assert done['status'] == 'completed'
    assert count(text) == 2


def test_retry_waits_for_old_worker(setup):
    c, text, s = live(setup)
    text.fail = True
    failed = wait(c, command(c, s, 'continue'))
    settled(c, failed['id'])
    c.app.state.rehearsal_running.add(failed['id'])
    try:
        r = c.post('/api/rehearsal/jobs/' + failed['id'] + '/retry', json={})
        assert r.status_code == 409
    finally:
        c.app.state.rehearsal_running.discard(failed['id'])


def test_partial_commit_uses_continuation_not_original_output(setup, monkeypatch):
    c, text, s = live(setup)
    # Inject a one-off failure during the second block commit, after the first
    # block and its event have committed in the same DB transaction.
    from echoloom.db import RehearsalScene
    from sqlalchemy import event
    writes = 0
    def break_second(mapper, connection, target):
        nonlocal writes
        nodes = list(target.document['nodes'].values())
        if nodes and len(nodes[-1]['blocks']) == 2 and writes == 0:
            writes += 1
            raise RuntimeError('Simulated second block failure')
    event.listen(RehearsalScene, 'before_update', break_second)
    try:
        failed = wait(c, command(c, s, 'continue'))
    finally:
        event.remove(RehearsalScene, 'before_update', break_second)
    assert failed['status'] == 'failed'
    settled(c, failed['id'])
    done = retry(c, failed['id'])
    assert done['status'] == 'completed'
    assert count(text) == 2
    with sessions(setup[-1])() as db:
        old = db.get(RehearsalOperation, failed['id'])
        new = db.get(RehearsalOperation, done['id'])
        assert old.result['checkpoint_thread_id'] != new.result['checkpoint_thread_id']
        assert new.result['generation']['kind'] == 'continue'
    nodes = list(done['scene']['document']['nodes'].values())
    assert len(nodes[0]['blocks']) == 1
    assert len(nodes) == 2
