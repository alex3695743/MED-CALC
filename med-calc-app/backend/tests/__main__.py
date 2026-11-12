"""Ejecuta las pruebas locales y deja un informe auditable, sin acceso a red."""

import argparse
import hashlib
import json
import os
import platform
import sys
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'


class ReportResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        self.events.append({'id': str(subtest), 'status': 'passed' if error is None else 'failed',
                            'detail': '' if error is None else self._exc_info_to_string(error, test)})

    def addSuccess(self, test):
        super().addSuccess(test)
        self.events.append({'id': test.id(), 'status': 'passed'})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.events.append({'id': test.id(), 'status': 'failed', 'detail': self._exc_info_to_string(error, test)})

    def addError(self, test, error):
        super().addError(test, error)
        self.events.append({'id': test.id(), 'status': 'error', 'detail': self._exc_info_to_string(error, test)})

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.events.append({'id': test.id(), 'status': 'known_discrepancy', 'detail': self._exc_info_to_string(error, test)})

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.events.append({'id': test.id(), 'status': 'unexpected_success', 'detail': 'Revisar la marca expectedFailure.'})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.events.append({'id': test.id(), 'status': 'skipped', 'detail': reason})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true', help='Falla también por discrepancias conocidas o pruebas omitidas.')
    args = parser.parse_args()
    os.chdir(ROOT)
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_suite')
    result = unittest.TextTestRunner(verbosity=2, resultclass=ReportResult).run(suite)

    reference_module = sys.modules.get('tests.test_suite')
    sources = json.loads((TESTS / 'data/sources.json').read_text(encoding='utf-8'))
    observations = getattr(reference_module, 'OBSERVATIONS', [])
    counts = Counter(row['kind'] for row in observations)
    raw = [row for row in observations if row['kind'] == 'raw']
    hashes = {}
    for path in [ROOT / 'egfr.py', ROOT / 'main.py', TESTS / 'requirements.lock', *sorted(TESTS.glob('*.py'))]:
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    status = 'FAILED'
    if result.wasSuccessful():
        status = 'WITH_KNOWN_DISCREPANCY' if result.expectedFailures or result.skipped else 'PASSED'
    exit_code = int(not result.wasSuccessful() or (args.strict and bool(result.expectedFailures or result.skipped)))
    report = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': status,
        'strict_mode': args.strict,
        'exit_code': exit_code,
        'python': platform.python_version(), 'platform': platform.platform(),
        'reference_set_version': sources['reference_set_version'],
        'clinical_signoff': sources['review']['clinical_signoff'],
        'test_methods': result.testsRun,
        'observations_by_kind': dict(counts),
        'events_by_status': dict(Counter(event['status'] for event in result.events)),
        'maximum_raw_absolute_error': max((row['difference'] for row in raw), default=None),
        'events': result.events, 'observations': observations,
        'tested_files_sha256': hashes,
        'evidence_manifest_sha256': hashlib.sha256((TESTS / 'data/sha256.json').read_bytes()).hexdigest(),
        'pending_criteria': sources['pending_criteria'],
    }
    reports = TESTS / 'reports'
    reports.mkdir(exist_ok=True)
    (reports / 'latest-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\nInforme: {reports / "latest-report.json"}')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
