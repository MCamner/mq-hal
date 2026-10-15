#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT" <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as temp:
    env = dict(os.environ, MQ_HAL_STATE_DIR=temp)
    def run(data, *args):
        return subprocess.run([str(root / 'bin/mq-hal'), 'workflow-receipt', *args], input=json.dumps(data), text=True, capture_output=True, env=env)
    receipt = {'schema': 'mq.workflow-receipt.v1', 'run_id': 'run-1', 'status': 'partial', 'ok': False, 'execution_run_id': 'exec-42', 'fallback': 'local-only', 'steps': [{'id': 'test', 'status': 'pending'}], 'completeness': {'planned': 2, 'completed': 1, 'coverage': None, 'status': 'partial'}, 'verification': {'status': 'unknown'}, 'recording': {'observation': 'failed'}}
    result = run(receipt)
    assert result.returncode == 0, result.stderr
    assert 'Execution run: exec-42' in result.stdout
    assert 'Fallback: local-only' in result.stdout
    assert 'Status: partial' in result.stdout
    assert 'Coverage: unknown' in result.stdout
    assert 'Verification: unknown' in result.stdout
    assert 'observation: failed' in result.stdout
    assert 'HAL writes: none' in result.stdout
    unknown = run({'schema': 'mq.workflow-receipt.v1', 'ok': None})
    assert 'Status: unknown' in unknown.stdout and 'OK: unknown' in unknown.stdout
    result = run(receipt, '--json')
    assert json.loads(result.stdout) == receipt
    receipt.update(status='completed', ok=True, completeness={'planned': 1, 'completed': 1, 'coverage': 1.0, 'status': 'complete'}, verification={'status': 'passed'})
    result = run(receipt, '--json')
    assert json.loads(result.stdout) == receipt  # no verdict recomputation
    path = Path(temp) / 'receipt.json'
    path.write_text(json.dumps(receipt))
    result = subprocess.run([str(root / 'bin/mq-hal'), 'workflow-receipt', str(path), '--json'], text=True, capture_output=True, env=env)
    assert json.loads(result.stdout) == receipt
    for malformed in ([], {'schema': 'other'}, {'schema': 'mq.workflow-receipt.v1', 'status': {}}, {'schema': 'mq.workflow-receipt.v1', 'steps': 'bad'}, {'schema': 'mq.workflow-receipt.v1', 'ok': 'yes'}, {'schema': 'mq.workflow-receipt.v1', 'recording': []}, {'schema': 'mq.workflow-receipt.v1', 'ok': True, 'status': 'partial'}, {'schema': 'mq.workflow-receipt.v1', 'ok': True, 'completeness': {'status': 'complete'}, 'verification': {'status': 'passed'}}, {'schema': 'mq.workflow-receipt.v1', 'ok': True, 'status': 'passed', 'completeness': {'status': 'complete'}, 'verification': {'status': 'passed'}}):
        result = run(malformed)
        assert result.returncode == 2, result
        assert 'ERROR:' in result.stderr
    result = subprocess.run([str(root / 'bin/mq-hal'), 'workflow-receipt'], input='{', text=True, capture_output=True, env=env)
    assert result.returncode == 2
    assert list(Path(temp).iterdir()) == [path], 'renderer wrote state/logs'
print('OK: workflow receipt smoke test passed')
PY
