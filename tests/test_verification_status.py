"""Operator evidence must remain separate from structural/runtime scores."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verification_status as evidence
import audit
import stack_status


def response(status):
    return {'schema': 'doctor.v1', 'verification': {
        'status': status, 'source': 'mq-agent', 'scope': 'changed_files_against_HEAD',
        'code_status': status, 'receipt_id': 'a' * 64, 'fingerprint': 'b' * 64}}


class VerificationTests(unittest.TestCase):
    def test_default_never_starts_provider(self):
        with patch.object(evidence.subprocess, 'run', side_effect=AssertionError('unexpected call')):
            self.assertEqual(evidence.collect(Path('.'))['status'], 'NOT_VERIFIED')

    def run_provider(self, payload, rc=0):
        def run(args, **kw):
            self.assertEqual(args[1:3], ['doctor', str(Path('.').resolve())])
            self.assertEqual(args[3:], ['--verification', '--json'])
            kw['stdout'].write(json.dumps(payload).encode())
            return subprocess.CompletedProcess(args, rc)
        return patch.object(evidence.subprocess, 'run', side_effect=run)

    def test_statuses(self):
        for status in ['PASS', 'FAIL', 'STALE', 'NOT_VERIFIED']:
            with self.subTest(status=status), self.run_provider(response(status)):
                got = evidence.collect(Path('.'), enabled=True)
                self.assertEqual(got['status'], status)
                self.assertNotIn('receipt_id', got)
                self.assertTrue(got['next_action'])

    def test_invalid_and_old_provider(self):
        for payload in [[], {}, {'schema': 'doctor.v1'}, response('ready'), response([]),
                        {'schema': 'doctor.v1', 'verification': {'status': 'PASS'}}]:
            with self.subTest(payload=payload), self.run_provider(payload):
                self.assertEqual(evidence.collect(Path('.'), enabled=True)['status'], 'NOT_VERIFIED')

    def test_provider_failures(self):
        for error in [FileNotFoundError(), subprocess.TimeoutExpired('doctor', 35)]:
            with self.subTest(error=error), patch.object(evidence.subprocess, 'run', side_effect=error):
                self.assertEqual(evidence.collect(Path('.'), enabled=True)['status'], 'NOT_VERIFIED')
        with self.run_provider(response('PASS'), rc=2):
            self.assertEqual(evidence.collect(Path('.'), enabled=True)['status'], 'NOT_VERIFIED')

    def test_summary_no_vacuous_pass(self):
        self.assertEqual(evidence.summary({}), 'NOT_VERIFIED')
        self.assertEqual(evidence.summary({'a': {'status': 'PASS'}, 'b': {'status': 'STALE'}}), 'STALE')
        self.assertEqual(evidence.summary({'a': {'status': 'PASS'}, 'b': {'status': 'FAIL'}}), 'FAIL')

    def test_audit_sample_json_and_text(self):
        for flags in [['--sample', '--json', '--verification'], ['--sample']]:
            with patch.object(evidence.subprocess, 'run', side_effect=AssertionError('sample called provider')):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(audit.main(flags), 0)
                if '--json' in flags:
                    self.assertEqual(json.loads(out.getvalue())['verification']['status'], 'NOT_VERIFIED')
                else:
                    self.assertIn('Code verification: NOT_VERIFIED', out.getvalue())

    def test_cockpit_projection_uses_config_not_external_paths(self):
        cockpit = {'components': [{'name': 'repo-signal', 'path': '/untrusted'}, {'name': 'unknown'}],
                   'overall': {'score': 100}}
        with patch.object(evidence, 'collect', return_value={'status': 'STALE', 'next_action': 'Review plan'}) as collect:
            result = stack_status.with_verification(cockpit, enabled=True,
                                                    repos={'repo-signal': '.'})
            collect.assert_called_once_with(Path('.'), enabled=True)
            self.assertEqual(result['verification_summary'], 'STALE')
            self.assertEqual(result['verification']['unknown']['status'], 'NOT_VERIFIED')
            self.assertEqual(result['overall'], cockpit['overall'])
            self.assertNotIn('verification', cockpit)

    def test_stack_main_both_formats_and_legacy(self):
        import tempfile
        from hal.stack import CockpitResult
        with tempfile.TemporaryDirectory() as tmp:
            config = {'repos': {'example': tmp}}
            cockpit = {'repos': [{'name': 'example', 'status': 'PASS'}], 'status': 'PASS'}
            legacy = {'repos': [{'name': 'example', 'exists': True, 'dirty': False,
                                 'branch': 'main', 'version': '1', 'publish':
                                 {'available': True, 'score': 100, 'total': 100, 'status': 'ready'}}],
                      'status': 'ok', 'tools': {}, 'recommendation': 'Existing recommendation'}
            for mode in [[], ['--legacy']]:
                for fmt in [[], ['--json']]:
                    with self.subTest(mode=mode, fmt=fmt), \
                         patch.object(stack_status, 'load_config', return_value=config), \
                         patch.object(stack_status, 'collect', return_value=legacy), \
                         patch.object(stack_status.operator_stack, 'read_cockpit',
                                      return_value=CockpitResult(cockpit, '', [], 0, '')), \
                         patch.object(evidence, 'collect', return_value=
                                      {**evidence.unverified(), 'status': 'STALE'}) as collect:
                        out = io.StringIO()
                        with contextlib.redirect_stdout(out):
                            self.assertEqual(stack_status.main(mode + fmt + ['--verification']), 0)
                        collect.assert_called_once_with(Path(tmp), enabled=True)
                        if fmt:
                            self.assertEqual(json.loads(out.getvalue())['verification_summary'], 'STALE')
                        else:
                            self.assertIn('example: STALE', out.getvalue())

    def test_audit_main_live_projection(self):
        publish = {'available': True, 'score': 16, 'total': 16, 'checks': []}
        readme = {'available': True, 'score': 100, 'total': 100, 'missing': []}
        with patch.object(audit, 'resolve_repo', return_value=('example', Path('.'))), \
             patch.object(audit, 'collect_publish', return_value=publish), \
             patch.object(audit, 'collect_readme', return_value=readme), \
             self.run_provider(response('FAIL')):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                audit.main(['--verification', '--json'])
            result = json.loads(out.getvalue())
            self.assertEqual(result['verification']['status'], 'FAIL')
            self.assertEqual(result['overall'], 'ready')
            self.assertIn('Structural', result['recommendation'])

    def test_unavailable_cockpit_is_explicitly_unverified(self):
        from hal.stack import CockpitResult
        with patch.object(stack_status.operator_stack, 'read_cockpit',
                          return_value=CockpitResult(None, '', [], 127, 'unavailable')), \
             patch.object(evidence, 'collect', side_effect=AssertionError('unexpected read')):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(stack_status.main(['--json', '--verification']), 1)
            self.assertEqual(json.loads(out.getvalue())['verification_summary'], 'NOT_VERIFIED')


if __name__ == '__main__':
    unittest.main()
