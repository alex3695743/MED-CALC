"""Batería única de verificación del cálculo y la API eGFR."""

import hashlib
import json
import sys
import unittest
from decimal import Decimal
from math import inf, nextafter
from pathlib import Path

from httpx import ASGITransport, AsyncClient

import egfr
from main import Estimate, app, compare_estimates
from tests.reference import calculate, category

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'
DATA = TESTS / 'data'
EGFR_URL = '/api/egfr'
SOURCES = json.loads((DATA / 'sources.json').read_text(encoding='utf-8'))
CASES = json.loads((DATA / 'reference-cases.json').read_text(encoding='utf-8'))
OBSERVATIONS = []

# Resultados esperados transcritos de la matriz KDIGO 2024, S126 (PDF 11).
EXPECTED_KDIGO_RISKS = {
    'G1': ('low', 'moderate', 'high'),
    'G2': ('low', 'moderate', 'high'),
    'G3a': ('moderate', 'high', 'very_high'),
    'G3b': ('high', 'very_high', 'very_high'),
    'G4': ('very_high', 'very_high', 'very_high'),
    'G5': ('very_high', 'very_high', 'very_high'),
}


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
                self.assertIsNone(result['kdigo'])
                expected = float(case['expected_value'])
                self.assertLessEqual(abs(result['value'] - expected), tolerance(expected))
                self.assertEqual(result['category'], case['expected_category'])
                self.assertEqual(result['unit'], 'mL/min/1.73 m²')
                equations = {'creatinine': 'CKD-EPI 2021 eGFRcr', 'cystatin': 'CKD-EPI 2012 eGFRcys', 'combined': 'CKD-EPI 2021 eGFRcr-cys'}
                self.assertEqual(result['equation'], equations[case['method']])
                if case['creatinine_mg_dl'] is not None:
                    # La misma entrada física en SI debe conservar resultado, categoría y avisos.
                    si_payload = {key: value for key, value in payload.items() if key != 'creatinine_mg_dl'}
                    si_value = float(Decimal(case['creatinine_mg_dl']) * Decimal('88.4'))
                    si_payload['creatinine_umol_l'] = si_value
                    si_response = await self.client.post(EGFR_URL, json=si_payload)
                    self.assertEqual(si_response.status_code, 200, si_response.text)
                    si_result = si_response.json()
                    self.assertLessEqual(abs(si_result['value'] - expected), tolerance(expected))
                    self.assertEqual(si_result['category'], result['category'])
                    self.assertEqual(si_result['equation'], result['equation'])
                    self.assertEqual(si_result['unit'], result['unit'])
                    self.assertEqual([w['field'] for w in si_result['warnings']],
                                     ['creatinine_umol_l' if w['field'] == 'creatinine_mg_dl' else w['field'] for w in result['warnings']])
                    for name, comparison in result['comparisons'].items():
                        self.assertEqual(si_result['comparisons'][name]['category'], comparison['category'])
                        self.assertLessEqual(abs(si_result['comparisons'][name]['value'] - comparison['value']), tolerance(comparison['value']))
                    if result['discrepancy'] is not None:
                        self.assertEqual(si_result['discrepancy']['detected'], result['discrepancy']['detected'])
                        self.assertEqual(si_result['discrepancy']['different_categories'], result['discrepancy']['different_categories'])
                    OBSERVATIONS.append({'kind': 'conversion', 'id': case['id'], 'method': case['method'],
                                         'creatinine_umol_l': si_value, 'expected': case['expected_value'],
                                         'actual': si_result['value'], 'difference': abs(si_result['value'] - expected),
                                         'tolerance': tolerance(expected), 'source_ids': ['NIDDK-ADULTS']})
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
                    cr, cy = result['comparisons']['creatinine'], result['comparisons']['cystatin']
                    discrepancy = result['discrepancy']
                    difference = abs(cr['value'] - cy['value'])
                    different_categories = cr['category'] != cy['category']
                    self.assertEqual(discrepancy['absolute_difference'], difference)
                    self.assertEqual(discrepancy['threshold'], 25)
                    self.assertEqual(discrepancy['different_categories'], different_categories)
                    detected = difference >= 25 or different_categories
                    self.assertEqual(discrepancy['detected'], detected)
                    self.assertEqual(bool(discrepancy['message']), detected)
                else:
                    self.assertEqual(result['comparisons'], {})
                    self.assertIsNone(result['discrepancy'])

        # Avisos no bloqueantes en los límites operativos de revisión de entradas.
        warning_cases = []
        for method, field, boundaries in [
            ('creatinine', 'creatinine_mg_dl', [(0.199, True), (0.2, False), (0.201, False), (14.999, False), (15, False), (15.001, True)]),
            ('cystatin', 'cystatin_mg_l', [(0.299, True), (0.3, False), (0.301, False), (7.999, False), (8, False), (8.001, True)]),
            ('creatinine', 'creatinine_umol_l', [(17.5916, True), (17.68, False), (17.7684, False), (1325.9116, False), (1326, False), (1326.0884, True)]),
        ]:
            for value, warned in boundaries:
                warning_cases.append((method, {field: value}, [field] if warned else []))
        warning_cases.extend([
            ('combined', {'creatinine_mg_dl': 0.1, 'cystatin_mg_l': 0.1}, ['creatinine_mg_dl', 'cystatin_mg_l']),
            ('combined', {'creatinine_mg_dl': 0.2, 'cystatin_mg_l': 8}, []),
            ('combined', {'creatinine_mg_dl': 16, 'cystatin_mg_l': 0.9}, ['creatinine_mg_dl']),
        ])
        for method, fields, expected_fields in warning_cases:
            with self.subTest(method=method, fields=fields):
                response = await self.client.post(EGFR_URL, json={'age': 62, 'sex': 'F', 'method': method, **fields})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual([warning['field'] for warning in result['warnings']], expected_fields)
                self.assertGreater(result['value'], 0)
                for warning in result['warnings']:
                    unit = {'creatinine_mg_dl': 'mg/dL', 'creatinine_umol_l': 'µmol/L', 'cystatin_mg_l': 'mg/L'}[warning['field']]
                    self.assertIn(unit, warning['message'])

        # Las 18 celdas G×A a través de la API, sin modificar la eGFR original.
        for gfr, cr in [('G1', 0.5), ('G2', 1), ('G3a', 1.2), ('G3b', 1.7), ('G4', 2.5), ('G5', 5)]:
            payload = {'age': 62, 'sex': 'F', 'method': 'creatinine', 'creatinine_mg_dl': cr}
            baseline = (await self.client.post(EGFR_URL, json=payload)).json()
            self.assertEqual(baseline['category'], gfr)
            for index, (acr, albuminuria) in enumerate([(10, 'A1'), (80, 'A2'), (500, 'A3')]):
                with self.subTest(gfr=gfr, albuminuria=albuminuria):
                    response = await self.client.post(EGFR_URL, json={**payload, 'acr_mg_g': acr})
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()
                    self.assertEqual(result['value'], baseline['value'])
                    assessment = result['kdigo']
                    self.assertEqual(assessment['acr_mg_g'], acr)
                    self.assertEqual(assessment['gfr_category'], gfr)
                    self.assertEqual(assessment['albuminuria_category'], albuminuria)
                    self.assertEqual(assessment['risk_level'], EXPECTED_KDIGO_RISKS[gfr][index])
                    self.assertEqual(assessment['risk_matrix'], {key: list(value) for key, value in EXPECTED_KDIGO_RISKS.items()})
                    self.assertTrue(assessment['risk_label'])
                    OBSERVATIONS.append({'kind': 'kdigo', 'gfr_category': gfr, 'acr_mg_g': acr,
                                         'albuminuria_category': albuminuria, 'risk_level': assessment['risk_level'],
                                         'source_ids': ['KDIGO-2024']})

        # Cero es un CAC válido; ausencia y null no deben asignar A1 por defecto.
        for method, fields in [('creatinine', {'creatinine_umol_l': 106.08}),
                               ('cystatin', {'cystatin_mg_l': 0.9}),
                               ('combined', {'creatinine_mg_dl': 1.2, 'cystatin_mg_l': 0.9})]:
            payload = {'age': 62, 'sex': 'F', 'method': method, **fields}
            for acr, expected in [(None, None), (0, 'A1'), (29.999, 'A1'), (30, 'A2'),
                                  (300, 'A2'), (300.001, 'A3'), (1e308, 'A3')]:
                with self.subTest(method=method, acr=acr):
                    response = await self.client.post(EGFR_URL, json={**payload, 'acr_mg_g': acr})
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()
                    if expected is None:
                        self.assertIsNone(result['kdigo'])
                    else:
                        self.assertEqual(result['kdigo']['albuminuria_category'], expected)
                        self.assertEqual(result['kdigo']['gfr_category'], result['category'])

    async def test_invalid_json_types_and_numeric_extremes(self):
        valid = {'age': 62, 'sex': 'F', 'method': 'creatinine', 'creatinine_mg_dl': 1.2}
        changes = [{'age': 17}, {'age': 121}, {'age': 200}, {'age': None}, {'age': True}, {'age': 62.5}, {'age': '62'},
                   {'sex': 'X'}, {'method': 'unknown'},
                   {'creatinine_mg_dl': True}, {'creatinine_mg_dl': '1.2'},
                   {'creatinine_mg_dl': 'abc'}, {'creatinine_mg_dl': 0}, {'creatinine_mg_dl': -1},
                   {'creatinine_mg_dl': float('nan')}, {'creatinine_mg_dl': float('inf')},
                   {'creatinine_mg_dl': 1e308}, {'unit': 'µmol/L'}]
        changes.extend({'creatinine_umol_l': value} for value in [88.4, 0, -1, True, '88.4', float('nan'), float('inf')])
        changes.extend({'acr_mg_g': value} for value in [-1, -1e-300, True, '80', '', [], {}, float('nan'), float('inf')])
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
            {'method': 'cystatin', 'creatinine_umol_l': 88.4, 'cystatin_mg_l': 0.9},
            {'method': 'creatinine', 'creatinine_umol_l': 0},
            {'method': 'creatinine', 'creatinine_umol_l': -1},
            {'method': 'creatinine', 'creatinine_umol_l': True},
            {'method': 'creatinine', 'creatinine_umol_l': '88.4'},
            {'method': 'creatinine', 'creatinine_umol_l': 1e308},
            {'method': 'creatinine', 'creatinine_umol_l': 5e-324},
        ]:
            payloads.append({'age': 62, 'sex': 'F', **fields})
        for payload in payloads:
            with self.subTest(payload=payload):
                response = await self.client.post(EGFR_URL, content=json.dumps(payload), headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn('value', response.json())
                self.assertIsInstance(response.json()['detail'], str)
        for body in ['{', '[]', 'null']:
            with self.subTest(body=body):
                response = await self.client.post(EGFR_URL, content=body, headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422, response.text)
        for age in [18, 120]:
            with self.subTest(age=age):
                response = await self.client.post(EGFR_URL, json={**valid, 'age': age})
                self.assertEqual(response.status_code, 200, response.text)

        # Errores específicos incluso si se accede a la API sin pasar por la web.
        for change, field, fragment in [
            ({'age': 121}, 'age', '18 a 120'),
            ({'sex': 'X'}, 'sex', 'sexo'),
            ({'method': 'unknown'}, 'method', 'método'),
            ({'creatinine_mg_dl': 'abc'}, 'creatinine_mg_dl', 'creatinina válida en mg/dL'),
            ({'creatinine_mg_dl': None}, 'creatinine_mg_dl', 'creatinina válida en mg/dL'),
            ({'method': 'combined', 'cystatin_mg_l': 0}, 'cystatin_mg_l', 'cistatina C válida en mg/L'),
            ({'method': 'combined'}, 'cystatin_mg_l', 'cistatina C válida en mg/L'),
            ({'cystatin_mg_l': 1}, 'cystatin_mg_l', 'método seleccionado'),
            ({'acr_mg_g': -1}, 'acr_mg_g', 'CAC válido en mg/g'),
        ]:
            with self.subTest(change=change):
                response = await self.client.post(EGFR_URL, json={**valid, **change})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIn(fragment, response.json()['errors'][field])

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
        # Se exige al menos el formato binario de doble precisión para las ecuaciones.
        self.assertGreaterEqual(sys.float_info.mant_dig, 53)
        self.assertGreaterEqual(sys.float_info.max_exp, 1024)
        for si, conventional in [(17.68, 0.2), (61.88, 0.7), (70.72, 0.8), (79.56, 0.9),
                                 (88.4, 1), (106.08, 1.2), (1326, 15)]:
            with self.subTest(creatinine_umol_l=si):
                self.assertEqual(egfr.creatinine_to_mg_dl(si), conventional)
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
        for value, expected in [(0, 'A1'), (nextafter(30, -inf), 'A1'), (30, 'A2'),
                                (nextafter(30, inf), 'A2'), (nextafter(300, -inf), 'A2'),
                                (300, 'A2'), (nextafter(300, inf), 'A3')]:
            with self.subTest(acr_mg_g=value):
                self.assertEqual(egfr.albuminuria_category(value), expected)
        for invalid in [-1, float('nan'), inf]:
            with self.subTest(acr_mg_g=invalid):
                with self.assertRaises(ValueError):
                    egfr.albuminuria_category(invalid)
        for gfr, risks in EXPECTED_KDIGO_RISKS.items():
            for index, albuminuria in enumerate(['A1', 'A2', 'A3']):
                with self.subTest(gfr=gfr, albuminuria=albuminuria):
                    self.assertEqual(egfr.kdigo_risk_level(gfr, albuminuria), risks[index])

        for boundary, below, above in [(15, 'G5', 'G4'), (30, 'G4', 'G3b'), (45, 'G3b', 'G3a'), (60, 'G3a', 'G2'), (90, 'G2', 'G1')]:
            for value, expected in [(boundary - 0.001, below), (nextafter(boundary, -inf), below), (boundary, above), (boundary + 0.001, above)]:
                with self.subTest(value=value):
                    self.assertEqual(egfr.gfr_category(value), expected)

        # Aislar cada condición de la regla y comprobar el umbral sin redondear.
        for cr, cy, detected, category_changed in [
            (100, nextafter(125, -inf), False, False),
            (100, 125, True, False),
            (nextafter(125, inf), 100, True, False),
            (59.999, 60, True, True),
            (60, 59.999, True, True),
            (65, 65, False, False),
            (35, 90, True, True),
        ]:
            with self.subTest(creatinine=cr, cystatin=cy):
                comparison = compare_estimates(
                    Estimate(value=cr, category=egfr.gfr_category(cr), equation='cr'),
                    Estimate(value=cy, category=egfr.gfr_category(cy), equation='cy'),
                )
                self.assertEqual(comparison.detected, detected)
                self.assertEqual(comparison.different_categories, category_changed)
