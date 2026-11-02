import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_brief


def check(gh, commits=(0, '3', '')):
    def fake(command, cwd, timeout=60):
        if command[0] == 'gh':
            assert command[:4] == ['gh', 'release', 'view', 'v2.3.1']
            return gh
        assert command[:3] == ['git', 'rev-list', '--count']
        assert command[3] == 'v2.3.1..HEAD'
        return commits
    with patch.object(release_brief, 'run', side_effect=fake):
        return release_brief.check_latest_release(Path('.'), 'v2.3.1', skip_gh=False)


def test_published_target_blocks_and_counts_commits():
    result = check((0, '{"tagName": "v2.3.1"}', ''))
    assert result['status'] == 'fail'
    assert 'already published' in result['message']
    assert '3 commit(s) since v2.3.1' in result['message']


def test_published_without_commit_count_still_blocks():
    result = check((0, '{"tagName": "v2.3.1"}', ''), commits=(128, '', 'bad'))
    assert result['status'] == 'fail'
    assert 'commit(s)' not in result['message']


def test_unpublished_target_is_ok():
    result = check((1, '', 'release not found'))
    assert result['status'] == 'ok'
    assert 'not yet published' in result['message']


def test_gh_error_is_warn_not_verdict():
    result = check((1, '', 'HTTP 401: Bad credentials'))
    assert result['status'] == 'warn'


def test_published_target_makes_overall_blocked():
    with patch.object(release_brief, 'run', side_effect=lambda c, cwd, timeout=60: (
            (0, '{"tagName": "v2.3.1"}', '') if c[0] == 'gh' else (0, '0', ''))):
        result = release_brief.check_latest_release(Path('.'), 'v2.3.1', skip_gh=False)
    assert release_brief.overall_status([result]) == 'blocked'
