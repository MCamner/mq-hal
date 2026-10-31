import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ci_status
import brief
import repo_status_json


def run(workflow, sha='head', conclusion='success', run_id=2):
    return dict(workflowName=workflow, workflowDatabaseId=1, headSha=sha,
                status='completed', conclusion=conclusion, databaseId=run_id,
                event='push', createdAt=f'2026-10-{run_id:02d}T00:00:00Z')


def build(runs):
    def fake(command, cwd):
        if command[0] == 'git':
            return 0, 'head', ''
        assert command[command.index('--commit') + 1] == 'head'
        return 0, json.dumps(runs), ''
    with patch.object(ci_status, 'run_cmd', side_effect=fake):
        return ci_status.build_ci('repo', Path('.'), 5)


def test_old_commit_excluded():
    data = build([run('Tests'), run('Tests', sha='old', conclusion='failure')])
    assert data['status'] == 'green'
    assert len(data['runs']) == 1


def test_latest_rerun_wins():
    data = build([run('Tests', conclusion='failure', run_id=1), run('Tests')])
    assert data['status'] == 'green'
    assert len(data['runs']) == 1


def test_no_runs_is_unknown():
    assert build([])['status'] == 'unknown'


def test_pending_and_failure():
    pending = run('Tests', conclusion='')
    pending['status'] = 'queued'
    assert build([pending])['status'] == 'running'
    assert build([run('Tests', conclusion='failure')])['status'] == 'red'


def test_missing_head_does_not_query_gh():
    with patch.object(ci_status, 'run_cmd', return_value=(1, '', 'no HEAD')) as cmd:
        assert ci_status.build_ci('repo', Path('.'), 5)['status'] == 'unknown'
    assert cmd.call_count == 1


def test_brief_uses_same_head_status():
    with patch.object(ci_status, 'run_cmd', side_effect=[(0, 'head', ''), (0, '[]', '')]):
        data = brief.collect_ci(Path('.'))
    assert data['status'] == 'unknown'
    assert data['head_sha'] == 'head'


def test_empty_stderr_has_exit_code():
    from subprocess import CompletedProcess
    with patch.object(repo_status_json.subprocess, 'run', return_value=CompletedProcess([], 7, '', '')):
        assert '7' in repo_status_json.repo_signal_json('inspect', Path('.'))['error']


def test_retry_on_same_run_uses_latest_attempt():
    old = run('Tests', conclusion='failure')
    old.update(attempt=1, startedAt='2026-10-01T00:00:00Z')
    new = run('Tests')
    new.update(attempt=2, startedAt='2026-10-02T00:00:00Z')
    assert build([old, new])['status'] == 'green'


def test_events_remain_separate():
    push = run('Tests', conclusion='failure')
    pr = run('Tests')
    pr['event'] = 'pull_request'
    data = build([push, pr])
    assert data['status'] == 'red'
    assert len(data['runs']) == 2


def test_invalid_response_is_unknown():
    with patch.object(ci_status, 'run_cmd', side_effect=[(0, 'head', ''), (0, '{}', '')]):
        assert ci_status.build_ci('repo', Path('.'), 5)['status'] == 'unknown'


def test_queued_new_run_supersedes_old_failure():
    old = run('Tests', conclusion='failure', run_id=1)
    old['startedAt'] = '2026-10-01T00:00:00Z'
    new = run('Tests', conclusion='', run_id=2)
    new.update(status='queued', startedAt='0001-01-01T00:00:00Z')
    assert build([old, new])['status'] == 'running'
