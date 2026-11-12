"""Batería única de verificación del cálculo y la API eGFR."""

import hashlib
import json
import unittest
from decimal import Decimal
from math import inf, nextafter
from pathlib import Path

from httpx import ASGITransport, AsyncClient

import egfr
from main import app
from tests.reference import calculate, category

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'
DATA = TESTS / 'data'
EGFR_URL = '/api/egfr'
SOURCES = json.loads((DATA / 'sources.json').read_text(encoding='utf-8'))
CASES = json.loads((DATA / 'reference-cases.json').read_text(encoding='utf-8'))
OBSERVATIONS = []


def actual_value(case):
    args = [case['age'], case['sex'] == 'F']
    if case['creatinine_mg_dl'] is not None:
        args.append(float(case['creatinine_mg_dl']))
    if case['cystatin_mg_l'] is not None:
        args.append(float(case['cystatin_mg_l']))
    function_name = {'creatinine': 'creatinine_2021', 'cystatin': 'cystatin_2012', 'combined': 'combined_2021'}[case['method']]
    return getattr(egfr, function_name)(*args)


def tolerance(expected):
    policy = SOURCES['acceptance']
    return policy['raw_absolute_tolerance'] + policy['raw_relative_tolerance'] * abs(expected)


class EgfrTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver')
        self.addAsyncCleanup(self.client.aclose)


    async def test_frozen_cases_through_api(self):
        for case in CASES:
            payload = {'age': case['age'], 'sex': case['sex'], 'method': case['method']}
            for marker in ['creatinine_mg_dl', 'cystatin_mg_l']:
                if case[marker] is not None:
                    payload[marker] = float(case[marker])
            with self.subTest(case=case['id']):
                response = await self.client.post(EGFR_URL, json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                expected = float(case['expected_value'])
                self.assertLessEqual(abs(result['value'] - expected), tolerance(expected))
                self.assertEqual(result['category'], case['expected_category'])
                self.assertEqual(result['unit'], 'mL/min/1.73 m²')
                equations = {'creatinine': 'CKD-EPI 2021 eGFRcr', 'cystatin': 'CKD-EPI 2012 eGFRcys', 'combined': 'CKD-EPI 2021 eGFRcr-cys'}
                self.assertEqual(result['equation'], equations[case['method']])
                if case['method'] == 'combined':
                    self.assertEqual(set(result['comparisons']), {'creatinine', 'cystatin'})
                    for method in ['creatinine', 'cystatin']:
                        reference = calculate(method, case['age'], case['sex'],
                                              case['creatinine_mg_dl'] if method == 'creatinine' else None,
                                              case['cystatin_mg_l'] if method == 'cystatin' else None)
                        comparison = result['comparisons'][method]
                        self.assertEqual(comparison['equation'], equations[method])
                        self.assertLessEqual(abs(comparison['value'] - float(reference)), tolerance(float(reference)))
                        self.assertEqual(comparison['category'], category(reference))
                else:
                    self.assertEqual(result['comparisons'], {})

    async def test_invalid_json_types_and_numeric_extremes(self):
        valid = {'age': 62, 'sex': 'F', 'method': 'creatinine', 'creatinine_mg_dl': 1.2}
        changes = [{'age': 17}, {'age': None}, {'age': True}, {'age': 62.5}, {'age': '62'},
                   {'sex': 'X'}, {'method': 'unknown'},
                   {'creatinine_mg_dl': True}, {'creatinine_mg_dl': '1.2'},
                   {'creatinine_mg_dl': 'abc'}, {'creatinine_mg_dl': 0}, {'creatinine_mg_dl': -1},
                   {'creatinine_mg_dl': float('nan')}, {'creatinine_mg_dl': float('inf')},
                   {'creatinine_mg_dl': 1e308}, {'unit': 'µmol/L'}]
        payloads = [{**valid, **change} for change in changes]
        for missing in ['age', 'sex', 'creatinine_mg_dl']:
            payloads.append({name: value for name, value in valid.items() if name != missing})
        for fields in [
            {'method': 'cystatin'},
            {'method': 'cystatin', 'cystatin_mg_l': 0},
            {'method': 'cystatin', 'cystatin_mg_l': 0.9, 'creatinine_mg_dl': 1.2},
            {'method': 'combined', 'cystatin_mg_l': 0.9},
            {'method': 'combined', 'creatinine_mg_dl': 1.2},
            {'method': 'combined', 'creatinine_mg_dl': 1.2, 'cystatin_mg_l': -0.9},
        ]:
            payloads.append({'age': 62, 'sex': 'F', **fields})
        for payload in payloads:
            with self.subTest(payload=payload):
                response = await self.client.post(EGFR_URL, content=json.dumps(payload), headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn('value', response.json())
        for body in ['{', '[]', 'null']:
            with self.subTest(body=body):
                response = await self.client.post(EGFR_URL, content=body, headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422, response.text)

    def test_evidence_integrity(self):
        manifest = json.loads((DATA / 'sha256.json').read_text(encoding='utf-8'))
        required = {'tests/data/reference-cases.json',
                    'tests/data/sources.json', 'tests/reference.py',
                    'tests/generate_reference.py', 'tests/requirements.lock'}
        required.update(path.relative_to(ROOT).as_posix() for path in (TESTS / 'evidence').glob('*'))
        self.assertEqual(set(manifest), required)
        for name, digest in manifest.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_raw_values_against_frozen_reference(self):
        self.assertEqual(len(CASES), 126)
        self.assertEqual(len({case['id'] for case in CASES}), len(CASES))
        for case in CASES:
            expected = float(case['expected_value'])
            actual = actual_value(case)
            allowed = tolerance(expected)
            OBSERVATIONS.append({'kind': 'raw', 'id': case['id'], 'method': case['method'],
                                 'inputs': {name: case[name] for name in ['age', 'sex', 'creatinine_mg_dl', 'cystatin_mg_l']},
                                 'expected': case['expected_value'], 'actual': actual,
                                 'difference': abs(actual - expected), 'tolerance': allowed,
                                 'source_ids': case['source_ids']})
            with self.subTest(case=case['id']):
                self.assertLessEqual(abs(actual - expected), allowed, f'{case}: obtenido={actual}')
                self.assertEqual(egfr.gfr_category(actual), case['expected_category'])

    def test_nkf_observed_outputs(self):
        observed = json.loads((TESTS / 'evidence/nkf-observed.json').read_text(encoding='utf-8'))
        outputs = {'creatinine': 'result_1', 'combined': 'result_2', 'cystatin': 'result_3'}
        for anchor in observed['cases']:
            for method, field in outputs.items():
                case = {'method': method, 'age': anchor['age'], 'sex': anchor['sex'][0],
                        'creatinine_mg_dl': anchor['cr'] if method != 'cystatin' else None,
                        'cystatin_mg_l': anchor['cy'] if method != 'creatinine' else None}
                external = Decimal(anchor['observed'][field])
                reference = calculate(method, case['age'], case['sex'], case['creatinine_mg_dl'], case['cystatin_mg_l'])
                actual = actual_value(case)
                OBSERVATIONS.append({'kind': 'nkf', 'id': anchor['id'], 'method': method,
                                     'observed': str(external), 'reference': str(reference), 'actual': actual,
                                     'difference': abs(actual - float(external)), 'tolerance': 0.50000001,
                                     'source_ids': ['NKF-CALCULATOR'], 'evidence': 'tests/evidence/' + anchor['id'] + '.png'})
                with self.subTest(anchor=anchor['id'], method=method):
                    self.assertLessEqual(abs(reference - external), Decimal('0.5'))
                    self.assertLessEqual(abs(actual - float(external)), 0.50000001)

    def test_kdigo_boundary_neighbourhood(self):
        for boundary, below, above in [(15, 'G5', 'G4'), (30, 'G4', 'G3b'), (45, 'G3b', 'G3a'), (60, 'G3a', 'G2'), (90, 'G2', 'G1')]:
            for value, expected in [(boundary - 0.001, below), (nextafter(boundary, -inf), below), (boundary, above), (boundary + 0.001, above)]:
                with self.subTest(value=value):
                    self.assertEqual(egfr.gfr_category(value), expected)
