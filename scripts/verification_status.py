"""Read-only presentation of repo-signal's validated changed-file evidence."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

ACTIONS = {
    'PASS': 'Review remaining release requirements; changed-file evidence is not a release approval.',
    'FAIL': 'Inspect failed checks in mq-agent before verifying again.',
    'STALE': 'Review the verification plan and verify the changed files again.',
    'NOT_VERIFIED': 'Review mq-agent verification scope and existing evidence.',
}


def unverified(reason: str = 'not_requested') -> dict[str, str]:
    return {'status': 'NOT_VERIFIED', 'source': 'repo-signal doctor --verification --json',
            'scope': 'changed_files_against_HEAD', 'reason': reason,
            'next_action': ACTIONS['NOT_VERIFIED']}


def collect(path: Path, *, enabled: bool = False) -> dict[str, str]:
    result = unverified()
    if not enabled:
        return result
    if not path.is_dir():
        return unverified('repo_unavailable')
    try:
        with tempfile.TemporaryFile() as output:
            proc = subprocess.run(
                ['repo-signal', 'doctor', str(path.expanduser().resolve()), '--verification', '--json'],
                stdout=output, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                timeout=35, check=False,
            )
            output.seek(0)
            raw = output.read(65537)
        if proc.returncode != 0 or len(raw) > 65536:
            return unverified('provider_unavailable')
        payload = json.loads(raw)
    except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError):
        return unverified('provider_unavailable')
    if not isinstance(payload, dict) or payload.get('schema') != 'doctor.v1':
        return unverified('invalid_response')
    verification = payload.get('verification')
    if not isinstance(verification, dict):
        return unverified('verification_unavailable')
    status = verification.get('status')
    if (not isinstance(status, str) or status not in ACTIONS or verification.get('source') != 'mq-agent'
            or verification.get('scope') != 'changed_files_against_HEAD'):
        return unverified('invalid_response')
    if status == 'PASS':
        if verification.get('code_status') != 'PASS' or any(
            not isinstance(verification.get(key), str)
            or not re.fullmatch(r'[0-9a-f]{64}', verification[key])
            for key in ('receipt_id', 'fingerprint')
        ):
            return unverified('invalid_response')
    # Never echo provider prose, paths or raw evidence into HAL output.
    return {**result, 'status': status, 'reason': 'reported_by_repo_signal',
            'next_action': ACTIONS[status]}


def summary(items: dict[str, dict[str, Any]]) -> str:
    statuses = [item.get('status', 'NOT_VERIFIED') for item in items.values()]
    for status in ['FAIL', 'STALE', 'NOT_VERIFIED']:
        if status in statuses:
            return status
    return 'PASS' if statuses and all(s == 'PASS' for s in statuses) else 'NOT_VERIFIED'


def render(items: dict[str, dict[str, Any]]) -> None:
    print('Changed-file verification (separate from structural/runtime status)')
    print('-----------------------------------------------------------------')
    for name, item in items.items():
        print(f"{name}: {item['status']} — {item['next_action']}")
    print(f'Verification summary: {summary(items)}')
    print('Not a full-suite, CI or release-approval verdict.')
